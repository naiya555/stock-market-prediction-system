"""Unit Tests for Day 17 XGBoost Direction Classifier Baseline.

Tests:
1. Model configuration and default baseline parameters with fixed seed.
2. Successful model fitting and inference on small valid synthetic dataset.
3. Strict feature column order preservation and alignment.
4. Missing value rejection policy in baseline mode.
5. Empty dataset rejection handling.
6. Single-class dataset rejection handling.
7. Target and future-column leakage rejection (isolation guard).
8. Chronological split boundaries and row count conservation.
9. Prevention of holdout leakage into training (temporal embargo validation).
10. Deterministic, reproducible predictions across repeated runs with identical seed.
11. Model serialization and persistence verification (JSON format).
12. Binary classification metric calculations and zero-division edge cases.
13. Graceful handling when xgboost is unavailable.
14. End-to-end training pipeline orchestration on synthetic FeatureMatrixDataset.
"""

from datetime import datetime, timedelta
import tempfile
from pathlib import Path
import unittest.mock as mock

import numpy as np
import pandas as pd
import pytest

from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FeatureMatrixDataset,
)
from app.training.xgboost_classifier import (
    ChronologicalSplitResult,
    ClassificationMetrics,
    DirectionTrainingResult,
    XGBoostConfig,
    XGBoostDirectionClassifier,
    compute_classification_metrics,
    run_training_pipeline,
    split_chronological_holdout,
    train_baseline_classifier,
)


@pytest.fixture
def synthetic_labeled_df() -> pd.DataFrame:
    """Generate a small, clean synthetic dataset with canonical schema."""
    rng = np.random.RandomState(42)
    n_rows = 50
    start_dt = datetime(2026, 1, 1)

    dates = [start_dt + timedelta(days=i) for i in range(n_rows)]
    next_dates = [start_dt + timedelta(days=i + 1) for i in range(n_rows)]

    data: dict = {
        "symbol": ["TEST"] * n_rows,
        "timestamp": dates,
        "next_timestamp": next_dates,
        "current_close": [100.0 + i for i in range(n_rows)],
        "next_close": [101.0 + i for i in range(n_rows)],
        "target_return": [0.01 if i % 2 == 0 else -0.01 for i in range(n_rows)],
        "target_direction": ["UP" if i % 2 == 0 else "DOWN" for i in range(n_rows)],
        "target_binary": [1.0 if i % 2 == 0 else 0.0 for i in range(n_rows)],
    }

    # Add canonical feature columns with non-NaN synthetic numbers
    for col in FEATURE_COLUMNS:
        data[col] = rng.randn(n_rows)

    return pd.DataFrame(data)


@pytest.fixture
def synthetic_feature_matrix_dataset(synthetic_labeled_df: pd.DataFrame) -> FeatureMatrixDataset:
    """Generate a valid FeatureMatrixDataset using synthetic fixture."""
    df = synthetic_labeled_df.copy()
    X = df[FEATURE_COLUMNS].copy()
    y = df["target_binary"].copy()
    metadata = df[["symbol", "timestamp", "next_timestamp", "current_close", "next_close"]].copy()

    return FeatureMatrixDataset(
        symbol="TEST",
        df=df,
        X=X,
        y=y,
        metadata=metadata,
        feature_names=FEATURE_COLUMNS,
        total_rows=len(df),
        labeled_rows=len(df),
        unlabeled_rows=0,
    )


# 1. Configuration tests
def test_xgboost_config_defaults_and_customization() -> None:
    """Verify default conservative hyperparameters and dictionary serialization."""
    config = XGBoostConfig()
    assert config.objective == "binary:logistic"
    assert config.eval_metric == "logloss"
    assert config.random_state == 42
    assert config.max_depth == 3
    assert config.learning_rate == 0.05
    assert config.n_estimators == 50
    assert config.subsample == 0.8
    assert config.colsample_bytree == 0.8
    assert config.n_jobs == 1
    assert config.allow_missing is False

    params = config.to_params_dict()
    assert params["objective"] == "binary:logistic"
    assert params["seed"] == 42
    assert params["nthread"] == 1

    d = config.to_dict()
    assert isinstance(d, dict)
    assert d["random_state"] == 42


