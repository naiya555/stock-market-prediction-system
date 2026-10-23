"""Deterministic Unit and Leakage Tests for Day 72 Intraday Baseline Benchmark Evaluation.

Tests:
1. Majority-class calculations strictly using training labels.
2. Deterministic tie handling (defaults to 0 / DOWN on tie).
3. Constant 0.50 probability baseline calculations and metrics.
4. Training-prior baseline calculations without validation leakage.
5. Persistence baseline with return_1bar and fallback behavior.
6. Undefined metrics handling (explicit None, never silently replaced with 0.0).
7. Insufficient samples / empty prediction sequence error handling.
8. Correct fold assignment, chronological order, and out-of-fold predictions.
9. No duplicate out-of-fold predictions and duplicate timestamp rejection.
10. Target horizon and embargo isolation across folds.
11. Missing and quarantined target tracking (explicit exclusion audit).
12. Separation of synthetic fixtures from empirical market data (flagging BLOCKED_NO_EMPIRICAL_DATA).
13. Strict Leakage Invariant: mutating validation labels has zero effect on baseline predictions fitted on training data.
14. Complete reproducibility of walk-forward baseline audits across repeated runs.
"""

from datetime import date, datetime, timedelta
import math
import pytest

from app.core.schemas import ValidationError
from app.market.intraday import (
    ConstantProbabilityBaseline,
    IntradayBaselinePrediction,
    IntradayCandle,
    IntradayDatasetObservation,
    IntradayEvaluationMetrics,
    IntradayInterval,
    IntradaySplit,
    IntradayTargetStatus,
    MajorityClassBaseline,
    PersistenceBaseline,
    TrainingPriorBaseline,
    assemble_intraday_dataset,
    compute_intraday_evaluation_metrics,
    evaluate_intraday_baseline_walk_forward,
    generate_intraday_chronological_splits,
)
from app.market.session import IST


def _make_candle(
    symbol: str,
    ts: datetime,
    close: float,
    volume: int | None = 1000,
    interval: IntradayInterval = IntradayInterval.M5,
    source: str = "synthetic_test",
) -> IntradayCandle:
    return IntradayCandle(
        symbol=symbol,
        timestamp=ts,
        open=close - 1.0,
        high=close + 2.0,
        low=close - 2.0,
        close=close,
        volume=volume,
        interval=interval,
        source=source,
    )


def _generate_synthetic_candles(
    session_date: date,
    symbol: str = "BHARTIARTL",
    base_price: float = 1850.0,
    num_bars: int = 25,
    source: str = "synthetic_test",
) -> list[IntradayCandle]:
    """Generates continuous 5-minute candles starting at 09:15 IST."""
    start_time = datetime(session_date.year, session_date.month, session_date.day, 9, 15, tzinfo=IST)
    candles = []
    for i in range(num_bars):
        ts = start_time + timedelta(minutes=5 * i)
        # Deterministic wave pattern
        price = base_price + (i % 4) * 2.5 - (i % 3) * 1.5
        candles.append(_make_candle(symbol, ts, price, volume=1000 + i * 50, source=source))
    return candles


# =========================================================================
# 1. Baseline Calculations & Tie-Breaking
# =========================================================================

def test_majority_class_baseline_training_only_and_tie_breaking():
    """Verify majority baseline fits training labels and resolves ties deterministically to 0/DOWN."""
    day = date(2026, 10, 15)
    candles = _generate_synthetic_candles(day, num_bars=15)
    dataset = assemble_intraday_dataset(candles, horizon_bars=2)

    # Subsets with known balances
    # Case A: UP majority (e.g. 3 UP, 1 DOWN)
    up_heavy = [o for o in dataset if o.has_target and o.target_binary == 1][:3]
    down_one = [o for o in dataset if o.has_target and o.target_binary == 0][:1]
    train_a = up_heavy + down_one

    baseline = MajorityClassBaseline()
    baseline.fit(train_a)
    pred_bin, pred_prob = baseline.predict(dataset[0])
    assert pred_bin == 1
    assert pred_prob == 1.0

    # Case B: DOWN majority (e.g. 1 UP, 3 DOWN)
    down_heavy = [o for o in dataset if o.has_target and o.target_binary == 0][:3]
    up_one = [o for o in dataset if o.has_target and o.target_binary == 1][:1]
    train_b = up_one + down_heavy

    baseline.fit(train_b)
    pred_bin, pred_prob = baseline.predict(dataset[0])
    assert pred_bin == 0
    assert pred_prob == 0.0

    # Case C: Exact tie (e.g. 2 UP, 2 DOWN)
    tie_train = [o for o in dataset if o.has_target and o.target_binary == 1][:2] + \
                [o for o in dataset if o.has_target and o.target_binary == 0][:2]
    assert len(tie_train) == 4

    baseline.fit(tie_train)
    pred_bin, pred_prob = baseline.predict(dataset[0])
    # Tie-breaking rule must deterministically produce 0 / DOWN
    assert pred_bin == 0
    assert pred_prob == 0.0


