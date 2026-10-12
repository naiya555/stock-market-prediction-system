"""Technical Indicators Layer: Moving Averages, Oscillators, and Volatility Bands.

Provides deterministic, point-in-time calculation of Simple Moving Averages (SMA),
Exponential Moving Averages (EMA), Relative Strength Index (RSI),
Moving Average Convergence Divergence (MACD), and Bollinger Bands on cleaned
historical market data (MarketOHLCV).
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV
from app.market.candlestick import (
    CandlestickFeatures,
    calculate_candlestick_features,
    calculate_single_candlestick,
    compute_candlestick_features,
)

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
class BollingerBandsSeries:
    """Calculated Bollinger Bands technical indicator series.

    Encapsulates middle band, upper band, lower band, bandwidth, and percent_b.
    Implements sequence protocol for 5-tuple unpacking:
        middle, upper, lower, bandwidth, percent_b = calculate_bollinger_bands(prices)
    """

    middle: List[Optional[float]]
    upper: List[Optional[float]]
    lower: List[Optional[float]]
    bandwidth: List[Optional[float]]
    percent_b: List[Optional[float]]

    def __iter__(self):
        """Allow unpacking as (middle, upper, lower, bandwidth, percent_b)."""
        return iter((self.middle, self.upper, self.lower, self.bandwidth, self.percent_b))

    def __len__(self) -> int:
        """Return the length of the series."""
        return len(self.middle)

    @property
    def band_width(self) -> List[Optional[float]]:
        """Convenience alias for bandwidth."""
        return self.bandwidth


@dataclass(frozen=True)
class MovingAverageFeatures:
    """Canonical calculated technical indicator features for a single market bar.

    Encapsulates Simple Moving Averages (SMA), Exponential Moving Averages (EMA),
    Relative Strength Index (RSI), Moving Average Convergence Divergence (MACD),
    and Bollinger Bands.
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
    bb_middle: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_bandwidth: Optional[float] = None
    bb_percent_b: Optional[float] = None
    atr: Dict[int, Optional[float]] = field(default_factory=dict)
    roc: Dict[int, Optional[float]] = field(default_factory=dict)
    candle_body: Optional[float] = None
    candle_body_abs: Optional[float] = None
    candle_range: Optional[float] = None
    candle_upper_wick: Optional[float] = None
    candle_lower_wick: Optional[float] = None
    candle_body_ratio: Optional[float] = None
    candle_upper_wick_ratio: Optional[float] = None
    candle_lower_wick_ratio: Optional[float] = None
    candle_close_location: Optional[float] = None
    candle_body_return_pct: Optional[float] = None
    candle_direction: Optional[str] = None

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

    @property
    def bollinger_middle(self) -> Optional[float]:
        """Convenience property for Bollinger middle band."""
        return self.bb_middle

    @property
    def bollinger_upper(self) -> Optional[float]:
        """Convenience property for Bollinger upper band."""
        return self.bb_upper

    @property
    def bollinger_lower(self) -> Optional[float]:
        """Convenience property for Bollinger lower band."""
        return self.bb_lower

    @property
    def bollinger_bandwidth(self) -> Optional[float]:
        """Convenience property for Bollinger Band Width."""
        return self.bb_bandwidth

    @property
    def bollinger_band_width(self) -> Optional[float]:
        """Convenience alias for Bollinger Band Width."""
        return self.bb_bandwidth

    @property
    def bollinger_percent_b(self) -> Optional[float]:
        """Convenience property for Bollinger %B."""
        return self.bb_percent_b

    @property
    def atr_14(self) -> Optional[float]:
        """Convenience property for standard 14-session Average True Range."""
        return self.atr.get(14)

    @property
    def roc_10(self) -> Optional[float]:
        """Convenience property for standard 10-session Rate of Change."""
        return self.roc.get(10)

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
        out["bb_middle"] = self.bb_middle
        out["bb_upper"] = self.bb_upper
        out["bb_lower"] = self.bb_lower
        out["bb_bandwidth"] = self.bb_bandwidth
        out["bb_percent_b"] = self.bb_percent_b
        out["bollinger_middle"] = self.bb_middle
        out["bollinger_upper"] = self.bb_upper
        out["bollinger_lower"] = self.bb_lower
        out["bollinger_bandwidth"] = self.bb_bandwidth
        out["bollinger_percent_b"] = self.bb_percent_b
        for p, val in sorted(self.atr.items()):
            out[f"atr_{p}"] = val
        for p, val in sorted(self.roc.items()):
            out[f"roc_{p}"] = val
        out["candle_body"] = self.candle_body
        out["candle_body_abs"] = self.candle_body_abs
        out["candle_range"] = self.candle_range
        out["candle_upper_wick"] = self.candle_upper_wick
        out["candle_lower_wick"] = self.candle_lower_wick
        out["candle_body_ratio"] = self.candle_body_ratio
        out["candle_upper_wick_ratio"] = self.candle_upper_wick_ratio
        out["candle_lower_wick_ratio"] = self.candle_lower_wick_ratio
        out["candle_close_location"] = self.candle_close_location
        out["candle_body_return_pct"] = self.candle_body_return_pct
        out["candle_direction"] = self.candle_direction
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


