"""Intraday Session Recorder and Isolated Archive Store.

Provides safe, restartable intraday session capture for authorized Indian equities
(NSE/BSE), enforcing:
1. Strict instrument authorization (BHARTIARTL default; indices prohibited).
2. Timezone-normalized timestamps in Asia/Kolkata (IST).
3. Session calendar awareness: distinguishes market closure from provider outages.
4. Completed-candle boundary validation: forming/partial candles are rejected or deferred.
5. Strict physical OHLC relationships and non-fabrication of missing volume.
6. Append-only isolated local archive with idempotent restart recovery and conflicting
   duplicate quarantine.
7. Explicit data provenance tagging (synthetic_test, provider_observation, validated_archive).
8. Strict separation from protected prediction database (data/predictions.db).
9. Empirical evaluation readiness verification gate.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
import json
import math
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union
from zoneinfo import ZoneInfo

from app.core.logging_config import get_logger, sanitize_log_field
from app.core.schemas import ValidationError
from app.market.intraday import (
    BaseIntradayDataProvider,
    IntradayCandle,
    IntradayCleaningResult,
    IntradayInterval,
    clean_intraday_candles,
)
from app.market.session import (
    IST,
    MarketSessionInfo,
    MarketSessionState,
    NSE_HOLIDAYS_2026,
    get_market_session,
)

logger = get_logger(__name__)

# Protected file paths that MUST NEVER be targeted by the recorder
PROTECTED_DB_NAMES = {"predictions.db", "predictions.db-journal", "predictions.db-wal"}


class CandleProvenance(str, Enum):
    """Data provenance origin for recorded intraday candlestick observations."""

    SYNTHETIC_TEST = "synthetic_test"
    PROVIDER_OBSERVATION = "provider_observation"
    VALIDATED_ARCHIVE = "validated_archive"


class RecorderStatus(str, Enum):
    """Operational lifecycle state of the intraday session recorder."""

    READY = "READY"
    RECORDING = "RECORDING"
    DEGRADED = "DEGRADED"
    STOPPED = "STOPPED"
    MARKET_CLOSED = "MARKET_CLOSED"


class EvaluationReadinessStatus(str, Enum):
    """Evaluation readiness gate status for downstream backtesting and walk-forward audits."""

    READY = "READY"
    BLOCKED_NO_VERIFIED_INTRADAY_PROVIDER = "BLOCKED_NO_VERIFIED_INTRADAY_PROVIDER"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    INSUFFICIENT_COVERAGE = "INSUFFICIENT_COVERAGE"
    CONTAMINATED_SYNTHETIC = "CONTAMINATED_SYNTHETIC"


@dataclass(frozen=True)
class RecordedCandleRecord:
    """Canonical immutable stored record of an intraday candle in the isolated archive."""

    symbol: str
    timestamp: datetime
    interval: IntradayInterval
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int]
    volume_reported: bool
    source: str
    provenance: CandleProvenance
    capture_timestamp: datetime
    is_completed: bool
    data_quality_flags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Validate symbol
        if not self.symbol or not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValidationError("symbol cannot be empty")
        object.__setattr__(self, "symbol", self.symbol.strip().upper())

        # Normalize timestamps to Asia/Kolkata (IST)
        for ts_attr in ("timestamp", "capture_timestamp"):
            val = getattr(self, ts_attr)
            if not isinstance(val, datetime):
                raise ValidationError(f"{ts_attr} must be a valid datetime instance")
            if val.tzinfo is None:
                object.__setattr__(self, ts_attr, val.replace(tzinfo=IST))
            else:
                object.__setattr__(self, ts_attr, val.astimezone(IST))

        # Enforce provenance type
        if isinstance(self.provenance, str):
            object.__setattr__(self, "provenance", CandleProvenance(self.provenance))

        # Enforce interval type
        if isinstance(self.interval, str):
            object.__setattr__(self, "interval", IntradayInterval.from_string(self.interval))

    @property
    def bar_end_timestamp(self) -> datetime:
        """Nominal bar closing timestamp."""
        return self.timestamp + timedelta(seconds=self.interval.duration_seconds)

    def to_intraday_candle(self) -> IntradayCandle:
        """Convert record back to canonical IntradayCandle."""
        return IntradayCandle(
            symbol=self.symbol,
            timestamp=self.timestamp,
            interval=self.interval,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            source=self.source,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize record to dictionary with ISO formatted timestamps."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["capture_timestamp"] = self.capture_timestamp.isoformat()
        data["interval"] = self.interval.value
        data["provenance"] = self.provenance.value
        data["bar_end_timestamp"] = self.bar_end_timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecordedCandleRecord":
        """Deserialize record from dictionary representation."""
        ts_raw = data["timestamp"]
        ts = datetime.fromisoformat(ts_raw) if isinstance(ts_raw, str) else ts_raw
        cap_raw = data["capture_timestamp"]
        cap_ts = datetime.fromisoformat(cap_raw) if isinstance(cap_raw, str) else cap_raw

        return cls(
            symbol=str(data["symbol"]),
            timestamp=ts,
            interval=IntradayInterval.from_string(str(data["interval"])),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
            volume=int(data["volume"]) if data.get("volume") is not None else None,
            volume_reported=bool(data.get("volume_reported", data.get("volume") is not None)),
            source=str(data.get("source", "unknown")),
            provenance=CandleProvenance(str(data.get("provenance", CandleProvenance.PROVIDER_OBSERVATION.value))),
            capture_timestamp=cap_ts,
            is_completed=bool(data.get("is_completed", True)),
            data_quality_flags=list(data.get("data_quality_flags", [])),
        )


@dataclass(frozen=True)
class ArchiveStats:
    """Summary metrics of the isolated intraday archive."""

    total_records: int
    symbols: List[str]
    intervals: List[str]
    min_timestamp: Optional[str]
    max_timestamp: Optional[str]
    provenance_counts: Dict[str, int]
    quarantined_count: int
    corrupted_records_count: int = 0


@dataclass(frozen=True)
class EvaluationReadinessReport:
    """Report detailing whether captured archive data satisfies empirical evaluation criteria."""

    status: EvaluationReadinessStatus
    is_ready_for_evaluation: bool
    reason: str
    total_candles: int
    provenance_counts: Dict[str, int]
    symbol: str
    interval: str
    gaps_count: int
    issues: List[str]


@dataclass(frozen=True)
class SessionCaptureSummary:
    """Consolidated summary of a bounded manual session recording run."""

    symbol: str
    interval: str
    status: str
    termination_reason: str
    cycles_completed: int
    total_runtime_seconds: float
    total_fetched: int
    total_persisted: int
    total_idempotent: int
    total_deferred: int
    total_quarantined: int
    cycle_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize summary to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class OperationalDiagnostics:
    """Operational diagnostics snapshot of recorder, provider, archive, and readiness state."""

    recorder_status: str
    last_successful_poll_time: Optional[str]
    provider_name: str
    provider_declared_delay: str
    latest_source_timestamp: Optional[str]
    latest_observation_timestamp: Optional[str]
    total_persisted_records: int
    provenance_counts: Dict[str, int]
    latest_capture_error: Optional[str]
    last_error_retry_count: int
    archive_file_exists: bool
    archive_corrupted_records_count: int
    quarantine_records_count: int
    readiness_status: str
    readiness_blocking_reasons: List[str]
    archive_file_health: str = "HEALTHY"
    quarantine_file_health: str = "CLEAN"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize diagnostics report to dictionary."""
        return asdict(self)


