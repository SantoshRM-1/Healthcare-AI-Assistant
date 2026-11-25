# MedAssist AI

Healthcare workspace built with Next.js 15, Clerk, FastAPI, SQLAlchemy, Alembic and PostgreSQL. It supports private medical report upload, OCR, report-scoped RAG with LangGraph and ChromaDB, grounded Gemini medical-document Q&A, report summaries, per-session language preferences and recommendations, voice transcription, user-entered-location hospital search, email sharing and chat export.

## Structure

```text
frontend/                 Next.js App Router application
  src/app/                Routes and layouts
  src/components/         Dashboard and reusable UI
  src/lib/                API client, query client, utilities
  src/store/              Zustand UI state
backend/                  FastAPI service
  app/api/v1/              Versioned REST endpoints
  app/core/                Settings, auth, errors
  app/db/                  Database setup
  app/models/              SQLAlchemy persistence models
  app/repositories/        Persistence boundary
  app/schemas/             Pydantic request/response contracts
  app/services/            Use cases, OCR, chunking, embeddings, retrieval, Gemini, voice and export
  app/workers/             PostgreSQL-queued report OCR worker
  alembic/                 Database migrations
```

## Setup

Requirements: Node.js 20+, Python 3.12+, PostgreSQL 15+.

1. Create a PostgreSQL database and copy `backend/.env.example` to `backend/.env`. Set `DATABASE_URL`, `CLERK_JWKS_URL`, and `CLERK_ISSUER` from the same Clerk instance used by the frontend; Cloudinary credentials; `GEMINI_API_KEY`; Resend `RESEND_API_KEY` and a verified `EMAIL_FROM`; and deployment-appropriate `CORS_ORIGINS`. The backend validates Clerk session-token signatures against the configured JWKS and issuer.
2. In `backend/`: `python -m venv .venv`, activate it, then install PaddlePaddle CPU for your platform following the [official installation guide](https://www.paddlepaddle.org.cn/documentation/docs/en/install/index_en.html). A typical Linux/macOS CPU install is `python -m pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/`. Then run `pip install -e '.[dev]'`, `alembic upgrade head`, and `uvicorn app.main:app --reload`. The API warms the configured Faster-Whisper model in a background startup task. Set `WHISPER_MODEL_SIZE` and `WHISPER_BEAM_SIZE` for the latency/accuracy tradeoff; set `NEXT_PUBLIC_VOICE_MAX_DURATION_SECONDS` to the same limit as `VOICE_MAX_DURATION_SECONDS` (default 180). For Kannada PDF glyphs, install a Kannada-capable TTF font and set `EXPORT_FONT_PATH` to its path.
3. Copy `frontend/.env.example` to `frontend/.env.local`; set `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and server-only `CLERK_SECRET_KEY` from the same Clerk instance configured in the backend. Keep `NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in`, `NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up`, and both fallback redirect URLs set to `/dashboard`; set `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`. Keep `.env.local` and `backend/.env` out of Git and restart the Next.js dev server after changing them.
4. In `frontend/`: `npm install`, then `npm run dev`. Visit `http://localhost:3000`.
5. The FastAPI lifespan starts a PostgreSQL queue consumer automatically. PaddleOCR initializes only when a scanned page needs OCR. For additional capacity, run dedicated replicas with `python -m app.workers.reports`; PostgreSQL `SKIP LOCKED` coordinates consumers.
6. For local development the default Chroma `PersistentClient` stores its data in `backend/.chroma`. For multi-instance deployments, run a protected Chroma server and set `CHROMA_HTTP_HOST`, `CHROMA_HTTP_PORT`, `CHROMA_SSL`, and the server's configured auth header/token. Chroma documents its local persistent client for development and server-backed clients for production.

Clerk sign-in and sign-up routes are `/sign-in` and `/sign-up`, provided by Clerk's hosted components. Unauthenticated requests to `/dashboard` go to sign-in and preserve the requested destination; sign-in and sign-up default to `/dashboard` when no destination was specified. Configure Google as a social connection in Clerk Dashboard if you want to offer social sign-in.

## API

All routes are under `/api/v1`. Authenticated requests use a Clerk bearer token. `GET /users/me`, chat/session/message routes, and reports routes remain available. AI routes include `POST /ai/chat` (SSE response; JSON body `{ "session_id": "...", "question": "..." }`), `POST /ai/report-summary`, `POST /ai/recommendations`, `POST /ai/doctor-recommendation`, and `POST /ai/language-mode` (body `{ "session_id": "...", "mode": "english|kannada|bilingual|auto" }`). `GET /memory/session/{id}` returns memory for that owned chat only. Language mode and structured memory are isolated per chat; auto mode detects English, Kannada, or mixed input. Recommendation history is also persisted by session. `GET /reports/{id}/summary` returns the saved structured report summary.

Medical recommendations retrieve report chunks before using Gemini for cautious educational suggestions. Doctor suggestions use the extensible specialty map in `backend/app/services/recommendations.py`. Responses include report sources when available and always include a clinician-care disclaimer; the system does not diagnose, prescribe, or instruct a user to change treatment.

Voice transcription is `POST /ai/voice` with multipart `session_id` and `file`; the browser shows recording/transcription/thinking stages and auto-stops at the configured duration. The API keeps one warmed Faster-Whisper instance per process; it verifies chat ownership and accepts short browser audio recordings. Transcribed text is then sent through the existing `/ai/chat` flow. Browser speech synthesis powers the optional Listen action. Hospital search is `POST /ai/hospital-recommendation`; the user supplies city, region, and local area. It uses only the PostgreSQL hospital directory and report/session context, without GPS or map services. Maintain directory data with a CSV containing `name,city,specialization,address,phone,website,rating`, then run `python -m app.scripts.import_hospitals path/to/hospitals.csv` from `backend/`. A blank import template is at `backend/data/hospitals.template.csv`; verify directory records and ratings with their source before importing.

`POST /share/email` sends a user-requested patient chat summary through Resend. Configure a verified sender and keep the Resend key server-side. It includes chat turns and citations, saved report summaries (when selected), and recommendation history. `GET /export/txt/{chat_id}` and `GET /export/pdf/{chat_id}` return private, owner-checked exports with chat history, citations, report summaries, and recommendation history. PDF text outside Latin-1 requires an appropriate font configured via `EXPORT_FONT_PATH` for full glyph preservation.

Reports support `POST /reports/upload?session_id=...` (multipart `file`), `GET /reports?session_id=...`, `GET /reports/{id}`, owner-scoped `GET /reports/{id}/debug`, `DELETE /reports/{id}`, `POST /reports/{id}/retry` (failed jobs only), and `GET /reports/{id}/preview`. Preview/downloads are proxied through the API after ownership checks; Cloudinary originals are uploaded as authenticated assets. Report uploads are limited to 20 MB, PDFs to 100 pages, and images to 40 megapixels by default. These limits can be adjusted in `backend/.env`.

OCR and indexing jobs are queued in PostgreSQL via `uploaded_reports.processing_status`. API uploads return after Cloudinary and PostgreSQL persistence; the separate worker extracts text and indexes in the background. The UI polls every two seconds and shows queued, extracting-text, embedding, and ready stages, with an owner-checked retry action for failed jobs. Run `alembic upgrade head` to add `processing_stage`. Workers atomically claim jobs with `FOR UPDATE SKIP LOCKED`; stale processing leases are recoverable after worker restarts, and transient failures are retried up to `REPORT_PROCESSING_MAX_ATTEMPTS`. Chunks carry `report_id`, `user_id`, and `session_id` metadata. Every retrieval filters by both authenticated user and active chat before any chunk is passed to Gemini. Report deletion removes its Chroma vectors as well as the source file and database row. The API runs a queue-consumer task automatically; dedicated OCR worker processes can be added to scale processing. OpenAPI docs are at `/docs`.

Gemini 2.5 Flash is configurable with `GEMINI_CHAT_MODEL` (default `gemini-2.5-flash`); embeddings use `gemini-embedding-001` with separate retrieval document/query task types. Google currently restricts access to Gemini 2.5 models for some new API users, so confirm the model is enabled on your account before launch.

Report-processing logs include upload, per-page OCR, embedding, Chroma insert, and end-to-end durations. Voice logs include model warm-up and transcription duration. These timings are emitted by each API/worker process and should be collected from both services.

## Production notes

Set strong unique secrets, configure CORS to the deployed frontend origin, use managed PostgreSQL with TLS and backups, run migrations as a release step, and place the API behind TLS and a trusted proxy. Clerk JWTs are verified against JWKS including issuer, expiry and subject. Keep Cloudinary and Gemini credentials server-side. OCR text, summaries, and embeddings are sensitive health information: use provider accounts and deployment regions appropriate to your privacy requirements, and cover PostgreSQL, Cloudinary, Google AI, and Chroma with the same access-control, retention, deletion, and incident policies. `gemini-2.5-flash` remains available, but Google currently recommends newer models for new projects and limits some account access. Chroma's local persistent client is for development; use its server-backed or cloud client for production replicas.
