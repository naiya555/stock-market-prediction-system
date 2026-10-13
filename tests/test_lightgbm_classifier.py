"""Unit Tests for Day 19 LightGBM Direction Classifier Baseline.

Tests:
1. Configuration defaults and dictionary serialization.
2. Successful model fitting and inference on valid synthetic dataset.
3. Feature column schema preservation and column realignment.
4. Missing value rejection policy (allow_missing=False).
5. Empty dataset rejection handling.
6. Single-class dataset rejection handling.
7. Target and future-column leakage rejection (isolation guard).
8. Deterministic, reproducible predictions across repeated runs with identical seed.
9. Probability prediction structure (predict_proba sums to 1.0, shape (N, 2)).
10. Model persistence (save and load model file).
11. Feature importance extraction.
12. Graceful ImportError handling when lightgbm is unavailable.
13. Small dataset rejection handling (< 10 samples).
14. Sample count mismatch between X and y rejection.
"""

from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest.mock as mock

import numpy as np
import pandas as pd
import pytest

from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FeatureMatrixDataset,
)
from app.training.lightgbm_classifier import (
    HAS_LIGHTGBM,
    LightGBMConfig,
    LightGBMDirectionClassifier,
)
from app.training.xgboost_classifier import compute_classification_metrics


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


# 1. Configuration tests
def test_lightgbm_config_defaults_and_customization() -> None:
    """Verify default conservative hyperparameters and dictionary serialization."""
    config = LightGBMConfig()
    assert config.objective == "binary"
    assert config.metric == "binary_logloss"
    assert config.random_state == 42
    assert config.max_depth == 3
    assert config.num_leaves == 7
    assert config.learning_rate == 0.05
    assert config.n_estimators == 50
    assert config.subsample == 0.8
    assert config.colsample_bytree == 0.8
    assert config.n_jobs == 1
    assert config.allow_missing is False

    params = config.to_params_dict()
    assert params["objective"] == "binary"
    assert params["seed"] == 42
    assert params["num_threads"] == 1
    assert params["deterministic"] is True

    d = config.to_dict()
    assert isinstance(d, dict)
    assert d["random_state"] == 42


