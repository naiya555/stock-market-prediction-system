"""Baseline Direction Classifiers & Comparative Evaluation Layer.

Implements standard benchmark strategies to evaluate whether trained machine learning
models (such as the Day 17 XGBoost direction classifier) genuinely outperform simple
non-parametric baselines on financial time series:

Strategies:
1. Baseline A — Majority-Class Classifier:
   - Predicts the most frequent directional class in the training partition for all test samples.
   - Deterministic tie-breaking policy (defaults to positive class 1/UP).
   - Strict zero-leakage guarantee: never inspects holdout labels to select predicted class.
2. Baseline B — Fixed-Seed Random Classifier:
   - Predicts direction pseudo-randomly using a fixed seed (default 42).
   - Explicit probability policies:
     * 'uniform': P(UP) = 0.5, P(DOWN) = 0.5.
     * 'stratified': P(UP) = empirical training prior, P(DOWN) = 1 - empirical training prior.
   - Completely reproducible and deterministic across repeated executions.
3. Model C — Existing Day 17 XGBoost Classifier:
   - Evaluates the unchanged baseline XGBoost model without hyperparameter tuning.

Evaluation Protocol:
- All strategies evaluated on identical chronological holdout observations.
- Uses identical metric definitions (Accuracy, Precision, Recall, F1, Confusion Matrix).
- Strict temporal isolation: zero future price or holdout outcome leakage.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from app.training.feature_matrix import FeatureMatrixDataset
from app.training.xgboost_classifier import (
    ChronologicalSplitResult,
    ClassificationMetrics,
    XGBoostConfig,
    XGBoostDirectionClassifier,
    compute_classification_metrics,
    split_chronological_holdout,
)

logger = get_logger(__name__)


def _resolve_n_samples(X: Union[pd.DataFrame, np.ndarray, int, Sequence[Any]]) -> int:
    """Validate and resolve positive sample count from input container or count integer."""
    if isinstance(X, bool):
        raise TypeError(f"Invalid input: boolean value {X} cannot be used as sample count.")
    if isinstance(X, int):
        n_samples = X
    elif hasattr(X, "__len__"):
        n_samples = len(X)
    else:
        raise TypeError(f"Expected integer sample count or Sized collection, got {type(X).__name__}.")

    if n_samples <= 0:
        raise ValueError(f"Number of samples must be positive, got {n_samples}.")
    return n_samples


class MajorityClassClassifier:
    """Predicts the most frequent class observed in the training labels.

    Strictly uses training labels to determine majority direction.
    Deterministic tie handling: if class frequencies are equal, predicts tie_break_class.
    """

    def __init__(self, tie_break_class: int = 1) -> None:
        """Initialize majority class classifier.

        Args:
            tie_break_class: Direction label to choose if classes are equally frequent (default 1 / UP).
        """
        if tie_break_class not in (0, 1):
            raise ValueError(f"tie_break_class must be 0 or 1, got {tie_break_class}")
        self.tie_break_class = tie_break_class
        self.majority_class_: Optional[int] = None
        self.class_counts_: Dict[int, int] = {}
        self.is_fitted: bool = False

    def fit(
        self,
        y: Union[np.ndarray, pd.Series, Sequence[int]],
        X: Optional[Union[pd.DataFrame, np.ndarray]] = None,
    ) -> "MajorityClassClassifier":
        """Determine majority class from training labels.

        Args:
            y: Training binary labels (0 or 1).
            X: Unused feature matrix (present for standard API compatibility).

        Returns:
            Fitted classifier instance.

        Raises:
            ValueError: If y is empty or contains non-binary values.
        """
        y_arr = np.asarray(y, dtype=int).ravel()
        if len(y_arr) == 0:
            raise ValueError("Cannot fit MajorityClassClassifier on empty labels.")

        n_zero = int(np.sum(y_arr == 0))
        n_one = int(np.sum(y_arr == 1))
        if n_zero + n_one != len(y_arr):
            raise ValueError("Labels must be strictly binary integers in {0, 1}.")

        self.class_counts_ = {0: n_zero, 1: n_one}

        if n_one > n_zero:
            self.majority_class_ = 1
        elif n_zero > n_one:
            self.majority_class_ = 0
        else:
            self.majority_class_ = self.tie_break_class

        self.is_fitted = True
        logger.info(
            "Fitted MajorityClassClassifier: counts=%s, majority=%d (tie_breaker=%d)",
            self.class_counts_,
            self.majority_class_,
            self.tie_break_class,
        )
        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray, int, Sequence[Any]]) -> np.ndarray:
        """Predict majority class for each sample.

        Args:
            X: Feature matrix, length integer, or sequence to determine output length.

        Returns:
            1D numpy array filled with the fitted majority class.
        """
        if not self.is_fitted or self.majority_class_ is None:
            raise ValueError("Classifier is not fitted. Call fit() before predict().")

        n_samples = _resolve_n_samples(X)
        return np.full(n_samples, self.majority_class_, dtype=int)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray, int, Sequence[Any]]) -> np.ndarray:
        """Return deterministic probability estimates.

        Assigns probability 1.0 to the majority class and 0.0 to the minority class.
        """
        if not self.is_fitted or self.majority_class_ is None:
            raise ValueError("Classifier is not fitted. Call fit() before predict_proba().")

        n_samples = _resolve_n_samples(X)
        p1 = 1.0 if self.majority_class_ == 1 else 0.0
        p0 = 1.0 - p1
        probs = np.tile([p0, p1], (n_samples, 1))
        return probs


class RandomClassifier:
    """Predicts market direction randomly using a fixed random seed.

    Policies:
    - 'uniform': P(UP) = 0.5, P(DOWN) = 0.5
    - 'stratified': P(UP) = training prior, P(DOWN) = 1 - training prior
    - 'custom': P(UP) = custom_p, P(DOWN) = 1 - custom_p
    """

    def __init__(
        self,
        policy: str = "uniform",
        random_state: int = 42,
        custom_p: Optional[float] = None,
    ) -> None:
        """Initialize random classifier.

        Args:
            policy: 'uniform', 'stratified', or 'custom'.
            random_state: Fixed random seed for deterministic repeatability.
            custom_p: Positive class probability when policy is 'custom'.
        """
        if policy not in ("uniform", "stratified", "custom"):
            raise ValueError(f"Unknown policy '{policy}'. Must be 'uniform', 'stratified', or 'custom'.")
        if policy == "custom":
            if custom_p is None or not (0.0 <= custom_p <= 1.0):
                raise ValueError("custom_p must be a float in [0.0, 1.0] when policy is 'custom'.")

        self.policy = policy
        self.random_state = random_state
        self.custom_p = custom_p
        self.p_: Optional[float] = None
        self.is_fitted: bool = False

    def fit(
        self,
        y: Optional[Union[np.ndarray, pd.Series, Sequence[int]]] = None,
        X: Optional[Union[pd.DataFrame, np.ndarray]] = None,
    ) -> "RandomClassifier":
        """Configure class probability according to policy.

        Args:
            y: Training labels (required if policy is 'stratified').
            X: Unused feature matrix.

        Returns:
            Fitted classifier instance.
        """
        if self.policy == "uniform":
            self.p_ = 0.5
        elif self.policy == "custom":
            self.p_ = float(self.custom_p)
        elif self.policy == "stratified":
            if y is None:
                raise ValueError("Labels y are required to fit 'stratified' random classifier.")
            y_arr = np.asarray(y, dtype=int).ravel()
            if len(y_arr) == 0:
                raise ValueError("Cannot fit 'stratified' classifier on empty labels.")
            n_zero = int(np.sum(y_arr == 0))
            n_one = int(np.sum(y_arr == 1))
            if n_zero + n_one != len(y_arr):
                raise ValueError("Labels must be strictly binary integers in {0, 1}.")
            self.p_ = float(np.mean(y_arr == 1))

        self.is_fitted = True
        logger.info(
            "Fitted RandomClassifier: policy=%s, p(UP)=%.4f, seed=%d",
            self.policy,
            self.p_,
            self.random_state,
        )
        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray, int, Sequence[Any]]) -> np.ndarray:
        """Generate pseudo-random binary predictions with fixed seed.

        Args:
            X: Feature matrix, length integer, or sequence to determine output length.

        Returns:
            1D numpy array of binary integers in {0, 1}.
        """
        if not self.is_fitted or self.p_ is None:
            raise ValueError("Classifier is not fitted. Call fit() before predict().")

        n_samples = _resolve_n_samples(X)
        rng = np.random.RandomState(self.random_state)
        return rng.binomial(n=1, p=self.p_, size=n_samples).astype(int)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray, int, Sequence[Any]]) -> np.ndarray:
        """Return expected class probability distribution."""
        if not self.is_fitted or self.p_ is None:
            raise ValueError("Classifier is not fitted. Call fit() before predict_proba().")

        n_samples = _resolve_n_samples(X)
        p1 = self.p_
        p0 = 1.0 - p1
        return np.tile([p0, p1], (n_samples, 1))


@dataclass(frozen=True)
class BaselineComparisonRow:
    """Evaluation summary row for a single predictive strategy."""

    strategy_name: str
    accuracy: float
    precision_up: float
    recall_up: float
    f1_up: float
    confusion_matrix: List[List[int]]
    pred_up_count: int
    pred_down_count: int
    correct_up_count: int
    correct_down_count: int
    total_samples: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize row to dictionary."""
        return asdict(self)


