"""Machine Learning Prediction Target Definition Layer.

Defines the mathematical formulation, temporal alignment, and leakage-safe
generation of forward prediction targets for machine learning forecasting models.

Mathematical Formulation:
    For a chronological sequence of trading sessions t = 0, 1, ..., N - 1:
        target_return[t] = (close[t+1] / close[t]) - 1.0
        target_direction[t] = "UP" if target_return[t] > 0.0 else "DOWN"
        target_binary[t] = 1 if target_return[t] > 0.0 else 0

Baseline Binary Policy & Zero-Return Grouping:
    This is an initial binary baseline experiment designed to evaluate directional
    classification. Sessions where close[t+1] == close[t] (target_return[t] == 0.0)
    are deterministically grouped into "DOWN" (target_binary = 0). They are explicitly
    retained and not silently discarded. Multi-class extensions (e.g. FLAT / SIDEWAYS)
    may be introduced in later project phases.

Calendar Invariant & Trading Session Spacing:
    close[t] represents the closing price of the current available trading session t.
    close[t+1] represents the closing price of the NEXT AVAILABLE trading session t+1.
    The engine never assumes that calendar day t+1 is a trading day; weekends, exchange
    holidays, and non-trading intervals are handled naturally by indexing the next
    available session in the chronological series.

Leakage-Safe Temporal Invariant:
    Features at session t utilize only information available at or before session t.
    The prediction target at session t represents the future outcome realized at
    session t+1. The final session in any historical series (t = N - 1) has no known
    subsequent close and evaluates strictly to None (missing target).
    Future closes and future returns must NEVER be included as input features.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV

logger = get_logger(__name__)


class DirectionTarget:
    """Canonical directional target constants."""

    UP = "UP"
    DOWN = "DOWN"
    UP_BINARY = 1
    DOWN_BINARY = 0


@dataclass(frozen=True)
class TargetObservation:
    """Canonical typed record representing a prediction session and its forward target.

    Attributes:
        symbol: Ticker symbol (e.g. 'BHARTIARTL').
        timestamp: Date and time of session t when prediction is made (at close).
        current_close: Closing price of session t (reference price).
        next_timestamp: Date and time of next session t+1 (None for latest bar).
        next_close: Closing price of session t+1 (outcome price, None for latest bar).
        target_return: Forward close-to-close return (close[t+1] / close[t] - 1.0).
        target_direction: 'UP' if target_return > 0 else 'DOWN' (None if undefined).
        target_binary: 1 if target_return > 0 else 0 (None if undefined).
    """

    symbol: str
    timestamp: datetime
    current_close: float
    next_timestamp: Optional[datetime]
    next_close: Optional[float]
    target_return: Optional[float]
    target_direction: Optional[str]
    target_binary: Optional[int]

    @property
    def is_up(self) -> Optional[bool]:
        """Whether the forward return is strictly positive."""
        if self.target_direction is None:
            return None
        return self.target_direction == DirectionTarget.UP

    @property
    def is_down(self) -> Optional[bool]:
        """Whether the forward return is zero or negative."""
        if self.target_direction is None:
            return None
        return self.target_direction == DirectionTarget.DOWN

    @property
    def has_target(self) -> bool:
        """Whether this observation has a valid, non-missing outcome target."""
        return self.target_direction is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert target observation to a flat dictionary for tabular datasets."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "current_close": self.current_close,
            "next_timestamp": self.next_timestamp.isoformat() if self.next_timestamp else None,
            "next_close": self.next_close,
            "target_return": self.target_return,
            "target_direction": self.target_direction,
            "target_binary": self.target_binary,
        }


def calculate_forward_return(current_close: float, next_close: float) -> Optional[float]:
    """Calculate single-step forward close-to-close return: close[t+1] / close[t] - 1.

    Rules:
        - If either price is non-positive (<= 0) or non-finite (NaN / Inf), returns None.
        - Division by zero is strictly prevented.
        - Returns float value: (next_close / current_close) - 1.0.
    """
    if not (math.isfinite(current_close) and math.isfinite(next_close)):
        return None
    if current_close <= 0.0 or next_close <= 0.0:
        return None
    return (next_close / current_close) - 1.0


def classify_forward_direction(
    target_return: Optional[float],
) -> Tuple[Optional[str], Optional[int]]:
    """Classify forward return into binary direction ('UP' or 'DOWN') and binary integer (1 or 0).

    Rules:
        - If target_return is None or non-finite: returns (None, None).
        - If target_return > 0.0: returns ('UP', 1).
        - If target_return <= 0.0: returns ('DOWN', 0).
          Zero-return sessions are deterministically grouped into 'DOWN'.
    """
    if target_return is None or not math.isfinite(target_return):
        return None, None
    if target_return > 0.0:
        return DirectionTarget.UP, DirectionTarget.UP_BINARY
    return DirectionTarget.DOWN, DirectionTarget.DOWN_BINARY


def compute_target_series(
    closes: Sequence[float],
) -> Tuple[List[Optional[float]], List[Optional[str]], List[Optional[int]]]:
    """Compute forward returns and binary targets from a chronological price sequence.

    For an input series of length N:
        - Elements 0 .. N - 2 evaluate to forward returns against closes[t+1].
        - Element N - 1 (final session) strictly evaluates to (None, None, None).
        - Returns a 3-tuple of parallel lists: (returns, directions, binaries).
    """
    n = len(closes)
    if n == 0:
        return [], [], []

    returns: List[Optional[float]] = []
    directions: List[Optional[str]] = []
    binaries: List[Optional[int]] = []

    for t in range(n - 1):
        ret = calculate_forward_return(closes[t], closes[t + 1])
        direction, binary = classify_forward_direction(ret)
        returns.append(ret)
        directions.append(direction)
        binaries.append(binary)

    # Final session has no subsequent outcome
    returns.append(None)
    directions.append(None)
    binaries.append(None)

    return returns, directions, binaries


def generate_direction_targets(
    records: Sequence[MarketOHLCV],
) -> List[TargetObservation]:
    """Generate aligned TargetObservation objects from a sequence of MarketOHLCV records.

    Behavior & Guarantees:
        - Handles unsorted input safely by sorting chronologically per symbol.
        - Supports multi-symbol inputs by isolating each ticker symbol.
        - Does not assume daily calendar spacing; consecutive records in the sequence
          are treated as consecutive trading sessions (handles weekends, holidays).
        - The final session of each symbol strictly receives None for next_timestamp,
          next_close, target_return, target_direction, and target_binary.
        - Returns a list of TargetObservation objects aligned to the prediction session t.
    """
    if not records:
        return []

    # Group records by symbol
    by_symbol: Dict[str, List[MarketOHLCV]] = defaultdict(list)
    for r in records:
        by_symbol[r.symbol].append(r)

    results: List[TargetObservation] = []

    for symbol, sym_records in by_symbol.items():
        # Ensure chronological ordering
        sorted_records = sorted(sym_records, key=lambda b: b.timestamp)
        n = len(sorted_records)

        for t in range(n):
            curr_bar = sorted_records[t]

            if t < n - 1:
                next_bar = sorted_records[t + 1]
                next_ts = next_bar.timestamp
                next_c = next_bar.close

                fwd_return = calculate_forward_return(curr_bar.close, next_c)
                direction, binary = classify_forward_direction(fwd_return)
            else:
                # Latest observation: future is unknown, target must be missing
                next_ts = None
                next_c = None
                fwd_return = None
                direction = None
                binary = None

            results.append(
                TargetObservation(
                    symbol=symbol,
                    timestamp=curr_bar.timestamp,
                    current_close=curr_bar.close,
                    next_timestamp=next_ts,
                    next_close=next_c,
                    target_return=fwd_return,
                    target_direction=direction,
                    target_binary=binary,
                )
            )

    return results
