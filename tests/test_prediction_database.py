"""Tests for Phase 6 SQLite Prediction Database and Immutability Enforcement.

Validates:
1. Schema initialization: stocks, model_versions, predictions, actuals tables, indexes, and triggers.
2. Stock and model version registration and querying.
3. Prediction persistence from typed PredictionResult objects.
4. Retention of Day 23 uncalibrated probability and unsupported expected movement semantics.
5. Strict immutability: UPDATE and DELETE trigger rejections at SQLite engine level.
6. Foreign key enforcement and duplicate prevention.
7. Filtering, pagination, and count operations.
8. PredictionService optional repository integration.
"""

from datetime import datetime, timedelta, timezone
import json
import sqlite3
import pytest

from app.database.connection import create_connection, db_session
from app.database.repository import PredictionRepository
from app.database.schema import initialize_database
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.service import PredictionService


@pytest.fixture
def in_memory_repo():
    """Create an in-memory PredictionRepository for isolated test runs."""
    conn = create_connection(":memory:")
    repo = PredictionRepository(conn=conn)
    yield repo
    repo.close()


def make_dummy_prediction_result(
    symbol: str = "BHARTIARTL",
    status: PredictionStatus = PredictionStatus.SUCCESS,
    direction: str = "UP",
    label: int = 1,
    p_up: float = 0.5823,
    p_down: float = 0.4177,
    model_name: str = "xgboost",
    model_version: str = "xgboost-direction-v1",
) -> PredictionResult:
    """Helper to construct a valid PredictionResult conforming to Day 23 contracts."""
    quality = PredictionDataQuality(
        total_bars_fetched=1235,
        cleaned_bars=1235,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp="2026-10-14T00:00:00+05:30",
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=0,
    )
    return PredictionResult(
        symbol=symbol,
        prediction_timestamp="2026-10-14T11:00:00+00:00",
        latest_input_timestamp="2026-10-14T00:00:00+05:30",
        status=status,
        predicted_direction=direction if status == PredictionStatus.SUCCESS else None,
        predicted_label=label if status == PredictionStatus.SUCCESS else None,
        probability_up=p_up if status == PredictionStatus.SUCCESS else None,
        probability_down=p_down if status == PredictionStatus.SUCCESS else None,
        is_probability_calibrated=False,
        probability_calibration="uncalibrated",
        expected_movement=None,
        expected_movement_status="UNSUPPORTED",
        model_name=model_name,
        model_version=model_version,
        model_metadata={"max_depth": 3, "learning_rate": 0.05},
        data_quality=quality,
        error_message=None if status == PredictionStatus.SUCCESS else "Synthetic error",
    )


def test_database_schema_initialization():
    """Verify all 4 required tables, indexes, and immutability triggers are created."""
    conn = create_connection(":memory:")
    initialize_database(conn)

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    assert "stocks" in tables
    assert "model_versions" in tables
    assert "predictions" in tables
    assert "actuals" in tables

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger';")
    triggers = {row[0] for row in cursor.fetchall()}
    assert "trg_prevent_prediction_update" in triggers
    assert "trg_prevent_prediction_delete" in triggers
    conn.close()


def test_stock_metadata_upsert(in_memory_repo: PredictionRepository):
    """Verify stock registration and idempotent updates."""
    in_memory_repo.upsert_stock("bhartiartl", company_name="Bharti Airtel Ltd", exchange="NSE")
    stocks = in_memory_repo.get_stocks()
    assert len(stocks) == 1
    assert stocks[0]["symbol"] == "BHARTIARTL"
    assert stocks[0]["company_name"] == "Bharti Airtel Ltd"
    assert stocks[0]["exchange"] == "NSE"

    # Update company name
    in_memory_repo.upsert_stock("BHARTIARTL", company_name="Bharti Airtel Limited")
    stocks = in_memory_repo.get_stocks()
    assert len(stocks) == 1
    assert stocks[0]["company_name"] == "Bharti Airtel Limited"


def test_model_version_registration(in_memory_repo: PredictionRepository):
    """Verify model version registration with hyperparameter metadata."""
    in_memory_repo.register_model_version(
        model_name="xgboost",
        model_version="xgboost-direction-v1",
        hyperparameters={"max_depth": 3, "n_estimators": 100},
    )
    models = in_memory_repo.get_model_versions()
    assert len(models) == 1
    assert models[0]["model_name"] == "xgboost"
    assert models[0]["model_version"] == "xgboost-direction-v1"
    assert models[0]["hyperparameters"] == {"max_depth": 3, "n_estimators": 100}

    # Idempotent registration of duplicate
    in_memory_repo.register_model_version(
        model_name="xgboost",
        model_version="xgboost-direction-v1",
        hyperparameters={"max_depth": 5},
    )
    models = in_memory_repo.get_model_versions("xgboost")
    assert len(models) == 1
    assert models[0]["hyperparameters"] == {"max_depth": 3, "n_estimators": 100}


