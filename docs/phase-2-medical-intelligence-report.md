# Phase 2 — Medical Intelligence Core

**Status:** Implemented as a conservative extraction and routing increment. Not clinically validated.

## Implementation plan

1. Reuse Phase 1's sector taxonomy, OCR page markers, user/session-filtered Chroma retrieval, existing LangGraph, and stored language preference.
2. Add deterministic, source-preserving lab, prescription, terminology, and symptom parsers with typed Pydantic schemas.
3. Add these parsers as a report-aware analysis node before the existing Gemini answer node. Preserve the existing REST request and SSE event contract.
4. Add synthetic regression tests and validate with Python compilation and Ruff.

## Modules implemented

- **Laboratory intelligence:** maps common CBC, KFT/RFT, LFT, lipid, thyroid, diabetes, urine, vitamin/mineral, electrolyte, inflammatory, cardiac, and coagulation parameters to canonical names. It retains the report label, raw line, parsed value/unit, printed range, page, and line. It classifies low/normal/high only when a numeric range is present and units are compatible. Missing ranges and qualified/ambiguous results remain unassessed. Conflicting duplicate values are marked ambiguous. No critical thresholds or universal reference ranges are embedded.
- **Prescription extraction:** extracts visible line-level medicine wording, strength and written instructions (route, frequency, timing, duration, food), plus clearly labeled prescriber/date fields when present. Generic names are left blank because no verified medicine reference is configured. Unclear names and all extracted instructions require confirmation against the original.
- **Symptom understanding:** normalizes a conservative set of English, Kannada-script, Romanized Kannada, and mixed-language patient phrases. It records symptom phrases as patient-reported, not diagnoses, and captures simple duration phrases. Taxonomy matches remain literal mentions and are not diagnostic conclusions.
- **Terminology:** adds contextual phrase mappings for common patient wording such as sugar/BP, kidney/urinary concerns, heart blockage, low blood count, yellow eyes, fracture, fever, pain, and common symptoms. Basic negation is respected.
- **Knowledge provider:** extended source metadata for organization, publication/update date, topic, evidence type, version, URL, and review date. The existing empty provider remains empty; it does not claim source verification.
- **LangGraph:** adds `analyze_clinical_context` between report context construction and answer generation. Lab parsing runs when retrieved context contains test parameters (or for report summaries); prescription parsing runs for medication questions or prescription-like summary context. Patient language analysis is supplied for the answer. The existing report retrieval continues to filter by both authenticated user ID and active session ID.
- **Response schemas:** adds typed internal Pydantic schemas for lab findings, prescriptions, symptoms, and combined analysis. The public chat request and SSE event shape remain unchanged.

## Files created

- `backend/app/schemas/medical_intelligence.py`
- `backend/app/services/laboratory_intelligence.py`
- `backend/app/services/prescription_intelligence.py`
- `backend/app/services/symptom_intelligence.py`
- `backend/app/services/medical_terminology.py`
- `backend/tests/test_phase2_intelligence.py`

## Files modified

- `backend/app/services/medical_qa.py`
- `backend/app/services/vector_store.py` (shared mandatory user/session filter helper)
- `backend/app/knowledge/provider.py`
- `backend/pyproject.toml` (include taxonomy JSON as package data)

Phase 1 files `medical_taxonomy.py` and `medical_taxonomy.json` are reused; no duplicate taxonomy was created. The pre-existing Phase 1 audit remains at `docs/medical-intelligence-audit.md`.

## Existing functionality and compatibility

- Reuses existing PyMuPDF/PaddleOCR output, including `--- Page N ---` markers; OCR and report processing were not replaced.
- Reuses Gemini, LangGraph, ChromaDB, PostgreSQL, Clerk, chat history, and session-scoped report retrieval.
- No endpoint payload, SSE event, database table, or migration changes.
- No frontend redesign or new dependency.

## Tests and validation

Commands run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q app tests
.\.venv\Scripts\python.exe -m ruff check app/schemas/medical_intelligence.py app/services/laboratory_intelligence.py app/services/medical_terminology.py app/services/symptom_intelligence.py app/services/prescription_intelligence.py app/services/medical_taxonomy.py app/services/medical_qa.py app/services/vector_store.py app/knowledge/provider.py tests
```

Results: **22 tests passed**, compilation passed, and targeted Ruff checks passed. Coverage includes 50 lab alias cases plus edge cases for missing ranges, incompatible units, unreadable values, range parsing, conflicting duplicates, and a numeric test name; 40 symptom phrases; 20 prescription lines plus unclear/missing instructions; 40 terminology phrases; 20 language cases; and 20 user/session filter pairs. Tests also compile the graph and exercise the deterministic context node.

The 20 isolation cases test the filter builder, not a live Chroma server or database. No Gemini, OCR worker, PostgreSQL, Cloudinary, or hospital-directory integration test was run. There was no pre-existing broader backend test suite in the inspected tree.

## Known limitations and pending modules

- This is extraction and phrase routing, not clinical interpretation, diagnosis, treatment, or a clinically validated NLP model. OCR layout or multi-column tables can still defeat line-based parsing; multi-line result/name relationships and some unit formats need more coverage.
- A laboratory value is not considered normal when its printed interval is absent. Unit conversion is intentionally not performed. Critical-value rules are unavailable and always report not assessed.
- Prescription parsing cannot validate handwriting, brand/generic equivalence, interactions, side effects, or dosage correctness. OCR text is never a substitute for checking the original prescription.
- The 25-sector list is a routing vocabulary, not a medical knowledge base. Synonyms and Kannada coverage remain limited; symptom analysis does not generate a disease differential.
- The provider has no configured corpus, so there are no independently verified medical-source citations. A licensed/reusable source set and clinical review are required for Phase 3.
- Frontend display of structured extractions, a physician inquiry docket, live database/Chroma authorization integration tests, and clinician-reviewed end-to-end evaluations remain pending.
- Synthetic unit tests do not establish medical accuracy or safety.

## Manual smoke test

1. Start the backend using the existing environment and open a chat with a processed synthetic report containing lines such as `Creatinine: 1.1 mg/dL (0.6 - 1.2)` and `HbA1c: 7.1 % (4.0 - 5.6)`.
2. Ask “Which values are outside the reference interval?” Verify that the answer cites the report and that any extracted status comes from that report's printed range.
3. Ask “What medicines are listed?” with a synthetic prescription containing `Tab. Example 250 mg BD after food for 5 days`. Verify that extracted text is described as requiring confirmation and that no generic or unprinted instruction is invented.
4. Ask in Romanized Kannada, for example `Nange fever ide`, and confirm the response follows the chat's saved language mode. In auto mode, mixed Romanized English/Kannada may be classified bilingual.
5. Use two synthetic users and two sessions to verify that report retrieval returns only the active user's active-session excerpts. The included unit tests validate filter construction only; a live integration check is still needed.
