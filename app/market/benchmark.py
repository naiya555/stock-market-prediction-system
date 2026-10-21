"""Benchmark and Sector Market Context Engine.

Provides deterministic, point-in-time calculation of:
- Benchmark index data normalization and session alignment.
- Relative performance features (daily alpha / excess return, relative strength ratio,
  relative strength momentum at 5d/20d windows).
- Rolling beta and rolling correlation against broad market (NIFTY 50) and sectoral benchmarks.
- Cross-sectional market breadth metrics (advances, declines, unchanged, advance-decline ratio,
  breadth thrust, net advances, moving average breadth participation).
"""

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV
from app.market.indicators import calculate_sma
from app.market.returns import calculate_daily_returns, calculate_standard_deviation

logger = get_logger(__name__)

# Standard Benchmark Symbols for Indian Equities
BROAD_MARKET_BENCHMARK = "^NSEI"  # NIFTY 50
BANKING_BENCHMARK = "^NSEBANK"  # NIFTY Bank
IT_BENCHMARK = "^CNXIT"  # NIFTY IT
TELECOM_BENCHMARK = "NIFTY_TELECOMMUNICATIONS"  # NIFTY Telecommunications

SECTOR_BENCHMARK_MAP: Dict[str, str] = {
    "BROAD": BROAD_MARKET_BENCHMARK,
    "NIFTY": BROAD_MARKET_BENCHMARK,
    "NIFTY50": BROAD_MARKET_BENCHMARK,
    "BANK": BANKING_BENCHMARK,
    "BANKING": BANKING_BENCHMARK,
    "FINANCIAL_SERVICES": BANKING_BENCHMARK,
    "FINANCE": BANKING_BENCHMARK,
    "IT": IT_BENCHMARK,
    "TECH": IT_BENCHMARK,
    "INFORMATION_TECHNOLOGY": IT_BENCHMARK,
    "TELECOM": TELECOM_BENCHMARK,
    "TELECOMMUNICATIONS": TELECOM_BENCHMARK,
    "NIFTY_TELECOM": TELECOM_BENCHMARK,
    "NIFTY_TELECOMMUNICATIONS": TELECOM_BENCHMARK,
}


def get_sector_benchmark(sector_or_alias: str) -> str:
    """Resolve sector identifier or alias to canonical Yahoo Finance benchmark ticker.

    Defaults to NIFTY 50 (^NSEI) if sector alias is unrecognized.
    """
    clean = sector_or_alias.strip().upper().replace(" ", "_")
    return SECTOR_BENCHMARK_MAP.get(clean, BROAD_MARKET_BENCHMARK)


@dataclass(frozen=True)
class RelativePerformanceFeature:
    """Canonical relative performance and benchmark context features for a single session."""

    symbol: str
    benchmark_symbol: str
    timestamp: datetime
    stock_close: float
    benchmark_close: Optional[float]
    stock_daily_return: Optional[float]
    benchmark_daily_return: Optional[float]
    relative_return: Optional[float]  # Excess return / alpha (R_stock - R_benchmark)
    relative_strength: Optional[float]  # Ratio: stock_close / benchmark_close
    relative_strength_momentum_5d: Optional[float]  # (RS_t / RS_{t-5}) - 1
    relative_strength_momentum_20d: Optional[float]  # (RS_t / RS_{t-20}) - 1
    rolling_beta_20d: Optional[float]  # Cov(R_s, R_b) / Var(R_b)
    rolling_correlation_20d: Optional[float]  # Cov(R_s, R_b) / (Std(R_s) * Std(R_b))

    def to_dict(self) -> Dict[str, Any]:
        """Convert feature record to flat dictionary for ML pipelines and logging."""
        return {
            "symbol": self.symbol,
            "benchmark_symbol": self.benchmark_symbol,
            "timestamp": self.timestamp.isoformat(),
            "stock_close": self.stock_close,
            "benchmark_close": self.benchmark_close,
            "stock_daily_return": self.relative_return_round(self.stock_daily_return),
            "benchmark_daily_return": self.relative_return_round(self.benchmark_daily_return),
            "relative_return": self.relative_return_round(self.relative_return),
            "relative_strength": self.relative_return_round(self.relative_strength, decimals=6),
            "relative_strength_momentum_5d": self.relative_return_round(self.relative_strength_momentum_5d),
            "relative_strength_momentum_20d": self.relative_return_round(self.relative_strength_momentum_20d),
            "rolling_beta_20d": self.relative_return_round(self.rolling_beta_20d),
            "rolling_correlation_20d": self.relative_return_round(self.rolling_correlation_20d),
        }

    @staticmethod
    def relative_return_round(val: Optional[float], decimals: int = 6) -> Optional[float]:
        """Safely round optional float value."""
        return round(val, decimals) if val is not None else None


