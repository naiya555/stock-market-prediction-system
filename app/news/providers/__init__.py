"""News Providers Package."""

from app.news.providers.base import BaseNewsProvider, NewsProviderError
from app.news.providers.rss_provider import COMPANY_NAME_MAP, RSSNewsProvider

__all__ = [
    "BaseNewsProvider",
    "NewsProviderError",
    "RSSNewsProvider",
    "COMPANY_NAME_MAP",
]
