"""Tests for Day 23 Structured Prediction Output.

Validates the structured prediction output contract using PredictionService and PredictionResult:
1. Complete structured output schema (symbol, timestamps, model metadata, data quality).
2. Predicted direction ('UP' or 'DOWN') and binary label (1 or 0).
3. Uncalibrated model probability transparency (is_probability_calibrated=False, probability_calibration='uncalibrated').
4. Expected movement boundary handling (expected_movement=None, expected_movement_status='UNSUPPORTED').
5. Serialization to primitive dictionary via to_dict() for downstream JSON consumers.
6. Human-readable summary representation via format_summary().
7. Symmetrical class probabilities (P(UP) + P(DOWN) == 1.0).
8. Failure and degraded result output containment.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Sequence
import numpy as np
import pandas as pd
import pytest

from app.core.schemas import MarketOHLCV
from app.market.providers.base import BaseMarketDataProvider
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.service import PredictionService
from app.training.feature_matrix import FEATURE_COLUMNS
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
    n_bars: int = 70,
    start_date: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc),
) -> List[MarketOHLCV]:
    """Generate deterministic synthetic OHLCV sequence."""
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
def mock_prediction_context():
    """Create test environment with mock provider and pre-trained classifiers."""
    bars = _create_mock_bars("BHARTIARTL", n_bars=70)
    provider = MockMarketDataProvider(bars)

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
    }


def test_structured_prediction_output_schema_and_types(mock_prediction_context):
    """Verify PredictionResult contains all required fields with expected types."""
    ctx = mock_prediction_context
    service = PredictionService(provider=ctx["provider"])

    req = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 10, tzinfo=timezone.utc),
    )
    res = service.predict(req, preloaded_model=ctx["xgb_model"])

    assert isinstance(res, PredictionResult)
    assert res.status == PredictionStatus.SUCCESS
    assert res.symbol == "BHARTIARTL"
    assert isinstance(res.prediction_timestamp, str)
    assert isinstance(res.latest_input_timestamp, str)
    assert res.predicted_direction in ("UP", "DOWN")
    assert res.predicted_label in (0, 1)
    assert isinstance(res.probability_up, float)
    assert isinstance(res.probability_down, float)
    assert res.model_name == "xgboost"
    assert res.model_version == "xgboost-direction-v1"
    assert isinstance(res.model_metadata, dict)
    assert isinstance(res.data_quality, PredictionDataQuality)
    assert res.error_message is None
    assert isinstance(res.disclaimer, str)


def test_uncalibrated_probability_transparency(mock_prediction_context):
    """Verify model probability is explicitly flagged as uncalibrated."""
    ctx = mock_prediction_context
    service = PredictionService(provider=ctx["provider"])

    req = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 10, tzinfo=timezone.utc),
    )
    res = service.predict(req, preloaded_model=ctx["xgb_model"])

    assert res.is_probability_calibrated is False
    assert res.probability_calibration == "uncalibrated"
    # Probabilities must be within valid unit interval
    assert 0.0 <= res.probability_up <= 1.0
    assert 0.0 <= res.probability_down <= 1.0
    assert round(res.probability_up + res.probability_down, 4) == 1.0000


def test_expected_movement_explicitly_unsupported(mock_prediction_context):
    """Verify expected movement is None and status is UNSUPPORTED for direction classifier."""
    ctx = mock_prediction_context
    service = PredictionService(provider=ctx["provider"])

    req = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 10, tzinfo=timezone.utc),
    )
    res = service.predict(req, preloaded_model=ctx["xgb_model"])

    assert res.expected_movement is None
    assert res.expected_movement_status == "UNSUPPORTED"


def test_prediction_result_to_dict_serialization(mock_prediction_context):
    """Verify to_dict() produces complete primitive representation for JSON serialization."""
    ctx = mock_prediction_context
    service = PredictionService(provider=ctx["provider"])

    req = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 10, tzinfo=timezone.utc),
    )
    res = service.predict(req, preloaded_model=ctx["xgb_model"])
    d = res.to_dict()

    assert isinstance(d, dict)
    assert d["status"] == "SUCCESS"
    assert d["symbol"] == "BHARTIARTL"
    assert d["predicted_direction"] in ("UP", "DOWN")
    assert d["predicted_label"] in (0, 1)
    assert isinstance(d["probability_up"], float)
    assert isinstance(d["probability_down"], float)
    assert d["is_probability_calibrated"] is False
    assert d["probability_calibration"] == "uncalibrated"
    assert d["expected_movement"] is None
    assert d["expected_movement_status"] == "UNSUPPORTED"
    assert d["model_name"] == "xgboost"
    assert d["model_version"] == "xgboost-direction-v1"
    assert isinstance(d["data_quality"], dict)
    assert d["data_quality"]["cleaned_bars"] >= 34
    assert d["data_quality"]["warmup_complete"] is True
    assert d["data_quality"]["missing_feature_count"] == 0
    assert "disclaimer" in d


def test_prediction_result_format_summary(mock_prediction_context):
    """Verify format_summary() renders human-readable output containing key disclosures."""
    ctx = mock_prediction_context
    service = PredictionService(provider=ctx["provider"])

    req = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        as_of_date=datetime(2026, 3, 10, tzinfo=timezone.utc),
    )
    res = service.predict(req, preloaded_model=ctx["xgb_model"])
    summary = res.format_summary()

    assert "Prediction Summary for BHARTIARTL:" in summary
    assert "Status:                 SUCCESS" in summary
    assert "Model:                  xgboost (xgboost-direction-v1)" in summary
    assert "Predicted Direction:" in summary
    assert "uncalibrated" in summary
    assert "Expected Movement:      null (status=UNSUPPORTED)" in summary
    assert "Disclaimer:" in summary


def test_structured_error_output_contains_required_diagnostics(mock_prediction_context):
    """Verify failed prediction requests produce structured PredictionResult with diagnostics."""
    ctx = mock_prediction_context
    service = PredictionService(provider=ctx["provider"])

    # Request with missing artifact
    req = PredictionRequest(
        symbol="BHARTIARTL",
        model_name="xgboost",
        model_artifact_path=Path("non_existent_path.json"),
        as_of_date=datetime(2026, 3, 10, tzinfo=timezone.utc),
    )
    res = service.predict(req)

    assert res.status == PredictionStatus.MODEL_UNAVAILABLE
    assert res.predicted_direction is None
    assert res.predicted_label is None
    assert res.probability_up is None
    assert res.probability_down is None
    assert res.is_probability_calibrated is False
    assert res.expected_movement is None
    assert res.expected_movement_status == "UNSUPPORTED"
    assert res.error_message is not None
    assert "Model artifact not found" in res.error_message
    assert res.data_quality.warmup_complete is True

    # Error summary representation
    summary = res.format_summary()
    assert "Status:                 MODEL_UNAVAILABLE" in summary
    assert "Error Message:" in summary
