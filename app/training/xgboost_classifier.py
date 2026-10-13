"""XGBoost Direction Classifier Baseline Module.

Implements the first reproducible XGBoost binary classifier predicting next-session
market direction (UP=1, DOWN=0) using technical features assembled from Day 15 targets
and Day 16 feature matrix.

Architectural Design & Invariants:
1. Binary Objective & Configuration:
   - Uses native `binary:logistic` objective with fixed random seed (default 42).
   - Conservative, explicit baseline hyperparameters (max_depth=3, learning_rate=0.05,
     n_estimators=50, subsample=0.8, colsample_bytree=0.8).
   - Deterministic execution with single thread (nthread=1).
2. Model Input (X) and Target (y) Isolation:
   - Enforces canonical feature column schema and ordering (`FEATURE_COLUMNS`).
   - Rejects target-derived or future outcome columns via `validate_feature_matrix_isolation`.
3. Temporal Evaluation Safety & Embargo:
   - Strict chronological holdout partitioning (no random shuffle).
   - Purges/embargos boundary session so training label outcome timestamps
     (`next_timestamp`) never touch or overlap with holdout session timestamps.
   - Preprocessing and model fitting strictly isolated to training partition.
4. Input Validation & Fault Tolerance:
   - Rejects empty, too-small, or single-class datasets with clear ValueError.
   - Rejects missing values in baseline training unless explicitly configured.
   - Graceful ImportError if optional xgboost package is not installed.
5. Research Baseline Disclaimer:
   - This module provides a research baseline, not production trading predictions.
   - Uncalibrated probabilities; does not claim financial edge or calibrated odds.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURE_PATTERNS,
    FeatureMatrixDataset,
    validate_feature_matrix_isolation,
)

logger = get_logger(__name__)

# Check for xgboost availability
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    xgb = None
    HAS_XGBOOST = False


@dataclass(frozen=True)
class XGBoostConfig:
    """Configuration container for baseline XGBoost direction classifier."""

    objective: str = "binary:logistic"
    eval_metric: str = "logloss"
    max_depth: int = 3
    learning_rate: float = 0.05
    n_estimators: int = 50
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_weight: float = 1.0
    gamma: float = 0.0
    random_state: int = 42
    n_jobs: int = 1
    allow_missing: bool = False

    def to_params_dict(self) -> Dict[str, Any]:
        """Convert configuration to parameter dictionary for xgb.train."""
        return {
            "objective": self.objective,
            "eval_metric": self.eval_metric,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "min_child_weight": self.min_child_weight,
            "gamma": self.gamma,
            "seed": self.random_state,
            "nthread": self.n_jobs,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to a dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class ClassificationMetrics:
    """Evaluation metrics for binary classification.
    
    Convention:
        Positive class = 1 (UP)
        Negative class = 0 (DOWN)
    """

    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: List[List[int]]  # [[TN, FP], [FN, TP]]
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    total_samples: int
    positive_samples: int
    negative_samples: int
    positive_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics to a dictionary."""
        return asdict(self)


