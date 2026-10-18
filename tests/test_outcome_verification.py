"""Focused Automated Unit Tests for Day 25 Prediction Outcome Verification and Evaluation.

Validates:
1. ActualOutcome contract validation (bounds, positive prices, valid directions).
2. Actual outcome persistence and retrieval via PredictionRepository.
3. Idempotent repeated outcome verification (safe re-runs).
4. Conflicting outcome rejection (cannot overwrite realized facts).
5. Immutability triggers on actuals table (preventing UPDATE and DELETE).
6. Correct vs incorrect directional verification (UP, DOWN, zero-return policy).
7. Pending target session handling (when session t+1 has not yet completed).
8. Weekend and market-holiday handling (non-calendar session spacing).
9. Missing and incomplete market data handling.
10. Ineligible predictions (failed predictions cannot have outcomes).
11. Invalid and non-positive price safety.
12. Evaluator directional accuracy calculation and denominator correctness.
13. Evaluator zero-division safety and insufficient sample handling.
14. Symmetrical class metrics (Precision, Recall, F1 for UP and DOWN).
15. Preservation of original immutable prediction records.
"""

from datetime import datetime, timedelta, timezone
import sqlite3
from typing import Optional
import pytest

from app.core.schemas import MarketOHLCV
from app.database.connection import create_connection
from app.database.repository import PredictionRepository
from app.history.contract import (
    ActualOutcome,
    EvaluationMetrics,
    VerificationRecord,
    VerificationStatus,
)
from app.history.evaluator import PredictionEvaluator
from app.history.verifier import OutcomeVerifier, parse_session_date
from app.market.providers.base import BaseMarketDataProvider
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionResult,
    PredictionStatus,
)


class MockProvider(BaseMarketDataProvider):
    """Deterministic in-memory mock provider for testing without network calls."""

    def __init__(self, bars: Optional[list] = None) -> None:
        self._bars = list(bars or [])

    @property
    def name(self) -> str:
        return "mock_provider"

    def fetch_historical_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ):
        return [
            b for b in self._bars
            if b.symbol == symbol.strip().upper() and start_date <= b.timestamp <= end_date
        ]


@pytest.fixture
def in_memory_repo():
    """Create isolated in-memory PredictionRepository."""
    conn = create_connection(":memory:")
    repo = PredictionRepository(conn=conn)
    yield repo
    repo.close()


def make_dummy_prediction(
    repo: PredictionRepository,
    pid: str = "pred-001",
    symbol: str = "BHARTIARTL",
    pred_dir: str = "UP",
    pred_lbl: int = 1,
    status: PredictionStatus = PredictionStatus.SUCCESS,
    latest_bar_ts: str = "2026-10-14T00:00:00+05:30",
    model_name: str = "xgboost",
) -> str:
    """Helper to save a valid dummy PredictionResult into repository."""
    dq = PredictionDataQuality(
        total_bars_fetched=100,
        cleaned_bars=100,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp=latest_bar_ts,
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=0,
    )
    result = PredictionResult(
        symbol=symbol,
        prediction_timestamp="2026-10-14T10:00:00+00:00",
        latest_input_timestamp=latest_bar_ts,
        status=status,
        predicted_direction=pred_dir if status == PredictionStatus.SUCCESS else None,
        predicted_label=pred_lbl if status == PredictionStatus.SUCCESS else None,
        probability_up=0.58 if status == PredictionStatus.SUCCESS else None,
        probability_down=0.42 if status == PredictionStatus.SUCCESS else None,
        is_probability_calibrated=False,
        probability_calibration="uncalibrated",
        expected_movement=None,
        expected_movement_status="UNSUPPORTED",
        model_name=model_name,
        model_version=f"{model_name}-direction-v1",
        model_metadata={},
        data_quality=dq,
        error_message=None if status == PredictionStatus.SUCCESS else "Synthetic error",
    )
    return repo.save_prediction(result, prediction_id=pid)


