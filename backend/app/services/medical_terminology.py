"""Conservative patient-language normalization; terms indicate concepts, not diagnoses."""

import re

_TERMS: dict[str, tuple[str, ...]] = {
    "blood_glucose": (
        "sugar level",
        "blood sugar",
        "sugar level jasthi",
        "sugar jasthi",
        "sakkare jaasti",
        "sakkare jasthi",
    ),
    "blood_pressure": (
        "bp high",
        "high bp",
        "blood pressure high",
        "bp tumba high",
        "pressure jasthi",
    ),
    "kidney_concern": (
        "kidney problem",
        "renal problem",
        "kidney issue",
        "kidney problem ide",
        "kidney issue ide",
    ),
    "cardiac_concern": ("heart blockage", "heart problem", "heart pain"),
    "low_blood_count": ("low blood count", "blood count low"),
    "jaundice_concern": ("yellow eyes", "eyes are yellow"),
    "fracture_concern": ("bone crack", "broken bone"),
    "urinary_concern": ("urine infection", "urinary infection", "mootra infection"),
    "thyroid_concern": ("thyroid problem", "thyroid report abnormal"),
    "fever": ("fever", "jwara", "jvaram", "nange fever ide", "nanage jwara ide"),
    "chest_pain": ("chest pain", "ಎದೆ ನೋವು", "edeyalli novu"),
    "dysuria": (
        "burning while urinating",
        "burning urination",
        "pain while urinating",
        "mootra madovaga uritha ide",
        "mootra madovaga uri",
        "mootra madovaga uritha",
        "uritha ide",
    ),
    "pain": ("pain", "ache", "novu", "nove"),
    "abdominal_pain": ("stomach pain", "stomach ache", "abdominal pain", "ಹೊಟ್ಟೆ ನೋವು", "hotte novu"),
    "headache": ("headache", "head pain", "ತಲೆ ನೋವು", "tale novu"),
    "arm_pain": ("arm pain", "hand pain", "kai novu"),
    "back_pain": ("back pain", "ಬೆನ್ನು ನೋವು", "bennu novu"),
    "joint_pain": ("joint pain", "joints hurt", "ಸಂಧಿ ನೋವು"),
    "cough": ("cough", "ಕೆಮ್ಮು", "kemmu"),
    "rash": ("rash", "skin rash", "ದದ್ದು", "daddu"),
    "itching": ("itching", "itchy", "ತುರಿಕೆ", "turike"),
    "dizziness": ("dizzy", "dizziness", "ತಲೆ ಸುತ್ತು", "tale suttu"),
    "breathlessness": (
        "shortness of breath",
        "breathless",
        "difficulty breathing",
        "usiraadakke kashta",
    ),
    "nausea": ("nausea", "ವಾಕರಿಕೆ", "vanti baruva bhavane"),
    "vomiting": ("vomiting", "vomit", "ವಾಂತಿ", "vanti"),
    "diarrhea": ("diarrhea", "loose motions", "ಅತಿಸಾರ", "atisara"),
    "constipation": ("constipation", " ಮಲಬದ್ಧತೆ".strip(), "malabaddhate"),
    "fatigue": ("fatigue", "tired all the time", "tiredness", "ಸೋಲು", "sustu"),
    "palpitations": ("palpitations", "heart racing", "ಹೃದಯ ಬಡಿತ ಹೆಚ್ಚಳ"),
    "numbness": ("numbness", "numb", "ಮರಗಟ್ಟುವಿಕೆ"),
    "swelling": ("swelling", "swollen", "ಊತ"),
    "dark_urine": ("dark urine", "urine is dark", "ಕಪ್ಪು ಮೂತ್ರ"),
    "sore_throat": ("sore throat", "throat pain", "ಗಂಟಲು ನೋವು"),
    "ear_pain": ("ear pain", "ಕಿವಿ ನೋವು"),
    "vision_change": ("blurred vision", "blurry vision", "vision is blurry", "ಮಸುಕಾದ ದೃಷ್ಟಿ"),
    "appetite_loss": ("loss of appetite", "no appetite", "appetite loss", "ಹಸಿವು ಇಲ್ಲ"),
}


def normalize_medical_terms(text: str) -> list[dict[str, str]]:
    normalized = re.sub(r"\s+", " ", text.casefold())
    found: list[dict[str, str]] = []
    for concept, variants in _TERMS.items():
        for phrase in sorted(variants, key=len, reverse=True):
            term = re.sub(r"\s+", " ", phrase.casefold()).strip()
            match = re.search(rf"(?<!\w){re.escape(term)}(?!\w)", normalized)
            if match:
                prefix = normalized[max(0, match.start() - 18) : match.start()]
                if re.search(r"\b(no|not|without|denies)\b.{0,18}$", prefix) or normalized[
                    match.end() : match.end() + 10
                ].startswith(" illa"):
                    break
                found.append(
                    {
                        "concept": concept,
                        "phrase_as_reported": phrase.strip(),
                        "interpretation": "language normalization only; not a diagnosis",
                    }
                )
                break
    return found
