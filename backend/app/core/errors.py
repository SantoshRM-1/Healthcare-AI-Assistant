import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def database_error_response(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(
        "database request failed method=%s path=%s exception_type=%s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc_info=(type(exc), exc, exc.__traceback__) if exc.__traceback__ else None,
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "A database operation is temporarily unavailable. Please retry."},
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(SQLAlchemyError, database_error_response)
