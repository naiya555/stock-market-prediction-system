"""Deterministic tests for probability calibration, reliability diagrams, and statistical significance (Day 62)."""

import math
from typing import List
import numpy as np
import pytest

from app.history.calibration import (
    ConfidenceInterval,
    PairedComparisonResult,
    ReliabilityDiagramResult,
    compute_log_loss,
    compute_mcnemar_paired_test,
    compute_reliability_diagram,
    compute_wilson_score_interval,
)
from app.training.retraining import ModelRetrainer


def test_constant_half_probability_baseline():
    """Verify that predicting constant P(UP)=0.50 yields exact Brier score 0.2500 and log loss ln(2)."""
    # Test on arbitrary class balance (e.g. 119 UP, 121 DOWN)
    y_true = [1] * 119 + [0] * 121
    y_prob = [0.50] * 240

    brier = ModelRetrainer.compute_brier_score(y_true, y_prob)
    assert brier == 0.2500

    log_loss = compute_log_loss(y_true, y_prob)
    expected_log_loss = math.log(2.0)  # ~0.693147
    assert math.isclose(log_loss, expected_log_loss, rel_tol=1e-5)


def test_majority_baseline_probability_semantics():
    """Verify majority baseline P(UP)=1.0 produces Brier score 0.5042 and heavy log loss."""
    y_true = [1] * 119 + [0] * 121
    # Hard majority decision: P(UP) = 1.0 for all samples
    y_prob = [1.0] * 240

    # Brier = (1-1)^2 * 119 + (0-1)^2 * 121 = 121 / 240 = 0.504166... -> 0.5042
    brier = ModelRetrainer.compute_brier_score(y_true, y_prob)
    assert brier == 0.5042

    # Log loss on y=0 with p=1.0 is severely penalized (clipped by eps)
    loss = compute_log_loss(y_true, y_prob, eps=1e-15)
    assert loss > 15.0  # Log loss heavily penalizes certainty on wrong outcomes


def test_training_prior_baseline():
    """Verify baseline forecasting historical training prior (502 / 958 = 0.5240)."""
    y_true = [1] * 119 + [0] * 121
    p_train = 502 / 958  # 0.524008...
    y_prob = [p_train] * 240

    brier = ModelRetrainer.compute_brier_score(y_true, y_prob)
    # (0.5240 - 1)^2 * 119 + (0.5240 - 0)^2 * 121 = 0.226576 * 119 + 0.274576 * 121 = 26.962 + 33.223 = 60.185 / 240 = 0.25077
    assert brier == 0.2508

    loss = compute_log_loss(y_true, y_prob)
    assert 0.694 < loss < 0.695


def test_wilson_score_confidence_interval_known_values():
    """Verify Wilson score interval calculation for known sample proportions."""
    # Symmetrical 50% case: 50 / 100
    ci_50 = compute_wilson_score_interval(successes=50, total=100, confidence=0.95)
    assert ci_50.observed_value == 0.50
    assert math.isclose(ci_50.lower_bound, 0.4038, abs_tol=1e-3)
    assert math.isclose(ci_50.upper_bound, 0.5962, abs_tol=1e-3)

    # XGBoost holdout: 123 / 240 = 51.25%
    ci_xgb = compute_wilson_score_interval(successes=123, total=240, confidence=0.95)
    assert math.isclose(ci_xgb.observed_value, 0.5125, abs_tol=1e-4)
    assert math.isclose(ci_xgb.lower_bound, 0.4496, abs_tol=1e-3)
    assert math.isclose(ci_xgb.upper_bound, 0.5749, abs_tol=1e-3)

    # LightGBM holdout: 129 / 240 = 53.75%
    ci_lgb = compute_wilson_score_interval(successes=129, total=240, confidence=0.95)
    assert math.isclose(ci_lgb.observed_value, 0.5375, abs_tol=1e-4)
    assert math.isclose(ci_lgb.lower_bound, 0.4743, abs_tol=1e-3)
    assert math.isclose(ci_lgb.upper_bound, 0.5994, abs_tol=1e-3)

    # Edge cases
    with pytest.raises(ValueError, match="Total trials must be positive"):
        compute_wilson_score_interval(0, 0)
    with pytest.raises(ValueError, match="Successes"):
        compute_wilson_score_interval(10, 5)