def compute_classification_metrics(
    y_true: Union[np.ndarray, pd.Series, Sequence[int]],
    y_pred: Union[np.ndarray, pd.Series, Sequence[int]],
) -> ClassificationMetrics:
    """Compute binary classification metrics with zero-division safety.

    Args:
        y_true: Ground truth binary labels (0 or 1).
        y_pred: Predicted binary labels (0 or 1).

    Returns:
        ClassificationMetrics container.

    Raises:
        ValueError: If array lengths do not match or arrays are empty.
    """
    yt = np.asarray(y_true, dtype=int).ravel()
    yp = np.asarray(y_pred, dtype=int).ravel()

    if len(yt) != len(yp):
        raise ValueError(f"Length mismatch: len(y_true)={len(yt)} != len(y_pred)={len(yp)}")
    if len(yt) == 0:
        raise ValueError("Cannot compute metrics on empty arrays.")

    tp = int(np.sum((yt == 1) & (yp == 1)))
    tn = int(np.sum((yt == 0) & (yp == 0)))
    fp = int(np.sum((yt == 0) & (yp == 1)))
    fn = int(np.sum((yt == 1) & (yp == 0)))

    total = len(yt)
    accuracy = float((tp + tn) / total)
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    pos_samples = int(np.sum(yt == 1))
    neg_samples = int(np.sum(yt == 0))
    pos_rate = float(pos_samples / total)

    return ClassificationMetrics(
        accuracy=round(accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        confusion_matrix=[[tn, fp], [fn, tp]],
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn,
        total_samples=total,
        positive_samples=pos_samples,
        negative_samples=neg_samples,
        positive_rate=round(pos_rate, 4),
    )


@dataclass
class ChronologicalSplitResult:
    """Artifacts from chronological holdout split with temporal embargo."""

    X_train: pd.DataFrame
    y_train: pd.Series
    X_test: pd.DataFrame
    y_test: pd.Series
    train_indices: List[int]
    test_indices: List[int]
    embargo_indices: List[int]
    train_start_date: Optional[str]
    train_end_date: Optional[str]
    holdout_start_date: Optional[str]
    holdout_end_date: Optional[str]
    train_outcome_cutoff: Optional[str]
    total_rows: int
    train_rows: int
    test_rows: int
    embargo_rows: int
    metadata_train: Optional[pd.DataFrame] = None
    metadata_test: Optional[pd.DataFrame] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize split information to dictionary."""
        return {
            "total_rows": self.total_rows,
            "train_rows": self.train_rows,
            "test_rows": self.test_rows,
            "embargo_rows": self.embargo_rows,
            "train_start_date": self.train_start_date,
            "train_end_date": self.train_end_date,
            "holdout_start_date": self.holdout_start_date,
            "holdout_end_date": self.holdout_end_date,
            "train_outcome_cutoff": self.train_outcome_cutoff,
        }


def split_chronological_holdout(
    data: Union[FeatureMatrixDataset, pd.DataFrame, Tuple[pd.DataFrame, pd.Series]],
    test_ratio: float = 0.2,
    embargo_sessions: int = 1,
    min_train_samples: int = 20,
    min_test_samples: int = 5,
    drop_incomplete_warmup: bool = True,
) -> ChronologicalSplitResult:
    """Partition dataset into chronological train and holdout sets with outcome embargo.

    To eliminate temporal label leakage:
    Each training row t has an outcome date t+1. The training cutoff is enforced
    such that every training row's outcome date is strictly earlier than the first
    session in the holdout partition. An embargo gap of `embargo_sessions` rows
    (default 1) is purged between the training partition and holdout partition.

    Args:
        data: FeatureMatrixDataset, combined DataFrame, or (X, y) tuple.
        test_ratio: Fraction of rows reserved for holdout evaluation (default 0.2).
        embargo_sessions: Number of boundary sessions purged between train and test (default 1).
        min_train_samples: Minimum required training samples (default 20).
        min_test_samples: Minimum required holdout samples (default 5).
        drop_incomplete_warmup: Whether to filter incomplete indicator warmup rows (default True).

    Returns:
        ChronologicalSplitResult with train, holdout, and audit metadata.

    Raises:
        ValueError: If inputs violate size requirements, chronological integrity,
                    or contain invalid configurations.
    """
    if test_ratio <= 0.0 or test_ratio >= 1.0:
        raise ValueError(f"test_ratio must be between 0.0 and 1.0 (exclusive), got {test_ratio}")
    if embargo_sessions < 0:
        raise ValueError(f"embargo_sessions must be non-negative, got {embargo_sessions}")

    # Extract aligned DataFrame with metadata, features, and target
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
        raise ValueError(f"Unsupported data type for splitting: {type(data)}")

    n_samples = len(sub_df)
    min_required = min_train_samples + min_test_samples + embargo_sessions
    if n_samples < min_required:
        raise ValueError(
            f"Dataset too small for chronological holdout split: "
            f"has {n_samples} rows, requires at least {min_required} "
            f"(min_train={min_train_samples}, min_test={min_test_samples}, embargo={embargo_sessions})."
        )

    # Compute partition sizes
    test_size = max(min_test_samples, int(np.round(n_samples * test_ratio)))
    if n_samples - test_size - embargo_sessions < min_train_samples:
        test_size = n_samples - min_train_samples - embargo_sessions

    train_end_idx = n_samples - test_size - embargo_sessions
    holdout_start_idx = n_samples - test_size

    train_df = sub_df.iloc[:train_end_idx].copy()
    embargo_df = sub_df.iloc[train_end_idx:holdout_start_idx].copy()
    test_df = sub_df.iloc[holdout_start_idx:].copy()

    # Extract dates if available in metadata
    train_start_date: Optional[str] = None
    train_end_date: Optional[str] = None
    holdout_start_date: Optional[str] = None
    holdout_end_date: Optional[str] = None
    train_outcome_cutoff: Optional[str] = None

    if "timestamp" in sub_df.columns:
        train_start_date = str(train_df["timestamp"].iloc[0])[:10]
        train_end_date = str(train_df["timestamp"].iloc[-1])[:10]
        holdout_start_date = str(test_df["timestamp"].iloc[0])[:10]
        holdout_end_date = str(test_df["timestamp"].iloc[-1])[:10]

    if "next_timestamp" in sub_df.columns:
        train_outcome_cutoff = str(train_df["next_timestamp"].iloc[-1])[:10]
        # Invariant check: training outcome cutoff must be <= holdout start date
        if holdout_start_date is not None and train_outcome_cutoff > holdout_start_date:
            raise ValueError(
                f"Temporal leakage detected: train_outcome_cutoff ({train_outcome_cutoff}) "
                f"exceeds holdout_start_date ({holdout_start_date})."
            )

    # Separate X and y
    feature_cols = [c for c in FEATURE_COLUMNS if c in sub_df.columns]
    if not feature_cols:
        # Fallback to all non-metadata and non-target columns
        ignore_cols = set(
            ["symbol", "timestamp", "next_timestamp", "current_close", "next_close"]
            + ["target_return", "target_direction", "target_binary"]
        )
        feature_cols = [c for c in sub_df.columns if c not in ignore_cols]

    X_train = train_df[feature_cols].copy()
    y_train = train_df["target_binary"].astype(int).copy()
    X_test = test_df[feature_cols].copy()
    y_test = test_df["target_binary"].astype(int).copy()

    # Enforce isolation guard
    validate_feature_matrix_isolation(X_train)
    meta_cols = [c for c in ["symbol", "timestamp", "next_timestamp", "current_close", "next_close", "target_direction"] if c in sub_df.columns]
    metadata_train = train_df[meta_cols].copy() if meta_cols else None
    metadata_test = test_df[meta_cols].copy() if meta_cols else None

    return ChronologicalSplitResult(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        train_indices=list(range(train_end_idx)),
        test_indices=list(range(holdout_start_idx, n_samples)),
        embargo_indices=list(range(train_end_idx, holdout_start_idx)),
        train_start_date=train_start_date,
        train_end_date=train_end_date,
        holdout_start_date=holdout_start_date,
        holdout_end_date=holdout_end_date,
        train_outcome_cutoff=train_outcome_cutoff,
        total_rows=n_samples,
        train_rows=len(X_train),
        test_rows=len(X_test),
        embargo_rows=len(embargo_df),
        metadata_train=metadata_train,
        metadata_test=metadata_test,
    )


class XGBoostDirectionClassifier:
    """Reproducible XGBoost binary classifier predicting market direction.

    Uses native `xgb.train()` and `xgb.DMatrix()` to eliminate external sklearn
    dependencies while maintaining strict schema, seed determinism, and serializability.
    """

    def __init__(self, config: Optional[XGBoostConfig] = None) -> None:
        """Initialize classifier with explicit configuration.

        Args:
            config: Baseline configuration dataclass (defaults to standard baseline).
        """
        self.config = config or XGBoostConfig()
        self.booster: Optional[Any] = None
        self.feature_names: List[str] = []
        self.is_fitted: bool = False

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray, Sequence[int]],
        feature_names: Optional[Sequence[str]] = None,
    ) -> "XGBoostDirectionClassifier":
        """Fit XGBoost binary classifier on training features and labels.

        Args:
            X: 2D feature matrix (DataFrame or numpy array).
            y: 1D target labels (0 or 1).
            feature_names: Optional custom feature column names.

        Returns:
            Fitted classifier instance.

        Raises:
            ImportError: If xgboost package is not installed.
            ValueError: If input violates schema, contains NaNs, is empty,
                        or contains only a single class.
        """
        if not HAS_XGBOOST:
            raise ImportError(
                "xgboost is not installed. Install with: pip install 'xgboost>=2.0.0'"
            )

        # Validate X and leakage guards
        if isinstance(X, pd.DataFrame):
            validate_feature_matrix_isolation(X)
            # Reorder columns to canonical order if columns match FEATURE_COLUMNS
            if set(FEATURE_COLUMNS).issubset(set(X.columns)):
                X_clean = X[FEATURE_COLUMNS].copy()
                names = list(FEATURE_COLUMNS)
            else:
                X_clean = X.copy()
                names = list(X.columns)
            X_arr = X_clean.to_numpy(dtype=float)
        else:
            X_arr = np.asarray(X, dtype=float)
            names = list(feature_names) if feature_names is not None else [f"f{i}" for i in range(X_arr.shape[1])]

        y_arr = np.asarray(y, dtype=int).ravel()

        if len(X_arr) == 0:
            raise ValueError("Cannot fit model on empty feature dataset.")
        if len(X_arr) != len(y_arr):
            raise ValueError(f"Sample count mismatch: X has {len(X_arr)} rows, y has {len(y_arr)} rows.")

        if len(X_arr) < 10:
            raise ValueError(f"Dataset too small to fit classifier: has {len(X_arr)} rows, requires at least 10.")

        # Check single-class invariant
        unique_classes = np.unique(y_arr)
        if len(unique_classes) < 2:
            raise ValueError(
                f"Dataset contains only one target class ({unique_classes.tolist()}). "
                f"Binary direction classification requires both classes (UP=1, DOWN=0)."
            )

        # Check missing values policy
        if not self.config.allow_missing:
            if np.isnan(X_arr).any():
                raise ValueError(
                    "Feature matrix X contains missing (NaN) values. Baseline model requires "
                    "complete labeled rows. Set allow_missing=True or drop incomplete warm-up rows."
                )
            if np.isnan(y_arr).any():
                raise ValueError("Target array y contains missing (NaN) values.")

        params = self.config.to_params_dict()
        dtrain = xgb.DMatrix(X_arr, label=y_arr, feature_names=names)

        logger.info(
            "Fitting XGBoost direction classifier: %d samples, %d features, seed=%d",
            len(X_arr),
            len(names),
            self.config.random_state,
        )

        self.booster = xgb.train(
            params=params,
            dtrain=dtrain,
            num_boost_round=self.config.n_estimators,
        )
        self.feature_names = names
        self.is_fitted = True
        return self

    def _prepare_dmatrix(self, X: Union[pd.DataFrame, np.ndarray]) -> Any:
        """Helper to create DMatrix with aligned feature names."""
        if not self.is_fitted or self.booster is None:
            raise ValueError("Classifier is not fitted yet. Call fit() before predicting.")

        if isinstance(X, pd.DataFrame):
            validate_feature_matrix_isolation(X)
            # Reorder to match fitted feature names
            if all(name in X.columns for name in self.feature_names):
                X_eval = X[self.feature_names].to_numpy(dtype=float)
            else:
                X_eval = X.to_numpy(dtype=float)
        else:
            X_eval = np.asarray(X, dtype=float)

        if not self.config.allow_missing and np.isnan(X_eval).any():
            raise ValueError("Evaluation features contain NaN values. Baseline requires complete rows.")

        return xgb.DMatrix(X_eval, feature_names=self.feature_names)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Compute predicted class probabilities for input features.

        Args:
            X: Input feature matrix.

        Returns:
            2D numpy array of shape (N, 2) where column 0 is P(DOWN) and column 1 is P(UP).
        """
        dmat = self._prepare_dmatrix(X)
        p1 = self.booster.predict(dmat)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        threshold: float = 0.5,
    ) -> np.ndarray:
        """Predict binary direction label (1 for UP, 0 for DOWN).

        Args:
            X: Input feature matrix.
            threshold: Probability threshold for positive class (default 0.5).

        Returns:
            1D numpy array of binary integers (0 or 1).
        """
        proba = self.predict_proba(X)[:, 1]
        return (proba > threshold).astype(int)

    def save_model(self, filepath: Union[str, Path]) -> None:
        """Persist fitted booster to native XGBoost JSON format.

        Args:
            filepath: Destination file path (e.g. 'models/xgboost_baseline.json').
        """
        if not self.is_fitted or self.booster is None:
            raise ValueError("Cannot save unfitted model.")
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.booster.save_model(str(path))
        logger.info("Persisted XGBoost model artifact to %s", path)

    @classmethod
    def load_model(
        cls,
        filepath: Union[str, Path],
        config: Optional[XGBoostConfig] = None,
    ) -> "XGBoostDirectionClassifier":
        """Load persisted model from native XGBoost format.

        Args:
            filepath: Source file path.
            config: Optional configuration dataclass.

        Returns:
            Fitted XGBoostDirectionClassifier instance.
        """
        if not HAS_XGBOOST:
            raise ImportError(
                "xgboost is not installed. Install with: pip install 'xgboost>=2.0.0'"
            )
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"Model file not found: {path}")

        booster = xgb.Booster()
        booster.load_model(str(path))
        feature_names = booster.feature_names or []

        clf = cls(config=config)
        clf.booster = booster
        clf.feature_names = feature_names
        clf.is_fitted = True
        return clf


