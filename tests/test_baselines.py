"""Unit Tests for Day 18 Baseline Classifiers & Comparative Evaluation.

Tests:
1. Majority-class selection using training labels only.
2. Deterministic tie-handling in MajorityClassClassifier.
3. MajorityClassClassifier shape, values, and probabilities.
4. MajorityClassClassifier error handling on invalid or empty inputs.
5. Reproducibility of fixed-seed random predictions.
6. Policy enforcement for RandomClassifier ('uniform', 'stratified', 'custom').
7. RandomClassifier input validation and error handling.
8. Identical holdout indices and fair evaluation across strategies.
9. Leakage prevention: holdout outcomes strictly invisible to baselines.
10. Consistent metric calculations and confusion-matrix correctness.
11. BaselineComparisonReport generation, summary table, and serialization.
12. Regression protection for existing Day 17 XGBoost classifier within comparison.
"""

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytest

from app.training.baselines import (
    BaselineComparisonReport,
    BaselineComparisonRow,
    MajorityClassClassifier,
    RandomClassifier,
    evaluate_baseline_comparison,
)
from app.training.feature_matrix import FEATURE_COLUMNS, FeatureMatrixDataset
from app.training.xgboost_classifier import (
    ChronologicalSplitResult,
    XGBoostConfig,
    compute_classification_metrics,
    split_chronological_holdout,
)


@pytest.fixture
def synthetic_train_test_split() -> ChronologicalSplitResult:
    """Fixture providing clean chronological train and holdout split."""
    rng = np.random.RandomState(42)
    n_total = 60
    start_dt = datetime(2026, 1, 1)

    dates = [start_dt + timedelta(days=i) for i in range(n_total)]
    next_dates = [start_dt + timedelta(days=i + 1) for i in range(n_total)]

    # 40 train, 1 embargo, 19 test
    # Train labels: 25 UP (1), 15 DOWN (0) -> majority is 1
    # Test labels: 10 UP (1), 9 DOWN (0)
    train_labels = [1] * 25 + [0] * 15
    embargo_label = [0]
    test_labels = [1] * 10 + [0] * 9
    y_all = train_labels + embargo_label + test_labels

    df_data: dict = {
        "symbol": ["TEST"] * n_total,
        "timestamp": dates,
        "next_timestamp": next_dates,
        "current_close": [100.0 + i for i in range(n_total)],
        "next_close": [101.0 + i for i in range(n_total)],
        "target_return": [0.01 if y == 1 else -0.01 for y in y_all],
        "target_direction": ["UP" if y == 1 else "DOWN" for y in y_all],
        "target_binary": [float(y) for y in y_all],
    }

    for col in FEATURE_COLUMNS:
        df_data[col] = rng.randn(n_total)

    df = pd.DataFrame(df_data)
    X = df[FEATURE_COLUMNS]
    y = df["target_binary"]
    metadata = df[["symbol", "timestamp", "next_timestamp", "current_close", "next_close"]]

    dataset = FeatureMatrixDataset(
        symbol="TEST",
        df=df,
        X=X,
        y=y,
        metadata=metadata,
        feature_names=FEATURE_COLUMNS,
        total_rows=n_total,
        labeled_rows=n_total,
        unlabeled_rows=0,
    )

    return split_chronological_holdout(
        data=dataset,
        test_ratio=0.316,
        embargo_sessions=1,
        min_train_samples=20,
        min_test_samples=5,
    )


# 1. Majority-class selection uses training labels only
def test_majority_class_selection_training_labels_only() -> None:
    """Verify majority class is determined solely by training labels."""
    # Training set has 3 DOWN (0) and 7 UP (1) -> majority is 1
    y_train = np.array([0, 0, 0, 1, 1, 1, 1, 1, 1, 1])
    clf = MajorityClassClassifier()
    clf.fit(y_train)

    assert clf.is_fitted is True
    assert clf.majority_class_ == 1
    assert clf.class_counts_ == {0: 3, 1: 7}

    # Training set with DOWN as majority
    y_train_down = np.array([0, 0, 0, 0, 1, 1])
    clf_down = MajorityClassClassifier()
    clf_down.fit(y_train_down)
    assert clf_down.majority_class_ == 0
    assert clf_down.class_counts_ == {0: 4, 1: 2}


