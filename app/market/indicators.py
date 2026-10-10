"""Technical Indicators Layer: Moving Averages and Oscillators.

Provides deterministic, point-in-time calculation of Simple Moving Averages (SMA),
Exponential Moving Averages (EMA), Relative Strength Index (RSI), and
Moving Average Convergence Divergence (MACD) on cleaned historical market data (MarketOHLCV).
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV

logger = get_logger(__name__)


@dataclass(frozen=True)
class MACDSeries:
    """Calculated Moving Average Convergence Divergence (MACD) indicator series.

    Encapsulates MACD line, Signal line, and MACD Histogram.
    Implements sequence protocol for 3-tuple unpacking:
        macd_line, signal_line, histogram = calculate_macd(prices)
    """

    macd: List[Optional[float]]
    signal: List[Optional[float]]
    histogram: List[Optional[float]]

    def __iter__(self):
        """Allow unpacking as (macd, signal, histogram)."""
        return iter((self.macd, self.signal, self.histogram))

    def __len__(self) -> int:
        """Return the length of the series."""
        return len(self.macd)


@dataclass(frozen=True)
class MovingAverageFeatures:
    """Canonical calculated technical indicator features for a single market bar.

    Encapsulates Simple Moving Averages (SMA), Exponential Moving Averages (EMA),
    Relative Strength Index (RSI), and Moving Average Convergence Divergence (MACD).
    """

    symbol: str
    timestamp: datetime
    close: float
    smas: Dict[int, Optional[float]]
    emas: Dict[int, Optional[float]]
    rsi: Dict[int, Optional[float]] = field(default_factory=dict)
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None

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

    @property
    def rsi_14(self) -> Optional[float]:
        """Convenience property for standard 14-session Relative Strength Index."""
        return self.rsi.get(14)

    @property
    def macd_line(self) -> Optional[float]:
        """Convenience property for MACD line."""
        return self.macd

    @property
    def signal_line(self) -> Optional[float]:
        """Convenience property for MACD signal line."""
        return self.macd_signal

    @property
    def histogram(self) -> Optional[float]:
        """Convenience property for MACD histogram."""
        return self.macd_histogram

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
        for p, val in sorted(self.rsi.items()):
            out[f"rsi_{p}"] = val
        out["macd"] = self.macd
        out["macd_signal"] = self.macd_signal
        out["macd_histogram"] = self.macd_histogram
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
    prices: Sequence[Optional[float]],
    window: int,
    min_periods: Optional[int] = None,
    adjust: bool = False,
    allow_negative: bool = False,
) -> List[Optional[float]]:
    """Compute Exponential Moving Average over a sliding chronological window.

    Mathematical Definition:
        alpha = 2 / (window + 1)
        EMA_t = alpha * P_t + (1 - alpha) * EMA_{t-1}

    Rules:
        - window must be >= 1.
        - min_periods defaults to window to avoid emitting under-warmed indicators.
        - For t < min_periods - 1: Returns None.
        - If allow_negative is False, non-positive (<= 0) or NaN prices return None for affected steps.
        - If allow_negative is True, only None or NaN values return None (permitting negative/zero oscillator values).
        - Point-in-time invariant: Strictly backward-looking recursion.

    Args:
        prices: Chronological sequence of prices or series values.
        window: Span of the exponential moving average.
        min_periods: Minimum required valid observations before emitting values (default: window).
        adjust: Whether to divide by decaying adjustment factor (default: False).
        allow_negative: Whether to permit zero or negative numbers in the series (default: False).

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
        if p is None or math.isnan(p) or (not allow_negative and p <= 0.0):
            clean_vals.append(float("nan"))
            has_invalid = True
        else:
            clean_vals.append(float(p))

    if has_invalid and not allow_negative:
        logger.warning("Encountered non-positive or NaN prices in EMA series; masking affected windows.")

    series = pd.Series(clean_vals, dtype="float64")
    ewm_series = series.ewm(span=window, min_periods=req_periods, adjust=adjust).mean()

    return [None if math.isnan(v) or math.isnan(clean_vals[i]) else float(v) for i, v in enumerate(ewm_series)]