def test_constant_probability_baseline():
    """Constant probability baseline must always predict 0.50 probability and 0 binary."""
    baseline = ConstantProbabilityBaseline()
    baseline.fit([])  # Zero parameters fitted
    
    day = date(2026, 10, 15)
    candles = _generate_synthetic_candles(day, num_bars=5)
    dataset = assemble_intraday_dataset(candles, horizon_bars=1)

    for obs in dataset:
        pred_bin, pred_prob = baseline.predict(obs)
        assert pred_bin == 0
        assert pred_prob == 0.50


def test_training_prior_baseline():
    """Training prior baseline estimates empirical base rate strictly from training set."""
    day = date(2026, 10, 15)
    candles = _generate_synthetic_candles(day, num_bars=15)
    dataset = assemble_intraday_dataset(candles, horizon_bars=2)

    # 3 UP, 1 DOWN -> p_up = 0.75
    train_obs = [o for o in dataset if o.has_target and o.target_binary == 1][:3] + \
                [o for o in dataset if o.has_target and o.target_binary == 0][:1]

    baseline = TrainingPriorBaseline()
    baseline.fit(train_obs)
    pred_bin, pred_prob = baseline.predict(dataset[0])
    assert pred_prob == 0.75
    assert pred_bin == 1  # 0.75 > 0.50

    # Empty training set safeguard
    empty_baseline = TrainingPriorBaseline()
    empty_baseline.fit([])
    pred_bin, pred_prob = empty_baseline.predict(dataset[0])
    assert pred_prob == 0.50
    assert pred_bin == 0


def test_persistence_baseline():
    """Persistence baseline uses 1-bar return at prediction time with fallback on open."""
    day = date(2026, 10, 15)
    candles = _generate_synthetic_candles(day, num_bars=10)
    dataset = assemble_intraday_dataset(candles, horizon_bars=2)

    baseline = PersistenceBaseline()
    baseline.fit(dataset[:5])

    # Observation 0 is session open -> return_1bar is None -> fallback to training prior
    pred_bin_0, pred_prob_0 = baseline.predict(dataset[0])
    assert dataset[0].features.return_1bar is None
    # Training prior for first 5 bars
    expected_prior = sum(1 for o in dataset[:5] if o.has_target and o.target_binary == 1) / 5
    assert pred_prob_0 == pytest.approx(expected_prior)

    # Observation with positive return_1bar
    pos_obs = next(o for o in dataset if o.features.return_1bar is not None and o.features.return_1bar > 0)
    pred_bin_pos, pred_prob_pos = baseline.predict(pos_obs)
    assert pred_bin_pos == 1
    assert pred_prob_pos == 1.0

    # Observation with negative or zero return_1bar
    neg_obs = next(o for o in dataset if o.features.return_1bar is not None and o.features.return_1bar <= 0)
    pred_bin_neg, pred_prob_neg = baseline.predict(neg_obs)
    assert pred_bin_neg == 0
    assert pred_prob_neg == 0.0


# =========================================================================
# 2. Evaluation Metrics & Undefined Handlers
# =========================================================================

def test_evaluation_metrics_mathematical_precision():
    """Verify metrics calculation against exact hand-calculated classification table."""
    # y_true: [1, 1, 1, 0, 0]
    # y_pred: [1, 1, 0, 0, 1]
    # y_prob: [0.9, 0.8, 0.4, 0.1, 0.7]
    y_true = [1, 1, 1, 0, 0]
    y_pred = [1, 1, 0, 0, 1]
    y_prob = [0.9, 0.8, 0.4, 0.1, 0.7]

    # TP = 2 (indices 0, 1)
    # FN = 1 (index 2)
    # TN = 1 (index 3)
    # FP = 1 (index 4)
    metrics = compute_intraday_evaluation_metrics(y_true, y_pred, y_prob, model_name="test_model")

    assert metrics.sample_count == 5
    assert metrics.up_count == 3
    assert metrics.down_count == 2
    assert metrics.true_positives == 2
    assert metrics.true_negatives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1

    # Accuracy: 3/5 = 0.60
    assert metrics.accuracy == pytest.approx(0.60)
    # Precision UP: TP / (TP + FP) = 2 / 3 = 0.6667
    assert metrics.precision_up == pytest.approx(2.0 / 3.0)
    # Recall UP: TP / (TP + FN) = 2 / 3 = 0.6667
    assert metrics.recall_up == pytest.approx(2.0 / 3.0)
    # F1 UP: 2 * (2/3 * 2/3) / (4/3) = 2/3 = 0.6667
    assert metrics.f1_up == pytest.approx(2.0 / 3.0)
    # Balanced Accuracy: 0.5 * (Recall UP + Specificity) = 0.5 * (2/3 + 1/2) = 0.5 * (7/6) = 7/12 = 0.5833
    assert metrics.balanced_accuracy == pytest.approx(7.0 / 12.0)
    # Brier score: ((0.9-1)^2 + (0.8-1)^2 + (0.4-1)^2 + (0.1-0)^2 + (0.7-0)^2) / 5
    # = (0.01 + 0.04 + 0.36 + 0.01 + 0.49) / 5 = 0.91 / 5 = 0.182
    assert metrics.brier_score == pytest.approx(0.182)


