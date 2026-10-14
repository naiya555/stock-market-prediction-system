"""Unit and Regression Tests for Walk-Forward Temporal Cross-Validation.

Validates:
1. Chronological expanding-window fold boundaries and strictly ascending order.
2. Temporal embargo gap enforcement and zero future lookahead leakage (train_outcome_cutoff <= val_start_date).
3. Complete pairwise disjointness of train, embargo, and validation index sets.
4. Input validation and error handling (undersized datasets, invalid parameters, invalid types).
5. Fault tolerance for single-class training labels (explicit SKIPPED_SINGLE_CLASS status).
6. Identical validation samples evaluated across all candidate strategies.
7. Exact reproducibility across repeated runs with identical random seeds.
8. Mathematical accuracy of macro fold aggregation (mean +/- sample std, ddof=1) and pooled metrics.
9. Table serialization (summary_table and fold_breakdown_table).
10. Input flexibility (FeatureMatrixDataset, DataFrame, and (X, y) tuple inputs).
11. Feature matrix isolation guards rejecting forbidden target or outcome columns.
"""

from datetime import datetime, timedelta
from typing import List

import numpy as np
import pandas as pd
import pytest

from app.core.schemas import MarketOHLCV
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FeatureMatrixDataset,
    assemble_feature_matrix,
)
from app.training.lightgbm_classifier import HAS_LIGHTGBM
from app.training.walk_forward import (
    WalkForwardFoldEvaluation,
    WalkForwardFoldSplit,
    WalkForwardReport,
    WalkForwardStrategySummary,
    evaluate_walk_forward,
    generate_walk_forward_splits,
)
from app.training.xgboost_classifier import compute_classification_metrics


