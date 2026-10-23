"""Intraday Market Data Engine and Canonical Contracts.

Provides explicit, immutable data contracts, provider abstractions, and
data-quality validation for intraday Indian equity bars (NSE/BSE).

Guarantees:
1. Strict separation from daily OHLCV pipelines (prevents feeding intraday bars
   to daily technical indicators or multi-year warmup models).
2. Timezone-aware timestamping strictly normalized to Asia/Kolkata (IST).
3. Explicit physical OHLC boundary verification: low <= min(open, close) and
   high >= max(open, close).
4. Optional trading volume without silent zero fabrication (distinguishes
   unreported volume from genuine 0-volume candles).
5. Indian market session awareness (regular hours 09:15:00 to 15:30:00 IST).
6. Non-fabrication gap detection for missing intervals during trading sessions.
7. Strict instrument isolation: only supported prediction instruments are permitted.
8. Zero premature forecasting: fast-fails with explicit diagnosis if prediction is requested
   prior to training and validating an intraday model.
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union
from zoneinfo import ZoneInfo

from app.core.logging_config import get_logger
from app.core.schemas import ValidationError
from app.market.session import (
    IST,
    MarketSessionState,
    REGULAR_MARKET_CLOSE,
    REGULAR_MARKET_OPEN,
    get_market_session,
)

logger = get_logger(__name__)


class IntradayInterval(str, Enum):
    """Canonical intraday bar intervals supported by the system."""

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    M60 = "60m"

    @property
    def duration_seconds(self) -> int:
        """Return the candle duration in seconds."""
        mapping = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "60m": 3600,
        }
        return mapping[self.value]

    @property
    def duration_minutes(self) -> int:
        """Return the candle duration in minutes."""
        return self.duration_seconds // 60

    @property
    def expected_bars_per_regular_session(self) -> int:
        """Return the maximum number of continuous bars in a 375-minute regular NSE session (09:15 to 15:30 IST)."""
        # Regular trading hours: 09:15 to 15:30 = 6 hours and 15 minutes = 375 minutes
        return 375 // self.duration_minutes

    @classmethod
    def from_string(cls, val: str) -> "IntradayInterval":
        """Parse string to IntradayInterval enum safely."""
        clean = val.strip().lower()
        if clean in ("1m", "1min", "m1"):
            return cls.M1
        if clean in ("5m", "5min", "m5"):
            return cls.M5
        if clean in ("15m", "15min", "m15"):
            return cls.M15
        if clean in ("30m", "30min", "m30"):
            return cls.M30
        if clean in ("60m", "60min", "1h", "m60"):
            return cls.M60
        raise ValidationError(f"Unsupported intraday interval: '{val}'. Supported: 1m, 5m, 15m, 30m, 60m.")


@dataclass(frozen=True)
class IntradayCandle:
    """Canonical point-in-time intraday candlestick for an individual equity.

    Strictly separate from the multi-year daily MarketOHLCV contract.
    """

    symbol: str
    timestamp: datetime
    interval: IntradayInterval
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None
    volume_reported: bool = True
    source: str = ""

    def __post_init__(self) -> None:
        # Validate symbol
        if not self.symbol or not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValidationError("symbol cannot be empty")
        object.__setattr__(self, "symbol", self.symbol.strip().upper())

        # Validate timestamp and ensure timezone awareness in Asia/Kolkata
        if not isinstance(self.timestamp, datetime):
            raise ValidationError("timestamp must be a valid datetime instance")
        if self.timestamp.tzinfo is None:
            norm_ts = self.timestamp.replace(tzinfo=IST)
        else:
            norm_ts = self.timestamp.astimezone(IST)
        object.__setattr__(self, "timestamp", norm_ts)

        # Validate interval
        if not isinstance(self.interval, IntradayInterval):
            if isinstance(self.interval, str):
                object.__setattr__(self, "interval", IntradayInterval.from_string(self.interval))
            else:
                raise ValidationError("interval must be an IntradayInterval instance")

        # Validate OHLC numeric properties
        for field_name in ("open", "high", "low", "close"):
            val = getattr(self, field_name)
            if not isinstance(val, (int, float)) or isinstance(val, bool) or math.isnan(val):
                raise ValidationError(f"{field_name} must be a valid non-NaN numeric value (got {val})")
            if val <= 0:
                raise ValidationError(f"{field_name} must be strictly positive (got {val})")
            object.__setattr__(self, field_name, float(val))

        # Physical OHLC boundary checks
        if self.high < self.low:
            raise ValidationError(f"high ({self.high}) cannot be less than low ({self.low})")
        if self.high < max(self.open, self.close):
            raise ValidationError(
                f"high ({self.high}) cannot be lower than open ({self.open}) or close ({self.close})"
            )
        if self.low > min(self.open, self.close):
            raise ValidationError(
                f"low ({self.low}) cannot be greater than open ({self.open}) or close ({self.close})"
            )

        # Validate volume (optional, never fabricated)
        if self.volume is not None:
            if not isinstance(self.volume, int) or isinstance(self.volume, bool):
                raise ValidationError(f"volume must be an integer (got {self.volume})")
            if self.volume < 0:
                raise ValidationError(f"volume cannot be negative (got {self.volume})")
            object.__setattr__(self, "volume_reported", True)
        else:
            object.__setattr__(self, "volume_reported", False)

        # Validate source
        if not self.source or not isinstance(self.source, str) or not self.source.strip():
            raise ValidationError("source cannot be empty")
        object.__setattr__(self, "source", self.source.strip())

    @property
    def bar_end_timestamp(self) -> datetime:
        """Return the nominal end timestamp for this candle."""
        return self.timestamp + timedelta(seconds=self.interval.duration_seconds)

    @property
    def is_regular_hours(self) -> bool:
        """Return True if candle open timestamp is within regular trading hours (09:15 to 15:30 IST) on a weekday."""
        if self.timestamp.weekday() >= 5:
            return False
        bar_time = self.timestamp.time()
        return REGULAR_MARKET_OPEN <= bar_time < REGULAR_MARKET_CLOSE

    def to_dict(self) -> Dict[str, Any]:
        """Serialize candle to dictionary with ISO formatted timestamps."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["bar_end_timestamp"] = self.bar_end_timestamp.isoformat()
        data["interval"] = self.interval.value
        data["is_regular_hours"] = self.is_regular_hours
        return data