# 2. Successful fitting on small valid synthetic dataset
def test_successful_fitting_synthetic_data(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify classifier fits cleanly on synthetic features and predicts valid classes."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y = synthetic_labeled_df["target_binary"]

    clf = XGBoostDirectionClassifier()
    clf.fit(X, y)

    assert clf.is_fitted is True
    assert clf.booster is not None

    preds = clf.predict(X)
    assert isinstance(preds, np.ndarray)
    assert len(preds) == len(X)
    assert set(np.unique(preds)).issubset({0, 1})

    proba = clf.predict_proba(X)
    assert proba.shape == (len(X), 2)
    assert np.allclose(proba.sum(axis=1), 1.0)
    assert (proba >= 0.0).all() and (proba <= 1.0).all()


# 3. Correct feature-column order
def test_feature_column_order_preservation(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify feature column order is strictly maintained and permuted input is aligned."""
    X = synthetic_labeled_df[FEATURE_COLUMNS].copy()
    y = synthetic_labeled_df["target_binary"]

    clf = XGBoostDirectionClassifier()
    clf.fit(X, y)
    assert clf.feature_names == FEATURE_COLUMNS

    # Permute DataFrame column order
    reversed_cols = list(reversed(FEATURE_COLUMNS))
    X_permuted = X[reversed_cols].copy()

    # Predicting with permuted DataFrame must reorder internally without crashing
    preds_orig = clf.predict(X)
    preds_perm = clf.predict(X_permuted)
    np.testing.assert_array_equal(preds_orig, preds_perm)


# 4. Missing-value policy
def test_missing_value_policy(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify missing values in X or y trigger explicit ValueError under baseline config."""
    X = synthetic_labeled_df[FEATURE_COLUMNS].copy()
    y = synthetic_labeled_df["target_binary"].copy()

    # Inject NaN into feature
    X.iloc[5, 2] = np.nan

    clf = XGBoostDirectionClassifier(config=XGBoostConfig(allow_missing=False))
    with pytest.raises(ValueError, match="contains missing \\(NaN\\) values"):
        clf.fit(X, y)


# 5. Empty dataset handling
def test_empty_dataset_rejection() -> None:
    """Verify empty feature dataset raises ValueError."""
    X_empty = pd.DataFrame(columns=FEATURE_COLUMNS)
    y_empty = pd.Series([], dtype=int)

    clf = XGBoostDirectionClassifier()
    with pytest.raises(ValueError, match="Cannot fit model on empty feature dataset"):
        clf.fit(X_empty, y_empty)


# 6. Single-class dataset handling
def test_single_class_dataset_rejection(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify single-class dataset (e.g. all 1s or all 0s) is rejected with clear error."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y_all_ones = pd.Series([1] * len(X))

    clf = XGBoostDirectionClassifier()
    with pytest.raises(ValueError, match="Dataset contains only one target class"):
        clf.fit(X, y_all_ones)


# 7. Target and future-column leakage rejection
def test_target_and_future_column_leakage_rejection(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify contaminated feature matrix containing target or future columns is rejected."""
    # Add forbidden target column
    X_bad = synthetic_labeled_df[FEATURE_COLUMNS].copy()
    X_bad["target_return"] = 0.05
    y = synthetic_labeled_df["target_binary"]

    clf = XGBoostDirectionClassifier()
    with pytest.raises(ValueError, match="Data leakage detected"):
        clf.fit(X_bad, y)

    # Add forbidden future timestamp column
    X_bad2 = synthetic_labeled_df[FEATURE_COLUMNS].copy()
    X_bad2["next_close"] = 120.0
    with pytest.raises(ValueError, match="Data leakage detected"):
        clf.fit(X_bad2, y)


# 8. Chronological split boundaries
def test_chronological_split_boundaries(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify chronological split boundaries, partition counts, and ordering."""
    split_res = split_chronological_holdout(
        data=synthetic_labeled_df,
        test_ratio=0.2,
        embargo_sessions=1,
    )

    assert isinstance(split_res, ChronologicalSplitResult)
    assert split_res.total_rows == len(synthetic_labeled_df)
    assert split_res.embargo_rows == 1

    # In 50 samples with 0.2 ratio -> 10 test samples, 1 embargo sample, 39 train samples
    assert split_res.test_rows == 10
    assert split_res.train_rows == 39
    assert split_res.train_rows + split_res.test_rows + split_res.embargo_rows == 50

    # Ensure strictly chronological: train dates come before holdout dates
    assert split_res.train_end_date is not None
    assert split_res.holdout_start_date is not None
    assert split_res.train_end_date < split_res.holdout_start_date


# 9. Prevention of holdout leakage into training (embargo check)
def test_prevention_of_holdout_leakage_into_training(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify training label outcome timestamps strictly precede holdout start date."""
    split_res = split_chronological_holdout(
        data=synthetic_labeled_df,
        test_ratio=0.2,
        embargo_sessions=1,
    )

    # The outcome cutoff of the last training session must be strictly prior to holdout start date
    assert split_res.train_outcome_cutoff is not None
    assert split_res.holdout_start_date is not None
    assert split_res.train_outcome_cutoff <= split_res.holdout_start_date

    # The embargoed row separates the train label's outcome from the holdout
    last_train_idx = split_res.train_indices[-1]
    first_holdout_idx = split_res.test_indices[0]
    assert first_holdout_idx - last_train_idx > 1


# 10. Reproducible predictions with fixed seed
def test_reproducible_predictions(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify identical predictions across separate model fits with identical random seed."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y = synthetic_labeled_df["target_binary"]

    clf1 = XGBoostDirectionClassifier(config=XGBoostConfig(random_state=42))
    clf1.fit(X, y)
    preds1 = clf1.predict(X)
    probs1 = clf1.predict_proba(X)

    clf2 = XGBoostDirectionClassifier(config=XGBoostConfig(random_state=42))
    clf2.fit(X, y)
    preds2 = clf2.predict(X)
    probs2 = clf2.predict_proba(X)

    np.testing.assert_array_equal(preds1, preds2)
    np.testing.assert_allclose(probs1, probs2, atol=1e-6)


# 11. Model persistence via native save/load
def test_model_save_and_load_persistence(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify model persists to and restores from native XGBoost JSON format with exact outputs."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y = synthetic_labeled_df["target_binary"]

    clf = XGBoostDirectionClassifier(config=XGBoostConfig(random_state=42))
    clf.fit(X, y)
    expected_preds = clf.predict(X)

    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "test_xgb.json"
        clf.save_model(model_path)
        assert model_path.exists()

        restored_clf = XGBoostDirectionClassifier.load_model(model_path)
        assert restored_clf.is_fitted is True
        assert restored_clf.feature_names == clf.feature_names

        restored_preds = restored_clf.predict(X)
        np.testing.assert_array_equal(expected_preds, restored_preds)


# 12. Classification metrics calculations & zero-division safety
def test_classification_metrics_calculation() -> None:
    """Verify metric formulas on known synthetic confusion matrix."""
    # TP=2, TN=2, FP=1, FN=1 -> Total=6
    y_true = [1, 1, 1, 0, 0, 0]
    y_pred = [1, 1, 0, 1, 0, 0]

    metrics = compute_classification_metrics(y_true, y_pred)
    assert metrics.total_samples == 6
    assert metrics.true_positives == 2
    assert metrics.true_negatives == 2
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.confusion_matrix == [[2, 1], [1, 2]]
    assert metrics.accuracy == pytest.approx(4 / 6, abs=1e-3)
    assert metrics.precision == pytest.approx(2 / 3, abs=1e-3)
    assert metrics.recall == pytest.approx(2 / 3, abs=1e-3)
    assert metrics.f1 == pytest.approx(2 / 3, abs=1e-3)

    # Edge case: zero positives predicted (FP=0, TP=0)
    y_true_zero = [1, 1, 0]
    y_pred_zero = [0, 0, 0]
    metrics_zero = compute_classification_metrics(y_true_zero, y_pred_zero)
    assert metrics_zero.precision == 0.0
    assert metrics_zero.recall == 0.0
    assert metrics_zero.f1 == 0.0


# 13. Graceful handling when optional xgboost is unavailable
def test_graceful_handling_unavailable_xgboost(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify informative ImportError is raised when xgboost cannot be imported."""
    import app.training.xgboost_classifier as xgb_mod

    monkeypatch.setattr(xgb_mod, "HAS_XGBOOST", False)

    clf = XGBoostDirectionClassifier()
    with pytest.raises(ImportError, match="xgboost is not installed"):
        clf.fit([[1.0, 2.0]], [1])


# 14. Full training pipeline orchestration on FeatureMatrixDataset
def test_run_training_pipeline_orchestration(
    synthetic_feature_matrix_dataset: FeatureMatrixDataset,
) -> None:
    """Verify end-to-end pipeline execution returns DirectionTrainingResult."""
    result = run_training_pipeline(
        dataset=synthetic_feature_matrix_dataset,
        config=XGBoostConfig(random_state=42),
        test_ratio=0.2,
        embargo_sessions=1,
    )

    assert isinstance(result, DirectionTrainingResult)
    assert result.model.is_fitted is True
    assert result.split.train_rows == 39
    assert result.split.test_rows == 10
    assert isinstance(result.train_metrics, ClassificationMetrics)
    assert isinstance(result.holdout_metrics, ClassificationMetrics)

    d = result.to_dict()
    assert d["feature_count"] == len(FEATURE_COLUMNS)
    assert "accuracy" in d["holdout_metrics"]
    assert "confusion_matrix" in d["holdout_metrics"]
