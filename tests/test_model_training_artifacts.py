"""Regression and integration tests for deliberate model training, artifact persistence, and inference readiness (GAP-02)."""

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import shutil
import tempfile
from typing import Generator
import pytest
import numpy as np
import pandas as pd

from app.core.schemas import MarketOHLCV
from app.market.providers.base import BaseMarketDataProvider
from app.prediction.contract import (
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.service import PredictionService, train_and_persist_baseline_model
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)
from app.training.lightgbm_classifier import (
    HAS_LIGHTGBM,
    LightGBMConfig,
    LightGBMDirectionClassifier,
)
from app.training.retraining import (
    ModelReleaseStatus,
    ModelRetrainer,
    RetrainingResult,
)
from app.training.xgboost_classifier import (
    HAS_XGBOOST,
    XGBoostConfig,
    XGBoostDirectionClassifier,
    split_chronological_holdout,
)


class MockMarketDataProvider(BaseMarketDataProvider):
    """Deterministic mock provider returning generated bars without network calls."""

    def __init__(self, records: Sequence[MarketOHLCV]):
        self._records = list(records)

    @property
    def name(self) -> str:
        return "mock_provider"

    def fetch_historical_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[MarketOHLCV]:
        clean_sym = symbol.strip().upper()
        if clean_sym.endswith(".NS"):
            clean_sym = clean_sym[:-3]
        return [
            r
            for r in self._records
            if r.symbol == clean_sym and start_date <= r.timestamp <= end_date
        ]


def _create_mock_bars(
    symbol: str = "BHARTIARTL",
    n_bars: int = 120,
    start_date: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc),
) -> List[MarketOHLCV]:
    """Generate realistic synthetic OHLCV sequence satisfying physical candle geometry."""
    bars: List[MarketOHLCV] = []
    np.random.seed(42)
    base_price = 1000.0

    for i in range(n_bars):
        ts = start_date + timedelta(days=i)
        pct = np.random.normal(0.001, 0.015)
        close = round(base_price * (1.0 + pct), 2)
        open_ = round(base_price * (1.0 + np.random.normal(0.0, 0.005)), 2)
        high = round(max(open_, close) + abs(np.random.normal(5.0, 2.0)), 2)
        low = round(min(open_, close) - abs(np.random.normal(5.0, 2.0)), 2)
        volume = int(np.random.randint(100_000, 500_000))

        bars.append(
            MarketOHLCV(
                symbol=symbol,
                timestamp=ts,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
                source="mock",
            )
        )
        base_price = close

    return bars


@pytest.fixture
def temp_models_dir() -> Generator[Path, None, None]:
    """Provide a clean temporary directory for isolated model persistence."""
    td = Path(tempfile.mkdtemp(prefix="test_models_"))
    yield td
    shutil.rmtree(td, ignore_errors=True)


def test_train_and_persist_baseline_model_lifecycle(temp_models_dir: Path):
    """Verify train_and_persist_baseline_model executes, serializes, and can be loaded."""
    bars = _create_mock_bars(n_bars=100)
    provider = MockMarketDataProvider(bars)
    as_of = datetime(2026, 4, 1, tzinfo=timezone.utc)

    xgb_path = temp_models_dir / "xgboost_direction.json"
    persisted_path = train_and_persist_baseline_model(
        symbol="BHARTIARTL",
        model_name="xgboost",
        output_path=xgb_path,
        lookback_days=100,
        end_date=as_of,
        provider=provider,
    )

    assert persisted_path == xgb_path
    assert xgb_path.is_file()
    assert xgb_path.stat().st_size > 0

    # Verify model resolution and inference through PredictionService
    service = PredictionService(provider=provider, models_dir=temp_models_dir)
    req = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        model_artifact_path=str(xgb_path),
        as_of_date=as_of,
    )
    result = service.predict(req)
    assert result.status == PredictionStatus.SUCCESS
    assert result.predicted_direction in ("UP", "DOWN")
    assert result.probability_up is not None
    assert result.probability_down is not None
    assert round(result.probability_up + result.probability_down, 4) == 1.0


