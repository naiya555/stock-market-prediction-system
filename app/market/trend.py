"""Trend Engine and Market Structure Analysis Layer.

Provides deterministic, point-in-time identification of swing highs and swing lows,
market structure classification (Higher Highs, Higher Lows, Lower Highs, Lower Lows),
and trend regime classification (UPTREND, DOWNTREND, SIDEWAYS) on canonical historical
market data (MarketOHLCV).

Look-Ahead Safeguards & Confirmation Policy:
A swing pivot at index t with window k requires k subsequent bars to form.
Therefore, the pivot is confirmed strictly at index t + k. At any evaluation
timestamp T, only swings confirmed at or before T (confirmation_index <= T)
are considered knowable. Swings pending confirmation are never used to claim
historical trend knowledge earlier than it existed in real time.

Non-Predictive Baseline Disclaimer:
Trend engine classifications represent descriptive historical market structure
and price action geometry; they do not constitute guaranteed future trend
continuations, directional trading signals, or predictive investment recommendations.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV

logger = get_logger(__name__)


class TrendClassification:
    """Canonical trend classification labels and status constants."""

    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    SIDEWAYS = "SIDEWAYS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INVALID_DATA = "INVALID_DATA"
    CONFIRMED = "CONFIRMED"


@dataclass(frozen=True)
class SwingPoint:
    """Canonical representation of an identified price swing point (pivot).

    Attributes:
        index: Zero-based bar index where the price extreme occurred (t).
        timestamp: Point-in-time timestamp of the extreme bar.
        price: Price level of the extreme (High for swing high, Low for swing low).
        swing_type: "HIGH" for swing high, "LOW" for swing low.
        confirmation_index: Bar index when the swing was confirmed (t + k).
        confirmation_timestamp: Timestamp when the confirmation bar closed.
        structure_label: Structural relation to previous swing of same type
                         ("HH", "LH", "EH" for highs; "HL", "LL", "EL" for lows).
    """

    index: int
    timestamp: datetime
    price: float
    swing_type: str
    confirmation_index: int
    confirmation_timestamp: datetime
    structure_label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert swing point to flat dictionary representation."""
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "price": self.price,
            "swing_type": self.swing_type,
            "confirmation_index": self.confirmation_index,
            "confirmation_timestamp": (
                self.confirmation_timestamp.isoformat() if self.confirmation_timestamp else None
            ),
            "structure_label": self.structure_label,
        }


@dataclass(frozen=True)
class TrendAnalysisResult:
    """Canonical typed result of trend engine and market structure analysis."""

    symbol: str
    as_of_timestamp: Optional[datetime]
    classification: Optional[str]
    status: str
    swing_window: int
    min_swings: int
    total_bars: int
    swing_highs: List[SwingPoint]
    swing_lows: List[SwingPoint]
    last_high_structure: Optional[str]
    last_low_structure: Optional[str]
    details: Dict[str, Any]

    @property
    def is_uptrend(self) -> bool:
        """Whether the market structure is classified as UPTREND."""
        return self.classification == TrendClassification.UPTREND

    @property
    def is_downtrend(self) -> bool:
        """Whether the market structure is classified as DOWNTREND."""
        return self.classification == TrendClassification.DOWNTREND

    @property
    def is_sideways(self) -> bool:
        """Whether the market structure is classified as SIDEWAYS."""
        return self.classification == TrendClassification.SIDEWAYS

    @property
    def is_confirmed(self) -> bool:
        """Whether the trend classification has sufficient confirmed structural evidence."""
        return self.status == TrendClassification.CONFIRMED

    def to_dict(self) -> Dict[str, Any]:
        """Convert trend analysis to dictionary for logging, serialization, and audits."""
        return {
            "symbol": self.symbol,
            "as_of_timestamp": (
                self.as_of_timestamp.isoformat() if self.as_of_timestamp else None
            ),
            "classification": self.classification,
            "status": self.status,
            "swing_window": self.swing_window,
            "min_swings": self.min_swings,
            "total_bars": self.total_bars,
            "swing_highs_count": len(self.swing_highs),
            "swing_lows_count": len(self.swing_lows),
            "last_high_structure": self.last_high_structure,
            "last_low_structure": self.last_low_structure,
            "swing_highs": [sh.to_dict() for sh in self.swing_highs],
            "swing_lows": [sl.to_dict() for sl in self.swing_lows],
            "details": self.details,
        }


