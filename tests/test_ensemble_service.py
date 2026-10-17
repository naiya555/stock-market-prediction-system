"""Focused Unit Tests for Multi-Agent Ensemble Layer (Day 32 / Phase 12).

Tests cover:
- EnsembleWeights normalization and validation.
- Agreement and Divergence categorization (STRONG_AGREEMENT, AGREEMENT, DIVERGENCE, PARTIAL, ML_ONLY).
- Transparent probability blending and independent score preservation.
- Target range calculation using ATR.
- Integrated factor ranking assembly.
- Conversion to canonical PredictionResult and persistence to PredictionRepository.
- Outcome verification of ensemble predictions using OutcomeVerifier.
- Graceful degradation on ML failure or LLM exceptions.
"""

from datetime import date, datetime, timedelta, timezone
import pytest

from app.core.schemas import MarketOHLCV, ValidationError
from app.database.connection import create_connection
from app.database.repository import PredictionRepository
from app.history.verifier import OutcomeVerifier
from app.llm.client import MockLLMClient
from app.llm.schemas import (
    NON_PREDICTIVE_QUALITATIVE_DISCLAIMER,
    LLMDirection,
    LLMReasoningResult,
)
from app.llm.service import LLMService
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.ensemble import (
    ENSEMBLE_DISCLAIMER,
    EnsembleAgreement,
    EnsemblePredictionResult,
    EnsembleService,
    EnsembleWeights,
    TargetRange,
)
from app.prediction.service import PredictionService


def _create_mock_ml_result(
    symbol: str = "TCS",
    direction: str = "UP",
    prob_up: float = 0.65,
    status: PredictionStatus = PredictionStatus.SUCCESS,
    error_message: str = None,
    latest_bar_timestamp: str = "2026-10-15T15:30:00+05:30",
) -> PredictionResult:
    """Helper to create a deterministic mock ML PredictionResult."""
    quality = PredictionDataQuality(
        total_bars_fetched=100,
        cleaned_bars=100,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp=latest_bar_timestamp,
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=0,
    )
    return PredictionResult(
        symbol=symbol,
        prediction_timestamp="2026-10-16T08:30:00+05:30",
        latest_input_timestamp=latest_bar_timestamp,
        status=status,
        predicted_direction=direction if status == PredictionStatus.SUCCESS else None,
        predicted_label=1 if direction == "UP" and status == PredictionStatus.SUCCESS else 0,
        probability_up=prob_up if status == PredictionStatus.SUCCESS else None,
        probability_down=(1.0 - prob_up) if status == PredictionStatus.SUCCESS else None,
        model_name="xgboost",
        model_version="xgboost_v1",
        model_metadata={"n_estimators": 100},
        data_quality=quality,
        is_probability_calibrated=False,
        probability_calibration="uncalibrated",
        expected_movement=None,
        expected_movement_status="UNSUPPORTED",
        error_message=error_message,
    )


def _create_mock_llm_result(
    symbol: str = "TCS",
    direction: LLMDirection = LLMDirection.UP,
    confidence: str = "HIGH",
    summary: str = "Strong earnings beat with steady order pipeline.",
) -> LLMReasoningResult:
    """Helper to create a deterministic mock LLMReasoningResult."""
    return LLMReasoningResult(
        symbol=symbol,
        direction=direction,
        reasoning_summary=summary,
        positive_factors=("Order book expansion 14% YoY", "Stable operating margins"),
        negative_factors=("Foreign exchange volatility",),
        downside_risks=("Global tech slowdown",),
        source_references=("Reuters: TCS Q3 Results",),
        confidence_assessment=confidence,
        model_version="gemma3:12b",
        generated_at=datetime.now(timezone.utc),
    )


# ==============================================================================
# 1. Weights and Schema Validation Tests
# ==============================================================================