def test_save_and_get_prediction_preserves_semantics(in_memory_repo: PredictionRepository):
    """Verify prediction persistence preserves all Day 23 transparency semantics."""
    res = make_dummy_prediction_result(symbol="RELIANCE", p_up=0.62, p_down=0.38)
    pid = in_memory_repo.save_prediction(res, prediction_id="test-pred-001")
    assert pid == "test-pred-001"

    saved = in_memory_repo.get_prediction("test-pred-001")
    assert saved is not None
    assert saved["symbol"] == "RELIANCE"
    assert saved["predicted_direction"] == "UP"
    assert saved["predicted_label"] == 1
    assert saved["probability_up"] == 0.62
    assert saved["probability_down"] == 0.38
    assert saved["is_probability_calibrated"] == 0
    assert saved["probability_calibration"] == "uncalibrated"
    assert saved["expected_movement"] is None
    assert saved["expected_movement_status"] == "UNSUPPORTED"
    assert saved["status"] == "SUCCESS"

    # Lossless raw JSON payload recovery
    raw = saved["raw_result"]
    assert raw is not None
    assert raw["symbol"] == "RELIANCE"
    assert raw["is_probability_calibrated"] is False
    assert raw["probability_calibration"] == "uncalibrated"
    assert raw["expected_movement"] is None
    assert raw["expected_movement_status"] == "UNSUPPORTED"
    assert raw["data_quality"]["cleaned_bars"] == 1235


def test_immutability_trigger_prevents_updates(in_memory_repo: PredictionRepository):
    """Verify that SQLite engine trigger rejects any UPDATE on predictions table."""
    res = make_dummy_prediction_result()
    pid = in_memory_repo.save_prediction(res, prediction_id="immutable-pred-1")

    with pytest.raises(sqlite3.DatabaseError) as exc_info:
        in_memory_repo.connection.execute(
            "UPDATE predictions SET predicted_direction = 'DOWN' WHERE prediction_id = ?;",
            (pid,),
        )
    assert "Predictions are immutable: updates are strictly prohibited" in str(exc_info.value)

    # Confirm record remains unchanged
    record = in_memory_repo.get_prediction(pid)
    assert record["predicted_direction"] == "UP"


def test_immutability_trigger_prevents_deletions(in_memory_repo: PredictionRepository):
    """Verify that SQLite engine trigger rejects any DELETE on predictions table."""
    res = make_dummy_prediction_result()
    pid = in_memory_repo.save_prediction(res, prediction_id="immutable-pred-2")

    with pytest.raises(sqlite3.DatabaseError) as exc_info:
        in_memory_repo.connection.execute(
            "DELETE FROM predictions WHERE prediction_id = ?;",
            (pid,),
        )
    assert "Predictions are immutable: deletions are strictly prohibited" in str(exc_info.value)

    # Confirm record still exists
    record = in_memory_repo.get_prediction(pid)
    assert record is not None


def test_duplicate_prediction_id_rejected(in_memory_repo: PredictionRepository):
    """Verify inserting a duplicate prediction_id raises IntegrityError."""
    res = make_dummy_prediction_result()
    in_memory_repo.save_prediction(res, prediction_id="dup-pred-1")

    with pytest.raises(sqlite3.IntegrityError):
        in_memory_repo.save_prediction(res, prediction_id="dup-pred-1")


