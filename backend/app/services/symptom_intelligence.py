"""Extract patient-reported symptom mentions without converting them to diagnoses."""

import re

from app.schemas.medical_intelligence import SymptomAnalysis, SymptomMention
from app.services.medical_taxonomy import match_reported_conditions
from app.services.medical_terminology import normalize_medical_terms

_DURATION = re.compile(
    r"\b(?:for|since|from past|for past)\s+(\d+\s*(?:days?|weeks?|months?|years?|hours?))\b|"
    r"\b(?:for|since)\s+(one|two|three|four|five)\s+(days?|weeks?|months?|years?|hours?)\b|"
    r"\b(mooru|mooru|muru)\s+(dinadinda|dinagalu)\b",
    re.IGNORECASE,
)


def analyze_patient_text(text: str) -> SymptomAnalysis:
    duration_match = _DURATION.search(text)
    duration = (
        " ".join(group for group in duration_match.groups() if group) if duration_match else None
    )
    terms = normalize_medical_terms(text)
    symptoms = [
        SymptomMention(
            concept=item["concept"],
            phrase_as_reported=item["phrase_as_reported"],
            duration_as_reported=duration,
        )
        for item in terms
        if item["concept"]
        not in {
            "blood_glucose",
            "blood_pressure",
            "kidney_concern",
            "cardiac_concern",
            "low_blood_count",
            "jaundice_concern",
            "fracture_concern",
            "urinary_concern",
            "thyroid_concern",
        }
    ]
    condition_mentions = [
        {"sector": item["sector"], "condition": item["condition"]}
        for item in match_reported_conditions(text)
    ]
    warnings = []
    if condition_mentions:
        warnings.append(
            "Condition phrases are mentions only; they are not confirmed diagnoses unless explicitly documented by a clinician."
        )
    if symptoms:
        warnings.append("Symptoms are patient-reported and do not establish a diagnosis.")
    return SymptomAnalysis(
        symptoms=symptoms, condition_mentions=condition_mentions, warnings=warnings
    )
