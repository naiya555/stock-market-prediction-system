"""FastAPI Application Factory for Indian Stock Market Prediction System.

Configures FastAPI application instance, exception handling, logging, and route mounting.
"""

import logging
import os
from pathlib import Path
import time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from app.api.routes import api_router
from app.api.schemas import ErrorDetail, ErrorResponse
from app.core.config import get_settings
from app.core.schemas import ValidationError

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    is_prod = settings.is_production()

    # Production safety checks
    if is_prod:
        if settings.debug:
            raise ValueError("APP_DEBUG cannot be enabled in production environment.")
        if not os.getenv("APP_CORS_ORIGINS"):
            raise ValueError(
                "APP_CORS_ORIGINS must be explicitly configured in production (cannot use local development defaults)."
            )
        if any(origin == "*" for origin in settings.cors_origins):
            raise ValueError(
                "Wildcard CORS origin '*' is strictly prohibited in production. Configure explicit trusted domain(s)."
            )
        for origin in settings.cors_origins:
            if origin.startswith("http://") and not any(h in origin for h in ("localhost", "127.0.0.1")):
                raise ValueError(
                    f"Insecure HTTP origin '{origin}' is strictly prohibited in production CORS settings (must use HTTPS)."
                )

    app = FastAPI(
        title="Indian Stock Market Directional Prediction API",
        description=(
            "REST API providing directional stock forecasts, multi-agent ensemble synthesis, "
            "immutable historical tracking, and macroeconomic/regulatory event monitoring."
        ),
        version="1.0.0",
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )

    # Configure CORS: Restrict to trusted origins and disable credentials (no cookie auth needed)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Defensive Security Response Headers & Operational Telemetry Middleware
    @app.middleware("http")
    async def add_security_headers_and_telemetry(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["X-Process-Time-Ms"] = str(duration_ms)
        # Operational telemetry: request method, path, HTTP status, and duration (ms)
        # Avoid logging query parameters, authorization headers, or request body to prevent data leaks
        logger.info(
            "HTTP %s %s -> %d (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

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
    # Static Assets & Web UI Mounting
    # -----------------------------------------------------------------------

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", tags=["system"], summary="Root API Information and Interactive Dashboard")
    def get_root(request: Request) -> Any:
        """Return basic service metadata, or serve web UI if requested by browser."""
        accept = request.headers.get("accept", "")
        if "text/html" in accept and "application/json" not in accept:
            index_path = STATIC_DIR / "index.html"
            if index_path.exists():
                return FileResponse(index_path, media_type="text/html")

        return {
            "name": settings.app_name,
            "version": "1.0.0",
            "environment": settings.environment,
            "status": "running",
            "docs": None if is_prod else "/docs",
            "health": "/api/health",
            "ui": "/ui",
        }

    @app.get("/ui", tags=["system"], summary="Interactive Stock Prediction Dashboard")
    def get_ui() -> FileResponse:
        """Serve the interactive web UI dashboard."""
        index_path = STATIC_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="Frontend index.html not found.")
        return FileResponse(index_path, media_type="text/html")

    # Mount API router under /api
    app.include_router(api_router, prefix="/api")

    return app


# Default singleton ASGI application instance
app = create_app()
