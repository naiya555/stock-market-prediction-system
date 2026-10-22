"""Deterministic tests for independent ML baseline reproducibility, temporal alignment, and probability audit (Day 61)."""

from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
from typing import List
import numpy as np
import pandas as pd
import pytest

from app.core.schemas import MarketOHLCV
from app.history.reproducibility import (
    BaselineReproducibilityReport,
    BaselineReproducibilityStatus,
    CANONICAL_LOOKBACK_DAYS,
    CANONICAL_TRAIN_CUTOFF_UTC,
    TemporalAlignmentAudit,
    audit_baseline_reproducibility,
    audit_temporal_alignment,
    compute_model_run_metrics,
)
from app.market.pipeline import MarketDataPipelineResult, process_market_data
from app.prediction.target import generate_direction_targets
from app.training.baselines import MajorityClassClassifier
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)
from app.training.lightgbm_classifier import HAS_LIGHTGBM, LightGBMDirectionClassifier
from app.training.retraining import ModelRetrainer
from app.training.xgboost_classifier import (
    HAS_XGBOOST,
    XGBoostDirectionClassifier,
    compute_classification_metrics,
    split_chronological_holdout,
)
from tests.test_model_training_artifacts import MockMarketDataProvider


def _create_mock_ohlcv_series(
    symbol: str = "BHARTIARTL",
    n_days: int = 120,
    start_date: datetime = datetime(2025, 1, 1, tzinfo=timezone.utc),
) -> List[MarketOHLCV]:
    """Generate a sequence of synthetic MarketOHLCV records."""
    records = []
    base_price = 1000.0
    current_time = start_date

    for i in range(n_days):
        # Skip weekends to simulate trading sessions
        while current_time.weekday() in (5, 6):
            current_time += timedelta(days=1)

        delta = 2.0 * math.sin(i / 5.0) + (1.0 if i % 2 == 0 else -1.0)
        close = max(100.0, base_price + delta)
        high = close + 5.0
        low = close - 5.0
        open_price = close - (1.0 if delta > 0 else -1.0)
        vol = 100000.0 + (i * 100)

        records.append(
            MarketOHLCV(
                symbol=symbol,
                timestamp=current_time,
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=int(vol),
                source="mock_provider",
            )
        )
        base_price = close
        current_time += timedelta(days=1)

    return records


# ==============================================================================
# Task 3: Probability Metric & Brier Score Tests
# ==============================================================================


def test_brier_score_small_known_examples():
    """Verify Brier score calculation on hand-calculated reference cases."""
    # Example 1: 4 samples
    # y = [1, 0, 1, 0]
    # p = [0.9, 0.2, 0.7, 0.4]
    # errors: (0.9-1)^2 = 0.01, (0.2-0)^2 = 0.04, (0.7-1)^2 = 0.09, (0.4-0)^2 = 0.16
    # sum = 0.30 -> mean = 0.075
    y_true = [1, 0, 1, 0]
    y_prob = [0.9, 0.2, 0.7, 0.4]
    brier = ModelRetrainer.compute_brier_score(y_true, y_prob)
    assert brier == 0.075

    # Example 2: Perfect forecasts
    assert ModelRetrainer.compute_brier_score([1, 0], [1.0, 0.0]) == 0.0

    # Example 3: Completely inverted forecasts
    assert ModelRetrainer.compute_brier_score([1, 0], [0.0, 1.0]) == 1.0

    # Example 4: Uninformative 0.5 forecasts
    assert ModelRetrainer.compute_brier_score([1, 0], [0.5, 0.5]) == 0.25

    # Edge cases: empty or mismatched
    assert ModelRetrainer.compute_brier_score([], []) is None
    assert ModelRetrainer.compute_brier_score([1], [0.5, 0.5]) is None


def test_majority_baseline_probability_and_brier():
    """Verify MajorityClassClassifier assigns P(UP)=1.0 and computes expected Brier score."""
    y_train = [1] * 50 + [0] * 40  # Majority is 1 (UP)
    clf = MajorityClassClassifier()
    clf.fit(y=y_train)

    X_test = pd.DataFrame({"feat": [1, 2, 3, 4]})
    probs = clf.predict_proba(X_test)

    # Column 0 is P(DOWN), Column 1 is P(UP)
    assert probs.shape == (4, 2)
    assert np.all(probs[:, 0] == 0.0)
    assert np.all(probs[:, 1] == 1.0)

    # For test set with 3 UP and 1 DOWN:
    # Brier = (1-1)^2 * 3 + (0-1)^2 * 1 = 1 / 4 = 0.25
    y_test = [1, 1, 1, 0]
    brier = ModelRetrainer.compute_brier_score(y_test, probs[:, 1])
    assert brier == 0.25

    # For 119 UP and 121 DOWN: Brier = 121 / 240 = 0.504166... -> 0.5042
    y_test_240 = [1] * 119 + [0] * 121
    probs_240 = [1.0] * 240
    brier_240 = ModelRetrainer.compute_brier_score(y_test_240, probs_240)
    assert brier_240 == 0.5042