class TestEnsembleWeights:
    """Test weight normalization and bounds validation."""

    def test_default_weights_normalized(self) -> None:
        w = EnsembleWeights()
        assert w.ml_weight == 0.70
        assert w.llm_weight == 0.30
        assert round(w.ml_weight + w.llm_weight, 2) == 1.0

    def test_custom_weights_normalization(self) -> None:
        w = EnsembleWeights(ml_weight=4.0, llm_weight=1.0)
        assert w.ml_weight == 0.80
        assert w.llm_weight == 0.20

    def test_negative_weight_raises_error(self) -> None:
        with pytest.raises(ValidationError, match="Weights must be non-negative"):
            EnsembleWeights(ml_weight=-0.5, llm_weight=0.5)

    def test_zero_sum_weights_raises_error(self) -> None:
        with pytest.raises(ValidationError, match="greater than zero"):
            EnsembleWeights(ml_weight=0.0, llm_weight=0.0)


# ==============================================================================
# 2. Agreement & Divergence Categorization Tests
# ==============================================================================

class TestEnsembleAgreement:
    """Test classification of consensus and divergence between ML and LLM."""

    def test_strong_agreement_up(self) -> None:
        ml = _create_mock_ml_result(direction="UP", prob_up=0.68)
        llm = _create_mock_llm_result(direction=LLMDirection.UP, confidence="HIGH")
        service = EnsembleService()
        result = service.synthesize(ml, llm)
        assert result.agreement_status == EnsembleAgreement.STRONG_AGREEMENT
        assert result.combined_direction == "UP"

    def test_agreement_moderate(self) -> None:
        ml = _create_mock_ml_result(direction="UP", prob_up=0.53)
        llm = _create_mock_llm_result(direction=LLMDirection.UP, confidence="LOW")
        service = EnsembleService()
        result = service.synthesize(ml, llm)
        assert result.agreement_status == EnsembleAgreement.AGREEMENT
        assert result.combined_direction == "UP"

    def test_divergence_ml_up_llm_down(self) -> None:
        ml = _create_mock_ml_result(direction="UP", prob_up=0.60)
        llm = _create_mock_llm_result(direction=LLMDirection.DOWN, confidence="HIGH")
        service = EnsembleService()
        result = service.synthesize(ml, llm)
        assert result.agreement_status == EnsembleAgreement.DIVERGENCE

    def test_divergence_ml_down_llm_up(self) -> None:
        ml = _create_mock_ml_result(direction="DOWN", prob_up=0.35)
        llm = _create_mock_llm_result(direction=LLMDirection.UP, confidence="MEDIUM")
        service = EnsembleService()
        result = service.synthesize(ml, llm)
        assert result.agreement_status == EnsembleAgreement.DIVERGENCE

    def test_partial_when_llm_insufficient_evidence(self) -> None:
        ml = _create_mock_ml_result(direction="UP", prob_up=0.58)
        llm = _create_mock_llm_result(direction=LLMDirection.INSUFFICIENT_EVIDENCE, confidence="LOW")
        service = EnsembleService()
        result = service.synthesize(ml, llm)
        assert result.agreement_status == EnsembleAgreement.PARTIAL

    def test_ml_only_when_llm_is_none(self) -> None:
        ml = _create_mock_ml_result(direction="UP", prob_up=0.62)
        service = EnsembleService()
        result = service.synthesize(ml, llm_result=None)
        assert result.agreement_status == EnsembleAgreement.ML_ONLY
        assert result.combined_probability_up == 0.62
        assert result.weights_used["ml"] == 1.0
        assert result.weights_used["llm"] == 0.0


# ==============================================================================
# 3. Probability Blending & Independent Score Preservation
# ==============================================================================