@dataclass
class BaselineComparisonReport:
    """Complete comparative audit report evaluating model vs baselines."""

    symbol: str
    holdout_sessions: int
    holdout_start_date: Optional[str]
    holdout_end_date: Optional[str]
    train_sessions: int
    train_up_count: int
    train_down_count: int
    train_majority_class: int
    rows: List[BaselineComparisonRow]
    best_strategy_by_accuracy: str
    best_strategy_by_f1: str
    xgboost_beat_majority: bool
    xgboost_beat_random: bool
    up_bias_detected: bool
    lightgbm_beat_majority: Optional[bool] = None
    lightgbm_beat_random: Optional[bool] = None

    def summary_table(self) -> str:
        """Format comparison report as a GitHub-flavored Markdown table."""
        header = (
            "| Strategy | Accuracy | UP Precision | UP Recall | UP F1 | "
            "Confusion Matrix (TN,FP,FN,TP) | Pred UP/DOWN | Correct UP/DOWN |\n"
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
        )
        lines = [header]
        for r in self.rows:
            tn, fp = r.confusion_matrix[0]
            fn, tp = r.confusion_matrix[1]
            cm_str = f"[[{tn},{fp}],[{fn},{tp}]]"
            line = (
                f"| **{r.strategy_name}** | {r.accuracy*100:.2f}% | "
                f"{r.precision_up*100:.2f}% | {r.recall_up*100:.2f}% | "
                f"{r.f1_up:.4f} | `{cm_str}` | {r.pred_up_count}/{r.pred_down_count} | "
                f"{r.correct_up_count}/{r.correct_down_count} |"
            )
            lines.append(line)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete comparison report."""
        return {
            "symbol": self.symbol,
            "holdout_sessions": self.holdout_sessions,
            "holdout_start_date": self.holdout_start_date,
            "holdout_end_date": self.holdout_end_date,
            "train_sessions": self.train_sessions,
            "train_up_count": self.train_up_count,
            "train_down_count": self.train_down_count,
            "train_majority_class": self.train_majority_class,
            "best_strategy_by_accuracy": self.best_strategy_by_accuracy,
            "best_strategy_by_f1": self.best_strategy_by_f1,
            "xgboost_beat_majority": self.xgboost_beat_majority,
            "xgboost_beat_random": self.xgboost_beat_random,
            "up_bias_detected": self.up_bias_detected,
            "lightgbm_beat_majority": self.lightgbm_beat_majority,
            "lightgbm_beat_random": self.lightgbm_beat_random,
            "rows": [r.to_dict() for r in self.rows],
        }


def _build_comparison_row(
    strategy_name: str,
    y_true: Union[np.ndarray, pd.Series],
    y_pred: np.ndarray,
) -> BaselineComparisonRow:
    """Helper to construct comparison row using canonical compute_classification_metrics."""
    metrics = compute_classification_metrics(y_true, y_pred)
    pred_up = int(np.sum(y_pred == 1))
    pred_down = int(np.sum(y_pred == 0))

    return BaselineComparisonRow(
        strategy_name=strategy_name,
        accuracy=metrics.accuracy,
        precision_up=metrics.precision,
        recall_up=metrics.recall,
        f1_up=metrics.f1,
        confusion_matrix=metrics.confusion_matrix,
        pred_up_count=pred_up,
        pred_down_count=pred_down,
        correct_up_count=metrics.true_positives,
        correct_down_count=metrics.true_negatives,
        total_samples=metrics.total_samples,
    )


def evaluate_baseline_comparison(
    split: Union[ChronologicalSplitResult, FeatureMatrixDataset],
    xgboost_config: Optional[XGBoostConfig] = None,
    random_seed: int = 42,
    include_lightgbm: bool = False,
    lightgbm_config: Optional[Any] = None,
) -> BaselineComparisonReport:
    """Execute fair, leakage-safe baseline evaluation across models on identical holdout.

    Evaluates:
    1. Baseline A: Majority-Class Classifier
    2. Baseline B1: Fixed-Seed Random Classifier (Uniform, p=0.5)
    3. Baseline B2: Fixed-Seed Random Classifier (Stratified, p=training_prior)
    4. Model C: Existing Day 17 XGBoost Classifier
    5. Model D (Optional): Day 19 LightGBM Classifier (when include_lightgbm=True)

    Args:
        split: Either a ChronologicalSplitResult or FeatureMatrixDataset.
        xgboost_config: Optional config for XGBoost (defaults to Day 17 baseline).
        random_seed: Random seed for random baseline classifiers (default 42).
        include_lightgbm: Whether to include LightGBM classifier in comparison (default False).
        lightgbm_config: Optional config for LightGBM.

    Returns:
        BaselineComparisonReport with comparative metrics and empirical findings.
    """
    if isinstance(split, FeatureMatrixDataset):
        split_res = split_chronological_holdout(
            data=split,
            test_ratio=0.2,
            embargo_sessions=1,
            drop_incomplete_warmup=True,
        )
        symbol = split.symbol
    elif isinstance(split, ChronologicalSplitResult):
        split_res = split
        symbol = "EQUITY"
    else:
        raise ValueError(f"Unsupported input type for split: {type(split)}")

    y_train = split_res.y_train.values
    y_test = split_res.y_test.values
    X_train = split_res.X_train
    X_test = split_res.X_test

    # 1. Baseline A: Majority Class Classifier
    clf_majority = MajorityClassClassifier(tie_break_class=1)
    clf_majority.fit(y_train)
    preds_majority = clf_majority.predict(X_test)
    row_majority = _build_comparison_row(
        strategy_name="Baseline A (Majority Class)",
        y_true=y_test,
        y_pred=preds_majority,
    )

    # 2. Baseline B1: Uniform Random Classifier (p=0.5)
    clf_rand_uniform = RandomClassifier(policy="uniform", random_state=random_seed)
    clf_rand_uniform.fit()
    preds_rand_uniform = clf_rand_uniform.predict(X_test)
    row_rand_uniform = _build_comparison_row(
        strategy_name="Baseline B1 (Uniform Random, p=0.5)",
        y_true=y_test,
        y_pred=preds_rand_uniform,
    )

    # 3. Baseline B2: Stratified Random Classifier (p=train_prior)
    clf_rand_strat = RandomClassifier(policy="stratified", random_state=random_seed)
    clf_rand_strat.fit(y_train)
    preds_rand_strat = clf_rand_strat.predict(X_test)
    row_rand_strat = _build_comparison_row(
        strategy_name="Baseline B2 (Stratified Random, p=train_prior)",
        y_true=y_test,
        y_pred=preds_rand_strat,
    )

    # 4. Model C: Existing Day 17 XGBoost Classifier
    cfg = xgboost_config or XGBoostConfig()
    model_xgb = XGBoostDirectionClassifier(config=cfg)
    model_xgb.fit(X_train, y_train)
    preds_xgb = model_xgb.predict(X_test)
    row_xgb = _build_comparison_row(
        strategy_name="Model C (Day 17 XGBoost)",
        y_true=y_test,
        y_pred=preds_xgb,
    )

    rows = [row_majority, row_rand_uniform, row_rand_strat, row_xgb]

    # Optional 5. Model D: Day 19 LightGBM Classifier
    lightgbm_beat_majority = None
    lightgbm_beat_random = None
    if include_lightgbm:
        from app.training.lightgbm_classifier import (
            LightGBMConfig,
            LightGBMDirectionClassifier,
        )

        lgb_cfg = lightgbm_config or LightGBMConfig()
        model_lgb = LightGBMDirectionClassifier(config=lgb_cfg)
        model_lgb.fit(X_train, y_train)
        preds_lgb = model_lgb.predict(X_test)
        row_lgb = _build_comparison_row(
            strategy_name="Model D (Day 19 LightGBM)",
            y_true=y_test,
            y_pred=preds_lgb,
        )
        rows.append(row_lgb)
        lgb_acc = row_lgb.accuracy
        maj_acc = row_majority.accuracy
        rand_unif_acc = row_rand_uniform.accuracy
        lightgbm_beat_majority = lgb_acc > maj_acc
        lightgbm_beat_random = lgb_acc > rand_unif_acc

    # Analysis calculations
    best_acc_row = max(rows, key=lambda r: r.accuracy)
    best_f1_row = max(rows, key=lambda r: r.f1_up)

    xgb_acc = row_xgb.accuracy
    maj_acc = row_majority.accuracy
    rand_unif_acc = row_rand_uniform.accuracy

    xgboost_beat_majority = xgb_acc > maj_acc
    xgboost_beat_random = xgb_acc > rand_unif_acc
    up_bias_detected = row_xgb.pred_up_count >= int(0.85 * len(y_test))

    train_up = int(np.sum(y_train == 1))
    train_down = int(np.sum(y_train == 0))

    if not clf_majority.is_fitted or clf_majority.majority_class_ is None:
        raise ValueError("MajorityClassClassifier must be fitted before constructing comparison report.")

    return BaselineComparisonReport(
        symbol=symbol,
        holdout_sessions=len(y_test),
        holdout_start_date=split_res.holdout_start_date,
        holdout_end_date=split_res.holdout_end_date,
        train_sessions=len(y_train),
        train_up_count=train_up,
        train_down_count=train_down,
        train_majority_class=clf_majority.majority_class_,
        rows=rows,
        best_strategy_by_accuracy=best_acc_row.strategy_name,
        best_strategy_by_f1=best_f1_row.strategy_name,
        xgboost_beat_majority=xgboost_beat_majority,
        xgboost_beat_random=xgboost_beat_random,
        up_bias_detected=up_bias_detected,
        lightgbm_beat_majority=lightgbm_beat_majority,
        lightgbm_beat_random=lightgbm_beat_random,
    )