def calculate_bollinger_bands(
    prices: Sequence[float],
    window: int = 20,
    multiplier: float = 2.0,
    num_std: Optional[float] = None,
    ddof: int = 0,
) -> BollingerBandsSeries:
    """Compute Bollinger Bands technical indicator over a sliding chronological window.

    Bollinger Bands are volatility bands placed above and below a moving average.
    Volatility is based on standard deviation, which changes as volatility increases or decreases.
    Note: Bollinger Bands provide a measure of relative price level and volatility;
    a band touch is NOT a guaranteed buy or sell signal.

    Mathematical Definitions:
        1. Middle Band:
            Middle_t = (1 / W) * sum_{i=0}^{W-1} P_{t-i} (Rolling SMA)
        2. Rolling Standard Deviation:
            sigma_t = sqrt( sum_{i=0}^{W-1} (P_{t-i} - Middle_t)^2 / (W - ddof) )
            Default ddof = 0 (population standard deviation, per John Bollinger's specification).
        3. Upper Band:
            Upper_t = Middle_t + multiplier * sigma_t
        4. Lower Band:
            Lower_t = Middle_t - multiplier * sigma_t
        5. Band Width:
            BandWidth_t = (Upper_t - Lower_t) / Middle_t, when Middle_t > 0
        6. Percent B (%B):
            PercentB_t = (P_t - Lower_t) / (Upper_t - Lower_t), when (Upper_t - Lower_t) > 0

    Warm-up & Edge-Case Rules:
        - window must be an integer >= 1.
        - multiplier must be positive and finite (> 0.0).
        - ddof must satisfy 0 <= ddof < window.
        - For t < window - 1: Insufficient history; all outputs return None.
        - Non-positive (<= 0) or NaN prices in the active window cause affected sessions to return None.
        - If Middle_t <= 0: Band Width returns None.
        - If (Upper_t - Lower_t) <= 0 (e.g. flat prices where sigma_t = 0): Percent B returns None
          (safely avoiding division by zero).
        - Point-in-time invariant: Calculation at session t depends strictly on observations up to t.

    Args:
        prices: Chronological sequence of prices (typically raw unadjusted close).
        window: Number of sessions in rolling window (default 20).
        multiplier: Standard deviation multiplier (default 2.0).
        num_std: Optional alias for multiplier.
        ddof: Delta degrees of freedom for standard deviation (default 0).

    Returns:
        BollingerBandsSeries containing middle, upper, lower, bandwidth, and percent_b lists.
    """
    mult = num_std if num_std is not None else multiplier

    if not isinstance(window, int) or isinstance(window, bool):
        raise TypeError(f"Bollinger Bands window must be an integer, got {type(window).__name__}")
    if window < 1:
        raise ValueError(f"Bollinger Bands window must be >= 1, got {window}")

    if not isinstance(mult, (int, float)) or isinstance(mult, bool):
        raise TypeError(f"Bollinger Bands multiplier must be a number, got {type(mult).__name__}")
    if math.isnan(mult) or math.isinf(mult) or mult <= 0.0:
        raise ValueError(f"Bollinger Bands multiplier must be positive and finite, got {mult}")

    if not isinstance(ddof, int) or isinstance(ddof, bool):
        raise TypeError(f"Bollinger Bands ddof must be an integer, got {type(ddof).__name__}")
    if ddof < 0 or ddof >= window:
        raise ValueError(f"Bollinger Bands ddof must satisfy 0 <= ddof < window ({window}), got {ddof}")

    n = len(prices)
    if n == 0:
        return BollingerBandsSeries(middle=[], upper=[], lower=[], bandwidth=[], percent_b=[])

    clean_vals: List[float] = []
    has_invalid = False
    for p in prices:
        if p is None or math.isnan(p) or p <= 0.0:
            clean_vals.append(float("nan"))
            has_invalid = True
        else:
            clean_vals.append(float(p))

    if has_invalid:
        logger.warning("Encountered non-positive or NaN prices in Bollinger Bands series; masking affected windows.")

    series = pd.Series(clean_vals, dtype="float64")
    rolling = series.rolling(window=window, min_periods=window)
    mean_series = rolling.mean()
    std_series = rolling.std(ddof=ddof)

    middle_list: List[Optional[float]] = []
    upper_list: List[Optional[float]] = []
    lower_list: List[Optional[float]] = []
    bw_list: List[Optional[float]] = []
    pct_b_list: List[Optional[float]] = []

    for i in range(n):
        m = mean_series.iloc[i]
        s = std_series.iloc[i]
        p = clean_vals[i]

        if math.isnan(m) or math.isnan(s):
            middle_list.append(None)
            upper_list.append(None)
            lower_list.append(None)
            bw_list.append(None)
            pct_b_list.append(None)
        else:
            m_val = float(m)
            s_val = float(s)
            u_val = m_val + mult * s_val
            l_val = m_val - mult * s_val

            middle_list.append(m_val)
            upper_list.append(u_val)
            lower_list.append(l_val)

            # Band width = (upper - lower) / middle
            if m_val > 0.0:
                bw_list.append((u_val - l_val) / m_val)
            else:
                bw_list.append(None)

            # Percent B = (close - lower) / (upper - lower)
            denom = u_val - l_val
            if denom > 0.0 and not math.isnan(p):
                pct_b_list.append((p - l_val) / denom)
            else:
                pct_b_list.append(None)

    return BollingerBandsSeries(
        middle=middle_list,
        upper=upper_list,
        lower=lower_list,
        bandwidth=bw_list,
        percent_b=pct_b_list,
    )


