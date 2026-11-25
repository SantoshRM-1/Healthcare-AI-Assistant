import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.db.session import engine
from app.services.voice_transcription import warm_whisper_model
from app.workers.reports import run as run_report_worker
from app.workers.medical_knowledge import run as run_knowledge_worker

logger = logging.getLogger(__name__)


def _background_worker_finished(task: asyncio.Task) -> None:
    task_name = task.get_name()
    if task.cancelled():
        logger.info("BACKGROUND WORKER STOPPED task_name=%s reason=application_shutdown", task_name)
        return
    error = task.exception()
    if error:
        logger.error("BACKGROUND WORKER TASK EXITED unexpectedly task_name=%s", task_name, exc_info=(type(error), error, error.__traceback__))
    else:
        logger.error("BACKGROUND WORKER TASK EXITED unexpectedly without an exception task_name=%s", task_name)


@asynccontextmanager
async def lifespan(_: FastAPI):
    warm_task = None
    report_worker_task = None
    knowledge_worker_task = None
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database health check passed during app startup")
        # Do not hold HTTP readiness on a potentially large model download/load.
        async def warm_models() -> None:
            for name, warm in (("whisper", warm_whisper_model),):
                try:
                    await asyncio.to_thread(warm)
                except Exception:
                    logger.exception("Background model warm-up failed for %s; first request will attempt initialization", name)

        warm_task = asyncio.create_task(warm_models(), name="warm-ai-models")
        report_worker_task = asyncio.create_task(run_report_worker(), name="report-queue-worker")
        report_worker_task.add_done_callback(_background_worker_finished)
        logger.info("REPORT WORKER TASK STARTED task_name=report-queue-worker")
        knowledge_worker_task = asyncio.create_task(run_knowledge_worker(), name="medical-knowledge-worker")
        knowledge_worker_task.add_done_callback(_background_worker_finished)
        logger.info("MEDICAL KNOWLEDGE WORKER TASK STARTED task_name=medical-knowledge-worker")
    except Exception:
        logger.exception("Database health check failed during app startup")
        raise
    try:
        yield
    finally:
        tasks = [task for task in (warm_task, report_worker_task, knowledge_worker_task) if task and not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])
install_error_handlers(app)
app.include_router(v1_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        logger.exception("Health check failed while probing the database")
        raise RuntimeError(f"Database unavailable: {exc}") from exc