def test_deliberate_gated_retraining_and_metadata_persistence(temp_models_dir: Path):
    """Verify ModelRetrainer gates, persists model artifact, and writes metadata JSON."""
    np.random.seed(42)
    n_train = 80
    n_val = 25
    feature_cols = list(FEATURE_COLUMNS)

    # Synthetic feature matrices
    X_train = pd.DataFrame(np.random.randn(n_train, len(feature_cols)), columns=feature_cols)
    y_train = pd.Series((X_train[feature_cols[0]] > 0).astype(int))

    X_val = pd.DataFrame(np.random.randn(n_val, len(feature_cols)), columns=feature_cols)
    y_val = pd.Series((X_val[feature_cols[0]] > 0).astype(int))

    retrainer = ModelRetrainer(models_dir=temp_models_dir, repository=None)
    result = retrainer.retrain_and_gate(
        symbol="BHARTIARTL",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-06-01",
        evaluation_cutoff_date="2025-07-01",
        candidate_version="v_test_gap02",
        force_promote=True,  # Test artifact writing even under strict gate testing
    )

    assert result.status == ModelReleaseStatus.PROMOTED
    assert result.is_promoted is True

    # Active model should exist
    active_path = temp_models_dir / "xgboost_direction.json"
    assert active_path.is_file()

    # Metadata file should exist
    meta_path = temp_models_dir / "xgboost_metadata.json"
    assert meta_path.is_file()
    with open(meta_path, "r", encoding="utf-8") as f:
        meta_data = json.load(f)

    assert meta_data["model_name"] == "xgboost"
    assert meta_data["model_version"] == "v_test_gap02"
    assert meta_data["feature_version"] == "canonical_37_features"
    assert meta_data["training_sample_count"] == n_train
    assert meta_data["evaluation_sample_count"] == n_val
    assert "metrics" in meta_data
    assert "accuracy" in meta_data["metrics"]
    assert "balanced_accuracy" in meta_data["metrics"]


def test_missing_and_corrupt_artifact_containment(temp_models_dir: Path):
    """Verify PredictionService gracefully contains missing or corrupt model files."""
    bars = _create_mock_bars(n_bars=60)
    provider = MockMarketDataProvider(bars)
    service = PredictionService(provider=provider, models_dir=temp_models_dir)
    as_of = datetime(2026, 3, 2, tzinfo=timezone.utc)

    # 1. Missing artifact
    req_missing = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=as_of,
    )
    res_missing = service.predict(req_missing)
    assert res_missing.status == PredictionStatus.MODEL_UNAVAILABLE
    assert "Model artifact not found" in (res_missing.error_message or "")

    # 2. Corrupt / truncated artifact
    corrupt_path = temp_models_dir / "xgboost_direction.json"
    corrupt_path.write_text("{invalid_json: true, broken", encoding="utf-8")

    res_corrupt = service.predict(req_missing)
    assert res_corrupt.status == PredictionStatus.MODEL_UNAVAILABLE
    assert "Failed to deserialize model artifact" in (res_corrupt.error_message or "")


def test_anti_leakage_and_chronological_inversion_rejection(temp_models_dir: Path):
    """Verify chronological inversion is detected and rejected without lookahead."""
    retrainer = ModelRetrainer(models_dir=temp_models_dir, repository=None)

    # Inverted cutoffs (training cutoff >= evaluation cutoff)
    is_valid, msg = retrainer.validate_chronological_ordering(
        training_cutoff_date="2025-08-01",
        evaluation_cutoff_date="2025-07-01",
    )
    assert is_valid is False
    assert "Chronological inversion detected" in msg

    # Date-aligned dataframe overlap detection
    df_train = pd.DataFrame({"Date": ["2025-07-05", "2025-07-10"]})
    df_val = pd.DataFrame({"Date": ["2025-07-08", "2025-07-15"]})
    is_valid_df, msg_df = retrainer.validate_chronological_ordering(
        training_cutoff_date="2025-07-01",
        evaluation_cutoff_date="2025-08-01",
        X_train=df_train,
        X_val=df_val,
    )
    assert is_valid_df is False
    assert "Temporal overlap/leakage detected" in msg_df


def test_production_active_artifacts_inference_readiness():
    """Verify that persisted production models in models/ are loadable and ready for inference."""
    models_dir = Path("models")
    xgb_path = models_dir / "xgboost_direction.json"
    lgb_path = models_dir / "lightgbm_direction.txt"

    # Only run if production artifacts are present on disk
    if not (xgb_path.is_file() and lgb_path.is_file()):
        pytest.skip("Production model artifacts not present on disk; run scripts/train_models.py first.")

    bars = _create_mock_bars(n_bars=60)
    provider = MockMarketDataProvider(bars)
    service = PredictionService(provider=provider, models_dir=models_dir)
    as_of = datetime(2026, 3, 2, tzinfo=timezone.utc)

    for model_name in ("xgboost", "lightgbm"):
        req = PredictionRequest(
            symbol="BHARTIARTL",
            model_name=model_name,
            as_of_date=as_of,
        )
        result = service.predict(req)
        assert result.status == PredictionStatus.SUCCESS
        assert result.predicted_direction in ("UP", "DOWN")
        assert result.probability_up is not None
        assert result.probability_down is not None
        assert math.isfinite(result.probability_up)
        assert math.isfinite(result.probability_down)
        assert round(result.probability_up + result.probability_down, 4) == 1.0
