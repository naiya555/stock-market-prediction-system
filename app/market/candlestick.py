"""Candlestick Feature Engineering Layer.

Provides deterministic, point-in-time calculation of single-session OHLC candle
geometric properties, wick and body dimensions, ratios, close location, percentage
price return, and direction on canonical historical market data (MarketOHLCV).

Non-predictive baseline disclaimer:
Candlestick features quantify single-bar geometric price action and intra-session
dynamics; they do not constitute guaranteed buy/sell signals or predictive forecasts.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Sequence

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV

logger = get_logger(__name__)


@dataclass(frozen=True)
class CandlestickFeatures:
    """Canonical calculated candlestick features for a single market bar.

    Encapsulates single-session OHLC geometric properties, wick and body dimensions,
    ratios, close location, intra-session return, and candle direction.
    """

    symbol: str
    timestamp: datetime
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    candle_body: Optional[float]
    candle_body_abs: Optional[float]
    candle_range: Optional[float]
    candle_upper_wick: Optional[float]
    candle_lower_wick: Optional[float]
    candle_body_ratio: Optional[float]
    candle_upper_wick_ratio: Optional[float]
    candle_lower_wick_ratio: Optional[float]
    candle_close_location: Optional[float]
    candle_body_return_pct: Optional[float]
    candle_direction: Optional[str]

    @property
    def body(self) -> Optional[float]:
        """Convenience alias for candle_body."""
        return self.candle_body

    @property
    def body_abs(self) -> Optional[float]:
        """Convenience alias for candle_body_abs."""
        return self.candle_body_abs

    @property
    def range(self) -> Optional[float]:
        """Convenience alias for candle_range."""
        return self.candle_range

    @property
    def upper_wick(self) -> Optional[float]:
        """Convenience alias for candle_upper_wick."""
        return self.candle_upper_wick

    @property
    def lower_wick(self) -> Optional[float]:
        """Convenience alias for candle_lower_wick."""
        return self.candle_lower_wick

    @property
    def body_ratio(self) -> Optional[float]:
        """Convenience alias for candle_body_ratio."""
        return self.candle_body_ratio

    @property
    def upper_wick_ratio(self) -> Optional[float]:
        """Convenience alias for candle_upper_wick_ratio."""
        return self.candle_upper_wick_ratio

    @property
    def lower_wick_ratio(self) -> Optional[float]:
        """Convenience alias for candle_lower_wick_ratio."""
        return self.candle_lower_wick_ratio

    @property
    def close_location(self) -> Optional[float]:
        """Convenience alias for candle_close_location."""
        return self.candle_close_location

    @property
    def body_return_pct(self) -> Optional[float]:
        """Convenience alias for candle_body_return_pct."""
        return self.candle_body_return_pct

    @property
    def direction(self) -> Optional[str]:
        """Convenience alias for candle_direction."""
        return self.candle_direction

    @property
    def is_bullish(self) -> bool:
        """Whether the candle direction is strictly bullish."""
        return self.candle_direction == "bullish"

    @property
    def is_bearish(self) -> bool:
        """Whether the candle direction is strictly bearish."""
        return self.candle_direction == "bearish"

    @property
    def is_neutral(self) -> bool:
        """Whether the candle direction is strictly neutral."""
        return self.candle_direction == "neutral"

    def to_dict(self) -> Dict[str, Any]:
        """Convert candlestick features to a flat dictionary for tabular analysis and ML datasets."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp is not None else None,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "candle_body": self.candle_body,
            "candle_body_abs": self.candle_body_abs,
            "candle_range": self.candle_range,
            "candle_upper_wick": self.candle_upper_wick,
            "candle_lower_wick": self.candle_lower_wick,
            "candle_body_ratio": self.candle_body_ratio,
            "candle_upper_wick_ratio": self.candle_upper_wick_ratio,
            "candle_lower_wick_ratio": self.candle_lower_wick_ratio,
            "candle_close_location": self.candle_close_location,
            "candle_body_return_pct": self.candle_body_return_pct,
            "candle_direction": self.candle_direction,
        }


