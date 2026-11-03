"""Isolated research evaluator for next-session return regression.

This module is deliberately separate from the production directional models.
It uses native XGBoost and LightGBM APIs, chronological folds, and training-only
baseline estimates. It does not write model artifacts or database records.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from app.training.feature_matrix import FeatureMatrixDataset

try:
    import xgboost as xgb
except ImportError:  # pragma: no cover - environment dependent
    xgb = None

try:
    import lightgbm as lgb
except ImportError:  # pragma: no cover - environment dependent
    lgb = None


@dataclass(frozen=True)
class RegressionMetrics:
    mae: float
    rmse: float
    mape: float
    directional_accuracy: float
    samples: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RegressionFold:
    fold: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    train_rows: int
    validation_rows: int
    metrics: Dict[str, RegressionMetrics]
    feature_importance: Dict[str, float]
    residual_mean: float
    residual_std: float
    residual_max_abs: float
    regime: str

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["metrics"] = {name: metric.to_dict() for name, metric in self.metrics.items()}
        return result


def _metrics(actual: np.ndarray, predicted: np.ndarray, reference: np.ndarray) -> RegressionMetrics:
    errors = predicted - actual
    actual_direction = actual > reference
    predicted_direction = predicted > reference
    return RegressionMetrics(
        mae=float(np.mean(np.abs(errors))),
        rmse=float(np.sqrt(np.mean(errors**2))),
        mape=float(np.mean(np.abs(errors / actual)) * 100.0),
        directional_accuracy=float(np.mean(actual_direction == predicted_direction)),
        samples=int(len(actual)),
    )


def _normalized_features(df: pd.DataFrame, feature_names: Sequence[str]) -> pd.DataFrame:
    """Make price-level features scale-stable while retaining technical signals."""
    result = pd.DataFrame(index=df.index)
    close = df["current_close"].astype(float).replace(0.0, np.nan)
    level_features = {
        "open", "high", "low", "close", "sma_5", "sma_10", "ema_5", "ema_10",
        "bb_middle", "bb_upper", "bb_lower",
    }
    for name in feature_names:
        values = df[name].astype(float)
        if name in level_features:
            result[name] = values / close - 1.0
        elif name == "volume":
            result[name] = np.log1p(values.clip(lower=0.0))
        else:
            result[name] = values
    return result


def _fold_ranges(n_rows: int, n_splits: int, min_train_ratio: float, embargo: int) -> Iterable[Tuple[int, int, int]]:
    initial_train = max(20, int(n_rows * min_train_ratio))
    available = n_rows - initial_train - embargo
    if available < n_splits:
        raise ValueError("Not enough rows for requested chronological regression folds.")
    fold_size = max(1, available // n_splits)
    for fold in range(n_splits):
        val_start = initial_train + embargo + fold * fold_size
        val_end = n_rows if fold == n_splits - 1 else min(n_rows, val_start + fold_size)
        if val_end > val_start:
            yield val_start - embargo, val_start, val_end


def _fit_xgboost(X: pd.DataFrame, y: pd.Series) -> Any:
    if xgb is None:
        raise ImportError("xgboost is required for regression research.")
    return xgb.train(
        {
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
            "max_depth": 3,
            "eta": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "seed": 42,
            "nthread": 1,
            "tree_method": "hist",
        },
        xgb.DMatrix(X, label=y, feature_names=list(X.columns)),
        num_boost_round=80,
        verbose_eval=False,
    )


def _fit_lightgbm(X: pd.DataFrame, y: pd.Series) -> Any:
    if lgb is None:
        raise ImportError("lightgbm is required for regression research.")
    train = lgb.Dataset(X, label=y, feature_name=list(X.columns), free_raw_data=False)
    return lgb.train(
        {
            "objective": "regression",
            "metric": "rmse",
            "max_depth": 3,
            "num_leaves": 7,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 1,
            "seed": 42,
            "num_threads": 1,
            "verbosity": -1,
            "deterministic": True,
        },
        train,
        num_boost_round=80,
    )


def evaluate_regression_research(
    dataset: FeatureMatrixDataset,
    n_splits: int = 5,
    min_train_ratio: float = 0.4,
    embargo_sessions: int = 1,
) -> Dict[str, Any]:
    """Evaluate return regressors and fold-local baselines without side effects."""
    required = list(dataset.feature_names) + ["current_close", "next_close", "target_return", "timestamp"]
    frame = dataset.df.dropna(subset=required).copy().reset_index(drop=True)
    if len(frame) < 100:
        raise ValueError("Regression research requires at least 100 complete labeled rows.")
    X_all = _normalized_features(frame, dataset.feature_names)
    if not np.isfinite(X_all.to_numpy(dtype=float)).all():
        raise ValueError("Normalized research features contain non-finite values.")
    target = frame["target_return"].astype(float)
    models = {"xgboost": _fit_xgboost, "lightgbm": _fit_lightgbm}
    folds: Dict[str, List[RegressionFold]] = {name: [] for name in models}

    for fold_number, (train_end, val_start, val_end) in enumerate(
        _fold_ranges(len(frame), n_splits, min_train_ratio, embargo_sessions), start=1
    ):
        train = frame.iloc[:train_end]
        validation = frame.iloc[val_start:val_end]
        X_train = X_all.iloc[:train_end]
        X_validation = X_all.iloc[val_start:val_end]
        y_train = target.iloc[:train_end]
        actual = validation["next_close"].to_numpy(dtype=float)
        reference = validation["current_close"].to_numpy(dtype=float)
        moving_average = validation["sma_10"].to_numpy(dtype=float)
        return_mean = float(y_train.mean())
        baseline_predictions = {
            "previous_close": reference,
            "moving_average": moving_average,
            "historical_return": reference * (1.0 + return_mean),
        }
        baseline_predictions["moving_average"] = np.where(
            np.isfinite(baseline_predictions["moving_average"]),
            baseline_predictions["moving_average"],
            reference,
        )
        validation_mean = float(validation["target_return"].mean())
        validation_volatility = float(validation["target_return"].std())
        train_volatility = float(train["target_return"].std())
        direction_regime = "positive_return_regime" if validation_mean >= 0.0 else "negative_return_regime"
        volatility_regime = "high_volatility" if validation_volatility > train_volatility else "normal_volatility"
        regime_label = f"{direction_regime}, {volatility_regime}"

        for model_name, fit in models.items():
            model = fit(X_train, y_train)
            if model_name == "xgboost":
                predicted_return = model.predict(xgb.DMatrix(X_validation, feature_names=list(X_all.columns)))
                importance = model.get_score(importance_type="gain")
            else:
                predicted_return = model.predict(X_validation)
                importance = dict(zip(X_all.columns, model.feature_importance(importance_type="gain")))
            predicted_price = reference * (1.0 + predicted_return)
            metrics = {name: _metrics(actual, values, reference) for name, values in baseline_predictions.items()}
            metrics[model_name] = _metrics(actual, predicted_price, reference)
            residuals = predicted_price - actual
            folds[model_name].append(
                RegressionFold(
                    fold=fold_number,
                    train_start=str(train["timestamp"].iloc[0]),
                    train_end=str(train["timestamp"].iloc[-1]),
                    validation_start=str(validation["timestamp"].iloc[0]),
                    validation_end=str(validation["timestamp"].iloc[-1]),
                    train_rows=len(train),
                    validation_rows=len(validation),
                    metrics=metrics,
                    feature_importance={key: float(value) for key, value in importance.items()},
                    residual_mean=float(np.mean(residuals)),
                    residual_std=float(np.std(residuals)),
                    residual_max_abs=float(np.max(np.abs(residuals))),
                    regime=regime_label,
                )
            )

    summary: Dict[str, Any] = {}
    for model_name, model_folds in folds.items():
        metric_names = ["previous_close", "moving_average", "historical_return", model_name]
        summary[model_name] = {
            "folds": [fold.to_dict() for fold in model_folds],
            "mean_metrics": {
                metric: {
                    key: float(np.mean([getattr(fold.metrics[metric], key) for fold in model_folds]))
                    for key in ("mae", "rmse", "mape", "directional_accuracy")
                }
                for metric in metric_names
            },
            "beats_previous_close_all_folds": all(
                fold.metrics[model_name].mae < fold.metrics["previous_close"].mae
                and fold.metrics[model_name].rmse < fold.metrics["previous_close"].rmse
                for fold in model_folds
            ),
            "beats_any_baseline_all_folds": all(
                fold.metrics[model_name].mae < min(
                    fold.metrics["previous_close"].mae,
                    fold.metrics["moving_average"].mae,
                    fold.metrics["historical_return"].mae,
                )
                and fold.metrics[model_name].rmse < min(
                    fold.metrics["previous_close"].rmse,
                    fold.metrics["moving_average"].rmse,
                    fold.metrics["historical_return"].rmse,
                )
                for fold in model_folds
            ),
        }
    return {
        "symbol": dataset.symbol,
        "rows": len(frame),
        "features": list(X_all.columns),
        "target": "next_session_return",
        "n_splits": n_splits,
        "embargo_sessions": embargo_sessions,
        "models": summary,
    }