def calculate_true_range(
    high: Any,
    low: Optional[Sequence[float]] = None,
    close: Optional[Sequence[float]] = None,
) -> List[Optional[float]]:
    """Compute True Range (TR) across chronological price sessions.

    Mathematical Definition:
        For session t = 0 (first session, no previous close):
            TR_0 = High_0 - Low_0
        For session t >= 1:
            TR_t = max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|)

    Args:
        high: Sequence of high prices, or Sequence of MarketOHLCV records.
        low: Sequence of low prices (required if high is float sequence).
        close: Sequence of closing prices (required if high is float sequence).

    Returns:
        List of True Range values, where invalid, missing, or unphysical sessions yield None.
    """
    if low is None and close is None:
        records = list(high)
        if len(records) == 0:
            return []
        h_vals = [getattr(r, "high", None) for r in records]
        l_vals = [getattr(r, "low", None) for r in records]
        c_vals = [getattr(r, "close", None) for r in records]
    else:
        if low is None or close is None:
            raise ValueError("Both low and close must be provided when high is a numeric sequence")
        h_vals = list(high)
        l_vals = list(low)
        c_vals = list(close)

    n = len(h_vals)
    if len(l_vals) != n or len(c_vals) != n:
        raise ValueError(
            f"Input sequences must have identical lengths: high={n}, low={len(l_vals)}, close={len(c_vals)}"
        )
    if n == 0:
        return []

    tr_list: List[Optional[float]] = []
    for t in range(n):
        h = h_vals[t]
        l = l_vals[t]

        if (
            h is None
            or l is None
            or not isinstance(h, (int, float))
            or not isinstance(l, (int, float))
            or isinstance(h, bool)
            or isinstance(l, bool)
            or not math.isfinite(h)
            or not math.isfinite(l)
            or h <= 0.0
            or l <= 0.0
            or h < l
        ):
            tr_list.append(None)
            continue

        if t == 0:
            # First session initialization policy: High - Low
            tr_list.append(float(h - l))
        else:
            prev_c = c_vals[t - 1]
            if (
                prev_c is None
                or not isinstance(prev_c, (int, float))
                or isinstance(prev_c, bool)
                or not math.isfinite(prev_c)
                or prev_c <= 0.0
            ):
                tr_list.append(None)
                continue

            hl = float(h - l)
            hc = float(abs(h - prev_c))
            lc = float(abs(l - prev_c))
            tr_list.append(max(hl, hc, lc))

    return tr_list