def _validate_bar_geometry(bar: Any) -> bool:
    """Verify that a market bar has valid numeric values and physical OHLC geometry."""
    for field_name in ("open", "high", "low", "close"):
        val = getattr(bar, field_name, None)
        if (
            val is None
            or isinstance(val, bool)
            or not isinstance(val, (int, float))
            or not math.isfinite(val)
            or val <= 0.0
        ):
            return False

    o = float(bar.open)
    h = float(bar.high)
    l = float(bar.low)
    c = float(bar.close)

    if h < l or h < max(o, c) or l > min(o, c):
        return False

    return True


def identify_swings(
    records: Sequence[MarketOHLCV],
    swing_window: int = 2,
    as_of_index: Optional[int] = None,
) -> Tuple[List[SwingPoint], List[SwingPoint]]:
    """Identify confirmed swing highs and swing lows from historical OHLC records.

    Rules for Swing High (local maximum):
        A candle at index t is a Swing High if:
        - High_t > High_{t - j} for all 1 <= j <= swing_window (strictly higher than preceding window)
        - High_t >= High_{t + j} for all 1 <= j <= swing_window (greater or equal to succeeding window)
        Deterministic tie-breaking: Strict inequality on the preceding side ensures that if
        two consecutive candles share identical peak highs, only the first is recognized as the pivot.

    Rules for Swing Low (local minimum):
        A candle at index t is a Swing Low if:
        - Low_t < Low_{t - j} for all 1 <= j <= swing_window (strictly lower than preceding window)
        - Low_t <= Low_{t + j} for all 1 <= j <= swing_window (less or equal to succeeding window)
        Deterministic tie-breaking: Strict inequality on preceding side breaks equal-low ties.

    Confirmation Timing (Look-ahead safeguard):
        A pivot at index t requires swing_window subsequent candles to form.
        Confirmation occurs strictly at index t + swing_window.
        If as_of_index is specified, only pivots with confirmation_index <= as_of_index
        are emitted.

    Args:
        records: Chronological sequence of validated MarketOHLCV bars.
        swing_window: Number of flanking bars required on each side (default 2).
        as_of_index: Maximum bar index allowed for confirmation (default len(records) - 1).

    Returns:
        Tuple of (confirmed_swing_highs, confirmed_swing_lows).
    """
    if swing_window < 1:
        raise ValueError(f"swing_window must be >= 1, got {swing_window}")

    n = len(records)
    if n < 2 * swing_window + 1:
        return [], []

    max_confirm_idx = as_of_index if as_of_index is not None else n - 1
    if max_confirm_idx < 0:
        return [], []

    swing_highs: List[SwingPoint] = []
    swing_lows: List[SwingPoint] = []

    # Valid candle bounds for pivots: t ranges from swing_window to n - 1 - swing_window
    for t in range(swing_window, n - swing_window):
        confirm_idx = t + swing_window
        if confirm_idx > max_confirm_idx:
            # Pivot at t is not yet confirmed as of max_confirm_idx
            continue

        bar_t = records[t]
        if not _validate_bar_geometry(bar_t):
            continue

        h_t = float(bar_t.high)
        l_t = float(bar_t.low)

        # Check Swing High
        is_high = True
        for j in range(1, swing_window + 1):
            prev_bar = records[t - j]
            next_bar = records[t + j]
            if not _validate_bar_geometry(prev_bar) or not _validate_bar_geometry(next_bar):
                is_high = False
                break
            if not (h_t > float(prev_bar.high) and h_t >= float(next_bar.high)):
                is_high = False
                break

        if is_high:
            confirm_bar = records[confirm_idx]
            swing_highs.append(
                SwingPoint(
                    index=t,
                    timestamp=bar_t.timestamp,
                    price=h_t,
                    swing_type="HIGH",
                    confirmation_index=confirm_idx,
                    confirmation_timestamp=confirm_bar.timestamp,
                    structure_label=None,
                )
            )

        # Check Swing Low
        is_low = True
        for j in range(1, swing_window + 1):
            prev_bar = records[t - j]
            next_bar = records[t + j]
            if not _validate_bar_geometry(prev_bar) or not _validate_bar_geometry(next_bar):
                is_low = False
                break
            if not (l_t < float(prev_bar.low) and l_t <= float(next_bar.low)):
                is_low = False
                break

        if is_low:
            confirm_bar = records[confirm_idx]
            swing_lows.append(
                SwingPoint(
                    index=t,
                    timestamp=bar_t.timestamp,
                    price=l_t,
                    swing_type="LOW",
                    confirmation_index=confirm_idx,
                    confirmation_timestamp=confirm_bar.timestamp,
                    structure_label=None,
                )
            )

    return swing_highs, swing_lows


