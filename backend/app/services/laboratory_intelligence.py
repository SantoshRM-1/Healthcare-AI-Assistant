"""Conservative extraction using only values and reference intervals in report text."""

import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from app.schemas.medical_intelligence import LabAnalysis, LabFinding

_PARAMETERS: dict[str, tuple[str, tuple[str, ...], str | None]] = {
    "hemoglobin": (
        "Complete Blood Count",
        ("hemoglobin", "haemoglobin", "hgb", "hb"),
        "Hematology",
    ),
    "red blood cell count": (
        "Complete Blood Count",
        ("rbc count", "red blood cell count", "erythrocyte count", "rbc"),
        "Hematology",
    ),
    "white blood cell count": (
        "Complete Blood Count",
        ("white blood cell count", "total leukocyte count", "tlc", "wbc count", "wbc"),
        "Hematology",
    ),
    "platelet count": (
        "Complete Blood Count",
        ("platelet count", "platelets", "plt"),
        "Hematology",
    ),
    "hematocrit": (
        "Complete Blood Count",
        ("hematocrit", "haematocrit", "packed cell volume", "pcv"),
        "Hematology",
    ),
    "mean corpuscular volume": (
        "Complete Blood Count",
        ("mean corpuscular volume", "mcv"),
        "Hematology",
    ),
    "mean corpuscular hemoglobin": (
        "Complete Blood Count",
        ("mean corpuscular hemoglobin", "mch"),
        "Hematology",
    ),
    "mean corpuscular hemoglobin concentration": (
        "Complete Blood Count",
        ("mean corpuscular hemoglobin concentration", "mchc"),
        "Hematology",
    ),
    "neutrophils": ("Complete Blood Count", ("neutrophils", "neutrophil"), "Hematology"),
    "lymphocytes": ("Complete Blood Count", ("lymphocytes", "lymphocyte"), "Hematology"),
    "eosinophils": ("Complete Blood Count", ("eosinophils", "eosinophil"), "Hematology"),
    "erythrocyte sedimentation rate": (
        "Inflammatory Markers",
        ("erythrocyte sedimentation rate", "esr"),
        None,
    ),
    "creatinine": (
        "Kidney Function Test",
        ("serum creatinine", "creatinine", "creat"),
        "Nephrologist",
    ),
    "blood urea nitrogen": ("Kidney Function Test", ("blood urea nitrogen", "bun"), "Nephrologist"),
    "urea": ("Kidney Function Test", ("blood urea", "serum urea", "urea"), "Nephrologist"),
    "estimated glomerular filtration rate": (
        "Kidney Function Test",
        ("estimated glomerular filtration rate", "egfr", "gfr"),
        "Nephrologist",
    ),
    "uric acid": ("Kidney Function Test", ("uric acid", "urate"), "Nephrologist"),
    "urine oxalate": (
        "Kidney Function Test",
        ("oxalate, random urine", "urine oxalate", "oxalate"),
        "Urologist",
    ),
    "urine protein": (
        "Urine Routine and Microscopy",
        ("urine protein", "urine albumin", "protein in urine"),
        "Nephrologist",
    ),
    "urine red blood cells": (
        "Urine Routine and Microscopy",
        ("urine red blood cells", "urine rbc", "rbc/hpf"),
        "Urologist",
    ),
    "urine white blood cells": (
        "Urine Routine and Microscopy",
        ("urine white blood cells", "urine wbc", "pus cells", "wbc/hpf"),
        "Urologist",
    ),
    "urine specific gravity": (
        "Urine Routine and Microscopy",
        ("urine specific gravity", "specific gravity"),
        None,
    ),
    "urine ph": ("Urine Routine and Microscopy", ("urine ph", "urine reaction"), None),
    "alanine aminotransferase": (
        "Liver Function Test",
        ("alanine aminotransferase", "alt", "sgpt"),
        "Hepatologist",
    ),
    "aspartate aminotransferase": (
        "Liver Function Test",
        ("aspartate aminotransferase", "ast", "sgot"),
        "Hepatologist",
    ),
    "alkaline phosphatase": (
        "Liver Function Test",
        ("alkaline phosphatase", "alp"),
        "Hepatologist",
    ),
    "bilirubin": ("Liver Function Test", ("total bilirubin", "bilirubin"), "Hepatologist"),
    "albumin": ("Liver Function Test", ("serum albumin", "albumin"), "Hepatologist"),
    "globulin": ("Liver Function Test", ("serum globulin", "globulin"), "Hepatologist"),
    "gamma-glutamyl transferase": (
        "Liver Function Test",
        ("gamma glutamyl transferase", "gamma-glutamyl transferase", "ggt"),
        "Hepatologist",
    ),
    "total cholesterol": ("Lipid Profile", ("total cholesterol", "cholesterol"), "Cardiologist"),
    "low-density lipoprotein": (
        "Lipid Profile",
        ("low density lipoprotein", "ldl cholesterol", "ldl"),
        "Cardiologist",
    ),
    "high-density lipoprotein": (
        "Lipid Profile",
        ("high density lipoprotein", "hdl cholesterol", "hdl"),
        "Cardiologist",
    ),
    "triglycerides": ("Lipid Profile", ("triglycerides", "triglyceride", "tg"), "Cardiologist"),
    "apolipoprotein b": ("Lipid Profile", ("apolipoprotein b", "apob", "apo b"), "Cardiologist"),
    "lipoprotein(a)": ("Lipid Profile", ("lipoprotein(a)", "lipoprotein a", "lpa"), "Cardiologist"),
    "thyroid-stimulating hormone": (
        "Thyroid Function Test",
        ("thyroid stimulating hormone", "tsh"),
        "Endocrinologist",
    ),
    "triiodothyronine": ("Thyroid Function Test", ("free t3", "total t3", "t3"), "Endocrinologist"),
    "thyroxine": ("Thyroid Function Test", ("free t4", "total t4", "t4"), "Endocrinologist"),
    "fasting blood glucose": (
        "Diabetes Tests",
        ("fasting blood glucose", "fasting glucose", "fbs", "fasting blood sugar"),
        "Endocrinologist",
    ),
    "postprandial blood glucose": (
        "Diabetes Tests",
        ("postprandial glucose", "post prandial glucose", "ppbs"),
        "Endocrinologist",
    ),
    "random blood glucose": (
        "Diabetes Tests",
        ("random blood glucose", "random glucose", "rbs"),
        "Endocrinologist",
    ),
    "glycated hemoglobin": (
        "Diabetes Tests",
        ("glycated hemoglobin", "glycosylated hemoglobin", "hba1c", "a1c"),
        "Endocrinologist",
    ),
    "insulin": ("Diabetes Tests", ("fasting insulin", "insulin"), "Endocrinologist"),
    "sodium": ("Electrolytes", ("serum sodium", "sodium", "na+"), None),
    "potassium": ("Electrolytes", ("serum potassium", "potassium", "k+"), None),
    "chloride": ("Electrolytes", ("serum chloride", "chloride", "cl-"), None),
    "bicarbonate": ("Electrolytes", ("bicarbonate", "serum hco3", "hco3"), None),
    "calcium": ("Vitamin and Mineral Tests", ("serum calcium", "calcium"), None),
    "vitamin d": (
        "Vitamin and Mineral Tests",
        ("25-oh vitamin d", "25 hydroxy vitamin d", "vitamin d"),
        None,
    ),
    "vitamin b12": (
        "Vitamin and Mineral Tests",
        ("vitamin b12", "vitamin b-12", "cobalamin"),
        None,
    ),
    "ferritin": ("Vitamin and Mineral Tests", ("serum ferritin", "ferritin"), "Hematology"),
    "iron": ("Vitamin and Mineral Tests", ("serum iron", "iron"), "Hematology"),
    "magnesium": ("Vitamin and Mineral Tests", ("serum magnesium", "magnesium"), None),
    "phosphorus": (
        "Vitamin and Mineral Tests",
        ("serum phosphorus", "phosphorus", "phosphate"),
        "Nephrologist",
    ),
    "c-reactive protein": ("Inflammatory Markers", ("c-reactive protein", "crp"), None),
    "troponin": ("Cardiac Markers", ("troponin i", "troponin t", "troponin"), "Cardiologist"),
    "creatine kinase mb": (
        "Cardiac Markers",
        ("creatine kinase mb", "ck-mb", "ckmb"),
        "Cardiologist",
    ),
    "b-type natriuretic peptide": (
        "Cardiac Markers",
        ("b-type natriuretic peptide", "nt-probnp", "bnp"),
        "Cardiologist",
    ),
    "prothrombin time": ("Coagulation Tests", ("prothrombin time", "pt/inr", "pt"), None),
    "international normalized ratio": (
        "Coagulation Tests",
        ("international normalized ratio", "inr"),
        None,
    ),
    "activated partial thromboplastin time": (
        "Coagulation Tests",
        ("activated partial thromboplastin time", "aptt"),
        None,
    ),
}

