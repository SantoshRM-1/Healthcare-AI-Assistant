# MedAssist AI Medical Intelligence Audit

**Audit date:** 2026-11-16  
**Scope:** Existing frontend/backend implementation and the master engineering prompt.  
**Approach:** Read-only inspection before implementation. Existing working-tree edits were present and have been preserved.

> This document records the Phase 1 baseline audit. Phase 1 fixes and the Phase 2 medical-intelligence increment were applied afterward; see [phase-2-medical-intelligence-report.md](phase-2-medical-intelligence-report.md) for the current implementation and validation status.

> **Final validation update (2026-11-16):** Phases 1–5 have since added structured medical extraction, a provenance-aware but currently empty approved-source pipeline, multilingual retrieval, recommendations, and memory. Phase 6 verification and its current production-readiness assessment are in [phase-6-final-validation-report.md](phase-6-final-validation-report.md). The latest run passed 53 backend tests, TypeScript, and the Next.js production build, and generated Alembic SQL offline through revision 0012. PostgreSQL was unreachable, so migration execution, hospital-directory contents, and live integration remain unverified. The product is not yet production-ready for patient-facing use; the Phase 6 report lists the specific release blockers.

## 1. Current architecture

- Next.js 15 App Router provides the existing dark glass chat, report manager, language selector, citations, exports, and voice controls. No frontend change is needed for the first backend intelligence increment.
- Clerk JWT authentication is resolved by FastAPI dependencies. Chat, report, memory, and recommendation routes resolve the owner and/or active chat before using patient data.
- PostgreSQL uses SQLAlchemy async sessions and Alembic migrations through `0011_report_processing_metrics`.
- Report upload stores files in Cloudinary. A FastAPI background worker claims queued reports, retrieves the file, extracts native PDF text or OCR text, stores OCR text in PostgreSQL, chunks the report, calls Gemini embeddings, and upserts vectors into ChromaDB.
- The current Chroma collection is `medassist_report_chunks_v1`. Vector metadata includes report, user, session, page, and section IDs. Retrieval filters by authenticated user and active session; report citations are built from retrieved metadata.
- The LangGraph currently has three nodes: report-chunk retrieval, context construction, and Gemini answer generation. The API separately handles report summaries, food recommendations, doctor recommendations, hospitals, and emergency matching.

## 2. Existing functionality confirmed by source inspection

- Report processing has worker lease/retry/progress fields, extraction/indexing, error persistence, and timing logs.
- Native PDF text is preferred; pages without usable embedded text are OCRed. OCR work is limited by page/pixel settings and uses a bounded thread pool.
- Report chunks retain page/section metadata. Embeddings are batched and checked for missing vectors.
- Report retrieval and hospital/report queries are constrained to the active user's reports and session.
- Report summaries and recommendations use Pydantic structured output. Hospital records can be imported from CSV; the repository includes a CSV template.
- Language mode is stored on each chat session. Unicode Kannada is recognized; a limited number of Kannada symptom/specialty terms are mapped.
- Recent work already added kidney-stone-to-urologist matching and page-null citation handling. Those are useful targeted fixes, not a complete 25-sector knowledge system.

## 3. Problems and limitations

### High priority

1. **No verified medical knowledge provider exists.** General answers use Gemini's internal knowledge. Report-grounded answers retrieve only patient report chunks. There is no separate verified-source corpus/provider, provenance/version tracking, or distinct medical-source citation contract.
2. **Emergency detection is not a global pre-answer gate.** A small regex runs inside the hospital intent branch. Ordinary medical Q&A, food, and doctor flows can reach Gemini without the deterministic emergency check running first.
3. **Knowledge coverage is incomplete.** The specialist map covers a subset of sectors and terms; the 25-sector taxonomy, condition/symptom graph, lab catalog, prescription catalog, and regional/Romanized Kannada normalization are absent.
4. **No evaluation suite is present.** The backend tree has no `tests` package or medical evaluation harness. There is no retrieval, citation, multilingual, safety, or cross-session regression suite.

### Medium priority

5. **Lab interpretation is prompt-only.** There is no deterministic extraction/normalization for parameter, value, unit, reference interval, or high/low status. The report answer model can summarize OCR text, but the system does not validate unit compatibility or use printed lab ranges as structured facts.
6. **Prescription understanding is not a separate flow.** Prescriptions go through generic report RAG/summarization; medicine/strength/route/frequency/duration ambiguity is not represented as a dedicated validated extraction result.
7. **Romanized Kannada is not detected.** `detect_language` uses Kannada script and English/Kannada language words. Phrases such as “Nanage jwara ide” are classified as English unless a narrow downstream phrase happens to match.
8. **Intent matching remains fragmented.** A regex dispatcher in the route handles a few summaries/recommendation intents, while the LangGraph handles only general Q&A. Intent detection, emergency safety, and specialty matching do not share one normalized concept layer.
9. **Hospital availability depends on external data provisioning.** The CSV importer exists, but no verified directory records are included. A city/specialty match can therefore return no hospitals even when specialty detection works.
10. **Retrieval quality is not measured.** Retrieval uses one embedding query, top-k and a distance threshold; no evaluation dataset, reranker, report-level selection, or citation coverage checks exist.

