# Phase 4 — Advanced Medical AI, RAG, Memory, and Kannada

## Implementation summary

Phase 4 builds on the Phase 1 routing taxonomy and emergency-first handler, Phase 2 report parsers and language normalization, and Phase 3 approved-reference retrieval. It keeps the current Gemini Developer API client, LangGraph graph, report Chroma collection, verified-knowledge Chroma collection, PostgreSQL memory, Clerk ownership checks, API and SSE contract. No migration or new runtime dependency was added.

### Query understanding and retrieval

- Added `medical_query.py` with deterministic intent routing for report explanations/summaries, lab questions, prescriptions, nutrition, precautions, symptoms, specialist/hospital questions, terminology, follow-ups, and conversational messages.
- Added medical query aliases for supported English, Kannada-script, and Romanized Kannada terms such as haemoglobin/Hb, creatinine/renal function, blood sugar/HbA1c, thyroid/TSH, blood pressure, urinary burning, kidney stones, abdominal pain, and fever. The original wording and values are preserved; aliases are search aids only.
- Patient report search now requests up to three times the configured top K under the existing authenticated user and active session filter, applies the existing distance cutoff, deduplicates identical excerpts, and applies a bounded lexical overlap tie-break to semantic distance. Verified-reference search uses the same tie-break after its PostgreSQL approval/version/hash validation. No cross-encoder or external reranking dependency was introduced.
- Small talk skips patient and knowledge retrieval. Report-summary prompts do not trigger general-reference retrieval. Follow-up queries can use recent user messages plus the existing same-session memory fields (`last_topic`, reported symptoms, diagnoses).
- Conversation text supplied to the graph is capped at 12 messages, 6,000 characters total, and 1,400 characters per message. Older details are represented only by the existing structured session memory; no generated memory summary is treated as evidence.
- Report answer instructions now require stating a date when one is visible and avoid describing dated older results as current. Report and medical-reference citations remain separate.

### Language and safety

- Reused the persisted English/Kannada/Bilingual selector and current Gemini response-language instructions. SSE uses UTF-8 JSON with Kannada Unicode preserved. Expanded auto-detection for common Romanized Kannada phrases and emergency wording; mixed Kannada-English remains eligible for bilingual mode.
- Expanded deterministic emergency phrase matching for Kannada and Romanized Kannada breathing and stroke warning signs. The API's existing emergency branch still executes before Gemini and report/reference retrieval and does not depend on a provider key.
- Kannada PDF export no longer silently substitutes missing glyphs. `EXPORT_FONT_PATH` must identify a TTF font that contains the Kannada characters in the export. If it is absent or unsuitable, export returns a readable service error; TXT export remains UTF-8.
- Existing report analysis, prescription extraction, food/doctor/hospital handlers, safety prompts, and personal report/session filters were reused rather than duplicated.

### Evaluation framework and results

- Added a synthetic, non-patient fixture at `backend/tests/fixtures/phase4_evaluation.json` with 13 routing/language/emergency cases, including English, Kannada script, Romanized Kannada, mixed language, report interpretation, food, prescription, symptoms, hospital, follow-up, and emergencies. It intentionally has no expected source IDs because no approved corpus is present.
- Added `score_retrieval` and `mean_retrieval_scores` for Precision@K, Recall@K, and MRR over a future labeled retrieval set. A synthetic unit case verifies the metric math. A separate toy reranker case verifies distance filtering, lexical tie-breaking, and duplicate removal.
- The 13 fixture cases passed the deterministic intent/language/emergency checks. This is not an end-to-end retrieval benchmark. There is no labeled approved-reference dataset here, so no baseline/improved Precision@K, Recall@K, MRR, citation-accuracy, or latency claim is made. A meaningful benchmark needs a reviewed corpus and human-labeled relevant passage IDs, including Kannada and Romanized Kannada queries.
- Model answer fluency and clinical correctness were not measured: no live Gemini generation, PostgreSQL/Chroma integration, Cloudinary/OCR processing, or clinician review was run in this phase.

## Fine-tuning feasibility

