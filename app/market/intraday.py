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

    @property
    def declared_delay(self) -> str:
        """Declared market data latency or delay description."""
        return "unknown"

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

    @property
    def declared_delay(self) -> str:
        return "synthetic test fixture (0s delay)"

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

    def compute_features(
        self,
        candles: Sequence[IntradayCandle],
        opening_range_minutes: int = 15,
    ) -> List["IntradayFeatureRecord"]:
        """Compute point-in-time intraday features with zero lookahead leakage."""
        return compute_intraday_features(candles=candles, opening_range_minutes=opening_range_minutes)


class OpeningRangeStatus(str, Enum):
    """Operational status of the session opening range calculation."""

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class IntradayFeatureRecord:
    """Canonical calculated intraday features for a single completed candle.

    Guarantees:
    - Zero Lookahead: 'available_at' is candle.bar_end_timestamp, representing the
      exact point-in-time when the candle closed and became historically observable.
    - Session Boundary Isolation: Returns, volatility, VWAP, and opening ranges reset
      at each session boundary and never cross calendar dates.
    - Zero Fabrication: If history or volume is insufficient or missing, features
      strictly evaluate to None.
    """

    symbol: str
    candle_timestamp: datetime
    available_at: datetime
    interval: IntradayInterval
    close: float
    volume: Optional[int]
    return_1bar: Optional[float]
    rolling_return_3bar: Optional[float]
    rolling_volatility_5bar: Optional[float]
    session_vwap: Optional[float]
    opening_range_high: Optional[float]
    opening_range_low: Optional[float]
    opening_range_status: OpeningRangeStatus
    opening_range_breakout: Optional[int]  # +1 (bullish), -1 (bearish), 0 (inside), None (before completion)

    def to_dict(self) -> Dict[str, Any]:
        """Convert feature record to dictionary for logging and downstream pipelines."""
        data = asdict(self)
        data["candle_timestamp"] = self.candle_timestamp.isoformat()
        data["available_at"] = self.available_at.isoformat()
        data["interval"] = self.interval.value
        data["opening_range_status"] = self.opening_range_status.value
        return data


