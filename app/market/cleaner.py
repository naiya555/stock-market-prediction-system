"""Market Data Cleaning Layer.

Provides deterministic, auditable, and non-destructive cleaning for historical
market data. Enforces missing-value detection, duplicate resolution, invalid-value
rejection, timezone normalization to Asia/Kolkata, and chronological sorting.
"""

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from zoneinfo import ZoneInfo

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV, ValidationError

logger = get_logger(__name__)


@dataclass(frozen=True)
class CleaningSummary:
    """Audit summary recording metrics and actions of the data-cleaning pipeline."""

    input_count: int
    output_count: int
    missing_records_count: int
    identical_duplicates_count: int
    conflicting_duplicates_count: int
    invalid_records_count: int
    rejected_count: int
    is_sorted: bool
    rejection_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class CleaningResult:
    """Container holding cleaned MarketOHLCV records and the associated audit summary."""

    records: List[MarketOHLCV]
    summary: CleaningSummary


def _is_missing(val: Any) -> bool:
    """Check if a field value is missing, None, blank, or NaN."""
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    return False


def _normalize_datetime(dt: Any, tz: ZoneInfo) -> Optional[datetime]:
    """Normalize timestamp to timezone-aware datetime in target timezone.

    Preserves calendar session date for timezone-naive timestamps.
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        try:
            parsed = datetime.fromisoformat(dt)
        except Exception:
            return None
    elif isinstance(dt, datetime):
        parsed = dt
    else:
        return None

    if parsed.tzinfo is None:
        # Interpret naive timestamp directly as target timezone (preserving calendar date)
        return parsed.replace(tzinfo=tz)
    else:
        # Convert timezone-aware timestamp to target timezone
        return parsed.astimezone(tz)


def clean_market_data(
    records: Sequence[Union[MarketOHLCV, Dict[str, Any]]],
    target_timezone: str = "Asia/Kolkata",
) -> CleaningResult:
    """Clean and validate historical market data records.

    Rules applied:
    1. Missing Values: Records with missing/null/NaN required fields are quarantined/rejected.
    2. Invalid Values: Non-positive prices, negative volume, or violated OHLC candle
       geometry are rejected.
    3. Timestamp Normalization: Standardized to target timezone (Asia/Kolkata) without shifting dates.
    4. Duplicates:
       - Identical duplicates (same symbol, timestamp, prices, volume) are safely collapsed into 1 bar.
       - Conflicting duplicates (same symbol and timestamp, conflicting values) are quarantined/rejected.
    5. Sorting: Records are sorted chronologically by (symbol, timestamp) ascending.

    Args:
        records: Sequence of MarketOHLCV dataclasses or raw dictionaries.
        target_timezone: Application timezone name (default 'Asia/Kolkata').

    Returns:
        CleaningResult containing validated canonical records and an audit summary.
    """
    input_count = len(records)
    tz = ZoneInfo(target_timezone)

    missing_records_count = 0
    invalid_records_count = 0
    rejection_reasons: List[str] = []

    valid_candidates: List[MarketOHLCV] = []

    for idx, item in enumerate(records):
        # Extract fields whether item is MarketOHLCV or Dict
        if isinstance(item, MarketOHLCV):
            symbol = item.symbol
            raw_ts = item.timestamp
            open_val = item.open
            high_val = item.high
            low_val = item.low
            close_val = item.close
            volume_val = item.volume
            source = item.source
        elif isinstance(item, dict):
            symbol = item.get("symbol")
            raw_ts = item.get("timestamp")
            open_val = item.get("open")
            high_val = item.get("high")
            low_val = item.get("low")
            close_val = item.get("close")
            volume_val = item.get("volume")
            source = item.get("source")
        else:
            invalid_records_count += 1
            msg = f"Record at index {idx} has unsupported type {type(item).__name__}"
            rejection_reasons.append(msg)
            logger.warning(msg)
            continue

        # Check required fields for missing values
        if (
            _is_missing(symbol)
            or _is_missing(raw_ts)
            or _is_missing(open_val)
            or _is_missing(high_val)
            or _is_missing(low_val)
            or _is_missing(close_val)
            or _is_missing(volume_val)
            or _is_missing(source)
        ):
            missing_records_count += 1
            msg = f"Record at index {idx} ({symbol}) rejected due to missing required field(s)"
            rejection_reasons.append(msg)
            logger.warning(msg)
            continue

        # Normalize timestamp
        norm_ts = _normalize_datetime(raw_ts, tz)
        if norm_ts is None:
            invalid_records_count += 1
            msg = f"Record at index {idx} ({symbol}) rejected due to invalid timestamp {raw_ts}"
            rejection_reasons.append(msg)
            logger.warning(msg)
            continue

        # Validate numeric types
        try:
            open_flt = float(open_val)
            high_flt = float(high_val)
            low_flt = float(low_val)
            close_flt = float(close_val)
            volume_int = int(volume_val)
        except (ValueError, TypeError) as exc:
            invalid_records_count += 1
            msg = f"Record at index {idx} ({symbol}) rejected due to non-numeric price/volume: {exc}"
            rejection_reasons.append(msg)
            logger.warning(msg)
            continue

        # Check physical domain constraints
        if (
            open_flt <= 0
            or high_flt <= 0
            or low_flt <= 0
            or close_flt <= 0
            or volume_int < 0
            or high_flt < low_flt
            or high_flt < max(open_flt, close_flt)
            or low_flt > min(open_flt, close_flt)
        ):
            invalid_records_count += 1
            msg = (
                f"Record at index {idx} ({symbol} on {norm_ts.date()}) rejected for invalid/impossible OHLCV: "
                f"O={open_flt}, H={high_flt}, L={low_flt}, C={close_flt}, V={volume_int}"
            )
            rejection_reasons.append(msg)
            logger.warning(msg)
            continue

        # Attempt canonical contract instantiation
        try:
            canonical_bar = MarketOHLCV(
                symbol=str(symbol),
                timestamp=norm_ts,
                open=open_flt,
                high=high_flt,
                low=low_flt,
                close=close_flt,
                volume=volume_int,
                source=str(source),
            )
            valid_candidates.append(canonical_bar)
        except ValidationError as exc:
            invalid_records_count += 1
            msg = f"Record at index {idx} failed canonical validation: {exc}"
            rejection_reasons.append(msg)
            logger.warning(msg)
            continue

    # Group valid records by (symbol, timestamp) to handle duplicates
    grouped: Dict[Tuple[str, datetime], List[MarketOHLCV]] = defaultdict(list)
    for bar in valid_candidates:
        grouped[(bar.symbol, bar.timestamp)].append(bar)

    identical_duplicates_count = 0
    conflicting_duplicates_count = 0
    deduplicated_records: List[MarketOHLCV] = []

    for (sym, ts), group in grouped.items():
        if len(group) == 1:
            deduplicated_records.append(group[0])
        else:
            # Check if all records in group are identical in price and volume
            first = group[0]
            all_identical = all(
                math.isclose(b.open, first.open, abs_tol=1e-5)
                and math.isclose(b.high, first.high, abs_tol=1e-5)
                and math.isclose(b.low, first.low, abs_tol=1e-5)
                and math.isclose(b.close, first.close, abs_tol=1e-5)
                and b.volume == first.volume
                for b in group
            )
            if all_identical:
                # Collapse identical duplicates safely into one bar
                collapsed_count = len(group) - 1
                identical_duplicates_count += collapsed_count
                deduplicated_records.append(first)
                logger.info("Collapsed %d identical duplicate bar(s) for %s on %s", collapsed_count, sym, ts)
            else:
                # Conflicting values: reject all to prevent inventing or guessing market reality
                conflicting_count = len(group)
                conflicting_duplicates_count += conflicting_count
                msg = f"Rejected {conflicting_count} conflicting duplicate records for {sym} on {ts}"
                rejection_reasons.append(msg)
                logger.warning(msg)

    # Sort deduplicated records chronologically
    sorted_records = sorted(deduplicated_records, key=lambda b: (b.symbol, b.timestamp))

    rejected_count = (
        missing_records_count
        + invalid_records_count
        + identical_duplicates_count
        + conflicting_duplicates_count
    )

    summary = CleaningSummary(
        input_count=input_count,
        output_count=len(sorted_records),
        missing_records_count=missing_records_count,
        identical_duplicates_count=identical_duplicates_count,
        conflicting_duplicates_count=conflicting_duplicates_count,
        invalid_records_count=invalid_records_count,
        rejected_count=rejected_count,
        is_sorted=True,
        rejection_reasons=rejection_reasons,
    )

    logger.info(
        "Cleaned market data: %d input -> %d output (rejected: %d, missing: %d, invalid: %d, "
        "identical dupes: %d, conflicting dupes: %d)",
        input_count,
        summary.output_count,
        summary.rejected_count,
        summary.missing_records_count,
        summary.invalid_records_count,
        summary.identical_duplicates_count,
        summary.conflicting_duplicates_count,
    )

    return CleaningResult(records=sorted_records, summary=summary)
