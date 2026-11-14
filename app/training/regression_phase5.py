"""Phase 5 data, feature, regime, baseline, and uncertainty audit."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, Sequence

import numpy as np
import pandas as pd

from app.training.feature_matrix import FEATURE_COLUMNS, INDEX_FEATURE_COLUMNS


def _finite(value: Any) -> bool:
    return value is not None and np.isfinite(float(value))


def audit_data(symbol: str, raw: Sequence[Any], cleaned: Sequence[Any], summary: Any) -> Dict[str, Any]:
    rows = sorted(cleaned, key=lambda row: row.timestamp)
    timestamps = [row.timestamp for row in rows]
    closes = np.array([float(row.close) for row in rows], dtype=float) if rows else np.array([])
    dates = [ts.date().isoformat() for ts in timestamps]
    invalid_ohlc = 0
    invalid_price = 0
    invalid_volume = 0
    missing_ohlc = 0
    for row in rows:
        values = [row.open, row.high, row.low, row.close]
        if any(value is None for value in values):
            missing_ohlc += 1
        elif not all(_finite(value) and float(value) > 0 for value in values):
            invalid_price += 1
        if all(_finite(value) for value in values) and not (
            row.low <= min(row.open, row.close) <= max(row.open, row.close) <= row.high
        ):
            invalid_ohlc += 1
        if row.volume is not None and (not _finite(row.volume) or row.volume < 0):
            invalid_volume += 1
    returns = np.diff(closes) / closes[:-1] if len(closes) > 1 else np.array([])
    suspicious = int(np.sum(np.abs(returns) > 0.20))
    tz_names = sorted({str(ts.tzinfo) for ts in timestamps})
    gaps = [
        (timestamps[i] - timestamps[i - 1]).days
        for i in range(1, len(timestamps))
        if (timestamps[i] - timestamps[i - 1]).days > 4
    ]
    return {
        "symbol": symbol,
        "raw_rows": len(raw),
        "cleaned_rows": len(cleaned),
        "rejected_rows": len(raw) - len(cleaned),
        "cleaning_summary": summary.to_dict(),
        "date_start": dates[0] if dates else None,
        "date_end": dates[-1] if dates else None,
        "duplicate_timestamps": len(timestamps) - len(set(timestamps)),
        "duplicate_session_dates": len(dates) - len(set(dates)),
        "chronological": timestamps == sorted(timestamps),
        "timezone_values": tz_names,
        "weekend_records": sum(ts.weekday() >= 5 for ts in timestamps),
        "gaps_over_four_days": len(gaps),
        "gap_days_max": max(gaps, default=0),
        "invalid_ohlc_relationships": invalid_ohlc,
        "missing_ohlc_fields": missing_ohlc,
        "invalid_or_nonpositive_prices": invalid_price,
        "invalid_volume_values": invalid_volume,
        "suspicious_abs_return_over_20pct": suspicious,
        "corporate_action_review": (
            "UNVERIFIABLE from provider-normalized series; adjusted equity data may embed actions."
            if symbol not in {"NIFTY_50", "NIFTY_TELECOMMUNICATIONS"}
            else "Not applicable to index series."
        ),
        "source_limitation": "Provider output was audited; no independent vendor cross-check was performed.",
    }


def feature_audit(feature_names: Iterable[str], index_only: bool = False) -> list[dict[str, Any]]:
    names = list(feature_names)
    rows = []
    methods = {
        "open": ("raw OHLCV open", 0), "high": ("raw OHLCV high", 0),
        "low": ("raw OHLCV low", 0), "close": ("raw OHLCV close", 0),
        "volume": ("raw OHLCV volume", 0),
        "daily_return": ("close[t]/close[t-1]-1", 1),
        "rolling_return_3d": ("rolling close return", 3),
        "rolling_return_5d": ("rolling close return", 5),
        "rolling_volatility_5d": ("rolling standard deviation of returns", 5),
        "annualized_volatility_5d": ("rolling volatility scaled by sqrt(252)", 5),
        "sma_5": ("rolling mean close", 5), "sma_10": ("rolling mean close", 10),
        "ema_5": ("exponential mean close", 5), "ema_10": ("exponential mean close", 10),
        "rsi_14": ("14-session RSI", 14), "macd": ("EMA difference", 26),
        "macd_signal": ("EMA of MACD", 35), "macd_histogram": ("MACD minus signal", 35),
        "bb_middle": ("20-session rolling mean", 20),
        "bb_upper": ("middle plus rolling deviation", 20),
        "bb_lower": ("middle minus rolling deviation", 20),
        "bb_bandwidth": ("Bollinger band width", 20),
        "bb_percent_b": ("close position in Bollinger band", 20),
        "atr_14": ("14-session true range average", 14),
        "roc_10": ("close rate of change", 10),
        "candle_body": ("close minus open", 0),
        "candle_body_abs": ("absolute candle body", 0),
        "candle_range": ("high minus low", 0),
        "candle_upper_wick": ("high minus candle body top", 0),
        "candle_lower_wick": ("candle body bottom minus low", 0),
        "candle_body_ratio": ("body divided by range", 0),
        "candle_upper_wick_ratio": ("upper wick divided by range", 0),
        "candle_lower_wick_ratio": ("lower wick divided by range", 0),
        "candle_close_location": ("close location in range", 0),
        "candle_body_return_pct": ("body divided by open", 0),
        "candle_direction_encoded": ("same-session candle direction", 0),
        "trend_regime_encoded": ("confirmed trend classification", 4),
    }
    for name in names:
        method, lookback = methods.get(name, ("implementation not mapped by audit", None))
        rows.append({
            "feature": name,
            "calculation": method,
            "source_columns": "OHLCV/derived history",
            "lookback_sessions": lookback,
            "available_at_close": True,
            "available_at_open": name in {"open", "volume"},
            "future_information_detected": False,
            "classification": "SAFE" if lookback is not None else "UNVERIFIABLE",
            "notes": "Close-derived features are valid for close-to-close targets; not valid for predicting the same session open.",
        })
    return rows


def _regimes(frame: pd.DataFrame) -> pd.DataFrame:
    close = frame["close"].astype(float)
    ret = close.pct_change()
    vol = ret.rolling(20).std()
    slope = close.pct_change(20)
    drawdown = close / close.cummax() - 1.0
    vol_hi, vol_lo = vol.quantile(0.75), vol.quantile(0.25)
    out = pd.DataFrame(index=frame.index)
    out["return"] = ret
    out["volatility"] = vol
    out["slope"] = slope
    out["drawdown"] = drawdown
    out["volatility_regime"] = np.select(
        [vol >= vol_hi, vol <= vol_lo], ["high_volatility", "low_volatility"], default="normal_volatility"
    )
    out["trend_regime"] = np.select(
        [slope >= 0.05, slope <= -0.05], ["trending_up", "trending_down"], default="sideways"
    )
    out["stress_regime"] = np.select(
        [drawdown <= -0.15, drawdown >= -0.03], ["correction", "recovery_or_high"], default="neutral"
    )
    return out


def baseline_audit(frame: pd.DataFrame) -> Dict[str, Any]:
    close = frame["close"].astype(float)
    ret = close.pct_change()
    valid = ret.dropna()
    errors = close.diff().dropna()
    ac = float(valid.autocorr()) if len(valid) > 2 else None
    direction_persistence = float(np.mean(np.sign(valid.iloc[1:].to_numpy()) == np.sign(valid.iloc[:-1].to_numpy()))) if len(valid) > 2 else None
    regimes = _regimes(frame)
    regime_errors = {}
    aligned = pd.DataFrame({"error": errors.abs(), "regime": regimes["volatility_regime"].iloc[1:].to_numpy()})
    for regime, group in aligned.groupby("regime"):
        regime_errors[regime] = {"samples": len(group), "mae": float(group["error"].mean())}
    return {
        "samples": len(valid),
        "mean_return": float(valid.mean()),
        "median_return": float(valid.median()),
        "return_std": float(valid.std()),
        "return_min": float(valid.min()),
        "return_max": float(valid.max()),
        "return_autocorrelation_lag1": ac,
        "directional_persistence": direction_persistence,
        "previous_close_mae": float(errors.abs().mean()),
        "previous_close_rmse": float(np.sqrt(np.mean(errors.to_numpy() ** 2))),
        "previous_close_error_by_volatility_regime": regime_errors,
        "volatility_clustering_proxy": float(valid.abs().autocorr()) if len(valid) > 2 else None,
        "interpretation": "Descriptive statistics only; predictability is not established by autocorrelation alone.",
    }


def uncertainty_audit(frame: pd.DataFrame) -> Dict[str, Any]:
    errors = frame["close"].diff().dropna().to_numpy()
    if len(errors) < 100:
        return {"status": "UNAVAILABLE", "reason": "Fewer than 100 baseline residuals."}
    low, high = np.quantile(errors, [0.05, 0.95])
    lower = frame["close"].iloc[1:].to_numpy() + low
    upper = frame["close"].iloc[1:].to_numpy() + high
    actual = frame["close"].iloc[1:].to_numpy()
    return {
        "status": "DESCRIPTIVE_BASELINE_ONLY",
        "residual_source": "previous-close baseline, not a fitted model",
        "nominal_interval": "empirical 90 percent central residual interval",
        "residual_q05": float(low),
        "residual_q95": float(high),
        "interval_width": float(high - low),
        "empirical_coverage": float(np.mean((actual >= lower) & (actual <= upper))),
        "warning": "Coverage is descriptive and not evidence for model confidence or future calibration.",
    }
