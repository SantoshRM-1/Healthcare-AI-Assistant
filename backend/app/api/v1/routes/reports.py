import asyncio
import io
import logging
import time
import uuid
from pathlib import Path
from urllib.parse import quote

import fitz
import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal, get_principal
from app.core.config import settings
from app.db.session import get_session
from app.models.uploaded_report import UploadedReport
from app.repositories.users import get_or_create_user
from app.schemas.ai import MedicalReportSummary, ReportSummaryResponse
from app.schemas.report import ReportProcessingDebug, ReportRead, ReportSummary
from app.services.chats import owned_chat
from app.services.report_storage import (
    create_private_download_url,
    delete_report_asset,
    upload_report,
)
from app.services.vector_store import delete_report_vectors

logger = logging.getLogger(__name__)
router = APIRouter()
ALLOWED_TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def _verify_file(data: bytes, suffix: str) -> None:
    valid = {
        ".pdf": data.startswith(b"%PDF-"),
        ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": data.startswith(b"\xff\xd8\xff"),
        ".jpeg": data.startswith(b"\xff\xd8\xff"),
        ".webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    }
    if not valid.get(suffix, False):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File contents do not match a supported report format")
    try:
        if suffix == ".pdf":
            document = fitz.open(stream=data, filetype="pdf")
            try:
                if document.is_encrypted or document.page_count == 0:
                    raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "PDF is empty or password protected")
                if document.page_count > settings.report_max_pdf_pages:
                    raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"PDF exceeds the {settings.report_max_pdf_pages}-page limit")
            finally:
                document.close()
        else:
            with Image.open(io.BytesIO(data)) as image:
                if image.width * image.height > 40_000_000:
                    raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image dimensions exceed the processing limit")
                image.verify()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "The uploaded report is damaged or unreadable") from exc


async def _load_owned_report(report_id: uuid.UUID, principal: Principal, session: AsyncSession) -> UploadedReport:
    user = await get_or_create_user(session, principal)
    report = await session.scalar(select(UploadedReport).where(UploadedReport.id == report_id, UploadedReport.user_id == user.id))
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    # Keep the extra session ownership check as defense in depth for legacy or malformed rows.
    await owned_chat(session, report.session_id, user.id)
    return report