def compute_intraday_features(
    candles: Sequence[IntradayCandle],
    opening_range_minutes: int = 15,
) -> List[IntradayFeatureRecord]:
    """Extract deterministic intraday features from completed IntradayCandle objects.

    Features Computed:
    1. return_1bar: Percentage close-to-close return vs previous completed candle in the same session.
    2. rolling_return_3bar: Percentage close-to-close return over 3 completed bars in the same session.
    3. rolling_volatility_5bar: Sample standard deviation (ddof=1) of 1-bar returns over 5 completed bars.
    4. session_vwap: Volume-weighted typical price (high + low + close)/3 cumulative from regular market open (09:15 IST).
       Resets at session start. Evaluates to None if any prior bar in session has missing/unreported volume or cum_vol == 0.
    5. opening_range (high, low, breakout): Highest high and lowest low during the first opening_range_minutes
       (default 15m). Evaluates to IN_PROGRESS before the range completes, COMPLETED at and after completion,
       or UNAVAILABLE if the session did not start at 09:15:00 IST with complete bars.

    Zero-Lookahead Invariants:
    - Input candles are validated and sorted chronologically before extraction.
    - Feature record 'available_at' equals candle.bar_end_timestamp.
    - Zero cross-session contamination: all window metrics reset on session date change.
    - Future candles have zero influence on past feature values.

    Args:
        candles: Sequence of IntradayCandle objects.
        opening_range_minutes: Duration of the opening range in minutes (default 15).

    Returns:
        List of IntradayFeatureRecord objects sorted by (symbol, candle_timestamp).
    """
    if not candles:
        return []

    # Sort strictly chronologically by (symbol, timestamp)
    sorted_candles = sorted(candles, key=lambda c: (c.symbol, c.timestamp))

    # Group candles by symbol for independent feature extraction
    by_symbol: Dict[str, List[IntradayCandle]] = defaultdict(list)
    for c in sorted_candles:
        by_symbol[c.symbol].append(c)

    all_features: List[IntradayFeatureRecord] = []

    for sym, sym_candles in by_symbol.items():
        # Track session state
        current_session_date: Optional[date] = None
        session_candles: List[IntradayCandle] = []
        session_returns: List[float] = []

        # VWAP accumulators
        cum_typical_volume: float = 0.0
        cum_volume: int = 0
        is_vwap_valid: bool = True

        # Opening range state
        opening_range_candles: List[IntradayCandle] = []
        opening_range_high: Optional[float] = None
        opening_range_low: Optional[float] = None
        opening_range_status: OpeningRangeStatus = OpeningRangeStatus.IN_PROGRESS
        is_opening_range_valid: bool = True

        for c in sym_candles:
            candle_date = c.timestamp.date()

            # Session boundary reset
            if current_session_date != candle_date:
                current_session_date = candle_date
                session_candles = []
                session_returns = []
                cum_typical_volume = 0.0
                cum_volume = 0
                is_vwap_valid = True
                opening_range_candles = []
                opening_range_high = None
                opening_range_low = None
                opening_range_status = OpeningRangeStatus.IN_PROGRESS

                # Check if session opens at official regular market open (09:15:00 IST)
                if c.timestamp.time() != REGULAR_MARKET_OPEN:
                    is_opening_range_valid = False
                    opening_range_status = OpeningRangeStatus.UNAVAILABLE
                else:
                    is_opening_range_valid = True

            session_candles.append(c)

            # 1. return_1bar calculation (strictly within same session)
            return_1bar: Optional[float] = None
            if len(session_candles) >= 2:
                prev_c = session_candles[-2]
                if prev_c.close > 0:
                    return_1bar = (c.close - prev_c.close) / prev_c.close
                    session_returns.append(return_1bar)

            # 2. rolling_return_3bar calculation (needs 3 prior completed candles in same session)
            rolling_return_3bar: Optional[float] = None
            if len(session_candles) >= 4:
                base_c = session_candles[-4]  # candle from 3 bars ago
                if base_c.close > 0:
                    rolling_return_3bar = (c.close - base_c.close) / base_c.close

            # 3. rolling_volatility_5bar calculation (needs 5 returns in same session)
            rolling_volatility_5bar: Optional[float] = None
            if len(session_returns) >= 5:
                window_returns = session_returns[-5:]
                mean_r = sum(window_returns) / 5.0
                variance = sum((r - mean_r) ** 2 for r in window_returns) / 4.0  # sample variance ddof=1
                rolling_volatility_5bar = math.sqrt(variance)

            # 4. session_vwap calculation
            session_vwap: Optional[float] = None
            if is_vwap_valid:
                if c.volume is not None and c.volume_reported and c.volume >= 0:
                    typical_price = (c.high + c.low + c.close) / 3.0
                    cum_typical_volume += typical_price * c.volume
                    cum_volume += c.volume
                    if cum_volume > 0:
                        session_vwap = round(cum_typical_volume / cum_volume, 4)
                else:
                    # Volume missing or unreported: invalidate VWAP for remainder of this session
                    is_vwap_valid = False
                    session_vwap = None

            # 5. Opening Range calculation
            opening_range_breakout: Optional[int] = None
            if is_opening_range_valid:
                # Time elapsed from session open to this bar's completion
                nominal_session_open = datetime.combine(candle_date, REGULAR_MARKET_OPEN, tzinfo=IST)
                elapsed_minutes = (c.bar_end_timestamp - nominal_session_open).total_seconds() / 60.0

                if opening_range_status == OpeningRangeStatus.IN_PROGRESS:
                    opening_range_candles.append(c)
                    if elapsed_minutes >= opening_range_minutes:
                        # Opening range is now completed!
                        opening_range_high = max(b.high for b in opening_range_candles)
                        opening_range_low = min(b.low for b in opening_range_candles)
                        opening_range_status = OpeningRangeStatus.COMPLETED

                if opening_range_status == OpeningRangeStatus.COMPLETED and opening_range_high is not None and opening_range_low is not None:
                    if c.close > opening_range_high:
                        opening_range_breakout = 1
                    elif c.close < opening_range_low:
                        opening_range_breakout = -1
                    else:
                        opening_range_breakout = 0
            else:
                opening_range_status = OpeningRangeStatus.UNAVAILABLE

            record = IntradayFeatureRecord(
                symbol=c.symbol,
                candle_timestamp=c.timestamp,
                available_at=c.bar_end_timestamp,
                interval=c.interval,
                close=c.close,
                volume=c.volume,
                return_1bar=return_1bar,
                rolling_return_3bar=rolling_return_3bar,
                rolling_volatility_5bar=rolling_volatility_5bar,
                session_vwap=session_vwap,
                opening_range_high=opening_range_high,
                opening_range_low=opening_range_low,
                opening_range_status=opening_range_status,
                opening_range_breakout=opening_range_breakout,
            )
            all_features.append(record)

    # Sort final records by (symbol, candle_timestamp)
    return sorted(all_features, key=lambda f: (f.symbol, f.candle_timestamp))


class IntradayTargetStatus(str, Enum):
    """Status classification of the forward prediction target for an intraday observation."""

    AVAILABLE = "AVAILABLE"
    SESSION_CLOSE_CUTOFF = "SESSION_CLOSE_CUTOFF"
    INCOMPLETE_HORIZON_GAP = "INCOMPLETE_HORIZON_GAP"
    MISSING_OUTCOME = "MISSING_OUTCOME"


