"""Focused Unit and Integration Tests for Phase 14 Day 35 Live Quote Inference Integration.

Validates:
1. Fresh quote integration into PredictionService inference.
2. Delayed quote integration and ~15-minute Yahoo Finance delay disclosure.
3. Stale quote handling with explicit status and zero price fabrication.
4. Failed quote retrieval handling (network failure, 404, or unsupported provider).
5. Point-in-time isolation and zero look-ahead bias in historical backtest mode.
6. Explicit opt-out via include_live_quote=False.
7. Backward compatibility for PredictionResult, EnsemblePredictionResult, and PredictionResponse.
8. Ensemble target range anchoring using verified live quote prices.
9. FastAPI route serialization of quote_context in both standalone and ensemble modes.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Sequence
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.dependencies import (
    get_db_connection,
    get_ensemble_service,
    get_prediction_repository,
    get_prediction_service,
)
from app.api.schemas import PredictionResponse, QuoteContextResponse
from app.core.schemas import MarketOHLCV
from app.market.providers.base import BaseMarketDataProvider
from app.market.quote import (
    DEFAULT_DELAY_DISCLAIMER,
    DataFreshnessStatus,
    LiveQuote,
)
from app.market.session import IST, MarketSessionState
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
    QuoteContext,
)
from app.prediction.ensemble import (
    EnsembleAgreement,
    EnsemblePredictionResult,
    EnsembleService,
    TargetRange,
)
from app.prediction.service import MIN_WARMUP_BARS, PredictionService
from app.training.feature_matrix import FEATURE_COLUMNS
from app.training.xgboost_classifier import (
    XGBoostConfig,
    XGBoostDirectionClassifier,
)


def _create_mock_bars(
    symbol: str = "RELIANCE",
    n_bars: int = 60,
    start_date: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc),
) -> List[MarketOHLCV]:
    """Generate synthetic OHLCV sequence satisfying physical candle geometry."""
    bars: List[MarketOHLCV] = []
    base_price = 2400.0
    for i in range(n_bars):
        ts = start_date + timedelta(days=i)
        close = round(base_price * (1.0 + (0.002 * (i % 5 - 2))), 2)
        open_ = round(base_price, 2)
        high = round(max(open_, close) + 10.0, 2)
        low = round(min(open_, close) - 10.0, 2)
        volume = 200_000
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


class MockQuoteAwareProvider(BaseMarketDataProvider):
    """Mock provider supporting both historical OHLCV and live quote fetching."""

    def __init__(
        self,
        records: Sequence[MarketOHLCV],
        quote: Optional[LiveQuote] = None,
        quote_error: Optional[Exception] = None,
    ) -> None:
        self._records = list(records)
        self._quote = quote
        self._quote_error = quote_error
        self.fetch_quote_called = 0

    @property
    def name(self) -> str:
        return "mock_quote_provider"

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

    def fetch_quote(self, symbol: str, max_staleness_seconds: int = 3600) -> LiveQuote:
        self.fetch_quote_called += 1
        if self._quote_error is not None:
            raise self._quote_error
        if self._quote is not None:
            return self._quote
        raise RuntimeError(f"No mock quote configured for {symbol}")


@pytest.fixture
def fitted_xgb_model() -> XGBoostDirectionClassifier:
    """Pre-fitted lightweight XGBoost classifier fixture."""
    np.random.seed(42)
    X_synthetic = pd.DataFrame(
        np.random.randn(50, len(FEATURE_COLUMNS)),
        columns=FEATURE_COLUMNS,
    )
    y_synthetic = pd.Series((X_synthetic["close"] > 0).astype(int))
    clf = XGBoostDirectionClassifier(XGBoostConfig(n_estimators=3, max_depth=2))
    clf.fit(X_synthetic, y_synthetic)
    return clf


def test_inference_with_fresh_quote(fitted_xgb_model: XGBoostDirectionClassifier) -> None:
    """Verify fresh quote is attached to PredictionResult with explicit last-price distinction."""
    now = datetime(2026, 10, 16, 11, 0, tzinfo=IST)
    fresh_quote = LiveQuote(
        symbol="RELIANCE",
        price=2480.50,
        timestamp=now,
        retrieved_at=now,
        source="yfinance",
        session_state=MarketSessionState.REGULAR_HOURS,
        freshness_status=DataFreshnessStatus.FRESH,
        open_price=2460.0,
        day_high=2490.0,
        day_low=2455.0,
        previous_close=2450.0,
        change=30.50,
        change_percent=1.24,
        volume=1200000,
        currency="INR",
        is_delayed=True,
        delay_minutes=15,
    )
    provider = MockQuoteAwareProvider(_create_mock_bars("RELIANCE"), quote=fresh_quote)
    service = PredictionService(provider=provider)

    req = PredictionRequest(symbol="RELIANCE", model_name="xgboost")
    res = service.predict(req, preloaded_model=fitted_xgb_model)

    assert res.status == PredictionStatus.SUCCESS
    assert provider.fetch_quote_called == 1
    assert res.quote_context is not None
    assert res.quote_context.symbol == "RELIANCE"
    assert res.quote_context.last_price == 2480.50
    assert res.quote_context.freshness_status == "FRESH"
    assert res.quote_context.session_state == "REGULAR_HOURS"
    assert res.quote_context.price_type == "LAST_TRADED_PRICE"
    assert res.quote_context.is_delayed is True
    assert res.quote_context.delay_minutes == 15
    assert "NOT a predicted opening or closing price" in res.quote_context.note

    # Direction and probabilities must remain directional classifications
    assert res.predicted_direction in ("UP", "DOWN")
    assert res.probability_up is not None

    summary = res.format_summary()
    assert "Last Quoted Price:     ₹ 2,480.50" in summary
    assert "[OBSERVED, not predicted]" in summary


def test_inference_with_delayed_quote(fitted_xgb_model: XGBoostDirectionClassifier) -> None:
    """Verify delayed quote preserves ~15m delay disclosure and disclaimer."""
    now = datetime(2026, 10, 16, 11, 0, tzinfo=IST)
    delayed_quote = LiveQuote(
        symbol="TCS",
        price=3200.0,
        timestamp=now - timedelta(minutes=15),
        retrieved_at=now,
        source="yfinance",
        session_state=MarketSessionState.REGULAR_HOURS,
        freshness_status=DataFreshnessStatus.DELAYED,
        is_delayed=True,
        delay_minutes=15,
    )
    provider = MockQuoteAwareProvider(_create_mock_bars("TCS"), quote=delayed_quote)
    service = PredictionService(provider=provider)

    req = PredictionRequest(symbol="TCS", model_name="xgboost")
    res = service.predict(req, preloaded_model=fitted_xgb_model)

    assert res.status == PredictionStatus.SUCCESS
    assert res.quote_context is not None
    assert res.quote_context.freshness_status == "DELAYED"
    assert res.quote_context.last_price == 3200.0
    assert res.quote_context.is_delayed is True
    assert res.quote_context.delay_minutes == 15
    assert "delayed by ~15 minutes" in res.quote_context.note


def test_inference_with_stale_quote(fitted_xgb_model: XGBoostDirectionClassifier) -> None:
    """Verify stale quote retains observed price without fabricating new prices."""
    old_time = datetime(2026, 10, 10, 15, 30, tzinfo=IST)
    now = datetime(2026, 10, 16, 11, 0, tzinfo=IST)
    stale_quote = LiveQuote(
        symbol="INFY",
        price=1800.0,
        timestamp=old_time,
        retrieved_at=now,
        source="yfinance",
        session_state=MarketSessionState.REGULAR_HOURS,
        freshness_status=DataFreshnessStatus.STALE,
        is_delayed=True,
        delay_minutes=15,
    )
    provider = MockQuoteAwareProvider(_create_mock_bars("INFY"), quote=stale_quote)
    service = PredictionService(provider=provider)

    req = PredictionRequest(symbol="INFY", model_name="xgboost")
    res = service.predict(req, preloaded_model=fitted_xgb_model)

    assert res.status == PredictionStatus.SUCCESS
    assert res.quote_context is not None
    assert res.quote_context.freshness_status == "STALE"
    assert res.quote_context.last_price == 1800.0


def test_inference_with_quote_fetch_failure(fitted_xgb_model: XGBoostDirectionClassifier) -> None:
    """Verify quote fetch exception does not abort prediction inference (zero fabrication)."""
    provider = MockQuoteAwareProvider(
        _create_mock_bars("RELIANCE"),
        quote_error=RuntimeError("Provider HTTP 503 Service Unavailable"),
    )
    service = PredictionService(provider=provider)

    req = PredictionRequest(symbol="RELIANCE", model_name="xgboost")
    res = service.predict(req, preloaded_model=fitted_xgb_model)

    # Core prediction must succeed
    assert res.status == PredictionStatus.SUCCESS
    assert res.predicted_direction in ("UP", "DOWN")
    assert res.quote_context is not None
    assert res.quote_context.freshness_status == "UNAVAILABLE"
    assert res.quote_context.last_price is None
    assert res.quote_context.price_type == "NONE"
    assert "Price was not fabricated" in res.quote_context.note
    assert "503" in (res.quote_context.error_message or "")


def test_inference_with_unsupported_quote_provider(fitted_xgb_model: XGBoostDirectionClassifier) -> None:
    """Verify provider lacking fetch_quote gracefully falls back to UNAVAILABLE without error."""
    class PureBarsProvider(BaseMarketDataProvider):
        @property
        def name(self) -> str:
            return "pure_bars_provider"

        def fetch_historical_ohlcv(self, symbol, start_date, end_date, interval="1d"):
            return _create_mock_bars(symbol)

    service = PredictionService(provider=PureBarsProvider())
    req = PredictionRequest(symbol="RELIANCE", model_name="xgboost")
    res = service.predict(req, preloaded_model=fitted_xgb_model)

    assert res.status == PredictionStatus.SUCCESS
    assert res.quote_context is not None
    assert res.quote_context.freshness_status == "UNAVAILABLE"
    assert res.quote_context.last_price is None


def test_historical_mode_lookahead_bias_isolation(fitted_xgb_model: XGBoostDirectionClassifier) -> None:
    """Verify point-in-time historical inference strictly isolates live quote queries."""
    provider = MockQuoteAwareProvider(_create_mock_bars("RELIANCE"))
    service = PredictionService(provider=provider)

    # Historical cutoff date requested (50 days after 2026-01-01 so >34 warmup bars exist)
    req = PredictionRequest(
        symbol="RELIANCE",
        model_name="xgboost",
        as_of_date=datetime(2026, 2, 20, tzinfo=timezone.utc),
    )
    res = service.predict(req, preloaded_model=fitted_xgb_model)

    assert res.status == PredictionStatus.SUCCESS
    # Crucial: Provider fetch_quote MUST NOT be called
    assert provider.fetch_quote_called == 0
    assert res.quote_context is not None
    assert res.quote_context.freshness_status == "NOT_APPLICABLE"
    assert res.quote_context.last_price is None
    assert "prevent look-ahead bias" in res.quote_context.note


def test_include_live_quote_false(fitted_xgb_model: XGBoostDirectionClassifier) -> None:
    """Verify caller can opt out of live quote context completely."""
    provider = MockQuoteAwareProvider(_create_mock_bars("RELIANCE"))
    service = PredictionService(provider=provider)

    req = PredictionRequest(
        symbol="RELIANCE",
        model_name="xgboost",
        include_live_quote=False,
    )
    res = service.predict(req, preloaded_model=fitted_xgb_model)

    assert res.status == PredictionStatus.SUCCESS
    assert provider.fetch_quote_called == 0
    assert res.quote_context is None


def test_backward_compatibility() -> None:
    """Verify legacy construction without quote_context preserves full backward compatibility."""
    quality = PredictionDataQuality(
        total_bars_fetched=50,
        cleaned_bars=50,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp="2026-10-15T00:00:00Z",
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=0,
    )
    res = PredictionResult(
        symbol="RELIANCE",
        prediction_timestamp="2026-10-16T10:00:00Z",
        latest_input_timestamp="2026-10-15T00:00:00Z",
        status=PredictionStatus.SUCCESS,
        predicted_direction="UP",
        predicted_label=1,
        probability_up=0.65,
        probability_down=0.35,
        model_name="xgboost",
        model_version="xgb_v1",
        model_metadata={},
        data_quality=quality,
    )
    assert res.quote_context is None
    d = res.to_dict()
    assert "quote_context" in d
    assert d["quote_context"] is None

    ens = EnsemblePredictionResult(
        symbol="RELIANCE",
        prediction_timestamp="2026-10-16T10:00:00Z",
        latest_input_timestamp="2026-10-15T00:00:00Z",
        status=PredictionStatus.SUCCESS,
        combined_direction="UP",
        combined_label=1,
        combined_probability_up=0.65,
        combined_probability_down=0.35,
        agreement_status=EnsembleAgreement.AGREEMENT,
        weights_used={"ml": 0.7, "llm": 0.3},
        ml_prediction=res,
        llm_reasoning=None,
    )
    assert ens.quote_context is None
    ens_dict = ens.to_dict()
    assert ens_dict["quote_context"] is None
    canon = ens.to_prediction_result()
    assert canon.quote_context is None


def test_ensemble_target_range_anchored_by_live_quote() -> None:
    """Verify ensemble anchors target range using verified quote price when current_price is omitted."""
    quote_ctx = QuoteContext(
        symbol="RELIANCE",
        last_price=2500.0,
        price_timestamp="2026-10-16T11:00:00+05:30",
        retrieved_at="2026-10-16T11:00:00+05:30",
        source="yfinance",
        session_state="REGULAR_HOURS",
        freshness_status="FRESH",
    )
    quality = PredictionDataQuality(
        total_bars_fetched=50,
        cleaned_bars=50,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp="2026-10-15T00:00:00Z",
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=0,
    )
    ml_res = PredictionResult(
        symbol="RELIANCE",
        prediction_timestamp="2026-10-16T11:00:00Z",
        latest_input_timestamp="2026-10-15T00:00:00Z",
        status=PredictionStatus.SUCCESS,
        predicted_direction="UP",
        predicted_label=1,
        probability_up=0.70,
        probability_down=0.30,
        model_name="xgboost",
        model_version="xgb_v1",
        model_metadata={},
        data_quality=quality,
        quote_context=quote_ctx,
    )

    ensemble_service = EnsembleService()
    # current_price omitted; atr_value provided
    ens_res = ensemble_service.synthesize(
        ml_result=ml_res,
        atr_value=40.0,
    )

    assert ens_res.target_range is not None
    assert ens_res.target_range.reference_price == 2500.0
    assert ens_res.target_range.lower_bound == 2460.0
    assert ens_res.target_range.upper_bound == 2540.0
    assert ens_res.target_range.method == "atr_14"
    assert ens_res.quote_context is not None
    assert ens_res.quote_context.last_price == 2500.0


def test_api_predict_route_quote_context_serialization() -> None:
    """Verify POST /api/predict serializes quote_context in response schema."""
    quote_ctx = QuoteContext(
        symbol="RELIANCE",
        last_price=2450.0,
        price_timestamp="2026-10-16T11:00:00+05:30",
        retrieved_at="2026-10-16T11:00:00+05:30",
        source="yfinance",
        session_state="REGULAR_HOURS",
        freshness_status="DELAYED",
    )
    quality = PredictionDataQuality(
        total_bars_fetched=50,
        cleaned_bars=50,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp="2026-10-15T00:00:00Z",
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=0,
    )
    dummy_res = PredictionResult(
        symbol="RELIANCE",
        prediction_timestamp="2026-10-16T11:00:00Z",
        latest_input_timestamp="2026-10-15T00:00:00Z",
        status=PredictionStatus.SUCCESS,
        predicted_direction="UP",
        predicted_label=1,
        probability_up=0.68,
        probability_down=0.32,
        model_name="xgboost",
        model_version="xgb_v1",
        model_metadata={},
        data_quality=quality,
        quote_context=quote_ctx,
    )

    app = create_app()
    mock_pred_svc = MagicMock()
    mock_pred_svc.predict.return_value = dummy_res
    mock_repo = MagicMock()
    mock_repo.save_prediction.return_value = "mock_pred_123"

    app.dependency_overrides[get_prediction_service] = lambda: mock_pred_svc
    app.dependency_overrides[get_prediction_repository] = lambda: mock_repo

    with TestClient(app) as client:
        res = client.post("/api/predict", json={"symbol": "RELIANCE", "model_name": "xgboost"})
        assert res.status_code == 200
        data = res.json()
        assert "quote_context" in data
        assert data["quote_context"] is not None
        assert data["quote_context"]["last_price"] == 2450.0
        assert data["quote_context"]["freshness_status"] == "DELAYED"
        assert data["quote_context"]["price_type"] == "LAST_TRADED_PRICE"
        assert "NOT a predicted opening or closing price" in data["quote_context"]["note"]


def test_quote_context_error_message_sanitizes_internal_paths() -> None:
    """Verify quote error messages with filesystem paths or tracebacks are sanitized in API response."""
    quote_ctx = QuoteContext(
        symbol="RELIANCE",
        last_price=None,
        price_timestamp=None,
        retrieved_at=None,
        source="yfinance",
        session_state="UNKNOWN",
        freshness_status="UNAVAILABLE",
        error_message="Traceback (most recent call last):\n  File 'C:\\Users\\admin\\app\\provider.py', line 42, in fetch\nException: timeout",
    )
    quality = PredictionDataQuality(
        total_bars_fetched=50,
        cleaned_bars=50,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp="2026-10-15T00:00:00Z",
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=0,
    )
    dummy_res = PredictionResult(
        symbol="RELIANCE",
        prediction_timestamp="2026-10-16T11:00:00Z",
        latest_input_timestamp="2026-10-15T00:00:00Z",
        status=PredictionStatus.SUCCESS,
        predicted_direction="UP",
        predicted_label=1,
        probability_up=0.60,
        probability_down=0.40,
        model_name="xgboost",
        model_version="xgb_v1",
        model_metadata={},
        data_quality=quality,
        quote_context=quote_ctx,
    )

    app = create_app()
    mock_pred_svc = MagicMock()
    mock_pred_svc.predict.return_value = dummy_res
    mock_repo = MagicMock()
    mock_repo.save_prediction.return_value = "mock_pred_456"

    app.dependency_overrides[get_prediction_service] = lambda: mock_pred_svc
    app.dependency_overrides[get_prediction_repository] = lambda: mock_repo

    with TestClient(app) as client:
        res = client.post("/api/predict", json={"symbol": "RELIANCE", "model_name": "xgboost"})
        assert res.status_code == 200
        data = res.json()
        qc = data["quote_context"]
        assert qc is not None
        assert qc["freshness_status"] == "UNAVAILABLE"
        # Must NOT leak Windows or Unix filesystem path or Python traceback
        assert "C:\\Users" not in qc["error_message"]
        assert "Traceback" not in qc["error_message"]
        assert "line 42" not in qc["error_message"]
        assert qc["error_message"] == "Quote retrieval failed. Check server logs."


def test_quote_acquisition_crlf_log_sanitization(caplog: pytest.LogCaptureFixture) -> None:
    """Verify PredictionService sanitizes CRLF characters when logging quote acquisition failures."""
    mock_provider = MagicMock()
    mock_provider.fetch_quote.side_effect = RuntimeError("Simulated network timeout")
    service = PredictionService(provider=mock_provider)

    req = PredictionRequest(symbol="RELIANCE", model_name="xgboost")
    with caplog.at_level("WARNING"):
        ctx = service._fetch_quote_context("RELIANCE\r\nINJECTED_LOG:root", req)

    assert ctx is not None
    assert ctx.freshness_status == "UNAVAILABLE"
    # caplog records must not contain unescaped CRLF in log messages
    for record in caplog.records:
        assert "\r" not in record.message
        assert "\n" not in record.message
        if "Live quote acquisition failed" in record.message:
            assert "\\r" in record.message or "\\n" in record.message


def test_prediction_pipeline_distinguishes_observed_price_and_direction() -> None:
    """Verify observed quote price is strictly isolated from directional forecasts."""
    quote_ctx = QuoteContext(
        symbol="TCS",
        last_price=3500.0,
        price_timestamp="2026-10-16T11:00:00+05:30",
        retrieved_at="2026-10-16T11:00:00+05:30",
        source="yfinance",
        session_state="REGULAR_HOURS",
        freshness_status="DELAYED",
    )
    res = PredictionResult(
        symbol="TCS",
        prediction_timestamp="2026-10-16T11:00:00Z",
        latest_input_timestamp="2026-10-15T00:00:00Z",
        status=PredictionStatus.SUCCESS,
        predicted_direction="DOWN",
        predicted_label=0,
        probability_up=0.35,
        probability_down=0.65,
        model_name="xgboost",
        model_version="xgb_v1",
        model_metadata={},
        data_quality=None,
        quote_context=quote_ctx,
    )
    api_resp = PredictionResponse(
        symbol=res.symbol,
        prediction_timestamp=res.prediction_timestamp,
        latest_input_timestamp=res.latest_input_timestamp,
        status=res.status.value,
        predicted_direction=res.predicted_direction,
        predicted_label=res.predicted_label,
        probability_up=res.probability_up,
        probability_down=res.probability_down,
        model_name=res.model_name,
        model_version=res.model_version,
        model_metadata=res.model_metadata,
        data_quality=None,
        quote_context=QuoteContextResponse(
            symbol=quote_ctx.symbol,
            last_price=quote_ctx.last_price,
            price_timestamp=quote_ctx.price_timestamp,
            retrieved_at=quote_ctx.retrieved_at,
            source=quote_ctx.source,
            session_state=quote_ctx.session_state,
            freshness_status=quote_ctx.freshness_status,
            is_delayed=quote_ctx.is_delayed,
            delay_minutes=quote_ctx.delay_minutes,
            price_type=quote_ctx.price_type,
            note=quote_ctx.note,
            error_message=quote_ctx.error_message,
        ),
        disclaimer=res.disclaimer,
    )

    resp_dict = api_resp.model_dump()
    # Direction is binary UP / DOWN with uncalibrated probabilities
    assert resp_dict["predicted_direction"] == "DOWN"
    assert resp_dict["probability_down"] == 0.65
    # Response root must not fabricate a predicted opening or closing price
    assert "predicted_price" not in resp_dict
    assert "predicted_open" not in resp_dict
    assert "predicted_close" not in resp_dict
    # Observed market quote is strictly quarantined inside quote_context
    assert resp_dict["quote_context"]["last_price"] == 3500.0
    assert resp_dict["quote_context"]["price_type"] == "LAST_TRADED_PRICE"
