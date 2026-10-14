import re
from dataclasses import dataclass

from app.core.config import settings

PAGE_MARKER = re.compile(r"^---\s*Page\s+(\d+)\s*---$", re.IGNORECASE)
HEADING_HINT = re.compile(
    r"\b(patient information|clinical history|diagnosis|medication(?:s)?(?: list)?|"
    r"prescription|laboratory results|test results|investigations|findings|"
    r"impression|recommendations?|discharge instructions|vital signs)\b",
    re.IGNORECASE,
)
ALL_CAPS_HEADING = re.compile(r"^[A-Z][A-Z0-9 /&(),:.-]{2,70}$")


@dataclass(frozen=True)
class ReportChunk:
    index: int
    page: int | None
    section: str
    text: str


def _section_for(line: str, current: str) -> str:
    cleaned = " ".join(line.strip(" #:*\t").split())
    if not cleaned or len(cleaned) > 90:
        return current
    hint = HEADING_HINT.search(cleaned)
    if hint:
        return hint.group(0).title()[:90]
    # Never copy values such as patient names or report IDs into source-section metadata.
    if ALL_CAPS_HEADING.fullmatch(cleaned) and ":" not in cleaned and not re.search(r"\d|@", cleaned) and len(cleaned.split()) <= 8:
        return cleaned.title()[:90]
    return current


def chunk_report(text: str, report_name: str) -> list[ReportChunk]:
    """Chunk by page and report headings, retaining nearby lines as context overlap."""
    if not text.strip():
        return []
    chunks: list[ReportChunk] = []
    page: int | None = None
    section = "Document text"
    lines: list[str] = []
    current_length = 0
    max_chars = max(500, settings.rag_chunk_size_chars)
    overlap = min(max(0, settings.rag_chunk_overlap_chars), max_chars // 3)

    def flush() -> None:
        nonlocal lines, current_length
        body = "\n".join(line for line in lines if line.strip()).strip()
        if body:
            prefix = f"Report: {report_name}\nSection: {section}"
            chunks.append(ReportChunk(len(chunks), page, section, f"{prefix}\n{body}"))
        if overlap and lines:
            tail: list[str] = []
            size = 0
            for line in reversed(lines):
                if size + len(line) + 1 > overlap:
                    break
                tail.append(line)
                size += len(line) + 1
            lines = list(reversed(tail))
            current_length = size
        else:
            lines = []
            current_length = 0

    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        match = PAGE_MARKER.match(raw.strip())
        if match:
            flush()
            page = int(match.group(1))
            section = f"Page {page}"
            lines = []
            current_length = 0
            continue
        new_section = _section_for(raw, section)
        if new_section != section:
            flush()
            lines = []
            current_length = 0
            section = new_section if page is None else f"Page {page} · {new_section}"
        line = raw.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if current_length + len(line) > max_chars and lines:
            flush()
        lines.append(line)
        current_length += len(line) + 1
    flush()
    return chunks