def make_bar(
    symbol: str,
    ts: datetime,
    close: float,
    open_: Optional[float] = None,
) -> MarketOHLCV:
    """Helper to construct physical MarketOHLCV bar."""
    o = open_ or close
    h = max(o, close) * 1.01
    l = max(0.01, min(o, close) * 0.99)
    return MarketOHLCV(
        symbol=symbol,
        timestamp=ts,
        open=o,
        high=h,
        low=l,
        close=close,
        volume=100000,
        source="mock",
    )


# ==============================================================================
# 1. Contract & Schema Validation Tests
# ==============================================================================


def test_actual_outcome_contract_validation():
    """Verify ActualOutcome enforces field types, direction labels, and positive prices."""
    # Valid construction
    outcome = ActualOutcome(
        prediction_id="p-1",
        symbol="BHARTIARTL",
        target_date="2026-10-15T00:00:00+05:30",
        actual_direction="UP",
        actual_label=1,
        actual_return=0.015,
        actual_close=1015.0,
        reference_close=1000.0,
    )
    assert outcome.actual_direction == "UP"
    assert outcome.actual_label == 1
    assert outcome.actual_close == 1015.0

    # Invalid direction
    with pytest.raises(ValueError, match="actual_direction must be 'UP' or 'DOWN'"):
        ActualOutcome(
            prediction_id="p-1",
            symbol="BHARTIARTL",
            target_date="2026-10-15",
            actual_direction="SIDEWAYS",
            actual_label=1,
            actual_return=0.0,
            actual_close=1000.0,
        )

    # Negative close price
    with pytest.raises(ValueError, match="actual_close must be a positive finite float"):
        ActualOutcome(
            prediction_id="p-1",
            symbol="BHARTIARTL",
            target_date="2026-10-15",
            actual_direction="DOWN",
            actual_label=0,
            actual_return=-0.05,
            actual_close=-50.0,
        )


def test_save_actual_and_retrieve_from_repository(in_memory_repo: PredictionRepository):
    """Verify saving and retrieving an actual outcome linked to a prediction."""
    pid = make_dummy_prediction(in_memory_repo, pid="test-pred-act-1")

    outcome = ActualOutcome(
        prediction_id=pid,
        symbol="BHARTIARTL",
        target_date="2026-10-15T00:00:00+05:30",
        actual_direction="UP",
        actual_label=1,
        actual_return=0.0125,
        actual_close=1012.5,
        reference_close=1000.0,
        source="mock",
    )
    saved_pid = in_memory_repo.save_actual(outcome)
    assert saved_pid == pid

    # Retrieve standalone actual
    rec = in_memory_repo.get_actual(pid)
    assert rec is not None
    assert rec["symbol"] == "BHARTIARTL"
    assert rec["actual_direction"] == "UP"
    assert rec["actual_label"] == 1
    assert rec["actual_close"] == 1012.5
    assert rec["reference_close"] == 1000.0
    assert rec["source"] == "mock"

    # Retrieve joined prediction with actual
    joined = in_memory_repo.get_prediction_with_actual(pid)
    assert joined is not None
    assert joined["predicted_direction"] == "UP"
    assert joined["actual_direction"] == "UP"
    assert joined["actual_close"] == 1012.5


def test_save_actual_idempotency_repeated_verification(in_memory_repo: PredictionRepository):
    """Verify that repeated verification with identical actual outcome is idempotent."""
    pid = make_dummy_prediction(in_memory_repo, pid="test-pred-idemp")

    outcome = ActualOutcome(
        prediction_id=pid,
        symbol="BHARTIARTL",
        target_date="2026-10-15T00:00:00+05:30",
        actual_direction="DOWN",
        actual_label=0,
        actual_return=-0.01,
        actual_close=990.0,
        reference_close=1000.0,
    )
    # First save
    in_memory_repo.save_actual(outcome)
    assert in_memory_repo.count_actuals() == 1

    # Second save with identical values (should succeed as no-op)
    saved_pid = in_memory_repo.save_actual(outcome)
    assert saved_pid == pid
    assert in_memory_repo.count_actuals() == 1