# 2. Deterministic tie handling
def test_majority_class_deterministic_tie_handling() -> None:
    """Verify tie between classes resolves deterministically to tie_break_class."""
    y_tied = np.array([0, 0, 1, 1])

    clf_tie_up = MajorityClassClassifier(tie_break_class=1)
    clf_tie_up.fit(y_tied)
    assert clf_tie_up.majority_class_ == 1

    clf_tie_down = MajorityClassClassifier(tie_break_class=0)
    clf_tie_down.fit(y_tied)
    assert clf_tie_down.majority_class_ == 0


# 3. Prediction shape, values, and probabilities
def test_majority_class_prediction_shape_and_probabilities() -> None:
    """Verify predictions and probabilities match expected dimensions and values."""
    y_train = np.array([1, 1, 0])
    clf = MajorityClassClassifier()
    clf.fit(y_train)

    preds = clf.predict(10)
    assert isinstance(preds, np.ndarray)
    assert len(preds) == 10
    assert (preds == 1).all()

    probs = clf.predict_proba(5)
    assert probs.shape == (5, 2)
    assert (probs[:, 0] == 0.0).all()
    assert (probs[:, 1] == 1.0).all()


# 4. Error handling on invalid inputs
def test_majority_class_invalid_inputs() -> None:
    """Verify fast failure on empty or non-binary labels."""
    clf = MajorityClassClassifier()
    with pytest.raises(ValueError, match="Cannot fit MajorityClassClassifier on empty labels"):
        clf.fit([])

    with pytest.raises(ValueError, match="Labels must be strictly binary integers"):
        clf.fit([0, 1, 2])

    with pytest.raises(ValueError, match="Classifier is not fitted"):
        clf.predict(5)


# 5. Reproducibility of fixed-seed random predictions
def test_random_classifier_reproducibility() -> None:
    """Verify random predictions are 100% reproducible with identical fixed seed."""
    clf1 = RandomClassifier(policy="uniform", random_state=42)
    clf1.fit()
    preds1 = clf1.predict(20)

    clf2 = RandomClassifier(policy="uniform", random_state=42)
    clf2.fit()
    preds2 = clf2.predict(20)

    np.testing.assert_array_equal(preds1, preds2)

    # Different seed produces different predictions
    clf_diff = RandomClassifier(policy="uniform", random_state=999)
    clf_diff.fit()
    preds_diff = clf_diff.predict(20)
    assert not np.array_equal(preds1, preds_diff)


# 6. Policy enforcement for RandomClassifier
def test_random_classifier_policies() -> None:
    """Verify uniform, stratified, and custom probability policies."""
    # Uniform policy: p=0.5
    clf_unif = RandomClassifier(policy="uniform")
    clf_unif.fit()
    assert clf_unif.p_ == 0.5
    probs_unif = clf_unif.predict_proba(4)
    assert probs_unif.shape == (4, 2)
    assert np.allclose(probs_unif[:, 1], 0.5)

    # Stratified policy: p = empirical train prior
    y_train = np.array([1, 1, 1, 0])  # 75% positive
    clf_strat = RandomClassifier(policy="stratified", random_state=42)
    clf_strat.fit(y_train)
    assert clf_strat.p_ == 0.75
    probs_strat = clf_strat.predict_proba(4)
    assert np.allclose(probs_strat[:, 1], 0.75)

    # Custom policy
    clf_custom = RandomClassifier(policy="custom", custom_p=0.33)
    clf_custom.fit()
    assert clf_custom.p_ == 0.33


# 7. RandomClassifier input validation
def test_random_classifier_validation_errors() -> None:
    """Verify exceptions on invalid policy or parameters."""
    with pytest.raises(ValueError, match="Unknown policy"):
        RandomClassifier(policy="invalid_policy")

    with pytest.raises(ValueError, match="custom_p must be a float in"):
        RandomClassifier(policy="custom", custom_p=1.5)

    with pytest.raises(ValueError, match="Labels y are required to fit 'stratified'"):
        clf = RandomClassifier(policy="stratified")
        clf.fit(None)

    with pytest.raises(ValueError, match="Classifier is not fitted"):
        clf_unfit = RandomClassifier()
        clf_unfit.predict(5)


# 8. Identical holdout indices and fair evaluation across strategies
def test_identical_holdout_indices_across_strategies(
    synthetic_train_test_split: ChronologicalSplitResult,
) -> None:
    """Verify every strategy evaluates on the identical holdout partition."""
    report = evaluate_baseline_comparison(
        split=synthetic_train_test_split,
        random_seed=42,
    )

    assert isinstance(report, BaselineComparisonReport)
    assert report.holdout_sessions == len(synthetic_train_test_split.y_test)

    # Every row in report must evaluate on exact same total samples
    for row in report.rows:
        assert row.total_samples == report.holdout_sessions
        assert row.pred_up_count + row.pred_down_count == report.holdout_sessions


