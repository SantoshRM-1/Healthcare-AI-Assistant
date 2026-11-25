"""Verified-source citation formatting kept independent of database/vector clients."""
from __future__ import annotations

from typing import Any


def make_medical_citations(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in chunks:
        meta = item["metadata"]
        key = (str(meta.get("source_id")), str(meta.get("document_id")), str(meta.get("section")))
        if key in seen:
            continue
        seen.add(key)
        page = meta.get("page")
        citations.append({
            "source_type": "medical_knowledge",
            "source_id": meta["source_id"],
            "document_id": meta["document_id"],
            "version_id": meta["version_id"],
            "title": meta["source_title"],
            "organization": meta["organization"],
            "source_url": meta["source_url"],
            "section": meta.get("section") or "Document text",
            "page": int(page) if page not in (None, "", 0, "0") else None,
            "publication_date": meta.get("publication_date") or None,
            "last_updated_date": meta.get("last_updated_date") or None,
            "version": meta["document_version"],
            "jurisdiction": meta.get("jurisdiction") or None,
            "language": meta["language"],
            "excerpt": " ".join(item["text"].split())[:900],
        })
    return citations