@dataclass(frozen=True)
class IntradayDatasetObservation:
    """Canonical typed record representing a single point-in-time intraday observation.

    Combines point-in-time features with forward prediction targets and explicit
    realization timestamps to guarantee zero lookahead bias.
    """

    symbol: str
    session_date: date
    candle_timestamp: datetime
    available_at: datetime
    interval: IntradayInterval
    features: IntradayFeatureRecord
    target_horizon_bars: int
    target_return: Optional[float]
    target_direction: Optional[str]  # "UP", "DOWN", or None
    target_binary: Optional[int]     # 1, 0, or None
    target_realized_at: Optional[datetime]
    target_status: IntradayTargetStatus
    candle: Optional[IntradayCandle] = None

    @property
    def has_target(self) -> bool:
        """Return True if this observation has a complete, valid forward label."""
        return self.target_status == IntradayTargetStatus.AVAILABLE and self.target_binary is not None

    @property
    def feature_record(self) -> IntradayFeatureRecord:
        """Alias for features record."""
        return self.features

    @property
    def feature_available_at(self) -> datetime:
        """Alias for available_at timestamp."""
        return self.available_at

    @property
    def observation_timestamp(self) -> datetime:
        """Alias for candle_timestamp."""
        return self.candle_timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert observation to flat dictionary for tabular processing."""
        data = {
            "symbol": self.symbol,
            "session_date": self.session_date.isoformat(),
            "candle_timestamp": self.candle_timestamp.isoformat(),
            "available_at": self.available_at.isoformat(),
            "interval": self.interval.value,
            "target_horizon_bars": self.target_horizon_bars,
            "target_return": self.target_return,
            "target_direction": self.target_direction,
            "target_binary": self.target_binary,
            "target_realized_at": self.target_realized_at.isoformat() if self.target_realized_at else None,
            "target_status": self.target_status.value,
            "has_target": self.has_target,
        }
        # Flatten feature attributes
        for k, v in self.features.to_dict().items():
            if k not in data:
                data[f"feat_{k}"] = v
        return data


def assemble_intraday_dataset(
    candles: Sequence[IntradayCandle],
    horizon_bars: int = 3,
    opening_range_minutes: int = 15,
) -> List[IntradayDatasetObservation]:
    """Assemble a leakage-safe intraday dataset with point-in-time features and forward targets.

    Mathematical Formulation:
    - Feature Observation: Made at candle t, available strictly at t's close (available_at = candle_t.bar_end_timestamp).
    - Prediction Target: Close-to-close percentage return over the next H completed candles in the SAME session:
        target_return = (close_{t+H} - close_t) / close_t
        target_direction = 'UP' if target_return > 0.0 else 'DOWN'
        target_binary = 1 if target_return > 0.0 else 0
    - Equal Price Policy: target_return == 0.0 deterministically grouped into 'DOWN' (target_binary = 0).
    - Session Boundary Guard: If t+H exceeds available session candles (approaching 15:30:00 IST market close),
      the label is marked SESSION_CLOSE_CUTOFF (target is None). Cross-session targets are strictly prohibited.
    - Missing Candle Guard: If intermediate candles in the horizon are missing (intraday feed gap),
      the label is marked INCOMPLETE_HORIZON_GAP (target is None). Zero synthetic price interpolation.

    Args:
        candles: Sequence of validated IntradayCandle objects.
        horizon_bars: Number of future completed candles in the prediction horizon (default 3).
        opening_range_minutes: Minutes for opening range feature calculation (default 15).

    Returns:
        List of IntradayDatasetObservation sorted chronologically.
    """
    if not candles:
        return []
    if horizon_bars < 1:
        raise ValidationError(f"horizon_bars must be >= 1 (got {horizon_bars})")

    # Multi-symbol check for instrument isolation
    symbols = {c.symbol for c in candles}
    if len(symbols) > 1:
        raise ValidationError(
            f"Multiple symbols detected in candle sequence: {sorted(symbols)}. Single-symbol isolation is required."
        )

    # Sort strictly chronologically
    sorted_candles = sorted(candles, key=lambda c: (c.symbol, c.timestamp))

    # Compute features for all candles
    feature_records = compute_intraday_features(sorted_candles, opening_range_minutes=opening_range_minutes)
    features_by_key = {(f.symbol, f.candle_timestamp): f for f in feature_records}

    # Group by (symbol, session_date) to prevent cross-session target generation
    by_session: Dict[Tuple[str, date], List[IntradayCandle]] = defaultdict(list)
    for c in sorted_candles:
        by_session[(c.symbol, c.timestamp.date())].append(c)

    dataset: List[IntradayDatasetObservation] = []

    for (sym, s_date), s_candles in by_session.items():
        n_candles = len(s_candles)
        interval_seconds = s_candles[0].interval.duration_seconds

        for idx, current_candle in enumerate(s_candles):
            target_idx = idx + horizon_bars
            target_return: Optional[float] = None
            target_direction: Optional[str] = None
            target_binary: Optional[int] = None
            target_realized_at: Optional[datetime] = None
            target_status: IntradayTargetStatus

            if target_idx >= n_candles:
                # Horizon extends beyond session close
                target_status = IntradayTargetStatus.SESSION_CLOSE_CUTOFF
            else:
                target_candle = s_candles[target_idx]
                expected_delta = timedelta(seconds=horizon_bars * interval_seconds)
                actual_delta = target_candle.timestamp - current_candle.timestamp

                if actual_delta != expected_delta:
                    # Intraday missing candle gap between current candle and target candle
                    target_status = IntradayTargetStatus.INCOMPLETE_HORIZON_GAP
                else:
                    # Valid contiguous horizon within the same session
                    if current_candle.close > 0:
                        target_return = (target_candle.close - current_candle.close) / current_candle.close
                        if target_return > 0.0:
                            target_direction = "UP"
                            target_binary = 1
                        else:
                            target_direction = "DOWN"
                            target_binary = 0
                        target_realized_at = target_candle.bar_end_timestamp
                        target_status = IntradayTargetStatus.AVAILABLE
                    else:
                        target_status = IntradayTargetStatus.MISSING_OUTCOME

            feat_record = features_by_key.get((current_candle.symbol, current_candle.timestamp))
            if feat_record is None:
                continue

            obs = IntradayDatasetObservation(
                symbol=current_candle.symbol,
                session_date=s_date,
                candle_timestamp=current_candle.timestamp,
                available_at=current_candle.bar_end_timestamp,
                interval=current_candle.interval,
                features=feat_record,
                target_horizon_bars=horizon_bars,
                target_return=target_return,
                target_direction=target_direction,
                target_binary=target_binary,
                target_realized_at=target_realized_at,
                target_status=target_status,
                candle=current_candle,
            )
            dataset.append(obs)

    return sorted(dataset, key=lambda o: (o.symbol, o.candle_timestamp))


@dataclass(frozen=True)
class IntradaySplit:
    """Artifacts and temporal boundaries for a single chronological or walk-forward split."""

    fold: int
    train_observations: List[IntradayDatasetObservation]
    val_observations: List[IntradayDatasetObservation]
    embargo_observations: List[IntradayDatasetObservation]
    train_start: datetime
    train_end: datetime
    train_target_cutoff: datetime
    val_start: datetime
    val_end: datetime
    train_count: int
    val_count: int
    embargo_count: int
    train_up_count: int
    train_down_count: int
    val_up_count: int
    val_down_count: int
    train_indices: Sequence[int] = ()
    val_indices: Sequence[int] = ()
    embargo_indices: Sequence[int] = ()

    @property
    def fold_index(self) -> int:
        """Alias for fold index."""
        return self.fold

    @property
    def train_end_timestamp(self) -> datetime:
        """Alias for train_end timestamp."""
        return self.train_end

    @property
    def val_end_timestamp(self) -> datetime:
        """Alias for val_end timestamp."""
        return self.val_end

    def to_dict(self) -> Dict[str, Any]:
        """Serialize fold split metadata."""
        return {
            "fold": self.fold,
            "train_count": self.train_count,
            "val_count": self.val_count,
            "embargo_count": self.embargo_count,
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "train_target_cutoff": self.train_target_cutoff.isoformat(),
            "val_start": self.val_start.isoformat(),
            "val_end": self.val_end.isoformat(),
            "train_up_count": self.train_up_count,
            "train_down_count": self.train_down_count,
            "val_up_count": self.val_up_count,
            "val_down_count": self.val_down_count,
            "train_indices": list(self.train_indices),
            "val_indices": list(self.val_indices),
            "embargo_indices": list(self.embargo_indices),
        }


def generate_intraday_chronological_splits(
    observations: Sequence[IntradayDatasetObservation],
    n_splits: int = 3,
    min_train_ratio: float = 0.4,
    min_train_samples: int = 10,
    min_val_samples: int = 5,
) -> List[IntradaySplit]:
    """Generate chronological expanding-window walk-forward splits with strict target embargoes.

    Partitioning Mathematics & Temporal Leakage Invariants:
    1. Chronological Sorting: Observations are filtered to labeled rows (has_target is True)
       and partitioned strictly in forward chronological sequence. Random row shuffling is prohibited.
    2. Target Embargo Invariant: For any training partition ending at observation t_k, its label outcome
       realizes at T_cutoff = t_k.target_realized_at.
       Any subsequent observation whose feature window is active on or before T_cutoff is placed into
       the EMBARGO partition to prevent lookahead target overlap from contaminating validation metrics.
    3. Disjoint Partitioning: Train ∩ Embargo = ∅, Train ∩ Val = ∅, Embargo ∩ Val = ∅.

    Args:
        observations: Sequence of IntradayDatasetObservation records.
        n_splits: Number of expanding-window walk-forward folds (default 3).
        min_train_ratio: Minimum fraction of labeled data reserved for fold 0 training (default 0.4).
        min_train_samples: Minimum absolute sample count for initial training fold (default 10).
        min_val_samples: Minimum sample count for each validation fold (default 5).

    Returns:
        List of IntradaySplit objects.

    Raises:
        ValidationError: If dataset is unsorted, insufficient in sample count, or lacks labels.
    """
    if not observations:
        raise ValidationError("Cannot split an empty observation sequence.")

    # Build reference mapping for index retrieval
    obs_to_idx = {id(o): idx for idx, o in enumerate(observations)}

    # Filter strictly to labeled observations
    labeled = [o for o in observations if o.has_target]
    if not labeled:
        raise ValidationError("Observation sequence contains zero observations with valid targets (has_target=True).")

    # Verify chronological ordering
    for i in range(len(labeled) - 1):
        if labeled[i].candle_timestamp > labeled[i + 1].candle_timestamp:
            raise ValidationError("Observations must be sorted strictly in ascending chronological order.")

    N = len(labeled)
    min_required = min_train_samples + (n_splits * min_val_samples)
    if N < min_required:
        raise ValidationError(
            f"Insufficient dataset observations: {N} labeled samples for {n_splits} folds with min_train={min_train_samples} "
            f"and min_val={min_val_samples} (requires at least {min_required} samples)."
        )

    initial_train_size = max(min_train_samples, int(N * min_train_ratio))
    val_pool = N - initial_train_size
    step_size = val_pool // n_splits

    if step_size < min_val_samples:
        raise ValidationError(
            f"Calculated validation fold size ({step_size}) is less than min_val_samples ({min_val_samples})."
        )

    splits: List[IntradaySplit] = []

    for fold in range(n_splits):
        train_end_idx = initial_train_size + (fold * step_size)
        train_obs = labeled[:train_end_idx]

        last_train = train_obs[-1]
        target_cutoff = last_train.target_realized_at
        if target_cutoff is None:
            raise ValidationError(f"Last training observation in fold {fold} has None target_realized_at.")

        # Find observations that fall within the embargo window
        # (any observation that was forming or realized on or before training target realization cutoff)
        rem_obs = labeled[train_end_idx:]
        embargo_obs: List[IntradayDatasetObservation] = []
        val_candidates: List[IntradayDatasetObservation] = []

        for candidate in rem_obs:
            if candidate.candle_timestamp < target_cutoff or candidate.available_at <= target_cutoff:
                embargo_obs.append(candidate)
            else:
                val_candidates.append(candidate)

        # Bounded validation window for this fold
        val_size = min(step_size, len(val_candidates))
        if val_size < min_val_samples:
            # If embargo reduced validation below threshold, take available or report fold limitation
            val_obs = val_candidates
        else:
            val_obs = val_candidates[:val_size]

        if not val_obs:
            raise ValidationError(
                f"Fold {fold} has 0 validation observations after applying target embargo to {target_cutoff}."
            )

        train_up = sum(1 for o in train_obs if o.target_binary == 1)
        train_down = sum(1 for o in train_obs if o.target_binary == 0)
        val_up = sum(1 for o in val_obs if o.target_binary == 1)
        val_down = sum(1 for o in val_obs if o.target_binary == 0)

        train_indices = [obs_to_idx[id(o)] for o in train_obs if id(o) in obs_to_idx]
        val_indices = [obs_to_idx[id(o)] for o in val_obs if id(o) in obs_to_idx]
        embargo_indices = [obs_to_idx[id(o)] for o in embargo_obs if id(o) in obs_to_idx]

        split = IntradaySplit(
            fold=fold,
            train_observations=train_obs,
            val_observations=val_obs,
            embargo_observations=embargo_obs,
            train_start=train_obs[0].candle_timestamp,
            train_end=train_obs[-1].candle_timestamp,
            train_target_cutoff=target_cutoff,
            val_start=val_obs[0].candle_timestamp,
            val_end=val_obs[-1].candle_timestamp,
            train_count=len(train_obs),
            val_count=len(val_obs),
            embargo_count=len(embargo_obs),
            train_up_count=train_up,
            train_down_count=train_down,
            val_up_count=val_up,
            val_down_count=val_down,
            train_indices=train_indices,
            val_indices=val_indices,
            embargo_indices=embargo_indices,
        )
        splits.append(split)

    return splits


# =========================================================================
# DAY 72: Intraday Baseline Benchmark Evaluation & Out-of-Fold Audit
# =========================================================================


@dataclass(frozen=True)
class IntradayBaselinePrediction:
    """Out-of-fold directional prediction record from an intraday baseline model."""

    symbol: str
    session_date: date
    candle_timestamp: datetime
    prediction_timestamp: datetime
    target_realized_at: datetime
    target_horizon_bars: int
    fold: int
    model_name: str
    predicted_probability: float  # Continuous probability of UP in [0.0, 1.0]
    predicted_binary: int         # Hard binary prediction (1 for UP, 0 for DOWN)
    actual_binary: int            # Ground truth direction (1 for UP, 0 for DOWN)
    actual_return: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize prediction metadata."""
        return {
            "symbol": self.symbol,
            "session_date": self.session_date.isoformat(),
            "candle_timestamp": self.candle_timestamp.isoformat(),
            "prediction_timestamp": self.prediction_timestamp.isoformat(),
            "target_realized_at": self.target_realized_at.isoformat(),
            "target_horizon_bars": self.target_horizon_bars,
            "fold": self.fold,
            "model_name": self.model_name,
            "predicted_probability": round(self.predicted_probability, 4),
            "predicted_binary": self.predicted_binary,
            "actual_binary": self.actual_binary,
            "actual_return": round(self.actual_return, 6) if self.actual_return is not None else None,
        }


