"""Technical Indicators Layer: Moving Averages.

Provides deterministic, point-in-time calculation of Simple Moving Averages (SMA)
and Exponential Moving Averages (EMA) on cleaned historical market data (MarketOHLCV).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV

logger = get_logger(__name__)


@dataclass(frozen=True)
class MovingAverageFeatures:
    """Canonical calculated moving average features for a single market bar."""

    symbol: str
    timestamp: datetime
    close: float
    smas: Dict[int, Optional[float]]
    emas: Dict[int, Optional[float]]

    @property
    def sma_5(self) -> Optional[float]:
        """Convenience property for 5-session Simple Moving Average."""
        return self.smas.get(5)

    @property
    def sma_10(self) -> Optional[float]:
        """Convenience property for 10-session Simple Moving Average."""
        return self.smas.get(10)

    @property
    def ema_5(self) -> Optional[float]:
        """Convenience property for 5-session Exponential Moving Average."""
        return self.emas.get(5)

    @property
    def ema_10(self) -> Optional[float]:
        """Convenience property for 10-session Exponential Moving Average."""
        return self.emas.get(10)

    def to_dict(self) -> Dict[str, Any]:
        """Convert features to a flat dictionary for tabular analysis and ML datasets."""
        out: Dict[str, Any] = {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "close": self.close,
        }
        for w, val in sorted(self.smas.items()):
            out[f"sma_{w}"] = val
        for w, val in sorted(self.emas.items()):
            out[f"ema_{w}"] = val
        return out


def calculate_sma(
    prices: Sequence[float],
    window: int,
) -> List[Optional[float]]:
    """Compute Simple Moving Average over a sliding chronological window.

    Mathematical Definition:
        SMA_{t, W} = (1 / W) * sum_{i=0}^{W-1} P_{t-i}

    Rules:
        - window must be >= 1.
        - For t < window - 1: Insufficient history; returns None.
        - If any price in the window is non-positive (<= 0) or NaN, returns None.
        - Point-in-time invariant: No future prices enter the calculation.

    Args:
        prices: Chronological sequence of prices (typically raw close).
        window: Number of sessions in moving average window.

    Returns:
        List of moving averages of the same length as prices.
    """
    if window < 1:
        raise ValueError(f"SMA window must be >= 1, got {window}")

    n = len(prices)
    if n == 0:
        return []

    # Check for invalid prices and convert to pandas Series
    clean_vals: List[float] = []
    has_invalid = False
    for p in prices:
        if p is None or math.isnan(p) or p <= 0.0:
            clean_vals.append(float("nan"))
            has_invalid = True
        else:
            clean_vals.append(float(p))

    if has_invalid:
        logger.warning("Encountered non-positive or NaN prices in SMA series; masking affected windows.")

    series = pd.Series(clean_vals, dtype="float64")
    rolling_series = series.rolling(window=window, min_periods=window).mean()

    return [None if math.isnan(v) else float(v) for v in rolling_series]


def calculate_ema(
    prices: Sequence[float],
    window: int,
    min_periods: Optional[int] = None,
    adjust: bool = False,
) -> List[Optional[float]]:
    """Compute Exponential Moving Average over a sliding chronological window.

    Mathematical Definition:
        alpha = 2 / (window + 1)
        EMA_t = alpha * P_t + (1 - alpha) * EMA_{t-1}

    Rules:
        - window must be >= 1.
        - min_periods defaults to window to avoid emitting under-warmed indicators.
        - For t < min_periods - 1: Returns None.
        - If any price in the series is non-positive or NaN, returns None for affected steps.
        - Point-in-time invariant: Strictly backward-looking recursion.

    Args:
        prices: Chronological sequence of prices.
        window: Span of the exponential moving average.
        min_periods: Minimum required valid observations before emitting values (default: window).
        adjust: Whether to divide by decaying adjustment factor (default: False).

    Returns:
        List of exponential moving averages of the same length as prices.
    """
    if window < 1:
        raise ValueError(f"EMA window must be >= 1, got {window}")

    n = len(prices)
    if n == 0:
        return []

    req_periods = min_periods if min_periods is not None else window
    if req_periods < 1:
        raise ValueError(f"EMA min_periods must be >= 1, got {req_periods}")

    clean_vals: List[float] = []
    has_invalid = False
    for p in prices:
        if p is None or math.isnan(p) or p <= 0.0:
            clean_vals.append(float("nan"))
            has_invalid = True
        else:
            clean_vals.append(float(p))

    if has_invalid:
        logger.warning("Encountered non-positive or NaN prices in EMA series; masking affected windows.")

    series = pd.Series(clean_vals, dtype="float64")
    ewm_series = series.ewm(span=window, min_periods=req_periods, adjust=adjust).mean()

    return [None if math.isnan(v) else float(v) for v in ewm_series]


def compute_moving_averages(
    records: Sequence[MarketOHLCV],
    sma_windows: Sequence[int] = (5, 10),
    ema_windows: Sequence[int] = (5, 10),
    min_periods_ema: Optional[int] = None,
    adjust_ema: bool = False,
) -> List[MovingAverageFeatures]:
    """Compute moving average indicators across a sequence of canonical MarketOHLCV records.

    Guarantees:
        - Multi-symbol isolation: Data is grouped by symbol and calculated independently.
        - Chronological ordering: Records are strictly sorted by timestamp ascending.
        - Point-in-time integrity: No future prices leak into historical observations.
        - Source preservation: Original records are never mutated.
        - Selected price basis: Uses canonical raw unadjusted close prices.

    Args:
        records: Sequence of validated MarketOHLCV bars.
        sma_windows: Windows to compute for SMA (default (5, 10)).
        ema_windows: Windows to compute for EMA (default (5, 10)).
        min_periods_ema: Minimum observations before emitting EMA (default: matching window).
        adjust_ema: Pandas EWM adjust parameter (default False).

    Returns:
        List of MovingAverageFeatures chronologically aligned with input bars.
    """
    if not records:
        return []

    # Group records by symbol for isolated per-ticker calculations
    grouped: Dict[str, List[MarketOHLCV]] = defaultdict(list)
    for rec in records:
        grouped[rec.symbol].append(rec)

    all_features: List[MovingAverageFeatures] = []

    for sym, sym_records in sorted(grouped.items(), key=lambda x: x[0]):
        sorted_bars = sorted(sym_records, key=lambda b: b.timestamp)
        prices = [b.close for b in sorted_bars]

        # Compute SMAs
        sma_results: Dict[int, List[Optional[float]]] = {}
        for w in sma_windows:
            sma_results[w] = calculate_sma(prices, window=w)

        # Compute EMAs
        ema_results: Dict[int, List[Optional[float]]] = {}
        for w in ema_windows:
            req_min = min_periods_ema if min_periods_ema is not None else w
            ema_results[w] = calculate_ema(
                prices,
                window=w,
                min_periods=req_min,
                adjust=adjust_ema,
            )

        # Assemble per-bar feature records
        for i, bar in enumerate(sorted_bars):
            bar_smas = {w: sma_results[w][i] for w in sma_windows}
            bar_emas = {w: ema_results[w][i] for w in ema_windows}

            features = MovingAverageFeatures(
                symbol=bar.symbol,
                timestamp=bar.timestamp,
                close=bar.close,
                smas=bar_smas,
                emas=bar_emas,
            )
            all_features.append(features)

    return sorted(all_features, key=lambda f: (f.symbol, f.timestamp))
