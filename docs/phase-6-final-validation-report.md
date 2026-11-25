# Phase 6 — Final Validation Report

**Validation date:** 2026-11-16  
**Scope:** Static audit, synthetic tests, local build/type checks, offline migration generation, and configured-service availability probes.  
**Patient data:** No real patient files or identifiable patient examples were used.

## Executive result

The project is **not production-ready for patient-facing deployment yet**. The frontend builds, the API imports, the offline migration chain reaches revision `0012_verified_medical_knowledge`, and the full backend test suite passes. However, live PostgreSQL was unreachable, the approved medical reference corpus is empty, the hospital directory could not be inspected, and no live Clerk/Gemini/Cloudinary/Resend/Chroma workflow was run. Clinical accuracy and Kannada generation quality have not been validated by clinicians or Kannada reviewers.

Phase 6 fixed four code issues found during the audit:

1. SQLAlchemy exception messages were returned to API clients. Responses now return a generic retry message while server logs retain the exception type/traceback. SQLAlchemy engine parameter logging is hidden.
2. Authentication/chat/report logs included Clerk IDs, chat titles, report names, and Cloudinary identifiers. These unnecessary values were removed from routine logs.
3. The Alembic logging config had an indented `datefmt` line treated as part of the log format, causing a formatter traceback for every migration step. The config is corrected; offline SQL generation completes without formatter errors.
4. Emergency phrase coverage missed “swallowed poison” and “severe bleeding”; both now route to emergency guidance. Kidney-stone red-flag guidance now includes India’s 112 number.

## Project feature inventory

“Implemented and tested” below means deterministic/unit or build checks only unless explicitly called live; it does not imply clinical validation or successful external integration.

| Area | Current status | Evidence / limitation |
|---|---|---|
| Next.js dashboard, landing, about, procedures, sign-in/up routes | Implemented and build-tested | Next.js 15 production build passed; browser interaction and mobile/accessibility audit not run. |
| Clerk sign-in/sign-out and client session | Implemented, not live-tested | Clerk env values exist; no browser sign-in or sign-out round trip was exercised. |
| Clerk JWT verification and protected API | Implemented, partially tested | Missing bearer token returns 401 in a synthetic dependency test; live JWKS, expiry, and identity-sync tests blocked by unavailable services. |
| PostgreSQL models, foreign keys, indexes, migrations | Implemented, offline-validated | Alembic head is `0012_verified_medical_knowledge`; full offline SQL generation passed. Database TCP is unreachable, so current revision/schema/data and transaction behavior were not inspected. |
| Chat CRUD, history, messages, memory isolation | Implemented, not integration-tested | Ownership/session filters exist; live persistence, deletion, long-chat and cross-user tests need PostgreSQL. |
| PDF/image upload, Cloudinary, OCR, report worker | Implemented, not integration-tested | Static inspection confirms content/signature and size checks, ownership checks, queue worker, private Cloudinary storage and OCR paths. No live upload, OCR, or failure-recovery test was run. |
| Report RAG and citation scoping | Implemented, unit-tested, integration blocked | Retrieval-filter and ranking tests pass. PostgreSQL/Chroma and report-to-answer citation flow were not exercised. |
| Approved medical knowledge ingestion and retrieval | Implemented, blocked by data/services | Admin allow-list is unset and Phase 3 documents an empty corpus. No approved/rejected/retired live-source test was possible. |
| Laboratory, symptom, prescription and terminology intelligence | Implemented and synthetic-tested | Parsers/routing pass existing unit coverage; OCR layout variability and clinical correctness are not established. |
| English/Kannada/bilingual response path | Partially tested | Language detection, UTF-8 SSE, localization labels and emergency examples pass deterministic checks. Live Gemini language generation, natural grammar, and medical meaning were not reviewed. |
| Food, precautions, specialist and doctor-question guidance | Implemented, partially tested | Intent/specialist/food-name/question logic passes synthetic tests. Condition-specific recommendations depend on live Gemini and eligible reference data; not integration-tested. |
| Hospital recommendations | Implemented, blocked by directory inspection | SQL matching uses directory rows only and does not fabricate entries. PostgreSQL is unreachable, so row count, duplicates, completeness, specialty match, and ranking could not be verified. |
| PDF export | Implemented with configuration requirement | Code rejects lossy Kannada fallback. `EXPORT_FONT_PATH` is unset, so Kannada PDF export is not ready; PDF rendering was not run. |
| TXT export | Implemented, not integration-tested | UTF-8 generation path exists; no chat-backed export was run because PostgreSQL is unreachable. |
| Voice input | Implemented, not live-tested | Faster Whisper code and limits exist. No microphone, transcription, Kannada, or runtime model test was performed. |
| Voice output | Implemented in frontend, not live-tested | Browser speech synthesis path not exercised. |
| Email sharing | Implemented, needs configuration/testing | Resend key is present but `EMAIL_FROM` is absent. No provider request was sent; delivery must not be claimed. No export attachment flow is present. |
| Observability/error handling | Implemented, partially tested | Generic DB error response and privacy behavior are tested. Logs are not a centralized structured telemetry/alerting system. |
| Security and privacy | Partially reviewed | Owner guards, private file access, file validation and fail-closed knowledge-admin check exist. Rate limiting is absent; retention/account-erasure policy and dependency vulnerability scan are not verified. |
| Performance | Not benchmarked | No before/after latency, throughput, memory, Gemini, OCR, Chroma or SQL measurements were collected; no performance claim is made. |

