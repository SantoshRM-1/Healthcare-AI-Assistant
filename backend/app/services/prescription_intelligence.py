"""Rule-based extraction of visible prescription wording, never prescribing."""

import re

from app.schemas.medical_intelligence import PrescriptionAnalysis, PrescriptionItem

_PAGE = re.compile(r"^---\s*Page\s+(\d+)\s*---$", re.IGNORECASE)
_STRENGTH = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|ml|mL|iu|units?|%|tablet(?:s)?|capsule(?:s)?)\b",
    re.IGNORECASE,
)
_INSTRUCTION = re.compile(
    r"\b(od|bd|tds|qid|sos|hs|ac|pc|once daily|twice daily|three times (?:a|per) day|at bedtime|before food|after food|for\s+\d+\s+days?)\b",
    re.IGNORECASE,
)
_UNREADABLE = re.compile(r"\b(?:illegible|unreadable|unclear)\b|[x?]{2,}", re.IGNORECASE)
_DURATION = re.compile(r"\bfor\s+\d+\s*(?:days?|weeks?|months?)\b", re.IGNORECASE)
_ROUTE = re.compile(
    r"\b(?:oral|by mouth|topical|inhal(?:ed|ation)|intravenous|\bi\.?v\.?\b|\bi\.?m\.?\b|ophthalmic|otic|sublingual|rectal)\b",
    re.IGNORECASE,
)
_FREQUENCY = re.compile(
    r"\b(?:od|bd|tds|qid|sos|hs|ac|pc|once daily|twice daily|three times (?:a|per) day|once a day|twice a day)\b",
    re.IGNORECASE,
)
_TIMING = re.compile(
    r"\b(?:at bedtime|morning|afternoon|evening|night|before food|after food|before meals?|after meals?)\b",
    re.IGNORECASE,
)
_FOOD = re.compile(
    r"\b(?:before food|after food|before meals?|after meals?|with food|empty stomach)\b",
    re.IGNORECASE,
)
_PRESCRIBER = re.compile(
    r"^\s*(?:prescribing doctor|prescriber|doctor|dr\.?)[\s:.-]+(.{2,100})$", re.IGNORECASE
)
_DATE = re.compile(r"^\s*(?:prescription\s+)?date\s*[:.-]\s*(.{4,40})$", re.IGNORECASE)


def contains_prescription_content(text: str) -> bool:
    return any(_STRENGTH.search(line) and _INSTRUCTION.search(line) for line in text.splitlines())


def _prefix_name(line: str, strength: re.Match[str] | None) -> str | None:
    if _UNREADABLE.search(line):
        return None
    if not strength:
        return None
    prefix = line[: strength.start()].strip(" :,-\t")
    prefix = re.sub(r"^\d+[.)]\s*", "", prefix)
    prefix = re.sub(
        r"^(?:tab(?:let)?|cap(?:sule)?|syp|syrup|inj(?:ection)?|cream|oint(?:ment)?)\.?\s*",
        "",
        prefix,
        flags=re.IGNORECASE,
    )
    if not prefix or len(prefix) > 80 or re.search(r"\d{3,}", prefix):
        return None
    return prefix


def extract_prescription_items(text: str) -> PrescriptionAnalysis:
    items: list[PrescriptionItem] = []
    page: int | None = None
    prescriber: str | None = None
    prescription_date: str | None = None
    warnings: list[str] = []
    for line_number, raw in enumerate(text.replace("\r", "").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        page_marker = _PAGE.match(line)
        if page_marker:
            page = int(page_marker.group(1))
            continue
        prescriber_match = _PRESCRIBER.match(line)
        if prescriber_match:
            prescriber = prescriber_match.group(1).strip()
            continue
        date_match = _DATE.match(line)
        if date_match:
            prescription_date = date_match.group(1).strip()
            continue
        if not (_STRENGTH.search(line) or _INSTRUCTION.search(line)):
            continue
        strength = _STRENGTH.search(line)
        name = _prefix_name(line, strength)
        instruction_matches = list(_INSTRUCTION.finditer(line))
        if not instruction_matches and not strength:
            continue
        if _UNREADABLE.search(line):
            name = None
        duration = _DURATION.search(line)
        route = _ROUTE.search(line)
        frequency = _FREQUENCY.search(line)
        timing = _TIMING.search(line)
        food = _FOOD.search(line)
        items.append(
            PrescriptionItem(
                medicine_name_as_written=name,
                generic_name=None,
                strength=strength.group(0) if strength else None,
                dosage_instructions_as_written=" ".join(m.group(0) for m in instruction_matches)
                or None,
                route_as_written=route.group(0) if route else None,
                frequency_as_written=frequency.group(0) if frequency else None,
                timing_as_written=timing.group(0) if timing else None,
                duration_as_written=duration.group(0) if duration else None,
                food_instructions_as_written=food.group(0) if food else None,
                prescriber_as_written=prescriber,
                prescription_date_as_written=prescription_date,
                page=page,
                source_location=f"page {page}, line {line_number}"
                if page
                else f"line {line_number}",
                original_text=line,
                extraction_status="unclear_name_requires_pharmacist_review"
                if name is None
                else "text_extracted_requires_original_prescription_confirmation",
            )
        )
    if items:
        warnings.append(
            "This is OCR text extraction, not a verified prescription. Confirm medicine names and instructions against the original with a pharmacist or prescribing clinician."
        )
    return PrescriptionAnalysis(items=items, warnings=warnings)