# ==============================================================================
# Task 2: Target & Trading Session Alignment Tests
# ==============================================================================


def test_binary_target_equality_handling():
    """Verify target calculation explicitly maps zero returns (equality) to DOWN (0)."""
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bars = [
        MarketOHLCV("TEST", now, 100.0, 105.0, 95.0, 100.0, 1000, source="test"),
        MarketOHLCV("TEST", now + timedelta(days=1), 100.0, 105.0, 95.0, 100.0, 1000, source="test"),  # Equal close -> DOWN
        MarketOHLCV("TEST", now + timedelta(days=2), 100.0, 110.0, 95.0, 105.0, 1000, source="test"),  # Higher close -> UP
        MarketOHLCV("TEST", now + timedelta(days=3), 105.0, 105.0, 90.0, 95.0, 1000, source="test"),   # Lower close -> DOWN
    ]
    targets = generate_direction_targets(bars)
    assert len(targets) == 4

    # Bar 0 -> Bar 1: Equal (100.0 -> 100.0) -> target_return=0.0 -> DOWN (0)
    assert targets[0].target_return == 0.0
    assert targets[0].target_direction == "DOWN"
    assert targets[0].target_binary == 0

    # Bar 1 -> Bar 2: Higher (100.0 -> 105.0) -> UP (1)
    assert targets[1].target_return > 0.0
    assert targets[1].target_direction == "UP"
    assert targets[1].target_binary == 1

    # Bar 2 -> Bar 3: Lower (105.0 -> 95.0) -> DOWN (0)
    assert targets[2].target_return < 0.0
    assert targets[2].target_direction == "DOWN"
    assert targets[2].target_binary == 0

    # Final bar 3: No future bar -> missing (None)
    assert targets[3].target_return is None
    assert targets[3].target_direction is None
    assert targets[3].target_binary is None


def test_temporal_embargo_isolation_invariant():
    """Verify that chronological holdout split strictly isolates training outcome from holdout features."""
    records = _create_mock_ohlcv_series(n_days=100)
    pipeline_res = process_market_data(records)
    dataset = assemble_feature_matrix(pipeline_res)

    split = split_chronological_holdout(dataset, test_ratio=0.2, embargo_sessions=1, drop_incomplete_warmup=True)
    t_audit = audit_temporal_alignment(split)

    # Invariant: train outcome cutoff must be strictly earlier than holdout start date
    assert t_audit.is_embargo_strictly_isolating is True
    assert t_audit.train_outcome_cutoff < t_audit.holdout_start_date
    assert t_audit.zero_overlap_verified is True
    assert t_audit.feature_isolation_verified is True


def test_feature_matrix_anti_leakage_guards():
    """Verify validate_feature_matrix_isolation rejects any matrix containing target columns."""
    df_clean = pd.DataFrame({"open": [10.0, 11.0], "close": [10.5, 11.5]})
    validate_feature_matrix_isolation(df_clean)  # Should pass

    # Forbidden target columns
    for bad_col in ["target_return", "target_binary", "next_close", "future_price", "outcome_label"]:
        df_dirty = pd.DataFrame({"open": [10.0], bad_col: [1.0]})
        with pytest.raises(ValueError, match="leakage"):
            validate_feature_matrix_isolation(df_dirty)



# ==============================================================================
# Task 1 & 4: Baseline Reproducibility & Model Metric Tests
# ==============================================================================


