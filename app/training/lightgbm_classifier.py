"""LightGBM Direction Classifier Baseline Module.

Implements the second reproducible gradient-boosted decision tree binary classifier
predicting next-session market direction (UP=1, DOWN=0) using technical features assembled
from Day 15 targets and Day 16 feature matrix.

Architectural Design & Invariants:
1. Binary Objective & Configuration:
   - Uses native `binary` objective with fixed random seed (default 42).
   - Equivalent baseline hyperparameters to XGBoost (max_depth=3, num_leaves=7,
     learning_rate=0.05, n_estimators=50, subsample/bagging_fraction=0.8,
     colsample_bytree/feature_fraction=0.8).
   - Deterministic execution with single thread (num_threads=1, deterministic=True).
2. Model Input (X) and Target (y) Isolation:
   - Enforces canonical feature column schema and ordering (`FEATURE_COLUMNS`).
   - Rejects target-derived or future outcome columns via `validate_feature_matrix_isolation`.
3. Temporal Evaluation Safety & Embargo:
   - Evaluated on identical chronological holdout partitioning as XGBoost and baselines.
   - Preprocessing and model fitting strictly isolated to training partition.
4. Input Validation & Fault Tolerance:
   - Rejects empty, too-small, or single-class datasets with clear ValueError.
   - Rejects missing values in baseline training unless explicitly configured.
   - Graceful ImportError if lightgbm package is not installed.
5. Research Baseline Disclaimer:
   - This module provides a research baseline, not production trading predictions.
   - Uncalibrated probabilities; does not claim financial edge or calibrated odds.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    validate_feature_matrix_isolation,
)
from app.training.xgboost_classifier import (
    ClassificationMetrics,
    compute_classification_metrics,
)

logger = get_logger(__name__)

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    lgb = None
    HAS_LIGHTGBM = False


@dataclass(frozen=True)
class LightGBMConfig:
    """Configuration container for baseline LightGBM direction classifier."""

    objective: str = "binary"
    metric: str = "binary_logloss"
    max_depth: int = 3
    num_leaves: int = 7
    learning_rate: float = 0.05
    n_estimators: int = 50
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_samples: int = 20
    random_state: int = 42
    n_jobs: int = 1
    verbose: int = -1
    allow_missing: bool = False

    def to_params_dict(self) -> Dict[str, Any]:
        """Convert configuration to parameter dictionary for lgb.train."""
        return {
            "objective": self.objective,
            "metric": self.metric,
            "max_depth": self.max_depth,
            "num_leaves": self.num_leaves,
            "learning_rate": self.learning_rate,
            "bagging_fraction": self.subsample,
            "bagging_freq": 1 if self.subsample < 1.0 else 0,
            "feature_fraction": self.colsample_bytree,
            "min_child_samples": self.min_child_samples,
            "seed": self.random_state,
            "num_threads": self.n_jobs,
            "verbose": self.verbose,
            "deterministic": True,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to a dictionary."""
        return asdict(self)


