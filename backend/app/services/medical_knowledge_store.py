"""Dedicated Chroma collection for curated medical references, never patient reports."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.knowledge.policy import document_is_indexable, document_is_retrievable
from app.models.medical_knowledge import (
    MedicalKnowledgeChunk,
    MedicalKnowledgeDocument,
    MedicalKnowledgeDocumentVersion,
    MedicalSource,
)
from app.services.medical_knowledge_documents import KnowledgeChunk
from app.services.medical_query import rerank_retrieval_results
from app.services.vector_store import chroma_client, generate_embeddings

COLLECTION_NAME = "medassist_verified_medical_knowledge_v1"
logger = logging.getLogger(__name__)


def collection():
    return chroma_client().get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


async def index_version(session: AsyncSession, version_id: uuid.UUID, chunks: list[KnowledgeChunk]) -> int:
    result = await session.execute(
        select(MedicalKnowledgeDocumentVersion, MedicalKnowledgeDocument, MedicalSource)
        .join(MedicalKnowledgeDocument, MedicalKnowledgeDocument.id == MedicalKnowledgeDocumentVersion.document_id)
        .join(MedicalSource, MedicalSource.id == MedicalKnowledgeDocument.source_id)
        .where(
            MedicalKnowledgeDocumentVersion.id == version_id,
            MedicalKnowledgeDocumentVersion.approval_status == "approved",
            MedicalSource.review_status == "approved",
        )
    )
    row = result.one_or_none()
    if row is None:
        raise ValueError("Only an approved source and document version can be indexed")
    version, document, source = row
    if not document_is_indexable(source.review_status, version.approval_status):
        raise ValueError("Only an approved source and document version can be indexed")
    target = collection()
    old = await session.scalars(select(MedicalKnowledgeChunk).where(MedicalKnowledgeChunk.version_id == version.id))
    for item in old.all():
        await session.delete(item)
    if not chunks:
        raise ValueError("No text chunks were extracted from this document")
    embeddings = await generate_embeddings([chunk.content for chunk in chunks], "RETRIEVAL_DOCUMENT", title=document.title)
    vector_ids = [f"mk:{version.id}:{chunk.index}" for chunk in chunks]
    common_metadata = {
        "source_id": str(source.id),
        "document_id": str(document.id),
        "version_id": str(version.id),
        "source_title": source.title,
        "organization": source.organization,
        "source_url": source.source_url,
        "source_type": source.source_type,
        "medical_category": source.medical_category,
        "specialty": source.specialty or "",
        "specialties": " | ".join(source.specialties or []),
        "relevant_topic": source.relevant_topic,
        "jurisdiction": source.jurisdiction or "",
        "language": source.language,
        "publication_date": source.publication_date or "",
        "last_updated_date": source.last_updated_date or "",
        "document_version": version.version_label,
    }
    metadatas = [
        {**common_metadata, "section": chunk.section, "page": chunk.page or 0, "chunk_index": chunk.index}
        for chunk in chunks
    ]
    await asyncio.to_thread(
        target.upsert,
        ids=vector_ids,
        embeddings=embeddings,
        documents=[chunk.content for chunk in chunks],
        metadatas=metadatas,
    )
    for vector_id, chunk in zip(vector_ids, chunks, strict=True):
        session.add(
            MedicalKnowledgeChunk(
                source_id=source.id,
                document_id=document.id,
                version_id=version.id,
                chunk_index=chunk.index,
                vector_id=vector_id,
                section=chunk.section,
                page=chunk.page,
                language=source.language,
                jurisdiction=source.jurisdiction,
                content_sha256=hashlib.sha256(chunk.content.encode()).hexdigest(),
                content=chunk.content,
            )
        )
    await session.flush()
    logger.info("MEDICAL KNOWLEDGE VECTOR STORE COMPLETED version_id=%s vectors=%d", version.id, len(chunks))
    return len(chunks)


async def remove_version_vectors(version_id: uuid.UUID) -> None:
    await asyncio.to_thread(collection().delete, where={"version_id": str(version_id)})


async def search_approved(
    session: AsyncSession,
    query: str,
    *,
    limit: int = 5,
    language: str | None = None,
    jurisdiction: str | None = None,
    specialty: str | None = None,
) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    ready_version = await session.scalar(
        select(MedicalKnowledgeDocumentVersion.id)
        .join(MedicalKnowledgeDocument, MedicalKnowledgeDocument.id == MedicalKnowledgeDocumentVersion.document_id)
        .join(MedicalSource, MedicalSource.id == MedicalKnowledgeDocument.source_id)
        .where(
            MedicalKnowledgeDocumentVersion.approval_status == "approved",
            MedicalKnowledgeDocumentVersion.is_active.is_(True),
            MedicalKnowledgeDocumentVersion.processing_status == "indexed",
            MedicalSource.review_status == "approved",
        )
        .limit(1)
    )
    if ready_version is None:
        return []
    query_vector = (await generate_embeddings([query], "QUESTION_ANSWERING"))[0]
    filters: list[dict[str, Any]] = []
    if language:
        filters.append({"language": language})
    if jurisdiction:
        filters.append({"$or": [{"jurisdiction": jurisdiction}, {"jurisdiction": ""}, {"jurisdiction": "Global"}]})
    if specialty:
        filters.append({"specialty": specialty})
    where = {"$and": filters} if len(filters) > 1 else filters[0] if filters else None
    result = await asyncio.to_thread(
        collection().query,
        query_embeddings=[query_vector],
        n_results=max(1, min(limit * 3, 30)),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    ids = (result.get("ids") or [[]])[0]
    docs = (result.get("documents") or [[]])[0]
    metadata = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    # Chroma metadata is a retrieval aid only. Revalidate every returned ID against
    # current PostgreSQL approval/active-version state to fail closed after revocation.
    candidate_ids: set[uuid.UUID] = set()
    for meta in metadata:
        if not meta or not meta.get("version_id"):
            continue
        try:
            candidate_ids.add(uuid.UUID(str(meta["version_id"])))
        except (ValueError, TypeError, AttributeError):
            continue
    if not candidate_ids:
        return []
    valid_result = await session.execute(
        select(
            MedicalKnowledgeDocumentVersion.id,
            MedicalKnowledgeDocumentVersion.approval_status,
            MedicalKnowledgeDocumentVersion.is_active,
            MedicalKnowledgeDocumentVersion.processing_status,
            MedicalSource.review_status,
            MedicalKnowledgeDocument.id,
            MedicalSource.id,
            MedicalSource.title,
            MedicalSource.organization,
            MedicalSource.source_url,
            MedicalSource.source_type,
            MedicalSource.medical_category,
            MedicalSource.relevant_topic,
            MedicalSource.specialty,
            MedicalSource.specialties,
            MedicalSource.jurisdiction,
            MedicalSource.language,
            MedicalSource.publication_date,
            MedicalSource.last_updated_date,
            MedicalSource.review_date,
            MedicalKnowledgeDocumentVersion.version_label,
            MedicalKnowledgeChunk.vector_id,
            MedicalKnowledgeChunk.content,
            MedicalKnowledgeChunk.section,
            MedicalKnowledgeChunk.page,
            MedicalKnowledgeChunk.content_sha256,
        )
        .join(MedicalKnowledgeDocument, MedicalKnowledgeDocument.id == MedicalKnowledgeDocumentVersion.document_id)
        .join(MedicalSource, MedicalSource.id == MedicalKnowledgeDocument.source_id)
        .join(MedicalKnowledgeChunk, MedicalKnowledgeChunk.version_id == MedicalKnowledgeDocumentVersion.id)
        .where(
            MedicalKnowledgeDocumentVersion.id.in_(candidate_ids),
            MedicalKnowledgeChunk.vector_id.in_(ids),
            MedicalKnowledgeDocumentVersion.approval_status == "approved",
            MedicalKnowledgeDocumentVersion.is_active.is_(True),
            MedicalKnowledgeDocumentVersion.processing_status == "indexed",
            MedicalSource.review_status == "approved",
        )
    )
    valid_chunks: dict[str, tuple[str, dict[str, Any]]] = {}
    for row in valid_result.all():
        (version_id, approval_status, is_active, processing_status, source_status,
         document_id, source_id, title, organization, source_url, source_type, medical_category,
         relevant_topic, specialty_value, specialties_value, jurisdiction_value, language_value, publication_date,
         updated_date, review_date, version_label, vector_id, content, section, page, content_hash) = row
        if not document_is_retrievable(source_status, approval_status, is_active, processing_status):
            continue
        if hashlib.sha256(content.encode()).hexdigest() != content_hash:
            continue
        valid_chunks[str(vector_id)] = (
            content,
            {
                "source_id": str(source_id),
                "document_id": str(document_id),
                "version_id": str(version_id),
                "source_title": title,
                "organization": organization,
                "source_url": source_url,
                "source_type": source_type,
                "medical_category": medical_category,
                "relevant_topic": relevant_topic,
                "specialty": specialty_value or "",
                "specialties": " | ".join(specialties_value or []),
                "jurisdiction": jurisdiction_value or "",
                "language": language_value,
                "publication_date": publication_date or "",
                "last_updated_date": updated_date or "",
                "source_review_date": review_date.isoformat() if review_date else "",
                "document_version": version_label,
                "section": section,
                "page": page or 0,
            },
        )
    output: list[dict[str, Any]] = []
    for vector_id, content, meta, distance in zip(ids, docs, metadata, distances, strict=True):
        validated = valid_chunks.get(str(vector_id))
        if not meta or not validated or validated[0] != content:
            continue
        if distance is None or float(distance) > settings.rag_max_cosine_distance:
            continue
        output.append({"id": vector_id, "text": content, "metadata": validated[1], "distance": float(distance)})
        if len(output) >= limit:
            break
    return rerank_retrieval_results(
        output,
        query,
        limit=limit,
        max_distance=settings.rag_max_cosine_distance,
    )
