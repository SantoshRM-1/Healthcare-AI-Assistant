"""PostgreSQL-backed report OCR worker. Run one or more worker processes."""
import asyncio
import logging
import os
import uuid

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionFactory, engine
from app.services.report_processing import process_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLAIM_REPORT = text("""
    WITH candidate AS (
        SELECT id FROM uploaded_reports
        WHERE processing_attempts < :max_attempts
          AND (
               processing_status IN ('pending', 'queued')
            OR (processing_status = 'processing' AND processing_started_at < now() - interval '30 minutes')
            OR (raw_extracted_text IS NOT NULL AND indexed_at IS NULL AND processing_status = 'completed')
          )
        ORDER BY upload_date
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    UPDATE uploaded_reports AS report
       SET processing_status = 'processing', processing_stage = 'processing', processing_error = NULL,
           processing_started_at = now(), processing_attempts = report.processing_attempts + 1,
           updated_at = now()
      FROM candidate
     WHERE report.id = candidate.id
    RETURNING report.id
""")

FAIL_EXHAUSTED_LEASES = text("""
    UPDATE uploaded_reports
       SET processing_status = 'failed', processing_stage = 'failed',
           processing_error = COALESCE(processing_error, 'Worker lease expired after retry limit'),
           processing_started_at = NULL, updated_at = now()
     WHERE processing_attempts >= :max_attempts
       AND (
            (processing_status = 'processing' AND processing_started_at < now() - interval '30 minutes')
         OR processing_status IN ('pending', 'queued')
       )
""")


async def claim_report() -> uuid.UUID | None:
    async with SessionFactory() as session:
        params = {"max_attempts": settings.report_processing_max_attempts}
        failed = await session.execute(FAIL_EXHAUSTED_LEASES, params)
        result = await session.execute(CLAIM_REPORT, params)
        report_id = result.scalar_one_or_none()
        await session.commit()
        if failed.rowcount:
            logger.error("REPORT FAILED count=%d reason=retry_limit_or_expired_lease", failed.rowcount)
        if report_id:
            logger.info("REPORT PROCESSING STARTED report_id=%s claim_committed=true", report_id)
        return report_id


async def run() -> None:
    logger.info("REPORT WORKER STARTED pid=%d", os.getpid())
    last_idle_log = 0.0
    try:
        while True:
            try:
                report_id = await claim_report()
                if report_id is None:
                    now = asyncio.get_running_loop().time()
                    if now - last_idle_log >= 30:
                        logger.info("REPORT WORKER IDLE queue_scan=ok database_commit=ok")
                        last_idle_log = now
                    await asyncio.sleep(1.5)
                    continue
                logger.info("Processing report %s", report_id)
                await process_report(report_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Report worker iteration failed")
                await asyncio.sleep(5)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