@dataclass(frozen=True)
class IntradayEvaluationMetrics:
    """Comprehensive performance metrics for an intraday classifier."""

    model_name: str
    sample_count: int
    up_count: int
    down_count: int
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    accuracy: float
    precision_up: Optional[float]
    recall_up: Optional[float]
    f1_up: Optional[float]
    balanced_accuracy: Optional[float]
    brier_score: float
    log_loss: float
    confusion_matrix: List[List[int]]  # [[TN, FP], [FN, TP]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary with rounded floats."""
        return {
            "model_name": self.model_name,
            "sample_count": self.sample_count,
            "up_count": self.up_count,
            "down_count": self.down_count,
            "true_positives": self.true_positives,
            "true_negatives": self.true_negatives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "accuracy": round(self.accuracy, 4),
            "precision_up": round(self.precision_up, 4) if self.precision_up is not None else None,
            "recall_up": round(self.recall_up, 4) if self.recall_up is not None else None,
            "f1_up": round(self.f1_up, 4) if self.f1_up is not None else None,
            "balanced_accuracy": round(self.balanced_accuracy, 4) if self.balanced_accuracy is not None else None,
            "brier_score": round(self.brier_score, 4),
            "log_loss": round(self.log_loss, 4),
            "confusion_matrix": self.confusion_matrix,
        }