## Tests and validation results

- `python -m compileall -q app tests`: **passed**.
- `python -c "import app.main"`: **passed** (PyMuPDF emits a deprecation warning for `fitz`).
- `python -m unittest discover -s tests`: **53 tests passed**.
- The 13-case Phase 4 intent/language/emergency fixture passed.
- The Phase 6 synthetic evaluation fixture contains **20 deterministic cases: 20 passed** across intent, language detection, emergency routing, lab parsing, negation, specialty routing, food-name recognition, prescription questions, and doctor questions. **Three live/configuration cases are marked blocked**, not passed: hospital directory, approved medical-reference retrieval, and Kannada PDF rendering.
- Focused Ruff checks on files changed for Phase 5/6: **passed** after import cleanup. A repository-wide Ruff run still reports pre-existing lint errors outside the focused set; see “Remaining issues.”
- `npm exec tsc -- --noEmit`: **passed**.
- `npm run build`: **passed** for Next.js 15.5.3; all routes generated successfully.
- `alembic heads` and `alembic history --verbose`: **passed**, one head at `0012_verified_medical_knowledge` with a linear chain from `0001_initial`.
- `alembic upgrade head --sql`: **passed** for offline DDL generation through `0012`; this did not connect to or modify PostgreSQL.
- `git diff --check`: **passed**; Git emits line-ending normalization notices for existing working-tree files.
- PostgreSQL TCP probe: **unreachable**. No migration was applied and no live row-count/foreign-key/ownership checks were attempted.
- Gemini/Cloudinary/Resend API calls: **not sent**. Presence of credentials alone is not integration validation and no paid/external calls were made.
- Live frontend-to-backend authenticated E2E, OCR, report retrieval, streaming generation, email delivery, and hospital search: **not run**.

## Synthetic medical and language evaluation

The synthetic case list is stored at `backend/tests/fixtures/phase6_synthetic_evaluation.json`. Each case records input, available evidence, expected behavior, actual deterministic behavior, language, safety constraint, citation expectation, status, and failure category. Clinical recommendations are not scored as medically correct from plausibility; there is no clinician-reviewed expected-answer set.

Emergency samples include severe chest pain, breathing difficulty, stroke wording, severe bleeding, severe allergic reaction, suspected poisoning, and Kannada/Romanized Kannada examples. The tested deterministic path returns 112 and bypasses Gemini/RAG. Coverage is still phrase-based and does not establish sensitivity for all patient wording or dialects.

Kannada coverage in this run establishes parser/routing behavior and Unicode preservation only. It does **not** establish natural grammar, faithful translation, or clinically correct Kannada answers. A reviewed language dataset and qualified Kannada/clinical reviewers are required before asserting parity.

## Database, authentication, and privacy

- Migration metadata inspection confirms a single linear Alembic head and offline DDL generation. Live schema consistency is unknown because PostgreSQL was down.
- Route inspection confirms user/chat/report ownership checks in report and chat operations; report preview uses a short-lived authenticated Cloudinary URL and private/no-store response headers. Live cross-account access attempts remain untested.
- Knowledge administration uses a Clerk-ID allow-list and fails closed. The configured allow-list is empty, so no administrator can currently use the knowledge management endpoints.
- Normal chat/report logs no longer include user titles, filenames, Clerk IDs, or Cloudinary public IDs. SQLAlchemy binds are hidden from engine logs.
- User account erasure and data retention/backup purge policy are not implemented or verified. Deleting chats/reports invokes storage/vector cleanup, but durable backup retention is an operational policy not represented in code.
- The JWT signing-key lookup now returns 503 when Clerk’s JWKS service is unavailable and 401 for invalid tokens; the live outage/expiry cases were not exercised.

## Security findings

1. **High deployment concern: no API rate limiting.** Authenticated endpoints that invoke Gemini, embeddings, OCR, Whisper, exports, and email can be repeatedly invoked. Add shared infrastructure-backed limits before public production; an in-process limiter would not be reliable across multiple workers.
2. **High deployment concern: empty knowledge-admin allow-list.** This is safe/fail-closed but prevents source curation. Configure authorized IDs only after administrator review.
3. **Medium: HTTPS and trusted proxy enforcement are deployment responsibilities.** Configure TLS, secure headers, and forwarded-header trust at the edge; do not expose the development server directly.
4. **Medium: no dependency vulnerability scan was run.** Run an approved offline/CI dependency scanner against Python and npm lockfiles before release.
5. **Medium: no account deletion or explicit retention workflow was validated.** Define retention, user deletion, backup expiry and audit-log retention with the operator.
6. **Medium: local Chroma mode is single-host.** `CHROMA_HTTP_HOST` is unset. Use durable shared storage/service and authenticated network controls for multiple API/worker instances.
7. **No evidence of SQL injection or public report URL exposure was found in inspected query paths.** This is a source review finding, not a penetration test.

