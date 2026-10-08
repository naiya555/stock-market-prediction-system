"""Unit Tests for Market Data Module and Provider Contracts.

Validates deterministic contracts, imports, abstract interface enforcement,
canonical schema identity, and provenance tracking without external API calls.
"""

from datetime import datetime, timezone
from typing import List
import pytest

from app.core.schemas import DataSourceMetadata, MarketOHLCV, MarketQuote, ValidationError
from app.market import (
    BaseMarketDataProvider,
    DataSourceMetadata as MarketDataSourceMetadata,
    MarketOHLCV as MarketModuleOHLCV,
    MarketQuote as MarketModuleQuote,
)
from app.market.providers import BaseMarketDataProvider as ProvidersBaseMarketDataProvider
from app.market.providers.base import BaseMarketDataProvider as DirectBaseMarketDataProvider


def test_market_package_imports() -> None:
    """Verify all market package modules and contracts import cleanly."""
    assert BaseMarketDataProvider is ProvidersBaseMarketDataProvider
    assert BaseMarketDataProvider is DirectBaseMarketDataProvider


def test_no_competing_or_duplicate_schemas() -> None:
    """Verify canonical schemas in app.market are exact identical references to app.core.schemas."""
    assert MarketModuleOHLCV is MarketOHLCV
    assert MarketModuleQuote is MarketQuote
    assert MarketDataSourceMetadata is DataSourceMetadata


def test_base_provider_abstract_instantiation_rejected() -> None:
    """Verify BaseMarketDataProvider cannot be directly instantiated."""
    with pytest.raises(TypeError) as excinfo:
        BaseMarketDataProvider()  # type: ignore[abstract]
    assert "Can't instantiate abstract class BaseMarketDataProvider" in str(excinfo.value)


def test_incomplete_provider_subclass_rejected() -> None:
    """Verify subclass lacking either name or fetch_historical_ohlcv cannot be instantiated."""

    class MissingFetchProvider(BaseMarketDataProvider):
        @property
        def name(self) -> str:
            return "test_missing_fetch"

    with pytest.raises(TypeError):
        MissingFetchProvider()  # type: ignore[abstract]

    class MissingNameProvider(BaseMarketDataProvider):
        def fetch_historical_ohlcv(
            self,
            symbol: str,
            start_date: datetime,
            end_date: datetime,
            interval: str = "1d",
        ) -> List[MarketOHLCV]:
            return []

    with pytest.raises(TypeError):
        MissingNameProvider()  # type: ignore[abstract]


def test_conforming_provider_contract_implementation() -> None:
    """Verify a conforming provider implementation adheres to the contract and returns canonical records."""

    class SyntheticTestProvider(BaseMarketDataProvider):
        @property
        def name(self) -> str:
            return "synthetic_test_provider"

        def fetch_historical_ohlcv(
            self,
            symbol: str,
            start_date: datetime,
            end_date: datetime,
            interval: str = "1d",
        ) -> List[MarketOHLCV]:
            # Returns a single canonical bar for contract verification
            return [
                MarketOHLCV(
                    symbol=symbol,
                    timestamp=start_date,
                    open=1500.0,
                    high=1520.0,
                    low=1490.0,
                    close=1510.0,
                    volume=100000,
                    source=self.name,
                )
            ]

    provider = SyntheticTestProvider()
    assert provider.name == "synthetic_test_provider"

    dt_start = datetime(2026, 1, 1, 9, 15, tzinfo=timezone.utc)
    dt_end = datetime(2026, 1, 1, 15, 30, tzinfo=timezone.utc)

    records = provider.fetch_historical_ohlcv(
        symbol="BHARTIARTL",
        start_date=dt_start,
        end_date=dt_end,
        interval="1d",
    )

    assert len(records) == 1
    record = records[0]
    assert isinstance(record, MarketOHLCV)
    assert record.symbol == "BHARTIARTL"
    assert record.source == "synthetic_test_provider"
    assert record.timestamp == dt_start
    assert record.open == 1500.0
    assert record.high == 1520.0
    assert record.low == 1490.0
    assert record.close == 1510.0
    assert record.volume == 100000


def test_provider_contract_enforces_domain_validation_on_bad_data() -> None:
    """Verify that malformed records produced during provider parsing fail fast via ValidationError."""

    class FaultyProvider(BaseMarketDataProvider):
        @property
        def name(self) -> str:
            return "faulty_provider"

        def fetch_historical_ohlcv(
            self,
            symbol: str,
            start_date: datetime,
            end_date: datetime,
            interval: str = "1d",
        ) -> List[MarketOHLCV]:
            # Violates physical bounds (high < max(open, close))
            return [
                MarketOHLCV(
                    symbol=symbol,
                    timestamp=start_date,
                    open=1500.0,
                    high=1400.0,  # Unphysical: lower than open
                    low=1350.0,
                    close=1450.0,
                    volume=50000,
                    source=self.name,
                )
            ]

    provider = FaultyProvider()
    dt = datetime(2026, 1, 1, 9, 15, tzinfo=timezone.utc)

    with pytest.raises(ValidationError) as excinfo:
        provider.fetch_historical_ohlcv("BHARTIARTL", dt, dt)
    assert "high (1400.0) cannot be lower than open (1500.0)" in str(excinfo.value)