def calculate_atr(
    high: Any,
    low: Optional[Sequence[float]] = None,
    close: Optional[Sequence[float]] = None,
    period: int = 14,
) -> List[Optional[float]]:
    """Compute Average True Range (ATR) using Wilder's smoothing method.

    Mathematical Definition:
        Initial ATR at session t = period - 1:
            ATR_{period-1} = (1 / period) * sum_{i=0}^{period-1} TR_i
        Subsequent sessions t >= period:
            ATR_t = ((period - 1) * ATR_{t-1} + TR_t) / period

    Args:
        high: Sequence of high prices, or Sequence of MarketOHLCV records.
        low: Sequence of low prices (required if high is float sequence).
        close: Sequence of closing prices (required if high is float sequence).
        period: Rolling session window (default 14, must be positive integer >= 1).

    Returns:
        List of smoothed ATR values, where un-warmed sessions (t < period - 1)
        or sessions with invalid data evaluate strictly to None.
    """
    if not isinstance(period, int) or isinstance(period, bool):
        raise TypeError(f"period must be an integer, got {type(period).__name__}")
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")

    tr_list = calculate_true_range(high, low, close)
    n = len(tr_list)
    if n == 0:
        return []

    atr_list: List[Optional[float]] = []
    prev_atr: Optional[float] = None

    for t in range(n):
        if t < period - 1:
            atr_list.append(None)
        elif t == period - 1:
            # Seed with simple arithmetic mean of the first 'period' True Ranges
            window_tr = tr_list[0:period]
            if any(val is None for val in window_tr):
                atr_list.append(None)
                prev_atr = None
            else:
                first_atr = sum(val for val in window_tr if val is not None) / float(period)
                atr_list.append(first_atr)
                prev_atr = first_atr
        else:
            tr_val = tr_list[t]
            if prev_atr is not None and tr_val is not None:
                curr_atr = ((period - 1) * prev_atr + tr_val) / float(period)
                atr_list.append(curr_atr)
                prev_atr = curr_atr
            else:
                atr_list.append(None)
                prev_atr = None

    return atr_list