def test_save_actual_conflicting_record_rejected(in_memory_repo: PredictionRepository):
    """Verify attempting to save a conflicting actual outcome raises ValueError."""
    pid = make_dummy_prediction(in_memory_repo, pid="test-pred-conflict")

    outcome1 = ActualOutcome(
        prediction_id=pid,
        symbol="BHARTIARTL",
        target_date="2026-10-15T00:00:00+05:30",
        actual_direction="DOWN",
        actual_label=0,
        actual_return=-0.01,
        actual_close=990.0,
    )
    in_memory_repo.save_actual(outcome1)

    # Attempt conflicting save with opposite direction and price
    outcome2 = ActualOutcome(
        prediction_id=pid,
        symbol="BHARTIARTL",
        target_date="2026-10-15T00:00:00+05:30",
        actual_direction="UP",
        actual_label=1,
        actual_return=0.02,
        actual_close=1020.0,
    )
    with pytest.raises(ValueError, match="Conflicting actual outcome already recorded"):
        in_memory_repo.save_actual(outcome2)


def test_actuals_immutability_triggers(in_memory_repo: PredictionRepository):
    """Verify SQLite triggers prevent any direct UPDATE or DELETE on actuals table."""
    pid = make_dummy_prediction(in_memory_repo, pid="test-pred-trig")
    outcome = ActualOutcome(
        prediction_id=pid,
        symbol="BHARTIARTL",
        target_date="2026-10-15T00:00:00+05:30",
        actual_direction="UP",
        actual_label=1,
        actual_return=0.01,
        actual_close=1010.0,
    )
    in_memory_repo.save_actual(outcome)

    # Test UPDATE trigger
    with pytest.raises(sqlite3.DatabaseError) as exc_update:
        in_memory_repo.connection.execute(
            "UPDATE actuals SET actual_direction = 'DOWN' WHERE prediction_id = ?;",
            (pid,),
        )
    assert "Actual outcomes are immutable: updates are strictly prohibited" in str(exc_update.value)

    # Test DELETE trigger
    with pytest.raises(sqlite3.DatabaseError) as exc_delete:
        in_memory_repo.connection.execute(
            "DELETE FROM actuals WHERE prediction_id = ?;",
            (pid,),
        )
    assert "Actual outcomes are immutable: deletions are strictly prohibited" in str(exc_delete.value)


# ==============================================================================
# 2. Outcome Verification Logic Tests
# ==============================================================================


def test_verification_correct_and_incorrect_directional_outcomes(in_memory_repo: PredictionRepository):
    """Verify OutcomeVerifier correctly checks direction against market outcome."""
    # Prediction 1: Predicted UP (Correct)
    pid1 = make_dummy_prediction(in_memory_repo, pid="p-1", pred_dir="UP", pred_lbl=1, latest_bar_ts="2026-10-14")
    # Prediction 2: Predicted UP (Incorrect, actual DOWN)
    pid2 = make_dummy_prediction(in_memory_repo, pid="p-2", pred_dir="UP", pred_lbl=1, latest_bar_ts="2026-10-14")
    # Prediction 3: Predicted DOWN (Correct via zero-return rule)
    pid3 = make_dummy_prediction(in_memory_repo, pid="p-3", pred_dir="DOWN", pred_lbl=0, latest_bar_ts="2026-10-14")

    t0 = datetime(2026, 10, 14, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)

    # 1. Bars where next close is higher (1000 -> 1020, UP)
    bars_up = [make_bar("BHARTIARTL", t0, 1000.0), make_bar("BHARTIARTL", t1, 1020.0)]
    verifier = OutcomeVerifier(in_memory_repo)
    res1 = verifier.verify_prediction(pid1, market_bars=bars_up, persist=True)
    assert res1.status == VerificationStatus.VERIFIED
    assert res1.is_correct is True
    assert res1.actual_direction == "UP"
    assert res1.actual_return == 0.02

    # 2. Bars where next close is lower (1000 -> 980, DOWN)
    bars_down = [make_bar("BHARTIARTL", t0, 1000.0), make_bar("BHARTIARTL", t1, 980.0)]
    res2 = verifier.verify_prediction(pid2, market_bars=bars_down, persist=True)
    assert res2.status == VerificationStatus.VERIFIED
    assert res2.is_correct is False
    assert res2.actual_direction == "DOWN"
    assert res2.actual_return == -0.02

    # 3. Bars where next close is equal (1000 -> 1000, DOWN per binary rule)
    bars_flat = [make_bar("BHARTIARTL", t0, 1000.0), make_bar("BHARTIARTL", t1, 1000.0)]
    res3 = verifier.verify_prediction(pid3, market_bars=bars_flat, persist=True)
    assert res3.status == VerificationStatus.VERIFIED
    assert res3.is_correct is True
    assert res3.actual_direction == "DOWN"
    assert res3.actual_return == 0.0