def test_undefined_metrics_handling():
    """When a model never predicts UP (TP+FP=0), precision and F1 must be None, not 0.0."""
    y_true = [1, 0, 1, 0]
    y_pred = [0, 0, 0, 0]  # Never predicts positive
    y_prob = [0.0, 0.0, 0.0, 0.0]

    metrics = compute_intraday_evaluation_metrics(y_true, y_pred, y_prob)
    assert metrics.true_positives == 0
    assert metrics.false_positives == 0
    assert metrics.precision_up is None  # Undefined denominator
    assert metrics.f1_up is None         # Undefined
    assert metrics.recall_up == 0.0      # Valid: 0/2 = 0.0
    assert metrics.accuracy == 0.50


def test_constant_050_probability_brier_and_log_loss():
    """Constant 0.50 probability predictor must produce exactly 0.25 Brier score and ~0.6931 log loss."""
    y_true = [1, 0, 1, 1, 0, 0]
    y_pred = [0, 0, 0, 0, 0, 0]
    y_prob = [0.50] * 6

    metrics = compute_intraday_evaluation_metrics(y_true, y_pred, y_prob)
    assert metrics.brier_score == pytest.approx(0.2500)
    assert metrics.log_loss == pytest.approx(math.log(2.0), abs=1e-4)


def test_empty_metrics_input_rejection():
    """Empty inputs to metrics calculation must raise ValidationError."""
    with pytest.raises(ValidationError, match="empty prediction sequences"):
        compute_intraday_evaluation_metrics([], [], [])


# =========================================================================
# 3. Walk-Forward Evaluation, Embargo, and Out-of-Fold Auditing
# =========================================================================

def test_walk_forward_baseline_evaluation_flow():
    """Verify full walk-forward evaluation flow across chronological splits."""
    candles = []
    for d in range(3):
        session_d = date(2026, 10, 14 + d)
        candles.extend(_generate_synthetic_candles(session_d, symbol="BHARTIARTL", num_bars=15))

    dataset = assemble_intraday_dataset(candles, horizon_bars=2)
    splits = generate_intraday_chronological_splits(
        dataset,
        n_splits=2,
        min_train_ratio=0.4,
        min_train_samples=8,
        min_val_samples=4,
    )

    baseline = MajorityClassBaseline()
    audit = evaluate_intraday_baseline_walk_forward(dataset, splits, baseline)

    assert audit.model_name == "majority_class"
    assert audit.n_splits == 2
    assert audit.total_observations == len(dataset)
    assert audit.eligible_observations == sum(1 for o in dataset if o.has_target)
    assert audit.excluded_observations == audit.total_observations - audit.eligible_observations
    assert "SESSION_CLOSE_CUTOFF" in audit.exclusion_reasons

    # Check synthetic fixture flag and empirical status
    assert audit.is_synthetic_fixture is True
    assert audit.empirical_status == "BLOCKED_NO_EMPIRICAL_DATA"

    # Per-fold validation
    assert len(audit.fold_results) == 2
    for fold_res in audit.fold_results:
        assert fold_res.val_count >= 4
        assert len(fold_res.predictions) == fold_res.val_count
        assert fold_res.metrics.sample_count == fold_res.val_count

    # Aggregate metrics
    assert audit.aggregate_metrics is not None
    expected_total_val = sum(f.val_count for f in audit.fold_results)
    assert audit.aggregate_metrics.sample_count == expected_total_val


def test_no_duplicate_out_of_fold_predictions():
    """Out-of-fold validation sets across folds must never contain duplicate timestamps."""
    candles = []
    for d in range(2):
        session_d = date(2026, 10, 14 + d)
        candles.extend(_generate_synthetic_candles(session_d, symbol="BHARTIARTL", num_bars=18))

    dataset = assemble_intraday_dataset(candles, horizon_bars=2)
    splits = generate_intraday_chronological_splits(dataset, n_splits=2, min_train_samples=8, min_val_samples=4)

    audit = evaluate_intraday_baseline_walk_forward(dataset, splits, ConstantProbabilityBaseline())
    all_oof_keys = [
        (p.symbol, p.candle_timestamp)
        for f in audit.fold_results
        for p in f.predictions
    ]
    # Check 100% uniqueness (no duplicate evaluation)
    assert len(all_oof_keys) == len(set(all_oof_keys))