def _field_isclose(a: Optional[float], b: Optional[float], abs_tol: float = 1e-5) -> bool:
    """Compare two float values for near-equality, treating None == None as True."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return math.isclose(a, b, abs_tol=abs_tol)


class IntradayArchiveStore:
    """Thread-safe, append-only isolated store for intraday candle observations.

    Guarantees:
    - Absolute physical isolation from predictions.db (aborts if configured there).
    - Deduplication: identical observations are collapsing idempotently.
    - Conflicting duplicate detection: differing OHLCV for same bar is quarantined.
    - Crash/restart recovery: loads existing indices on initialization.
    """

    def __init__(
        self,
        archive_path: Union[str, Path] = "data/intraday/intraday_archive.jsonl",
        quarantine_path: Union[str, Path] = "data/intraday/quarantined_candles.jsonl",
    ) -> None:
        self.archive_path = Path(archive_path)
        self.quarantine_path = Path(quarantine_path)
        self._lock = threading.Lock()

        # Enforce strict separation from protected predictions database
        self._validate_paths()

        # In-memory index of stored records: (symbol, interval, timestamp_iso) -> RecordedCandleRecord
        self._index: Dict[Tuple[str, str, str], RecordedCandleRecord] = {}
        self._quarantined_count = 0
        self._corrupted_records_count = 0
        self._corrupted_record_details: List[Dict[str, Any]] = []

        # Create parent directories safely
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        self.quarantine_path.parent.mkdir(parents=True, exist_ok=True)

        # Recover index from existing archive file
        self._recover_index()

    @property
    def corrupted_records_count(self) -> int:
        """Count of malformed or corrupted records found in archive file."""
        return self._corrupted_records_count

    @property
    def corrupted_record_details(self) -> List[Dict[str, Any]]:
        """List of corrupted record diagnostics."""
        return list(self._corrupted_record_details)

    def _validate_paths(self) -> None:
        """Ensure storage paths never point to protected prediction database."""
        for p in (self.archive_path, self.quarantine_path):
            if p.name in PROTECTED_DB_NAMES:
                raise ValueError(
                    f"Illegal storage path: '{p}'. Cannot target protected prediction database."
                )
            # Check normalized string path
            norm_str = str(p).replace("\\", "/").lower()
            if "predictions.db" in norm_str:
                raise ValueError(
                    f"Illegal storage path: '{p}'. Cannot point inside protected predictions database."
                )

    def _recover_index(self) -> None:
        """Populate index from existing archive file to enable idempotent restart."""
        with self._lock:
            if self.archive_path.exists():
                try:
                    with open(self.archive_path, "r", encoding="utf-8") as f:
                        for line_num, line in enumerate(f, start=1):
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                record = RecordedCandleRecord.from_dict(data)
                                # Validate canonical candle physical integrity
                                _ = record.to_intraday_candle()
                                key = (
                                    record.symbol,
                                    record.interval.value,
                                    record.timestamp.isoformat(),
                                )
                                self._index[key] = record
                            except Exception as e:
                                self._corrupted_records_count += 1
                                self._corrupted_record_details.append(
                                    {"line_number": line_num, "error": str(e)}
                                )
                                logger.warning(
                                    "Skipping corrupt archive record at %s:%d: %s",
                                    self.archive_path,
                                    line_num,
                                    e,
                                )
                except Exception as exc:
                    logger.error("Failed to recover index from %s: %s", self.archive_path, exc)

            if self.quarantine_path.exists():
                try:
                    with open(self.quarantine_path, "r", encoding="utf-8") as f:
                        count = sum(1 for line in f if line.strip())
                        self._quarantined_count = count
                except Exception as exc:
                    logger.warning("Failed to count quarantined records: %s", exc)

    def append(self, record: RecordedCandleRecord) -> Tuple[bool, str]:
        """Append a validated candle record to the archive.

        Returns:
            Tuple of (success: bool, status_message: str)
            - (True, "persisted") if newly written
            - (True, "idempotent_duplicate") if already present with identical OHLCV
            - (False, "conflicting_duplicate_quarantined") if conflicting OHLCV detected
        """
        key = (record.symbol, record.interval.value, record.timestamp.isoformat())

        with self._lock:
            # Check for existing observation
            if key in self._index:
                existing = self._index[key]
                # Compare OHLC and volume
                is_identical = (
                    _field_isclose(existing.open, record.open)
                    and _field_isclose(existing.high, record.high)
                    and _field_isclose(existing.low, record.low)
                    and _field_isclose(existing.close, record.close)
                    and existing.volume == record.volume
                )
                if is_identical:
                    return (True, "idempotent_duplicate")

                # Conflicting duplicate detected -> Quarantine!
                quarantine_entry = {
                    "quarantine_reason": "conflicting_duplicate",
                    "quarantined_at": datetime.now(IST).isoformat(),
                    "existing_record": existing.to_dict(),
                    "conflicting_record": record.to_dict(),
                }
                with open(self.quarantine_path, "a", encoding="utf-8") as qf:
                    qf.write(json.dumps(quarantine_entry) + "\n")
                self._quarantined_count += 1
                logger.warning(
                    "Conflicting duplicate candle quarantined for %s at %s",
                    record.symbol,
                    record.timestamp.isoformat(),
                )
                return (False, "conflicting_duplicate_quarantined")

            # Persist newly arrived candle to append-only archive
            line_data = json.dumps(record.to_dict())
            with open(self.archive_path, "a", encoding="utf-8") as af:
                af.write(line_data + "\n")
                af.flush()

            self._index[key] = record
            return (True, "persisted")

    def get_records(
        self,
        symbol: Optional[str] = None,
        interval: Optional[IntradayInterval] = None,
    ) -> List[RecordedCandleRecord]:
        """Retrieve stored records chronologically sorted."""
        with self._lock:
            records = list(self._index.values())

        if symbol:
            sym_clean = symbol.strip().upper()
            records = [r for r in records if r.symbol == sym_clean]
        if interval:
            records = [r for r in records if r.interval == interval]

        return sorted(records, key=lambda r: (r.symbol, r.timestamp))

    def get_stats(self) -> ArchiveStats:
        """Compute aggregate summary statistics of the archive."""
        with self._lock:
            records = list(self._index.values())
            quarantined = self._quarantined_count

        if not records:
            return ArchiveStats(
                total_records=0,
                symbols=[],
                intervals=[],
                min_timestamp=None,
                max_timestamp=None,
                provenance_counts={},
                quarantined_count=quarantined,
                corrupted_records_count=self._corrupted_records_count,
            )

        symbols = sorted(list({r.symbol for r in records}))
        intervals = sorted(list({r.interval.value for r in records}))
        timestamps = [r.timestamp for r in records]
        min_ts = min(timestamps).isoformat()
        max_ts = max(timestamps).isoformat()

        prov_counts: Dict[str, int] = {}
        for r in records:
            prov_counts[r.provenance.value] = prov_counts.get(r.provenance.value, 0) + 1

        return ArchiveStats(
            total_records=len(records),
            symbols=symbols,
            intervals=intervals,
            min_timestamp=min_ts,
            max_timestamp=max_ts,
            provenance_counts=prov_counts,
            quarantined_count=quarantined,
            corrupted_records_count=self._corrupted_records_count,
        )


class DeterministicTestIntradayAdapter(BaseIntradayDataProvider):
    """Deterministic, provider-independent test adapter for offline testing."""

    __test__ = False  # Prevent pytest from collecting this as a test class

    def __init__(
        self,
        name: str = "test_adapter",
        candle_queue: Optional[Sequence[IntradayCandle]] = None,
        simulate_timeout: bool = False,
    ) -> None:
        self._name = name
        self._queue: List[IntradayCandle] = list(candle_queue) if candle_queue else []
        self._simulate_timeout = simulate_timeout
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def declared_delay(self) -> str:
        return "offline deterministic test fixture (0s delay)"

    def queue_candles(self, candles: Sequence[IntradayCandle]) -> None:
        """Enqueue candles to be emitted on fetch."""
        self._queue.extend(candles)

    def set_simulate_timeout(self, timeout: bool) -> None:
        """Enable or disable simulated network timeout."""
        self._simulate_timeout = timeout

    def fetch_intraday_candles(
        self,
        symbol: str,
        session_date: date,
        interval: IntradayInterval = IntradayInterval.M5,
    ) -> List[IntradayCandle]:
        """Fetch queued test candles or raise simulated timeout."""
        self.call_count += 1
        if self._simulate_timeout:
            raise TimeoutError("Simulated provider connection timeout")

        clean_sym = symbol.strip().upper()
        res = [
            c for c in self._queue
            if c.symbol == clean_sym and c.timestamp.date() == session_date and c.interval == interval
        ]
        return list(res)


# Alias for compatibility with __test__ = False preserved
TestIntradayRecorderAdapter = DeterministicTestIntradayAdapter


class IntradaySessionRecorder:
    """Safe, restartable intraday session recorder orchestration service.

    Enforces:
    1. Authorized instrument: defaults to BHARTIARTL. Index instruments rejected.
    2. Completed candle validation boundary: forming candles are deferred.
    3. Session calendar: market closure detected cleanly without logging false outages.
    4. Bounded retries: provider failures handled safely without tight loops.
    5. Clean shutdown and provenance tracking.
    """

    def __init__(
        self,
        provider: BaseIntradayDataProvider,
        store: IntradayArchiveStore,
        symbol: str = "BHARTIARTL",
        interval: IntradayInterval = IntradayInterval.M5,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.5,
        provenance: CandleProvenance = CandleProvenance.PROVIDER_OBSERVATION,
        supported_symbols: Optional[Set[str]] = None,
    ) -> None:
        self.provider = provider
        self.store = store
        self.interval = interval
        self.max_retries = max(1, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.provenance = provenance
        self._status = RecorderStatus.READY

        # Instrument authorization
        self.supported_symbols = (
            {s.upper() for s in supported_symbols}
            if supported_symbols is not None
            else {"BHARTIARTL"}
        )
        clean_symbol = symbol.strip().upper()
        if clean_symbol not in self.supported_symbols:
            raise ValidationError(
                f"Unauthorized instrument '{symbol}' for intraday recording. Supported: {self.supported_symbols}"
            )
        self.symbol = clean_symbol

        # Operational diagnostics tracking
        self._last_successful_poll_time: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._last_error_retry_count: int = 0
        self._latest_source_timestamp: Optional[datetime] = None
        self._latest_observation_timestamp: Optional[datetime] = None

    @property
    def status(self) -> RecorderStatus:
        """Current operational state."""
        return self._status

    def is_candle_completed(self, candle: IntradayCandle, as_of: datetime) -> bool:
        """Check if candle has completed its nominal bar duration at observation time.

        A candle starting at T_start with duration D is completed if and only if
        as_of >= T_start + D.
        """
        as_of_ist = as_of if as_of.tzinfo is not None else as_of.replace(tzinfo=IST)
        return as_of_ist >= candle.bar_end_timestamp

    def record_cycle(
        self,
        as_of: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Execute a single polling and recording cycle.

        Steps:
        1. Query market session status (IST).
           If market is CLOSED, set state to MARKET_CLOSED and return gracefully.
        2. Attempt to fetch candles with bounded retries.
        3. Audit fetched candles for OHLC validity and volume preservation.
        4. Validate candle completion boundary: defer forming candles.
        5. Persist completed candles into the isolated archive with provenance tag.

        Returns:
            Dictionary containing cycle metrics and diagnostic status.
        """
        now_ist = as_of if as_of is not None else datetime.now(IST)
        if now_ist.tzinfo is None:
            now_ist = now_ist.replace(tzinfo=IST)

        session_info = get_market_session(now_ist)
        session_date = session_info.session_date

        # Check market session state
        if session_info.state == MarketSessionState.CLOSED:
            self._status = RecorderStatus.MARKET_CLOSED
            logger.info("Market session is CLOSED on %s (%s). Recorder idle.", session_date, now_ist.time())
            return {
                "status": self._status.value,
                "session_state": session_info.state.value,
                "fetched_count": 0,
                "persisted_count": 0,
                "idempotent_count": 0,
                "forming_deferred_count": 0,
                "quarantined_count": 0,
                "reason": "Market is closed",
            }

        self._status = RecorderStatus.RECORDING

        # Bounded retry provider fetch
        raw_candles: List[IntradayCandle] = []
        fetch_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                raw_candles = self.provider.fetch_intraday_candles(
                    symbol=self.symbol,
                    session_date=session_date,
                    interval=self.interval,
                )
                fetch_error = None
                break
            except Exception as exc:
                fetch_error = exc
                logger.warning(
                    "Provider '%s' fetch attempt %d/%d failed: %s",
                    self.provider.name,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries and self.retry_backoff_seconds > 0:
                    time.sleep(self.retry_backoff_seconds)

        if fetch_error is not None:
            self._status = RecorderStatus.DEGRADED
            self._last_error = str(fetch_error)
            self._last_error_retry_count = self.max_retries
            logger.error("Provider '%s' fetch exhausted all retries: %s", self.provider.name, fetch_error)
            return {
                "status": self._status.value,
                "session_state": session_info.state.value,
                "fetched_count": 0,
                "persisted_count": 0,
                "idempotent_count": 0,
                "forming_deferred_count": 0,
                "quarantined_count": 0,
                "error": str(fetch_error),
            }

        # Update poll success state
        self._last_successful_poll_time = now_ist
        self._last_error = None
        self._last_error_retry_count = 0
        if raw_candles:
            self._latest_source_timestamp = max(c.timestamp for c in raw_candles)
            self._latest_observation_timestamp = now_ist

        # Validate and clean candles using existing clean_intraday_candles utility
        cleaning_result = clean_intraday_candles(
            records=raw_candles,
            expected_interval=self.interval,
            allow_out_of_session=False,
        )

        persisted_count = 0
        idempotent_count = 0
        forming_deferred_count = 0
        quarantined_count = 0

        for candle in cleaning_result.candles:
            # Completed-candle boundary check
            if not self.is_candle_completed(candle, as_of=now_ist):
                forming_deferred_count += 1
                logger.debug(
                    "Deferring forming candle for %s at %s (ends at %s, current %s)",
                    candle.symbol,
                    candle.timestamp,
                    candle.bar_end_timestamp,
                    now_ist,
                )
                continue

            # Construct immutable RecordedCandleRecord
            flags = []
            if candle.volume is not None:
                flags.append("VOLUME_REPORTED")
            else:
                flags.append("VOLUME_UNREPORTED")

            record = RecordedCandleRecord(
                symbol=candle.symbol,
                timestamp=candle.timestamp,
                interval=candle.interval,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                volume_reported=candle.volume_reported,
                source=self.provider.name,
                provenance=self.provenance,
                capture_timestamp=now_ist,
                is_completed=True,
                data_quality_flags=flags,
            )

            success, status_msg = self.store.append(record)
            if success:
                if status_msg == "persisted":
                    persisted_count += 1
                elif status_msg == "idempotent_duplicate":
                    idempotent_count += 1
            else:
                if status_msg == "conflicting_duplicate_quarantined":
                    quarantined_count += 1

        return {
            "status": self._status.value,
            "session_state": session_info.state.value,
            "fetched_count": len(raw_candles),
            "cleaned_valid_count": len(cleaning_result.candles),
            "persisted_count": persisted_count,
            "idempotent_count": idempotent_count,
            "forming_deferred_count": forming_deferred_count,
            "quarantined_count": quarantined_count,
            "cleaning_rejected_count": cleaning_result.summary.rejected_count,
            "gaps_detected_count": cleaning_result.summary.missing_candle_gaps_count,
        }

    def stop(self) -> None:
        """Stop recorder and mark status STOPPED."""
        self._status = RecorderStatus.STOPPED
        logger.info("Recorder stopped cleanly.")

    def get_operational_diagnostics(self) -> OperationalDiagnostics:
        """Construct a point-in-time operational diagnostics report."""
        stats = self.store.get_stats()
        readiness = check_evaluation_readiness(
            store=self.store,
            symbol=self.symbol,
            interval=self.interval,
        )

        archive_health = "HEALTHY"
        if not self.store.archive_path.exists():
            archive_health = "MISSING"
        elif stats.corrupted_records_count > 0:
            archive_health = f"CORRUPTED ({stats.corrupted_records_count} bad records)"

        quarantine_health = "CLEAN"
        if not self.store.quarantine_path.exists():
            quarantine_health = "NOT_CREATED"
        elif stats.quarantined_count > 0:
            quarantine_health = f"ACTIVE_QUARANTINE ({stats.quarantined_count} records)"

        return OperationalDiagnostics(
            recorder_status=self._status.value,
            last_successful_poll_time=(
                self._last_successful_poll_time.isoformat()
                if self._last_successful_poll_time is not None
                else None
            ),
            provider_name=self.provider.name,
            provider_declared_delay=getattr(self.provider, "declared_delay", "unknown"),
            latest_source_timestamp=(
                self._latest_source_timestamp.isoformat()
                if self._latest_source_timestamp is not None
                else (stats.max_timestamp if stats.total_records > 0 else None)
            ),
            latest_observation_timestamp=(
                self._latest_observation_timestamp.isoformat()
                if self._latest_observation_timestamp is not None
                else None
            ),
            total_persisted_records=stats.total_records,
            provenance_counts=stats.provenance_counts,
            latest_capture_error=self._last_error,
            last_error_retry_count=self._last_error_retry_count,
            archive_file_exists=self.store.archive_path.exists(),
            archive_corrupted_records_count=stats.corrupted_records_count,
            quarantine_records_count=stats.quarantined_count,
            readiness_status=readiness.status.value,
            readiness_blocking_reasons=readiness.issues,
            archive_file_health=archive_health,
            quarantine_file_health=quarantine_health,
        )

    def run_bounded_session(
        self,
        max_cycles: Optional[int] = 12,
        max_runtime_seconds: Optional[float] = 3600.0,
        poll_interval_seconds: float = 60.0,
        stop_on_market_close: bool = True,
        stop_on_degraded: bool = True,
        clock_fn: Optional[Callable[[], datetime]] = None,
        sleep_fn: Optional[Callable[[float], None]] = None,
    ) -> SessionCaptureSummary:
        """Execute a controlled, bounded manual recording session across multiple polling cycles.

        Guarantees:
        - Never runs as an unattended infinite loop or background daemon.
        - Stops cleanly when market is closed, runtime limit reached, cycle limit reached,
          fatal provider degradation occurs, or stop() is invoked.
        - Supports injected clock_fn and sleep_fn for deterministic simulation.

        Returns:
            SessionCaptureSummary containing aggregated metrics across all cycles.
        """
        if max_cycles is not None and max_cycles <= 0:
            raise ValidationError(f"max_cycles must be a positive integer, got {max_cycles}")
        if max_runtime_seconds is not None and max_runtime_seconds <= 0:
            raise ValidationError(f"max_runtime_seconds must be positive, got {max_runtime_seconds}")
        if poll_interval_seconds < 0:
            raise ValidationError(f"poll_interval_seconds cannot be negative, got {poll_interval_seconds}")

        get_now = clock_fn if clock_fn is not None else (lambda: datetime.now(IST))
        do_sleep = sleep_fn if sleep_fn is not None else time.sleep

        start_time = get_now()
        cycles_completed = 0
        total_fetched = 0
        total_persisted = 0
        total_idempotent = 0
        total_deferred = 0
        total_quarantined = 0
        cycle_history: List[Dict[str, Any]] = []
        termination_reason = "completed"

        logger.info(
            "Starting bounded manual recording session for %s [%s] (max_cycles=%s, max_runtime=%ss)",
            self.symbol,
            self.interval.value,
            max_cycles,
            max_runtime_seconds,
        )

        while True:
            # Check manual stop signal
            if self._status == RecorderStatus.STOPPED:
                termination_reason = "manual_stop"
                break

            current_time = get_now()
            elapsed_seconds = (current_time - start_time).total_seconds()

            # Check runtime limit
            if max_runtime_seconds is not None and elapsed_seconds >= max_runtime_seconds:
                termination_reason = "runtime_limit_reached"
                logger.info("Session reached maximum runtime limit (%.1fs)", max_runtime_seconds)
                break

            # Check cycle limit
            if max_cycles is not None and cycles_completed >= max_cycles:
                termination_reason = "cycle_limit_reached"
                logger.info("Session reached maximum cycle limit (%d)", max_cycles)
                break

            # Check market session state
            session_info = get_market_session(current_time)
            if stop_on_market_close and session_info.state == MarketSessionState.CLOSED:
                cycle_result = self.record_cycle(as_of=current_time)
                cycle_history.append(cycle_result)
                termination_reason = "market_closed"
                logger.info("Market session is CLOSED. Terminating bounded capture session.")
                break

            # Execute poll cycle
            cycle_result = self.record_cycle(as_of=current_time)
            cycles_completed += 1
            cycle_history.append(cycle_result)

            total_fetched += cycle_result.get("fetched_count", 0)
            total_persisted += cycle_result.get("persisted_count", 0)
            total_idempotent += cycle_result.get("idempotent_count", 0)
            total_deferred += cycle_result.get("forming_deferred_count", 0)
            total_quarantined += cycle_result.get("quarantined_count", 0)

            # Check provider degraded state
            if stop_on_degraded and self._status == RecorderStatus.DEGRADED:
                termination_reason = "provider_degraded"
                logger.warning("Provider entered DEGRADED status. Halting bounded session.")
                break

            # Check if session transitioned past regular hours
            if session_info.state in (MarketSessionState.POST_CLOSE, MarketSessionState.CLOSED):
                termination_reason = "session_ended"
                logger.info("Trading session ended (%s). Halting bounded session.", session_info.state.value)
                break

            # Check if another cycle is allowed before sleeping
            if max_cycles is not None and cycles_completed >= max_cycles:
                termination_reason = "cycle_limit_reached"
                break

            # Sleep bounded interval
            if poll_interval_seconds > 0:
                do_sleep(poll_interval_seconds)

        final_time = get_now()
        total_duration = max(0.0, (final_time - start_time).total_seconds())

        summary = SessionCaptureSummary(
            symbol=self.symbol,
            interval=self.interval.value,
            status=self._status.value,
            termination_reason=termination_reason,
            cycles_completed=cycles_completed,
            total_runtime_seconds=round(total_duration, 2),
            total_fetched=total_fetched,
            total_persisted=total_persisted,
            total_idempotent=total_idempotent,
            total_deferred=total_deferred,
            total_quarantined=total_quarantined,
            cycle_history=cycle_history,
        )

        logger.info(
            "Bounded session finished: %s (%d cycles, %d persisted, reason=%s)",
            self.symbol,
            cycles_completed,
            total_persisted,
            termination_reason,
        )
        return summary


def check_evaluation_readiness(
    store: IntradayArchiveStore,
    symbol: str = "BHARTIARTL",
    interval: IntradayInterval = IntradayInterval.M5,
    min_required_candles: Optional[int] = None,
    supported_symbols: Optional[Set[str]] = None,
) -> EvaluationReadinessReport:
    """Verify whether the isolated intraday archive is ready for empirical backtest evaluation.

    Evaluation Gate Criteria:
    1. Zero synthetic fixtures: if the archive contains synthetic_test data, empirical
       evaluation is blocked (CONTAMINATED_SYNTHETIC).
    2. Genuine provider observations present: must contain provider_observation or validated_archive.
       If none present, report BLOCKED_NO_VERIFIED_INTRADAY_PROVIDER.
    3. Unresolved quarantine conflicts: if the store has quarantined conflicting records,
       evaluation is blocked (PENDING_VALIDATION).
    4. Completed candles only: all records must have is_completed=True.
    5. Sufficient historical depth: must contain at least min_required_candles
       (defaults dynamically to interval.expected_bars_per_regular_session, e.g. 75 for 5m, 25 for 15m).
    6. Monotonic chronological ordering: timestamps must strictly increase.
    7. Valid trading session calendar: candles must fall on valid NSE trading days (no weekends or holidays).
    8. Interval continuity and zero gaps: sessions must have zero missing candle gaps.
    9. Clean OHLCV: zero rejected candles during cleaning verification.
    """
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        raise ValidationError("symbol cannot be empty")
    clean_sym = symbol.strip().upper()

    allowed_symbols = (
        {s.upper() for s in supported_symbols}
        if supported_symbols is not None
        else {"BHARTIARTL"}
    )
    if clean_sym not in allowed_symbols:
        return EvaluationReadinessReport(
            status=EvaluationReadinessStatus.BLOCKED_NO_VERIFIED_INTRADAY_PROVIDER,
            is_ready_for_evaluation=False,
            reason=f"Unsupported symbol '{clean_sym}'. Intraday evaluation is restricted to authorized instruments.",
            total_candles=0,
            provenance_counts={},
            symbol=clean_sym,
            interval=interval.value,
            gaps_count=0,
            issues=[f"Symbol '{clean_sym}' is not authorized for intraday evaluation. Supported: {sorted(list(allowed_symbols))}"],
        )

    records = store.get_records(symbol=clean_sym, interval=interval)

    # Dynamic minimum required candles based on interval session expectation
    effective_min_candles = (
        min_required_candles
        if min_required_candles is not None
        else interval.expected_bars_per_regular_session
    )

    issues: List[str] = []
    prov_counts: Dict[str, int] = {}
    for r in records:
        prov_counts[r.provenance.value] = prov_counts.get(r.provenance.value, 0) + 1

    # Check 0: Archive structural integrity (malformed or corrupt records)
    if store.corrupted_records_count > 0:
        issues.append(
            f"Archive contains {store.corrupted_records_count} malformed or corrupted JSONL records. Archive structure must be completely uncorrupted before evaluation."
        )
        return EvaluationReadinessReport(
            status=EvaluationReadinessStatus.PENDING_VALIDATION,
            is_ready_for_evaluation=False,
            reason=f"Archive contains {store.corrupted_records_count} corrupted or truncated records requiring manual inspection.",
            total_candles=len(records),
            provenance_counts=prov_counts,
            symbol=clean_sym,
            interval=interval.value,
            gaps_count=0,
            issues=issues,
        )

    # Check 1: Synthetic test contamination
    if prov_counts.get(CandleProvenance.SYNTHETIC_TEST.value, 0) > 0:
        issues.append(
            f"Archive contains {prov_counts[CandleProvenance.SYNTHETIC_TEST.value]} synthetic_test fixtures. Synthetic data cannot be used for empirical market evaluation."
        )
        return EvaluationReadinessReport(
            status=EvaluationReadinessStatus.CONTAMINATED_SYNTHETIC,
            is_ready_for_evaluation=False,
            reason="Archive contains synthetic test fixtures. Real empirical evaluation requires unadulterated provider data.",
            total_candles=len(records),
            provenance_counts=prov_counts,
            symbol=clean_sym,
            interval=interval.value,
            gaps_count=0,
            issues=issues,
        )

    # Check 2: No provider observations captured
    genuine_count = prov_counts.get(CandleProvenance.PROVIDER_OBSERVATION.value, 0) + prov_counts.get(
        CandleProvenance.VALIDATED_ARCHIVE.value, 0
    )
    if genuine_count == 0:
        issues.append("No genuine provider observations have been captured into the archive.")
        return EvaluationReadinessReport(
            status=EvaluationReadinessStatus.BLOCKED_NO_VERIFIED_INTRADAY_PROVIDER,
            is_ready_for_evaluation=False,
            reason="Blocked: No verified intraday market data provider observations captured.",
            total_candles=0,
            provenance_counts=prov_counts,
            symbol=clean_sym,
            interval=interval.value,
            gaps_count=0,
            issues=issues,
        )

    # Check 3: Unresolved quarantined conflicts
    quarantined = store.get_stats().quarantined_count
    if quarantined > 0:
        issues.append(
            f"Archive has {quarantined} unresolved quarantined conflicting records. Requires review before empirical validation."
        )
        return EvaluationReadinessReport(
            status=EvaluationReadinessStatus.PENDING_VALIDATION,
            is_ready_for_evaluation=False,
            reason=f"Archive contains {quarantined} quarantined conflicting records requiring manual resolution.",
            total_candles=len(records),
            provenance_counts=prov_counts,
            symbol=clean_sym,
            interval=interval.value,
            gaps_count=0,
            issues=issues,
        )

    # Check 4: Uncompleted/forming candles
    uncompleted_count = sum(1 for r in records if not r.is_completed)
    if uncompleted_count > 0:
        issues.append(f"Archive contains {uncompleted_count} forming or uncompleted candles.")
        return EvaluationReadinessReport(
            status=EvaluationReadinessStatus.PENDING_VALIDATION,
            is_ready_for_evaluation=False,
            reason=f"Archive contains {uncompleted_count} incomplete/forming candles.",
            total_candles=len(records),
            provenance_counts=prov_counts,
            symbol=clean_sym,
            interval=interval.value,
            gaps_count=0,
            issues=issues,
        )

    # Check 5: Coverage sufficiency
    if len(records) < effective_min_candles:
        issues.append(
            f"Archive has {len(records)} candles, fewer than required minimum of {effective_min_candles} bars."
        )
        return EvaluationReadinessReport(
            status=EvaluationReadinessStatus.INSUFFICIENT_COVERAGE,
            is_ready_for_evaluation=False,
            reason=f"Insufficient candle coverage ({len(records)} < {effective_min_candles} bars).",
            total_candles=len(records),
            provenance_counts=prov_counts,
            symbol=clean_sym,
            interval=interval.value,
            gaps_count=0,
            issues=issues,
        )

    # Check 6: Monotonic timestamp ordering
    for i in range(len(records) - 1):
        if records[i + 1].timestamp <= records[i].timestamp:
            issues.append(
                f"Non-monotonic timestamp detected: {records[i].timestamp} -> {records[i + 1].timestamp}."
            )
            return EvaluationReadinessReport(
                status=EvaluationReadinessStatus.PENDING_VALIDATION,
                is_ready_for_evaluation=False,
                reason="Archive timestamps are not strictly monotonic.",
                total_candles=len(records),
                provenance_counts=prov_counts,
                symbol=clean_sym,
                interval=interval.value,
                gaps_count=0,
                issues=issues,
            )

    # Check 7: Session calendar validation (weekdays and non-holidays)
    for r in records:
        r_date = r.timestamp.date()
        if r_date.weekday() >= 5 or r_date in NSE_HOLIDAYS_2026:
            issues.append(f"Candle at {r.timestamp} falls on a weekend or declared NSE holiday ({r_date}).")
            return EvaluationReadinessReport(
                status=EvaluationReadinessStatus.PENDING_VALIDATION,
                is_ready_for_evaluation=False,
                reason=f"Archive contains observation on non-trading session date {r_date}.",
                total_candles=len(records),
                provenance_counts=prov_counts,
                symbol=clean_sym,
                interval=interval.value,
                gaps_count=0,
                issues=issues,
            )

    # Check 8: Session cleaning, out-of-session checks, and gap auditing
    intraday_candles = []
    for r in records:
        try:
            intraday_candles.append(r.to_intraday_candle())
        except Exception as exc:
            issues.append(f"Corrupted or invalid candle record at {r.timestamp}: {exc}")
            return EvaluationReadinessReport(
                status=EvaluationReadinessStatus.PENDING_VALIDATION,
                is_ready_for_evaluation=False,
                reason="Archive contains corrupted or physically invalid candle records.",
                total_candles=len(records),
                provenance_counts=prov_counts,
                symbol=clean_sym,
                interval=interval.value,
                gaps_count=0,
                issues=issues,
            )
    cleaning_res = clean_intraday_candles(
        intraday_candles,
        expected_interval=interval,
        allow_out_of_session=False,
    )
    gaps_count = cleaning_res.summary.missing_candle_gaps_count
    if gaps_count > 0:
        issues.append(f"{gaps_count} missing interval gaps detected during regular trading sessions.")
        return EvaluationReadinessReport(
            status=EvaluationReadinessStatus.PENDING_VALIDATION,
            is_ready_for_evaluation=False,
            reason=f"Archive contains {gaps_count} missing interval gaps during regular trading sessions.",
            total_candles=len(records),
            provenance_counts=prov_counts,
            symbol=clean_sym,
            interval=interval.value,
            gaps_count=gaps_count,
            issues=issues,
        )

    if cleaning_res.summary.rejected_count > 0:
        issues.append(
            f"{cleaning_res.summary.rejected_count} candles rejected during quality verification."
        )
        return EvaluationReadinessReport(
            status=EvaluationReadinessStatus.PENDING_VALIDATION,
            is_ready_for_evaluation=False,
            reason="Archived observations contain rejected candles or session discrepancies requiring review.",
            total_candles=len(records),
            provenance_counts=prov_counts,
            symbol=clean_sym,
            interval=interval.value,
            gaps_count=gaps_count,
            issues=issues,
        )

    # All criteria satisfied!
    return EvaluationReadinessReport(
        status=EvaluationReadinessStatus.READY,
        is_ready_for_evaluation=True,
        reason="Archive satisfies all empirical evaluation criteria: verified provenance, sufficient depth, clean OHLCV.",
        total_candles=len(records),
        provenance_counts=prov_counts,
        symbol=clean_sym,
        interval=interval.value,
        gaps_count=0,
        issues=[],
    )