def calculate_rsi(
    prices: Sequence[float],
    period: int = 14,
) -> List[Optional[float]]:
    """Compute Relative Strength Index (RSI) using Wilder's smoothing method.

    RSI measures the speed and change of price movements on a scale from 0 to 100.
    Note: RSI is an indicator of historical momentum and relative price changes;
    it is NOT a guaranteed price-direction predictor.

    Mathematical Definition (Wilder's Smoothing):
        For consecutive prices P_0, P_1, ..., P_{N-1}:
            Price change Delta P_t = P_t - P_{t-1} for t >= 1
            Gain_t = max(Delta P_t, 0.0)
            Loss_t = max(-Delta P_t, 0.0)

        Initial Seed (at t = period, over the first 'period' price changes):
            AvgGain_{period} = (1 / period) * sum_{i=1}^{period} Gain_i
            AvgLoss_{period} = (1 / period) * sum_{i=1}^{period} Loss_i

        Wilder's Smoothing for subsequent sessions (t > period):
            AvgGain_t = (AvgGain_{t-1} * (period - 1) + Gain_t) / period
            AvgLoss_t = (AvgLoss_{t-1} * (period - 1) + Loss_t) / period

        Relative Strength (RS) and RSI Conversion:
            RS = AvgGain / AvgLoss
            RSI = 100.0 - (100.0 / (1.0 + RS)) = 100.0 * (AvgGain / (AvgGain + AvgLoss))

    Warm-up & Edge-Case Rules:
        - period must be >= 1.
        - For t < period (fewer than period price changes, meaning <= period total prices): returns None.
        - Flat prices (AvgGain == 0 and AvgLoss == 0): returns 50.0 (neutral baseline).
        - Gains without losses (AvgGain > 0 and AvgLoss == 0): returns 100.0.
        - Losses without gains (AvgLoss > 0 and AvgGain == 0): returns 0.0.
        - Defined values are strictly bounded within [0.0, 100.0].
        - Non-positive (<= 0) or NaN prices in the active window cause affected sessions to return None.
        - Point-in-time invariant: Calculation at session t depends solely on observations up to t.

    Args:
        prices: Chronological sequence of price observations (typically raw unadjusted close).
        period: Number of price change periods (default 14).

    Returns:
        List of RSI values (Optional[float]) matching length of input prices.
    """
    if period < 1:
        raise ValueError(f"RSI period must be >= 1, got {period}")

    n = len(prices)
    if n == 0:
        return []
    if n <= period:
        return [None] * n

    out: List[Optional[float]] = [None] * n

    valid_prices: List[Optional[float]] = []
    for p in prices:
        if p is None or math.isnan(p) or p <= 0.0:
            valid_prices.append(None)
        else:
            valid_prices.append(float(p))

    changes: List[Optional[float]] = []
    for i in range(1, n):
        p_prev = valid_prices[i - 1]
        p_curr = valid_prices[i]
        if p_prev is None or p_curr is None:
            changes.append(None)
        else:
            changes.append(p_curr - p_prev)

    def _compute_rsi(ag: float, al: float) -> float:
        if ag == 0.0 and al == 0.0:
            return 50.0
        denom = ag + al
        val = 100.0 * (ag / denom)
        return min(100.0, max(0.0, val))

    running_avg_gain: Optional[float] = None
    running_avg_loss: Optional[float] = None

    if all(c is not None for c in changes[:period]):
        gains = [max(c, 0.0) for c in changes[:period]]  # type: ignore
        losses = [max(-c, 0.0) for c in changes[:period]]  # type: ignore
        running_avg_gain = sum(gains) / period
        running_avg_loss = sum(losses) / period
        out[period] = _compute_rsi(running_avg_gain, running_avg_loss)

    for i in range(period, len(changes)):
        c = changes[i]
        idx = i + 1
        if c is None or running_avg_gain is None or running_avg_loss is None:
            if i >= period - 1 and all(ch is not None for ch in changes[i - period + 1 : i + 1]):
                window_changes = changes[i - period + 1 : i + 1]
                gains = [max(ch, 0.0) for ch in window_changes]  # type: ignore
                losses = [max(-ch, 0.0) for ch in window_changes]  # type: ignore
                running_avg_gain = sum(gains) / period
                running_avg_loss = sum(losses) / period
                out[idx] = _compute_rsi(running_avg_gain, running_avg_loss)
            else:
                running_avg_gain = None
                running_avg_loss = None
                out[idx] = None
        else:
            g = max(c, 0.0)
            l = max(-c, 0.0)
            running_avg_gain = (running_avg_gain * (period - 1) + g) / period
            running_avg_loss = (running_avg_loss * (period - 1) + l) / period
            out[idx] = _compute_rsi(running_avg_gain, running_avg_loss)

    return out