def compute_intraday_evaluation_metrics(
    y_true: Sequence[int],
    y_pred: Sequence[int],
    y_prob: Sequence[float],
    model_name: str = "baseline",
    eps: float = 1e-15,
) -> IntradayEvaluationMetrics:
    """Calculate comprehensive evaluation metrics handling edge cases and undefined metrics explicitly.

    Mathematical Formulations & Edge Case Guarantees:
    - Confusion Matrix: [[TN, FP], [FN, TP]]
    - Accuracy: (TP + TN) / Total
    - Precision (UP): TP / (TP + FP) if (TP + FP) > 0 else None (explicitly undefined, never fabricated as 0.0)
    - Recall (UP): TP / (TP + FN) if (TP + FN) > 0 else None
    - F1 (UP): 2 * (Prec * Rec) / (Prec + Rec) if Prec and Rec are defined and sum > 0 else None
    - Balanced Accuracy: 0.5 * (Sensitivity + Specificity) where:
        Sensitivity = Recall(UP) = TP / (TP + FN)
        Specificity = Recall(DOWN) = TN / (TN + FP)
        If either class has 0 true samples, balanced_accuracy evaluates to None.
    - Brier Score: (1/N) * sum((prob - true)^2)
    - Log Loss: Binary cross-entropy with epsilon clipping to [eps, 1-eps].
    """
    if len(y_true) != len(y_pred) or len(y_true) != len(y_prob):
        raise ValidationError(
            f"Length mismatch: len(y_true)={len(y_true)}, len(y_pred)={len(y_pred)}, len(y_prob)={len(y_prob)}"
        )
    if len(y_true) == 0:
        raise ValidationError("Cannot calculate evaluation metrics on empty prediction sequences.")

    N = len(y_true)
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    up_count = sum(1 for yt in y_true if yt == 1)
    down_count = sum(1 for yt in y_true if yt == 0)

    accuracy = (tp + tn) / N

    # Precision UP
    precision_up = tp / (tp + fp) if (tp + fp) > 0 else None

    # Recall UP (Sensitivity)
    recall_up = tp / (tp + fn) if (tp + fn) > 0 else None

    # Specificity (Recall DOWN)
    specificity = tn / (tn + fp) if (tn + fp) > 0 else None

    # F1 UP
    if precision_up is not None and recall_up is not None and (precision_up + recall_up) > 0:
        f1_up = 2.0 * (precision_up * recall_up) / (precision_up + recall_up)
    else:
        f1_up = None

    # Balanced Accuracy
    if recall_up is not None and specificity is not None:
        balanced_accuracy = 0.5 * (recall_up + specificity)
    else:
        balanced_accuracy = None

    # Brier Score
    brier_score = sum((float(p) - float(yt)) ** 2 for yt, p in zip(y_true, y_prob)) / N

    # Log Loss (with epsilon clipping)
    loss_sum = 0.0
    for yt, p in zip(y_true, y_prob):
        p_clipped = max(eps, min(1.0 - eps, float(p)))
        loss_sum -= (float(yt) * math.log(p_clipped) + (1.0 - float(yt)) * math.log(1.0 - p_clipped))
    log_loss = loss_sum / N

    return IntradayEvaluationMetrics(
        model_name=model_name,
        sample_count=N,
        up_count=up_count,
        down_count=down_count,
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn,
        accuracy=accuracy,
        precision_up=precision_up,
        recall_up=recall_up,
        f1_up=f1_up,
        balanced_accuracy=balanced_accuracy,
        brier_score=brier_score,
        log_loss=log_loss,
        confusion_matrix=[[tn, fp], [fn, tp]],
    )