The application currently creates the Google Gen AI client with `GEMINI_API_KEY`, i.e. the Gemini Developer API path. Google's current Gemini API tuning page says that no model is available for fine-tuning through the Gemini API/AI Studio. Google's Gemini Enterprise Agent Platform documentation lists supervised tuning for `gemini-2.5-flash`. Thus tuning is a possible separate Vertex/Agent Platform project, but is not available through this application's current API-key client without a provider/auth/deployment migration. Sources: [Gemini API model tuning](https://ai.google.dev/gemini-api/docs/model-tuning), [Agent Platform supervised tuning](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/tuning/supervised-tuning), [supported tuning models](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/tuning).

No fine-tuning job was created. Do not send patient reports to training. Before any future tuned model, prepare expert-authored, appropriately licensed and de-identified English, Kannada-script, Romanized Kannada, and bilingual examples; split train/validation/test data by source/patient to prevent leakage; obtain clinical and privacy review; evaluate safety, citation behavior, language parity, and regressions; then run a gated deployment comparison. Fine-tuning can adjust response behavior but does not replace retrieval for current medical facts or approved references. Kannada quality must be independently evaluated; this implementation's synthetic tests do not establish fluency.

## Files changed

- Added `backend/app/services/medical_query.py` and `backend/app/services/rag_evaluation.py`.
- Updated `backend/app/services/medical_qa.py`, `backend/app/services/vector_store.py`, and `backend/app/services/medical_knowledge_store.py` for intent-aware multilingual query expansion, scoped retrieval, reranking, compact context, greetings, and dated-evidence instructions.
- Updated `backend/app/api/v1/routes/ai.py`, `backend/app/services/session_memory.py`, and `backend/app/api/v1/routes/platform.py` for bounded same-session context, persistent reported symptom context, expanded deterministic emergency terms, and explicit Kannada PDF-font errors.
- Updated `backend/app/services/chat_export.py` to reject Kannada PDF output if a configured TTF lacks required glyphs.
- Added `backend/tests/test_phase4_retrieval.py` and `backend/tests/fixtures/phase4_evaluation.json`.

## Validation

- Full backend unit suite: **42 passed**.
- Python compilation: **passed**.
- Ruff focused checks for the changed services/routes/tests: **passed**.
- `git diff --check`: **passed** (Git emitted only existing CRLF conversion notices).
- Frontend production build was attempted but Next.js failed writing `.next/server/app/start-program` with Windows `EPERM`. Phase 4 made no frontend source changes; this build result does not verify the UI.
- Live PostgreSQL and Chroma retrieval, Gemini generation in all three response modes, actual Kannada PDF rendering with a supplied font, and report-upload-to-citation integration remain unverified. No corpus or live credentials were used for tests.

## Manual validation instructions

1. Apply the existing Phase 3 migration and configure a designated `KNOWLEDGE_ADMIN_CLERK_IDS` administrator.
2. Ingest and approve permitted reference documents and a synthetic report, then verify both retrieval stores return only their own citation type.
3. In one chat, ask about a report value in English, Kannada script, Romanized Kannada, and bilingual mode; follow with “what does it mean?” and a food question. Check values, units, citations, and the selected language.
4. In another chat, repeat a context-free follow-up and verify it does not inherit the first chat's medical context.
5. Test emergency examples in English, Kannada, and Romanized Kannada with Gemini disabled; verify direct urgent guidance and no retrieval delay.
6. Set `EXPORT_FONT_PATH` to a licensed Kannada-capable TTF, export a Kannada conversation to PDF, and visually inspect all glyphs. Confirm TXT is UTF-8.
7. Create a labeled retrieval set from the approved corpus and compute baseline and reranked metrics with `rag_evaluation.py` before claiming ranking gains.

## Remaining work

- There is still no approved general-medical corpus, so clinical knowledge answers requiring such references will fail closed or state the evidence limitation.
- Intent and alias rules are deterministic coverage aids, not a trained multilingual classifier. Spelling, dialect, complex mixed-language queries, and more medical abbreviations need labeled evaluation and iterative additions.
- The reranker is a lightweight lexical tie-break only; no evidence shows it improves production retrieval quality until a real labeled evaluation set is run.
- The local database connection stalled on a read-only revision check during the previous Phase 3 validation; apply and verify the migration on the running database before using the new verified source workflow.
- Kannada response instructions are prompt-level and API generation has not been exercised here. Human review is required before making clinical quality or Kannada fluency claims.
