"""Abstract Base Contract for Market Data Providers.

Defines the interface for acquiring historical and real-time market data.
All provider implementations must normalize external payloads into
canonical MarketOHLCV records from app.core.schemas.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from app.core.schemas import MarketOHLCV


class BaseMarketDataProvider(ABC):
    """Abstract base class defining the contract for market data providers.

    Subclasses implement communication with specific data sources
    (e.g., Yahoo Finance, NSE Bhavcopy, Broker APIs) and map raw
    source payloads into canonical, validated MarketOHLCV objects.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique provider identifier (e.g., 'yfinance', 'nse_bhavcopy')."""
        pass

    @abstractmethod
    def fetch_historical_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[MarketOHLCV]:
        """Fetch historical OHLCV data for a given symbol within a date range.

        Args:
            symbol: Ticker symbol (e.g., 'BHARTIARTL').
            start_date: Inclusive start datetime of the observation window.
            end_date: Inclusive end datetime of the observation window.
            interval: Bar aggregation interval (default '1d').

        Returns:
            List of canonical MarketOHLCV records sorted in chronological order.

        Raises:
            ValidationError: If returned data violates canonical schema bounds.
            Exception: If provider communication or parsing fails.
        """
        pass
