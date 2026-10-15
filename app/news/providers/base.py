"""Abstract Base Contract for Financial News Providers.

Defines the interface for acquiring financial news headlines and metadata.
All concrete provider adapters must normalize raw provider payloads into
canonical NewsArticle records.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app.news.schemas import NewsArticle


class NewsProviderError(RuntimeError):
    """Raised when an external news provider communication or parsing fails."""
    pass


class BaseNewsProvider(ABC):
    """Abstract base class defining the contract for news data providers.

    Subclasses implement communication with specific financial news sources
    (e.g., Google News RSS, Moneycontrol, Economic Times, Yahoo Finance RSS)
    and normalize source payloads into canonical NewsArticle records.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique provider identifier (e.g., 'google_news_rss')."""
        pass

    @abstractmethod
    def fetch_news(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[NewsArticle]:
        """Fetch and normalize financial news records for a given equity ticker or index.

        Args:
            symbol: Equity or index symbol (e.g., 'BHARTIARTL', 'NIFTY').
            start_date: Optional inclusive start datetime filter.
            end_date: Optional inclusive end datetime filter.
            limit: Maximum number of articles to return (default 50).

        Returns:
            List of canonical NewsArticle records sorted in descending chronological order
            (most recent publication first).

        Raises:
            ValidationError: If symbol is invalid or record validation fails.
            NewsProviderError: If remote provider fails or returns unparseable content.
        """
        pass
