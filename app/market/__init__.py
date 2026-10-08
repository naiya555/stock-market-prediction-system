"""Market Data Module.

Provides abstractions and adapters for market data acquisition, normalization, and validation.
"""

from app.core.schemas import DataSourceMetadata, MarketOHLCV, MarketQuote
from app.market.providers.base import BaseMarketDataProvider

__all__ = [
    "BaseMarketDataProvider",
    "MarketOHLCV",
    "MarketQuote",
    "DataSourceMetadata",
]
