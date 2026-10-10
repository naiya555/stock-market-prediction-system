"""Unit Tests for Market Data Pipeline Orchestration Layer.

Validates end-to-end integration of provider, cleaner, and return/volatility feature
engine in offline mode without network access.
"""

from datetime import datetime, timezone
from typing import List, Sequence

import pytest

from app.core.schemas import MarketOHLCV
from app.market.pipeline import (
    MarketDataPipelineResult,
    process_market_data,
    run_market_data_pipeline,
)
from app.market.providers.base import BaseMarketDataProvider


class MockMarketDataProvider(BaseMarketDataProvider):
    """Deterministic mock provider returning fixed canonical bars without network access."""

    def __init__(self, records: Sequence[MarketOHLCV]):
        self._records = list(records)

    @property
    def name(self) -> str:
        return "mock_provider"

    def fetch_historical_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[MarketOHLCV]:
        return [r for r in self._records if r.symbol == symbol]


def _make_bar(
    symbol: str = "BHARTIARTL",
    day: int = 1,
    close: float = 100.0,
    open_: float = 100.0,
    high: float = 105.0,
    low: float = 95.0,
    volume: int = 1000,
) -> MarketOHLCV:
    """Helper to generate valid canonical MarketOHLCV bars."""
    return MarketOHLCV(
        symbol=symbol,
        timestamp=datetime(2026, 9, day, 10, 0, tzinfo=timezone.utc),
        open=open_,
        high=max(high, open_, close),
        low=min(low, open_, close),
        close=close,
        volume=volume,
        source="mock_feed",
    )


def test_process_market_data_end_to_end():
    """Verify offline pipeline processes raw bars through cleaner and feature generator."""
    raw_bars = [
        _make_bar(day=1, close=100.0),
        _make_bar(day=2, close=105.0),
        _make_bar(day=3, close=110.0),
        _make_bar(day=4, close=115.0),
        _make_bar(day=5, close=120.0),
        _make_bar(day=6, close=125.0),
    ]

    result = process_market_data(raw_bars, rolling_return_windows=(3, 5), volatility_windows=(5,))

    assert isinstance(result, MarketDataPipelineResult)
    assert result.symbol == "BHARTIARTL"
    assert not result.is_empty
    assert result.record_count == 6
    assert len(result.cleaned_records) == 6
    assert result.cleaning_summary.output_count == 6
    assert result.cleaning_summary.rejected_count == 0

    # Verify features
    features = result.features
    assert len(features) == 6
    assert features[0].daily_return is None
    assert features[1].daily_return == pytest.approx(0.05)
    assert features[3].rolling_return_3d is not None
    assert features[5].rolling_return_5d is not None
    assert features[5].volatility_5d is not None

    # Verify indicators
    indicators = result.indicators
    assert len(indicators) == 6
    assert indicators[0].sma_5 is None
    assert indicators[4].sma_5 == pytest.approx(110.0)  # (100+105+110+115+120)/5 = 110
    assert indicators[5].sma_5 == pytest.approx(115.0)  # (105+110+115+120+125)/5 = 115
    assert indicators[5].sma_10 is None  # 6 bars < 10 window
def test_process_market_data_empty():
    """Verify pipeline behavior on empty input sequence."""
    result = process_market_data([])
    assert result.is_empty
    assert result.record_count == 0
    assert result.raw_records == []
    assert result.cleaned_records == []
    assert result.features == []


def test_process_market_data_filters_invalid():
    """Verify pipeline filters invalid bars and handles duplicates deterministically."""
    valid_bar1 = _make_bar(day=1, close=100.0)
    dupe_bar1 = _make_bar(day=1, close=100.0)  # Identical duplicate
    valid_bar2 = _make_bar(day=2, close=110.0)

    result = process_market_data([valid_bar1, dupe_bar1, valid_bar2])
    assert result.record_count == 2
    assert result.cleaning_summary.identical_duplicates_count == 1
    assert len(result.cleaned_records) == 2


