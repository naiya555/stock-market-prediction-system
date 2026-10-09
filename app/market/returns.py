"""Returns and Volatility Feature Engineering Layer.

Provides deterministic, point-in-time calculation of daily percentage returns,
multi-window rolling returns, sample standard deviations, and rolling realized
volatilities on cleaned historical market data (MarketOHLCV).
"""

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Sequence

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV

logger = get_logger(__name__)


@dataclass(frozen=True)
class ReturnFeatures:
    """Canonical calculated return and volatility features for a single market bar."""

    symbol: str
    timestamp: datetime
    close: float
    daily_return: Optional[float]
    rolling_returns: Dict[int, Optional[float]]
    rolling_volatilities: Dict[int, Optional[float]]
    annualized_volatilities: Dict[int, Optional[float]]

    @property
    def rolling_return_3d(self) -> Optional[float]:
        """Convenience property for 3-session rolling return."""
        return self.rolling_returns.get(3)

    @property
    def rolling_return_5d(self) -> Optional[float]:
        """Convenience property for 5-session rolling return."""
        return self.rolling_returns.get(5)

    @property
    def volatility_5d(self) -> Optional[float]:
        """Convenience property for 5-session raw rolling volatility."""
        return self.rolling_volatilities.get(5)

    @property
    def annualized_volatility_5d(self) -> Optional[float]:
        """Convenience property for 5-session annualized rolling volatility."""
        return self.annualized_volatilities.get(5)

    def to_dict(self) -> Dict[str, Any]:
        """Convert feature record to flat dictionary for tabular and ML pipelines."""
        out: Dict[str, Any] = {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "close": self.close,
            "daily_return": self.daily_return,
        }
        for w, val in sorted(self.rolling_returns.items()):
            out[f"rolling_return_{w}d"] = val
        for w, val in sorted(self.rolling_volatilities.items()):
            out[f"rolling_volatility_{w}d"] = val
        for w, val in sorted(self.annualized_volatilities.items()):
            out[f"annualized_volatility_{w}d"] = val
        return out


def calculate_daily_returns(prices: Sequence[float]) -> List[Optional[float]]:
    """Compute daily simple percentage returns from a chronological price series.

    Convention:
        R_t = (P_t / P_{t-1}) - 1 = (P_t - P_{t-1}) / P_{t-1}

    Rules:
        - The first observation (t=0) has no previous close; returns None.
        - If previous price P_{t-1} <= 0 or current price P_t <= 0, returns None
          (prevents division by zero, negative base distortions, or infinite values).
        - No future prices are used (strictly point-in-time).

    Args:
        prices: Chronological sequence of close prices.

    Returns:
        List of daily percentage returns, aligned 1:1 with input prices.
    """
    n = len(prices)
    if n == 0:
        return []

    returns: List[Optional[float]] = [None] * n
    for t in range(1, n):
        prev = prices[t - 1]
        curr = prices[t]
        if prev <= 0.0 or curr <= 0.0 or math.isnan(prev) or math.isnan(curr):
            logger.warning(
                "Invalid price encountered at index %d (prev=%s, curr=%s); marking return as None",
                t,
                prev,
                curr,
            )
            returns[t] = None
        else:
            returns[t] = (curr / prev) - 1.0

    return returns


def calculate_rolling_returns(
    prices: Sequence[float],
    window: int,
) -> List[Optional[float]]:
    """Compute multi-session cumulative simple returns over a rolling window.

    Convention:
        R_{t, w} = (P_t / P_{t-w}) - 1

    Rules:
        - For t < window: Insufficient historical sessions; returns None.
        - For t >= window: Uses only current price P_t and historical price P_{t-w}.
        - If historical price P_{t-w} <= 0 or current price P_t <= 0, returns None.
        - Zero future observations enter the calculation.

    Args:
        prices: Chronological sequence of close prices.
        window: Number of elapsed trading sessions (must be >= 1).

    Returns:
        List of rolling returns of the same length as prices.
    """
    if window < 1:
        raise ValueError(f"Rolling return window must be >= 1, got {window}")

    n = len(prices)
    if n == 0:
        return []

    rolling: List[Optional[float]] = [None] * n
    for t in range(window, n):
        base = prices[t - window]
        curr = prices[t]
        if base <= 0.0 or curr <= 0.0 or math.isnan(base) or math.isnan(curr):
            rolling[t] = None
        else:
            rolling[t] = (curr / base) - 1.0

    return rolling


def calculate_standard_deviation(
    values: Sequence[float],
    ddof: int = 1,
) -> Optional[float]:
    """Compute sample standard deviation for a numeric sequence with explicit ddof.

    Formula:
        mean = sum(x) / N
        variance = sum((x - mean)^2) / (N - ddof)
        stdev = sqrt(variance)

    Rules:
        - Requires len(values) > ddof (e.g., at least 2 observations for ddof=1).
        - If any value is NaN, returns None.
        - Returns 0.0 if all values are identical.

    Args:
        values: Sequence of numeric values.
        ddof: Delta degrees of freedom (default 1 for sample standard deviation).

    Returns:
        Standard deviation as float, or None if insufficient observations.
    """
    n = len(values)
    if n <= ddof:
        return None

    for val in values:
        if math.isnan(val):
            return None

    mean_val = sum(values) / n
    sum_sq_diff = sum((x - mean_val) ** 2 for x in values)
    variance = sum_sq_diff / (n - ddof)
    return math.sqrt(max(0.0, variance))