def test_verification_pending_target_session(in_memory_repo: PredictionRepository):
    """Verify that when session t+1 has not occurred yet, outcome is returned as PENDING."""
    pid = make_dummy_prediction(in_memory_repo, pid="p-pending", latest_bar_ts="2026-10-14")
    t0 = datetime(2026, 10, 14, 0, 0, tzinfo=timezone.utc)

    # Market bars only contain session t (no session t+1 exists yet)
    bars = [make_bar("BHARTIARTL", t0, 1000.0)]

    verifier = OutcomeVerifier(in_memory_repo)
    record = verifier.verify_prediction(pid, market_bars=bars, persist=True)

    assert record.status == VerificationStatus.PENDING
    assert record.is_correct is None
    assert record.actual_direction is None
    # Confirm outcome was NOT persisted to actuals
    assert in_memory_repo.get_actual(pid) is None


def test_verification_weekend_and_market_holiday_handling(in_memory_repo: PredictionRepository):
    """Verify outcome correctly bridges non-calendar gaps (weekends/holidays)."""
    # Prediction made on Friday (2026-10-09)
    pid = make_dummy_prediction(in_memory_repo, pid="p-weekend", latest_bar_ts="2026-10-09")

    fri = datetime(2026, 10, 9, 0, 0, tzinfo=timezone.utc)
    mon = datetime(2026, 10, 12, 0, 0, tzinfo=timezone.utc)  # Monday session (3 days later)

    bars = [make_bar("BHARTIARTL", fri, 1000.0), make_bar("BHARTIARTL", mon, 1030.0)]

    verifier = OutcomeVerifier(in_memory_repo)
    record = verifier.verify_prediction(pid, market_bars=bars, persist=True)

    assert record.status == VerificationStatus.VERIFIED
    assert record.target_date == mon.isoformat()
    assert record.actual_direction == "UP"
    assert record.actual_return == 0.03
    assert record.is_correct is True


def test_verification_missing_or_incomplete_market_data(in_memory_repo: PredictionRepository):
    """Verify handling when reference date is not in market data or bars empty."""
    pid = make_dummy_prediction(in_memory_repo, pid="p-missing", latest_bar_ts="2026-10-14")
    verifier = OutcomeVerifier(in_memory_repo)

    # Empty bars
    rec1 = verifier.verify_prediction(pid, market_bars=[], persist=True)
    assert rec1.status == VerificationStatus.DATA_UNAVAILABLE

    # Reference bar date missing in bars
    other_bar = make_bar("BHARTIARTL", datetime(2026, 1, 1, tzinfo=timezone.utc), 1000.0)
    rec2 = verifier.verify_prediction(pid, market_bars=[other_bar], persist=True)
    assert rec2.status == VerificationStatus.DATA_UNAVAILABLE
    assert "Reference session date" in rec2.message


def test_verification_ineligible_predictions(in_memory_repo: PredictionRepository):
    """Verify that failed/ineligible predictions are cleanly marked INELIGIBLE."""
    # Failed prediction with status MODEL_UNAVAILABLE
    pid_fail = make_dummy_prediction(
        in_memory_repo,
        pid="p-inelig",
        status=PredictionStatus.MODEL_UNAVAILABLE,
    )
    verifier = OutcomeVerifier(in_memory_repo)
    rec = verifier.verify_prediction(pid_fail)
    assert rec.status == VerificationStatus.INELIGIBLE
    assert "only SUCCESS predictions" in rec.message