class IntradayBaseline:
    """Protocol for intraday baseline predictors."""

    name: str

    def fit(self, train_obs: Sequence[IntradayDatasetObservation]) -> None:
        """Fit baseline strategy strictly from the training partition."""
        pass

    def predict(self, obs: IntradayDatasetObservation) -> Tuple[int, float]:
        """Predict directional class and continuous probability for an observation.

        Returns:
            Tuple of (predicted_binary: 0 or 1, predicted_probability: float in [0.0, 1.0]).
        """
        raise NotImplementedError


class MajorityClassBaseline(IntradayBaseline):
    """Predicts majority directional class strictly using training partition labels.

    Deterministic Tie-Breaking Rule:
    If UP count == DOWN count, predict 0 (DOWN) with probability 0.0,
    conforming to the conservative zero-return non-positive directional default.
    """

    name = "majority_class"

    def __init__(self) -> None:
        self.majority_label: int = 0
        self.majority_prob: float = 0.0

    def fit(self, train_obs: Sequence[IntradayDatasetObservation]) -> None:
        labeled = [o for o in train_obs if o.has_target and o.target_binary is not None]
        if not labeled:
            self.majority_label = 0
            self.majority_prob = 0.0
            return

        up_count = sum(1 for o in labeled if o.target_binary == 1)
        down_count = sum(1 for o in labeled if o.target_binary == 0)

        if up_count > down_count:
            self.majority_label = 1
            self.majority_prob = 1.0
        else:
            self.majority_label = 0
            self.majority_prob = 0.0

    def predict(self, obs: IntradayDatasetObservation) -> Tuple[int, float]:
        return self.majority_label, self.majority_prob