def label_market_structure(
    swings: Sequence[SwingPoint],
) -> List[SwingPoint]:
    """Label structural relationship between consecutive swing points of the same type.

    For Highs:
        - Price > Previous Price -> Higher High ("HH")
        - Price < Previous Price -> Lower High ("LH")
        - Price == Previous Price -> Equal High ("EH")

    For Lows:
        - Price > Previous Price -> Higher Low ("HL")
        - Price < Previous Price -> Lower Low ("LL")
        - Price == Previous Price -> Equal Low ("EL")

    Args:
        swings: Sequence of confirmed SwingPoints of a single type (sorted chronologically).

    Returns:
        List of new SwingPoints with structure_label populated.
    """
    if not swings:
        return []

    labeled: List[SwingPoint] = []
    for i, sp in enumerate(swings):
        if i == 0:
            # Baseline swing point has no preceding swing for comparison
            label = None
        else:
            prev_price = swings[i - 1].price
            curr_price = sp.price
            if sp.swing_type == "HIGH":
                if curr_price > prev_price:
                    label = "HH"
                elif curr_price < prev_price:
                    label = "LH"
                else:
                    label = "EH"
            elif sp.swing_type == "LOW":
                if curr_price > prev_price:
                    label = "HL"
                elif curr_price < prev_price:
                    label = "LL"
                else:
                    label = "EL"
            else:
                label = None

        labeled.append(
            SwingPoint(
                index=sp.index,
                timestamp=sp.timestamp,
                price=sp.price,
                swing_type=sp.swing_type,
                confirmation_index=sp.confirmation_index,
                confirmation_timestamp=sp.confirmation_timestamp,
                structure_label=label,
            )
        )

    return labeled


def classify_market_structure(
    swing_highs: Sequence[SwingPoint],
    swing_lows: Sequence[SwingPoint],
    min_swings: int = 2,
) -> Tuple[Optional[str], str, Optional[str], Optional[str]]:
    """Determine trend classification based on confirmed market structure evidence.

    Classification Rules (Dow Theory Structural Axioms):
    - UPTREND:
        Requires at least min_swings highs and lows.
        Latest confirmed high transition is Higher High ("HH") AND
        latest confirmed low transition is Higher Low ("HL").
    - DOWNTREND:
        Requires at least min_swings highs and lows.
        Latest confirmed high transition is Lower High ("LH") AND
        latest confirmed low transition is Lower Low ("LL").
    - SIDEWAYS:
        Sufficient confirmed swings exist (>= min_swings per type), but neither
        pure directional pattern is satisfied (e.g. HH with LL [broadening range],
        LH with HL [contracting consolidation], or equal levels EH / EL).
    - INSUFFICIENT_DATA:
        Fewer than min_swings confirmed highs or lows exist.
        Yields classification = None and status = INSUFFICIENT_DATA.
        Safeguard: Insufficient data is NEVER mislabeled as SIDEWAYS.

    Args:
        swing_highs: Sequence of labeled SwingPoints of type HIGH.
        swing_lows: Sequence of labeled SwingPoints of type LOW.
        min_swings: Minimum number of confirmed swings required for each type (default 2).

    Returns:
        Tuple of (classification, status, last_high_structure, last_low_structure).
    """
    if len(swing_highs) < min_swings or len(swing_lows) < min_swings:
        last_h = swing_highs[-1].structure_label if swing_highs else None
        last_l = swing_lows[-1].structure_label if swing_lows else None
        return None, TrendClassification.INSUFFICIENT_DATA, last_h, last_l

    last_high_label = swing_highs[-1].structure_label
    last_low_label = swing_lows[-1].structure_label

    if last_high_label == "HH" and last_low_label == "HL":
        return TrendClassification.UPTREND, TrendClassification.CONFIRMED, last_high_label, last_low_label

    if last_high_label == "LH" and last_low_label == "LL":
        return TrendClassification.DOWNTREND, TrendClassification.CONFIRMED, last_high_label, last_low_label

    return TrendClassification.SIDEWAYS, TrendClassification.CONFIRMED, last_high_label, last_low_label