def test_verification_invalid_prices_handling(in_memory_repo: PredictionRepository):
    """Verify that non-positive prices in market bars return DATA_UNAVAILABLE safely."""
    pid = make_dummy_prediction(in_memory_repo, pid="p-inv-price", latest_bar_ts="2026-10-14")
    t0 = datetime(2026, 10, 14, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 15, tzinfo=timezone.utc)

    # Target bar has 0.0 close
    bars = [
        make_bar("BHARTIARTL", t0, 1000.0),
        make_bar("BHARTIARTL", t1, 0.01),  # physical validation requires > 0
    ]
    # Manually bypass physical validator to test division-by-zero protection in return calculator
    object.__setattr__(bars[1], "close", 0.0)

    verifier = OutcomeVerifier(in_memory_repo)
    rec = verifier.verify_prediction(pid, market_bars=bars, persist=True)
    assert rec.status == VerificationStatus.DATA_UNAVAILABLE
    assert "Non-positive" in rec.message


# ==============================================================================
# 3. Evaluation Service & Metrics Tests
# ==============================================================================


def test_evaluator_accuracy_and_denominator_correctness(in_memory_repo: PredictionRepository):
    """Verify that directional accuracy is computed STRICTLY over verified predictions."""
    # 4 predictions:
    # - p1: verified, correct (predicted UP, actual UP)
    # - p2: verified, incorrect (predicted UP, actual DOWN)
    # - p3: pending (no actual)
    # - p4: ineligible (status MODEL_UNAVAILABLE)
    pid1 = make_dummy_prediction(in_memory_repo, pid="p1", pred_dir="UP", pred_lbl=1)
    pid2 = make_dummy_prediction(in_memory_repo, pid="p2", pred_dir="UP", pred_lbl=1)
    pid3 = make_dummy_prediction(in_memory_repo, pid="p3", pred_dir="UP", pred_lbl=1)
    pid4 = make_dummy_prediction(in_memory_repo, pid="p4", status=PredictionStatus.MODEL_UNAVAILABLE)

    # Save actuals only for p1 and p2
    in_memory_repo.save_actual(ActualOutcome(
        prediction_id=pid1, symbol="BHARTIARTL", target_date="2026-10-15",
        actual_direction="UP", actual_label=1, actual_return=0.01, actual_close=1010.0
    ))
    in_memory_repo.save_actual(ActualOutcome(
        prediction_id=pid2, symbol="BHARTIARTL", target_date="2026-10-15",
        actual_direction="DOWN", actual_label=0, actual_return=-0.01, actual_close=990.0
    ))

    evaluator = PredictionEvaluator(in_memory_repo)
    metrics = evaluator.evaluate()

    assert metrics.total_predictions == 4
    assert metrics.eligible_predictions == 3
    assert metrics.ineligible_predictions == 1
    assert metrics.verified_predictions == 2  # The denominator!
    assert metrics.pending_predictions == 1   # p3 is pending, not in denominator!
    assert metrics.correct_predictions == 1
    assert metrics.incorrect_predictions == 1
    # Accuracy: 1 / 2 = 0.50 (50.0%)
    assert metrics.directional_accuracy == 0.50


def test_evaluator_insufficient_samples_zero_division_safety(in_memory_repo: PredictionRepository):
    """Verify that when 0 verified predictions exist, accuracy evaluates to None without errors."""
    # Save a pending prediction
    make_dummy_prediction(in_memory_repo, pid="p-only-pend")

    evaluator = PredictionEvaluator(in_memory_repo)
    metrics = evaluator.evaluate()

    assert metrics.total_predictions == 1
    assert metrics.verified_predictions == 0
    assert metrics.pending_predictions == 1
    assert metrics.directional_accuracy is None
    assert metrics.precision_up is None
    assert metrics.recall_up is None
    assert metrics.f1_up is None
    assert "N/A (no verified sessions)" in metrics.format_summary()


