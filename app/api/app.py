"""FastAPI Application Factory for Indian Stock Market Prediction System.

Configures FastAPI application instance, exception handling, logging, and route mounting.
"""

import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.api.schemas import ErrorDetail, ErrorResponse
from app.core.config import get_settings
from app.core.schemas import ValidationError

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="Indian Stock Market Directional Prediction API",
        description=(
            "REST API providing directional stock forecasts, multi-agent ensemble synthesis, "
            "immutable historical tracking, and macroeconomic/regulatory event monitoring."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # -----------------------------------------------------------------------
    # Exception Handlers
    # -----------------------------------------------------------------------

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle Pydantic schema validation errors with structured JSON response."""
        errors = exc.errors()
        first_msg = errors[0].get("msg", "Validation error") if errors else "Invalid request body"
        field_loc = " -> ".join(str(l) for l in errors[0].get("loc", [])) if errors else "payload"

        error_resp = ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message=f"Validation failed on {field_loc}: {first_msg}",
                details=[{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in errors],
            )
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_resp.model_dump(),
        )

    @app.exception_handler(ValidationError)
    async def domain_validation_exception_handler(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        """Handle domain-level validation errors (app.core.schemas.ValidationError)."""
        error_resp = ErrorResponse(
            error=ErrorDetail(
                code="DOMAIN_VALIDATION_ERROR",
                message=str(exc),
            )
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_resp.model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        """Handle explicit HTTP exceptions."""
        error_resp = ErrorResponse(
            error=ErrorDetail(
                code=f"HTTP_{exc.status_code}",
                message=str(exc.detail),
            )
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_resp.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Catch-all for unhandled exceptions without leaking stack traces or internal secrets."""
        logger.error("Unhandled API exception on %s: %s", request.url.path, exc, exc_info=True)
        error_resp = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred. Please contact the administrator.",
            )
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_resp.model_dump(),
        )

    # -----------------------------------------------------------------------
    # Root & Information Endpoints
    # -----------------------------------------------------------------------

    @app.get("/", tags=["system"], summary="Root API Information")
    def get_root() -> Dict[str, Any]:
        """Return basic service metadata and documentation links."""
        return {
            "name": settings.app_name,
            "version": "1.0.0",
            "environment": settings.environment,
            "status": "running",
            "docs": "/docs",
            "health": "/api/health",
        }

    # Mount API router under /api
    app.include_router(api_router, prefix="/api")

    return app


# Default singleton ASGI application instance
app = create_app()
