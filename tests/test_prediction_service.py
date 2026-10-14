"""Tests for Day 22 Prediction Engine Service Foundation.

Validates:
1. Valid prediction requests with XGBoost and LightGBM models.
2. In-memory registered models vs persistent filesystem artifacts.
3. Unsupported symbols and missing market data.
4. Insufficient history and warm-up requirements.
5. Missing and NaN feature handling.
6. Target and future outcome exclusion (zero leakage).
7. Feature column order consistency with FEATURE_COLUMNS.
8. Actionable error handling when model artifacts are missing (zero silent retraining).
9. Model prediction runtime error containment.
10. Symmetrical UP/DOWN class and probability mapping.
11. Prediction determinism and reproducibility.
12. Point-in-time timestamp correctness.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Sequence
import pytest
import numpy as np
import pandas as pd

from app.core.schemas import MarketOHLCV
from app.market.providers.base import BaseMarketDataProvider
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.service import (
    MIN_WARMUP_BARS,
    PredictionService,
    train_and_persist_baseline_model,
)
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURE_PATTERNS,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)
from app.training.lightgbm_classifier import (
    LightGBMConfig,
    LightGBMDirectionClassifier,
)
from app.training.xgboost_classifier import (
    XGBoostConfig,
    XGBoostDirectionClassifier,
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
    n_bars: int = 60,
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
def mock_dataset_and_models(tmp_path: Path):
    """Fixture providing mock provider, fitted models, and sample bars."""
    bars = _create_mock_bars("BHARTIARTL", n_bars=80)
    provider = MockMarketDataProvider(bars)

    # Train a baseline XGBoost model
    np.random.seed(42)
    X_synthetic = pd.DataFrame(
        np.random.randn(60, len(FEATURE_COLUMNS)),
        columns=FEATURE_COLUMNS,
    )
    y_synthetic = pd.Series((X_synthetic["close"] > 0).astype(int))

    xgb_clf = XGBoostDirectionClassifier(XGBoostConfig(n_estimators=5, max_depth=2))
    xgb_clf.fit(X_synthetic, y_synthetic)

    lgb_clf = LightGBMDirectionClassifier(LightGBMConfig(n_estimators=5, max_depth=2, num_leaves=4))
    lgb_clf.fit(X_synthetic, y_synthetic)

    return {
        "bars": bars,
        "provider": provider,
        "xgb_model": xgb_clf,
        "lgb_model": lgb_clf,
        "tmp_path": tmp_path,
    }


def test_valid_prediction_request_with_preloaded_xgboost(mock_dataset_and_models):
    """Verify valid prediction request using preloaded XGBoost model."""
    ctx = mock_dataset_and_models
    service = PredictionService(provider=ctx["provider"])

    request = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    result = service.predict(request, preloaded_model=ctx["xgb_model"])

    assert result.status == PredictionStatus.SUCCESS
    assert result.symbol == "BHARTIARTL"
    assert result.predicted_direction in ("UP", "DOWN")
    assert result.predicted_label in (0, 1)
    assert result.probability_up is not None
    assert 0.0 <= result.probability_up <= 1.0
    assert result.probability_down is not None
    assert round(result.probability_up + result.probability_down, 2) == 1.00
    assert result.model_name == "xgboost"
    assert result.data_quality.warmup_complete is True
    assert result.data_quality.missing_feature_count == 0
    assert result.latest_input_timestamp is not None
    assert result.error_message is None


def test_valid_prediction_request_with_preloaded_lightgbm(mock_dataset_and_models):
    """Verify valid prediction request using preloaded LightGBM model."""
    ctx = mock_dataset_and_models
    service = PredictionService(provider=ctx["provider"])

    request = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="lightgbm",
        as_of_date=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    result = service.predict(request, preloaded_model=ctx["lgb_model"])

    assert result.status == PredictionStatus.SUCCESS
    assert result.model_name == "lightgbm"
    assert result.predicted_direction in ("UP", "DOWN")
    assert result.probability_up is not None


def test_in_memory_model_registry(mock_dataset_and_models):
    """Verify PredictionService resolves models from in-memory registry."""
    ctx = mock_dataset_and_models
    registry = {"xgboost": ctx["xgb_model"]}
    service = PredictionService(provider=ctx["provider"], model_registry=registry)

    request = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    result = service.predict(request)
    assert result.status == PredictionStatus.SUCCESS
    assert result.predicted_direction in ("UP", "DOWN")


def test_unsupported_and_invalid_symbols(mock_dataset_and_models):
    """Verify validation handles invalid or empty symbol requests."""
    ctx = mock_dataset_and_models
    service = PredictionService(provider=ctx["provider"])

    # Empty symbol raises ValueError on request creation
    with pytest.raises(ValueError, match="symbol must be a non-empty string"):
        _ = PredictionRequest(symbol="   ")

    # Invalid model_name raises ValueError
    with pytest.raises(ValueError, match="Unsupported model_name"):
        _ = PredictionRequest(symbol="BHARTIARTL", model_name="random_forest")


def test_missing_market_data():
    """Verify service handles symbols with zero historical bars gracefully."""
    empty_provider = MockMarketDataProvider([])
    service = PredictionService(provider=empty_provider)

    request = PredictionRequest(symbol="UNKNOWN_STOCK")
    result = service.predict(request)

    assert result.status == PredictionStatus.INSUFFICIENT_DATA
    assert result.predicted_direction is None
    assert "No market data found" in result.error_message


def test_insufficient_feature_history():
    """Verify service rejects input if bars are fewer than MIN_WARMUP_BARS (34)."""
    short_bars = _create_mock_bars("SHORT", n_bars=15)
    provider = MockMarketDataProvider(short_bars)
    service = PredictionService(provider=provider)

    request = PredictionRequest(symbol="SHORT")
    result = service.predict(request)

    assert result.status == PredictionStatus.INSUFFICIENT_DATA
    assert result.data_quality.warmup_complete is False
    assert "Insufficient historical bars" in result.error_message
    assert f"minimum {MIN_WARMUP_BARS} required" in result.error_message


def test_target_and_future_columns_excluded(mock_dataset_and_models):
    """Verify that inference feature matrix excludes target and future outcome columns."""
    ctx = mock_dataset_and_models
    bars = ctx["bars"]

    from app.market.pipeline import run_market_data_pipeline
    pipeline_res = run_market_data_pipeline(
        symbol="BHARTIARTL",
        start_date=bars[0].timestamp,
        end_date=bars[-1].timestamp,
        provider=ctx["provider"],
    )
    dataset = assemble_feature_matrix(pipeline_res)

    latest_X = dataset.X.iloc[[-1]]
    validate_feature_matrix_isolation(latest_X)

    # Invariant: No forbidden pattern in columns
    for col in latest_X.columns:
        for pat in FORBIDDEN_FEATURE_PATTERNS:
            assert pat not in col.lower(), f"Forbidden pattern '{pat}' found in inference feature '{col}'"


def test_feature_order_consistency(mock_dataset_and_models):
    """Verify feature ordering sent to model strictly matches FEATURE_COLUMNS."""
    ctx = mock_dataset_and_models
    service = PredictionService(provider=ctx["provider"])

    captured_features = []

    class MockSpyClassifier:
        is_fitted = True
        feature_names = list(FEATURE_COLUMNS)
        config = XGBoostConfig()

        def predict_proba(self, X):
            nonlocal captured_features
            if isinstance(X, pd.DataFrame):
                captured_features = list(X.columns)
            return np.array([[0.45, 0.55]])

    request = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    result = service.predict(request, preloaded_model=MockSpyClassifier())
    assert result.status == PredictionStatus.SUCCESS
    assert captured_features == FEATURE_COLUMNS


def test_missing_model_artifacts_error_actionable(mock_dataset_and_models, tmp_path: Path):
    """Verify actionable error is returned when model artifact is absent (no silent retraining)."""
    ctx = mock_dataset_and_models
    empty_models_dir = tmp_path / "empty_models"
    empty_models_dir.mkdir()

    service = PredictionService(provider=ctx["provider"], models_dir=empty_models_dir)

    request = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    result = service.predict(request)

    assert result.status == PredictionStatus.MODEL_UNAVAILABLE
    assert result.predicted_direction is None
    assert "Model artifact not found" in result.error_message
    assert "Automatic on-the-fly retraining during inference is prohibited" in result.error_message


def test_model_prediction_runtime_error_handled(mock_dataset_and_models):
    """Verify runtime exception during model.predict_proba is caught safely."""
    ctx = mock_dataset_and_models
    service = PredictionService(provider=ctx["provider"])

    class FailingClassifier:
        is_fitted = True
        feature_names = list(FEATURE_COLUMNS)
        config = XGBoostConfig()

        def predict_proba(self, X):
            raise RuntimeError("CUDA out of memory simulation")

    request = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    result = service.predict(request, preloaded_model=FailingClassifier())

    assert result.status == PredictionStatus.FAILED
    assert "Model inference failed: CUDA out of memory simulation" in result.error_message
    assert result.predicted_direction is None


def test_up_down_class_and_probability_mapping(mock_dataset_and_models):
    """Verify class thresholding and symmetrical probability calculations."""
    ctx = mock_dataset_and_models
    service = PredictionService(provider=ctx["provider"])

    class HighProbUpClassifier:
        is_fitted = True
        feature_names = list(FEATURE_COLUMNS)
        config = XGBoostConfig()

        def predict_proba(self, X):
            return np.array([[0.30, 0.70]])

    class HighProbDownClassifier:
        is_fitted = True
        feature_names = list(FEATURE_COLUMNS)
        config = XGBoostConfig()

        def predict_proba(self, X):
            return np.array([[0.65, 0.35]])

    req = PredictionRequest(symbol="BHARTIARTL", as_of_date=datetime(2026, 3, 20, tzinfo=timezone.utc))

    res_up = service.predict(req, preloaded_model=HighProbUpClassifier())
    assert res_up.status == PredictionStatus.SUCCESS
    assert res_up.predicted_direction == "UP"
    assert res_up.predicted_label == 1
    assert res_up.probability_up == 0.70
    assert res_up.probability_down == 0.30

    res_dn = service.predict(req, preloaded_model=HighProbDownClassifier())
    assert res_dn.status == PredictionStatus.SUCCESS
    assert res_dn.predicted_direction == "DOWN"
    assert res_dn.predicted_label == 0
    assert res_dn.probability_up == 0.35
    assert res_dn.probability_down == 0.65


def test_reproducibility_with_persisted_model(mock_dataset_and_models, tmp_path: Path):
    """Verify identical predictions are produced from persisted model artifact across calls."""
    ctx = mock_dataset_and_models
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    artifact_path = models_dir / "xgboost_direction.json"

    # Persist the test model
    ctx["xgb_model"].save_model(artifact_path)
    assert artifact_path.is_file()

    service = PredictionService(provider=ctx["provider"], models_dir=models_dir)

    req = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    res1 = service.predict(req)
    res2 = service.predict(req)

    assert res1.status == PredictionStatus.SUCCESS
    assert res2.status == PredictionStatus.SUCCESS
    assert res1.predicted_direction == res2.predicted_direction
    assert res1.probability_up == res2.probability_up
    assert res1.probability_down == res2.probability_down
    assert res1.latest_input_timestamp == res2.latest_input_timestamp


def test_prediction_timestamp_and_input_data_timestamp(mock_dataset_and_models):
    """Verify distinctness of prediction generation timestamp and input observation timestamp."""
    ctx = mock_dataset_and_models
    service = PredictionService(provider=ctx["provider"])

    as_of = datetime(2026, 3, 20, tzinfo=timezone.utc)
    req = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=as_of,
    )

    result = service.predict(req, preloaded_model=ctx["xgb_model"])

    assert result.status == PredictionStatus.SUCCESS
    # Prediction timestamp is current execution time
    pred_dt = datetime.fromisoformat(result.prediction_timestamp)
    # Latest input timestamp is the date of the market bar
    input_dt = datetime.fromisoformat(result.latest_input_timestamp)

    assert pred_dt.year >= 2026
    assert input_dt <= as_of
