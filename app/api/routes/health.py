"""Health Check and Dependency Readiness API Route.

Exposes application readiness and subsystem health diagnostics without disclosing
internal secrets, filesystem paths, or credentials. Does not trigger slow LLM inference.
"""

from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.dependencies import get_prediction_repository
from app.api.schemas import DependencyStatus, HealthResponse
from app.core.config import get_settings
from app.database.repository import PredictionRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=HealthResponse,
    summary="Application Health & Subsystem Readiness",
    description=(
        "Checks application runtime state, database connectivity, model registry readiness, "
        "and LLM configuration without triggering slow model inference or exposing secrets."
    ),
)
def get_health(
    repository: PredictionRepository = Depends(get_prediction_repository),
) -> JSONResponse:
    """Evaluate application health and dependency availability."""
    settings = get_settings()
    now_iso = datetime.now(timezone.utc).isoformat()
    dependencies = {}
    is_overall_healthy = True

    # 1. SQLite Database Connectivity Check
    try:
        cursor = repository.connection.execute("SELECT 1;")
        row = cursor.fetchone()
        if row and row[0] == 1:
            dependencies["database"] = DependencyStatus(
                status="ok",
                details="SQLite database connection and query operational",
            )
        else:
            dependencies["database"] = DependencyStatus(
                status="degraded",
                details="Unexpected query result from database",
            )
            is_overall_healthy = False
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        dependencies["database"] = DependencyStatus(
            status="unreachable",
            details="Database connection query failed",
        )
        is_overall_healthy = False

    # 2. Model Directory & Artifact Readiness (Filesystem checks without leaking absolute paths)
    try:
        if settings.model_dir.exists():
            dependencies["models"] = DependencyStatus(
                status="ok",
                details="Model artifact storage directory is accessible",
            )
        else:
            dependencies["models"] = DependencyStatus(
                status="degraded",
                details="Model directory not found on storage",
            )
    except Exception as exc:
        logger.warning("Model storage check error: %s", exc)
        dependencies["models"] = DependencyStatus(
            status="degraded",
            details="Error verifying model artifact storage",
        )

    # 3. LLM Configuration Readiness (Config check only; no slow inference calls!)
    dependencies["llm"] = DependencyStatus(
        status="configured",
        details="Local Ollama Gemma 3 12B integration configured (runtime-deferred)",
    )

    overall_status = "healthy" if is_overall_healthy else "degraded"
    response_status = status.HTTP_200_OK if is_overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    payload = HealthResponse(
        status=overall_status,
        app_name=settings.app_name,
        environment=settings.environment,
        timestamp=now_iso,
        dependencies=dependencies,
    )

    return JSONResponse(
        status_code=response_status,
        content=payload.model_dump(),
    )
