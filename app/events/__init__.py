"""Macroeconomic, Regulatory, and External Events Package.

Provides schemas, providers, deduplication, and point-in-time filtering for
RBI monetary policy, SEBI circulars, government announcements, and external market observations.
"""

from app.events.aligner import (
    AlignedEventSession,
    AlignmentStatus,
    EventSessionAligner,
    SessionPhase,
)
from app.events.calendar import (
    BaseTradingCalendar,
    ExchangeTradingCalendar,
    IST,
    MARKET_CLOSE_TIME,
    MARKET_OPEN_TIME,
    MarketDataTradingCalendar,
)
from app.events.cleaner import (
    EventCleaningResult,
    EventDeduplicationSummary,
    deduplicate_events,
    filter_events_point_in_time,
)
from app.events.impact import (
    AggregateImpactSummary,
    EventImpactAnalyzer,
    EventImpactMeasurement,
    NON_CAUSAL_DISCLAIMER,
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
    "AggregateImpactSummary",
    "AlignedEventSession",
    "AlignmentStatus",
    "BaseEventProvider",
    "BaseTradingCalendar",
    "EventCategory",
    "EventCleaningResult",
    "EventDeduplicationSummary",
    "EventImpactAnalyzer",
    "EventImpactMeasurement",
    "EventProviderError",
    "EventSessionAligner",
    "ExchangeTradingCalendar",
    "ExternalMarketObservation",
    "ExternalMarketProvider",
    "IST",
    "MARKET_CLOSE_TIME",
    "MARKET_OPEN_TIME",
    "MacroEvent",
    "MarketDataTradingCalendar",
    "NON_CAUSAL_DISCLAIMER",
    "RBIEventProvider",
    "SEBIEventProvider",
    "SUPPORTED_EXTERNAL_SERIES",
    "SessionPhase",
    "StructuredEventValue",
    "deduplicate_events",
    "filter_events_point_in_time",
]
