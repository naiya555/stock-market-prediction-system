"""Walk-Forward Temporal Cross-Validation Layer.

Implements leakage-safe, expanding-window walk-forward temporal cross-validation
for financial time series. Strictly prevents future lookahead leakage:
1. Chronological expanding-window folds: each fold trains only on past data.
2. Temporal embargo gap (default >= 1 session): ensures training outcome dates
   never touch or overlap with validation window session dates.
3. Strict index and date validation: zero index overlap between train, embargo, and val.
4. Identical validation evaluation across baselines, XGBoost, and LightGBM.
5. Multi-fold aggregation: reports both unweighted fold averages (mean +/- std)
   and micro-pooled confusion matrix totals across all validation samples.
6. Explicit fault tolerance: detects undersized or single-class folds without
   silent failures or metric fabrication.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from app.training.baselines import (
    MajorityClassClassifier,
    RandomClassifier,
)
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FeatureMatrixDataset,
    validate_feature_matrix_isolation,
)
from app.training.lightgbm_classifier import (
    HAS_LIGHTGBM,
    LightGBMConfig,
    LightGBMDirectionClassifier,
)
from app.training.xgboost_classifier import (
    ClassificationMetrics,
    XGBoostConfig,
    XGBoostDirectionClassifier,
    compute_classification_metrics,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class WalkForwardFoldSplit:
    """Artifacts and temporal boundaries for a single walk-forward validation fold."""

    fold: int
    X_train: pd.DataFrame
    y_train: pd.Series
    X_val: pd.DataFrame
    y_val: pd.Series
    train_indices: List[int]
    val_indices: List[int]
    embargo_indices: List[int]
    train_start_date: Optional[str]
    train_end_date: Optional[str]
    train_outcome_cutoff: Optional[str]
    val_start_date: Optional[str]
    val_end_date: Optional[str]
    train_rows: int
    val_rows: int
    embargo_rows: int
    train_up_count: int
    train_down_count: int
    train_up_ratio: float
    val_up_count: int
    val_down_count: int
    val_up_ratio: float
    metadata_train: Optional[pd.DataFrame] = None
    metadata_val: Optional[pd.DataFrame] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize fold split boundaries and sample counts."""
        return {
            "fold": self.fold,
            "train_rows": self.train_rows,
            "val_rows": self.val_rows,
            "embargo_rows": self.embargo_rows,
            "train_start_date": self.train_start_date,
            "train_end_date": self.train_end_date,
            "train_outcome_cutoff": self.train_outcome_cutoff,
            "val_start_date": self.val_start_date,
            "val_end_date": self.val_end_date,
            "train_up_count": self.train_up_count,
            "train_down_count": self.train_down_count,
            "train_up_ratio": self.train_up_ratio,
            "val_up_count": self.val_up_count,
            "val_down_count": self.val_down_count,
            "val_up_ratio": self.val_up_ratio,
        }


