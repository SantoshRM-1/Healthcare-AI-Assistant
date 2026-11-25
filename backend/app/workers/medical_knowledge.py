"""Durable PostgreSQL-backed extraction/index worker for curated references."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid

import httpx
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import SessionFactory
from app.models.medical_knowledge import KnowledgeIngestionJob, MedicalKnowledgeDocument, MedicalKnowledgeDocumentVersion
from app.services.medical_knowledge_documents import chunk_document, extract_document
from app.services.medical_knowledge_store import index_version
from app.services.report_storage import create_private_download_url

logger = logging.getLogger(__name__)

CLAIM_JOB = text("""
WITH candidate AS (
  SELECT id FROM knowledge_ingestion_jobs
  WHERE attempts < :max_attempts AND (
    status = 'queued' OR (status = 'processing' AND started_at < now() - interval '30 minutes')
  )
  ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1
)
UPDATE knowledge_ingestion_jobs j
SET status='processing', attempts=j.attempts+1, started_at=now(), finished_at=NULL, error=NULL
FROM candidate WHERE j.id=candidate.id
RETURNING j.id
""")


async def claim_job() -> uuid.UUID | None:
    async with SessionFactory() as session:
        expired = await session.execute(text("""
          UPDATE knowledge_ingestion_jobs SET status='failed', finished_at=now(),
            error=COALESCE(error, 'Worker lease expired after retry limit')
          WHERE attempts >= :max_attempts AND
            (status='queued' OR (status='processing' AND started_at < now() - interval '30 minutes'))
          RETURNING version_id
        """), {"max_attempts": settings.knowledge_ingestion_max_attempts})
        for (version_id,) in expired.all():
            await session.execute(text("""
              UPDATE medical_knowledge_document_versions
              SET processing_status=CASE WHEN is_active AND approval_status='approved' THEN 'indexed' ELSE 'failed' END,
                  processing_error='Worker lease expired after retry limit', updated_at=now()
              WHERE id=:version_id
            """), {"version_id": version_id})
        result = await session.execute(CLAIM_JOB, {"max_attempts": settings.knowledge_ingestion_max_attempts})
        job_id = result.scalar_one_or_none()
        await session.commit()
        return job_id


async def process_job(job_id: uuid.UUID) -> None:
    async with SessionFactory() as session:
        job = await session.get(KnowledgeIngestionJob, job_id)
        if not job or job.status != "processing":
            return
        version = await session.get(MedicalKnowledgeDocumentVersion, job.version_id, with_for_update=True)
        if not version:
            job.status, job.error = "failed", "Document version no longer exists"
            await session.commit()
            return
        # A second worker can claim an expired lease while the original job holds
        # the version lock. Refresh after acquiring it so completed work is not repeated.
        await session.refresh(job)
        if job.status != "processing":
            return
        try:
            if job.operation == "extract":
                version.processing_status = "processing"
                version.processing_error = None
                await session.commit()
            if job.operation == "extract":
                url = await create_private_download_url(
                    version.cloudinary_public_id,
                    version.cloudinary_resource_type,
                    version.mime_type,
                )
                async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.content
                text_content = await extract_document(data, version.mime_type, version.original_file_name, str(version.id))
                if not text_content.strip():
                    raise ValueError("No readable text was extracted; check the document quality and OCR output")
                if len(text_content) > 5_000_000:
                    raise ValueError("Extracted text exceeds the 5 MB review limit; split the reference into smaller files")
                version.extracted_text = text_content
                version.processing_status = "ready_for_review"
                job.status = "completed"
                logger.info("MEDICAL KNOWLEDGE EXTRACTION COMPLETED version_id=%s chars=%d", version.id, len(text_content))
            elif job.operation == "index":
                if version.approval_status != "approved":
                    raise ValueError("Index job refused: document version is not approved")
                if not version.extracted_text:
                    raise ValueError("Index job refused: extracted text is missing")
                await session.scalar(
                    select(MedicalKnowledgeDocument.id)
                    .where(MedicalKnowledgeDocument.id == version.document_id)
                    .with_for_update()
                )
                chunks = chunk_document(version.extracted_text)
                version.processing_status = "index_queued"
                await session.flush()
                count = await index_version(session, version.id, chunks)
                previous_versions = await session.scalars(select(MedicalKnowledgeDocumentVersion).where(
                    MedicalKnowledgeDocumentVersion.document_id == version.document_id,
                    MedicalKnowledgeDocumentVersion.id != version.id,
                    MedicalKnowledgeDocumentVersion.is_active.is_(True),
                ).with_for_update())
                for previous in previous_versions.all():
                    previous.is_active = False
                    previous.approval_status = "retired"
                await session.flush()
                version.is_active = True
                version.processing_status = "indexed"
                job.status = "completed"
                logger.info("MEDICAL KNOWLEDGE INDEX COMPLETED version_id=%s chunks=%d", version.id, count)
            else:
                raise ValueError("Unsupported knowledge ingestion operation")
            job.finished_at = None  # filled by database clock below
            await session.execute(text("UPDATE knowledge_ingestion_jobs SET finished_at=now() WHERE id=:id"), {"id": job.id})
            await session.commit()
        except Exception as exc:
            logger.exception("MEDICAL KNOWLEDGE JOB FAILED job_id=%s operation=%s", job.id, job.operation)
            await session.rollback()
            job = await session.get(KnowledgeIngestionJob, job_id)
            version = await session.get(MedicalKnowledgeDocumentVersion, job.version_id) if job else None
            if job:
                job.status = "failed" if job.attempts >= settings.knowledge_ingestion_max_attempts else "queued"
                job.error = f"{type(exc).__name__}: {exc}"[:4000]
                await session.execute(text("UPDATE knowledge_ingestion_jobs SET finished_at=now() WHERE id=:id"), {"id": job.id})
            if version and job and job.operation == "extract":
                version.processing_status = "failed" if job.status == "failed" else "queued"
                version.processing_error = f"{type(exc).__name__}: {exc}"[:4000]
            if version and job and job.operation == "index":
                version.processing_status = (
                    "indexed" if version.is_active and version.approval_status == "approved"
                    else "failed" if job.status == "failed"
                    else "index_queued"
                )
                version.processing_error = f"{type(exc).__name__}: {exc}"[:4000]
            if job:
                await session.commit()


async def run() -> None:
    logger.info("MEDICAL KNOWLEDGE WORKER STARTED pid=%d", os.getpid())
    try:
        while True:
            try:
                job_id = await claim_job()
                if job_id is None:
                    await asyncio.sleep(2)
                    continue
                await process_job(job_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Medical knowledge worker iteration failed")
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        raise