def calculate_single_candlestick(
    open_: Any,
    high: Any,
    low: Any,
    close: Any,
    timestamp: Optional[datetime] = None,
    symbol: str = "UNKNOWN",
) -> CandlestickFeatures:
    """Calculate candlestick features for a single OHLC observation.

    Mathematical Definitions:
        Signed body = Close - Open
        Absolute body = abs(Close - Open)
        Candle range = High - Low
        Upper wick = High - max(Open, Close)
        Lower wick = min(Open, Close) - Low
        Body-to-range ratio = absolute body / candle range, when range > 0 (else None)
        Upper-wick-to-range ratio = upper wick / candle range, when range > 0 (else None)
        Lower-wick-to-range ratio = lower wick / candle range, when range > 0 (else None)
        Close location within range = (Close - Low) / (High - Low), when range > 0 (else None)
        Body return percentage = ((Close / Open) - 1) * 100, when Open > 0 (else None)
        Candle direction = 'bullish' if Close > Open, 'bearish' if Close < Open, 'neutral' if Close == Open

    Validation Rules:
        - All price components must be finite numeric values > 0.
        - Geometry checks: High >= Low, High >= max(Open, Close), Low <= min(Open, Close).
        - If invalid, all features evaluate strictly to None.
        - For zero-range candles (High == Low == Open == Close):
          valid zero dimensions are preserved; ratios evaluate strictly to None.

    Args:
        open_: Opening price.
        high: Session high price.
        low: Session low price.
        close: Closing price.
        timestamp: Point-in-time timestamp (optional).
        symbol: Market ticker symbol (default 'UNKNOWN').

    Returns:
        CandlestickFeatures instance.
    """
    ts = timestamp if timestamp is not None else datetime.min

    # Check numeric types, finiteness, and positive values
    for val in (open_, high, low, close):
        if (
            val is None
            or isinstance(val, bool)
            or not isinstance(val, (int, float))
            or not math.isfinite(val)
            or val <= 0.0
        ):
            return CandlestickFeatures(
                symbol=symbol,
                timestamp=ts,
                open=float(open_) if isinstance(open_, (int, float)) and not isinstance(open_, bool) else None,
                high=float(high) if isinstance(high, (int, float)) and not isinstance(high, bool) else None,
                low=float(low) if isinstance(low, (int, float)) and not isinstance(low, bool) else None,
                close=float(close) if isinstance(close, (int, float)) and not isinstance(close, bool) else None,
                candle_body=None,
                candle_body_abs=None,
                candle_range=None,
                candle_upper_wick=None,
                candle_lower_wick=None,
                candle_body_ratio=None,
                candle_upper_wick_ratio=None,
                candle_lower_wick_ratio=None,
                candle_close_location=None,
                candle_body_return_pct=None,
                candle_direction=None,
            )

    o = float(open_)
    h = float(high)
    l = float(low)
    c = float(close)

    # Validate physical OHLC candle geometry
    if h < l or h < max(o, c) or l > min(o, c):
        logger.warning(
            "Invalid OHLC candle geometry for %s: Open=%s, High=%s, Low=%s, Close=%s",
            symbol,
            o,
            h,
            l,
            c,
        )
        return CandlestickFeatures(
            symbol=symbol,
            timestamp=ts,
            open=o,
            high=h,
            low=l,
            close=c,
            candle_body=None,
            candle_body_abs=None,
            candle_range=None,
            candle_upper_wick=None,
            candle_lower_wick=None,
            candle_body_ratio=None,
            candle_upper_wick_ratio=None,
            candle_lower_wick_ratio=None,
            candle_close_location=None,
            candle_body_return_pct=None,
            candle_direction=None,
        )

    # Dimensions
    candle_body = c - o
    candle_body_abs = abs(candle_body)
    candle_range = h - l
    candle_upper_wick = h - max(o, c)
    candle_lower_wick = min(o, c) - l

    # Direction
    if c > o:
        candle_direction = "bullish"
    elif c < o:
        candle_direction = "bearish"
    else:
        candle_direction = "neutral"

    # Return percentage
    candle_body_return_pct = ((c / o) - 1.0) * 100.0 if o > 0.0 else None

    # Ratios and close location within range
    if candle_range > 0.0:
        candle_body_ratio = candle_body_abs / candle_range
        candle_upper_wick_ratio = candle_upper_wick / candle_range
        candle_lower_wick_ratio = candle_lower_wick / candle_range
        candle_close_location = (c - l) / candle_range
    else:
        candle_body_ratio = None
        candle_upper_wick_ratio = None
        candle_lower_wick_ratio = None
        candle_close_location = None

    return CandlestickFeatures(
        symbol=symbol,
        timestamp=ts,
        open=o,
        high=h,
        low=l,
        close=c,
        candle_body=candle_body,
        candle_body_abs=candle_body_abs,
        candle_range=candle_range,
        candle_upper_wick=candle_upper_wick,
        candle_lower_wick=candle_lower_wick,
        candle_body_ratio=candle_body_ratio,
        candle_upper_wick_ratio=candle_upper_wick_ratio,
        candle_lower_wick_ratio=candle_lower_wick_ratio,
        candle_close_location=candle_close_location,
        candle_body_return_pct=candle_body_return_pct,
        candle_direction=candle_direction,
    )


