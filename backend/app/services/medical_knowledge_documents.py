"""Safe extraction and provenance-preserving chunking for curated references."""
from __future__ import annotations

import asyncio
import hashlib
import io
import csv
import json
import re
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    index: int
    section: str
    page: int | None
    content: str


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_text_file(data: bytes, extension: str) -> str:
    if extension in {"txt", "md"}:
        return data.decode("utf-8-sig", errors="strict").replace("\x00", "")
    if extension == "json":
        return json.dumps(json.loads(data.decode("utf-8-sig", errors="strict")), ensure_ascii=False, indent=2)
    if extension == "csv":
        rows = csv.reader(io.StringIO(data.decode("utf-8-sig", errors="strict")))
        return "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)
    if extension == "docx":
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", ns):
            text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)
    raise ValueError("Only PDF, DOCX, TXT, Markdown, JSON, and CSV references are supported")


async def extract_document(data: bytes, mime_type: str, file_name: str, version_id: str) -> str:
    extension = file_name.rsplit(".", 1)[-1].lower()
    if extension == "pdf" and mime_type == "application/pdf":
        from app.services.report_ocr import run_ocr

        return await run_ocr(data, mime_type, settings.knowledge_max_pdf_pages, version_id)
    return await asyncio.to_thread(extract_text_file, data, extension)


_PAGE = re.compile(r"^---\s*Page\s+(\d+)\s*---$", re.I)
_HEADING = re.compile(r"^(?:#{1,6}\s+|[A-Z][A-Z0-9 /&(),:.-]{2,90}$)")


def chunk_document(text: str, chunk_size: int = 1500, overlap: int = 180) -> list[KnowledgeChunk]:
    """Chunk on paragraph/page/heading boundaries without losing section labels."""
    chunks: list[KnowledgeChunk] = []
    page: int | None = None
    section = "Document text"
    current: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal current, size
        content = "\n".join(current).strip()
        if content:
            chunks.append(KnowledgeChunk(len(chunks), section[:240], page, content))
        tail: list[str] = []
        tail_size = 0
        for line in reversed(current):
            if tail_size + len(line) + 1 > overlap:
                break
            tail.append(line)
            tail_size += len(line) + 1
        current = list(reversed(tail))
        size = tail_size

    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        marker = _PAGE.match(line)
        if marker:
            flush()
            page = int(marker.group(1))
            section = f"Page {page}"
            current, size = [], 0
            continue
        if line and _HEADING.match(line) and len(line) <= 240:
            flush()
            section = line.lstrip("# ").strip()[:240]
            current, size = [], 0
        if not line:
            if current and current[-1]:
                current.append("")
            continue
        pieces: list[str] = []
        remaining = line
        while len(remaining) > chunk_size:
            split_at = remaining.rfind(" ", 0, chunk_size + 1)
            split_at = split_at if split_at > 0 else chunk_size
            pieces.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        if remaining:
            pieces.append(remaining)
        for piece in pieces:
            if size + len(piece) > chunk_size and current:
                flush()
            current.append(piece)
            size += len(piece) + 1
    flush()
    return chunks
