# Phase 3 — Verified Medical Knowledge Base

## Architecture implemented

Phase 3 adds a separate, administrator-curated knowledge pipeline alongside the existing patient report pipeline. It does not replace the existing Clerk authentication, patient report OCR, report collection, report filters, or chat history behavior.

The knowledge flow is:

1. An administrator registers a source. It is saved as `pending_review`.
2. An administrator uploads an original PDF, DOCX, TXT, Markdown, JSON, or CSV file. The private original is stored in Cloudinary and a version record plus extraction job are committed to PostgreSQL.
3. The PostgreSQL-backed knowledge worker downloads the private original, extracts text (PDFs use the existing PyMuPDF/PaddleOCR path), and marks the version `ready_for_review`.
4. An administrator reviews the source license/provenance and document text. Source approval and document-version approval are separate actions.
5. Only an approved source and explicitly approved document version can be queued for indexing. The worker chunks text with page/heading context, creates embeddings using the existing Gemini embedding configuration, and writes to `medassist_verified_medical_knowledge_v1`.
6. The new version becomes active only after its Chroma upsert and PostgreSQL chunk records complete. A previously active version remains available while a replacement is processing.
7. Chat retrieval searches only this collection when the question (or its recent same-session context) appears to need medical knowledge. The retrieved version, source, document, vector ID, and chunk hash are revalidated against PostgreSQL before use. Report retrieval remains in `medassist_report_chunks_v1` with the existing user/session filter.
8. The LangGraph workflow supplies report excerpts and approved medical excerpts in separate labeled contexts. The SSE stream uses the existing `citations` event for report citations and a separate `medical_citations` event for reference citations. Saved messages keep the two citation types distinguishable, and the chat displays source title, publisher, section, page, and source link.

When no approved reference is available for a medical question, the graph returns a clear limitation and does not ask Gemini to answer from model memory. Small talk and nonmedical questions retain the existing behavior.

## Source categories and provenance

The registry stores publisher/title/URL/type, one of the 14 supported medical categories, topic, one or more taxonomy-backed specialties, jurisdiction, source and publication dates, source version, retrieval/review dates, language, license/permission basis, review state, and reviewer identity. The existing 25-sector taxonomy is used to validate specialty metadata; it is routing vocabulary, not itself an approved clinical reference.

