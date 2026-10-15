"""Macroeconomic, Regulatory, and External Events Package.

Provides schemas, providers, deduplication, and point-in-time filtering for
RBI monetary policy, SEBI circulars, government announcements, and external market observations.
"""

from app.events.cleaner import (
    EventCleaningResult,
    EventDeduplicationSummary,
    deduplicate_events,
    filter_events_point_in_time,
)
from app.events.providers import (
    BaseEventProvider,
    EventProviderError,
    ExternalMarketProvider,
    RBIEventProvider,
    SEBIEventProvider,
    SUPPORTED_EXTERNAL_SERIES,
)
from app.events.schemas import (
    EventCategory,
    ExternalMarketObservation,
    MacroEvent,
    StructuredEventValue,
)

__all__ = [
    "BaseEventProvider",
    "EventCategory",
    "EventCleaningResult",
    "EventDeduplicationSummary",
    "EventProviderError",
    "ExternalMarketObservation",
    "ExternalMarketProvider",
    "MacroEvent",
    "RBIEventProvider",
    "SEBIEventProvider",
    "SUPPORTED_EXTERNAL_SERIES",
    "StructuredEventValue",
    "deduplicate_events",
    "filter_events_point_in_time",
]
