"""Phase 3 isolated forecasting research.

Only standard-library/NumPy code and already-installed native booster APIs are
used. Nothing here is imported by the production prediction service.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from app.training.feature_matrix import FeatureMatrixDataset

try:
    import xgboost as xgb
except ImportError:  # pragma: no cover
    xgb = None

try:
    import lightgbm as lgb
except ImportError:  # pragma: no cover
    lgb = None


@dataclass(frozen=True)
class Phase3Metrics:
    mae: float
    rmse: float
    mape: float
    directional_accuracy: float
    samples: int


def _metrics(actual: np.ndarray, predicted: np.ndarray, reference: np.ndarray) -> Phase3Metrics:
    error = predicted - actual
    return Phase3Metrics(
        mae=float(np.mean(np.abs(error))),
        rmse=float(np.sqrt(np.mean(error**2))),
        mape=float(np.mean(np.abs(error / actual)) * 100.0),
        directional_accuracy=float(np.mean((actual > reference) == (predicted > reference))),
        samples=int(actual.size),
    )


def _fold_ranges(n_rows: int, n_splits: int, min_train_ratio: float, embargo: int):
    initial = max(50, int(n_rows * min_train_ratio))
    available = n_rows - initial - embargo
    if available < n_splits:
        raise ValueError("Insufficient rows for requested Phase 3 folds.")
    size = max(1, available // n_splits)
    for fold in range(n_splits):
        start = initial + embargo + fold * size
        end = n_rows if fold == n_splits - 1 else min(n_rows, start + size)
        if end > start:
            yield fold + 1, start - embargo, start, end


def build_phase3_features(
    frame: pd.DataFrame,
    feature_names: Sequence[str],
    context: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Build prediction-time-only relative features from an aligned frame."""
    result = pd.DataFrame(index=frame.index)
    close = frame["current_close"].astype(float)
    prev_close = close.shift(1)
    for name in feature_names:
        values = frame[name].astype(float)
        if name in {
            "open", "high", "low", "close", "sma_5", "sma_10", "ema_5", "ema_10",
            "bb_middle", "bb_upper", "bb_lower",
        }:
            result[f"rel_{name}"] = values / close.replace(0.0, np.nan) - 1.0
        elif name == "volume":
            result["log_volume"] = np.log1p(values.clip(lower=0.0))
        else:
            result[name] = values

    for window in (1, 2, 3, 5, 10):
        result[f"return_{window}"] = close.pct_change(window)
    has_open = "open" in frame and frame["open"].notna().all()
    has_volume = "volume" in frame and frame["volume"].notna().all()
    result["gap_pct"] = frame["open"].astype(float) / prev_close - 1.0 if has_open else 0.0
    result["volume_change_1"] = (
        frame["volume"].astype(float).pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
        if has_volume else 0.0
    )
    result["volume_ratio_10"] = (
        (
            frame["volume"].astype(float)
            / frame["volume"].astype(float).rolling(10).mean().replace(0.0, np.nan)
        ).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        if has_volume else 0.0
    )
    result["sma_distance_10"] = close / close.rolling(10).mean() - 1.0
    result["sma_distance_20"] = close / close.rolling(20).mean() - 1.0

    if context is not None and not context.empty:
        frame_dates = pd.to_datetime(frame["timestamp"]).dt.normalize()
        context_index = pd.to_datetime(context.index).normalize()
        normalized_context = context.copy()
        normalized_context.index = context_index
        joined = normalized_context.reindex(frame_dates.array)
        for column in joined.columns:
            result[f"context_{column}"] = joined[column].to_numpy()
    return result.replace([np.inf, -np.inf], np.nan)


def _ridge_fit_predict(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    alpha: float,
) -> np.ndarray:
    mean = X_train.mean(axis=0)
    scale = X_train.std(axis=0)
    scale[scale == 0.0] = 1.0
    train = (X_train - mean) / scale
    test = (X_test - mean) / scale
    design = np.column_stack([np.ones(len(train)), train])
    penalty = np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    if alpha == 0.0:
        coefficients = np.linalg.lstsq(design, y_train, rcond=None)[0]
    else:
        coefficients = np.linalg.solve(design.T @ design + alpha * penalty, design.T @ y_train)
    return np.column_stack([np.ones(len(test)), test]) @ coefficients


def _fit_booster(
    name: str,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
) -> tuple[np.ndarray, Dict[str, float]]:
    if name == "xgboost":
        if xgb is None:
            raise ImportError("xgboost is unavailable")
        model = xgb.train(
            {
                "objective": "reg:squarederror", "eval_metric": "rmse",
                "max_depth": 3, "eta": 0.03, "subsample": 0.85,
                "colsample_bytree": 0.8, "min_child_weight": 10,
                "seed": 42, "nthread": 1, "tree_method": "hist",
            },
            xgb.DMatrix(X_train, label=y_train, feature_names=list(X_train.columns)),
            num_boost_round=150,
            verbose_eval=False,
        )
        return (
            model.predict(xgb.DMatrix(X_test, feature_names=list(X_test.columns))),
            {key: float(value) for key, value in model.get_score(importance_type="gain").items()},
        )
    if lgb is None:
        raise ImportError("lightgbm is unavailable")
    train = lgb.Dataset(X_train, label=y_train, feature_name=list(X_train.columns), free_raw_data=False)
    model = lgb.train(
        {
            "objective": "regression", "metric": "rmse", "max_depth": 3,
            "num_leaves": 7, "learning_rate": 0.03, "feature_fraction": 0.8,
            "bagging_fraction": 0.85, "bagging_freq": 1, "min_data_in_leaf": 20,
            "seed": 42, "num_threads": 1, "verbosity": -1, "deterministic": True,
        },
        train,
        num_boost_round=150,
    )
    return (
        model.predict(X_test),
        {name: float(value) for name, value in zip(X_train.columns, model.feature_importance(importance_type="gain"))},
    )


