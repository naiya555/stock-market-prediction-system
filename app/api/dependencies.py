"""FastAPI Dependency Injection Providers.

Supplies loosely coupled database connections, repositories, prediction engines,
and event providers to API endpoint handlers. Supports clean overrides during automated testing.
"""

from typing import Generator, List, Optional
import sqlite3

from fastapi import Depends

from app.core.config import get_settings
from app.database.connection import create_connection
from app.database.repository import PredictionRepository
from app.events.providers.base import BaseEventProvider
from app.events.providers.rbi_provider import RBIEventProvider
from app.events.providers.sebi_provider import SEBIEventProvider
from app.prediction.ensemble import EnsembleService
from app.prediction.service import PredictionService


def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a configured SQLite database connection and ensure clean closure."""
    conn = create_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_prediction_repository(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> PredictionRepository:
    """Provide an initialized PredictionRepository instance."""
    return PredictionRepository(conn=conn)


def get_prediction_service(
    repository: PredictionRepository = Depends(get_prediction_repository),
) -> PredictionService:
    """Provide an initialized PredictionService with bound repository."""
    settings = get_settings()
    return PredictionService(
        models_dir=settings.model_dir,
        repository=repository,
    )


def get_ensemble_service(
    prediction_service: PredictionService = Depends(get_prediction_service),
    repository: PredictionRepository = Depends(get_prediction_repository),
) -> EnsembleService:
    """Provide an initialized EnsembleService for multi-agent synthesis."""
    return EnsembleService(
        prediction_service=prediction_service,
        repository=repository,
    )


def get_event_providers() -> List[BaseEventProvider]:
    """Provide default list of active macroeconomic/regulatory event providers."""
    return [
        RBIEventProvider(),
        SEBIEventProvider(),
    ]