def test_evaluator_symmetrical_class_metrics_and_breakdowns(in_memory_repo: PredictionRepository):
    """Verify confusion matrix, symmetrical class metrics, and group breakdowns."""
    # Create 4 verified predictions:
    # TP: pred UP, act UP
    pid_tp = make_dummy_prediction(in_memory_repo, pid="tp", pred_dir="UP", pred_lbl=1, model_name="xgboost")
    in_memory_repo.save_actual(ActualOutcome(pid_tp, "BHARTIARTL", "2026-10-15", "UP", 1, 0.01, 1010.0))

    # FP: pred UP, act DOWN
    pid_fp = make_dummy_prediction(in_memory_repo, pid="fp", pred_dir="UP", pred_lbl=1, model_name="xgboost")
    in_memory_repo.save_actual(ActualOutcome(pid_fp, "BHARTIARTL", "2026-10-15", "DOWN", 0, -0.01, 990.0))

    # TN: pred DOWN, act DOWN
    pid_tn = make_dummy_prediction(in_memory_repo, pid="tn", pred_dir="DOWN", pred_lbl=0, model_name="lightgbm")
    in_memory_repo.save_actual(ActualOutcome(pid_tn, "BHARTIARTL", "2026-10-15", "DOWN", 0, -0.01, 990.0))

    # FN: pred DOWN, act UP
    pid_fn = make_dummy_prediction(in_memory_repo, pid="fn", pred_dir="DOWN", pred_lbl=0, model_name="lightgbm")
    in_memory_repo.save_actual(ActualOutcome(pid_fn, "BHARTIARTL", "2026-10-15", "UP", 1, 0.01, 1010.0))

    evaluator = PredictionEvaluator(in_memory_repo)
    metrics = evaluator.evaluate()

    assert metrics.verified_predictions == 4
    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.true_negatives == 1
    assert metrics.false_negatives == 1

    # Precision UP: 1 / (1 + 1) = 0.50
    # Recall UP: 1 / (1 + 1) = 0.50
    # F1 UP: 0.50
    assert metrics.precision_up == 0.50
    assert metrics.recall_up == 0.50
    assert metrics.f1_up == 0.50

    # Precision DOWN: 1 / (1 + 1) = 0.50
    # Recall DOWN: 1 / (1 + 1) = 0.50
    # F1 DOWN: 0.50
    assert metrics.precision_down == 0.50
    assert metrics.recall_down == 0.50
    assert metrics.f1_down == 0.50

    # Breakdown by model
    assert "xgboost" in metrics.by_model
    assert "lightgbm" in metrics.by_model
    assert metrics.by_model["xgboost"]["total"] == 2
    assert metrics.by_model["xgboost"]["directional_accuracy"] == 0.50
    assert metrics.by_model["lightgbm"]["total"] == 2
    assert metrics.by_model["lightgbm"]["directional_accuracy"] == 0.50


def test_evaluator_preservation_of_immutable_prediction_records(in_memory_repo: PredictionRepository):
    """Verify that running verification and evaluation does not alter the original prediction records."""
    pid = make_dummy_prediction(in_memory_repo, pid="p-check-immut")
    pred_before = in_memory_repo.get_prediction(pid)

    t0 = datetime(2026, 10, 14, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 15, tzinfo=timezone.utc)
    bars = [make_bar("BHARTIARTL", t0, 1000.0), make_bar("BHARTIARTL", t1, 1010.0)]

    verifier = OutcomeVerifier(in_memory_repo)
    verifier.verify_prediction(pid, market_bars=bars, persist=True)

    evaluator = PredictionEvaluator(in_memory_repo)
    evaluator.evaluate()

    pred_after = in_memory_repo.get_prediction(pid)

    # Every single field in predictions table must be identical
    assert pred_before == pred_after
    assert pred_after["predicted_direction"] == "UP"
    assert pred_after["is_probability_calibrated"] == 0
    assert pred_after["probability_calibration"] == "uncalibrated"
    assert pred_after["expected_movement"] is None
    assert pred_after["expected_movement_status"] == "UNSUPPORTED"