def analyze_market_trend(
    records: Sequence[MarketOHLCV],
    swing_window: int = 2,
    min_swings: int = 2,
    as_of_index: Optional[int] = None,
) -> TrendAnalysisResult:
    """Execute end-to-end trend engine analysis across a sequence of MarketOHLCV bars.

    Guarantees:
        - Deterministic results across repeated executions.
        - Strict point-in-time integrity: Swing points not confirmed at or before
          as_of_index are completely excluded from trend determination.
        - Safe handling of empty, invalid, or flat datasets.

    Args:
        records: Chronological sequence of MarketOHLCV bars for a single symbol.
        swing_window: Flanking window for pivot detection (default 2).
        min_swings: Minimum swings required per type (default 2).
        as_of_index: Historical cutoff index for point-in-time replay (default: latest bar).

    Returns:
        TrendAnalysisResult containing classification, status, swing points, and metadata.
    """
    if swing_window < 1:
        raise ValueError(f"swing_window must be >= 1, got {swing_window}")
    if min_swings < 1:
        raise ValueError(f"min_swings must be >= 1, got {min_swings}")

    if not records:
        return TrendAnalysisResult(
            symbol="",
            as_of_timestamp=None,
            classification=None,
            status=TrendClassification.INSUFFICIENT_DATA,
            swing_window=swing_window,
            min_swings=min_swings,
            total_bars=0,
            swing_highs=[],
            swing_lows=[],
            last_high_structure=None,
            last_low_structure=None,
            details={"reason": "empty_input_sequence"},
        )

    # Sort strictly chronologically
    sorted_bars = sorted(records, key=lambda b: b.timestamp)
    symbol = sorted_bars[0].symbol
    n = len(sorted_bars)

    cutoff_idx = as_of_index if as_of_index is not None else n - 1
    cutoff_idx = min(max(cutoff_idx, 0), n - 1)
    as_of_ts = sorted_bars[cutoff_idx].timestamp

    # Identify swings confirmed up to cutoff_idx
    raw_highs, raw_lows = identify_swings(
        records=sorted_bars,
        swing_window=swing_window,
        as_of_index=cutoff_idx,
    )

    # Label market structure transitions
    labeled_highs = label_market_structure(raw_highs)
    labeled_lows = label_market_structure(raw_lows)

    # Classify trend
    classification, status, last_h_struct, last_l_struct = classify_market_structure(
        swing_highs=labeled_highs,
        swing_lows=labeled_lows,
        min_swings=min_swings,
    )

    details: Dict[str, Any] = {
        "cutoff_index": cutoff_idx,
        "as_of_timestamp": as_of_ts.isoformat(),
        "confirmed_highs_count": len(labeled_highs),
        "confirmed_lows_count": len(labeled_lows),
        "last_high_price": labeled_highs[-1].price if labeled_highs else None,
        "last_low_price": labeled_lows[-1].price if labeled_lows else None,
        "last_high_structure": last_h_struct,
        "last_low_structure": last_l_struct,
    }

    if status == TrendClassification.INSUFFICIENT_DATA:
        details["reason"] = (
            f"Insufficient confirmed swings: highs={len(labeled_highs)}, "
            f"lows={len(labeled_lows)}, minimum_required={min_swings}"
        )

    return TrendAnalysisResult(
        symbol=symbol,
        as_of_timestamp=as_of_ts,
        classification=classification,
        status=status,
        swing_window=swing_window,
        min_swings=min_swings,
        total_bars=cutoff_idx + 1,
        swing_highs=labeled_highs,
        swing_lows=labeled_lows,
        last_high_structure=last_h_struct,
        last_low_structure=last_l_struct,
        details=details,
    )


def compute_latest_trend(
    records: Sequence[MarketOHLCV],
    swing_window: int = 2,
    min_swings: int = 2,
) -> Optional[str]:
    """Compute point-in-time trend classification for the latest bar only.

    Avoids evaluating intermediate bars when caller only needs the current regime.

    Args:
        records: Sequence of MarketOHLCV bars.
        swing_window: Flanking window for pivot detection (default 2).
        min_swings: Minimum swings required per type (default 2).

    Returns:
        Trend classification string ("UPTREND", "DOWNTREND", "SIDEWAYS", or None).
    """
    res = analyze_market_trend(
        records=records,
        swing_window=swing_window,
        min_swings=min_swings,
    )
    return res.classification


