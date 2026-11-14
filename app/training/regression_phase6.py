"""Phase 6 out-of-sample residual and interval research."""

from __future__ import annotations

from typing import Any, Dict, Iterable

import numpy as np
import pandas as pd


REGIMES = ("volatility", "trend")
INTERVAL_LEVELS = (0.50, 0.80, 0.90, 0.95)


def _signals(frame: pd.DataFrame) -> pd.DataFrame:
    close = frame["close"].astype(float)
    returns = close.pct_change()
    result = pd.DataFrame(index=frame.index)
    result["volatility"] = returns.rolling(20).std()
    result["trend_return"] = close.pct_change(20)
    return result


def _labels(signals: pd.DataFrame, train_signals: pd.DataFrame) -> pd.DataFrame:
    vol_low, vol_high = train_signals["volatility"].dropna().quantile([0.25, 0.75])
    return pd.DataFrame({
        "volatility": np.select(
            [signals["volatility"] <= vol_low, signals["volatility"] >= vol_high],
            ["low_volatility", "high_volatility"],
            default="normal_volatility",
        ),
        "trend": np.select(
            [signals["trend_return"] <= -0.05, signals["trend_return"] >= 0.05],
            ["trending_down", "trending_up"],
            default="sideways",
        ),
    }, index=signals.index)


def _stats(actual: np.ndarray, predicted: np.ndarray, reference: np.ndarray) -> Dict[str, Any]:
    residual = actual - predicted
    absolute = np.abs(residual)
    return {
        "samples": int(len(actual)),
        "mae": float(absolute.mean()) if len(actual) else None,
        "rmse": float(np.sqrt(np.mean(residual ** 2))) if len(actual) else None,
        "mean_residual": float(residual.mean()) if len(actual) else None,
        "median_residual": float(np.median(residual)) if len(actual) else None,
        "residual_std": float(residual.std(ddof=1)) if len(actual) > 1 else None,
        "absolute_error_quantiles": {
            str(level): float(np.quantile(absolute, level)) for level in (0.5, 0.8, 0.9, 0.95)
        } if len(actual) else {},
        "directional_accuracy": float(
            np.mean((actual > reference) == (predicted > reference))
        ) if len(actual) else None,
    }


def _intervals(
    actual: np.ndarray,
    predicted: np.ndarray,
    residual_history: np.ndarray,
) -> Dict[str, Any]:
    if len(residual_history) < 50:
        return {
            str(level): {
                "status": "UNAVAILABLE",
                "reason": "Fewer than 50 prior out-of-sample residuals.",
            }
            for level in INTERVAL_LEVELS
        }
    output = {}
    for level in INTERVAL_LEVELS:
        alpha = (1.0 - level) / 2.0
        low, high = np.quantile(residual_history, [alpha, 1.0 - alpha])
        lower, upper = predicted + low, predicted + high
        output[str(level)] = {
            "status": "WALK_FORWARD_EMPIRICAL",
            "residual_history_samples": int(len(residual_history)),
            "lower_residual": float(low),
            "upper_residual": float(high),
            "average_width": float(high - low),
            "coverage": float(np.mean((actual >= lower) & (actual <= upper))),
        }
    return output


def evaluate_walk_forward(
    frame: pd.DataFrame,
    n_splits: int = 5,
    min_train_ratio: float = 0.4,
    embargo: int = 1,
) -> Dict[str, Any]:
    signals = _signals(frame)
    n_rows = len(frame)
    initial = max(50, int(n_rows * min_train_ratio))
    available = n_rows - initial - embargo
    if available < n_splits:
        raise ValueError("Insufficient rows for Phase 6 walk-forward evaluation.")
    fold_size = max(1, available // n_splits)
    folds = []
    residual_history = []
    for fold_number in range(n_splits):
        start = initial + embargo + fold_number * fold_size
        end = n_rows if fold_number == n_splits - 1 else min(n_rows, start + fold_size)
        train_end = start - embargo
        train = frame.iloc[:train_end]
        validation = frame.iloc[start:end]
        actual = validation["close"].to_numpy(dtype=float)
        predicted = validation["close"].shift(1).to_numpy(dtype=float).copy()
        reference = validation["close"].shift(1).to_numpy(dtype=float).copy()
        # The first validation row uses the immediately preceding training close.
        predicted[0] = frame["close"].iloc[start - 1]
        reference[0] = predicted[0]
        residuals = actual - predicted
        labels = _labels(signals.iloc[start:end], signals.iloc[:train_end])
        fold_record = {
            "fold": fold_number + 1,
            "train_end": str(train["timestamp"].iloc[-1]),
            "validation_start": str(validation["timestamp"].iloc[0]),
            "validation_end": str(validation["timestamp"].iloc[-1]),
            "samples": len(validation),
            "overall": _stats(actual, predicted, reference),
            "regimes": {},
            "intervals": _intervals(actual, predicted, np.asarray(residual_history)),
        }
        for regime_column in REGIMES:
            fold_record["regimes"][regime_column] = {}
            for label in sorted(labels[regime_column].unique()):
                mask = labels[regime_column].to_numpy() == label
                regime_stats = _stats(actual[mask], predicted[mask], reference[mask])
                regime_stats["intervals"] = {}
                for level, interval in fold_record["intervals"].items():
                    if interval["status"] == "UNAVAILABLE":
                        regime_stats["intervals"][level] = interval
                        continue
                    low, high = interval["lower_residual"], interval["upper_residual"]
                    regime_stats["intervals"][level] = {
                        "status": interval["status"],
                        "coverage": float(np.mean(
                            (actual[mask] >= predicted[mask] + low)
                            & (actual[mask] <= predicted[mask] + high)
                        )),
                        "average_width": interval["average_width"],
                    }
                fold_record["regimes"][regime_column][label] = regime_stats
        folds.append(fold_record)
        residual_history.extend(residuals.tolist())
    return {
        "folds": folds,
        "total_out_of_sample_samples": sum(fold["samples"] for fold in folds),
        "interval_levels": INTERVAL_LEVELS,
        "interval_method": "training-history residual quantiles applied to later validation fold",
        "embargo_sessions": embargo,
    }


def aggregate_regime_results(evaluation: Dict[str, Any]) -> Dict[str, Any]:
    output: Dict[str, Any] = {}
    for dimension in REGIMES:
        output[dimension] = {}
        labels = {
            label
            for fold in evaluation["folds"]
            for label in fold["regimes"][dimension]
        }
        for label in sorted(labels):
            records = [
                fold["regimes"][dimension][label]
                for fold in evaluation["folds"]
                if label in fold["regimes"][dimension]
            ]
            weights = np.array([record["samples"] for record in records], dtype=float)
            output[dimension][label] = {
                "samples": int(weights.sum()),
                "mae": float(np.average([r["mae"] for r in records], weights=weights)),
                "rmse": float(np.sqrt(np.average([r["rmse"] ** 2 for r in records], weights=weights))),
                "mean_residual": float(np.average([r["mean_residual"] for r in records], weights=weights)),
                "median_residual": float(np.average([r["median_residual"] for r in records], weights=weights)),
                "residual_std": float(np.average([r["residual_std"] for r in records], weights=weights)),
                "directional_accuracy": float(np.average([r["directional_accuracy"] for r in records], weights=weights)),
                "absolute_error_quantiles": {
                    key: float(np.average([r["absolute_error_quantiles"][key] for r in records], weights=weights))
                    for key in records[0]["absolute_error_quantiles"]
                },
            }
    return output