def test_foreign_key_enforcement(in_memory_repo: PredictionRepository):
    """Verify foreign key enforcement rejects orphaned records."""
    # Attempting raw direct insertion with a non-existent stock symbol without foreign key disabled
    with pytest.raises(sqlite3.IntegrityError):
        in_memory_repo.connection.execute(
            """
            INSERT INTO predictions (
                prediction_id, symbol, model_name, model_version,
                prediction_timestamp, status, disclaimer, raw_result_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "orphan-1",
                "NONEXISTENT_STOCK",
                "xgboost",
                "v1",
                "2026-10-14T00:00:00Z",
                "SUCCESS",
                "disc",
                "{}",
                "2026-10-14T00:00:00Z",
            ),
        )


def test_list_and_count_predictions(in_memory_repo: PredictionRepository):
    """Verify filtering, counting, and pagination of predictions."""
    res1 = make_dummy_prediction_result(symbol="INFY", model_name="xgboost")
    res2 = make_dummy_prediction_result(symbol="INFY", model_name="lightgbm")
    res3 = make_dummy_prediction_result(symbol="TCS", model_name="xgboost")

    in_memory_repo.save_prediction(res1, prediction_id="p-1")
    in_memory_repo.save_prediction(res2, prediction_id="p-2")
    in_memory_repo.save_prediction(res3, prediction_id="p-3")

    assert in_memory_repo.count_predictions() == 3
    assert in_memory_repo.count_predictions(symbol="INFY") == 2
    assert in_memory_repo.count_predictions(symbol="TCS") == 1
    assert in_memory_repo.count_predictions(symbol="INFY", model_name="xgboost") == 1

    infy_preds = in_memory_repo.list_predictions(symbol="INFY")
    assert len(infy_preds) == 2

    limited = in_memory_repo.list_predictions(limit=1, offset=0)
    assert len(limited) == 1


def test_save_error_prediction_result(in_memory_repo: PredictionRepository):
    """Verify error prediction results can be audited and retrieved."""
    err_res = make_dummy_prediction_result(
        symbol="BHARTIARTL",
        status=PredictionStatus.MODEL_UNAVAILABLE,
    )
    pid = in_memory_repo.save_prediction(err_res)
    saved = in_memory_repo.get_prediction(pid)

    assert saved is not None
    assert saved["status"] == "MODEL_UNAVAILABLE"
    assert saved["predicted_direction"] is None
    assert saved["probability_up"] is None
    assert saved["error_message"] == "Synthetic error"


def test_prediction_service_optional_persistence(in_memory_repo: PredictionRepository):
    """Verify PredictionService automatically persists prediction when repository and persist=True are set."""
    import numpy as np
    import pandas as pd
    from app.market.providers.base import BaseMarketDataProvider
    from app.core.schemas import MarketOHLCV
    from app.training.feature_matrix import FEATURE_COLUMNS

    class DummyFittedModel:
        is_fitted = True
        config = type("Config", (), {"to_dict": lambda s: {"test": 1}})()
        feature_names = list(FEATURE_COLUMNS)

        def predict_proba(self, X):
            return np.array([[0.45, 0.55]])

    class MockProvider(BaseMarketDataProvider):
        def __init__(self, bars):
            self._bars = bars

        @property
        def name(self) -> str:
            return "mock"

        def fetch_historical_ohlcv(self, symbol, start_date, end_date, interval="1d"):
            return self._bars

    # Generate 80 realistic bars so all 37 indicators warm up cleanly
    bars = []
    np.random.seed(42)
    base_price = 1000.0
    start_date = datetime.now(timezone.utc) - timedelta(days=80)
    for i in range(80):
        ts = start_date + timedelta(days=i)
        pct = np.random.normal(0.001, 0.015)
        close = round(base_price * (1.0 + pct), 2)
        open_ = round(base_price * (1.0 + np.random.normal(0.0, 0.005)), 2)
        high = round(max(open_, close) + abs(np.random.normal(5.0, 2.0)), 2)
        low = round(min(open_, close) - abs(np.random.normal(5.0, 2.0)), 2)
        volume = int(np.random.randint(100_000, 500_000))
        bars.append(MarketOHLCV(
            symbol="BHARTIARTL",
            timestamp=ts,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
            source="mock",
        ))
        base_price = close

    dummy_model = DummyFittedModel()
    service = PredictionService(
        provider=MockProvider(bars),
        repository=in_memory_repo,
    )

    # 1. Without persist=True
    req = PredictionRequest(symbol="BHARTIARTL", model_name="xgboost")
    result_unpersisted = service.predict(req, preloaded_model=dummy_model, persist=False)
    assert result_unpersisted.status == PredictionStatus.SUCCESS
    assert in_memory_repo.count_predictions(symbol="BHARTIARTL") == 0

    # 2. With persist=True
    result_persisted = service.predict(req, preloaded_model=dummy_model, persist=True)
    assert result_persisted.status == PredictionStatus.SUCCESS
    assert in_memory_repo.count_predictions(symbol="BHARTIARTL") == 1

    stored = in_memory_repo.list_predictions(symbol="BHARTIARTL")[0]
    assert stored["predicted_direction"] == "UP"
    assert stored["probability_up"] == 0.55
    assert stored["is_probability_calibrated"] == 0
    assert stored["expected_movement"] is None
    assert stored["expected_movement_status"] == "UNSUPPORTED"
