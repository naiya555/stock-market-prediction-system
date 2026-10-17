"""Macroeconomic and Regulatory Events API Route.

Exposes normalized official RBI policy announcements, SEBI circulars, and market
events with point-in-time filtering and deduplication.
"""

from datetime import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_event_providers
from app.api.schemas import EventItemResponse, EventsResponse
from app.events.cleaner import deduplicate_events
from app.events.providers.base import BaseEventProvider
from app.events.schemas import EventCategory, MacroEvent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=EventsResponse,
    status_code=status.HTTP_200_OK,
    summary="Query Ingested Macroeconomic & Regulatory Events",
    description=(
        "Retrieves normalized macroeconomic, policy, and regulatory announcements "
        "from official regulatory sources (RBI, SEBI) with deduplication and category filtering."
    ),
)
def get_events(
    category: Optional[str] = Query(
        None,
        description="Filter by EventCategory (e.g. 'monetary_policy', 'regulatory')",
    ),
    source: Optional[str] = Query(
        None,
        description="Filter by provider source name substring (e.g. 'rbi', 'sebi')",
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Filter events published on or after this timestamp",
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter events published on or before this timestamp",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Maximum number of events to return (1-100)",
    ),
    providers: List[BaseEventProvider] = Depends(get_event_providers),
) -> EventsResponse:
    """Acquire events across active providers, deduplicate, filter, and return structured items."""
    raw_events: List[MacroEvent] = []
    queried_providers: List[str] = []

    clean_source = source.strip().lower() if source else None
    clean_cat = category.strip().lower() if category else None

    for provider in providers:
        p_name = provider.name.lower()
        if clean_source and clean_source not in p_name:
            continue

        queried_providers.append(provider.name)
        try:
            fetched = provider.fetch_events(
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
            raw_events.extend(fetched)
        except Exception as exc:
            logger.warning("Provider '%s' failed to fetch events: %s", provider.name, exc)

    # Apply canonical deduplication if events were returned
    if raw_events:
        cleaned_res = deduplicate_events(raw_events)
        unique_events = cleaned_res.events
    else:
        unique_events = []

    # Category filtering
    if clean_cat:
        filtered_events = [
            e for e in unique_events
            if e.category.value.lower() == clean_cat or clean_cat in e.category.value.lower()
        ]
    else:
        filtered_events = unique_events

    # Bounded slicing
    selected = filtered_events[:limit]

    items: List[EventItemResponse] = []
    for ev in selected:
        items.append(
            EventItemResponse(
                event_id=ev.event_id,
                title=ev.title,
                category=ev.category.value,
                event_type=ev.event_type,
                source_org=ev.source_org,
                published_at=ev.published_at.isoformat() if ev.published_at else None,
                announced_at=ev.announced_at.isoformat() if ev.announced_at else None,
                effective_at=ev.effective_at.isoformat() if ev.effective_at else None,
                ingested_at=ev.ingested_at.isoformat(),
                url=ev.url,
                affected_sectors=list(ev.affected_sectors),
                affected_symbols=list(ev.affected_symbols),
                summary=ev.summary,
                provider=ev.provider,
                is_verified=ev.is_verified,
            )
        )

    return EventsResponse(
        events=items,
        count=len(items),
        providers_queried=queried_providers,
    )