@dataclass(frozen=True)
class IntradayQualitySummary:
    """Audit summary for an intraday cleaning and validation run."""

    input_count: int
    output_count: int
    rejected_count: int
    identical_duplicates_count: int
    conflicting_duplicates_count: int
    invalid_records_count: int
    out_of_session_count: int
    missing_candle_gaps_count: int
    rejection_reasons: List[str]
    gap_intervals: List[Tuple[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class IntradayCleaningResult:
    """Container holding cleaned IntradayCandle records and the associated audit summary."""

    candles: List[IntradayCandle]
    summary: IntradayQualitySummary


def _field_isclose(a: Optional[float], b: Optional[float], abs_tol: float = 1e-5) -> bool:
    """Compare two float values for near-equality, treating None == None as True."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return math.isclose(a, b, abs_tol=abs_tol)


def clean_intraday_candles(
    records: Sequence[Union[IntradayCandle, Dict[str, Any]]],
    expected_interval: Optional[IntradayInterval] = None,
    allow_out_of_session: bool = False,
) -> IntradayCleaningResult:
    """Clean, validate, and audit intraday candlestick data.

    Enforces:
    1. Valid OHLC physics and strictly positive prices.
    2. Explicit optional volume (no silent zero fabrication).
    3. Timezone normalization to Asia/Kolkata (IST).
    4. Identical duplicate collapsing; conflicting duplicate rejection.
    5. Chronological sorting and strict timestamp monotonicity.
    6. Non-fabrication gap auditing during regular market hours.
    7. Quarantine of out-of-session candles when allow_out_of_session is False.

    Args:
        records: Sequence of IntradayCandle instances or dictionaries.
        expected_interval: Optional expected candle interval to enforce.
        allow_out_of_session: If False, candles outside 09:15-15:30 IST or on non-trading days are filtered.

    Returns:
        IntradayCleaningResult containing sorted valid candles and an audit summary.
    """
    input_count = len(records)
    invalid_records_count = 0
    out_of_session_count = 0
    rejection_reasons: List[str] = []
    valid_candidates: List[IntradayCandle] = []

    for idx, item in enumerate(records):
        try:
            if isinstance(item, IntradayCandle):
                candle = item
            elif isinstance(item, dict):
                sym = item.get("symbol")
                ts_raw = item.get("timestamp")
                inter_val = item.get("interval")
                if isinstance(ts_raw, str):
                    ts = datetime.fromisoformat(ts_raw)
                elif isinstance(ts_raw, datetime):
                    ts = ts_raw
                else:
                    raise ValidationError(f"Invalid timestamp type: {type(ts_raw)}")

                if isinstance(inter_val, str):
                    inter = IntradayInterval.from_string(inter_val)
                elif isinstance(inter_val, IntradayInterval):
                    inter = inter_val
                elif expected_interval is not None:
                    inter = expected_interval
                else:
                    inter = IntradayInterval.M5

                candle = IntradayCandle(
                    symbol=str(sym),
                    timestamp=ts,
                    interval=inter,
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=int(item["volume"]) if item.get("volume") is not None else None,
                    source=str(item.get("source", "unknown")),
                )
            else:
                invalid_records_count += 1
                msg = f"Record at index {idx} has unsupported type {type(item).__name__}"
                rejection_reasons.append(msg)
                continue

            # Interval match check if expected_interval is enforced
            if expected_interval is not None and candle.interval != expected_interval:
                invalid_records_count += 1
                msg = f"Record at index {idx} ({candle.symbol} at {candle.timestamp}) interval {candle.interval.value} does not match expected {expected_interval.value}"
                rejection_reasons.append(msg)
                continue

            # Check regular trading hours filter
            if not allow_out_of_session and not candle.is_regular_hours:
                out_of_session_count += 1
                msg = f"Record at index {idx} ({candle.symbol} at {candle.timestamp}) is outside regular trading hours (filtered)"
                rejection_reasons.append(msg)
                continue

            valid_candidates.append(candle)

        except Exception as exc:
            invalid_records_count += 1
            msg = f"Record at index {idx} failed validation: {exc}"
            rejection_reasons.append(msg)

    # Group valid candles by (symbol, timestamp, interval) to detect duplicates
    grouped: Dict[Tuple[str, datetime, IntradayInterval], List[IntradayCandle]] = defaultdict(list)
    for c in valid_candidates:
        grouped[(c.symbol, c.timestamp, c.interval)].append(c)

    identical_duplicates_count = 0
    conflicting_duplicates_count = 0
    deduped: List[IntradayCandle] = []

    for (sym, ts, inter), group in grouped.items():
        if len(group) == 1:
            deduped.append(group[0])
        else:
            first = group[0]
            all_identical = all(
                _field_isclose(b.open, first.open)
                and _field_isclose(b.high, first.high)
                and _field_isclose(b.low, first.low)
                and _field_isclose(b.close, first.close)
                and b.volume == first.volume
                for b in group
            )
            if all_identical:
                identical_duplicates_count += len(group) - 1
                deduped.append(first)
            else:
                conflicting_duplicates_count += len(group)
                msg = f"Rejected {len(group)} conflicting duplicate intraday candles for {sym} at {ts}"
                rejection_reasons.append(msg)

    # Sort chronologically by (symbol, timestamp)
    sorted_candles = sorted(deduped, key=lambda c: (c.symbol, c.timestamp))

    # Gap detection audit (ponytail: O(n) sequential scan of session bars for gap detection is optimal for single-day 75-375 bars; for multi-month tick data, upgrade to vectorized indexer)
    gap_intervals: List[Tuple[str, str]] = []
    if len(sorted_candles) > 1:
        for i in range(len(sorted_candles) - 1):
            curr_c = sorted_candles[i]
            next_c = sorted_candles[i + 1]
            if curr_c.symbol != next_c.symbol:
                continue
            # If both are in same session date
            if curr_c.timestamp.date() == next_c.timestamp.date():
                expected_next = curr_c.bar_end_timestamp
                if next_c.timestamp > expected_next:
                    # Missing candle gap detected
                    gap_intervals.append((expected_next.isoformat(), next_c.timestamp.isoformat()))
                    rejection_reasons.append(
                        f"Missing intraday candle gap detected for {curr_c.symbol} between {expected_next} and {next_c.timestamp}"
                    )

    rejected_count = (
        invalid_records_count
        + out_of_session_count
        + identical_duplicates_count
        + conflicting_duplicates_count
    )

    summary = IntradayQualitySummary(
        input_count=input_count,
        output_count=len(sorted_candles),
        rejected_count=rejected_count,
        identical_duplicates_count=identical_duplicates_count,
        conflicting_duplicates_count=conflicting_duplicates_count,
        invalid_records_count=invalid_records_count,
        out_of_session_count=out_of_session_count,
        missing_candle_gaps_count=len(gap_intervals),
        rejection_reasons=rejection_reasons,
        gap_intervals=gap_intervals,
    )

    return IntradayCleaningResult(candles=sorted_candles, summary=summary)


class BaseIntradayDataProvider(ABC):
    """Abstract interface for acquiring intraday market data."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return provider identifier."""
        pass

    @abstractmethod
    def fetch_intraday_candles(
        self,
        symbol: str,
        session_date: date,
        interval: IntradayInterval = IntradayInterval.M5,
    ) -> List[IntradayCandle]:
        """Fetch raw intraday candles for a given symbol and trading date."""
        pass


class SyntheticTestIntradayProvider(BaseIntradayDataProvider):
    """Synthetic in-memory intraday provider strictly for deterministic testing."""

    def __init__(self, name: str = "synthetic_fixture") -> None:
        self._name = name
        self._registry: Dict[Tuple[str, date, IntradayInterval], List[IntradayCandle]] = {}

    @property
    def name(self) -> str:
        return self._name

    def register_candles(
        self,
        symbol: str,
        session_date: date,
        interval: IntradayInterval,
        candles: List[IntradayCandle],
    ) -> None:
        """Store test candles in the synthetic registry."""
        self._registry[(symbol.upper(), session_date, interval)] = list(candles)

    def fetch_intraday_candles(
        self,
        symbol: str,
        session_date: date,
        interval: IntradayInterval = IntradayInterval.M5,
    ) -> List[IntradayCandle]:
        """Retrieve registered test candles, or return empty list."""
        key = (symbol.upper(), session_date, interval)
        return list(self._registry.get(key, []))


class IntradayEngine:
    """Orchestrates intraday market data intake, quality audits, and safety guards.

    Enforces:
    - Supported instrument policy: restricts inference to authorized models (BHARTIARTL).
    - Market calendar session checks.
    - Zero fabrication of missing bars or model predictions.
    """

    def __init__(
        self,
        provider: BaseIntradayDataProvider,
        supported_symbols: Optional[Set[str]] = None,
    ) -> None:
        self.provider = provider
        self.supported_symbols = (
            {s.upper() for s in supported_symbols}
            if supported_symbols is not None
            else {"BHARTIARTL"}
        )

    def get_session_candles(
        self,
        symbol: str,
        session_date: date,
        interval: IntradayInterval = IntradayInterval.M5,
        allow_out_of_session: bool = False,
    ) -> Tuple[List[IntradayCandle], IntradayQualitySummary]:
        """Fetch and clean intraday candles for a session.

        Raises:
            ValidationError: If symbol is unsupported or invalid.
        """
        clean_symbol = symbol.strip().upper()
        if clean_symbol not in self.supported_symbols:
            raise ValidationError(
                f"Instrument '{clean_symbol}' is not supported for intraday processing. "
                f"Supported: {sorted(list(self.supported_symbols))}"
            )

        # Check market session calendar for this date
        test_dt = datetime.combine(session_date, REGULAR_MARKET_OPEN, tzinfo=IST)
        session_info = get_market_session(test_dt)
        if session_info.is_weekend or session_info.is_holiday:
            logger.info("Session date %s is a non-trading day (%s)", session_date, session_info.state.value)

        # Fetch from provider
        raw_candles = self.provider.fetch_intraday_candles(
            symbol=clean_symbol,
            session_date=session_date,
            interval=interval,
        )

        # Clean and audit
        result = clean_intraday_candles(
            records=raw_candles,
            expected_interval=interval,
            allow_out_of_session=allow_out_of_session,
        )

        return result.candles, result.summary

    def verify_forecast_readiness(self, symbol: str) -> Dict[str, Any]:
        """Verify whether an intraday predictive model is trained and available.

        Prevents running daily models on intraday bars or fabricating forecasts.
        """
        clean_symbol = symbol.strip().upper()
        if clean_symbol not in self.supported_symbols:
            return {
                "is_ready": False,
                "status": "UNSUPPORTED_INSTRUMENT",
                "message": f"Instrument '{clean_symbol}' is not in supported catalog.",
            }

        # Intraday prediction model is not yet implemented in Phase 16 / Day 69
        return {
            "is_ready": False,
            "status": "MODEL_UNAVAILABLE",
            "message": (
                "Intraday prediction model has not been trained or validated. "
                "Daily models (models/xgboost_direction.*) are strictly restricted from intraday inference."
            ),
        }