class TestEnsembleSynthesis:
    """Test mathematical probability blending and preservation of standalone scores."""

    def test_probability_calculation_mathematics(self) -> None:
        # ML: P(UP) = 0.70
        # LLM: UP with HIGH confidence -> polarity = 1.0, implied P = 1.0
        # Default weights: ML = 0.70, LLM = 0.30
        # Expected combined P(UP) = (0.70 * 0.70) + (0.30 * 1.0) = 0.49 + 0.30 = 0.79
        ml = _create_mock_ml_result(direction="UP", prob_up=0.70)
        llm = _create_mock_llm_result(direction=LLMDirection.UP, confidence="HIGH")
        service = EnsembleService()
        res = service.synthesize(ml, llm)

        assert pytest.approx(res.combined_probability_up, 0.001) == 0.79
        assert pytest.approx(res.combined_probability_down, 0.001) == 0.21
        assert res.combined_direction == "UP"
        assert res.combined_label == 1

    def test_independent_outputs_preserved(self) -> None:
        ml = _create_mock_ml_result(direction="UP", prob_up=0.65)
        llm = _create_mock_llm_result(direction=LLMDirection.DOWN, confidence="LOW")
        service = EnsembleService()
        res = service.synthesize(ml, llm)

        # Verify standalone ML prediction is preserved in full
        assert res.ml_prediction is not None
        assert res.ml_prediction.model_name == "xgboost"
        assert res.ml_prediction.probability_up == 0.65

        # Verify standalone LLM reasoning is preserved in full
        assert res.llm_reasoning is not None
        assert res.llm_reasoning.direction == LLMDirection.DOWN
        assert res.llm_reasoning.model_version == "gemma3:12b"

        # Serialization to dict preserves both
        d = res.to_dict()
        assert d["ml_prediction"]["model_name"] == "xgboost"
        assert d["llm_reasoning"]["direction"] == "DOWN"

    def test_target_range_calculation(self) -> None:
        ml = _create_mock_ml_result(direction="UP", prob_up=0.60)
        llm = _create_mock_llm_result(direction=LLMDirection.UP)
        service = EnsembleService()
        res = service.synthesize(
            ml,
            llm,
            current_price=3500.0,
            atr_value=45.5,
        )

        assert res.target_range is not None
        assert res.target_range.reference_price == 3500.0
        assert res.target_range.lower_bound == 3454.5
        assert res.target_range.upper_bound == 3545.5
        assert res.target_range.method == "atr_14"

    def test_integrated_factor_rankings(self) -> None:
        ml = _create_mock_ml_result(direction="UP", prob_up=0.65)
        llm = _create_mock_llm_result(direction=LLMDirection.UP)
        service = EnsembleService()
        res = service.synthesize(ml, llm)

        assert len(res.integrated_positive_factors) >= 2
        assert any("Order book expansion" in f for f in res.integrated_positive_factors)
        assert any("Quantitative xgboost signal" in f for f in res.integrated_positive_factors)
        assert len(res.downside_risks) >= 1
        assert "Global tech slowdown" in res.downside_risks
        assert res.disclaimer == ENSEMBLE_DISCLAIMER


# ==============================================================================
# 4. Canonical PredictionResult Adaptation & Database Persistence
# ==============================================================================

class TestEnsemblePersistenceAndVerification:
    """Test adaptation to canonical PredictionResult, SQLite storage, and outcome verification."""

    def test_to_prediction_result_conversion(self) -> None:
        ml = _create_mock_ml_result(direction="UP", prob_up=0.70)
        llm = _create_mock_llm_result(direction=LLMDirection.UP)
        service = EnsembleService()
        ensemble_res = service.synthesize(ml, llm, current_price=3500.0, atr_value=50.0)

        adapted = ensemble_res.to_prediction_result()
        assert isinstance(adapted, PredictionResult)
        assert adapted.model_name == "ensemble"
        assert adapted.model_version == "ensemble_v1"
        assert adapted.predicted_direction == "UP"
        assert adapted.predicted_label == 1
        assert adapted.probability_up == ensemble_res.combined_probability_up
        assert adapted.expected_movement == 50.0  # upper_bound - current_price
        assert adapted.expected_movement_status == "RANGE_HIGH_ATR_14"
        assert adapted.model_metadata["agreement_status"] == "STRONG_AGREEMENT"

    def test_sqlite_persistence_and_outcome_verification(self) -> None:
        """Verify that an ensemble prediction can be saved to SQLite and verified against actuals."""
        conn = create_connection(":memory:")
        repo = PredictionRepository(conn=conn)

        ml = _create_mock_ml_result(symbol="INFY", direction="UP", prob_up=0.68)
        llm = _create_mock_llm_result(symbol="INFY", direction=LLMDirection.UP)
        service = EnsembleService(repository=repo)

        # Synthesize and adapt
        ens_res = service.synthesize(ml, llm, current_price=1800.0, atr_value=25.0)
        adapted = ens_res.to_prediction_result()

        # Save to database
        pred_id = repo.save_prediction(adapted)
        assert pred_id is not None

        # Verify it was saved with model_name='ensemble'
        saved = repo.get_prediction(pred_id)
        assert saved["model_name"] == "ensemble"
        assert saved["predicted_direction"] == "UP"
        assert saved["symbol"] == "INFY"

        bars = [
            MarketOHLCV(
                symbol="INFY",
                timestamp=datetime(2026, 10, 15, 15, 30, tzinfo=timezone.utc),
                open=1795.0, high=1805.0, low=1790.0, close=1800.0, volume=100000,
                source="yfinance",
            ),
            MarketOHLCV(
                symbol="INFY",
                timestamp=datetime(2026, 10, 16, 15, 30, tzinfo=timezone.utc),
                open=1802.0, high=1830.0, low=1800.0, close=1825.0, volume=120000,
                source="yfinance",
            ),
        ]

        verifier = OutcomeVerifier(repository=repo)
        v_record = verifier.verify_prediction(pred_id, market_bars=bars, persist=True)

        assert v_record.status.value == "VERIFIED"
        assert v_record.actual_direction == "UP"
        assert v_record.is_correct is True

        # Ensure actual outcome record was written
        actuals = repo.get_actual(pred_id)
        assert actuals is not None
        assert actuals["actual_direction"] == "UP"