class LightGBMDirectionClassifier:
    """Reproducible LightGBM binary classifier predicting market direction.

    Uses native `lgb.train()` and `lgb.Dataset()` without requiring external scikit-learn
    dependencies while maintaining strict schema, seed determinism, and serializability.
    """

    def __init__(self, config: Optional[LightGBMConfig] = None) -> None:
        """Initialize classifier with explicit configuration.

        Args:
            config: Baseline configuration dataclass (defaults to standard baseline).
        """
        self.config = config or LightGBMConfig()
        self.booster: Optional[Any] = None
        self.feature_names: List[str] = []
        self.is_fitted: bool = False

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray, Sequence[int]],
        feature_names: Optional[Sequence[str]] = None,
    ) -> "LightGBMDirectionClassifier":
        """Fit LightGBM binary classifier on training features and labels.

        Args:
            X: 2D feature matrix (DataFrame or numpy array).
            y: 1D target labels (0 or 1).
            feature_names: Optional custom feature column names.

        Returns:
            Fitted classifier instance.

        Raises:
            ImportError: If lightgbm package is not installed.
            ValueError: If input violates schema, contains NaNs, is empty,
                        or contains only a single class.
        """
        if not HAS_LIGHTGBM:
            raise ImportError(
                "lightgbm is not installed. Install with: pip install 'lightgbm>=4.0.0'"
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
        dtrain = lgb.Dataset(X_arr, label=y_arr, feature_name=names, free_raw_data=False)

        logger.info(
            "Fitting LightGBM direction classifier: %d samples, %d features, seed=%d",
            len(X_arr),
            len(names),
            self.config.random_state,
        )

        self.booster = lgb.train(
            params=params,
            train_set=dtrain,
            num_boost_round=self.config.n_estimators,
        )
        self.feature_names = names
        self.is_fitted = True
        return self

    def _prepare_input_matrix(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Validate and format input matrix for inference."""
        if not self.is_fitted or self.booster is None:
            raise ValueError("Model is not fitted. Call fit() before predict().")

        if isinstance(X, pd.DataFrame):
            validate_feature_matrix_isolation(X)
            if set(self.feature_names).issubset(set(X.columns)):
                X_clean = X[self.feature_names].copy()
            else:
                X_clean = X.copy()
            X_arr = X_clean.to_numpy(dtype=float)
        else:
            X_arr = np.asarray(X, dtype=float)

        if len(X_arr) == 0:
            raise ValueError("Cannot predict on empty feature dataset.")

        if X_arr.shape[1] != len(self.feature_names):
            raise ValueError(
                f"Feature dimension mismatch: expected {len(self.feature_names)} features, "
                f"got {X_arr.shape[1]}."
            )

        if not self.config.allow_missing and np.isnan(X_arr).any():
            raise ValueError("Feature matrix contains NaN values. Prediction requires complete features.")

        return X_arr

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Predict class probabilities for input features.

        Args:
            X: 2D feature matrix.

        Returns:
            2D numpy array of shape (N, 2) where col 0 is P(DOWN) and col 1 is P(UP).
        """
        X_arr = self._prepare_input_matrix(X)
        p_up = self.booster.predict(X_arr)
        p_down = 1.0 - p_up
        return np.column_stack([p_down, p_up])

    def predict(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        threshold: float = 0.5,
    ) -> np.ndarray:
        """Predict binary directional classes (0=DOWN, 1=UP).

        Args:
            X: 2D feature matrix.
            threshold: Probability threshold for positive class (default 0.5).

        Returns:
            1D numpy array of binary predictions in {0, 1}.
        """
        probs = self.predict_proba(X)
        p_up = probs[:, 1]
        return (p_up > threshold).astype(int)

    def evaluate(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray, Sequence[int]],
        threshold: float = 0.5,
    ) -> ClassificationMetrics:
        """Evaluate model predictions against true labels using canonical metrics.

        Args:
            X: 2D feature matrix.
            y: 1D true binary labels.
            threshold: Probability cutoff for positive class.

        Returns:
            ClassificationMetrics container.
        """
        y_pred = self.predict(X, threshold=threshold)
        return compute_classification_metrics(y_true=y, y_pred=y_pred)

    @property
    def feature_importances_(self) -> Dict[str, float]:
        """Return feature importance scores (split count) mapped to feature names."""
        if not self.is_fitted or self.booster is None:
            raise ValueError("Model is not fitted. Cannot extract feature importances.")
        importances = self.booster.feature_importance(importance_type="split")
        return {name: float(score) for name, score in zip(self.feature_names, importances)}

    def save_model(self, model_path: Union[str, Path]) -> None:
        """Serialize booster model to file."""
        if not self.is_fitted or self.booster is None:
            raise ValueError("Cannot save unfitted model.")
        p = Path(model_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.booster.save_model(str(p))
        logger.info("Saved LightGBM model to %s", p)

    def load_model(self, model_path: Union[str, Path]) -> "LightGBMDirectionClassifier":
        """Load booster model from file."""
        if not HAS_LIGHTGBM:
            raise ImportError("lightgbm is not installed.")
        p = Path(model_path)
        if not p.is_file():
            raise FileNotFoundError(f"Model file not found: {p}")
        self.booster = lgb.Booster(model_file=str(p))
        self.feature_names = self.booster.feature_name()
        self.is_fitted = True
        logger.info("Loaded LightGBM model from %s", p)
        return self