def compute_rolling_trends(
    records: Sequence[MarketOHLCV],
    swing_window: int = 2,
    min_swings: int = 2,
) -> List[Optional[str]]:
    """Compute point-in-time trend classifications for each bar in a chronological series.

    Uses an incremental O(N) single-pass algorithm guaranteeing:
        - Zero look-ahead leakage: For bar at index t, only data available at index t
          (confirmations <= t) is used.
        - Perfectly aligned 1:1 with input records.
        - Numerical and semantic equivalence to repeated analyze_market_trend.

    Args:
        records: Sequence of MarketOHLCV bars.
        swing_window: Flanking window for pivot detection (default 2).
        min_swings: Minimum swings required per type (default 2).

    Returns:
        List of trend classification strings ("UPTREND", "DOWNTREND", "SIDEWAYS", or None),
        with length equal to len(records).
    """
    if swing_window < 1:
        raise ValueError(f"swing_window must be >= 1, got {swing_window}")
    if min_swings < 1:
        raise ValueError(f"min_swings must be >= 1, got {min_swings}")

    n = len(records)
    if n == 0:
        return []

    sorted_bars = sorted(records, key=lambda b: b.timestamp)
    trend_series: List[Optional[str]] = []

    confirmed_highs: List[SwingPoint] = []
    confirmed_lows: List[SwingPoint] = []

    for t in range(n):
        # Candidate pivot confirmed exactly at t: p = t - swing_window
        p = t - swing_window
        if p >= swing_window:
            bar_p = sorted_bars[p]
            if _validate_bar_geometry(bar_p):
                h_p = float(bar_p.high)
                l_p = float(bar_p.low)

                # Check Swing High
                is_high = True
                for j in range(1, swing_window + 1):
                    prev_bar = sorted_bars[p - j]
                    next_bar = sorted_bars[p + j]
                    if not _validate_bar_geometry(prev_bar) or not _validate_bar_geometry(next_bar):
                        is_high = False
                        break
                    if not (h_p > float(prev_bar.high) and h_p >= float(next_bar.high)):
                        is_high = False
                        break

                if is_high:
                    label: Optional[str] = None
                    if confirmed_highs:
                        prev_price = confirmed_highs[-1].price
                        if h_p > prev_price:
                            label = "HH"
                        elif h_p < prev_price:
                            label = "LH"
                        else:
                            label = "EH"
                    confirm_bar = sorted_bars[t]
                    confirmed_highs.append(
                        SwingPoint(
                            index=p,
                            timestamp=bar_p.timestamp,
                            price=h_p,
                            swing_type="HIGH",
                            confirmation_index=t,
                            confirmation_timestamp=confirm_bar.timestamp,
                            structure_label=label,
                        )
                    )

                # Check Swing Low
                is_low = True
                for j in range(1, swing_window + 1):
                    prev_bar = sorted_bars[p - j]
                    next_bar = sorted_bars[p + j]
                    if not _validate_bar_geometry(prev_bar) or not _validate_bar_geometry(next_bar):
                        is_low = False
                        break
                    if not (l_p < float(prev_bar.low) and l_p <= float(next_bar.low)):
                        is_low = False
                        break

                if is_low:
                    label = None
                    if confirmed_lows:
                        prev_price = confirmed_lows[-1].price
                        if l_p > prev_price:
                            label = "HL"
                        elif l_p < prev_price:
                            label = "LL"
                        else:
                            label = "EL"
                    confirm_bar = sorted_bars[t]
                    confirmed_lows.append(
                        SwingPoint(
                            index=p,
                            timestamp=bar_p.timestamp,
                            price=l_p,
                            swing_type="LOW",
                            confirmation_index=t,
                            confirmation_timestamp=confirm_bar.timestamp,
                            structure_label=label,
                        )
                    )

        # Classify market structure at index t
        if len(confirmed_highs) < min_swings or len(confirmed_lows) < min_swings:
            trend_series.append(None)
        else:
            last_high_label = confirmed_highs[-1].structure_label
            last_low_label = confirmed_lows[-1].structure_label
            if last_high_label == "HH" and last_low_label == "HL":
                trend_series.append(TrendClassification.UPTREND)
            elif last_high_label == "LH" and last_low_label == "LL":
                trend_series.append(TrendClassification.DOWNTREND)
            else:
                trend_series.append(TrendClassification.SIDEWAYS)

    return trend_series