The app intentionally ships with **no approved medical sources or documents**. Public availability alone is not approval to reproduce or embed content. For example, WHO states that many publications use a noncommercial Creative Commons license and that third-party content may have separate rights ([WHO copyright policy](https://www.who.int/about/policies/publishing/copyright), [WHO open-access policy](https://www.who.int/about/policies/publishing/open-access)). ICMR's policy also distinguishes ICMR material from third-party materials ([ICMR copyright policy](https://www.icmr.gov.in/copyright-policy)). A curator must verify the actual document's terms and the application's permitted use before approval.

## Database migration

Added Alembic revision `0012_verified_medical_knowledge`, after `0011_report_processing_metrics`. It creates:

- `medical_sources`
- `medical_knowledge_documents`
- `medical_knowledge_document_versions`
- `medical_knowledge_chunks`
- `medical_knowledge_reviews`
- `knowledge_ingestion_jobs`

The migration includes status check constraints, source/document/version foreign keys, duplicate hash and version-label constraints, retrieval/queue indexes, a one-active-version-per-document partial unique index, and a review-target integrity constraint. It is additive and does not alter report/chat tables.

## Admin API

All `/api/v1/knowledge/*` endpoints require a valid Clerk token and a Clerk user ID in `KNOWLEDGE_ADMIN_CLERK_IDS`. The allow-list is empty by default and fails closed; Clerk public/user metadata does not grant administrator privileges.

- `POST /api/v1/knowledge/sources` — register a pending source.
- `GET /api/v1/knowledge/sources` — list source registry entries.
- `POST /api/v1/knowledge/sources/{source_id}/review` — approve, reject, or retire a source; rejection/retirement deactivates its approved versions.
- `POST /api/v1/knowledge/documents` — multipart upload; fields: `source_id`, `title`, `version_label`, optional `document_id`, and `file`.
- `GET /api/v1/knowledge/documents?source_id=...` — list documents.
- `GET /api/v1/knowledge/documents/{document_id}` — list versions.
- `GET /api/v1/knowledge/versions/{version_id}` — inspect source and extracted text (review text is capped at 100,000 characters in this response).
- `GET /api/v1/knowledge/versions/{version_id}/original` — authorized redirect to a short-lived private Cloudinary URL.
- `POST /api/v1/knowledge/versions/{version_id}/review` — approve, reject, or retire a version. Approval requires an approved source and completed extraction.
- `POST /api/v1/knowledge/versions/{version_id}/reindex` — queue idempotent indexing of an approved version.
- `GET /api/v1/knowledge/jobs/{job_id}` — inspect extraction/index job state.

Supported uploaded reference files are PDF, DOCX, TXT, Markdown, JSON, and CSV. JSON/CSV support covers controlled structured datasets or permitted API snapshots supplied by a curator; the application does not scrape publisher websites or fetch arbitrary URLs.

## Configuration and operation

Add to the backend environment (never commit real secrets):

```dotenv
KNOWLEDGE_ADMIN_CLERK_IDS=user_xxx,user_yyy
KNOWLEDGE_INGESTION_MAX_ATTEMPTS=5
KNOWLEDGE_MAX_DOCUMENT_SIZE_MB=20
KNOWLEDGE_MAX_PDF_PAGES=250
KNOWLEDGE_DEFAULT_JURISDICTION=IN
```

Install the backend dependencies using the repository's existing `backend/pyproject.toml`, apply the migration, and start FastAPI as usual. The app lifespan starts the knowledge worker next to the existing report worker. In development, the administrator can use the authenticated API through `/docs`; no new patient-facing admin dashboard was added.

For each new reference: register the source and enter the license basis; review and approve the source; upload the file; wait for extraction; inspect the original and extracted text; approve the version; poll `GET /knowledge/versions/{id}` until `processing_status` is `indexed`. A version in `ready_for_review` is not searchable. Retiring/rejecting a source or version immediately excludes it through the PostgreSQL retrieval gate even if old Chroma vectors remain.

## Files created or modified for Phase 3

- Models and schema: `backend/app/models/medical_knowledge.py`, `backend/app/models/__init__.py`, `backend/app/schemas/medical_knowledge.py`
- Migration: `backend/alembic/versions/0012_verified_medical_knowledge.py`
- Admin API and authorization: `backend/app/api/v1/routes/medical_knowledge.py`, `backend/app/api/v1/router.py`, `backend/app/core/auth.py`, `backend/app/core/config.py`
- Ingestion and search: `backend/app/services/medical_knowledge_documents.py`, `backend/app/services/medical_knowledge_store.py`, `backend/app/services/medical_knowledge_citations.py`, `backend/app/knowledge/provider.py`, `backend/app/knowledge/policy.py`, `backend/app/workers/medical_knowledge.py`
- Integration and runtime: `backend/app/services/medical_qa.py`, `backend/app/services/vector_store.py`, `backend/app/services/report_storage.py`, `backend/app/main.py`, `backend/.env.example`
- Citation display and test coverage: `frontend/src/components/ai-chat-panel.tsx`, `backend/tests/test_verified_knowledge.py`

## Validation results

- Python bytecode compilation for backend app, tests, and migration: **passed**.
- Full backend unit suite: **32 passed**, including the new verified-knowledge tests and existing medical-intelligence tests.
- Ruff focused checks for Phase 3/import correctness: **passed**. A repository-wide Ruff run reports pre-existing lint findings across unrelated and existing files; those were left untouched.
- PostgreSQL SQLAlchemy DDL compilation for all six new tables: **passed**. This compiles the model DDL; it is not a live database migration.
- Frontend Next.js production build: **passed**.
- Alembic recognizes `0012_verified_medical_knowledge` as the head revision, and SQLAlchemy PostgreSQL DDL compilation passes for the new tables. A live `alembic current` probe did not return because the configured PostgreSQL connection was unreachable or stalled; migration execution and live PostgreSQL/Chroma/Cloudinary/Gemini/OCR integration remain unverified. No real source corpus or test patient data was used.

## Known limits and production checklist

- The source corpus is empty until an authorized administrator supplies and reviews documents. Medical answers that need general references will state that limitation until eligible sources have been approved and indexed.
- The worker runs in the FastAPI process and uses PostgreSQL row locks/leases. For multi-instance production, run a dedicated worker process/service from the same code rather than starting one worker per API replica; `SKIP LOCKED` prevents concurrent job claims.
- Configure a durable, private Chroma deployment for multiple hosts; the existing local persistent Chroma path is suitable only for one host/development.
- Before production: run `alembic upgrade head` against the target PostgreSQL database; configure private Cloudinary credentials, `GEMINI_API_KEY`, Clerk issuer/JWKS, Chroma endpoint/token, and the admin ID allow-list; upload one permitted synthetic reference; exercise extraction/review/index/search/retire; confirm the source card and SSE flow; and test worker restart/retry behavior.
- Retrieval and citation structure is tested with synthetic fixtures; clinical answer quality cannot be evaluated until approved, licensed reference content is supplied and reviewed.
