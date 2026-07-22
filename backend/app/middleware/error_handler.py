"""
Global exception handler — converts all AppErrors and unexpected exceptions
into a consistent JSON response shape.
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core import AppError

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the AppError and catch-all exception handlers to `app`."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred.", "status_code": 500},
        )