class ConstantProbabilityBaseline(IntradayBaseline):
    """Predicts a fixed reference probability of 0.50 for UP and 0.50 for DOWN.

    This is an uninformative reference anchor, not a trained statistical model.
    Hard classification maps to 0 (DOWN) by conservative decision boundary (requires p > 0.50 for UP).
    Probability metrics (Brier score and Log Loss) evaluate directly against the continuous 0.50 probability.
    """

    name = "constant_probability_0.50"

    def fit(self, train_obs: Sequence[IntradayDatasetObservation]) -> None:
        pass  # Zero parameters fitted

    def predict(self, obs: IntradayDatasetObservation) -> Tuple[int, float]:
        return 0, 0.50


class TrainingPriorBaseline(IntradayBaseline):
    """Predicts the empirical base-rate prior P(UP) observed in the training partition.

    Hard prediction maps to 1 if p_up > 0.50, else 0.
    Probability metrics evaluate against the actual continuous base rate p_up.
    Empty training partition safeguard: defaults to 0.50.
    """

    name = "training_prior"

    def __init__(self) -> None:
        self.p_up: float = 0.50
        self.hard_label: int = 0

    def fit(self, train_obs: Sequence[IntradayDatasetObservation]) -> None:
        labeled = [o for o in train_obs if o.has_target and o.target_binary is not None]
        if not labeled:
            self.p_up = 0.50
            self.hard_label = 0
            return

        up_count = sum(1 for o in labeled if o.target_binary == 1)
        self.p_up = up_count / len(labeled)
        self.hard_label = 1 if self.p_up > 0.50 else 0

    def predict(self, obs: IntradayDatasetObservation) -> Tuple[int, float]:
        return self.hard_label, self.p_up


class PersistenceBaseline(IntradayBaseline):
    """Predicts direction of the most recent completed 1-bar return in the same session.

    Formulation:
    - If return_1bar > 0.0: predict 1 (UP) with probability 1.0.
    - If return_1bar <= 0.0: predict 0 (DOWN) with probability 0.0.
    - If return_1bar is None (e.g. session open bar): fallback to training prior p_up.
    """

    name = "persistence_return_1bar"

    def __init__(self) -> None:
        self.fallback_p_up: float = 0.50
        self.fallback_hard_label: int = 0

    def fit(self, train_obs: Sequence[IntradayDatasetObservation]) -> None:
        labeled = [o for o in train_obs if o.has_target and o.target_binary is not None]
        if not labeled:
            self.fallback_p_up = 0.50
            self.fallback_hard_label = 0
            return

        up_count = sum(1 for o in labeled if o.target_binary == 1)
        self.fallback_p_up = up_count / len(labeled)
        self.fallback_hard_label = 1 if self.fallback_p_up > 0.50 else 0

    def predict(self, obs: IntradayDatasetObservation) -> Tuple[int, float]:
        ret1 = obs.features.return_1bar
        if ret1 is not None:
            if ret1 > 0.0:
                return 1, 1.0
            else:
                return 0, 0.0
        return self.fallback_hard_label, self.fallback_p_up


@dataclass(frozen=True)
class IntradayFoldResult:
    """Evaluation result for a single walk-forward fold."""

    fold: int
    model_name: str
    train_count: int
    train_up_count: int
    train_down_count: int
    val_count: int
    metrics: IntradayEvaluationMetrics
    predictions: List[IntradayBaselinePrediction]

    def to_dict(self) -> Dict[str, Any]:
        """Convert fold result to dictionary."""
        return {
            "fold": self.fold,
            "model_name": self.model_name,
            "train_count": self.train_count,
            "train_up_count": self.train_up_count,
            "train_down_count": self.train_down_count,
            "val_count": self.val_count,
            "metrics": self.metrics.to_dict(),
            "prediction_count": len(self.predictions),
        }


@dataclass(frozen=True)
class IntradayBaselineAudit:
    """Complete walk-forward evaluation audit report for an intraday predictor."""

    model_name: str
    n_splits: int
    total_observations: int
    eligible_observations: int
    excluded_observations: int
    exclusion_reasons: Dict[str, int]
    is_synthetic_fixture: bool
    empirical_status: str  # "BLOCKED_NO_EMPIRICAL_DATA" or "EVALUATED"
    fold_results: List[IntradayFoldResult]
    aggregate_metrics: Optional[IntradayEvaluationMetrics]

    def to_dict(self) -> Dict[str, Any]:
        """Convert complete audit to dictionary."""
        return {
            "model_name": self.model_name,
            "n_splits": self.n_splits,
            "total_observations": self.total_observations,
            "eligible_observations": self.eligible_observations,
            "excluded_observations": self.excluded_observations,
            "exclusion_reasons": self.exclusion_reasons,
            "is_synthetic_fixture": self.is_synthetic_fixture,
            "empirical_status": self.empirical_status,
            "fold_results": [f.to_dict() for f in self.fold_results],
            "aggregate_metrics": self.aggregate_metrics.to_dict() if self.aggregate_metrics else None,
        }