_NUMBER = r"[<>≤≥]?\s*-?\d[\d,]*(?:\.\d+)?"
_VALUE = re.compile(rf"(?<![\w.])({_NUMBER})\s*([%a-zA-Zµμ/³^0-9.-]*)")
_RANGE = re.compile(
    rf"(?:\(\s*({_NUMBER})\s*(?:[-–—]|\bto\b)\s*({_NUMBER})\s*\)|(?:reference|ref(?:erence)? range|normal range)\s*[:=]?\s*({_NUMBER})\s*(?:[-–—]|\bto\b)\s*({_NUMBER}))",
    re.IGNORECASE,
)
_PAGE = re.compile(r"^---\s*Page\s+(\d+)\s*---$", re.IGNORECASE)


def _number(value: str) -> Decimal | None:
    cleaned = (
        value.replace(",", "")
        .replace("≤", "")
        .replace("≥", "")
        .replace("<", "")
        .replace(">", "")
        .strip()
    )
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _alias_match(line: str) -> tuple[str, str] | None:
    lowered = line.casefold()
    aliases = sorted(
        ((alias, canonical) for canonical, (_, names, _) in _PARAMETERS.items() for alias in names),
        key=lambda item: (-len(item[0]), item[0]),
    )
    matches: list[tuple[int, int, str, str]] = []
    for alias, canonical in aliases:
        match = re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lowered)
        if match:
            matches.append((match.start(), -len(alias), alias, canonical))
    if not matches:
        return None
    _, _, alias, canonical = min(matches)
    return canonical, alias


