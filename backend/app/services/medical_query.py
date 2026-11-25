"""Deterministic medical query routing and multilingual retrieval helpers.

These rules normalize search queries and select retrieval paths only. They do not
diagnose a patient or add clinical facts to an answer.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any


_INTENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("report_summary", re.compile(r"\b(summarize|summarise|summary|overview|compare|difference between|saaramsha|vivarisi|explain.{0,30}report|what does.{0,35}report.{0,25}(show|say|indicate)|what is in my report|what problem.{0,20}report|what does my blood report)\b|ಸಾರಾಂಶ|ವರದಿ.*(ವಿವರಿಸಿ|ಹೇಳಿ)|ವರದಿಯಲ್ಲಿ ಏನು", re.I)),
    ("laboratory", re.compile(r"\b(hba1c|hemoglobin|haemoglobin|creatinine|platelets?|cholesterol|thyroid|tsh|blood test|lab(?:oratory)? result|reference range|report value|cbc|kft|lft)\b|ಹಿಮೋಗ್ಲೋಬಿನ್|ಕ್ರಿಯಾಟಿನಿನ್|ಪ್ಲೇಟ್.?ಲೆಟ್|ರಕ್ತ ಪರೀಕ್ಷೆ|ರಕ್ತದ ಸಕ್ಕರೆ|ಮೂತ್ರ ಪರೀಕ್ಷೆ", re.I)),
    ("prescription", re.compile(r"\b(prescription|medicine|medication|drug|tablet|capsule|dosage|dose|side effect|when should i take|medicine yavaga tagobeku)\b|ಔಷಧಿ|ಮಾತ್ರೆ|ಔಷಧವನ್ನು ಯಾವಾಗ", re.I)),
    ("nutrition", re.compile(r"\b(food|foods|eat|eating|diet|nutrition|meal|what should i eat|tinnabeku|tinnabahudu|oota|tindi)\b|ಆಹಾರ|ಊಟ|ತಿನ್ನಬೇಕು|ತಿನ್ನಬಹುದು|ತಿಂಡಿ", re.I)),
    ("precautions", re.compile(r"\b(precautions?|warning sign|what should i avoid|avoid|monitor|what should i take care|jagrate)\b|ಮುನ್ನೆಚ್ಚರಿಕೆ|ತಪ್ಪಿಸಬೇಕು|ಗಮನಿಸಬೇಕು", re.I)),
    ("hospital", re.compile(r"\b(hospital|clinic|where should i go|aspatal|aaspatre)\b|ಆಸ್ಪತ್ರೆ|ಹಾಸ್ಪಿಟಲ್", re.I)),
    ("specialist", re.compile(r"\b(doctor|specialist|physician|which doctor|who should i consult|vaidya|daaktar|daktar)\b|ವೈದ್ಯ|ಡಾಕ್ಟರ್|ತಜ್ಞ", re.I)),
    ("symptoms", re.compile(r"\b(symptom|symptoms|pain|fever|cough|itching|dizzy|headache|breathing|chest pain|burning urination|urinating|jwara|novu|uritha ide|mootra madovaga|saas|usiraada|mukha|mathanadakke)\b|ಲಕ್ಷಣ|ನೋವು|ಜ್ವರ|ಕೆಮ್ಮು|ತುರಿಕೆ|ಮೂತ್ರ ವಿಸರ್ಜನೆ|ಉರಿ|ಉಸಿರಾಟ|ಉಸಿರಾಡ|ಎದೆ ನೋವು|ಮುಖ ಒಂದು ಕಡೆ", re.I)),
    ("terminology", re.compile(r"\b(what does .{1,60} mean|meaning of|define|explain the term)\b|ಅರ್ಥವೇನು|ಅರ್ಥ ಏನು", re.I)),
)

_MEDICAL_QUERY_MARKERS = re.compile(
    r"\b(health|medical|disease|condition|test|report|symptom|medicine|doctor|hospital|"
    r"pain|fever|sick|sugar|kidney|heart|blood|urine|creatinine|tsh|hba1c)\b|"
    r"ಆರೋಗ್ಯ|ರೋಗ|ಪರೀಕ್ಷೆ|ವರದಿ|ಲಕ್ಷಣ|ಔಷಧ|ವೈದ್ಯ|ಆಸ್ಪತ್ರೆ|ನೋವು|ಜ್ವರ|ಸಕ್ಕರೆ|ಮೂತ್ರ|ಕಿಡ್ನಿ|ಹೃದಯ",
    re.I,
)
_FOLLOW_UP_MARKERS = re.compile(
    r"\b(it|this|that|these|those|they|them|what about|why|how about|does it|is it|"
    r"what does that|what does it|and food|and diet)\b|ಇದರ|ಅದು|ಅದಕ್ಕೆ|ಇದರಿಂದ|ಹಾಗಾದರೆ|ಮತ್ತೆ",
    re.I,
)
_SMALLTALK = re.compile(r"^(hi|hello|hey|thanks|thank you|good morning|good evening|ನಮಸ್ಕಾರ|ಧನ್ಯವಾದ)\W*$", re.I)

# Query-only cross-language aliases. Keep numbers and the user's original wording.
_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("haemoglobin hemoglobin Hb Hgb", ("haemoglobin", "hemoglobin", "hgb", "hb", "ಹಿಮೋಗ್ಲೋಬಿನ್", "ರಕ್ತಹೀನತೆ", "rakta heenate")),
    ("creatinine kidney renal kidney function renal function ಮೂತ್ರಪಿಂಡ ಕ್ರಿಯಾಟಿನಿನ್", ("creatinine", "ಕ್ರಿಯಾಟಿನಿನ್", "kidney function", "renal function", "ಮೂತ್ರಪಿಂಡ", "moothrapinda")),
    ("blood glucose blood sugar HbA1c diabetes sakkare ರಕ್ತದಲ್ಲಿನ ಸಕ್ಕರೆ ಮಧುಮೇಹ", ("hba1c", "blood glucose", "blood sugar", "sugar level", "sakkare", "ಸಕ್ಕರೆ", "ಮಧುಮೇಹ", "diabetes")),
    ("platelet count CBC ಪ್ಲೇಟ್‌ಲೆಟ್‌ಗಳು ರಕ್ತ ಪರೀಕ್ಷೆ", ("platelet", "platelets", "ಪ್ಲೇಟ್‌ಲೆಟ್", "cbc")),
    ("thyroid TSH ಥೈರಾಯ್ಡ್", ("thyroid", "tsh", "ಥೈರಾಯ್ಡ್")),
    ("blood pressure hypertension BP ರಕ್ತದೊತ್ತಡ", ("blood pressure", "hypertension", "bp", "ರಕ್ತದೊತ್ತಡ")),
    ("urinary burning dysuria painful urination ಮೂತ್ರ ವಿಸರ್ಜನೆ ಉರಿ", ("burning urination", "burning while urinating", "urinating", "mootra", "uritha", "ಮೂತ್ರ", "ಉರಿ")),
    ("kidney stone renal calculus kidney calculus ಮೂತ್ರಪಿಂಡದ ಕಲ್ಲು", ("kidney stone", "renal stone", "kidney calculus", "ಮೂತ್ರಪಿಂಡದ ಕಲ್ಲು", "ಕಿಡ್ನಿ ಕಲ್ಲು", "kidney kallu")),
    ("abdominal pain stomach pain ಹೊಟ್ಟೆ ನೋವು hotte novu", ("abdominal pain", "stomach pain", "ಹೊಟ್ಟೆ ನೋವು", "hotte novu")),
    ("fever pyrexia ಜ್ವರ jwara", ("fever", "ಜ್ವರ", "jwara", "jwara ide")),
)

_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "in", "on", "for", "my", "me", "i", "you",
    "what", "which", "does", "do", "did", "can", "could", "would", "should", "and", "or", "it", "this", "that",
    "ಮತ್ತು", "ನನ್ನ", "ನನಗೆ", "ಇದು", "ಏನು", "ಯಾವ", "ಆಗಿದೆ", "ಇದೆ",
}


def compact_conversation_history(
    history: Sequence[dict[str, str]], *, max_messages: int = 12, max_chars: int = 6000, per_message_chars: int = 1400
) -> list[dict[str, str]]:
    """Keep recent turns and bound prompt size; session authorization is enforced by the caller."""
    selected: list[dict[str, str]] = []
    size = 0
    for item in reversed(history):
        role = item.get("role", "")
        content = item.get("content", "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        content = content[-per_message_chars:]
        if size + len(content) > max_chars:
            content = content[-max(0, max_chars - size):]
        if not content:
            break
        selected.append({"role": role, "content": content})
        size += len(content)
        if len(selected) >= max_messages or size >= max_chars:
            break
    return list(reversed(selected))


def _history_text(history: Sequence[dict[str, str]], memory: dict[str, Any] | None = None) -> str:
    recent = " ".join(item.get("content", "") for item in history[-12:] if item.get("role") == "user")
    if memory:
        memory_facts = [memory.get(key, "") for key in ("last_topic", "reported_symptoms")]
        memory_facts.extend(memory.get(key, [])[-3:] for key in ("diagnoses",))
        memory_text = " ".join(value if isinstance(value, str) else " ".join(value) for value in memory_facts if value)
        recent = f"{recent} {memory_text}"
    return recent[-2400:]


def classify_medical_intent(
    question: str, history: Sequence[dict[str, str]] = (), memory: dict[str, Any] | None = None
) -> str:
    """Return a retrieval route, not a clinical conclusion."""
    clean = re.sub(r"\s+", " ", question).strip()
    if _SMALLTALK.fullmatch(clean):
        return "conversational"
    specific_patterns = [(intent, pattern) for intent, pattern in _INTENT_PATTERNS if intent != "terminology"]
    for intent, pattern in specific_patterns:
        if pattern.search(clean):
            return intent
    recent_user_text = _history_text(history, memory)
    if (_FOLLOW_UP_MARKERS.search(clean) or len(clean.split()) <= 7) and _MEDICAL_QUERY_MARKERS.search(recent_user_text):
        return "follow_up"
    terminology_pattern = dict(_INTENT_PATTERNS)["terminology"]
    if terminology_pattern.search(clean):
        return "terminology"
    if _MEDICAL_QUERY_MARKERS.search(clean):
        return "general_medical"
    return "conversational"


def expand_medical_query(
    question: str,
    history: Sequence[dict[str, str]] = (),
    memory: dict[str, Any] | None = None,
    *,
    max_history_chars: int = 1200,
) -> str:
    """Preserve the query while appending only aliases explicitly matched in it/context."""
    recent_user_text = _history_text(history, memory)[-max_history_chars:]
    base = " ".join(part for part in (recent_user_text, question.strip()) if part)
    normalized = re.sub(r"\s+", " ", base.casefold())
    aliases = [alias for alias, variants in _ALIASES if any(variant.casefold() in normalized for variant in variants)]
    return f"{base}\nMedical query aliases: {'; '.join(aliases)}" if aliases else base


def rerank_retrieval_results(
    results: Iterable[dict[str, Any]],
    query: str,
    *,
    limit: int,
    max_distance: float,
) -> list[dict[str, Any]]:
    """Small, dependency-free lexical tie-break over semantic candidates.

    The semantic distance remains the main relevance signal; the bounded overlap
    bonus can only reorder close candidates. Duplicate excerpts are removed.
    """
    query_tokens = {
        token for token in re.findall(r"[\w]+", query.casefold(), flags=re.UNICODE)
        if len(token) > 1 and token not in _STOP_WORDS
    }
    ranked: list[tuple[float, float, int, dict[str, Any]]] = []
    seen: set[str] = set()
    for position, item in enumerate(results):
        text = str(item.get("text", ""))
        try:
            distance = float(item.get("distance"))
        except (TypeError, ValueError):
            continue
        if not text.strip() or distance > max_distance:
            continue
        duplicate_key = re.sub(r"\s+", " ", text.casefold()).strip()
        if duplicate_key in seen:
            continue
        seen.add(duplicate_key)
        text_tokens = set(re.findall(r"[\w]+", text.casefold(), flags=re.UNICODE))
        overlap = len(query_tokens & text_tokens) / max(1, len(query_tokens))
        score = distance - min(0.08, overlap * 0.08)
        ranked.append((score, distance, position, item))
    ranked.sort(key=lambda value: (value[0], value[1], value[2]))
    return [item for _, _, _, item in ranked[: max(0, limit)]]