@pytest.fixture
def synthetic_feature_dataset() -> FeatureMatrixDataset:
    """Generate a deterministic synthetic FeatureMatrixDataset of 120 sequential trading bars."""
    rng = np.random.RandomState(42)
    n_total = 120
    start_dt = datetime(2023, 1, 2)

    dates = []
    current_date = start_dt
    for _ in range(n_total):
        while current_date.weekday() >= 5:
            current_date += timedelta(days=1)
        dates.append(current_date)
        current_date += timedelta(days=1)

    next_dates = dates[1:] + [dates[-1] + timedelta(days=1)]

    # Balanced targets: alternating 1 and 0
    y_all = [1 if i % 2 == 0 else 0 for i in range(n_total)]

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

    return FeatureMatrixDataset(
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



# 1. Chronological ordering and fold boundaries
def test_generate_walk_forward_splits_boundaries_and_order(
    synthetic_feature_dataset: FeatureMatrixDataset,
) -> None:
    """Verify that walk-forward splits expand monotonically and maintain correct boundary sizing."""
    splits = generate_walk_forward_splits(
        data=synthetic_feature_dataset,
        n_splits=4,
        min_train_ratio=0.4,
        embargo_sessions=1,
    )

    assert len(splits) == 4

    prev_train_rows = 0
    prev_val_end = -1

    for s in splits:
        # Folds are 1-indexed
        assert s.fold >= 1
        # Training size expands monotonically
        assert s.train_rows > prev_train_rows
        prev_train_rows = s.train_rows

        # Embargo is strictly 1 session
        assert s.embargo_rows == 1
        assert len(s.embargo_indices) == 1

        # Validation window is non-empty
        assert s.val_rows >= 5
        assert len(s.val_indices) == s.val_rows

        # Contiguous validation windows across folds
        if prev_val_end != -1:
            assert min(s.val_indices) == prev_val_end
        prev_val_end = max(s.val_indices) + 1

        # Train and val have both classes in this balanced synthetic dataset
        assert s.train_up_count > 0
        assert s.train_down_count > 0
        assert s.val_up_count > 0
        assert s.val_down_count > 0


# 2. Embargo and target leakage prevention
def test_walk_forward_embargo_and_leakage_prevention(
    synthetic_feature_dataset: FeatureMatrixDataset,
) -> None:
    """Verify that train_outcome_cutoff <= val_start_date on all folds."""
    splits = generate_walk_forward_splits(
        data=synthetic_feature_dataset,
        n_splits=5,
        min_train_ratio=0.35,
        embargo_sessions=1,
    )

    for s in splits:
        assert s.train_outcome_cutoff is not None
        assert s.val_start_date is not None
        # Invariant: Training label outcome cutoff must not exceed validation start date
        assert s.train_outcome_cutoff <= s.val_start_date
        # Embargo row separates the last training row from the first validation row
        assert max(s.train_indices) < min(s.embargo_indices)
        assert max(s.embargo_indices) < min(s.val_indices)


# 3. Train/validation/embargo index separation (pairwise disjoint)
def test_walk_forward_index_disjointness(
    synthetic_feature_dataset: FeatureMatrixDataset,
) -> None:
    """Verify train, validation, and embargo index sets are strictly pairwise disjoint."""
    splits = generate_walk_forward_splits(
        data=synthetic_feature_dataset,
        n_splits=3,
        min_train_ratio=0.4,
        embargo_sessions=2,
    )

    for s in splits:
        set_tr = set(s.train_indices)
        set_va = set(s.val_indices)
        set_em = set(s.embargo_indices)

        assert set_tr.isdisjoint(set_va)
        assert set_tr.isdisjoint(set_em)
        assert set_va.isdisjoint(set_em)
        assert max(s.train_indices) < min(s.val_indices)


# 4. Input validation and error handling
def test_walk_forward_invalid_parameters(
    synthetic_feature_dataset: FeatureMatrixDataset,
) -> None:
    """Verify parameter validation for n_splits, embargo, min_train_ratio, and dataset size."""
    # n_splits < 2
    with pytest.raises(ValueError, match="n_splits must be at least 2"):
        generate_walk_forward_splits(synthetic_feature_dataset, n_splits=1)

    # embargo < 1
    with pytest.raises(ValueError, match="embargo_sessions must be at least 1"):
        generate_walk_forward_splits(synthetic_feature_dataset, embargo_sessions=0)

    # invalid min_train_ratio
    with pytest.raises(ValueError, match="min_train_ratio must be between 0.0 and 1.0"):
        generate_walk_forward_splits(synthetic_feature_dataset, min_train_ratio=0.0)
    with pytest.raises(ValueError, match="min_train_ratio must be between 0.0 and 1.0"):
        generate_walk_forward_splits(synthetic_feature_dataset, min_train_ratio=1.0)

    # Unsupported data type
    with pytest.raises(ValueError, match="Unsupported data type"):
        generate_walk_forward_splits("invalid_type")  # type: ignore


def test_walk_forward_undersized_dataset_error() -> None:
    """Verify error raised when dataset has fewer samples than required by configuration."""
    tiny_df = pd.DataFrame({
        "open": [10.0] * 15,
        "high": [11.0] * 15,
        "low": [9.0] * 15,
        "close": [10.0] * 15,
        "volume": [1000] * 15,
        "target_binary": [1, 0] * 7 + [1],
    })

    with pytest.raises(ValueError, match="Dataset too small"):
        generate_walk_forward_splits(
            data=tiny_df,
            n_splits=5,
            min_train_samples=20,
            min_val_samples=5,
            embargo_sessions=1,
        )


# 5. Fault tolerance for single-class training labels
def test_walk_forward_single_class_training_handling() -> None:
    """Verify that when a fold training set contains only a single class, it is skipped gracefully."""
    # Create dataset where the first 25 rows have target=0 only, and subsequent rows have 1
    df = pd.DataFrame({
        c: np.random.randn(50) for c in FEATURE_COLUMNS
    })
    # Target: 0 for first 25, 1 for remaining 25
    df["target_binary"] = [0] * 25 + [1] * 25

    report = evaluate_walk_forward(
        data=df,
        n_splits=2,
        min_train_ratio=0.4,
        min_train_samples=10,
        min_val_samples=5,
        embargo_sessions=1,
    )

    # Fold 1 train set is rows 0..19, which contains only class 0
    f1_evals = [e for e in report.fold_evaluations if e.fold == 1]
    for ev in f1_evals:
        assert ev.status == "SKIPPED_SINGLE_CLASS"
        assert ev.skip_reason is not None
        assert "single class" in ev.skip_reason.lower()


# 6. Identical validation samples evaluated across all candidate strategies
def test_walk_forward_identical_validation_samples_across_strategies(
    synthetic_feature_dataset: FeatureMatrixDataset,
) -> None:
    """Verify that all strategies are evaluated on identical validation samples for every fold."""
    report = evaluate_walk_forward(
        data=synthetic_feature_dataset,
        n_splits=3,
        min_train_ratio=0.4,
        embargo_sessions=1,
    )

    for fold_idx in range(1, 4):
        fold_evals = [e for e in report.fold_evaluations if e.fold == fold_idx]
        assert len(fold_evals) >= 4  # Majority, Uniform, Stratified, XGBoost (and LightGBM if installed)
        expected_samples = fold_evals[0].metrics.total_samples

        for ev in fold_evals:
            assert ev.metrics.total_samples == expected_samples
            assert ev.pred_up_count + ev.pred_down_count == expected_samples


# 7. Reproducibility across repeated runs with identical random seed
def test_walk_forward_reproducibility(
    synthetic_feature_dataset: FeatureMatrixDataset,
) -> None:
    """Verify that evaluate_walk_forward produces identical metrics when called with the same seed."""
    rep1 = evaluate_walk_forward(
        data=synthetic_feature_dataset,
        n_splits=3,
        min_train_ratio=0.4,
        random_seed=42,
    )
    rep2 = evaluate_walk_forward(
        data=synthetic_feature_dataset,
        n_splits=3,
        min_train_ratio=0.4,
        random_seed=42,
    )

    assert rep1.best_strategy_by_mean_accuracy == rep2.best_strategy_by_mean_accuracy
    assert rep1.best_strategy_by_mean_f1 == rep2.best_strategy_by_mean_f1

    for strat_name, s1 in rep1.strategy_summaries.items():
        s2 = rep2.strategy_summaries[strat_name]
        assert s1.mean_accuracy == s2.mean_accuracy
        assert s1.std_accuracy == s2.std_accuracy
        assert s1.mean_f1 == s2.mean_f1
        assert s1.pooled_confusion_matrix == s2.pooled_confusion_matrix


# 8. Correct aggregation of fold metrics (mean, sample std ddof=1, pooled confusion matrix)
def test_walk_forward_aggregation_mathematics(
    synthetic_feature_dataset: FeatureMatrixDataset,
) -> None:
    """Verify macro mean, sample standard deviation (ddof=1), and pooled confusion matrix math."""
    report = evaluate_walk_forward(
        data=synthetic_feature_dataset,
        n_splits=3,
        min_train_ratio=0.4,
        embargo_sessions=1,
        random_seed=42,
    )

    for name, summ in report.strategy_summaries.items():
        accs = summ.fold_accuracies
        assert len(accs) == 3
        # Macro mean matches numpy
        assert summ.mean_accuracy == pytest.approx(round(float(np.mean(accs)), 4), abs=1e-4)
        # Sample standard deviation (ddof=1)
        assert summ.std_accuracy == pytest.approx(round(float(np.std(accs, ddof=1)), 4), abs=1e-4)

        # Pooled confusion matrix equals sum of individual fold confusion matrices
        strat_evals = [e for e in report.fold_evaluations if e.strategy_name == name and e.status == "COMPLETED"]
        manual_tn = sum(e.metrics.true_negatives for e in strat_evals)
        manual_fp = sum(e.metrics.false_positives for e in strat_evals)
        manual_fn = sum(e.metrics.false_negatives for e in strat_evals)
        manual_tp = sum(e.metrics.true_positives for e in strat_evals)

        assert summ.pooled_confusion_matrix == [[manual_tn, manual_fp], [manual_fn, manual_tp]]
        total_p = manual_tn + manual_fp + manual_fn + manual_tp
        assert summ.pooled_accuracy == pytest.approx(round((manual_tn + manual_tp) / total_p, 4), abs=1e-4)


# 9. Table serialization
def test_walk_forward_table_rendering(
    synthetic_feature_dataset: FeatureMatrixDataset,
) -> None:
    """Verify summary_table and fold_breakdown_table produce valid markdown tables."""
    report = evaluate_walk_forward(
        data=synthetic_feature_dataset,
        n_splits=3,
        min_train_ratio=0.4,
        random_seed=42,
    )

    summary_tbl = report.summary_table()
    assert "| Strategy" in summary_tbl
    assert "Model C (Day 17 XGBoost)" in summary_tbl
    assert "Baseline A (Majority Class)" in summary_tbl

    breakdown_tbl = report.fold_breakdown_table()
    assert "| Fold |" in breakdown_tbl
    assert "| 1 |" in breakdown_tbl
    assert "| 2 |" in breakdown_tbl
    assert "| 3 |" in breakdown_tbl


# 10. Flexibility across input types (FeatureMatrixDataset, DataFrame, and (X, y) tuple)
def test_walk_forward_input_types_compatibility(
    synthetic_feature_dataset: FeatureMatrixDataset,
) -> None:
    """Verify identical splits generated whether input is FeatureMatrixDataset, DataFrame, or (X, y) tuple."""
    # From FeatureMatrixDataset
    splits_ds = generate_walk_forward_splits(synthetic_feature_dataset, n_splits=3)

    # From DataFrame
    complete_mask = synthetic_feature_dataset.y.notna() & synthetic_feature_dataset.X.notna().all(axis=1)
    df_clean = synthetic_feature_dataset.df[complete_mask].copy().reset_index(drop=True)
    splits_df = generate_walk_forward_splits(df_clean, n_splits=3)

    # From (X, y) tuple
    X_clean = df_clean[FEATURE_COLUMNS]
    y_clean = df_clean["target_binary"]
    splits_tup = generate_walk_forward_splits((X_clean, y_clean), n_splits=3)

    assert len(splits_ds) == len(splits_df) == len(splits_tup) == 3
    for i in range(3):
        assert splits_ds[i].train_rows == splits_df[i].train_rows == splits_tup[i].train_rows
        assert splits_ds[i].val_rows == splits_df[i].val_rows == splits_tup[i].val_rows
        assert splits_ds[i].embargo_rows == splits_df[i].embargo_rows == splits_tup[i].embargo_rows


# 11. Feature matrix isolation guard
def test_walk_forward_isolation_guard_rejection() -> None:
    """Verify that walk-forward split generation rejects dataframes containing forbidden leak columns."""
    leaky_df = pd.DataFrame({
        c: np.random.randn(60) for c in FEATURE_COLUMNS
    })
    leaky_df["target_binary"] = np.random.choice([0, 1], size=60)
    # Inject forbidden column
    leaky_df["target_return_leak"] = np.random.randn(60)

    with pytest.raises(ValueError, match="Data leakage detected"):
        generate_walk_forward_splits(leaky_df, n_splits=2)