## Configuration and service availability

Only presence/availability was checked; secret values were not printed.

- Backend `.env` exists; Clerk issuer/JWKS URL, database URL, Gemini key, and Cloudinary credentials are present.
- PostgreSQL endpoint is unreachable from this workspace.
- `CHROMA_HTTP_HOST` is unset; configured local persistence directory exists. Its collection contents were not queried.
- Resend key exists, but `EMAIL_FROM` is unset.
- `EXPORT_FONT_PATH` is unset, blocking Kannada PDF output.
- `KNOWLEDGE_ADMIN_CLERK_IDS` is unset, so admin endpoints fail closed.
- The knowledge corpus is reported empty in the Phase 3 inventory; clinical reference retrieval cannot be evaluated.
- No real provider request or database migration was attempted.

## Performance and reliability

No actual latency baselines were collected, so no before/after values are reported. Existing logs include upload, OCR, embedding, vector insert, voice and Gemini-stage timers. The OCR model is lazily initialized; `warm_ocr_model()` exists but application startup currently warms Whisper only, so first scanned-report latency may include model initialization. Confirm with timings before changing startup behavior.

Reliability behavior observed in source includes worker retries/leases, upload byte/page limits, PDF/image signature checks, timeouts for Gemini/preview/Resend, report processing failure states, and clear API error mappings. These paths require fault-injection against configured services to verify operationally.

## Production readiness assessment

| Component | Status | Release condition |
|---|---|---|
| Frontend | Ready with limitations | Production build and TypeScript pass; still needs browser/mobile/accessibility E2E. |
| Backend | Ready with limitations | Import and unit suite pass; live DB and provider integrations remain untested. |
| Authentication | Needs testing | Run Clerk sign-in/out, expiry, JWKS outage, protected route and user isolation tests. |
| Database/migrations | Needs configuration/testing | Start PostgreSQL, apply `alembic upgrade head`, compare schema, exercise constraints and ownership. |
| Gemini | Needs testing | Use controlled synthetic prompts, timeout/rate-limit tests, citation and language checks; no live call in this audit. |
| ChromaDB | Needs configuration/testing | Confirm persisted collections, vector counts, backup/recovery, isolation, and multi-instance plan. |
| Approved medical corpus | Not ready | Curate and license sources, review/index them, and run cited retrieval evaluations. |
| Medical intelligence | Ready with limitations | Synthetic parser tests pass; clinical reviewer evaluation is absent. |
| Kannada | Needs testing | Unicode/routing passes; human language and medical review required. |
| Report upload/OCR | Needs testing | Exercise real synthetic PDFs/images through Cloudinary, worker, OCR and vectors. |
| RAG/citations | Needs testing | Run report-to-answer and approved-source E2E with isolated synthetic fixtures. |
| Hospital directory | Needs configuration | Populate and verify real records; inspect duplicates, specialties, addresses, phones and PINs. |
| Recommendations | Needs testing | Requires Gemini plus approved references; do not treat general model plausibility as validation. |
| PDF/TXT export | Ready with limitations | TXT needs an E2E test; Kannada PDF needs a licensed font configured and visual check. |
| Voice | Needs testing | Configure/warm model and test microphone, limits, errors, English/Kannada. |
| Email | Needs configuration/testing | Set sender/from identity and verify a controlled Resend delivery; attachment export is absent. |
| Privacy | Needs policy | Define retention, account deletion, backup expiry and operator access logging. |
| Security | Not ready | Add shared rate limiting, run vulnerability scan and deployment TLS/proxy review. |
| Performance | Needs testing | Measure representative end-to-end latency and load before tuning. |
| Monitoring | Needs configuration | Connect structured logs, error tracking, metrics and worker/database alerts. |

## Bugs fixed in Phase 6

- Prevented raw SQL/database exception text from reaching patients.
- Redacted unnecessary account/title/file/storage identifiers in logs and enabled SQL parameter redaction.
- Fixed Alembic formatter configuration and verified clean offline SQL generation.
- Expanded emergency phrase detection for severe bleeding and poison ingestion; included 112 in kidney-stone red-flag wording.

## Remaining issues and release checklist

- Full repository Ruff reports existing issues outside the focused changed files; clean those incrementally before enforcing repo-wide lint in CI.
- PostgreSQL needs to be started and verified before applying migrations or attempting hospital/report/chat integration tests.
- Set `EMAIL_FROM`, `EXPORT_FONT_PATH`, an administrator allow-list, and production Chroma host/token as applicable.
- Populate/verify the hospital directory and approved knowledge corpus; empty data must continue to return explicit limitations.
- Run signed-in browser E2E for Clerk, chat CRUD, report upload/status/OCR, chat SSE, source cards, exports, voice, and email.
- Run synthetic two-user/two-chat isolation and file preview authorization tests against a live database and Chroma store.
- Add shared API rate limits, TLS/proxy policy, dependency scan, retention/deletion policy, backup/recovery and monitoring before public deployment.
- Obtain qualified clinical and Kannada-language review. Do not describe this system as clinically validated or as a substitute for medical care.