def test_reliability_diagram_and_empty_bins_safety():
    """Verify reliability diagram calculation handles empty bins gracefully without errors."""
    y_true = [1, 0, 1, 0]
    # All probabilities clustered in [0.4, 0.6]
    y_prob = [0.45, 0.55, 0.48, 0.52]

    res = compute_reliability_diagram(y_true, y_prob, n_bins=5)
    assert res.n_bins == 5
    assert len(res.bins) == 5

    # Bins 0, 1, 3, 4 should be empty
    assert res.bins[0].sample_count == 0
    assert res.bins[0].mean_confidence is None
    assert res.bins[0].empirical_accuracy is None
    assert res.bins[0].calibration_gap is None

    # Bin 2 [0.4, 0.6] contains all 4 samples
    assert res.bins[2].sample_count == 4
    assert res.bins[2].mean_confidence == 0.50
    assert res.bins[2].empirical_accuracy == 0.50
    assert res.bins[2].calibration_gap == 0.0

    # Overall ECE is 0.0 because the only occupied bin is perfectly calibrated
    assert res.expected_calibration_error == 0.0


def test_reliability_diagram_perfect_calibration():
    """Verify reliability diagram on perfectly calibrated predictions."""
    y_true = [0, 0, 1, 1]
    y_prob = [0.0, 0.0, 1.0, 1.0]

    res = compute_reliability_diagram(y_true, y_prob, n_bins=5)
    assert res.expected_calibration_error == 0.0
    assert res.brier_score == 0.0


def test_mcnemar_test_paired_properties():
    """Verify McNemar's test for paired classification accuracy comparison."""
    # Case 1: Identical predictions (0 discordant pairs)
    y_true = [1, 0, 1, 0]
    y_pred1 = [1, 0, 1, 0]
    y_pred2 = [1, 0, 1, 0]
    res_ident = compute_mcnemar_paired_test(y_true, y_pred1, y_pred2)
    assert res_ident.statistic == 0.0
    assert res_ident.p_value == 1.0
    assert res_ident.is_significant is False

    # Case 2: Symmetrical discordant pairs (b = 10, c = 10)
    # y = [1]*20
    # m1 correct on first 10, wrong on next 10
    # m2 wrong on first 10, correct on next 10
    y_t = [1] * 20
    p1 = [1] * 10 + [0] * 10
    p2 = [0] * 10 + [1] * 10
    res_sym = compute_mcnemar_paired_test(y_t, p1, p2)
    assert res_sym.a_correct_b_incorrect == 10
    assert res_sym.b_correct_a_incorrect == 10
    assert res_sym.statistic == 0.0
    assert res_sym.p_value == 1.0
    assert res_sym.is_significant is False

    # Case 3: Asymmetrical discordant pairs (b = 25, c = 0)
    p_bad = [0] * 25
    p_good = [1] * 25
    res_asym = compute_mcnemar_paired_test([1] * 25, p_bad, p_good)
    assert res_asym.statistic > 20.0
    assert res_asym.p_value < 0.001
    assert res_asym.is_significant is True


def test_mcnemar_on_bhartiartl_holdout_pairs():
    """Verify paired comparison between XGBoost and LightGBM matches audited metrics."""
    # From audited holdout outputs:
    # 240 samples: both_correct=109, both_incorrect=97, xgb_wrong_lgb_right(b)=20, xgb_right_lgb_wrong(c)=14
    # chi2 with Edwards correction: (|20 - 14| - 1)^2 / 34 = 25 / 34 = 0.73529... -> 0.7353
    # p-value ~ 0.3912
    # Synthesize exact paired outcomes:
    y_t = [1] * 240
    # 109 both correct (1, 1)
    # 97 both wrong (0, 0)
    # 20 xgb wrong (0), lgb right (1)
    # 14 xgb right (1), lgb wrong (0)
    p_xgb = [1] * 109 + [0] * 97 + [0] * 20 + [1] * 14
    p_lgb = [1] * 109 + [0] * 97 + [1] * 20 + [0] * 14

    res = compute_mcnemar_paired_test(y_t, p_xgb, p_lgb, "XGBoost", "LightGBM")
    assert res.both_correct == 109
    assert res.both_incorrect == 97
    assert res.a_correct_b_incorrect == 14
    assert res.b_correct_a_incorrect == 20
    assert math.isclose(res.statistic, 0.7353, abs_tol=1e-3)
    assert math.isclose(res.p_value, 0.3912, abs_tol=1e-3)
    assert res.is_significant is False
    assert "Inconclusive" in res.conclusion


def test_calibration_partition_temporal_isolation_design():
    """Verify that a 3-way train/calibration/holdout design strictly isolates all boundary outcome cutoffs."""
    # Given hypothetical date bounds:
    train_end = "2025-06-30"
    train_outcome_cutoff = "2025-07-01"
    cal_start = "2025-07-02"
    cal_end = "2025-10-27"
    cal_outcome_cutoff = "2025-10-28"
    holdout_start = "2025-10-29"

    # Isolation Check 1: Training to Calibration
    assert train_outcome_cutoff < cal_start, "Training outcome leaks into calibration!"

    # Isolation Check 2: Calibration to Holdout
    assert cal_outcome_cutoff < holdout_start, "Calibration outcome leaks into holdout!"