def contains_laboratory_parameters(text: str) -> bool:
    return any(_alias_match(line) for line in text.splitlines())


def parse_laboratory_results(text: str) -> LabAnalysis:
    findings: list[LabFinding] = []
    page: int | None = None
    for line_number, raw_line in enumerate(text.replace("\r", "").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        page_marker = _PAGE.match(line)
        if page_marker:
            page = int(page_marker.group(1))
            continue
        matched = _alias_match(line)
        if not matched:
            continue
        canonical, alias = matched
        category, _, specialty = _PARAMETERS[canonical]
        alias_match = re.search(
            rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", line, re.IGNORECASE
        )
        assert alias_match is not None
        suffix = line[alias_match.end() :]
        value_match = _VALUE.search(suffix)
        range_match = _RANGE.search(line)
        if (
            value_match
            and range_match
            and alias_match.end() + value_match.start() >= range_match.start()
        ):
            value_match = None
        unit = None
        value = None
        status = "missing"
        reference = None
        if value_match:
            value = value_match.group(1).strip()
            unit = value_match.group(2).strip(" .,:;()") or None
            denominator = re.match(
                r"\s+(creatinine|creat|protein)\b", suffix[value_match.end() :], re.IGNORECASE
            )
            if unit and denominator:
                unit = f"{unit} {denominator.group(1)}"
            status = "unassessed"
        else:
            status = "unreadable"
        if range_match:
            low_raw, high_raw = (
                (range_match.group(1), range_match.group(2))
                if range_match.group(1)
                else (range_match.group(3), range_match.group(4))
            )
            reference = f"{low_raw.strip()} - {high_raw.strip()}"
            range_unit_match = re.match(r"\s*([%a-zA-Zµμ/³^0-9.-]+)", line[range_match.end() :])
            range_unit = range_unit_match.group(1) if range_unit_match else None
            value_number, low_number, high_number = (
                _number(value or ""),
                _number(low_raw),
                _number(high_raw),
            )
            has_qualifier = bool(value and re.match(r"\s*[<>≤≥]", value))
            unit_compatible = not range_unit or (
                unit is not None and range_unit.casefold() == unit.casefold()
            )
            if (
                value_number is not None
                and low_number is not None
                and high_number is not None
                and not has_qualifier
                and unit_compatible
            ):
                status = (
                    "low"
                    if value_number < low_number
                    else "high"
                    if value_number > high_number
                    else "normal"
                )
            elif value is not None:
                status = "unassessed"
        findings.append(
            LabFinding(
                canonical_name=canonical,
                original_name=alias_match.group(0),
                category=category,
                value=value,
                unit=unit,
                reference_range=reference,
                status=status,
                specialty=specialty,
                page=page,
                source_location=f"page {page}, line {line_number}"
                if page
                else f"line {line_number}",
                original_text=line,
            )
        )
    grouped: dict[str, list[LabFinding]] = defaultdict(list)
    for finding in findings:
        if finding.value is not None:
            grouped[finding.canonical_name].append(finding)
    warnings: list[str] = []
    for name, duplicates in grouped.items():
        values = {(item.value, item.unit.casefold() if item.unit else None) for item in duplicates}
        if len(values) > 1:
            warnings.append(f"Conflicting values were found for {name}; manual review is needed.")
            for item in duplicates:
                item.status = "ambiguous"
    if any(item.status == "unreadable" for item in findings):
        warnings.append("Some recognized test names had no readable numeric result.")
    return LabAnalysis(findings=findings, warnings=warnings)