def generate_walk_forward_splits(
    data: Union[FeatureMatrixDataset, pd.DataFrame, Tuple[pd.DataFrame, pd.Series]],
    n_splits: int = 5,
    min_train_ratio: float = 0.4,
    embargo_sessions: int = 1,
    min_train_samples: int = 20,
    min_val_samples: int = 5,
    drop_incomplete_warmup: bool = True,
) -> List[WalkForwardFoldSplit]:
    """Generate chronological expanding-window splits with strict outcome embargoes.

    Partitioning Mathematics:
    - Given N clean labeled observations in chronological order.
    - An initial training window of size N_train_init = max(min_train_samples, floor(N * min_train_ratio))
      is reserved for the first fold.
    - The remaining observations (N - N_train_init) are divided into K validation folds.
    - For fold k in 0..K-1:
        Val window:   [v_start .. v_end)
        Embargo gap:  [v_start - embargo_sessions .. v_start)
        Train window: [0 .. v_start - embargo_sessions)
    - Because each training observation at index t has an outcome timestamp realized at t+1,
      purging at least 1 session prior to v_start guarantees that the latest training outcome
      cutoff is strictly earlier than or equal to the first validation session date.

    Args:
        data: FeatureMatrixDataset, combined DataFrame, or (X, y) tuple.
        n_splits: Number of chronological validation folds (default 5, must be >= 2).
        min_train_ratio: Fraction of dataset reserved for initial training partition (default 0.4).
        embargo_sessions: Sessions purged between train and val to prevent label leakage (default 1, >= 1).
        min_train_samples: Minimum allowable training samples for any fold (default 20).
        min_val_samples: Minimum allowable validation samples for any fold (default 5).
        drop_incomplete_warmup: Whether to filter incomplete indicator warmup rows (default True).

    Returns:
        List of WalkForwardFoldSplit instances in chronological order.

    Raises:
        ValueError: On invalid configurations, insufficient data, or detected temporal leakage.
    """
    if n_splits < 2:
        raise ValueError(f"n_splits must be at least 2, got {n_splits}")
    if embargo_sessions < 1:
        raise ValueError(f"embargo_sessions must be at least 1, got {embargo_sessions}")
    if min_train_ratio <= 0.0 or min_train_ratio >= 1.0:
        raise ValueError(f"min_train_ratio must be between 0.0 and 1.0 (exclusive), got {min_train_ratio}")

    # Step 1: Extract clean tabular DataFrame
    if isinstance(data, FeatureMatrixDataset):
        if drop_incomplete_warmup:
            complete_mask = data.y.notna() & data.X.notna().all(axis=1)
        else:
            complete_mask = data.y.notna()
        sub_df = data.df[complete_mask].copy().reset_index(drop=True)
    elif isinstance(data, pd.DataFrame):
        sub_df = data.copy().reset_index(drop=True)
    elif isinstance(data, tuple) and len(data) == 2:
        X_in, y_in = data
        sub_df = X_in.copy().reset_index(drop=True)
        sub_df["target_binary"] = y_in.values
    else:
        raise ValueError(f"Unsupported data type for walk-forward splitting: {type(data)}")

    n_samples = len(sub_df)
    min_required = min_train_samples + (n_splits * min_val_samples) + embargo_sessions
    if n_samples < min_required:
        raise ValueError(
            f"Dataset too small for {n_splits}-fold walk-forward validation: "
            f"has {n_samples} rows, requires at least {min_required} "
            f"(min_train={min_train_samples}, min_val={min_val_samples}, embargo={embargo_sessions})."
        )

    # Step 2: Calculate fold boundaries
    min_train_init = max(min_train_samples, int(np.floor(n_samples * min_train_ratio)))
    val_pool = n_samples - min_train_init
    val_size = val_pool // n_splits

    if val_size < min_val_samples:
        raise ValueError(
            f"Resulting validation fold size ({val_size}) is smaller than min_val_samples ({min_val_samples}). "
            f"Reduce n_splits or reduce min_train_ratio."
        )

    # Identify feature and metadata columns
    known_non_features = set(
        ["symbol", "timestamp", "next_timestamp", "current_close", "next_close"]
        + ["target_return", "target_direction", "target_binary"]
    )
    feature_candidates = [c for c in sub_df.columns if c not in known_non_features]
    if feature_candidates:
        validate_feature_matrix_isolation(sub_df[feature_candidates])

    feature_cols = [c for c in FEATURE_COLUMNS if c in sub_df.columns]
    if not feature_cols:
        feature_cols = feature_candidates


    meta_cols = [
        c for c in ["symbol", "timestamp", "next_timestamp", "current_close", "next_close", "target_direction"]
        if c in sub_df.columns
    ]

    splits: List[WalkForwardFoldSplit] = []

    for k in range(n_splits):
        v_start = min_train_init + k * val_size
        v_end = min_train_init + (k + 1) * val_size if k < n_splits - 1 else n_samples
        e_start = v_start - embargo_sessions
        e_end = v_start
        t_start = 0
        t_end = e_start

        if t_end < min_train_samples:
            raise ValueError(
                f"Fold {k + 1}: training samples ({t_end}) smaller than min_train_samples ({min_train_samples})."
            )
        if (v_end - v_start) < min_val_samples:
            raise ValueError(
                f"Fold {k + 1}: validation samples ({v_end - v_start}) smaller than min_val_samples ({min_val_samples})."
            )

        train_df = sub_df.iloc[t_start:t_end].copy()
        embargo_df = sub_df.iloc[e_start:e_end].copy()
        val_df = sub_df.iloc[v_start:v_end].copy()

        train_indices = list(range(t_start, t_end))
        embargo_indices = list(range(e_start, e_end))
        val_indices = list(range(v_start, v_end))

        # Invariant: Disjoint indices
        if set(train_indices) & set(val_indices):
            raise ValueError(f"Fold {k + 1}: Overlapping train and validation indices detected.")
        if set(train_indices) & set(embargo_indices):
            raise ValueError(f"Fold {k + 1}: Overlapping train and embargo indices detected.")
        if set(val_indices) & set(embargo_indices):
            raise ValueError(f"Fold {k + 1}: Overlapping validation and embargo indices detected.")
        if max(train_indices) >= min(val_indices):
            raise ValueError(f"Fold {k + 1}: Non-chronological ordering between train and val indices.")

        # Extract timestamps and check temporal leakage
        train_start_date: Optional[str] = None
        train_end_date: Optional[str] = None
        train_outcome_cutoff: Optional[str] = None
        val_start_date: Optional[str] = None
        val_end_date: Optional[str] = None

        if "timestamp" in sub_df.columns:
            train_start_date = str(train_df["timestamp"].iloc[0])[:10]
            train_end_date = str(train_df["timestamp"].iloc[-1])[:10]
            val_start_date = str(val_df["timestamp"].iloc[0])[:10]
            val_end_date = str(val_df["timestamp"].iloc[-1])[:10]

        if "next_timestamp" in sub_df.columns:
            train_outcome_cutoff = str(train_df["next_timestamp"].iloc[-1])[:10]
            if val_start_date is not None and train_outcome_cutoff > val_start_date:
                raise ValueError(
                    f"Fold {k + 1}: Temporal leakage detected! "
                    f"train_outcome_cutoff ({train_outcome_cutoff}) > val_start_date ({val_start_date})."
                )

        X_train = train_df[feature_cols].copy()
        y_train = train_df["target_binary"].astype(int).copy()
        X_val = val_df[feature_cols].copy()
        y_val = val_df["target_binary"].astype(int).copy()

        # Enforce feature matrix isolation guard
        validate_feature_matrix_isolation(X_train)
        validate_feature_matrix_isolation(X_val)

        train_up = int(np.sum(y_train == 1))
        train_down = int(np.sum(y_train == 0))
        val_up = int(np.sum(y_val == 1))
        val_down = int(np.sum(y_val == 0))

        metadata_train = train_df[meta_cols].copy() if meta_cols else None
        metadata_val = val_df[meta_cols].copy() if meta_cols else None

        split = WalkForwardFoldSplit(
            fold=k + 1,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            train_indices=train_indices,
            val_indices=val_indices,
            embargo_indices=embargo_indices,
            train_start_date=train_start_date,
            train_end_date=train_end_date,
            train_outcome_cutoff=train_outcome_cutoff,
            val_start_date=val_start_date,
            val_end_date=val_end_date,
            train_rows=len(X_train),
            val_rows=len(X_val),
            embargo_rows=len(embargo_df),
            train_up_count=train_up,
            train_down_count=train_down,
            train_up_ratio=round(train_up / len(y_train), 4) if len(y_train) > 0 else 0.0,
            val_up_count=val_up,
            val_down_count=val_down,
            val_up_ratio=round(val_up / len(y_val), 4) if len(y_val) > 0 else 0.0,
            metadata_train=metadata_train,
            metadata_val=metadata_val,
        )
        splits.append(split)

    return splits