def calculate_roc(
    prices: Any,
    period: int = 10,
    lookback: Optional[int] = None,
) -> List[Optional[float]]:
    """Compute Price Rate of Change (ROC) over a sliding chronological lookback.

    Mathematical Definition:
        ROC_{t, n} = ((Close_t / Close_{t-n}) - 1) * 100

    Args:
        prices: Sequence of closing prices, or Sequence of MarketOHLCV records.
        period: Number of historical sessions to look back (default 10).
        lookback: Optional alias for period.

    Returns:
        List of ROC percentage values, where un-warmed sessions (t < n)
        or sessions with missing/non-positive prices evaluate strictly to None.
    """
    if lookback is not None:
        period = lookback

    if not isinstance(period, int) or isinstance(period, bool):
        raise TypeError(f"period must be an integer, got {type(period).__name__}")
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")

    p_vals: List[Any]
    if len(prices) > 0 and hasattr(prices[0], "close"):
        p_vals = [r.close for r in prices]
    else:
        p_vals = list(prices)

    n = len(p_vals)
    if n == 0:
        return []

    roc_list: List[Optional[float]] = []
    for t in range(n):
        if t < period:
            roc_list.append(None)
            continue

        curr_p = p_vals[t]
        prev_p = p_vals[t - period]

        if (
            curr_p is None
            or prev_p is None
            or isinstance(curr_p, bool)
            or isinstance(prev_p, bool)
            or not isinstance(curr_p, (int, float))
            or not isinstance(prev_p, (int, float))
            or not math.isfinite(curr_p)
            or not math.isfinite(prev_p)
            or curr_p <= 0.0
            or prev_p <= 0.0
        ):
            roc_list.append(None)
            continue

        roc_val = ((float(curr_p) / float(prev_p)) - 1.0) * 100.0
        roc_list.append(roc_val)

    return roc_list


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
    bb_window: Optional[int] = 20,
    bb_multiplier: Optional[float] = 2.0,
    bb_ddof: int = 0,
    atr_periods: Sequence[int] = (14,),
    roc_periods: Sequence[int] = (10,),
) -> List[MovingAverageFeatures]:
    """Compute moving average, momentum, and volatility indicators across canonical MarketOHLCV records.

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
        bb_window: Rolling window for Bollinger Bands (default 20, or None to skip).
        bb_multiplier: Standard deviation multiplier for Bollinger Bands (default 2.0).
        bb_ddof: Degrees of freedom for Bollinger standard deviation (default 0).
        atr_periods: Periods to compute for Average True Range (default (14,)).
        roc_periods: Lookbacks to compute for Rate of Change (default (10,)).

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
        highs = [b.high for b in sorted_bars]
        lows = [b.low for b in sorted_bars]

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

        # Compute Bollinger Bands
        if bb_window is not None and bb_multiplier is not None:
            bb_series = calculate_bollinger_bands(
                prices,
                window=bb_window,
                multiplier=bb_multiplier,
                ddof=bb_ddof,
            )
        else:
            bb_series = BollingerBandsSeries(
                middle=[None] * len(sorted_bars),
                upper=[None] * len(sorted_bars),
                lower=[None] * len(sorted_bars),
                bandwidth=[None] * len(sorted_bars),
                percent_b=[None] * len(sorted_bars),
            )

        # Compute ATRs
        atr_results: Dict[int, List[Optional[float]]] = {}
        for p in atr_periods:
            atr_results[p] = calculate_atr(highs, lows, prices, period=p)

        # Compute ROCs
        roc_results: Dict[int, List[Optional[float]]] = {}
        for p in roc_periods:
            roc_results[p] = calculate_roc(prices, period=p)

        # Compute Candlestick Features
        candle_features = calculate_candlestick_features(sorted_bars)

        # Assemble per-bar feature records
        for i, bar in enumerate(sorted_bars):
            bar_smas = {w: sma_results[w][i] for w in sma_windows}
            bar_emas = {w: ema_results[w][i] for w in ema_windows}
            bar_rsi = {p: rsi_results[p][i] for p in rsi_periods}
            bar_atr = {p: atr_results[p][i] for p in atr_periods}
            bar_roc = {p: roc_results[p][i] for p in roc_periods}
            c_feat = candle_features[i]

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
                bb_middle=bb_series.middle[i],
                bb_upper=bb_series.upper[i],
                bb_lower=bb_series.lower[i],
                bb_bandwidth=bb_series.bandwidth[i],
                bb_percent_b=bb_series.percent_b[i],
                atr=bar_atr,
                roc=bar_roc,
                candle_body=c_feat.candle_body,
                candle_body_abs=c_feat.candle_body_abs,
                candle_range=c_feat.candle_range,
                candle_upper_wick=c_feat.candle_upper_wick,
                candle_lower_wick=c_feat.candle_lower_wick,
                candle_body_ratio=c_feat.candle_body_ratio,
                candle_upper_wick_ratio=c_feat.candle_upper_wick_ratio,
                candle_lower_wick_ratio=c_feat.candle_lower_wick_ratio,
                candle_close_location=c_feat.candle_close_location,
                candle_body_return_pct=c_feat.candle_body_return_pct,
                candle_direction=c_feat.candle_direction,
            )
            all_features.append(features)

    return sorted(all_features, key=lambda f: (f.symbol, f.timestamp))


# Alias for comprehensive indicator computation
compute_technical_indicators = compute_moving_averages
