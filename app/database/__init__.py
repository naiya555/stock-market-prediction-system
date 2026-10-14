"""Database Package for Indian Stock Market Prediction System.

Exposes SQLite connection management, schema initialization, and PredictionRepository.
"""

from app.database.connection import (
    create_connection,
    db_session,
    get_default_db_path,
)
from app.database.repository import PredictionRepository
from app.database.schema import (
    SCHEMA_SQL,
    initialize_database,
)

__all__ = [
    "create_connection",
    "db_session",
    "get_default_db_path",
    "initialize_database",
    "PredictionRepository",
    "SCHEMA_SQL",
]