def calculate_macd(
    prices: Sequence[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> MACDSeries:
    """Compute Moving Average Convergence Divergence (MACD) technical indicator.

    MACD is a trend-following momentum indicator that shows the relationship between
    two exponential moving averages of a security's price.
    Note: MACD is an indicator of historical trend and momentum; it is NOT a
    guaranteed price-direction predictor.

    Mathematical Definitions:
        1. Fast EMA:
            EMA_{fast, t} = EMA(prices, window=fast_period)
        2. Slow EMA:
            EMA_{slow, t} = EMA(prices, window=slow_period)
        3. MACD Line:
            MACD_t = EMA_{fast, t} - EMA_{slow, t}
        4. Signal Line:
            Signal_t = EMA(MACD, window=signal_period)
        5. MACD Histogram:
            Histogram_t = MACD_t - Signal_t

    Warm-up & Initialization Policy:
        - All periods must be positive integers (>= 1).
        - fast_period must be strictly less than slow_period.
        - EMA uses recursive exponential weighting with multiplier alpha = 2 / (span + 1),
          adjust=False, seeded from the first valid observation.
        - MACD line requires slow_period valid observations to warm up (since slow_period > fast_period).
          For t < slow_period - 1: MACD line returns None.
        - Signal line is the signal_period EMA of the MACD line. It requires signal_period valid
          MACD line values before emitting its first output.
          For t < (slow_period - 1) + (signal_period - 1): Signal line returns None.
        - MACD histogram = MACD line - Signal line. When Signal line is None, Histogram returns None.
        - Insufficient historical observations or undefined intermediate values return None;
          no numbers are fabricated.
        - Point-in-time invariant: Calculation at session t strictly depends on observations up to t;
          altering future prices never changes past or current values.

    Args:
        prices: Chronological sequence of prices (typically raw unadjusted close).
        fast_period: Span for the fast exponential moving average (default 12).
        slow_period: Span for the slow exponential moving average (default 26).
        signal_period: Span for the signal-line exponential moving average (default 9).

    Returns:
        MACDSeries containing macd, signal, and histogram lists aligned with input prices.
    """
    for name, val in [("fast_period", fast_period), ("slow_period", slow_period), ("signal_period", signal_period)]:
        if not isinstance(val, int) or isinstance(val, bool):
            raise TypeError(f"{name} must be an integer, got {type(val).__name__}")
        if val < 1:
            raise ValueError(f"{name} must be >= 1, got {val}")

    if fast_period >= slow_period:
        raise ValueError(f"fast_period ({fast_period}) must be strictly less than slow_period ({slow_period})")

    n = len(prices)
    if n == 0:
        return MACDSeries(macd=[], signal=[], histogram=[])

    fast_ema = calculate_ema(prices, window=fast_period, min_periods=fast_period, adjust=False)
    slow_ema = calculate_ema(prices, window=slow_period, min_periods=slow_period, adjust=False)

    macd_vals: List[Optional[float]] = []
    for f, s in zip(fast_ema, slow_ema):
        if f is not None and s is not None:
            macd_vals.append(f - s)
        else:
            macd_vals.append(None)

    signal_vals = calculate_ema(
        macd_vals,
        window=signal_period,
        min_periods=signal_period,
        adjust=False,
        allow_negative=True,
    )

    hist_vals: List[Optional[float]] = []
    for m, sig in zip(macd_vals, signal_vals):
        if m is not None and sig is not None:
            hist_vals.append(m - sig)
        else:
            hist_vals.append(None)

    return MACDSeries(macd=macd_vals, signal=signal_vals, histogram=hist_vals)


def compute_moving_averages(
    records: Sequence[MarketOHLCV],
    sma_windows: Sequence[int] = (5, 10),
    ema_windows: Sequence[int] = (5, 10),
    min_periods_ema: Optional[int] = None,
    adjust_ema: bool = False,
    rsi_periods: Sequence[int] = (14,),
    macd_fast: Optional[int] = 12,
    macd_slow: Optional[int] = 26,
    macd_signal: Optional[int] = 9,
) -> List[MovingAverageFeatures]:
    """Compute moving average and momentum indicators across canonical MarketOHLCV records.

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
        rsi_periods: Periods to compute for RSI (default (14,)).
        macd_fast: Fast EMA period for MACD (default 12, or None to skip).
        macd_slow: Slow EMA period for MACD (default 26, or None to skip).
        macd_signal: Signal EMA period for MACD (default 9, or None to skip).

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

        # Compute RSIs
        rsi_results: Dict[int, List[Optional[float]]] = {}
        for p in rsi_periods:
            rsi_results[p] = calculate_rsi(prices, period=p)

        # Compute MACD
        if macd_fast is not None and macd_slow is not None and macd_signal is not None:
            macd_series = calculate_macd(
                prices,
                fast_period=macd_fast,
                slow_period=macd_slow,
                signal_period=macd_signal,
            )
        else:
            macd_series = MACDSeries(
                macd=[None] * len(sorted_bars),
                signal=[None] * len(sorted_bars),
                histogram=[None] * len(sorted_bars),
            )

        # Assemble per-bar feature records
        for i, bar in enumerate(sorted_bars):
            bar_smas = {w: sma_results[w][i] for w in sma_windows}
            bar_emas = {w: ema_results[w][i] for w in ema_windows}
            bar_rsi = {p: rsi_results[p][i] for p in rsi_periods}

            features = MovingAverageFeatures(
                symbol=bar.symbol,
                timestamp=bar.timestamp,
                close=bar.close,
                smas=bar_smas,
                emas=bar_emas,
                rsi=bar_rsi,
                macd=macd_series.macd[i],
                macd_signal=macd_series.signal[i],
                macd_histogram=macd_series.histogram[i],
            )
            all_features.append(features)

    return sorted(all_features, key=lambda f: (f.symbol, f.timestamp))


# Alias for comprehensive indicator computation
compute_technical_indicators = compute_moving_averages