def evaluate_intraday_baseline_walk_forward(
    observations: Sequence[IntradayDatasetObservation],
    splits: Sequence[IntradaySplit],
    baseline: IntradayBaseline,
) -> IntradayBaselineAudit:
    """Evaluate an intraday baseline across expanding-window walk-forward splits with full out-of-fold auditing.

    Protocol Invariants:
    1. Zero Validation Leakage: The baseline is fitted on split.train_observations only.
    2. Zero Duplicate Pooling: Checks that validation observation timestamps across folds are 100% disjoint.
       If any observation timestamp appears in multiple folds, an error is raised.
    3. Audit Trail: Tracks total observations, eligible observations, and counts per exclusion reason
       (SESSION_CLOSE_CUTOFF, INCOMPLETE_HORIZON_GAP, MISSING_OUTCOME).
    4. Synthetic Data Isolation: Detects if observations originate from synthetic fixtures (source == "synthetic_test")
       and flags empirical_status as "BLOCKED_NO_EMPIRICAL_DATA" to prevent reporting test fixtures as market evidence.

    Args:
        observations: Sequence of all IntradayDatasetObservation objects in the dataset.
        splits: Pre-computed sequence of disjoint IntradaySplit objects.
        baseline: Instantiated IntradayBaseline predictor.

    Returns:
        IntradayBaselineAudit with fold results and aggregate out-of-fold metrics.
    """
    if not observations:
        raise ValidationError("Cannot evaluate baselines on an empty observation sequence.")
    if not splits:
        raise ValidationError("Cannot evaluate baselines without walk-forward splits.")

    total_obs = len(observations)
    eligible_obs = sum(1 for o in observations if o.has_target)
    excluded_obs = total_obs - eligible_obs

    exclusion_reasons: Dict[str, int] = defaultdict(int)
    for o in observations:
        if not o.has_target:
            exclusion_reasons[o.target_status.value] += 1

    # Check for synthetic test fixture usage
    is_synthetic = any(
        o.candle is not None and o.candle.source == "synthetic_test"
        for o in observations
    )
    empirical_status = "BLOCKED_NO_EMPIRICAL_DATA" if is_synthetic else "EVALUATED"

    fold_results: List[IntradayFoldResult] = []
    seen_val_timestamps: Set[Tuple[str, datetime]] = set()
    all_oof_predictions: List[IntradayBaselinePrediction] = []

    for split in splits:
        # Fit baseline on training partition only
        baseline.fit(split.train_observations)

        fold_preds: List[IntradayBaselinePrediction] = []
        for val_obs in split.val_observations:
            if not val_obs.has_target or val_obs.target_binary is None or val_obs.target_realized_at is None:
                continue

            ts_key = (val_obs.symbol, val_obs.candle_timestamp)
            if ts_key in seen_val_timestamps:
                raise ValidationError(
                    f"Duplicate validation observation timestamp detected across folds: {ts_key}. "
                    f"Out-of-fold windows must not overlap."
                )
            seen_val_timestamps.add(ts_key)

            pred_binary, pred_prob = baseline.predict(val_obs)

            pred = IntradayBaselinePrediction(
                symbol=val_obs.symbol,
                session_date=val_obs.session_date,
                candle_timestamp=val_obs.candle_timestamp,
                prediction_timestamp=val_obs.available_at,
                target_realized_at=val_obs.target_realized_at,
                target_horizon_bars=val_obs.target_horizon_bars,
                fold=split.fold,
                model_name=baseline.name,
                predicted_probability=pred_prob,
                predicted_binary=pred_binary,
                actual_binary=val_obs.target_binary,
                actual_return=val_obs.target_return,
            )
            fold_preds.append(pred)
            all_oof_predictions.append(pred)

        # Compute fold metrics
        if fold_preds:
            y_true_fold = [p.actual_binary for p in fold_preds]
            y_pred_fold = [p.predicted_binary for p in fold_preds]
            y_prob_fold = [p.predicted_probability for p in fold_preds]
            fold_metrics = compute_intraday_evaluation_metrics(
                y_true=y_true_fold,
                y_pred=y_pred_fold,
                y_prob=y_prob_fold,
                model_name=baseline.name,
            )
        else:
            raise ValidationError(f"Fold {split.fold} produced 0 eligible validation predictions.")

        fold_result = IntradayFoldResult(
            fold=split.fold,
            model_name=baseline.name,
            train_count=split.train_count,
            train_up_count=split.train_up_count,
            train_down_count=split.train_down_count,
            val_count=len(fold_preds),
            metrics=fold_metrics,
            predictions=fold_preds,
        )
        fold_results.append(fold_result)

    # Compute aggregate out-of-fold metrics across all disjoint validation folds
    if all_oof_predictions:
        y_true_all = [p.actual_binary for p in all_oof_predictions]
        y_pred_all = [p.predicted_binary for p in all_oof_predictions]
        y_prob_all = [p.predicted_probability for p in all_oof_predictions]
        aggregate_metrics = compute_intraday_evaluation_metrics(
            y_true=y_true_all,
            y_pred=y_pred_all,
            y_prob=y_prob_all,
            model_name=baseline.name,
        )
    else:
        aggregate_metrics = None

    return IntradayBaselineAudit(
        model_name=baseline.name,
        n_splits=len(splits),
        total_observations=total_obs,
        eligible_observations=eligible_obs,
        excluded_observations=excluded_obs,
        exclusion_reasons=dict(exclusion_reasons),
        is_synthetic_fixture=is_synthetic,
        empirical_status=empirical_status,
        fold_results=fold_results,
        aggregate_metrics=aggregate_metrics,
    )