### Lower priority

11. Several answer paths have different language/disclaimer/source formatting. Chat is free text; only some recommendation/summary outputs are schema-validated.
12. Session memory extracts some diagnoses/symptoms with regex and otherwise stores recommendation history; it is not a normalized clinical timeline and should remain context only, never diagnostic evidence.

## 4. Recommended implementation order

1. Preserve existing auth, report processing, Chroma collection, and UI.
2. Add a versioned taxonomy/synonym layer based only on the 25-sector list supplied in the prompt. Treat it as a routing lexicon, not clinical evidence.
3. Add a reusable, deterministic emergency gate before every generative/recommendation branch; route emergencies directly to localized safety guidance.
4. Add explicit patient-reported concept extraction and specialty matching. Keep patient-reported symptoms distinct from documented diagnoses; never promote an isolated lab result to a diagnosis.
5. Add a source-provider interface and separate patient-report citations from verified-medical-source citations. Only serve clinical guidance when verified content is configured; do not backfill absent evidence with model memory.
6. Add lab-result parsing that preserves source value/unit/reference range and reports “not assessed” when a range or conversion basis is absent.
7. Add separate prescription extraction with ambiguity flags, then integrate only after a sourced medication reference provider is configured.
8. Add deterministic unit tests for matching, safety, extraction, and isolation, followed by clinician-reviewed RAG evaluation cases. Do not generate fabricated reports or clinical expected answers to meet a case-count target.
9. Keep frontend changes limited to rendering source type and structured fields if/when backend contracts require them.

## 5. Files for the first incremental implementation

- `backend/app/services/medical_qa.py` — preserve report RAG; feed structured language/safety/context rather than replacing it.
- `backend/app/api/v1/routes/ai.py` — apply safety gate and normalized intent before dispatch.
- `backend/app/services/recommendations.py` — consume normalized reported concepts for food/specialty flow.
- `backend/app/services/hospital_recommendations.py` — consume specialty concepts while preserving existing directory filters.
- New `backend/app/knowledge/` modules — taxonomy, language normalization, source-provider contract, and safety rules.
- New backend tests — deterministic unit tests; no external Gemini/network calls.
- No initial database migration is necessary for a read-only bundled taxonomy/provider interface. Persisted verified records can be migrated once a licensed source corpus is selected.

## 6. Audit conclusion

The current application is a report-aware assistant foundation, not yet a complete medical intelligence platform. Its strongest boundaries are Clerk ownership, chat-session isolation, report OCR/indexing, and report citations. Its largest gap is the absence of a verified general medical knowledge layer and a global safety/semantic normalization stage. The safe next increment is deterministic taxonomy, multilingual concept normalization, and pre-generation safety; broader clinical interpretation must remain explicitly limited until sourced knowledge and reviewed evaluations are available.

## 7. First implementation increment

- Added the owner-supplied 25-sector and 250-condition vocabulary as a routing taxonomy. It is explicitly marked `taxonomy_only`; it contains no disease explanations, test interpretation, reference ranges, or treatment guidance.
- Added literal, negation-aware condition matching for specialist routing. It does not infer a diagnosis from a biomarker.
- Doctor and hospital recommendation paths now include recent user-authored messages from the active session, so a follow-up request can use symptoms described earlier in that same chat.
- Added Romanized Kannada language markers and food/doctor/hospital intent terms.
- Emergency detection now runs before ordinary chat branches, and emergency answers bypass Gemini.
- Added a provenance-bearing medical knowledge provider interface with an explicit empty implementation. The verified/licensed corpus must still be configured before external medical-source retrieval is enabled.
- Added six deterministic tests for intent/language detection, urgent routing, taxonomy coverage, singular matching, and negation.

## 8. Remaining work

This increment is not the complete clinical intelligence engine requested in the prompt. Structured report-field extraction, lab value parsing/interpretation, prescription parsing, symptom differential support, verified-source ingestion/retrieval, citations for medical sources, clinician-reviewed emergency rules, doctor question docket generation, and broad clinical evaluation remain pending. Hospital results still depend on operator-provided current directory records. The system must not be represented as clinically validated or as providing diagnosis or treatment.