@router.post("/upload", response_model=ReportSummary, status_code=status.HTTP_202_ACCEPTED)
async def upload(
    session_id: uuid.UUID,
    file: UploadFile = File(...),
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> ReportSummary:
    upload_started = time.perf_counter()
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, session_id, user.id)
    suffix = Path(file.filename or "").suffix.lower()
    file_type = ALLOWED_TYPES.get(suffix)
    if file_type is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a PDF, PNG, JPG, JPEG, or WEBP file")
    max_size = settings.report_max_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > max_size:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds the {settings.report_max_size_mb} MB limit")
        chunks.append(chunk)
    data = b"".join(chunks)
    await file.close()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The selected file is empty")
    await asyncio.to_thread(_verify_file, data, suffix)
    report_id = uuid.uuid4()
    resource_type = "raw" if file_type == "application/pdf" else "image"
    public_id = f"medassist/{user.id}/{chat.id}/{report_id}"
    cloudinary_started = time.perf_counter()
    try:
        asset = await upload_report(data, public_id, resource_type)
    except Exception as exc:
        logger.exception("REPORT FAILED report_id=%s stage=cloudinary_upload", report_id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Report storage is temporarily unavailable") from exc
    logger.info("REPORT CLOUDINARY UPLOADED report_id=%s", report_id)
    logger.info("report_timing report_id=%s stage=cloudinary_upload bytes=%d seconds=%.3f", report_id, size, time.perf_counter() - cloudinary_started)
    original_name = Path(file.filename or f"report{suffix}").name
    original_name = "".join(ch for ch in original_name if ch.isprintable() and ch not in "/\\").strip()[:255] or f"report{suffix}"
    report = UploadedReport(
        id=report_id,
        user_id=user.id,
        session_id=chat.id,
        file_name=original_name,
        file_type=file_type,
        file_size=size,
        file_url=str(asset.get("secure_url", "")),
        cloudinary_public_id=str(asset["public_id"]),
        cloudinary_resource_type=str(asset["resource_type"]),
        processing_status="pending",
        processing_stage="queued",
    )
    try:
        session.add(report)
        await session.commit()
        await session.refresh(report)
    except Exception:
        logger.exception("REPORT FAILED report_id=%s stage=database_commit", report_id)
        await session.rollback()
        try:
            await delete_report_asset(public_id, resource_type)
        except Exception:
            logger.exception("Could not clean up orphaned Cloudinary asset after database failure")
        raise
    logger.info("REPORT CREATED report_id=%s", report.id)
    logger.info("REPORT QUEUED report_id=%s status=%s stage=%s commit_completed=true", report.id, report.processing_status, report.processing_stage)
    logger.info("report_timing report_id=%s stage=upload_total bytes=%d seconds=%.3f", report_id, size, time.perf_counter() - upload_started)
    return ReportSummary.model_validate(report)


@router.post("/{report_id}/retry", response_model=ReportSummary, status_code=status.HTTP_202_ACCEPTED)
async def retry_report(
    report_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> ReportSummary:
    report = await _load_owned_report(report_id, principal, session)
    if report.processing_status != "failed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only failed reports can be retried")
    report.processing_status = "pending"
    report.processing_stage = "queued"
    report.processing_started_at = None
    report.processing_attempts = 0
    report.indexed_at = None
    report.processing_error = None
    report.chunks_created = 0
    report.embeddings_created = 0
    report.vectors_saved = 0
    await session.commit()
    await session.refresh(report)
    return ReportSummary.model_validate(report)


@router.get("", response_model=list[ReportSummary])
async def list_reports(
    session_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> list[ReportSummary]:
    user = await get_or_create_user(session, principal)
    query = select(UploadedReport).where(UploadedReport.user_id == user.id)
    if session_id:
        await owned_chat(session, session_id, user.id)
        query = query.where(UploadedReport.session_id == session_id)
    result = await session.scalars(query.order_by(UploadedReport.upload_date.desc()).limit(limit).offset(offset))
    await session.commit()
    return [ReportSummary.model_validate(item) for item in result.all()]


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> ReportRead:
    report = await _load_owned_report(report_id, principal, session)
    await session.commit()
    return ReportRead.model_validate(report)


@router.get("/{report_id}/debug", response_model=ReportProcessingDebug)
async def debug_report(
    report_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> ReportProcessingDebug:
    report = await _load_owned_report(report_id, principal, session)
    result = ReportProcessingDebug(
        report_id=report.id,
        status=report.processing_status,
        stage=report.processing_stage,
        error=report.processing_error,
        created_at=report.created_at,
        updated_at=report.updated_at,
        cloudinary_uploaded=bool(report.cloudinary_public_id and report.file_url),
        text_extracted=bool(report.raw_extracted_text),
        chunks_created=report.chunks_created,
        embeddings_created=report.embeddings_created,
        vectors_saved=report.vectors_saved,
    )
    await session.commit()
    return result


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> Response:
    report = await _load_owned_report(report_id, principal, session)
    previous_status, previous_indexed_at = report.processing_status, report.indexed_at
    report.processing_status = "deleting"
    await session.commit()
    try:
        await delete_report_vectors(report.id)
    except Exception as exc:
        logger.exception("ChromaDB report deletion failed for %s", report_id)
        report.processing_status = previous_status
        report.indexed_at = previous_indexed_at
        await session.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Report index is temporarily unavailable") from exc
    try:
        await delete_report_asset(report.cloudinary_public_id, report.cloudinary_resource_type)
    except Exception as exc:
        logger.exception("Cloudinary report deletion failed for %s", report_id)
        report.indexed_at = None
        report.processing_status = "pending" if report.raw_extracted_text else previous_status
        await session.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Report storage is temporarily unavailable") from exc
    await session.delete(report)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{report_id}/summary", response_model=ReportSummaryResponse)
async def get_report_summary(
    report_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> ReportSummaryResponse:
    report = await _load_owned_report(report_id, principal, session)
    if not report.summary_data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No summary has been generated for this report")
    response = ReportSummaryResponse(
        report_id=report.id,
        report_name=report.file_name,
        generated_at=report.summary_generated_at,
        summary=MedicalReportSummary.model_validate(report.summary_data),
    )
    await session.commit()
    return response


@router.get("/{report_id}/preview")
async def preview_report(
    report_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    report = await _load_owned_report(report_id, principal, session)
    file_name, file_type = report.file_name, report.file_type
    try:
        url = await create_private_download_url(report.cloudinary_public_id, report.cloudinary_resource_type, file_type)
    except Exception as exc:
        logger.exception("Could not create private report download URL")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Report storage is temporarily unavailable") from exc
    await session.commit()
    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0), follow_redirects=True)
    try:
        upstream = await client.send(client.build_request("GET", url), stream=True)
        if upstream.status_code != 200:
            await upstream.aclose()
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Report preview is temporarily unavailable")
    except HTTPException:
        await client.aclose()
        raise
    except httpx.HTTPError as exc:
        await client.aclose()
        logger.exception("Cloudinary report preview fetch failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Report preview is temporarily unavailable") from exc

    async def stream():
        try:
            async for chunk in upstream.aiter_bytes(64 * 1024):
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    disposition = "inline" if file_type == "application/pdf" or file_type.startswith("image/") else "attachment"
    safe_name = quote(file_name, safe="")
    return StreamingResponse(stream(), media_type=file_type, headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{safe_name}", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox; default-src 'none'", "Cache-Control": "private, no-store"})
