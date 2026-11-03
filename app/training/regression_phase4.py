"""Phase 4 isolated target and horizon research."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from app.training.feature_matrix import FeatureMatrixDataset
from app.training.regression_phase3 import (
    _fit_booster,
    _fold_ranges,
    _metrics,
    _ridge_fit_predict,
    build_phase3_features,
)


TARGETS = {
    "close_1": ("close", 1, "price"),
    "close_3": ("close", 3, "price"),
    "close_5": ("close", 5, "price"),
    "open_1": ("open", 1, "price"),
    "return_1": ("return", 1, "return"),
    "return_3": ("return", 3, "return"),
    "return_5": ("return", 5, "return"),
    "high_1": ("high", 1, "price"),
    "low_1": ("low", 1, "price"),
}


def _target_frame(frame: pd.DataFrame, kind: str, horizon: int) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    if kind == "return":
        result["target"] = frame["close"].shift(-horizon) / frame["current_close"] - 1.0
    else:
        result["target"] = frame[kind].shift(-horizon)
    result["reference"] = frame["current_close"]
    result["target_timestamp"] = frame["timestamp"].shift(-horizon)
    result["horizon_return"] = frame["close"].shift(-horizon) / frame["current_close"] - 1.0
    return result


def _prediction_price(predicted: np.ndarray, reference: np.ndarray, kind: str) -> np.ndarray:
    return reference * (1.0 + predicted) if kind == "return" else predicted


def _evaluate_fold(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    feature_columns: list[str],
    kind: str,
) -> Dict[str, Any]:
    X_train = train[feature_columns].to_numpy(dtype=float)
    X_test = validation[feature_columns].to_numpy(dtype=float)
    y_train = train["target"].to_numpy(dtype=float)
    actual = validation["target"].to_numpy(dtype=float)
    reference = validation["reference"].to_numpy(dtype=float)
    train_reference = train["reference"].to_numpy(dtype=float)
    if kind == "return":
        baseline = {
            "previous_close": np.zeros(len(validation)),
            "sma_10": np.zeros(len(validation)),
            "historical_return": np.full(len(validation), np.mean(y_train)),
            "exponential_smoothing": np.full(
                len(validation), train["target"].ewm(span=10).mean().iloc[-1]
            ),
        }
    else:
        baseline_return = np.mean(y_train / train_reference - 1.0)
        baseline = {
            "previous_close": reference,
            "sma_10": validation["sma_10"].to_numpy(dtype=float),
            "historical_return": reference * (1.0 + baseline_return),
            "exponential_smoothing": reference * (
                1.0 + np.mean(train["target"].tail(10) / train_reference[-10:] - 1.0)
            ),
        }
        baseline["sma_10"] = np.where(
            np.isfinite(baseline["sma_10"]), baseline["sma_10"], reference
        )

    predictions: Dict[str, np.ndarray] = baseline.copy()
    predictions["ridge"] = _ridge_fit_predict(
        X_train, y_train, X_test, 10.0
    )
    predictions["linear"] = _ridge_fit_predict(X_train, y_train, X_test, 0.0)
    importance: Dict[str, Dict[str, float]] = {}
    for model_name in ("xgboost", "lightgbm"):
        try:
            predictions[model_name], importance[model_name] = _fit_booster(
                model_name,
                train[feature_columns],
                train["target"],
                validation[feature_columns],
            )
        except ImportError:
            predictions[model_name] = np.full(len(validation), np.nan)
            importance[model_name] = {}

    metrics: Dict[str, Dict[str, Any]] = {}
    for name, predicted in predictions.items():
        if kind == "return":
            metrics[name] = {
                "mae": float(np.mean(np.abs(predicted - actual))),
                "rmse": float(np.sqrt(np.mean((predicted - actual) ** 2))),
                "mape": None,
                "directional_accuracy": float(
                    np.mean((actual > 0.0) == (predicted > 0.0))
                ),
                "samples": int(actual.size),
            }
        else:
            metrics[name] = {
                "mae": float(_metrics(actual, predicted, reference).mae),
                "rmse": float(_metrics(actual, predicted, reference).rmse),
                "mape": float(_metrics(actual, predicted, reference).mape),
                "directional_accuracy": float(
                    np.mean(
                        (actual > reference) == (predicted > reference)
                    )
                ),
                "samples": int(actual.size),
            }
    return {
        "metrics": metrics,
        "feature_importance": importance,
        "regime": (
            "high_volatility"
            if validation["horizon_return"].std() > train["horizon_return"].std()
            else "normal_volatility"
        ),
    }


def evaluate_phase4_target(
    dataset: FeatureMatrixDataset,
    target_name: str,
    context: Optional[pd.DataFrame] = None,
    n_splits: int = 5,
    min_train_ratio: float = 0.4,
    embargo_sessions: int = 1,
) -> Dict[str, Any]:
    kind, horizon, target_type = TARGETS[target_name]
    required = list(dataset.feature_names) + [
        "timestamp", "current_close", "sma_10", "close",
    ]
    if kind != "return":
        required.append(kind)
    frame = dataset.df.dropna(subset=required).copy().reset_index(drop=True)
    features = build_phase3_features(frame, dataset.feature_names, context)
    combined = frame.join(features.add_prefix("f_"))
    feature_columns = [c for c in combined if c.startswith("f_")]
    targets = _target_frame(combined, kind, horizon)
    combined = combined.join(targets)
    clean = combined.dropna(subset=feature_columns + ["target", "reference", "target_timestamp"]).reset_index(drop=True)
    results: Dict[str, list[dict[str, Any]]] = {}
    model_names = [
        "previous_close", "sma_10", "historical_return", "exponential_smoothing",
        "ridge", "linear", "xgboost", "lightgbm",
    ]
    for name in model_names:
        results[name] = []
    for fold, train_end, val_start, val_end in _fold_ranges(
        len(clean), n_splits, min_train_ratio, embargo_sessions
    ):
        train = clean.iloc[:train_end]
        validation = clean.iloc[val_start:val_end]
        evaluated = _evaluate_fold(train, validation, feature_columns, target_type)
        fold_data = {
            "fold": fold,
            "train_start": str(train["timestamp"].iloc[0]),
            "train_end": str(train["timestamp"].iloc[-1]),
            "validation_start": str(validation["timestamp"].iloc[0]),
            "validation_end": str(validation["timestamp"].iloc[-1]),
            "target_start": str(validation["target_timestamp"].iloc[0]),
            "target_end": str(validation["target_timestamp"].iloc[-1]),
            "regime": evaluated["regime"],
            "metrics": evaluated["metrics"],
            "feature_importance": evaluated["feature_importance"],
            "coverage": int(len(validation)),
        }
        for name in model_names:
            results[name].append(fold_data)
    acceptance = {
        name: all(
            fold["metrics"][name]["mae"] < fold["metrics"]["previous_close"]["mae"]
            and fold["metrics"][name]["rmse"] < fold["metrics"]["previous_close"]["rmse"]
            for fold in folds
        )
        for name, folds in results.items()
    }
    return {
        "target": target_name,
        "target_type": target_type,
        "horizon": horizon,
        "symbol": dataset.symbol,
        "rows": len(clean),
        "coverage": len(clean) / max(1, len(frame)),
        "features": feature_columns,
        "folds": results,
        "acceptance": acceptance,
    }