# 9. Leakage prevention: holdout outcomes strictly invisible to baselines
def test_leakage_prevention_baselines(
    synthetic_train_test_split: ChronologicalSplitResult,
) -> None:
    """Verify baseline training only uses train partition."""
    y_train = synthetic_train_test_split.y_train.values
    y_test = synthetic_train_test_split.y_test.values

    # Majority classifier
    clf = MajorityClassClassifier()
    clf.fit(y_train)

    train_n1 = int(np.sum(y_train == 1))
    train_n0 = int(np.sum(y_train == 0))
    expected_majority = 1 if train_n1 >= train_n0 else 0

    assert clf.majority_class_ == expected_majority

    # Predictions must not alter based on test data
    preds = clf.predict(len(y_test))
    assert (preds == expected_majority).all()


# 10. Consistent metric calculations and confusion matrix correctness
def test_consistent_metrics_and_confusion_matrix() -> None:
    """Verify metrics and confusion matrix correctness on deterministic baseline predictions."""
    y_true = np.array([1, 1, 0, 0])
    y_pred = np.array([1, 1, 1, 1])  # All UP (like Majority Class)

    metrics = compute_classification_metrics(y_true, y_pred)
    assert metrics.accuracy == 0.5
    assert metrics.precision == 0.5
    assert metrics.recall == 1.0
    assert metrics.f1 == pytest.approx(0.6667, abs=1e-3)
    assert metrics.confusion_matrix == [[0, 2], [0, 2]]  # TN=0, FP=2, FN=0, TP=2


# 11. BaselineComparisonReport structure and summary table
def test_baseline_comparison_report_structure(
    synthetic_train_test_split: ChronologicalSplitResult,
) -> None:
    """Verify report formatting, summary table, and serialization."""
    report = evaluate_baseline_comparison(
        split=synthetic_train_test_split,
        random_seed=42,
    )

    d = report.to_dict()
    assert "rows" in d
    assert len(d["rows"]) == 4
    assert "best_strategy_by_accuracy" in d
    assert "xgboost_beat_majority" in d

    table = report.summary_table()
    assert "| Strategy | Accuracy |" in table
    assert "Baseline A (Majority Class)" in table
    assert "Model C (Day 17 XGBoost)" in table


# 12. Regression protection for existing XGBoost classifier
def test_regression_protection_existing_xgboost(
    synthetic_train_test_split: ChronologicalSplitResult,
) -> None:
    """Verify Day 17 XGBoost evaluated within comparison suite matches standalone execution."""
    from app.training.xgboost_classifier import XGBoostDirectionClassifier

    # Standalone XGBoost fit
    standalone_clf = XGBoostDirectionClassifier(config=XGBoostConfig(random_state=42))
    standalone_clf.fit(synthetic_train_test_split.X_train, synthetic_train_test_split.y_train)
    standalone_preds = standalone_clf.predict(synthetic_train_test_split.X_test)
    standalone_metrics = compute_classification_metrics(
        synthetic_train_test_split.y_test, standalone_preds
    )

    # Suite comparison XGBoost fit
    report = evaluate_baseline_comparison(
        split=synthetic_train_test_split,
        random_seed=42,
    )
    xgb_row = next(r for r in report.rows if "XGBoost" in r.strategy_name)

    assert xgb_row.accuracy == standalone_metrics.accuracy
    assert xgb_row.f1_up == standalone_metrics.f1
    assert xgb_row.confusion_matrix == standalone_metrics.confusion_matrix


# 13. LightGBM inclusion in baseline comparison suite
def test_baseline_comparison_with_lightgbm(
    synthetic_train_test_split: ChronologicalSplitResult,
) -> None:
    """Verify include_lightgbm=True appends Model D (Day 19 LightGBM) to report."""
    from app.training.lightgbm_classifier import LightGBMConfig

    report = evaluate_baseline_comparison(
        split=synthetic_train_test_split,
        random_seed=42,
        include_lightgbm=True,
        lightgbm_config=LightGBMConfig(min_child_samples=5),
    )

    d = report.to_dict()
    assert len(d["rows"]) == 5
    strategy_names = [r["strategy_name"] for r in d["rows"]]
    assert "Model D (Day 19 LightGBM)" in strategy_names
    assert report.lightgbm_beat_majority is not None
    assert report.lightgbm_beat_random is not None
    assert "| **Model D (Day 19 LightGBM)** |" in report.summary_table()
