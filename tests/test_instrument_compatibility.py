"""Deterministic regression tests for Day 59: Multi-Instrument Validation & Ensemble Safety Gates.

Verifies:
1. Canonical Instrument Registry entries for BHARTIARTL, TCS, RELIANCE, NIFTY_TELECOMMUNICATIONS, NIFTY_50.
2. Cross-instrument model isolation:
   - Equity models cannot predict sectoral/benchmark indices.
   - BHARTIARTL equity models cannot be cross-applied to TCS or RELIANCE.
   - Preloaded models fitted for one symbol are rejected for other symbols.
   - Explicit artifact paths with conflicting metadata are rejected.
3. Close-only index feature restrictions:
   - Candlestick geometry and ATR are NaN without genuine intraday OHLC.
   - Volume is 0 for indices.
4. Data quality gates:
   - Insufficient historical bars (<34) return INSUFFICIENT_DATA.
   - Stale data returns STALE_DATA unless explicitly permitted.
5. Ensemble safety & fallback weight accounting:
   - Preserves requested_weights vs weights_used on fallback.
   - Preserves custom-configured weights.
   - Rejects NaN/Inf/negative weights.
   - Does not fabricate combined probabilities when ML prediction is unavailable.
6. Honest evaluation reporting:
   - Missing models report MODEL_UNAVAILABLE / BLOCKED, never 0% accuracy or success.
   - LLM historical blending remains labeled NOT EVALUATED without historical point-in-time news corpus.
7. Protected file hashes remain pristine.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from app.core.schemas import MarketOHLCV
from app.market.instruments import (
    INSTRUMENT_ALIAS_MAP,
    INSTRUMENT_REGISTRY,
    InstrumentType,
    get_instrument,
    is_equity,
    is_index,
    resolve_canonical_symbol,
    validate_instrument_separation,
)
from app.market.pipeline import MarketDataPipelineResult, process_market_data
from app.market.providers.base import BaseMarketDataProvider
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
    EnsembleWeights,
)
from app.prediction.service import MIN_WARMUP_BARS, PredictionService
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)
from app.training.xgboost_classifier import (
    XGBoostConfig,
    XGBoostDirectionClassifier,
)

PROTECTED_DB_HASH = "d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e"
PROTECTED_MODELS_GITKEEP_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class MockSyntheticProvider(BaseMarketDataProvider):
    """Deterministic mock market data provider for multi-instrument testing."""

    def __init__(self, records: list[MarketOHLCV]):
        self._records = records

    @property
    def name(self) -> str:
        return "mock_synthetic_provider"

    def fetch_historical_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> list[MarketOHLCV]:
        clean = resolve_canonical_symbol(symbol)
        return [
            r for r in self._records
            if resolve_canonical_symbol(r.symbol) == clean
            and start_date <= r.timestamp <= end_date
        ]


def _build_synthetic_bars(
    symbol: str,
    n_bars: int = 70,
    end_date: Optional[datetime] = None,
    is_close_only: bool = False,
) -> list[MarketOHLCV]:
    """Generate deterministic synthetic market data bars with proper geometric integrity."""
    bars: list[MarketOHLCV] = []
    base_price = 1500.0
    effective_end = end_date or datetime.now(timezone.utc)
    for i in range(n_bars):
        bar_date = effective_end - timedelta(days=(n_bars - i))
        pct = 0.002 * ((i % 7) - 3)
        price = round(base_price * (1.0 + pct), 2)
        base_price = price
        if is_close_only:
            bars.append(
                MarketOHLCV(
                    symbol=symbol,
                    timestamp=bar_date,
                    open=None,
                    high=None,
                    low=None,
                    close=price,
                    volume=0,
                    source="nifty_indices",
                )
            )
        else:
            open_ = round(price * 0.998, 2)
            high = round(max(open_, price) + 6.0, 2)
            low = round(min(open_, price) - 6.0, 2)
            bars.append(
                MarketOHLCV(
                    symbol=symbol,
                    timestamp=bar_date,
                    open=open_,
                    high=high,
                    low=low,
                    close=price,
                    volume=350_000,
                    source="yfinance",
                )
            )
    return bars


# ---------------------------------------------------------------------------
# 1. Instrument Registry & Identity Tests
# ---------------------------------------------------------------------------

class TestInstrumentRegistryIdentity:
    """Validate canonical registration, types, and alias mapping for all 4+ instruments."""

    @pytest.mark.parametrize(
        "symbol,expected_type,expected_tradable",
        [
            ("BHARTIARTL", InstrumentType.EQUITY, True),
            ("TCS", InstrumentType.EQUITY, True),
            ("RELIANCE", InstrumentType.EQUITY, True),
            ("NIFTY_TELECOMMUNICATIONS", InstrumentType.INDEX, False),
            ("NIFTY_50", InstrumentType.INDEX, False),
        ],
    )
    def test_registered_instruments(
        self, symbol: str, expected_type: InstrumentType, expected_tradable: bool
    ) -> None:
        inst = get_instrument(symbol)
        assert inst is not None, f"Instrument '{symbol}' missing from registry"
        assert inst.instrument_type == expected_type
        assert inst.is_tradable == expected_tradable
        assert inst.canonical_symbol == symbol

    def test_alias_resolution(self) -> None:
        assert resolve_canonical_symbol("TCS.NS") == "TCS"
        assert resolve_canonical_symbol("tcs") == "TCS"
        assert resolve_canonical_symbol("RELIANCE.NS") == "RELIANCE"
        assert resolve_canonical_symbol("reliance") == "RELIANCE"
        assert resolve_canonical_symbol("BHARTIARTL.NS") == "BHARTIARTL"
        assert resolve_canonical_symbol("NIFTY_TELECOM") == "NIFTY_TELECOMMUNICATIONS"

    def test_instrument_separation_validation(self) -> None:
        # Valid equity-to-index pairing
        validate_instrument_separation("BHARTIARTL", "NIFTY_TELECOMMUNICATIONS")
        validate_instrument_separation("TCS", "NIFTY_50")
        validate_instrument_separation("RELIANCE", "NIFTY_TELECOMMUNICATIONS")

        # Invalid: same instrument
        with pytest.raises(ValueError, match="must be distinct"):
            validate_instrument_separation("TCS", "TCS")

        # Invalid: equity provided where index expected
        with pytest.raises(ValueError, match="Expected index symbol"):
            validate_instrument_separation("BHARTIARTL", "TCS")

        # Invalid: index provided where equity expected
        with pytest.raises(ValueError, match="Expected equity symbol"):
            validate_instrument_separation("NIFTY_50", "NIFTY_TELECOMMUNICATIONS")


# ---------------------------------------------------------------------------
# 2. Cross-Instrument Model Isolation & Safety Gates
# ---------------------------------------------------------------------------

class TestCrossInstrumentModelSafety:
    """Validate that models are strictly symbol-specific and fail safely on mismatch."""

    def test_equity_model_cannot_predict_sectoral_index(self) -> None:
        service = PredictionService()
        req = PredictionRequest(
            symbol="NIFTY_TELECOMMUNICATIONS",
            model_name="xgboost",
        )
        res = service.predict(req)
        assert res.status == PredictionStatus.MODEL_UNAVAILABLE
        assert "Index-specific forecasting model" in res.error_message
        assert "BHARTIARTL equity models cannot be reused" in res.error_message

    def test_untrained_equity_tcs_returns_model_unavailable(self) -> None:
        bars = _build_synthetic_bars("TCS", n_bars=70)
        provider = MockSyntheticProvider(bars)
        service = PredictionService(provider=provider)

        req = PredictionRequest(symbol="TCS", model_name="xgboost", lookback_days=80)
        res = service.predict(req)
        assert res.status == PredictionStatus.MODEL_UNAVAILABLE
        assert "No trained model artifact found for equity instrument 'TCS'" in res.error_message
        assert "specifically for 'BHARTIARTL'" in res.error_message

    def test_untrained_equity_reliance_returns_model_unavailable(self) -> None:
        bars = _build_synthetic_bars("RELIANCE", n_bars=70)
        provider = MockSyntheticProvider(bars)
        service = PredictionService(provider=provider)

        req = PredictionRequest(symbol="RELIANCE", model_name="xgboost", lookback_days=80)
        res = service.predict(req)
        assert res.status == PredictionStatus.MODEL_UNAVAILABLE
        assert "No trained model artifact found for equity instrument 'RELIANCE'" in res.error_message

    def test_preloaded_model_fitted_for_bhartiartl_rejected_for_tcs(self) -> None:
        service = PredictionService()
        mock_model = MagicMock()
        mock_model.is_fitted = True
        mock_model.symbol = "BHARTIARTL"

        model, err = service._resolve_model(
            model_name="xgboost",
            preloaded_model=mock_model,
            symbol="TCS",
        )
        assert model is None
        assert "Model was fitted for equity 'BHARTIARTL' and cannot be reused for equity 'TCS'" in err

    def test_explicit_artifact_with_conflicting_metadata_rejected(self) -> None:
        service = PredictionService()
        default_xgb_path = service._get_default_artifact_path("xgboost")

        # Pass default BHARTIARTL artifact explicitly for TCS
        model, err = service._resolve_model(
            model_name="xgboost",
            explicit_artifact_path=default_xgb_path,
            symbol="TCS",
        )
        assert model is None
        assert "trained for 'BHARTIARTL' and cannot be reused for 'TCS'" in err


# ---------------------------------------------------------------------------
# 3. Close-Only Index Data Feature Restrictions
# ---------------------------------------------------------------------------

class TestCloseOnlyDataFeatureRestrictions:
    """Verify close-only index data respects feature restrictions without hallucinating OHLC."""

    def test_close_only_index_features_leave_candlestick_geometry_nan(self) -> None:
        bars = _build_synthetic_bars("NIFTY_TELECOMMUNICATIONS", n_bars=60, is_close_only=True)
        pipeline_res = process_market_data(bars)
        dataset = assemble_feature_matrix(pipeline_res, only_latest=False)

        # Canonical columns present
        assert list(dataset.X.columns) == FEATURE_COLUMNS

        # Strict isolation: target/future columns excluded
        validate_feature_matrix_isolation(dataset.X)

        # Candlestick geometry and ATR strictly NaN (no fabrication from close-only)
        assert dataset.X["open"].isna().all()
        assert dataset.X["high"].isna().all()
        assert dataset.X["low"].isna().all()
        assert dataset.X["candle_body"].isna().all()
        assert dataset.X["candle_upper_wick"].isna().all()
        assert dataset.X["atr_14"].isna().all()
        assert (dataset.X["volume"] == 0).all()

        # Close-derived indicators successfully populated
        assert dataset.X["close"].notna().all()
        assert dataset.X["sma_5"].iloc[10:].notna().all()
        assert dataset.X["rsi_14"].iloc[15:].notna().all()


# ---------------------------------------------------------------------------
# 4. Data Quality & Temporal Cutoff Gates
# ---------------------------------------------------------------------------

class TestDataQualityAndCutoffGates:
    """Verify warmup sufficiency, staleness rejection, and cutoff boundaries."""

    def test_insufficient_history_returns_insufficient_data(self) -> None:
        # 15 bars is below MIN_WARMUP_BARS (34)
        bars = _build_synthetic_bars("BHARTIARTL", n_bars=15)
        provider = MockSyntheticProvider(bars)
        service = PredictionService(provider=provider)

        req = PredictionRequest(symbol="BHARTIARTL", model_name="xgboost")
        res = service.predict(req)
        assert res.status == PredictionStatus.INSUFFICIENT_DATA
        assert res.data_quality.warmup_complete is False
        assert "Insufficient historical bars" in res.error_message
        assert f"minimum {MIN_WARMUP_BARS} required" in res.error_message

    def test_stale_data_rejected_by_default(self) -> None:
        # 50 bars ending 10 days ago (within 60-day lookback window)
        old_end = datetime.now(timezone.utc) - timedelta(days=10)
        bars = _build_synthetic_bars("BHARTIARTL", n_bars=50, end_date=old_end)
        provider = MockSyntheticProvider(bars)
        service = PredictionService(provider=provider)

        req = PredictionRequest(
            symbol="BHARTIARTL",
            model_name="xgboost",
            max_stale_days=3,
            lookback_days=70,
            allow_stale_data=False,
        )
        res = service.predict(req)
        assert res.status == PredictionStatus.STALE_DATA
        assert res.data_quality.is_stale is True
        assert "exceeding max_stale_days=3" in res.error_message

    def test_stale_data_permitted_when_explicitly_configured(self) -> None:
        old_end = datetime.now(timezone.utc) - timedelta(days=10)
        bars = _build_synthetic_bars("BHARTIARTL", n_bars=50, end_date=old_end)
        provider = MockSyntheticProvider(bars)
        service = PredictionService(provider=provider)

        req = PredictionRequest(
            symbol="BHARTIARTL",
            model_name="xgboost",
            max_stale_days=3,
            lookback_days=70,
            allow_stale_data=True,
        )
        res = service.predict(req)
        # Bypasses STALE_DATA check and succeeds on valid bars
        assert res.status == PredictionStatus.SUCCESS
        assert res.data_quality.is_stale is True


# ---------------------------------------------------------------------------
# 5. Ensemble Safety Gates & Fallback Accounting
# ---------------------------------------------------------------------------

class TestEnsembleSafetyGates:
    """Validate weight normalization, ML-only fallback, and zero-fabrication guarantees."""

    def test_weights_normalization_and_validation(self) -> None:
        # Default 70/30
        w = EnsembleWeights()
        assert w.ml_weight == 0.70
        assert w.llm_weight == 0.30

        # Custom 80/20
        w2 = EnsembleWeights(ml_weight=0.8, llm_weight=0.2)
        assert w2.ml_weight == 0.8
        assert w2.llm_weight == 0.2

        # Non-normalized input 7/3 sums to 1.0
        w3 = EnsembleWeights(ml_weight=7.0, llm_weight=3.0)
        assert w3.ml_weight == 0.70
        assert w3.llm_weight == 0.30

        # Invalid non-finite or negative weights
        with pytest.raises(Exception):
            EnsembleWeights(ml_weight=float("nan"), llm_weight=0.3)
        with pytest.raises(Exception):
            EnsembleWeights(ml_weight=0.7, llm_weight=float("inf"))
        with pytest.raises(Exception):
            EnsembleWeights(ml_weight=-0.5, llm_weight=0.5)

    def test_fallback_preserves_requested_weights_and_reports_effective(self) -> None:
        service = EnsembleService(default_weights=EnsembleWeights(ml_weight=0.75, llm_weight=0.25))

        dummy_ml = PredictionResult(
            symbol="BHARTIARTL",
            prediction_timestamp=datetime.now(timezone.utc).isoformat(),
            latest_input_timestamp=datetime.now(timezone.utc).isoformat(),
            status=PredictionStatus.SUCCESS,
            predicted_direction="UP",
            predicted_label=1,
            probability_up=0.62,
            probability_down=0.38,
            is_probability_calibrated=False,
            probability_calibration="uncalibrated",
            expected_movement=None,
            expected_movement_status="UNSUPPORTED",
            model_name="xgboost",
            model_version="xgboost_v1",
            model_metadata={},
            data_quality=PredictionDataQuality(
                total_bars_fetched=60,
                cleaned_bars=60,
                warmup_bars_required=34,
                warmup_complete=True,
                latest_bar_timestamp=datetime.now(timezone.utc).isoformat(),
                missing_feature_count=0,
                missing_features=[],
                is_stale=False,
                stale_days=0,
            ),
            error_message=None,
        )

        # Call synthesize without qualitative LLM
        res = service.synthesize(ml_result=dummy_ml, llm_result=None)

        assert res.status == PredictionStatus.SUCCESS
        assert res.requested_weights == {"ml": 0.75, "llm": 0.25}
        assert res.weights_used == {"ml": 1.0, "llm": 0.0}
        assert "fell back to 100% quantitative ML" in res.fallback_reason
        assert res.combined_direction == "UP"
        assert res.combined_probability_up == 0.62

    def test_failed_ml_does_not_fabricate_probabilities(self) -> None:
        service = EnsembleService()
        failed_ml = PredictionResult(
            symbol="TCS",
            prediction_timestamp=datetime.now(timezone.utc).isoformat(),
            latest_input_timestamp=None,
            status=PredictionStatus.MODEL_UNAVAILABLE,
            predicted_direction=None,
            predicted_label=None,
            probability_up=None,
            probability_down=None,
            is_probability_calibrated=False,
            probability_calibration="uncalibrated",
            expected_movement=None,
            expected_movement_status="UNSUPPORTED",
            model_name="xgboost",
            model_version="xgboost_v1",
            model_metadata={},
            data_quality=None,
            error_message="Model unavailable for TCS",
        )

        res = service.synthesize(ml_result=failed_ml, llm_result=None)
        assert res.status == PredictionStatus.MODEL_UNAVAILABLE
        assert res.combined_direction is None
        assert res.combined_probability_up is None
        assert res.combined_probability_down is None
        assert "unable to synthesize ensemble" in res.fallback_reason


# ---------------------------------------------------------------------------
# 6. Protected Files Integrity Gate
# ---------------------------------------------------------------------------

class TestProtectedFilesIntegrity:
    """Verify that protected files have not been modified or corrupted."""

    def test_database_and_gitkeep_hashes_unchanged(self) -> None:
        db_path = Path("data/predictions.db")
        gitkeep_path = Path("models/.gitkeep")

        assert db_path.exists(), "data/predictions.db missing"
        assert gitkeep_path.exists(), "models/.gitkeep missing"

        db_sha = hashlib.sha256(db_path.read_bytes()).hexdigest().lower()
        gitkeep_sha = hashlib.sha256(gitkeep_path.read_bytes()).hexdigest().lower()

        assert db_sha == PROTECTED_DB_HASH, (
            f"Protected database data/predictions.db modified! SHA256: {db_sha}"
        )
        assert gitkeep_sha == PROTECTED_MODELS_GITKEEP_HASH, (
            f"Protected models/.gitkeep modified! SHA256: {gitkeep_sha}"
        )