@dataclass(frozen=True)
class WalkForwardFoldEvaluation:
    """Evaluation metrics for a single strategy on a specific validation fold."""

    fold: int
    strategy_name: str
    metrics: ClassificationMetrics
    pred_up_count: int
    pred_down_count: int
    status: str = "COMPLETED"
    skip_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize fold evaluation metrics."""
        return {
            "fold": self.fold,
            "strategy_name": self.strategy_name,
            "status": self.status,
            "skip_reason": self.skip_reason,
            "accuracy": self.metrics.accuracy,
            "precision": self.metrics.precision,
            "recall": self.metrics.recall,
            "f1": self.metrics.f1,
            "confusion_matrix": self.metrics.confusion_matrix,
            "pred_up_count": self.pred_up_count,
            "pred_down_count": self.pred_down_count,
            "total_samples": self.metrics.total_samples,
        }


@dataclass
class WalkForwardStrategySummary:
    """Aggregated cross-validation metrics across all folds for a strategy."""

    strategy_name: str
    folds_evaluated: int
    fold_accuracies: List[float]
    fold_f1s: List[float]
    fold_precisions: List[float]
    fold_recalls: List[float]
    mean_accuracy: float
    std_accuracy: float
    mean_f1: float
    std_f1: float
    mean_precision: float
    std_precision: float
    mean_recall: float
    std_recall: float
    pooled_confusion_matrix: List[List[int]]
    pooled_accuracy: float
    pooled_precision: float
    pooled_recall: float
    pooled_f1: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize strategy aggregate performance."""
        return {
            "strategy_name": self.strategy_name,
            "folds_evaluated": self.folds_evaluated,
            "fold_accuracies": self.fold_accuracies,
            "fold_f1s": self.fold_f1s,
            "mean_accuracy": self.mean_accuracy,
            "std_accuracy": self.std_accuracy,
            "mean_f1": self.mean_f1,
            "std_f1": self.std_f1,
            "mean_precision": self.mean_precision,
            "std_precision": self.std_precision,
            "mean_recall": self.mean_recall,
            "std_recall": self.std_recall,
            "pooled_confusion_matrix": self.pooled_confusion_matrix,
            "pooled_accuracy": self.pooled_accuracy,
            "pooled_precision": self.pooled_precision,
            "pooled_recall": self.pooled_recall,
            "pooled_f1": self.pooled_f1,
        }