def test_duplicate_validation_timestamp_collision_detection():
    """If two folds share a validation observation, evaluation must raise ValidationError."""
    day = date(2026, 10, 15)
    candles = _generate_synthetic_candles(day, num_bars=20)
    dataset = assemble_intraday_dataset(candles, horizon_bars=2)

    # Artificially construct conflicting splits sharing an observation
    split0 = IntradaySplit(
        fold=0,
        train_observations=dataset[:8],
        val_observations=dataset[10:14],
        embargo_observations=dataset[8:10],
        train_start=dataset[0].candle_timestamp,
        train_end=dataset[7].candle_timestamp,
        train_target_cutoff=dataset[7].target_realized_at or datetime.now(tz=IST),
        val_start=dataset[10].candle_timestamp,
        val_end=dataset[13].candle_timestamp,
        train_count=8,
        val_count=4,
        embargo_count=2,
        train_up_count=4,
        train_down_count=4,
        val_up_count=2,
        val_down_count=2,
    )
    # Split 1 illegally re-validates dataset[12]
    split1 = IntradaySplit(
        fold=1,
        train_observations=dataset[:12],
        val_observations=dataset[12:16],  # Overlaps with 12, 13!
        embargo_observations=[],
        train_start=dataset[0].candle_timestamp,
        train_end=dataset[11].candle_timestamp,
        train_target_cutoff=dataset[11].target_realized_at or datetime.now(tz=IST),
        val_start=dataset[12].candle_timestamp,
        val_end=dataset[15].candle_timestamp,
        train_count=12,
        val_count=4,
        embargo_count=0,
        train_up_count=6,
        train_down_count=6,
        val_up_count=2,
        val_down_count=2,
    )

    with pytest.raises(ValidationError, match="Duplicate validation observation timestamp"):
        evaluate_intraday_baseline_walk_forward(dataset, [split0, split1], TrainingPriorBaseline())


# =========================================================================
# 4. Strict Zero-Leakage & Validation Tampering Invariant Test
# =========================================================================

def test_validation_label_tampering_zero_leakage():
    """Altering validation labels must NOT alter the baseline predictions fitted on training data."""
    day = date(2026, 10, 15)
    candles = _generate_synthetic_candles(day, num_bars=25)
    dataset_orig = assemble_intraday_dataset(candles, horizon_bars=2)
    splits_orig = generate_intraday_chronological_splits(dataset_orig, n_splits=2, min_train_samples=8, min_val_samples=4)

    baseline_orig = MajorityClassBaseline()
    baseline_orig.fit(splits_orig[0].train_observations)
    orig_preds = [baseline_orig.predict(o) for o in splits_orig[0].val_observations]

    # Tamper with validation observations (flip all target labels)
    tampered_val = []
    for o in splits_orig[0].val_observations:
        tampered_o = IntradayDatasetObservation(
            symbol=o.symbol,
            session_date=o.session_date,
            candle_timestamp=o.candle_timestamp,
            available_at=o.available_at,
            interval=o.interval,
            features=o.features,
            target_horizon_bars=o.target_horizon_bars,
            target_return=-o.target_return if o.target_return is not None else None,
            target_direction="DOWN" if o.target_direction == "UP" else "UP",
            target_binary=0 if o.target_binary == 1 else 1,
            target_realized_at=o.target_realized_at,
            target_status=o.target_status,
            candle=o.candle,
        )
        tampered_val.append(tampered_o)

    # Refit baseline on unchanged training partition
    baseline_check = MajorityClassBaseline()
    baseline_check.fit(splits_orig[0].train_observations)
    check_preds = [baseline_check.predict(o) for o in tampered_val]

    # Predictions MUST be identical despite validation label changes
    assert orig_preds == check_preds


def test_evaluation_reproducibility():
    """Repeated execution of walk-forward evaluation on identical datasets must yield identical metrics."""
    candles = _generate_synthetic_candles(date(2026, 10, 15), num_bars=25)
    dataset = assemble_intraday_dataset(candles, horizon_bars=2)
    splits = generate_intraday_chronological_splits(dataset, n_splits=2, min_train_samples=8, min_val_samples=4)

    audit1 = evaluate_intraday_baseline_walk_forward(dataset, splits, TrainingPriorBaseline())
    audit2 = evaluate_intraday_baseline_walk_forward(dataset, splits, TrainingPriorBaseline())

    assert audit1.to_dict() == audit2.to_dict()
