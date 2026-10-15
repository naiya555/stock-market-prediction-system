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

    def save_actual(
        self,
        actual: Any,
    ) -> str:
        """Persist a verified actual market outcome into immutable storage.

        Args:
            actual: ActualOutcome instance or dict with required fields.

        Returns:
            The stored prediction_id.

        Raises:
            ValueError: If validation fails, prediction doesn't exist, symbol mismatches,
                        or conflicting outcome is already recorded.
            sqlite3.IntegrityError: If foreign key or database constraints fail.
        """
        if hasattr(actual, "to_dict"):
            data = actual.to_dict()
        elif isinstance(actual, dict):
            data = dict(actual)
        else:
            raise TypeError(f"Expected ActualOutcome or dict, got {type(actual).__name__}")

        pid = str(data.get("prediction_id", "")).strip()
        if not pid:
            raise ValueError("prediction_id is required and cannot be empty.")

        # Verify parent prediction exists
        pred = self.get_prediction(pid)
        if pred is None:
            raise ValueError(f"Parent prediction '{pid}' does not exist in predictions table.")

        symbol = str(data.get("symbol", "")).strip().upper()
        if not symbol:
            raise ValueError("symbol is required and cannot be empty.")
        if symbol != pred["symbol"]:
            raise ValueError(
                f"Symbol mismatch: actual outcome symbol '{symbol}' does not match "
                f"prediction symbol '{pred['symbol']}'."
            )

        target_date = str(data.get("target_date", "")).strip()
        if not target_date:
            raise ValueError("target_date is required and cannot be empty.")

        actual_direction = str(data.get("actual_direction", "")).strip().upper()
        if actual_direction not in ("UP", "DOWN"):
            raise ValueError(f"actual_direction must be 'UP' or 'DOWN', got {actual_direction!r}.")

        actual_label = int(data.get("actual_label", 1 if actual_direction == "UP" else 0))
        if actual_label not in (0, 1):
            raise ValueError(f"actual_label must be 0 or 1, got {actual_label!r}.")

        try:
            actual_return = float(data["actual_return"])
            actual_close = float(data["actual_close"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid numeric actual_return or actual_close: {exc}")

        if actual_close <= 0.0:
            raise ValueError(f"actual_close must be positive, got {actual_close}.")

        ref_close = data.get("reference_close")
        if ref_close is not None:
            try:
                ref_close = float(ref_close)
                if ref_close <= 0.0:
                    raise ValueError(f"reference_close must be positive, got {ref_close}.")
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid reference_close: {exc}")

        source = str(data.get("source", "yfinance")).strip()
        recorded_at = str(data.get("recorded_at") or datetime.now(timezone.utc).isoformat())

        # Check for existing actual record for this prediction
        existing = self.get_actual(pid)
        if existing is not None:
            # Idempotency check: if identical outcome, return existing without modification
            is_same_target = existing["target_date"] == target_date
            is_same_direction = existing["actual_direction"] == actual_direction
            is_same_label = existing["actual_label"] == actual_label
            is_same_close = abs(float(existing["actual_close"]) - actual_close) < 1e-4
            is_same_return = abs(float(existing["actual_return"]) - actual_return) < 1e-4

            if is_same_target and is_same_direction and is_same_label and is_same_close and is_same_return:
                return pid
            else:
                raise ValueError(
                    f"Conflicting actual outcome already recorded for prediction '{pid}': "
                    f"existing=(direction={existing['actual_direction']}, close={existing['actual_close']}, target={existing['target_date']}), "
                    f"new=(direction={actual_direction}, close={actual_close}, target={target_date})."
                )

        sql = """
        INSERT INTO actuals (
            prediction_id,
            symbol,
            target_date,
            actual_direction,
            actual_label,
            actual_return,
            actual_close,
            reference_close,
            source,
            recorded_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        );
        """
        self._conn.execute(
            sql,
            (
                pid,
                symbol,
                target_date,
                actual_direction,
                actual_label,
                actual_return,
                actual_close,
                ref_close,
                source,
                recorded_at,
            ),
        )
        self._conn.commit()
        return pid

    def get_actual(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve actual outcome record by prediction_id."""
        cursor = self._conn.execute(
            "SELECT * FROM actuals WHERE prediction_id = ?;",
            (prediction_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_actuals(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List actual outcome records with optional symbol filtering."""
        query = "SELECT * FROM actuals WHERE 1=1"
        params: List[Any] = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol.strip().upper())
        query += " ORDER BY target_date DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def count_actuals(self, symbol: Optional[str] = None) -> int:
        """Count verified actual records."""
        query = "SELECT COUNT(*) FROM actuals WHERE 1=1"
        params: List[Any] = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol.strip().upper())
        cursor = self._conn.execute(query, params)
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_prediction_with_actual(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a prediction joined with its actual outcome if available."""
        sql = """
        SELECT
            p.id AS prediction_db_id,
            p.prediction_id,
            p.symbol,
            p.model_name,
            p.model_version,
            p.prediction_timestamp,
            p.latest_input_timestamp,
            p.status,
            p.predicted_direction,
            p.predicted_label,
            p.probability_up,
            p.probability_down,
            p.is_probability_calibrated,
            p.probability_calibration,
            p.expected_movement,
            p.expected_movement_status,
            p.raw_result_json,
            a.id AS actual_db_id,
            a.target_date,
            a.actual_direction,
            a.actual_label,
            a.actual_return,
            a.actual_close,
            a.reference_close,
            a.source AS actual_source,
            a.recorded_at AS actual_recorded_at
        FROM predictions p
        LEFT JOIN actuals a ON p.prediction_id = a.prediction_id
        WHERE p.prediction_id = ?;
        """
        cursor = self._conn.execute(sql, (prediction_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        rec = dict(row)
        if rec.get("raw_result_json"):
            try:
                rec["raw_result"] = json.loads(rec["raw_result_json"])
            except Exception:
                rec["raw_result"] = None
        return rec

    def list_predictions_with_actuals(
        self,
        symbol: Optional[str] = None,
        model_name: Optional[str] = None,
        verified_only: bool = False,
        pending_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List predictions joined with their actual outcomes."""
        query = """
        SELECT
            p.id AS prediction_db_id,
            p.prediction_id,
            p.symbol,
            p.model_name,
            p.model_version,
            p.prediction_timestamp,
            p.latest_input_timestamp,
            p.status,
            p.predicted_direction,
            p.predicted_label,
            p.probability_up,
            p.probability_down,
            p.is_probability_calibrated,
            p.probability_calibration,
            p.expected_movement,
            p.expected_movement_status,
            p.raw_result_json,
            a.id AS actual_db_id,
            a.target_date,
            a.actual_direction,
            a.actual_label,
            a.actual_return,
            a.actual_close,
            a.reference_close,
            a.source AS actual_source,
            a.recorded_at AS actual_recorded_at
        FROM predictions p
        LEFT JOIN actuals a ON p.prediction_id = a.prediction_id
        WHERE 1=1
        """
        params: List[Any] = []
        if symbol:
            query += " AND p.symbol = ?"
            params.append(symbol.strip().upper())
        if model_name:
            query += " AND p.model_name = ?"
            params.append(model_name.strip().lower())
        if verified_only:
            query += " AND a.id IS NOT NULL"
        elif pending_only:
            query += " AND a.id IS NULL AND p.status = 'SUCCESS'"

        query += " ORDER BY p.prediction_timestamp DESC LIMIT ? OFFSET ?;"
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
