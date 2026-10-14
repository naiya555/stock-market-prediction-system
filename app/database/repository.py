"""Prediction Repository and Data Access Layer for Phase 6.

Provides strongly-typed persistence for PredictionResult objects,
stock metadata tracking, model provenance recording, and immutable historical auditing.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Union
import uuid

from app.database.connection import create_connection
from app.database.schema import initialize_database
from app.prediction.contract import PredictionResult


class PredictionRepository:
    """Repository handling persistence and retrieval of predictions, stocks, and model versions."""

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """Initialize repository and ensure schema is initialized.

        Args:
            db_path: Path to SQLite database file or ':memory:'. Ignored if conn is provided.
            conn: Existing sqlite3.Connection. If None, a connection is created using db_path.
        """
        self._owns_connection = conn is None
        self._conn = conn if conn is not None else create_connection(db_path)
        initialize_database(self._conn)

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the active SQLite connection."""
        return self._conn

    def close(self) -> None:
        """Close connection if owned by this repository instance."""
        if self._owns_connection and self._conn:
            self._conn.close()

    def __enter__(self) -> "PredictionRepository":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def upsert_stock(
        self,
        symbol: str,
        company_name: Optional[str] = None,
        exchange: str = "NSE",
        is_active: bool = True,
    ) -> None:
        """Insert or update stock metadata."""
        clean_symbol = symbol.strip().upper()
        now_iso = datetime.now(timezone.utc).isoformat()
        sql = """
        INSERT INTO stocks (symbol, company_name, exchange, is_active, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            company_name = COALESCE(excluded.company_name, stocks.company_name),
            exchange = excluded.exchange,
            is_active = excluded.is_active;
        """
        self._conn.execute(sql, (clean_symbol, company_name, exchange, 1 if is_active else 0, now_iso))
        self._conn.commit()

    def get_stocks(self) -> List[Dict[str, Any]]:
        """Retrieve all registered stocks."""
        cursor = self._conn.execute("SELECT * FROM stocks ORDER BY symbol ASC;")
        return [dict(row) for row in cursor.fetchall()]

    def register_model_version(
        self,
        model_name: str,
        model_version: str,
        hyperparameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a model architecture version if not already present."""
        now_iso = datetime.now(timezone.utc).isoformat()
        hp_json = json.dumps(hyperparameters, default=str) if hyperparameters else None
        sql = """
        INSERT OR IGNORE INTO model_versions (model_name, model_version, hyperparameters, created_at)
        VALUES (?, ?, ?, ?);
        """
        self._conn.execute(sql, (model_name, model_version, hp_json, now_iso))
        self._conn.commit()

    def get_model_versions(self, model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve registered model versions, optionally filtered by model name."""
        if model_name:
            cursor = self._conn.execute(
                "SELECT * FROM model_versions WHERE model_name = ? ORDER BY id ASC;",
                (model_name,),
            )
        else:
            cursor = self._conn.execute("SELECT * FROM model_versions ORDER BY model_name, id ASC;")
        rows = []
        for row in cursor.fetchall():
            d = dict(row)
            if d.get("hyperparameters"):
                try:
                    d["hyperparameters"] = json.loads(d["hyperparameters"])
                except Exception:
                    pass
            rows.append(d)
        return rows

    def save_prediction(
        self,
        result: PredictionResult,
        prediction_id: Optional[str] = None,
    ) -> str:
        """Persist a PredictionResult into immutable storage.

        Args:
            result: Structured PredictionResult from PredictionService.
            prediction_id: Optional custom prediction identifier (UUID hex generated if None).

        Returns:
            The stored prediction_id.

        Raises:
            sqlite3.IntegrityError: If prediction_id already exists or foreign key constraints fail.
        """
        if not isinstance(result, PredictionResult):
            raise TypeError(f"Expected PredictionResult, got {type(result).__name__}")

        pid = prediction_id if prediction_id else uuid.uuid4().hex
        now_iso = datetime.now(timezone.utc).isoformat()

        # Ensure parent foreign key references exist
        self.upsert_stock(result.symbol)
        self.register_model_version(
            model_name=result.model_name,
            model_version=result.model_version,
            hyperparameters=result.model_metadata,
        )

        # Full lossless payload serialized as JSON
        raw_json = json.dumps(result.to_dict(), default=str)

        sql = """
        INSERT INTO predictions (
            prediction_id,
            symbol,
            model_name,
            model_version,
            prediction_timestamp,
            latest_input_timestamp,
            status,
            predicted_direction,
            predicted_label,
            probability_up,
            probability_down,
            is_probability_calibrated,
            probability_calibration,
            expected_movement,
            expected_movement_status,
            total_bars_fetched,
            cleaned_bars,
            warmup_bars_required,
            warmup_complete,
            missing_feature_count,
            error_message,
            disclaimer,
            raw_result_json,
            created_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        );
        """

        dq = result.data_quality
        params = (
            pid,
            result.symbol.strip().upper(),
            result.model_name,
            result.model_version,
            result.prediction_timestamp,
            result.latest_input_timestamp,
            result.status.value,
            result.predicted_direction,
            result.predicted_label,
            result.probability_up,
            result.probability_down,
            1 if result.is_probability_calibrated else 0,
            result.probability_calibration,
            result.expected_movement,
            result.expected_movement_status,
            dq.total_bars_fetched if dq else None,
            dq.cleaned_bars if dq else None,
            dq.warmup_bars_required if dq else None,
            (1 if dq.warmup_complete else 0) if dq else None,
            dq.missing_feature_count if dq else None,
            result.error_message,
            result.disclaimer,
            raw_json,
            now_iso,
        )

        self._conn.execute(sql, params)
        self._conn.commit()
        return pid

    def get_prediction(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored prediction by its unique identifier."""
        cursor = self._conn.execute(
            "SELECT * FROM predictions WHERE prediction_id = ?;",
            (prediction_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        record = dict(row)
        if record.get("raw_result_json"):
            try:
                record["raw_result"] = json.loads(record["raw_result_json"])
            except Exception:
                record["raw_result"] = None
        return record

    def list_predictions(
        self,
        symbol: Optional[str] = None,
        model_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List historical predictions with optional symbol and model filtering."""
        query = "SELECT * FROM predictions WHERE 1=1"
        params: List[Any] = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol.strip().upper())
        if model_name:
            query += " AND model_name = ?"
            params.append(model_name.strip().lower())

        query += " ORDER BY prediction_timestamp DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = self._conn.execute(query, params)
        records = []
        for row in cursor.fetchall():
            rec = dict(row)
            if rec.get("raw_result_json"):
                try:
                    rec["raw_result"] = json.loads(rec["raw_result_json"])
                except Exception:
                    rec["raw_result"] = None
            records.append(rec)
        return records

    def count_predictions(
        self,
        symbol: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> int:
        """Count predictions matching optional filters."""
        query = "SELECT COUNT(*) FROM predictions WHERE 1=1"
        params: List[Any] = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol.strip().upper())
        if model_name:
            query += " AND model_name = ?"
            params.append(model_name.strip().lower())

        cursor = self._conn.execute(query, params)
        row = cursor.fetchone()
        return row[0] if row else 0