# ==============================================================================
# 5. Failure Handling & Degradation Tests
# ==============================================================================

class TestEnsembleFailureHandling:
    """Test degradation behavior under component failures and missing inputs."""

    def test_ml_failure_propagates_error(self) -> None:
        ml = _create_mock_ml_result(
            direction=None,
            prob_up=None,
            status=PredictionStatus.INSUFFICIENT_DATA,
            error_message="Only 10 bars available; minimum 34 required.",
        )
        llm = _create_mock_llm_result()
        service = EnsembleService()
        res = service.synthesize(ml, llm)

        assert res.status == PredictionStatus.INSUFFICIENT_DATA
        assert res.combined_direction is None
        assert res.combined_probability_up is None
        assert "ML prediction failed" in (res.error_message or "")
        assert res.agreement_status == EnsembleAgreement.LLM_ONLY

    def test_llm_exception_in_predict_ensemble_falls_back_to_ml(self) -> None:
        """When LLM raises an unhandled error, predict_ensemble must degrade to ML_ONLY rather than crash."""
        class FailingLLMService:
            def generate_qualitative_reasoning(self, *args, **kwargs):
                raise RuntimeError("Ollama connection reset by peer")

        class MockPredService:
            def predict(self, *args, **kwargs):
                return _create_mock_ml_result(symbol="RELIANCE", direction="DOWN", prob_up=0.38)

        service = EnsembleService(
            prediction_service=MockPredService(),
            llm_service=FailingLLMService(),
        )

        req = PredictionRequest(symbol="RELIANCE", model_name="xgboost")
        res = service.predict_ensemble(request=req, articles=[{"headline": "Some news"}])

        assert res.status == PredictionStatus.SUCCESS
        assert res.agreement_status == EnsembleAgreement.ML_ONLY
        assert res.combined_direction == "DOWN"
        assert res.combined_probability_up == 0.38
        assert res.weights_used["ml"] == 1.0
        assert res.weights_used["llm"] == 0.0

    def test_format_summary_renders_cleanly(self) -> None:
        ml = _create_mock_ml_result(direction="UP", prob_up=0.65)
        llm = _create_mock_llm_result(direction=LLMDirection.UP)
        service = EnsembleService()
        res = service.synthesize(ml, llm, current_price=2500.0, atr_value=30.0)

        summary = res.format_summary()
        assert "Multi-Agent Ensemble Prediction for TCS" in summary
        assert "STRONG_AGREEMENT" in summary
        assert "P(UP)=75.50%" in summary
        assert "Target Range (1d)" in summary
        assert "Global tech slowdown" in summary
