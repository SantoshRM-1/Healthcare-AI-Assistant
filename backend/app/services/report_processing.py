import logging
import time
import traceback
import uuid
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.db.session import SessionFactory
from app.models.uploaded_report import UploadedReport
from app.services.report_ocr import run_ocr
from app.services.report_storage import create_private_download_url
from app.services.vector_store import delete_report_vectors, index_report

logger = logging.getLogger(__name__)


async def process_report(report_id: uuid.UUID) -> None:
    processing_started = time.perf_counter()
    logger.info("REPORT PROCESSING STARTED report_id=%s", report_id)
    try:
        async with SessionFactory() as session:
            report = await session.get(UploadedReport, report_id)
            if report is None:
                logger.error("REPORT PROCESSING ABORTED report_id=%s reason=database_row_missing", report_id)
                return
            if report.processing_status == "deleting":
                logger.info("REPORT PROCESSING ABORTED report_id=%s reason=deleting", report_id)
                return
            report.processing_status = "processing"
            report.processing_stage = "processing"
            report.processing_error = None
            report.processing_started_at = datetime.now(timezone.utc)
            report.chunks_created = 0
            report.embeddings_created = 0
            report.vectors_saved = 0
            await session.commit()
            public_id = report.cloudinary_public_id
            resource_type = report.cloudinary_resource_type
            file_type = report.file_type
            extracted = report.raw_extracted_text
            user_id, session_id, report_name = report.user_id, report.session_id, report.file_name
        logger.info("REPORT STATUS COMMITTED report_id=%s status=processing stage=processing", report_id)

        if not extracted:
            await _set_stage(report_id, "extracting_text")
            logger.info("REPORT OCR STARTED report_id=%s file_type=%s", report_id, file_type)
            url = await create_private_download_url(public_id, resource_type, file_type)
            download_started = time.perf_counter()
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=20.0), follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
            logger.info("report_timing report_id=%s stage=source_download bytes=%d seconds=%.3f", report_id, len(response.content), time.perf_counter() - download_started)
            ocr_started = time.perf_counter()
            extracted = await run_ocr(response.content, file_type, settings.report_max_pdf_pages, str(report_id))
            logger.info("report_timing report_id=%s stage=ocr seconds=%.3f", report_id, time.perf_counter() - ocr_started)
            logger.info("REPORT OCR COMPLETED report_id=%s characters=%d", report_id, len(extracted))
            async with SessionFactory() as session:
                report = await session.get(UploadedReport, report_id)
                if report is None:
                    raise RuntimeError(f"Report {report_id} was deleted after text extraction")
                report.raw_extracted_text = extracted
                report.processing_stage = "generating_embeddings"
                await session.commit()
                logger.info("REPORT OCR TEXT COMMITTED report_id=%s characters=%d", report_id, len(extracted))
        else:
            logger.info("REPORT OCR CACHE HIT report_id=%s characters=%d", report_id, len(extracted))
            await _set_stage(report_id, "generating_embeddings")

        logger.info("REPORT CHUNKING AND INDEXING STARTED report_id=%s", report_id)
        await index_report(
            report_id,
            user_id,
            session_id,
            report_name,
            extracted or "",
            progress=lambda key, value: _record_progress(report_id, key, value),
        )

        remove_vectors = False
        async with SessionFactory() as session:
            report = await session.get(UploadedReport, report_id)
            if report is None or report.processing_status == "deleting":
                remove_vectors = True
            else:
                report.processing_status = "completed"
                report.processing_stage = "completed"
                report.processing_error = None
                report.processing_started_at = None
                report.indexed_at = datetime.now(timezone.utc)
                await session.commit()
                logger.info("REPORT COMPLETED report_id=%s chunks=%d embeddings=%d vectors=%d", report_id, report.chunks_created, report.embeddings_created, report.vectors_saved)
        if remove_vectors:
            await delete_report_vectors(report_id)
        logger.info("report_timing report_id=%s stage=total seconds=%.3f", report_id, time.perf_counter() - processing_started)
    except Exception as exc:
        formatted_traceback = traceback.format_exc()
        logger.error("REPORT FAILED report_id=%s error=%r\n%s", report_id, exc, formatted_traceback)
        try:
            async with SessionFactory() as session:
                report = await session.get(UploadedReport, report_id)
                if report is not None and report.processing_status != "deleting":
                    report.processing_status = "failed"
                    report.processing_stage = "failed"
                    report.processing_error = f"{type(exc).__name__}: {exc}\n{formatted_traceback}"[-16_000:]
                    report.processing_started_at = None
                    await session.commit()
                    logger.info("REPORT FAILURE SAVED report_id=%s status=failed", report_id)
        except Exception:
            logger.exception("Could not persist report failure state report_id=%s", report_id)


async def _record_progress(report_id: uuid.UUID, key: str, value: int) -> None:
    async with SessionFactory() as session:
        report = await session.get(UploadedReport, report_id)
        if report is None:
            raise RuntimeError(f"Report {report_id} disappeared during indexing")
        if key == "chunks_created":
            report.chunks_created = value
        elif key == "embeddings_created":
            report.embeddings_created = value
        elif key == "storing_vectors":
            report.processing_stage = "storing_vectors"
        elif key == "vectors_saved":
            report.vectors_saved = value
        await session.commit()
        logger.info("REPORT PROGRESS COMMITTED report_id=%s metric=%s value=%d", report_id, key, value)


async def _set_stage(report_id: uuid.UUID, stage: str) -> None:
    async with SessionFactory() as session:
        report = await session.get(UploadedReport, report_id)
        if report is not None:
            report.processing_stage = stage
            await session.commit()
            logger.info("REPORT STAGE COMMITTED report_id=%s stage=%s", report_id, stage)