@dataclass
class WalkForwardReport:
    """Complete summary container for walk-forward temporal cross-validation."""

    symbol: str
    total_dataset_rows: int
    retained_rows: int
    n_splits: int
    embargo_sessions: int
    folds: List[WalkForwardFoldSplit]
    fold_evaluations: List[WalkForwardFoldEvaluation]
    strategy_summaries: Dict[str, WalkForwardStrategySummary]
    best_strategy_by_mean_accuracy: str
    best_strategy_by_mean_f1: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entire walk-forward report."""
        return {
            "symbol": self.symbol,
            "total_dataset_rows": self.total_dataset_rows,
            "retained_rows": self.retained_rows,
            "n_splits": self.n_splits,
            "embargo_sessions": self.embargo_sessions,
            "folds": [f.to_dict() for f in self.folds],
            "fold_evaluations": [e.to_dict() for e in self.fold_evaluations],
            "strategy_summaries": {k: v.to_dict() for k, v in self.strategy_summaries.items()},
            "best_strategy_by_mean_accuracy": self.best_strategy_by_mean_accuracy,
            "best_strategy_by_mean_f1": self.best_strategy_by_mean_f1,
        }

    def summary_table(self) -> str:
        """Render a clean Markdown summary table comparing all strategies."""
        headers = [
            "Strategy",
            "Folds",
            "Mean Acc (±Std)",
            "Mean F1 (±Std)",
            "Mean Prec",
            "Mean Rec",
            "Pooled Acc",
            "Pooled F1",
            "Pooled CM [[TN,FP],[FN,TP]]",
        ]
        col_w = [40, 7, 18, 18, 11, 11, 12, 11, 30]

        sep = "|" + "|".join("-" * (w + 2) for w in col_w) + "|"
        header_str = "|" + "|".join(f" {h:<{col_w[i]}} " for i, h in enumerate(headers)) + "|"

        rows = []
        for name, summ in self.strategy_summaries.items():
            acc_str = f"{summ.mean_accuracy*100:.2f}% (±{summ.std_accuracy*100:.2f}%)"
            f1_str = f"{summ.mean_f1:.4f} (±{summ.std_f1:.4f})"
            prec_str = f"{summ.mean_precision*100:.2f}%"
            rec_str = f"{summ.mean_recall*100:.2f}%"
            p_acc_str = f"{summ.pooled_accuracy*100:.2f}%"
            p_f1_str = f"{summ.pooled_f1:.4f}"
            cm_str = str(summ.pooled_confusion_matrix).replace(" ", "")

            row_str = (
                f"| {name:<{col_w[0]}} "
                f"| {summ.folds_evaluated:^{col_w[1]}} "
                f"| {acc_str:<{col_w[2]}} "
                f"| {f1_str:<{col_w[3]}} "
                f"| {prec_str:<{col_w[4]}} "
                f"| {rec_str:<{col_w[5]}} "
                f"| {p_acc_str:<{col_w[6]}} "
                f"| {p_f1_str:<{col_w[7]}} "
                f"| {cm_str:<{col_w[8]}} |"
            )
            rows.append(row_str)

        return "\n".join([header_str, sep] + rows)

    def fold_breakdown_table(self) -> str:
        """Render a clean Markdown table with detailed fold-by-fold boundaries and metrics."""
        lines = [
            "| Fold | Train Range | Val Range | Train (UP/DN) | Val (UP/DN) | Maj Acc | Unif Acc | Strat Acc | XGB Acc | LGB Acc |",
            "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]
        eval_by_fold: Dict[int, Dict[str, float]] = {}
        for ev in self.fold_evaluations:
            if ev.fold not in eval_by_fold:
                eval_by_fold[ev.fold] = {}
            eval_by_fold[ev.fold][ev.strategy_name] = ev.metrics.accuracy

        for f in self.folds:
            t_span = f"{f.train_start_date}..{f.train_end_date}" if f.train_start_date else f"N={f.train_rows}"
            v_span = f"{f.val_start_date}..{f.val_end_date}" if f.val_start_date else f"N={f.val_rows}"
            t_bal = f"{f.train_up_count}/{f.train_down_count}"
            v_bal = f"{f.val_up_count}/{f.val_down_count}"

            m = eval_by_fold.get(f.fold, {})
            maj = f"{m.get('Baseline A (Majority Class)', 0.0)*100:.1f}%"
            unif = f"{m.get('Baseline B1 (Uniform Random, p=0.5)', 0.0)*100:.1f}%"
            strat = f"{m.get('Baseline B2 (Stratified Random, p=train_prior)', 0.0)*100:.1f}%"
            xgb = f"{m.get('Model C (Day 17 XGBoost)', 0.0)*100:.1f}%"
            lgb = f"{m.get('Model D (Day 19 LightGBM)', 0.0)*100:.1f}%"

            lines.append(
                f"| {f.fold} | {t_span} | {v_span} | {t_bal} | {v_bal} | {maj} | {unif} | {strat} | {xgb} | {lgb} |"
            )
        return "\n".join(lines)


def _aggregate_strategy_metrics(
    strategy_name: str,
    evals: Sequence[WalkForwardFoldEvaluation],
) -> WalkForwardStrategySummary:
    """Aggregate individual fold evaluations into macro and pooled summary statistics."""
    valid_evals = [e for e in evals if e.status == "COMPLETED"]
    n_folds = len(valid_evals)

    if n_folds == 0:
        return WalkForwardStrategySummary(
            strategy_name=strategy_name,
            folds_evaluated=0,
            fold_accuracies=[],
            fold_f1s=[],
            fold_precisions=[],
            fold_recalls=[],
            mean_accuracy=0.0,
            std_accuracy=0.0,
            mean_f1=0.0,
            std_f1=0.0,
            mean_precision=0.0,
            std_precision=0.0,
            mean_recall=0.0,
            std_recall=0.0,
            pooled_confusion_matrix=[[0, 0], [0, 0]],
            pooled_accuracy=0.0,
            pooled_precision=0.0,
            pooled_recall=0.0,
            pooled_f1=0.0,
        )

    accs = [e.metrics.accuracy for e in valid_evals]
    f1s = [e.metrics.f1 for e in valid_evals]
    precs = [e.metrics.precision for e in valid_evals]
    recs = [e.metrics.recall for e in valid_evals]

    mean_acc = round(float(np.mean(accs)), 4)
    std_acc = round(float(np.std(accs, ddof=1)), 4) if n_folds > 1 else 0.0
    mean_f1 = round(float(np.mean(f1s)), 4)
    std_f1 = round(float(np.std(f1s, ddof=1)), 4) if n_folds > 1 else 0.0
    mean_prec = round(float(np.mean(precs)), 4)
    std_prec = round(float(np.std(precs, ddof=1)), 4) if n_folds > 1 else 0.0
    mean_rec = round(float(np.mean(recs)), 4)
    std_rec = round(float(np.std(recs, ddof=1)), 4) if n_folds > 1 else 0.0

    # Pooled confusion matrix
    sum_tn = sum(e.metrics.true_negatives for e in valid_evals)
    sum_fp = sum(e.metrics.false_positives for e in valid_evals)
    sum_fn = sum(e.metrics.false_negatives for e in valid_evals)
    sum_tp = sum(e.metrics.true_positives for e in valid_evals)
    total_val = sum_tn + sum_fp + sum_fn + sum_tp

    pooled_cm = [[sum_tn, sum_fp], [sum_fn, sum_tp]]
    pooled_acc = round(float((sum_tn + sum_tp) / total_val), 4) if total_val > 0 else 0.0
    pooled_prec = round(float(sum_tp / (sum_tp + sum_fp)), 4) if (sum_tp + sum_fp) > 0 else 0.0
    pooled_rec = round(float(sum_tp / (sum_tp + sum_fn)), 4) if (sum_tp + sum_fn) > 0 else 0.0
    pooled_f1 = (
        round(float(2.0 * pooled_prec * pooled_rec / (pooled_prec + pooled_rec)), 4)
        if (pooled_prec + pooled_rec) > 0
        else 0.0
    )

    return WalkForwardStrategySummary(
        strategy_name=strategy_name,
        folds_evaluated=n_folds,
        fold_accuracies=accs,
        fold_f1s=f1s,
        fold_precisions=precs,
        fold_recalls=recs,
        mean_accuracy=mean_acc,
        std_accuracy=std_acc,
        mean_f1=mean_f1,
        std_f1=std_f1,
        mean_precision=mean_prec,
        std_precision=std_prec,
        mean_recall=mean_rec,
        std_recall=std_rec,
        pooled_confusion_matrix=pooled_cm,
        pooled_accuracy=pooled_acc,
        pooled_precision=pooled_prec,
        pooled_recall=pooled_rec,
        pooled_f1=pooled_f1,
    )


def evaluate_walk_forward(
    data: Union[FeatureMatrixDataset, pd.DataFrame, Tuple[pd.DataFrame, pd.Series]],
    n_splits: int = 5,
    min_train_ratio: float = 0.4,
    embargo_sessions: int = 1,
    min_train_samples: int = 20,
    min_val_samples: int = 5,
    drop_incomplete_warmup: bool = True,
    random_seed: int = 42,
    xgboost_config: Optional[XGBoostConfig] = None,
    lightgbm_config: Optional[LightGBMConfig] = None,
) -> WalkForwardReport:
    """Execute walk-forward temporal cross-validation across all baseline & ML strategies.

    Strategies Evaluated:
    1. Baseline A: Majority-Class Classifier (fitted on fold y_train).
    2. Baseline B1: Uniform Random Classifier (p=0.5, deterministic seed=random_seed).
    3. Baseline B2: Stratified Random Classifier (p=train_prior, deterministic seed=random_seed).
    4. Model C: XGBoost Direction Classifier (Day 17 conservative baseline).
    5. Model D: LightGBM Direction Classifier (Day 19 symmetrical baseline, if available).

    Args:
        data: FeatureMatrixDataset or tabular dataset.
        n_splits: Number of expanding-window folds (default 5).
        min_train_ratio: Fraction of rows reserved for initial train partition (default 0.4).
        embargo_sessions: Purged sessions between train and validation (default 1).
        min_train_samples: Minimum required training samples per fold (default 20).
        min_val_samples: Minimum required validation samples per fold (default 5).
        drop_incomplete_warmup: Whether to exclude indicator warmup rows (default True).
        random_seed: Deterministic seed for random baselines and tree models (default 42).
        xgboost_config: Optional configuration for XGBoost.
        lightgbm_config: Optional configuration for LightGBM.

    Returns:
        WalkForwardReport with fold breakdowns, metric aggregations, and summary table.
    """
    symbol = data.symbol if isinstance(data, FeatureMatrixDataset) else "EQUITY"
    total_rows = data.total_rows if isinstance(data, FeatureMatrixDataset) else len(data)

    splits = generate_walk_forward_splits(
        data=data,
        n_splits=n_splits,
        min_train_ratio=min_train_ratio,
        embargo_sessions=embargo_sessions,
        min_train_samples=min_train_samples,
        min_val_samples=min_val_samples,
        drop_incomplete_warmup=drop_incomplete_warmup,
    )

    retained_rows = splits[0].train_rows + splits[0].embargo_rows + sum(s.val_rows for s in splits)

    all_evaluations: List[WalkForwardFoldEvaluation] = []
    strat_names = [
        "Baseline A (Majority Class)",
        "Baseline B1 (Uniform Random, p=0.5)",
        "Baseline B2 (Stratified Random, p=train_prior)",
        "Model C (Day 17 XGBoost)",
    ]
    if HAS_LIGHTGBM:
        strat_names.append("Model D (Day 19 LightGBM)")

    xgb_cfg = xgboost_config or XGBoostConfig(random_state=random_seed)
    lgb_cfg = lightgbm_config or (LightGBMConfig(random_state=random_seed) if HAS_LIGHTGBM else None)

    for s in splits:
        y_tr = s.y_train.values
        y_va = s.y_val.values
        X_tr = s.X_train
        X_va = s.X_val
        n_val = len(y_va)

        # Invariant check: Single class guard
        unique_classes = np.unique(y_tr)
        if len(unique_classes) < 2:
            logger.warning(
                "Fold %d has single-class training labels (%s); skipping model fits.",
                s.fold,
                unique_classes.tolist(),
            )
            for name in strat_names:
                dummy_m = compute_classification_metrics(y_va, np.zeros(n_val, dtype=int))
                all_evaluations.append(
                    WalkForwardFoldEvaluation(
                        fold=s.fold,
                        strategy_name=name,
                        metrics=dummy_m,
                        pred_up_count=0,
                        pred_down_count=n_val,
                        status="SKIPPED_SINGLE_CLASS",
                        skip_reason=f"Training set has single class {unique_classes.tolist()}",
                    )
                )
            continue

        # 1. Baseline A: Majority Class
        maj_clf = MajorityClassClassifier().fit(y_tr)
        maj_preds = maj_clf.predict(X_va)
        maj_m = compute_classification_metrics(y_va, maj_preds)
        all_evaluations.append(
            WalkForwardFoldEvaluation(
                fold=s.fold,
                strategy_name="Baseline A (Majority Class)",
                metrics=maj_m,
                pred_up_count=int(np.sum(maj_preds == 1)),
                pred_down_count=int(np.sum(maj_preds == 0)),
            )
        )

        # 2. Baseline B1: Uniform Random (p=0.5)
        # Use deterministic fold-specific seed derived from base random_seed to vary sequence across folds
        fold_seed = random_seed + s.fold
        unif_clf = RandomClassifier(policy="uniform", random_state=fold_seed).fit()
        unif_preds = unif_clf.predict(X_va)
        unif_m = compute_classification_metrics(y_va, unif_preds)
        all_evaluations.append(
            WalkForwardFoldEvaluation(
                fold=s.fold,
                strategy_name="Baseline B1 (Uniform Random, p=0.5)",
                metrics=unif_m,
                pred_up_count=int(np.sum(unif_preds == 1)),
                pred_down_count=int(np.sum(unif_preds == 0)),
            )
        )

        # 3. Baseline B2: Stratified Random (fitted strictly on fold y_tr)
        strat_clf = RandomClassifier(policy="stratified", random_state=fold_seed).fit(y_tr)
        strat_preds = strat_clf.predict(X_va)
        strat_m = compute_classification_metrics(y_va, strat_preds)
        all_evaluations.append(
            WalkForwardFoldEvaluation(
                fold=s.fold,
                strategy_name="Baseline B2 (Stratified Random, p=train_prior)",
                metrics=strat_m,
                pred_up_count=int(np.sum(strat_preds == 1)),
                pred_down_count=int(np.sum(strat_preds == 0)),
            )
        )

        # 4. Model C: Day 17 XGBoost
        xgb_clf = XGBoostDirectionClassifier(config=xgb_cfg)
        xgb_clf.fit(X_tr, y_tr)
        xgb_preds = xgb_clf.predict(X_va)
        xgb_m = compute_classification_metrics(y_va, xgb_preds)
        all_evaluations.append(
            WalkForwardFoldEvaluation(
                fold=s.fold,
                strategy_name="Model C (Day 17 XGBoost)",
                metrics=xgb_m,
                pred_up_count=int(np.sum(xgb_preds == 1)),
                pred_down_count=int(np.sum(xgb_preds == 0)),
            )
        )

        # 5. Model D: Day 19 LightGBM
        if HAS_LIGHTGBM and lgb_cfg is not None:
            lgb_clf = LightGBMDirectionClassifier(config=lgb_cfg)
            lgb_clf.fit(X_tr, y_tr)
            lgb_preds = lgb_clf.predict(X_va)
            lgb_m = compute_classification_metrics(y_va, lgb_preds)
            all_evaluations.append(
                WalkForwardFoldEvaluation(
                    fold=s.fold,
                    strategy_name="Model D (Day 19 LightGBM)",
                    metrics=lgb_m,
                    pred_up_count=int(np.sum(lgb_preds == 1)),
                    pred_down_count=int(np.sum(lgb_preds == 0)),
                )
            )

    # Aggregate summaries per strategy
    summaries: Dict[str, WalkForwardStrategySummary] = {}
    for name in strat_names:
        strat_evals = [e for e in all_evaluations if e.strategy_name == name]
        summaries[name] = _aggregate_strategy_metrics(name, strat_evals)

    # Determine best strategies
    best_acc = max(summaries.values(), key=lambda s: s.mean_accuracy) if summaries else None
    best_f1 = max(summaries.values(), key=lambda s: s.mean_f1) if summaries else None

    return WalkForwardReport(
        symbol=symbol,
        total_dataset_rows=total_rows,
        retained_rows=retained_rows,
        n_splits=n_splits,
        embargo_sessions=embargo_sessions,
        folds=splits,
        fold_evaluations=all_evaluations,
        strategy_summaries=summaries,
        best_strategy_by_mean_accuracy=best_acc.strategy_name if best_acc else "None",
        best_strategy_by_mean_f1=best_f1.strategy_name if best_f1 else "None",
    )