@dataclass
class DirectionTrainingResult:
    """Container for complete training execution results."""

    model: XGBoostDirectionClassifier
    config: XGBoostConfig
    split: ChronologicalSplitResult
    train_metrics: ClassificationMetrics
    holdout_metrics: ClassificationMetrics
    feature_names: List[str]
    audit: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize training results to dictionary."""
        return {
            "config": self.config.to_dict(),
            "split": self.split.to_dict(),
            "train_metrics": self.train_metrics.to_dict(),
            "holdout_metrics": self.holdout_metrics.to_dict(),
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
            "audit": self.audit,
        }


def train_baseline_classifier(
    X_train: Union[pd.DataFrame, np.ndarray],
    y_train: Union[pd.Series, np.ndarray],
    config: Optional[XGBoostConfig] = None,
    feature_names: Optional[Sequence[str]] = None,
) -> XGBoostDirectionClassifier:
    """Functional helper to fit baseline direction classifier on training partition.

    Args:
        X_train: Training features.
        y_train: Training binary labels.
        config: Model configuration (defaults to standard baseline).
        feature_names: Optional column names.

    Returns:
        Fitted XGBoostDirectionClassifier.
    """
    model = XGBoostDirectionClassifier(config=config)
    return model.fit(X=X_train, y=y_train, feature_names=feature_names)


def run_training_pipeline(
    dataset: FeatureMatrixDataset,
    config: Optional[XGBoostConfig] = None,
    test_ratio: float = 0.2,
    embargo_sessions: int = 1,
) -> DirectionTrainingResult:
    """Orchestrate end-to-end dataset validation, temporal split, and model fitting.

    Args:
        dataset: FeatureMatrixDataset produced by Day 16 assembly pipeline.
        config: Baseline model configuration.
        test_ratio: Chronological holdout fraction (default 0.2).
        embargo_sessions: Sessions purged to prevent label outcome leakage (default 1).

    Returns:
        DirectionTrainingResult containing fitted model, metrics, and temporal audit.
    """
    active_config = config or XGBoostConfig()

    # Step 1: Chronological holdout split with outcome embargo
    split_res = split_chronological_holdout(
        data=dataset,
        test_ratio=test_ratio,
        embargo_sessions=embargo_sessions,
        drop_incomplete_warmup=True,
    )

    # Step 2: Fit model strictly on training data
    model = XGBoostDirectionClassifier(config=active_config)
    model.fit(X=split_res.X_train, y=split_res.y_train)

    # Step 3: Compute evaluation metrics
    train_preds = model.predict(split_res.X_train)
    train_metrics = compute_classification_metrics(split_res.y_train, train_preds)

    holdout_preds = model.predict(split_res.X_test)
    holdout_metrics = compute_classification_metrics(split_res.y_test, holdout_preds)

    audit = {
        "symbol": dataset.symbol,
        "initial_total_rows": dataset.total_rows,
        "labeled_rows": dataset.labeled_rows,
        "unlabeled_rows": dataset.unlabeled_rows,
        "retained_complete_rows": split_res.total_rows,
        "train_rows": split_res.train_rows,
        "test_rows": split_res.test_rows,
        "embargo_rows": split_res.embargo_rows,
    }

    return DirectionTrainingResult(
        model=model,
        config=active_config,
        split=split_res,
        train_metrics=train_metrics,
        holdout_metrics=holdout_metrics,
        feature_names=model.feature_names,
        audit=audit,
    )
