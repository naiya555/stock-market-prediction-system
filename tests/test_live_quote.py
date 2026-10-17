"""Deterministic Unit Tests for Live Market Quote Engine and YFinance Quote Adapter.

Validates LiveQuote contract constraints, staleness detection, market session alignment,
provider failure handling, and zero-fabrication guarantees with offline fixtures.
Zero external network calls during normal test execution.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from app.core.schemas import MarketQuote, ValidationError
from app.market.pipeline import fetch_live_quote
from app.market.providers.base import BaseMarketDataProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.market.quote import (
    DEFAULT_DELAY_DISCLAIMER,
    DataFreshnessStatus,
    LiveQuote,
)
from app.market.session import IST, MarketSessionState


@pytest.fixture
def sample_live_quote() -> LiveQuote:
    """Fixture providing a standard valid LiveQuote record."""
    now = datetime(2026, 10, 14, 11, 0, 0, tzinfo=IST)
    return LiveQuote(
        symbol="RELIANCE",
        price=2450.50,
        timestamp=now,
        retrieved_at=now,
        source="yfinance",
        session_state=MarketSessionState.REGULAR_HOURS,
        freshness_status=DataFreshnessStatus.DELAYED,
        open_price=2440.0,
        day_high=2465.0,
        day_low=2435.0,
        previous_close=2430.0,
        change=20.50,
        change_percent=0.8436,
        volume=1500000,
        currency="INR",
        is_delayed=True,
        delay_minutes=15,
    )


def test_live_quote_contract_validation(sample_live_quote: LiveQuote) -> None:
    """Verify LiveQuote preserves attributes and validates physical constraints."""
    q = sample_live_quote
    assert q.symbol == "RELIANCE"
    assert q.price == 2450.50
    assert q.source == "yfinance"
    assert q.session_state == MarketSessionState.REGULAR_HOURS
    assert q.freshness_status == DataFreshnessStatus.DELAYED
    assert q.is_delayed is True
    assert q.delay_minutes == 15
    assert q.currency == "INR"
    assert DEFAULT_DELAY_DISCLAIMER in q.disclaimer


def test_live_quote_rejections() -> None:
    """Verify input validation enforces strict physical bounds and rejects invalid types."""
    now = datetime(2026, 10, 14, 11, 0, 0, tzinfo=IST)

    # Empty symbol
    with pytest.raises(ValidationError, match="symbol cannot be empty"):
        LiveQuote(
            symbol="",
            price=100.0,
            timestamp=now,
            retrieved_at=now,
            source="yfinance",
            session_state=MarketSessionState.REGULAR_HOURS,
            freshness_status=DataFreshnessStatus.DELAYED,
        )

    # Non-positive price
    with pytest.raises(ValidationError, match="price must be strictly positive"):
        LiveQuote(
            symbol="TCS",
            price=-10.0,
            timestamp=now,
            retrieved_at=now,
            source="yfinance",
            session_state=MarketSessionState.REGULAR_HOURS,
            freshness_status=DataFreshnessStatus.DELAYED,
        )

    # Invalid timestamp type
    with pytest.raises(ValidationError, match="timestamp must be a valid datetime instance"):
        LiveQuote(
            symbol="TCS",
            price=100.0,
            timestamp="2026-10-14",  # type: ignore
            retrieved_at=now,
            source="yfinance",
            session_state=MarketSessionState.REGULAR_HOURS,
            freshness_status=DataFreshnessStatus.DELAYED,
        )

    # Negative volume
    with pytest.raises(ValidationError, match="volume cannot be negative"):
        LiveQuote(
            symbol="TCS",
            price=100.0,
            timestamp=now,
            retrieved_at=now,
            source="yfinance",
            session_state=MarketSessionState.REGULAR_HOURS,
            freshness_status=DataFreshnessStatus.DELAYED,
            volume=-50,
        )


def test_live_quote_downcasting_and_serialization(sample_live_quote: LiveQuote) -> None:
    """Verify to_market_quote downcasts cleanly to core MarketQuote and to_dict formats properly."""
    mq = sample_live_quote.to_market_quote()
    assert isinstance(mq, MarketQuote)
    assert mq.symbol == "RELIANCE"
    assert mq.price == 2450.50
    assert mq.source == "yfinance"
    assert mq.previous_close == 2430.0
    assert mq.volume == 1500000

    d = sample_live_quote.to_dict()
    assert d["symbol"] == "RELIANCE"
    assert d["price"] == 2450.50
    assert d["session_state"] == "REGULAR_HOURS"
    assert d["freshness_status"] == "DELAYED"
    assert "2026-10-14T11:00:00+05:30" in d["timestamp"]


def test_base_provider_default_fetch_quote_raises() -> None:
    """Verify BaseMarketDataProvider raises NotImplementedError for providers without live support."""
    class SimpleProvider(BaseMarketDataProvider):
        @property
        def name(self) -> str:
            return "simple"

        def fetch_historical_ohlcv(self, symbol, start_date, end_date, interval="1d"):
            return []

    p = SimpleProvider()
    with pytest.raises(NotImplementedError, match="does not implement fetch_quote"):
        p.fetch_quote("RELIANCE")


@patch("app.market.providers.yfinance_provider.yf.Ticker")
def test_yfinance_fetch_quote_success_fast_info(mock_ticker_cls: MagicMock) -> None:
    """Verify YFinanceProvider.fetch_quote extracts data from fast_info and history."""
    now_ist = datetime(2026, 10, 14, 11, 30, 0, tzinfo=IST)

    # Mock fast_info
    mock_fast_info = MagicMock()
    mock_fast_info.last_price = 2450.0
    mock_fast_info.previous_close = 2430.0
    mock_fast_info.open = 2435.0
    mock_fast_info.day_high = 2460.0
    mock_fast_info.day_low = 2430.0
    mock_fast_info.last_volume = 1200000
    mock_fast_info.currency = "INR"

    # Mock intraday history
    df_intra = pd.DataFrame(
        {
            "Open": [2435.0],
            "High": [2460.0],
            "Low": [2430.0],
            "Close": [2450.0],
            "Volume": [1200000],
        },
        index=[pd.Timestamp(now_ist)],
    )

    mock_instance = MagicMock()
    mock_instance.fast_info = mock_fast_info
    mock_instance.history.return_value = df_intra
    mock_ticker_cls.return_value = mock_instance

    provider = YFinanceProvider()
    quote = provider.fetch_quote("RELIANCE")

    assert quote.symbol == "RELIANCE"
    assert quote.price == 2450.0
    assert quote.previous_close == 2430.0
    assert quote.change == 20.0
    assert quote.change_percent == pytest.approx(0.823, abs=0.001)
    assert quote.volume == 1200000
    assert quote.is_delayed is True
    assert quote.delay_minutes == 15


@patch("app.market.providers.yfinance_provider.yf.Ticker")
def test_yfinance_fetch_quote_daily_fallback(mock_ticker_cls: MagicMock) -> None:
    """Verify YFinanceProvider falls back to 5d history when fast_info and intraday are unavailable."""
    trade_time = datetime(2026, 10, 16, 15, 30, 0, tzinfo=IST)

    df_daily = pd.DataFrame(
        {
            "Open": [1200.0, 1215.0],
            "High": [1210.0, 1225.0],
            "Low": [1190.0, 1205.0],
            "Close": [1205.0, 1220.0],
            "Volume": [500000, 600000],
        },
        index=[
            pd.Timestamp("2026-10-15 15:30:00", tz=IST),
            pd.Timestamp(trade_time),
        ],
    )

    mock_instance = MagicMock()
    mock_instance.fast_info = None
    # Intraday returns empty
    mock_instance.history.side_effect = [
        pd.DataFrame(),  # 1m history
        df_daily,        # 5d daily history fallback
    ]
    mock_ticker_cls.return_value = mock_instance

    provider = YFinanceProvider()
    quote = provider.fetch_quote("RELIANCE.NS")

    assert quote.symbol == "RELIANCE"
    assert quote.price == 1220.0
    assert quote.previous_close == 1205.0
    assert quote.change == 15.0
    assert quote.change_percent == pytest.approx(1.2448, abs=0.001)


@patch("app.market.providers.yfinance_provider.yf.Ticker")
def test_yfinance_fetch_quote_no_data_raises_runtime_error(mock_ticker_cls: MagicMock) -> None:
    """Verify provider raises RuntimeError and never invents fake prices when vendor returns no data."""
    mock_instance = MagicMock()
    mock_instance.fast_info = None
    mock_instance.history.return_value = pd.DataFrame()
    mock_ticker_cls.return_value = mock_instance

    provider = YFinanceProvider()
    with pytest.raises(RuntimeError, match="No quote data returned"):
        provider.fetch_quote("NONEXISTENT")


@patch("app.market.providers.yfinance_provider.yf.Ticker")
def test_yfinance_fetch_quote_non_positive_price_raises_validation_error(mock_ticker_cls: MagicMock) -> None:
    """Verify non-positive prices from corrupted vendor feeds raise ValidationError."""
    mock_fast_info = MagicMock()
    mock_fast_info.last_price = 0.0
    mock_instance = MagicMock()
    mock_instance.fast_info = mock_fast_info
    mock_instance.history.return_value = pd.DataFrame()
    mock_ticker_cls.return_value = mock_instance

    provider = YFinanceProvider()
    with pytest.raises(ValidationError, match="Invalid non-positive quote price"):
        provider.fetch_quote("RELIANCE")


def test_fetch_live_quote_pipeline_orchestration() -> None:
    """Verify fetch_live_quote pipeline function orchestrates provider quote retrieval."""
    mock_provider = MagicMock(spec=BaseMarketDataProvider)
    mock_provider.name = "mock_provider"
    expected_quote = LiveQuote(
        symbol="INFY",
        price=1850.0,
        timestamp=datetime(2026, 10, 14, 11, 0, 0, tzinfo=IST),
        retrieved_at=datetime(2026, 10, 14, 11, 0, 0, tzinfo=IST),
        source="mock_provider",
        session_state=MarketSessionState.REGULAR_HOURS,
        freshness_status=DataFreshnessStatus.DELAYED,
    )
    mock_provider.fetch_quote.return_value = expected_quote

    res = fetch_live_quote("INFY", provider=mock_provider)
    assert res == expected_quote
    mock_provider.fetch_quote.assert_called_once_with(symbol="INFY", max_staleness_seconds=3600)
