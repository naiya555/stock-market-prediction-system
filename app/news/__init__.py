"""Financial News Ingestion and Processing Module.

Provides data contracts, provider adapters, deduplication algorithms, and
point-in-time temporal filtering for Indian equity financial news.
"""

from app.news.cleaner import (
    NewsCleaningResult,
    NewsDeduplicationSummary,
    deduplicate_news,
    filter_news_point_in_time,
)
from app.news.providers.base import BaseNewsProvider, NewsProviderError
from app.news.providers.rss_provider import COMPANY_NAME_MAP, RSSNewsProvider
from app.news.schemas import NewsArticle

__all__ = [
    "NewsArticle",
    "BaseNewsProvider",
    "NewsProviderError",
    "RSSNewsProvider",
    "COMPANY_NAME_MAP",
    "NewsCleaningResult",
    "NewsDeduplicationSummary",
    "deduplicate_news",
    "filter_news_point_in_time",
]
