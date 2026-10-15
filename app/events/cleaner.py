"""Macroeconomic and Regulatory Events Cleaning, Deduplication, and Point-in-Time Filtering.

Provides deterministic deduplication of regulatory and macro events across official feeds
and strict point-in-time session filtering to prevent temporal look-ahead leakage.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import re
from typing import Any, Dict, List, Optional, Sequence, Set

from app.core.logging_config import get_logger
from app.events.schemas import MacroEvent

logger = get_logger(__name__)


@dataclass(frozen=True)
class EventDeduplicationSummary:
    """Audit summary metrics for an event deduplication execution."""

    total_input: int
    unique_count: int
    duplicates_removed: int
    removed_ids: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class EventCleaningResult:
    """Container holding deduplicated MacroEvent records and audit summary."""

    events: List[MacroEvent]
    summary: EventDeduplicationSummary

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "events": [e.to_dict() for e in self.events],
            "summary": self.summary.to_dict(),
        }


def _normalize_title_text(text: str) -> str:
    """Normalize event title for deduplication.

    Converts to lowercase, strips punctuation, and collapses whitespace.
    """
    clean = text.lower()
    clean = re.sub(r"[^\w\s]", " ", clean)
    return " ".join(clean.split())


def deduplicate_events(
    events: Sequence[MacroEvent],
    window_hours: int = 72,
) -> EventCleaningResult:
    """Deduplicate macro and regulatory events across identical IDs, URLs, and syndicated titles.

    Deduplication Rules:
    1. Exact Event ID: If two records share an identical deterministic hash, duplicate is discarded.
    2. Exact URL: If two records share the same non-empty URL, duplicate is discarded.
    3. Source + Title Match within Window: If two records from the same source organization
       share the exact normalized title within `window_hours`, the later publication is considered duplicate.
    4. Ordering: Preserves descending chronological order (most recent first).

    Args:
        events: Input sequence of MacroEvent records.
        window_hours: Window within which matching source+title is considered duplicate (default 72h).

    Returns:
        EventCleaningResult containing unique MacroEvent records and comprehensive audit summary.
    """
    if not events:
        summary = EventDeduplicationSummary(
            total_input=0,
            unique_count=0,
            duplicates_removed=0,
            removed_ids=[],
        )
        return EventCleaningResult(events=[], summary=summary)

    # Sort input by primary timestamp ascending so earliest publication is treated as canonical origin
    sorted_inputs = sorted(events, key=lambda e: e.primary_timestamp)

    seen_ids: Set[str] = set()
    seen_urls: Set[str] = set()
    # Map of (source_org, normalized_title) -> list of primary_timestamp
    seen_titles: Dict[str, List[datetime]] = {}

    unique_events: List[MacroEvent] = []
    removed_ids: List[str] = []

    for ev in sorted_inputs:
        is_duplicate = False

        # Rule 1: Exact Event ID
        if ev.event_id in seen_ids:
            is_duplicate = True
            removed_ids.append(ev.event_id)

        # Rule 2: Exact URL
        elif ev.url and ev.url in seen_urls:
            is_duplicate = True
            removed_ids.append(ev.event_id)

        # Rule 3: Same source + title within window
        else:
            norm_key = f"{ev.source_org.lower()}:{_normalize_title_text(ev.title)}"
            if norm_key in seen_titles:
                prior_dates = seen_titles[norm_key]
                for p_date in prior_dates:
                    diff = abs((ev.primary_timestamp - p_date).total_seconds())
                    if diff <= window_hours * 3600:
                        is_duplicate = True
                        removed_ids.append(ev.event_id)
                        break

        if not is_duplicate:
            unique_events.append(ev)
            seen_ids.add(ev.event_id)
            if ev.url:
                seen_urls.add(ev.url)
            norm_key = f"{ev.source_org.lower()}:{_normalize_title_text(ev.title)}"
            if norm_key not in seen_titles:
                seen_titles[norm_key] = []
            seen_titles[norm_key].append(ev.primary_timestamp)

    # Sort output descending by primary timestamp (most recent first)
    unique_events.sort(key=lambda e: e.primary_timestamp, reverse=True)

    summary = EventDeduplicationSummary(
        total_input=len(events),
        unique_count=len(unique_events),
        duplicates_removed=len(removed_ids),
        removed_ids=removed_ids,
    )

    logger.info(
        "Event deduplication complete: %d input -> %d unique (%d duplicates removed)",
        summary.total_input,
        summary.unique_count,
        summary.duplicates_removed,
    )

    return EventCleaningResult(events=unique_events, summary=summary)


def filter_events_point_in_time(
    events: Sequence[MacroEvent],
    as_of_time: datetime,
    lookback_window: Optional[timedelta] = None,
) -> List[MacroEvent]:
    """Strictly filter macro and regulatory events to eliminate look-ahead bias before a given decision cutoff.

    Invariants:
    1. Temporal Availability Invariant:
       - The event's information availability timestamp (primary_timestamp: published_at or announced_at)
         must be strictly <= as_of_time.
       - The system acquisition timestamp (`ingested_at`) must be strictly <= as_of_time.
       - Any event published or ingested after as_of_time is strictly excluded.
    2. Effective Date Preservation:
       - An event effective in the future (effective_at > as_of_time) is eligible if and only if
         it was published/announced on or before as_of_time (e.g., policy rate announced Friday
         effective Monday is known Friday). Its effective_at remains unaltered.
    3. Optional Lookback Window:
       - If `lookback_window` is provided, events with primary_timestamp < as_of_time - lookback_window
         are excluded.

    Args:
        events: Sequence of MacroEvent records.
        as_of_time: Market cutoff timestamp (timezone-aware).
        lookback_window: Optional maximum age duration prior to as_of_time.

    Returns:
        List of eligible point-in-time MacroEvent records sorted descending by primary timestamp.
    """
    eligible: List[MacroEvent] = []
    min_time = (as_of_time - lookback_window) if lookback_window is not None else None

    for ev in events:
        # Zero look-ahead: primary availability timestamp must be <= as_of_time
        if ev.primary_timestamp > as_of_time:
            continue

        # Ingestion guard: system must have acquired the record on or before cutoff
        if ev.ingested_at > as_of_time:
            continue

        # Lookback window guard
        if min_time is not None and ev.primary_timestamp < min_time:
            continue

        eligible.append(ev)

    eligible.sort(key=lambda e: e.primary_timestamp, reverse=True)
    return eligible
