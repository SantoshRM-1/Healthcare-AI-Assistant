# Phase 5 — Patient Recommendations Report

## Implementation summary

Phase 5 extends the existing recommendation services, medical taxonomy, approved medical knowledge provider, hospital directory, session memory, and `/ai/chat` SSE flow. It does not add a second AI or recommendation service and does not replace Phase 1–4 behavior.

The main reliability issue fixed was broad context leakage: recommendation fallback could pass entire extracted reports to Gemini, while hospital matching scanned all completed report text and old chat turns as diagnoses. Recommendations now use retrieved report chunks first, then a bounded same-session fallback containing matching lines, explicitly labeled report statements, and parsed abnormal results. Hospital/specialist routing uses recent active-session patient statements, negation-aware taxonomy matches, explicit report diagnoses, and parsed abnormal lab findings. An abnormal result routes to a general physician (and a parser-provided specialty when available) for review; it is not labeled as a diagnosis.

## Reused functionality and additions

- Reused Phase 2 laboratory, prescription, symptom, and taxonomy parsers.
- Reused Phase 3 `ApprovedMedicalKnowledgeProvider`; recommendation and specialist responses return its provenance separately from report citations. Provider errors fail soft and produce no fabricated citations.
- Reused Phase 4 saved language mode and response-language selection.
- Reused existing PostgreSQL hospital rows only. City filters select the directory records; locality, district, and optional PIN code rank matching address records. Phone, website, ratings, and specialization are returned only when stored.
- Added Indian/Karnataka food name recognition for common foods in English and Kannada. Recognition is used to preserve named foods in prompt context; it does not assert that a food is suitable for a given condition.
- Added deterministic patient-facing questions from abnormal values printed in reports, visible prescription wording, and patient-reported symptoms. Medicine instructions are never inferred.
- Added backward-compatible optional structured fields to recommendation items and optional `medical_sources` response fields.
- Added optional PIN code input to the existing hospital location prompt. It is matched against stored addresses; no GPS or external location service is used.
- Added Kannada and bilingual category headings and recommendation disclaimers.

## Files changed

- `backend/app/services/recommendations.py`
- `backend/app/services/hospital_recommendations.py`
- `backend/app/api/v1/routes/ai.py`
- `backend/app/schemas/ai.py`
- `backend/app/schemas/platform.py`
- `frontend/src/components/ai-chat-panel.tsx`
- `backend/tests/test_phase5_recommendations.py`

No database migration was needed.

## Validation performed

- Python `compileall` for application and tests: passed.
- Backend test suite (`python -m unittest discover -s tests`): **50 tests passed**.
- Focused Ruff check on changed backend files: passed.
- `git diff --check`: passed (Git reported only existing line-ending normalization warnings).
- Frontend TypeScript check (`npm exec tsc -- --noEmit`): passed.
- Synthetic checks cover Karnataka food-name recognition, negated conditions, kidney-stone and abdominal-symptom routing, abnormal creatinine routing to a general physician without diagnosis, Kannada doctor questions, prescription-name questions, and no-evidence behavior.

## Limitations and deployment checks

- The approved medical knowledge collection may be empty. In that case the service returns no medical-source citations and the nutrition prompt is instructed to avoid condition-specific claims; its empty state must remain visible to patients. No source corpus was populated as part of this phase.
- The PostgreSQL hospital directory may be empty or have incomplete specialization/address/contact fields. The code returns only rows found there and explains when it has no matching listing; live matching could not be confirmed without a configured database and representative directory records.
- Gemini, PostgreSQL, and Chroma were not live-tested in this run. No real patient document was used.
- Hospital area and PIN matching can only rank address text already stored in the directory; records without those details cannot be proximity-ranked.
- Specialist routing is a care-navigation aid based on literal taxonomy terms or explicit symptom/lab parser output. It does not diagnose; emergency triage remains ahead of recommendation routing in the chat endpoint.
- The configured approved-reference search requests `kn` for Kannada and `en` for English. A corpus without language-tagged Kannada references can return no Kannada medical citations; it does not translate or relabel English references as Kannada.

## Manual smoke test

1. Open a chat with a processed report containing a printed abnormal lab interval; ask for food suggestions in English, Kannada, and bilingual mode. Check report citations and any available approved medical citations separately.
2. Ask about a named Karnataka food (for example, ragi mudde or akki rotti). Confirm the answer discusses it only when evidence and patient context support a suitability claim.
3. Enter a patient-reported condition or symptom and ask which doctor to see. Confirm the answer labels symptoms as patient-reported and suggests a general physician when evidence is uncertain.
4. Ask for a hospital. Enter a city, area, and/or PIN code. Confirm every result exists in the hospital directory and missing phone/contact fields remain omitted.
5. Ask for questions to discuss with a clinician. Confirm questions only refer to parsed report values, prescription text, or symptoms from the active chat.
6. Repeat with a negated condition and in a second chat to confirm it does not route from the first chat's memory.