def test_pipeline_serialization():
    """Verify dictionary serialization methods of MarketDataPipelineResult."""
    bars = [_make_bar(day=1, close=100.0), _make_bar(day=2, close=105.0)]
    result = process_market_data(bars)

    summary_dict = result.to_dict()
    assert summary_dict["symbol"] == "BHARTIARTL"
    assert summary_dict["raw_count"] == 2
    assert summary_dict["cleaned_count"] == 2
    assert summary_dict["feature_count"] == 2
    assert summary_dict["indicator_count"] == 2
    assert "cleaning_summary" in summary_dict

    feature_dicts = result.to_feature_dicts()
    assert len(feature_dicts) == 2
    assert feature_dicts[0]["daily_return"] is None
    assert feature_dicts[1]["daily_return"] == pytest.approx(0.05)

    indicator_dicts = result.to_indicator_dicts()
    assert len(indicator_dicts) == 2
    assert indicator_dicts[0]["symbol"] == "BHARTIARTL"
    assert indicator_dicts[0]["close"] == 100.0


def test_run_market_data_pipeline_with_mock_provider():
    """Verify run_market_data_pipeline orchestrates provider, cleaning, and features."""
    bars = [
        _make_bar(day=1, close=1800.0),
        _make_bar(day=2, close=1820.0),
        _make_bar(day=3, close=1810.0),
    ]
    mock_provider = MockMarketDataProvider(bars)

    result = run_market_data_pipeline(
        symbol="BHARTIARTL",
        start_date=datetime(2026, 9, 1),
        end_date=datetime(2026, 9, 4),
        provider=mock_provider,
    )

    assert result.symbol == "BHARTIARTL"
    assert result.record_count == 3
    assert result.features[0].daily_return is None
    assert result.features[1].daily_return == pytest.approx((1820.0 / 1800.0) - 1.0)
    assert len(result.indicators) == 3
    assert result.indicators[0].sma_5 is None  # 3 bars < 5 window
    indicator_dicts = result.to_indicator_dicts()
    assert len(indicator_dicts) == 3
    assert "sma_5" in indicator_dicts[0]
    assert "ema_5" in indicator_dicts[0]
    assert "rsi_14" in indicator_dicts[0]


def test_run_market_data_pipeline_with_default_lookback():
    """Verify run_market_data_pipeline calculates start_date from lookback_days when omitted."""
    bars = [
        _make_bar(day=1, close=1800.0),
        _make_bar(day=2, close=1820.0),
    ]
    mock_provider = MockMarketDataProvider(bars)

    result = run_market_data_pipeline(
        symbol="BHARTIARTL",
        lookback_days=180,
        provider=mock_provider,
    )

    assert result.symbol == "BHARTIARTL"
    assert result.record_count == 2
    assert len(result.indicators) == 2


def test_pipeline_macd_integration():
    """Verify market data pipeline computes and serializes MACD indicators."""
    bars = [_make_bar(day=i, close=100.0 + i * 2.0) for i in range(1, 15)]
    # Use small periods for integration test: fast=2, slow=4, signal=2
    result = process_market_data(
        bars,
        macd_fast=2,
        macd_slow=4,
        macd_signal=2,
    )

    assert len(result.indicators) == 14
    # With fast=2, slow=4, signal=2:
    # Index 3 (4th bar) is first valid MACD line
    # Index 4 (5th bar) is first valid signal line and histogram
    assert result.indicators[2].macd_line is None
    assert result.indicators[3].macd_line is not None
    assert result.indicators[3].signal_line is None
    assert result.indicators[4].signal_line is not None
    assert result.indicators[4].histogram is not None
    assert result.indicators[4].histogram == pytest.approx(
        result.indicators[4].macd_line - result.indicators[4].signal_line
    )

    # Verify serialization
    indicator_dicts = result.to_indicator_dicts()
    assert len(indicator_dicts) == 14
    assert "macd" in indicator_dicts[4]
    assert "macd_signal" in indicator_dicts[4]
    assert "macd_histogram" in indicator_dicts[4]
    assert indicator_dicts[4]["macd"] is not None
    assert indicator_dicts[4]["macd_signal"] is not None
    assert indicator_dicts[4]["macd_histogram"] is not None
