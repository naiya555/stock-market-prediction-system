"""Abstract Base Contract for Macroeconomic and Regulatory Event Providers.

Defines the interface for acquiring macroeconomic releases, policy announcements,
and external market indicators. All concrete adapters normalize raw source payloads
into canonical MacroEvent records.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app.events.schemas import MacroEvent


class EventProviderError(RuntimeError):
    """Raised when an external event source communication, HTTP request, or parsing fails."""
    pass


class BaseEventProvider(ABC):
    """Abstract base class defining the contract for event data providers.

    Subclasses implement communication with specific regulatory/macroeconomic sources
    (e.g., Reserve Bank of India, SEBI, Ministry of Finance, Global Market Feeds)
    and normalize source payloads into canonical MacroEvent records.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique provider identifier (e.g., 'rbi_rss_provider')."""
        pass

    @abstractmethod
    def fetch_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[MacroEvent]:
        """Fetch and normalize event records from the source.

        Args:
            start_date: Optional inclusive start datetime filter.
            end_date: Optional inclusive end datetime filter.
            limit: Maximum number of events to return (default 50).

        Returns:
            List of canonical MacroEvent records sorted in descending chronological order
            (most recent publication first).

        Raises:
            EventProviderError: If remote provider fails, is rate-limited, or returns unparseable content.
        """
        pass