# 2. Successful fitting on small valid synthetic dataset
def test_successful_fitting_synthetic_data(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify classifier fits cleanly on synthetic features and predicts valid classes."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y = synthetic_labeled_df["target_binary"]

    clf = LightGBMDirectionClassifier(config=LightGBMConfig(min_child_samples=5))
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

    clf = LightGBMDirectionClassifier(config=LightGBMConfig(min_child_samples=5))
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

    clf = LightGBMDirectionClassifier(config=LightGBMConfig(allow_missing=False, min_child_samples=5))
    with pytest.raises(ValueError, match="contains missing \\(NaN\\) values"):
        clf.fit(X, y)


# 5. Empty dataset handling
def test_empty_dataset_rejection() -> None:
    """Verify empty feature dataset raises ValueError."""
    X_empty = pd.DataFrame(columns=FEATURE_COLUMNS)
    y_empty = pd.Series([], dtype=int)

    clf = LightGBMDirectionClassifier()
    with pytest.raises(ValueError, match="Cannot fit model on empty feature dataset"):
        clf.fit(X_empty, y_empty)


# 6. Single-class dataset handling
def test_single_class_dataset_rejection(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify single-class dataset (e.g. all 1s or all 0s) is rejected with clear error."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y_all_ones = pd.Series([1] * len(X))

    clf = LightGBMDirectionClassifier(config=LightGBMConfig(min_child_samples=5))
    with pytest.raises(ValueError, match="Dataset contains only one target class"):
        clf.fit(X, y_all_ones)


# 7. Target and future-column leakage rejection
def test_target_and_future_column_leakage_rejection(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify feature matrix containing target or outcome columns is rejected by isolation guard."""
    X_leaked = synthetic_labeled_df.copy()  # Contains target_return, next_close, etc.
    y = synthetic_labeled_df["target_binary"]

    clf = LightGBMDirectionClassifier(config=LightGBMConfig(min_child_samples=5))
    with pytest.raises(ValueError, match="Data leakage detected! Feature matrix X contains forbidden column"):
        clf.fit(X_leaked, y)


# 8. Deterministic, reproducible predictions
def test_deterministic_reproducible_predictions(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify identical seed yields identical predictions on the same dataset."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y = synthetic_labeled_df["target_binary"]

    clf1 = LightGBMDirectionClassifier(config=LightGBMConfig(random_state=42, min_child_samples=5))
    clf1.fit(X, y)
    preds1 = clf1.predict_proba(X)

    clf2 = LightGBMDirectionClassifier(config=LightGBMConfig(random_state=42, min_child_samples=5))
    clf2.fit(X, y)
    preds2 = clf2.predict_proba(X)

    np.testing.assert_allclose(preds1, preds2, rtol=1e-5, atol=1e-5)


# 9. Probability prediction structure
def test_predict_proba_structure(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify probability predictions form a valid 2D distribution summing to 1."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y = synthetic_labeled_df["target_binary"]

    clf = LightGBMDirectionClassifier(config=LightGBMConfig(min_child_samples=5))
    clf.fit(X, y)
    proba = clf.predict_proba(X)

    assert proba.shape == (len(X), 2)
    assert np.allclose(proba[:, 0] + proba[:, 1], 1.0)


# 10. Model persistence (save and load)
def test_model_persistence(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify model can be saved to file and reloaded to produce identical predictions."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y = synthetic_labeled_df["target_binary"]

    clf = LightGBMDirectionClassifier(config=LightGBMConfig(min_child_samples=5))
    clf.fit(X, y)
    orig_preds = clf.predict_proba(X)

    with tempfile.TemporaryDirectory() as tmp_dir:
        model_file = Path(tmp_dir) / "lgb_baseline.txt"
        clf.save_model(model_file)
        assert model_file.is_file()

        loaded_clf = LightGBMDirectionClassifier()
        loaded_clf.load_model(model_file)
        assert loaded_clf.is_fitted is True

        loaded_preds = loaded_clf.predict_proba(X)
        np.testing.assert_allclose(orig_preds, loaded_preds, rtol=1e-5, atol=1e-5)


# 11. Feature importance extraction
def test_feature_importance_extraction(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify feature importances are extracted cleanly for all feature columns."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y = synthetic_labeled_df["target_binary"]

    clf = LightGBMDirectionClassifier(config=LightGBMConfig(min_child_samples=5))
    clf.fit(X, y)

    importances = clf.feature_importances_
    assert isinstance(importances, dict)
    assert set(importances.keys()) == set(FEATURE_COLUMNS)
    assert all(isinstance(v, float) for v in importances.values())


# 12. Graceful ImportError handling
def test_graceful_missing_lightgbm_error(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify explicit error if lightgbm is not available."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y = synthetic_labeled_df["target_binary"]

    with mock.patch("app.training.lightgbm_classifier.HAS_LIGHTGBM", False):
        clf = LightGBMDirectionClassifier()
        with pytest.raises(ImportError, match="lightgbm is not installed"):
            clf.fit(X, y)


# 13. Small dataset rejection
def test_small_dataset_rejection(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify dataset with fewer than 10 samples is rejected."""
    X_small = synthetic_labeled_df[FEATURE_COLUMNS].iloc[:5]
    y_small = synthetic_labeled_df["target_binary"].iloc[:5]

    clf = LightGBMDirectionClassifier()
    with pytest.raises(ValueError, match="Dataset too small to fit classifier"):
        clf.fit(X_small, y_small)


# 14. Sample count mismatch
def test_sample_count_mismatch(synthetic_labeled_df: pd.DataFrame) -> None:
    """Verify mismatched row counts between X and y raise ValueError."""
    X = synthetic_labeled_df[FEATURE_COLUMNS]
    y_short = synthetic_labeled_df["target_binary"].iloc[:20]

    clf = LightGBMDirectionClassifier()
    with pytest.raises(ValueError, match="Sample count mismatch"):
        clf.fit(X, y_short)