def evaluate_phase3(
    dataset: FeatureMatrixDataset,
    context: Optional[pd.DataFrame] = None,
    n_splits: int = 5,
    min_train_ratio: float = 0.4,
    embargo_sessions: int = 1,
) -> Dict[str, Any]:
    required = list(dataset.feature_names) + ["timestamp", "current_close", "next_close", "target_return"]
    frame = dataset.df.dropna(subset=required).copy().reset_index(drop=True)
    features = build_phase3_features(frame, dataset.feature_names, context)
    combined = frame.join(features.add_prefix("f_"))
    feature_columns = [column for column in combined.columns if column.startswith("f_")]
    clean = combined.dropna(subset=feature_columns).reset_index(drop=True)
    results: Dict[str, list[dict[str, Any]]] = {
        "previous_close": [], "sma_10": [], "historical_return": [],
        "ridge": [], "linear": [], "xgboost": [], "lightgbm": [],
        "exponential_smoothing": [], "volatility_adjusted": [],
    }

    for fold, train_end, val_start, val_end in _fold_ranges(
        len(clean), n_splits, min_train_ratio, embargo_sessions
    ):
        train = clean.iloc[:train_end]
        validation = clean.iloc[val_start:val_end]
        X_train = train[feature_columns].to_numpy(dtype=float)
        X_test = validation[feature_columns].to_numpy(dtype=float)
        y_train = train["target_return"].to_numpy(dtype=float)
        actual = validation["next_close"].to_numpy(dtype=float)
        reference = validation["current_close"].to_numpy(dtype=float)
        baselines = {
            "previous_close": reference,
            "sma_10": validation["sma_10"].to_numpy(dtype=float),
            "historical_return": reference * (1.0 + np.mean(y_train)),
            "exponential_smoothing": reference * (1.0 + train["target_return"].ewm(span=10).mean().iloc[-1]),
            "volatility_adjusted": reference * (
                1.0 + np.clip(train["target_return"].tail(20).mean(), -train["target_return"].tail(20).std(), train["target_return"].tail(20).std())
            ),
        }
        baselines["sma_10"] = np.where(np.isfinite(baselines["sma_10"]), baselines["sma_10"], reference)
        shared = {
            "fold": fold,
            "train_start": str(train["timestamp"].iloc[0]),
            "train_end": str(train["timestamp"].iloc[-1]),
            "validation_start": str(validation["timestamp"].iloc[0]),
            "validation_end": str(validation["timestamp"].iloc[-1]),
            "metrics": {},
            "residual_mean": {},
            "residual_std": {},
            "regime": "high_volatility" if validation["target_return"].std() > train["target_return"].std() else "normal_volatility",
            "feature_importance": {},
        }
        for name, predicted in baselines.items():
            shared["metrics"][name] = asdict(_metrics(actual, predicted, reference))

        model_predictions = {
            "ridge": _ridge_fit_predict(X_train, y_train, X_test, 10.0),
            "linear": _ridge_fit_predict(X_train, y_train, X_test, 0.0),
        }
        for name in ("xgboost", "lightgbm"):
            try:
                predicted_return, importance = _fit_booster(
                    name,
                    clean.iloc[:train_end][feature_columns],
                    train["target_return"],
                    clean.iloc[val_start:val_end][feature_columns],
                )
                model_predictions[name] = predicted_return
                shared["feature_importance"][name] = importance
            except ImportError:
                shared["feature_importance"][name] = {}

        for name, predicted_return in model_predictions.items():
            predicted_price = reference * (1.0 + predicted_return)
            shared["metrics"][name] = asdict(_metrics(actual, predicted_price, reference))
            residual = predicted_price - actual
            shared["residual_mean"][name] = float(np.mean(residual))
            shared["residual_std"][name] = float(np.std(residual))
        for name in ("exponential_smoothing", "volatility_adjusted"):
            residual = baselines[name] - actual
            shared["residual_mean"][name] = float(np.mean(residual))
            shared["residual_std"][name] = float(np.std(residual))
        for name in results:
            results[name].append(shared.copy())

    return {
        "symbol": dataset.symbol,
        "rows": len(clean),
        "features": feature_columns,
        "folds": results,
        "acceptance": {
            name: all(
                fold["metrics"][name]["mae"] < fold["metrics"]["previous_close"]["mae"]
                and fold["metrics"][name]["rmse"] < fold["metrics"]["previous_close"]["rmse"]
                for fold in folds
            )
            for name, folds in results.items()
        },
    }
