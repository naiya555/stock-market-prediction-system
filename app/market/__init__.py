"""Market Data Module.

Provides abstractions and adapters for market data acquisition, normalization, and validation.
"""

from app.core.schemas import DataSourceMetadata, MarketOHLCV, MarketQuote
from app.market.cleaner import CleaningResult, CleaningSummary, clean_market_data
from app.market.providers.base import BaseMarketDataProvider
from app.market.providers.yfinance_provider import YFinanceProvider

__all__ = [
    "BaseMarketDataProvider",
    "YFinanceProvider",
    "MarketOHLCV",
    "MarketQuote",
    "DataSourceMetadata",
    "clean_market_data",
    "CleaningResult",
    "CleaningSummary",
]