@dataclass(frozen=True)
class MarketBreadthObservation:
    """Cross-sectional market breadth summary for a single trading session."""

    timestamp: datetime
    total_stocks: int
    advances: int
    declines: int
    unchanged: int
    advance_decline_ratio: Optional[float]  # advances / declines (None if declines == 0)
    breadth_thrust: Optional[float]  # advances / total_stocks
    net_advances: int  # advances - declines
    pct_above_sma20: Optional[float]  # Fraction of stocks trading above their 20-day SMA

    def to_dict(self) -> Dict[str, Any]:
        """Convert observation to flat dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_stocks": self.total_stocks,
            "advances": self.advances,
            "declines": self.declines,
            "unchanged": self.unchanged,
            "advance_decline_ratio": round(self.advance_decline_ratio, 4) if self.advance_decline_ratio is not None else None,
            "breadth_thrust": round(self.breadth_thrust, 4) if self.breadth_thrust is not None else None,
            "net_advances": self.net_advances,
            "pct_above_sma20": round(self.pct_above_sma20, 4) if self.pct_above_sma20 is not None else None,
        }


def compute_covariance(
    x: Sequence[float],
    y: Sequence[float],
    ddof: int = 1,
) -> Optional[float]:
    """Compute sample covariance between two equal-length numeric sequences.

    Formula:
        mean_x = sum(x) / N
        mean_y = sum(y) / N
        cov = sum((x_i - mean_x) * (y_i - mean_y)) / (N - ddof)

    Returns:
        Sample covariance, or None if len(x) <= ddof or any value is NaN.
    """
    n = len(x)
    if n != len(y) or n <= ddof:
        return None

    for val in x:
        if math.isnan(val):
            return None
    for val in y:
        if math.isnan(val):
            return None

    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / (n - ddof)
    return cov


def align_benchmark_series(
    stock_bars: Sequence[MarketOHLCV],
    benchmark_bars: Sequence[MarketOHLCV],
) -> List[Tuple[MarketOHLCV, Optional[MarketOHLCV]]]:
    """Strict point-in-time alignment of stock bars with benchmark bars.

    Matches each stock session strictly to the benchmark session sharing the exact
    calendar date (bar.timestamp.date()). If no benchmark bar exists on that date
    (e.g., market holiday discrepancy or halted trading), pairs with None.

    Guarantees zero look-ahead bias: future benchmark observations are never accessed.

    Args:
        stock_bars: Chronologically sorted stock OHLCV bars.
        benchmark_bars: Chronologically sorted benchmark index OHLCV bars.

    Returns:
        List of (stock_bar, paired_benchmark_bar_or_none) aligned 1:1 with stock_bars.
    """
    # Build fast lookup by date for benchmark
    bench_by_date: Dict[date, MarketOHLCV] = {
        b.timestamp.date(): b for b in benchmark_bars
    }

    aligned: List[Tuple[MarketOHLCV, Optional[MarketOHLCV]]] = []
    for s_bar in stock_bars:
        s_date = s_bar.timestamp.date()
        b_bar = bench_by_date.get(s_date)
        aligned.append((s_bar, b_bar))

    return aligned


def compute_relative_performance(
    stock_bars: Sequence[MarketOHLCV],
    benchmark_bars: Sequence[MarketOHLCV],
    beta_window: int = 20,
    min_periods: int = 10,
) -> List[RelativePerformanceFeature]:
    """Compute point-in-time relative performance and risk metrics against a benchmark.

    Calculates:
    - Relative Return (Alpha): R_{stock, t} - R_{bench, t}
    - Relative Strength Ratio: Close_{stock, t} / Close_{bench, t}
    - Relative Strength Momentum: (RS_t / RS_{t-w}) - 1 for w in [5, 20]
    - Rolling Beta: Cov(R_s, R_b) / Var(R_b) over rolling window
    - Rolling Correlation: Cov(R_s, R_b) / (Std(R_s) * Std(R_b))

    Rules & Invariants:
    - Strictly point-in-time: observation at t uses only sessions <= t.
    - If benchmark bar is missing on session t, relative metrics evaluate to None.
    - Zero variance guards: if Var(R_b) < 1e-12, beta evaluates to None.
    - If either series has zero variance or insufficient observations (< min_periods),
      correlation evaluates to None.
    - Correlation is bounded to [-1.0, 1.0].

    Args:
        stock_bars: Chronological stock OHLCV records.
        benchmark_bars: Chronological benchmark OHLCV records.
        beta_window: Window size for rolling beta and correlation (default 20).
        min_periods: Minimum valid paired return observations required in window (default 10).

    Returns:
        List of RelativePerformanceFeature records aligned 1:1 with stock_bars.
    """
    if not stock_bars:
        return []

    symbol = stock_bars[0].symbol
    bench_symbol = benchmark_bars[0].symbol if benchmark_bars else "BENCHMARK"

    # 1. Align series strictly on session date
    aligned = align_benchmark_series(stock_bars, benchmark_bars)
    n = len(aligned)

    # 2. Extract price sequences
    stock_prices = [s.close for s, _ in aligned]
    bench_prices: List[Optional[float]] = [b.close if b is not None else None for _, b in aligned]

    # 3. Compute daily returns independently
    stock_returns = calculate_daily_returns(stock_prices)

    # Compute benchmark daily returns where available
    bench_returns: List[Optional[float]] = [None] * n
    for t in range(1, n):
        prev_b = bench_prices[t - 1]
        curr_b = bench_prices[t]
        if prev_b is not None and curr_b is not None and prev_b > 0.0 and curr_b > 0.0:
            bench_returns[t] = (curr_b / prev_b) - 1.0
        else:
            bench_returns[t] = None

    # 4. Compute Relative Strength Ratios
    rs_ratios: List[Optional[float]] = [None] * n
    for t in range(n):
        s_close = stock_prices[t]
        b_close = bench_prices[t]
        if b_close is not None and b_close > 0.0 and s_close > 0.0:
            rs_ratios[t] = s_close / b_close
        else:
            rs_ratios[t] = None

    # 5. Compute features session by session
    features: List[RelativePerformanceFeature] = []

    for t in range(n):
        s_bar, b_bar = aligned[t]
        s_close = stock_prices[t]
        b_close = bench_prices[t]
        s_ret = stock_returns[t]
        b_ret = bench_returns[t]

        # Relative return (alpha)
        if s_ret is not None and b_ret is not None:
            rel_ret = s_ret - b_ret
        else:
            rel_ret = None

        rs_curr = rs_ratios[t]

        # 5d RS Momentum
        rs_mom_5d: Optional[float] = None
        if t >= 5 and rs_curr is not None:
            rs_5d_prev = rs_ratios[t - 5]
            if rs_5d_prev is not None and rs_5d_prev > 0.0:
                rs_mom_5d = (rs_curr / rs_5d_prev) - 1.0

        # 20d RS Momentum
        rs_mom_20d: Optional[float] = None
        if t >= 20 and rs_curr is not None:
            rs_20d_prev = rs_ratios[t - 20]
            if rs_20d_prev is not None and rs_20d_prev > 0.0:
                rs_mom_20d = (rs_curr / rs_20d_prev) - 1.0

        # Rolling Beta and Correlation over beta_window
        rolling_beta: Optional[float] = None
        rolling_corr: Optional[float] = None

        if t >= min_periods:
            start_idx = max(0, t - beta_window + 1)
            paired_s: List[float] = []
            paired_b: List[float] = []
            for k in range(start_idx, t + 1):
                r_s = stock_returns[k]
                r_b = bench_returns[k]
                if r_s is not None and r_b is not None:
                    paired_s.append(r_s)
                    paired_b.append(r_b)

            if len(paired_s) >= min_periods:
                cov = compute_covariance(paired_s, paired_b, ddof=1)
                std_s = calculate_standard_deviation(paired_s, ddof=1)
                std_b = calculate_standard_deviation(paired_b, ddof=1)

                if cov is not None and std_b is not None and std_b > 1e-6:
                    var_b = std_b * std_b
                    rolling_beta = cov / var_b

                if cov is not None and std_s is not None and std_b is not None:
                    denom = std_s * std_b
                    if denom > 1e-12:
                        raw_corr = cov / denom
                        rolling_corr = max(-1.0, min(1.0, raw_corr))

        features.append(
            RelativePerformanceFeature(
                symbol=symbol,
                benchmark_symbol=bench_symbol,
                timestamp=s_bar.timestamp,
                stock_close=s_close,
                benchmark_close=b_close,
                stock_daily_return=s_ret,
                benchmark_daily_return=b_ret,
                relative_return=rel_ret,
                relative_strength=rs_curr,
                relative_strength_momentum_5d=rs_mom_5d,
                relative_strength_momentum_20d=rs_mom_20d,
                rolling_beta_20d=rolling_beta,
                rolling_correlation_20d=rolling_corr,
            )
        )

    return features


def compute_market_breadth(
    timestamp: datetime,
    stock_returns: Dict[str, Optional[float]],
    stock_sma_status: Optional[Dict[str, bool]] = None,
) -> MarketBreadthObservation:
    """Compute cross-sectional market breadth metrics for a single market session.

    Args:
        timestamp: Session datetime.
        stock_returns: Map of symbol -> daily percentage return for the session.
        stock_sma_status: Optional map of symbol -> bool indicating whether close > SMA20.

    Returns:
        MarketBreadthObservation summarizing advance/decline distribution.
    """
    advances = 0
    declines = 0
    unchanged = 0

    for ret in stock_returns.values():
        if ret is None:
            continue
        if ret > 1e-6:
            advances += 1
        elif ret < -1e-6:
            declines += 1
        else:
            unchanged += 1

    total = advances + declines + unchanged
    ad_ratio = (advances / declines) if declines > 0 else None
    thrust = (advances / total) if total > 0 else None
    net_adv = advances - declines

    pct_above_sma: Optional[float] = None
    if stock_sma_status:
        valid_statuses = [v for v in stock_sma_status.values() if v is not None]
        if valid_statuses:
            pct_above_sma = sum(1 for v in valid_statuses if v) / len(valid_statuses)

    return MarketBreadthObservation(
        timestamp=timestamp,
        total_stocks=total,
        advances=advances,
        declines=declines,
        unchanged=unchanged,
        advance_decline_ratio=ad_ratio,
        breadth_thrust=thrust,
        net_advances=net_adv,
        pct_above_sma20=pct_above_sma,
    )


def compute_multi_symbol_breadth_series(
    multi_symbol_bars: Dict[str, Sequence[MarketOHLCV]],
    sma_window: int = 20,
) -> List[MarketBreadthObservation]:
    """Compute chronological daily market breadth series across a universe of stocks.

    Rules:
    - Groups stock sessions by calendar date.
    - Determines advances, declines, and unchanged stocks per session.
    - Evaluates 20-day SMA participation point-in-time per symbol.

    Args:
        multi_symbol_bars: Dictionary mapping symbol -> list of historical MarketOHLCV.
        sma_window: Window for moving average participation (default 20).

    Returns:
        Chronological list of MarketBreadthObservation records.
    """
    if not multi_symbol_bars:
        return []

    # Precompute daily returns and SMA20 status for each stock
    symbol_dates: Dict[str, Dict[date, Tuple[datetime, Optional[float], Optional[bool]]]] = {}

    for sym, bars in multi_symbol_bars.items():
        if not bars:
            continue
        closes = [b.close for b in bars]
        returns = calculate_daily_returns(closes)
        smas = calculate_sma(closes, sma_window)

        date_map: Dict[date, Tuple[datetime, Optional[float], Optional[bool]]] = {}
        for idx, bar in enumerate(bars):
            d = bar.timestamp.date()
            ret = returns[idx]
            sma_val = smas[idx]
            above_sma = (bar.close > sma_val) if sma_val is not None else None
            date_map[d] = (bar.timestamp, ret, above_sma)

        symbol_dates[sym] = date_map

    # Collect all unique session dates sorted chronologically
    all_dates = sorted({d for d_map in symbol_dates.values() for d in d_map.keys()})

    observations: List[MarketBreadthObservation] = []
    for d in all_dates:
        session_ts: Optional[datetime] = None
        returns_map: Dict[str, Optional[float]] = {}
        sma_status_map: Dict[str, bool] = {}

        for sym, d_map in symbol_dates.items():
            if d in d_map:
                ts, ret, above_sma = d_map[d]
                if session_ts is None:
                    session_ts = ts
                returns_map[sym] = ret
                if above_sma is not None:
                    sma_status_map[sym] = above_sma

        if session_ts is not None and returns_map:
            obs = compute_market_breadth(
                timestamp=session_ts,
                stock_returns=returns_map,
                stock_sma_status=sma_status_map if sma_status_map else None,
            )
            observations.append(obs)

    return observations