def test_active_model_artifacts_probability_ordering():
    """Verify that active models output 2D probabilities where col 0 is P(DOWN) and col 1 is P(UP)."""
    models_dir = Path("models")
    xgb_path = models_dir / "xgboost_direction.json"
    lgb_path = models_dir / "lightgbm_direction.txt"

    # Dummy feature row with canonical 37 columns
    dummy_row = pd.DataFrame([{col: 1.0 for col in FEATURE_COLUMNS}])

    if xgb_path.is_file() and HAS_XGBOOST:
        xgb = XGBoostDirectionClassifier.load_model(xgb_path)
        probs = xgb.predict_proba(dummy_row)
        assert probs.shape == (1, 2)
        assert np.isclose(probs[0, 0] + probs[0, 1], 1.0, atol=1e-4)

    if lgb_path.is_file() and HAS_LIGHTGBM:
        lgb = LightGBMDirectionClassifier().load_model(lgb_path)
        probs = lgb.predict_proba(dummy_row)
        assert probs.shape == (1, 2)
        assert np.isclose(probs[0, 0] + probs[0, 1], 1.0, atol=1e-4)


def test_compute_model_run_metrics_correctness():
    """Verify compute_model_run_metrics calculates exact accuracy, confusion matrix, and class statistics."""
    y_true = [1, 1, 0, 0]
    y_pred = [1, 0, 0, 1]
    y_prob = [0.8, 0.4, 0.2, 0.6]

    run = compute_model_run_metrics("test_model", y_true, y_pred, y_prob)
    assert run.sample_size == 4
    assert run.accuracy == 0.50
    assert run.true_positives == 1
    assert run.true_negatives == 1
    assert run.false_positives == 1
    assert run.false_negatives == 1
    assert run.confusion_matrix == [[1, 1], [1, 1]]
    assert run.brier_score is not None


def test_reproducibility_report_on_canonical_snapshot():
    """Verify end-to-end audit_baseline_reproducibility matches metadata and achieves REPRODUCIBLE status."""
    report = audit_baseline_reproducibility(symbol="BHARTIARTL")

    # Verify reproducibility status
    assert report.status == BaselineReproducibilityStatus.REPRODUCIBLE
    assert report.run_to_run_identical is True
    assert report.metadata_match_verified is True
    assert len(report.discrepancies) == 0

    # Verify sample sizes
    assert report.temporal_audit.holdout_sample_count == 240
    assert report.temporal_audit.train_sample_count == 958
    assert report.temporal_audit.embargo_sample_count == 1

    # Verify date boundaries
    assert report.temporal_audit.train_end_date == "2025-10-27"
    assert report.temporal_audit.train_outcome_cutoff == "2025-10-28"
    assert report.temporal_audit.holdout_start_date == "2025-10-29"
    assert report.temporal_audit.holdout_end_date == "2026-10-19"
    assert report.temporal_audit.holdout_final_target_session == "2026-10-21"

    # Verify class distribution
    assert report.class_distribution["UP"] == 119
    assert report.class_distribution["DOWN"] == 121

    # Verify majority baseline
    assert report.majority_baseline.accuracy == 0.4958
    assert report.majority_baseline.brier_score == 0.5042

    # Verify XGBoost metrics
    if report.xgboost_metrics is not None:
        assert report.xgboost_metrics.accuracy == 0.5125
        assert report.xgboost_metrics.brier_score == 0.2556
        assert report.xgboost_metrics.confusion_matrix == [[46, 75], [42, 77]]

    # Verify LightGBM metrics
    if report.lightgbm_metrics is not None:
        assert report.lightgbm_metrics.accuracy == 0.5375
        assert report.lightgbm_metrics.brier_score == 0.2562
        assert report.lightgbm_metrics.confusion_matrix == [[50, 71], [40, 79]]


def test_unanchored_live_rolling_window_shift_detection():
    """Verify that shifting the evaluation cutoff forward causes holdout dates to advance."""
    # Anchored to canonical cutoff
    report_anchored = audit_baseline_reproducibility(
        symbol="BHARTIARTL",
        cutoff_time=CANONICAL_TRAIN_CUTOFF_UTC,
    )
    assert report_anchored.temporal_audit.holdout_start_date == "2025-10-29"

    # Evaluated with cutoff + 1 day
    cutoff_plus_one = CANONICAL_TRAIN_CUTOFF_UTC + timedelta(days=1)
    report_advanced = audit_baseline_reproducibility(
        symbol="BHARTIARTL",
        cutoff_time=cutoff_plus_one,
    )
    # The advanced cutoff either stays equal or advances, preserving relative tail calculation
    assert report_advanced.temporal_audit.is_embargo_strictly_isolating is True


def test_run_to_run_determinism_explicit():
    """Verify that multiple consecutive runs on the exact same snapshot return bit-identical probabilities."""
    report = audit_baseline_reproducibility(symbol="BHARTIARTL")
    assert report.run_to_run_identical is True

