"""Admin-controlled source registry and medical reference review APIs."""
from __future__ import annotations

import io
import logging
import uuid
import zipfile
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal, require_knowledge_admin
from app.core.config import settings
from app.db.session import get_session
from app.models.medical_knowledge import (
    KnowledgeIngestionJob,
    MedicalKnowledgeDocument,
    MedicalKnowledgeDocumentVersion,
    MedicalKnowledgeReview,
    MedicalSource,
)
from app.schemas.medical_knowledge import (
    KnowledgeIngestionJobRead,
    MedicalKnowledgeDocumentRead,
    MedicalKnowledgeVersionDetailRead,
    MedicalKnowledgeVersionRead,
    MedicalSourceCreate,
    MedicalSourceRead,
    ReviewRequest,
)
from app.services.medical_knowledge_documents import sha256
from app.services.medical_taxonomy import load_taxonomy
from app.services.report_storage import create_private_download_url, delete_report_asset, upload_report

logger = logging.getLogger(__name__)
router = APIRouter()

_MIME = {
    ".pdf": ("application/pdf", "pdf"),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    ".txt": ("text/plain", "txt"),
    ".md": ("text/markdown", "md"),
    ".json": ("application/json", "json"),
    ".csv": ("text/csv", "csv"),
}


def _check_file(name: str, content_type: str | None, data: bytes) -> tuple[str, str]:
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    expected = _MIME.get(ext)
    if not expected:
        raise HTTPException(415, "Supported formats: PDF, DOCX, TXT, Markdown, JSON, and CSV")
    mime, _extension = expected
    if content_type and content_type not in {mime, "application/octet-stream"}:
        raise HTTPException(415, "File extension and content type do not match")
    if ext == ".pdf" and not data.startswith(b"%PDF-"):
        raise HTTPException(400, "The uploaded file is not a valid PDF")
    if ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members = {item.filename: item for item in archive.infolist()}
                if "word/document.xml" not in members:
                    raise ValueError("Missing Word document")
                document_xml = members["word/document.xml"]
                if document_xml.file_size > 50 * 1024 * 1024 or document_xml.file_size > max(document_xml.compress_size, 1) * 100:
                    raise ValueError("Expanded Word document exceeds safe processing limits")
        except (zipfile.BadZipFile, ValueError) as exc:
            raise HTTPException(400, "The uploaded file is not a valid DOCX document") from exc
    if ext in {".txt", ".md"}:
        try:
            data.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise HTTPException(400, "TXT and Markdown files must use UTF-8 encoding") from exc
    if ext == ".json":
        try:
            import json
            json.loads(data.decode("utf-8-sig", errors="strict"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise HTTPException(400, "The uploaded JSON file is not valid UTF-8 JSON") from exc
    if ext == ".csv":
        try:
            data.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise HTTPException(400, "CSV files must use UTF-8 encoding") from exc
    return mime, "raw"


@router.post("/sources", response_model=MedicalSourceRead, status_code=status.HTTP_201_CREATED)
async def register_source(
    payload: MedicalSourceCreate,
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    supported_specialties = {
        item.casefold()
        for sector in load_taxonomy()
        for item in sector.get("specialties", [])
    }
    requested_specialties = list(dict.fromkeys(
        item.strip() for item in [*payload.specialties, *([payload.specialty] if payload.specialty else [])]
        if item.strip()
    ))
    unsupported = [item for item in requested_specialties if item.casefold() not in supported_specialties]
    if unsupported:
        raise HTTPException(422, f"Specialties must match the project's medical taxonomy: {', '.join(unsupported)}")
    values = payload.model_dump(mode="json")
    values["specialties"] = requested_specialties
    values["specialty"] = requested_specialties[0] if requested_specialties else None
    source = MedicalSource(
        **values,
        created_by_clerk_id=principal.clerk_id,
        review_status="pending_review",
    )
    session.add(source)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(409, "A source with this source_key already exists") from exc
    await session.refresh(source)
    logger.info("MEDICAL SOURCE REGISTERED source_id=%s status=pending_review by=%s", source.id, principal.clerk_id)
    return source


@router.get("/sources", response_model=list[MedicalSourceRead])
async def list_sources(
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.scalars(select(MedicalSource).order_by(MedicalSource.created_at.desc()))
    return result.all()


@router.post("/sources/{source_id}/review", response_model=MedicalSourceRead)
async def review_source(
    source_id: uuid.UUID,
    payload: ReviewRequest,
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    source = await session.get(MedicalSource, source_id, with_for_update=True)
    if not source:
        raise HTTPException(404, "Source not found")
    if payload.action not in {"approve", "reject", "retire"}:
        raise HTTPException(422, "Unsupported review action")
    if payload.action == "approve" and any(
        term in source.license_permission.casefold()
        for term in ("unknown", "unverified", "not assessed", "pending", "unspecified")
    ):
        raise HTTPException(409, "Document the source's license or permission basis before approval")
    source.review_status = {"approve": "approved", "reject": "rejected", "retire": "retired"}[payload.action]
    source.reviewer_clerk_id = principal.clerk_id
    source.review_date = datetime.now(UTC)
    if payload.action in {"reject", "retire"}:
        versions = await session.scalars(
            select(MedicalKnowledgeDocumentVersion)
            .join(MedicalKnowledgeDocument, MedicalKnowledgeDocument.id == MedicalKnowledgeDocumentVersion.document_id)
            .where(MedicalKnowledgeDocument.source_id == source.id)
            .with_for_update()
        )
        for version in versions.all():
            version.is_active = False
            if version.approval_status == "approved":
                version.approval_status = "retired"
    session.add(MedicalKnowledgeReview(
        source_id=source.id,
        target_type="source",
        action={"approve": "approved", "reject": "rejected", "retire": "retired"}[payload.action],
        reviewer_clerk_id=principal.clerk_id,
        notes=payload.notes,
    ))
    await session.commit()
    await session.refresh(source)
    logger.info("MEDICAL SOURCE REVIEWED source_id=%s status=%s reviewer=%s", source.id, source.review_status, principal.clerk_id)
    return source


@router.post("/documents", response_model=MedicalKnowledgeVersionRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    source_id: uuid.UUID = Form(...),
    title: str = Form(..., min_length=3, max_length=500),
    version_label: str = Form(default="1", min_length=1, max_length=120),
    document_id: uuid.UUID | None = Form(default=None),
    file: UploadFile = File(...),
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    source = await session.get(MedicalSource, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    if source.review_status in {"rejected", "retired"}:
        raise HTTPException(409, "Rejected or retired sources cannot receive new documents")
    data = await file.read(settings.knowledge_max_document_size_mb * 1024 * 1024 + 1)
    if not data:
        raise HTTPException(400, "The uploaded file is empty")
    if len(data) > settings.knowledge_max_document_size_mb * 1024 * 1024:
        raise HTTPException(413, "The uploaded document exceeds the configured size limit")
    mime, resource_type = _check_file(file.filename or "reference", file.content_type, data)
    digest = sha256(data)
    if document_id:
        document = await session.get(MedicalKnowledgeDocument, document_id)
        if not document or document.source_id != source.id:
            raise HTTPException(404, "Document not found for this source")
        duplicate = await session.scalar(select(MedicalKnowledgeDocumentVersion.id).where(
            MedicalKnowledgeDocumentVersion.document_id == document.id,
            MedicalKnowledgeDocumentVersion.content_sha256 == digest,
        ))
        if duplicate:
            raise HTTPException(409, "This exact file version is already registered")
    else:
        duplicate = await session.scalar(select(MedicalKnowledgeDocumentVersion.id).join(
            MedicalKnowledgeDocument, MedicalKnowledgeDocument.id == MedicalKnowledgeDocumentVersion.document_id,
        ).where(MedicalKnowledgeDocument.source_id == source.id, MedicalKnowledgeDocumentVersion.content_sha256 == digest))
        if duplicate:
            raise HTTPException(409, "This exact file is already registered for the source")
        document = MedicalKnowledgeDocument(source_id=source.id, title=title.strip(), created_by_clerk_id=principal.clerk_id)
        session.add(document)
        await session.flush()
    public_id = f"medassist/verified-knowledge/{source.id}/{document.id}/{uuid.uuid4()}"
    uploaded = False
    try:
        await upload_report(data, public_id, resource_type)
        uploaded = True
        version = MedicalKnowledgeDocumentVersion(
            document_id=document.id,
            version_label=version_label.strip(),
            content_sha256=digest,
            original_file_name=(file.filename or f"reference.{resource_type}")[:255],
            mime_type=mime,
            file_size=len(data),
            cloudinary_public_id=public_id,
            cloudinary_resource_type=resource_type,
            processing_status="queued",
            approval_status="pending_review",
            is_active=False,
            created_by_clerk_id=principal.clerk_id,
        )
        session.add(version)
        await session.flush()
        job = KnowledgeIngestionJob(version_id=version.id, operation="extract", status="queued")
        session.add(job)
        await session.flush()
        version.job_id = job.id
        await session.commit()
        await session.refresh(version)
        logger.info("MEDICAL DOCUMENT UPLOADED source_id=%s document_id=%s version_id=%s status=pending_review", source.id, document.id, version.id)
        return version
    except IntegrityError as exc:
        await session.rollback()
        if uploaded:
            await delete_report_asset(public_id, resource_type)
        raise HTTPException(409, "A document with this version label already exists") from exc
    except Exception:
        await session.rollback()
        if uploaded:
            try:
                await delete_report_asset(public_id, resource_type)
            except Exception:
                logger.exception("Failed to clean up Cloudinary object after document registration failure public_id=%s", public_id)
        raise


@router.get("/documents/{document_id}", response_model=list[MedicalKnowledgeVersionRead])
async def list_document_versions(
    document_id: uuid.UUID,
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    document = await session.get(MedicalKnowledgeDocument, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    versions = await session.scalars(select(MedicalKnowledgeDocumentVersion).where(
        MedicalKnowledgeDocumentVersion.document_id == document.id,
    ).order_by(MedicalKnowledgeDocumentVersion.created_at.desc()))
    return versions.all()


@router.get("/documents", response_model=list[MedicalKnowledgeDocumentRead])
async def list_documents(
    source_id: uuid.UUID | None = None,
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    query = select(MedicalKnowledgeDocument).order_by(MedicalKnowledgeDocument.created_at.desc())
    if source_id:
        query = query.where(MedicalKnowledgeDocument.source_id == source_id)
    return (await session.scalars(query)).all()


@router.get("/versions/{version_id}", response_model=MedicalKnowledgeVersionDetailRead)
async def get_version_details(
    version_id: uuid.UUID,
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        select(MedicalKnowledgeDocumentVersion, MedicalKnowledgeDocument, MedicalSource)
        .join(MedicalKnowledgeDocument, MedicalKnowledgeDocument.id == MedicalKnowledgeDocumentVersion.document_id)
        .join(MedicalSource, MedicalSource.id == MedicalKnowledgeDocument.source_id)
        .where(MedicalKnowledgeDocumentVersion.id == version_id)
    )
    result = row.one_or_none()
    if result is None:
        raise HTTPException(404, "Document version not found")
    version, _document, source = result
    return MedicalKnowledgeVersionDetailRead(
        **MedicalKnowledgeVersionRead.model_validate(version).model_dump(),
        extracted_text=version.extracted_text[:100_000] if version.extracted_text else None,
        source_status=source.review_status,
        source_title=source.title,
        source_url=source.source_url,
        medical_category=source.medical_category,
        organization=source.organization,
        relevant_topic=source.relevant_topic,
        specialty=source.specialty,
        specialties=source.specialties or [],
        jurisdiction=source.jurisdiction,
        language=source.language,
        license_permission=source.license_permission,
    )


@router.get("/versions/{version_id}/original")
async def get_version_original(
    version_id: uuid.UUID,
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    version = await session.get(MedicalKnowledgeDocumentVersion, version_id)
    if not version:
        raise HTTPException(404, "Document version not found")
    try:
        url = await create_private_download_url(
            version.cloudinary_public_id,
            version.cloudinary_resource_type,
            version.mime_type,
        )
    except RuntimeError as exc:
        raise HTTPException(503, "Private document storage is not configured") from exc
    return RedirectResponse(url=url, status_code=307)


@router.post("/versions/{version_id}/review", response_model=MedicalKnowledgeVersionRead)
async def review_version(
    version_id: uuid.UUID,
    payload: ReviewRequest,
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    version = await session.get(MedicalKnowledgeDocumentVersion, version_id, with_for_update=True)
    if not version:
        raise HTTPException(404, "Document version not found")
    document = await session.get(MedicalKnowledgeDocument, version.document_id)
    source = await session.get(MedicalSource, document.source_id) if document else None
    if not source:
        raise HTTPException(404, "Source not found")
    if payload.action == "approve":
        if version.approval_status == "approved":
            raise HTTPException(409, "This version is already approved; use the reindex operation if needed")
        if source.review_status != "approved":
            raise HTTPException(409, "Approve the source registry entry before approving its documents")
        if version.processing_status not in {"ready_for_review", "indexed", "failed"} or not version.extracted_text:
            raise HTTPException(409, "Document extraction must complete before review")
        version.approval_status = "approved"
        version.is_active = False
        version.processing_status = "index_queued"
        session.add(KnowledgeIngestionJob(version_id=version.id, operation="index", status="queued"))
    elif payload.action == "reject":
        version.approval_status = "rejected"
        version.is_active = False
    elif payload.action == "retire":
        version.approval_status = "retired"
        version.is_active = False
    else:
        raise HTTPException(422, "Unsupported review action")
    version.reviewed_by_clerk_id = principal.clerk_id
    version.reviewed_at = datetime.now(UTC)
    session.add(MedicalKnowledgeReview(
        version_id=version.id,
        target_type="document_version",
        action={"approve": "approved", "reject": "rejected", "retire": "retired"}[payload.action],
        reviewer_clerk_id=principal.clerk_id,
        notes=payload.notes,
    ))
    await session.commit()
    await session.refresh(version)
    return version


@router.get("/jobs/{job_id}", response_model=KnowledgeIngestionJobRead)
async def get_job(
    job_id: uuid.UUID,
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    job = await session.get(KnowledgeIngestionJob, job_id)
    if not job:
        raise HTTPException(404, "Ingestion job not found")
    return job


@router.post("/versions/{version_id}/reindex", response_model=KnowledgeIngestionJobRead, status_code=202)
async def reindex_version(
    version_id: uuid.UUID,
    principal: Principal = Depends(require_knowledge_admin),
    session: AsyncSession = Depends(get_session),
):
    version = await session.get(MedicalKnowledgeDocumentVersion, version_id)
    if not version:
        raise HTTPException(404, "Document version not found")
    document = await session.get(MedicalKnowledgeDocument, version.document_id)
    source = await session.get(MedicalSource, document.source_id) if document else None
    if not source or source.review_status != "approved" or version.approval_status != "approved":
        raise HTTPException(409, "Only a document with an approved source and document review can be re-indexed")
    if not version.extracted_text:
        raise HTTPException(409, "Document extraction is not available for this version")
    job = KnowledgeIngestionJob(version_id=version.id, operation="index", status="queued")
    if not version.is_active:
        version.processing_status = "index_queued"
    version.processing_error = None
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job