def calculate_candlestick_features(
    open_prices: Any,
    high_prices: Optional[Sequence[Any]] = None,
    low_prices: Optional[Sequence[Any]] = None,
    close_prices: Optional[Sequence[Any]] = None,
    timestamps: Optional[Sequence[datetime]] = None,
    symbol: str = "UNKNOWN",
) -> List[CandlestickFeatures]:
    """Calculate candlestick features across a sequence of market observations.

    Accepts either:
    1. A sequence of MarketOHLCV records (or objects with .open, .high, .low, .close, .timestamp, .symbol)
       as the first parameter:
           calculate_candlestick_features(records)
    2. Separate sequences of prices:
           calculate_candlestick_features(opens, highs, lows, closes, timestamps, symbol)

    Guarantees:
        - Strictly point-in-time: Each bar's features depend solely on its own contemporaneous OHLC.
        - Preserves input sequence length and alignment.
        - Does not mutate raw input records.

    Args:
        open_prices: Sequence of open prices or sequence of MarketOHLCV records.
        high_prices: Sequence of high prices (optional if records provided).
        low_prices: Sequence of low prices (optional if records provided).
        close_prices: Sequence of close prices (optional if records provided).
        timestamps: Sequence of point-in-time timestamps (optional).
        symbol: Symbol identifier (default 'UNKNOWN').

    Returns:
        List of CandlestickFeatures aligned 1:1 with input observations.
    """
    if open_prices is None:
        return []

    # If first argument contains records with OHLC attributes
    if high_prices is None and low_prices is None and close_prices is None:
        records_list = list(open_prices)
        if not records_list:
            return []

        out: List[CandlestickFeatures] = []
        for r in records_list:
            if hasattr(r, "open") and hasattr(r, "high") and hasattr(r, "low") and hasattr(r, "close"):
                r_sym = getattr(r, "symbol", symbol)
                r_ts = getattr(r, "timestamp", None)
                feat = calculate_single_candlestick(
                    open_=r.open,
                    high=r.high,
                    low=r.low,
                    close=r.close,
                    timestamp=r_ts,
                    symbol=r_sym,
                )
                out.append(feat)
            else:
                raise TypeError(
                    "When passing a single sequence, elements must have open, high, low, close attributes."
                )
        return out

    # Otherwise separate sequences were provided
    o_list = list(open_prices)
    h_list = list(high_prices) if high_prices is not None else []
    l_list = list(low_prices) if low_prices is not None else []
    c_list = list(close_prices) if close_prices is not None else []

    n = len(o_list)
    if not (len(h_list) == n and len(l_list) == n and len(c_list) == n):
        raise ValueError(
            f"Price sequences must have identical lengths: open={n}, high={len(h_list)}, "
            f"low={len(l_list)}, close={len(c_list)}"
        )

    ts_list = list(timestamps) if timestamps is not None else None
    if ts_list is not None and len(ts_list) != n:
        raise ValueError(f"Timestamps sequence length ({len(ts_list)}) must match prices ({n})")

    out_features: List[CandlestickFeatures] = []
    for i in range(n):
        ts = ts_list[i] if ts_list is not None else None
        feat = calculate_single_candlestick(
            open_=o_list[i],
            high=h_list[i],
            low=l_list[i],
            close=c_list[i],
            timestamp=ts,
            symbol=symbol,
        )
        out_features.append(feat)

    return out_features


def compute_candlestick_features(
    records: Sequence[MarketOHLCV],
) -> List[CandlestickFeatures]:
    """Compute candlestick features across canonical MarketOHLCV records with multi-symbol isolation.

    Guarantees:
        - Multi-symbol isolation: Data is grouped by symbol and calculated independently.
        - Chronological ordering: Records are strictly sorted by timestamp ascending.
        - Point-in-time integrity: Calculations use strictly contemporaneous candle data.
        - Source preservation: Original records are never mutated.

    Args:
        records: Sequence of validated MarketOHLCV bars.

    Returns:
        List of CandlestickFeatures chronologically aligned with input bars.
    """
    if not records:
        return []

    grouped: Dict[str, List[MarketOHLCV]] = defaultdict(list)
    for rec in records:
        grouped[rec.symbol].append(rec)

    all_features: List[CandlestickFeatures] = []
    for sym, sym_records in sorted(grouped.items(), key=lambda x: x[0]):
        sorted_bars = sorted(sym_records, key=lambda b: b.timestamp)
        sym_features = calculate_candlestick_features(sorted_bars)
        all_features.extend(sym_features)

    return sorted(all_features, key=lambda f: (f.symbol, f.timestamp))