def calculate_rolling_volatility(
    daily_returns: Sequence[Optional[float]],
    window: int,
    ddof: int = 1,
    annualized: bool = False,
    trading_days: int = 252,
) -> List[Optional[float]]:
    """Compute rolling realized volatility from a daily return series.

    Convention:
        - At session t, the window spans daily returns [t - window + 1 ... t].
        - A window requires exactly `window` valid daily returns. If any return
          in the window is None or NaN (such as the initial None return at t=0),
          or if t < window, the volatility for that session is None.
        - Raw volatility is the sample standard deviation (ddof=1) of daily returns.
        - Annualized volatility scales raw daily volatility by sqrt(trading_days)
          (standard 252 sessions for Indian equity markets).

    Args:
        daily_returns: Daily return series (aligned 1:1 with market bars).
        window: Number of daily return observations in rolling window (>= 2).
        ddof: Degrees of freedom for sample standard deviation (default 1).
        annualized: Whether to annualize by sqrt(trading_days).
        trading_days: Number of trading sessions per year (default 252).

    Returns:
        List of rolling volatilities of same length as daily_returns.
    """
    if window < 2:
        raise ValueError(f"Rolling volatility window must be >= 2, got {window}")

    n = len(daily_returns)
    if n == 0:
        return []

    volatilities: List[Optional[float]] = [None] * n
    annual_factor = math.sqrt(trading_days) if annualized else 1.0

    for t in range(n):
        start_idx = t - window + 1
        if start_idx < 0:
            volatilities[t] = None
            continue

        window_slice = daily_returns[start_idx : t + 1]
        # Verify all returns in window are present
        if any(r is None or math.isnan(r) for r in window_slice):
            volatilities[t] = None
            continue

        valid_vals = [r for r in window_slice if r is not None]
        stdev = calculate_standard_deviation(valid_vals, ddof=ddof)
        if stdev is None:
            volatilities[t] = None
        else:
            volatilities[t] = stdev * annual_factor

    return volatilities


def compute_market_returns(
    records: Sequence[MarketOHLCV],
    rolling_return_windows: Sequence[int] = (3, 5),
    volatility_windows: Sequence[int] = (5,),
    trading_days: int = 252,
) -> List[ReturnFeatures]:
    """Compute complete return and volatility feature layer on cleaned market bars.

    Guarantees:
        - Multi-symbol grouping: Calculations are isolated per symbol.
        - Chronological ordering: Bars are strictly sorted by timestamp ascending
          prior to calculations.
        - Strict point-in-time: No future rows or lookahead leakage.
        - Consistent price basis: Uses raw unadjusted close prices from canonical MarketOHLCV.
        - Unavailable initial values are represented as None (zero forward-filling or fabrication).

    Args:
        records: Sequence of cleaned MarketOHLCV records.
        rolling_return_windows: Session window sizes for rolling returns (default (3, 5)).
        volatility_windows: Session window sizes for rolling volatility (default (5,)).
        trading_days: Annual trading days convention for Indian markets (default 252).

    Returns:
        List of ReturnFeatures chronologically sorted and aligned with input bars.
    """
    if not records:
        return []

    # Group by symbol to support multi-symbol sequences without cross-ticker leakage
    grouped: Dict[str, List[MarketOHLCV]] = defaultdict(list)
    for rec in records:
        grouped[rec.symbol].append(rec)

    all_features: List[ReturnFeatures] = []

    for sym, sym_records in sorted(grouped.items(), key=lambda x: x[0]):
        # Enforce chronological ascending sort by timestamp
        sorted_bars = sorted(sym_records, key=lambda b: b.timestamp)
        prices = [b.close for b in sorted_bars]

        # 1. Daily returns
        daily_rets = calculate_daily_returns(prices)

        # 2. Rolling returns
        rolling_rets: Dict[int, List[Optional[float]]] = {}
        for w in rolling_return_windows:
            rolling_rets[w] = calculate_rolling_returns(prices, window=w)

        # 3. Rolling volatilities (raw and annualized)
        rolling_vols: Dict[int, List[Optional[float]]] = {}
        annual_vols: Dict[int, List[Optional[float]]] = {}
        for w in volatility_windows:
            rolling_vols[w] = calculate_rolling_volatility(
                daily_rets,
                window=w,
                ddof=1,
                annualized=False,
                trading_days=trading_days,
            )
            annual_vols[w] = calculate_rolling_volatility(
                daily_rets,
                window=w,
                ddof=1,
                annualized=True,
                trading_days=trading_days,
            )

        # 4. Assemble canonical ReturnFeatures records
        for i, bar in enumerate(sorted_bars):
            bar_rolling_ret = {w: rolling_rets[w][i] for w in rolling_return_windows}
            bar_rolling_vol = {w: rolling_vols[w][i] for w in volatility_windows}
            bar_annual_vol = {w: annual_vols[w][i] for w in volatility_windows}

            features = ReturnFeatures(
                symbol=bar.symbol,
                timestamp=bar.timestamp,
                close=bar.close,
                daily_return=daily_rets[i],
                rolling_returns=bar_rolling_ret,
                rolling_volatilities=bar_rolling_vol,
                annualized_volatilities=bar_annual_vol,
            )
            all_features.append(features)

    # Return final features sorted by (symbol, timestamp)
    return sorted(all_features, key=lambda f: (f.symbol, f.timestamp))
