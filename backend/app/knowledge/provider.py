"""Provider boundary for a separately sourced, provenance-aware medical corpus.

No clinical knowledge is bundled here. Implementations must return licensed,
reviewed material with a source URL and version before the application uses it.
"""

from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings
from app.db.session import SessionFactory
from app.services.medical_knowledge_store import search_approved


@dataclass(frozen=True, slots=True)
class MedicalKnowledgeSource:
    source_id: str
    title: str
    organization: str | None
    excerpt: str
    source_url: str
    published_or_updated: str | None
    relevant_topic: str
    evidence_type: str
    version: str
    last_reviewed: str | None
    document_id: str | None = None
    version_id: str | None = None
    section: str | None = None
    page: int | None = None
    language: str | None = None
    jurisdiction: str | None = None
    specialty: str | None = None
    publication_date: str | None = None
    last_updated_date: str | None = None
    medical_category: str | None = None


class MedicalKnowledgeProvider(Protocol):
    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        language: str | None = None,
        jurisdiction: str | None = None,
        specialty: str | None = None,
    ) -> list[MedicalKnowledgeSource]: ...


class UnconfiguredMedicalKnowledgeProvider:
    """Explicit empty provider; prevents pretending unverified model memory is sourced."""

    async def search(self, query: str, *, limit: int = 5, language: str | None = None, jurisdiction: str | None = None, specialty: str | None = None) -> list[MedicalKnowledgeSource]:
        return []


class ApprovedMedicalKnowledgeProvider:
    """Production provider with approval revalidation on every retrieval."""

    async def search(self, query: str, *, limit: int = 5, language: str | None = None, jurisdiction: str | None = None, specialty: str | None = None) -> list[MedicalKnowledgeSource]:
        async with SessionFactory() as session:
            chunks = await search_approved(
                session,
                query,
                limit=limit,
                language=language,
                jurisdiction=jurisdiction or settings.knowledge_default_jurisdiction,
                specialty=specialty,
            )
        return [
            MedicalKnowledgeSource(
                source_id=str(item["metadata"]["source_id"]),
                title=str(item["metadata"]["source_title"]),
                organization=str(item["metadata"]["organization"]),
                excerpt=" ".join(item["text"].split())[:900],
                source_url=str(item["metadata"]["source_url"]),
                published_or_updated=item["metadata"].get("last_updated_date") or item["metadata"].get("publication_date"),
                relevant_topic=str(item["metadata"].get("relevant_topic") or "general medicine"),
                evidence_type=str(item["metadata"].get("source_type") or "reference"),
                version=str(item["metadata"]["document_version"]),
                last_reviewed=None,
                document_id=str(item["metadata"]["document_id"]),
                version_id=str(item["metadata"]["version_id"]),
                section=str(item["metadata"].get("section") or "Document text"),
                page=int(item["metadata"]["page"]) if item["metadata"].get("page") else None,
                language=str(item["metadata"]["language"]),
                jurisdiction=item["metadata"].get("jurisdiction") or None,
                specialty=item["metadata"].get("specialty") or None,
                publication_date=item["metadata"].get("publication_date") or None,
                last_updated_date=item["metadata"].get("last_updated_date") or None,
                medical_category=item["metadata"].get("medical_category") or None,
            )
            for item in chunks
        ]
