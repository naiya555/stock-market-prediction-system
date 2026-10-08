"""Deterministic Unit Tests for YFinanceProvider Adapter.

Validates provider contract implementation, symbol normalization,
DataFrame-to-MarketOHLCV mapping, price convention, timestamp handling,
error propagation, and edge case resilience using offline mock fixtures.
Zero external network calls during normal pytest execution.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from app.core.schemas import MarketOHLCV, ValidationError
from app.market.providers.base import BaseMarketDataProvider
from app.market.providers.yfinance_provider import YFinanceProvider


@pytest.fixture
def provider() -> YFinanceProvider:
    return YFinanceProvider()


def test_provider_initialization_and_contract(provider: YFinanceProvider) -> None:
    """Verify YFinanceProvider implements BaseMarketDataProvider and defines unique name."""
    assert isinstance(provider, BaseMarketDataProvider)
    assert provider.name == "yfinance"


def test_symbol_resolution(provider: YFinanceProvider) -> None:
    """Verify symbol normalization handles bare symbols and exchange-suffixed tickers."""
    base, query = provider._resolve_symbols("BHARTIARTL")
    assert base == "BHARTIARTL"
    assert query == "BHARTIARTL.NS"

    base_ns, query_ns = provider._resolve_symbols("bhartiartl.ns")
    assert base_ns == "BHARTIARTL"
    assert query_ns == "BHARTIARTL.NS"

    base_bse, query_bse = provider._resolve_symbols("TCS.BO")
    assert base_bse == "TCS"
    assert query_bse == "TCS.BO"


def test_input_validation_rejections(provider: YFinanceProvider) -> None:
    """Verify input boundaries reject empty symbol, bad date types, or inverted date ranges."""
    dt1 = datetime(2026, 9, 1, tzinfo=timezone.utc)
    dt2 = datetime(2026, 9, 5, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="symbol cannot be empty"):
        provider.fetch_historical_ohlcv("", dt1, dt2)

    with pytest.raises(ValidationError, match="symbol cannot be empty"):
        provider.fetch_historical_ohlcv("   ", dt1, dt2)

    with pytest.raises(ValidationError, match="must be datetime instances"):
        provider.fetch_historical_ohlcv("BHARTIARTL", "2026-09-01", dt2)  # type: ignore

    with pytest.raises(ValidationError, match="cannot be after end_date"):
        provider.fetch_historical_ohlcv("BHARTIARTL", dt2, dt1)


def test_successful_normalization_and_unadjusted_price_convention(provider: YFinanceProvider) -> None:
    """Verify provider output maps correctly into canonical MarketOHLCV using unadjusted prices."""
    # Synthetic DataFrame with raw Close and distinct Adj Close
    data = {
        "Open": [1820.0, 1835.0],
        "High": [1845.0, 1850.0],
        "Low": [1810.0, 1830.0],
        "Close": [1840.0, 1845.0],
        "Adj Close": [1800.0, 1805.0],  # Different from raw close to test price convention
        "Volume": [2500000, 3100000],
    }
    dates = pd.DatetimeIndex(["2026-09-01", "2026-09-02"], name="Date")
    mock_df = pd.DataFrame(data, index=dates)

    dt_start = datetime(2026, 9, 1)
    dt_end = datetime(2026, 9, 2)

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_instance

        records = provider.fetch_historical_ohlcv("BHARTIARTL", dt_start, dt_end)

        mock_instance.history.assert_called_once_with(
            start="2026-09-01",
            end="2026-09-03",  # end_date + 1 day
            interval="1d",
            auto_adjust=False,  # Unadjusted raw series convention
        )

    assert len(records) == 2

    r1 = records[0]
    assert isinstance(r1, MarketOHLCV)
    assert r1.symbol == "BHARTIARTL"
    assert r1.source == "yfinance"
    assert r1.open == 1820.0
    assert r1.high == 1845.0
    assert r1.low == 1810.0
    assert r1.close == 1840.0  # Uses raw Close, NOT Adj Close (1800.0)
    assert r1.volume == 2500000
    assert r1.timestamp.date() == datetime(2026, 9, 1).date()

    r2 = records[1]
    assert r2.close == 1845.0
    assert r2.volume == 3100000
    assert r2.timestamp.date() == datetime(2026, 9, 2).date()


def test_empty_response_handling(provider: YFinanceProvider) -> None:
    """Verify empty DataFrame from provider returns an empty list without error."""
    dt_start = datetime(2026, 9, 6)
    dt_end = datetime(2026, 9, 7)

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame()
        mock_ticker_cls.return_value = mock_instance

        records = provider.fetch_historical_ohlcv("BHARTIARTL", dt_start, dt_end)

    assert records == []


def test_missing_required_columns_error(provider: YFinanceProvider) -> None:
    """Verify missing price/volume columns in provider response raises RuntimeError."""
    bad_df = pd.DataFrame({"Open": [1800.0], "Close": [1810.0]}, index=pd.DatetimeIndex(["2026-09-01"]))
    dt = datetime(2026, 9, 1)

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_instance = MagicMock()
        mock_instance.history.return_value = bad_df
        mock_ticker_cls.return_value = mock_instance

        with pytest.raises(RuntimeError, match="missing required columns"):
            provider.fetch_historical_ohlcv("BHARTIARTL", dt, dt)


def test_provider_network_exception_propagates(provider: YFinanceProvider) -> None:
    """Verify upstream network/HTTP failure is cleanly wrapped and propagated."""
    dt = datetime(2026, 9, 1)

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_instance = MagicMock()
        mock_instance.history.side_effect = ConnectionError("Connection refused by host")
        mock_ticker_cls.return_value = mock_instance

        with pytest.raises(RuntimeError, match="yfinance fetch failed"):
            provider.fetch_historical_ohlcv("BHARTIARTL", dt, dt)


def test_nan_rows_filtered_out(provider: YFinanceProvider) -> None:
    """Verify rows containing NaN in price or volume fields are skipped cleanly."""
    data = {
        "Open": [1820.0, float("nan")],
        "High": [1845.0, 1850.0],
        "Low": [1810.0, 1830.0],
        "Close": [1840.0, 1845.0],
        "Volume": [2500000, 3100000],
    }
    dates = pd.DatetimeIndex(["2026-09-01", "2026-09-02"], name="Date")
    mock_df = pd.DataFrame(data, index=dates)

    dt_start = datetime(2026, 9, 1)
    dt_end = datetime(2026, 9, 2)

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_instance

        records = provider.fetch_historical_ohlcv("BHARTIARTL", dt_start, dt_end)

    assert len(records) == 1
    assert records[0].open == 1820.0


def test_malformed_unphysical_bar_fails_canonical_validation(provider: YFinanceProvider) -> None:
    """Verify that unphysical prices (e.g. High < Low) fail fast via canonical ValidationError."""
    data = {
        "Open": [1820.0],
        "High": [1800.0],  # Lower than Open
        "Low": [1810.0],
        "Close": [1805.0],
        "Volume": [2500000],
    }
    dates = pd.DatetimeIndex(["2026-09-01"], name="Date")
    mock_df = pd.DataFrame(data, index=dates)

    dt = datetime(2026, 9, 1)

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_instance

        with pytest.raises(ValidationError, match="high .* cannot be less than low"):
            provider.fetch_historical_ohlcv("BHARTIARTL", dt, dt)
