"""Read-only validation and anomaly monitoring for canonical market records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from statistics import median
from typing import Any, Iterable, Sequence

from app.core.schemas import MarketOHLCV
from app.market.instruments import get_instrument
from app.market.quality.nse_calendar import NSECalendarEvidence


@dataclass(frozen=True)
class QualityFinding:
    instrument: str
    date_or_range: str
    check_name: str
    status: str
    observed_value: str
    expected_condition: str
    explanation: str
    source: str
    detected_at: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _finding(symbol: str, record_date: str, check: str, status: str, observed: Any,
             expected: str, explanation: str, source: str, detected_at: str) -> QualityFinding:
    return QualityFinding(symbol, record_date, check, status, str(observed), expected,
                          explanation, source, detected_at)


def monitor_records(
    symbol: str,
    records: Sequence[MarketOHLCV],
    *,
    provider: str | None = None,
    retrieved_at: datetime | None = None,
    stale_after_days: int = 3,
    price_jump_warning: float = 0.20,
    volume_ratio_warning: float = 10.0,
    calendar_evidence: dict[Any, NSECalendarEvidence] | None = None,
) -> dict[str, Any]:
    """Validate records without modifying, sorting, deduplicating, or repairing them."""
    now = datetime.now(timezone.utc)
    detected_at = now.isoformat()
    canonical = symbol.strip().upper()
    source = provider or (records[0].source if records else "unknown")
    inst = get_instrument(canonical)
    close_only = canonical == "NIFTY_TELECOMMUNICATIONS" or (
        bool(records) and all(record.is_close_only for record in records)
    )
    findings: list[QualityFinding] = []
    required = {"symbol", "timestamp", "close", "source"}
    expected = {"symbol", "timestamp", "open", "high", "low", "close", "volume", "source",
                "is_close_only", "volume_reported"}
    previous = None
    volumes: list[int] = []
    ordered = list(records)
    for index, record in enumerate(ordered):
        date = record.timestamp.date().isoformat()
        if not record.symbol or not record.source:
            findings.append(_finding(canonical, date, "required_fields", "FAIL", record,
                                     "symbol, timestamp, close and source are present",
                                     "Required provenance or identity field is empty.", source, detected_at))
        if not math.isfinite(float(record.close)) or record.close <= 0:
            findings.append(_finding(canonical, date, "price_domain", "FAIL", record.close,
                                     "close is finite and greater than zero", "Invalid close price.", source, detected_at))
        if not close_only:
            if any(value is None for value in (record.open, record.high, record.low)):
                findings.append(_finding(canonical, date, "ohlc_completeness", "FAIL", record,
                                         "equity OHLC fields are present", "Equity OHLCV record is incomplete.", source, detected_at))
            elif record.high < max(record.open, record.close) or record.low > min(record.open, record.close) or record.high < record.low:
                findings.append(_finding(canonical, date, "ohlc_relationship", "FAIL", record,
                                         "high >= open/close and low <= open/close", "OHLC geometry is impossible.", source, detected_at))
        if record.volume is not None:
            if record.volume < 0:
                findings.append(_finding(canonical, date, "volume_domain", "FAIL", record.volume,
                                         "volume is non-negative", "Negative volume is invalid.", source, detected_at))
            if record.volume_reported:
                volumes.append(record.volume)
                if record.volume == 0:
                    findings.append(_finding(canonical, date, "zero_volume", "WARNING", record.volume,
                                             "reported equity volume is normally positive", "Zero volume requires review; it is not automatically an error.", source, detected_at))
        if previous is not None:
            if record.timestamp < previous.timestamp:
                findings.append(_finding(canonical, date, "date_order", "FAIL", record.timestamp,
                                         "timestamps are chronological", "Records are out of order.", source, detected_at))
            if record.timestamp == previous.timestamp:
                findings.append(_finding(canonical, date, "duplicate_timestamp", "FAIL", record.timestamp,
                                         "one observation per instrument and session", "Duplicate session timestamp.", source, detected_at))
            if previous.close > 0:
                change = record.close / previous.close - 1
                if abs(change) >= price_jump_warning:
                    findings.append(_finding(canonical, date, "price_jump", "WARNING", f"{change:.6f}",
                                             f"absolute return below {price_jump_warning:.2%}",
                                             "Large movement may be valid but needs corporate-action or market-event review.", source, detected_at))
            calendar_gap = (record.timestamp.date() - previous.timestamp.date()).days
            if calendar_gap > 3:
                findings.append(_finding(canonical, f"{previous.timestamp.date()}..{date}", "missing_sessions", "UNVERIFIED",
                                         f"{calendar_gap} calendar days",
                                         "session gaps are explained by a supported exchange calendar",
                                         "A multi-day gap was observed, but this monitor has no calendar evidence to classify holidays or missing sessions.", source, detected_at))
            if previous.volume and record.volume_reported and record.volume is not None:
                ratio = record.volume / previous.volume if previous.volume else math.inf
                if ratio >= volume_ratio_warning or ratio <= 1 / volume_ratio_warning:
                    findings.append(_finding(canonical, date, "volume_change", "WARNING", f"{ratio:.6g}x",
                                             f"volume ratio within {1 / volume_ratio_warning:.2g}x to {volume_ratio_warning:.2g}x",
                                             "Unusual volume change requires review.", source, detected_at))
        calendar = calendar_evidence.get(record.timestamp.date()) if calendar_evidence else None
        if calendar and calendar.verification_status == "VERIFIED":
            calendar_status = "PASS" if calendar.classification in {"REGULAR_SESSION", "SPECIAL_SESSION"} else "WARNING"
            calendar_explanation = calendar.evidence_description
        else:
            calendar_status = "UNVERIFIED"
            calendar_explanation = "No verified official NSE evidence was supplied for this date."
        if record.timestamp.weekday() >= 5 or calendar_evidence is not None:
            findings.append(_finding(canonical, date, "session_calendar", calendar_status, record.timestamp,
                                     "session classification is supported by an exchange calendar",
                                     calendar_explanation, source, detected_at))
        previous = record
    if not ordered:
        findings.append(_finding(canonical, "", "empty_response", "FAIL", 0,
                                 "provider returns at least one record", "Provider response was empty.", source, detected_at))
    if ordered:
        latest = ordered[-1].timestamp
        age = (now - latest.astimezone(timezone.utc)).total_seconds() / 86400
        if age > stale_after_days:
            findings.append(_finding(canonical, latest.date().isoformat(), "stale_data", "WARNING", f"{age:.2f} days",
                                     f"latest observation is no more than {stale_after_days} days old",
                                     "Latest observation is older than the configured freshness threshold.", source, detected_at))
    if volumes and median(volumes) == 0 and not close_only:
        findings.append(_finding(canonical, f"{ordered[0].timestamp.date()}..{ordered[-1].timestamp.date()}",
                                 "flat_volume", "WARNING", "median=0",
                                 "reported equity volume should not be entirely zero",
                                 "Volume is flat at zero across the observed range.", source, detected_at))
    statuses = {finding.status for finding in findings}
    overall = "FAIL" if "FAIL" in statuses else "WARNING" if "WARNING" in statuses else "UNVERIFIED" if "UNVERIFIED" in statuses else "PASS"
    return {
        "instrument": canonical,
        "instrument_type": inst.instrument_type.value if inst else "UNKNOWN",
        "provider": source,
        "retrieved_at": retrieved_at.isoformat() if retrieved_at else None,
        "record_count": len(ordered),
        "date_range": {
            "start": ordered[0].timestamp.isoformat() if ordered else None,
            "end": ordered[-1].timestamp.isoformat() if ordered else None,
        },
        "schema": sorted(expected if ordered else required),
        "close_only": close_only,
        "overall_status": overall,
        "finding_counts": {status: sum(finding.status == status for finding in findings)
                           for status in ("PASS", "WARNING", "FAIL", "UNVERIFIED")},
        "findings": [finding.to_dict() for finding in findings],
    }
