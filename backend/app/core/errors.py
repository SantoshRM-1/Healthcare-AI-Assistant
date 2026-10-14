import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception(
            "database request failed method=%s path=%s exception_type=%s",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        # Temporarily return the real exception so the database defect is visible.
        return JSONResponse(status_code=503, content={"detail": f"Database operation unavailable: {exc}"})
