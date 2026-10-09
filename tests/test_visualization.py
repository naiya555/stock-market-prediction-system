"""Unit Tests for Historical Market Data Visualizer.

Validates offline chart generation for closing price time series and daily percentage
returns without network access.
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from app.core.schemas import MarketOHLCV
from app.market.returns import compute_market_returns
from app.market.visualizer import (
    generate_market_charts,
    plot_closing_prices,
    plot_daily_returns,
)


def _make_bar(
    symbol: str = "BHARTIARTL",
    day: int = 1,
    close: float = 100.0,
) -> MarketOHLCV:
    """Helper to generate valid canonical MarketOHLCV bars."""
    return MarketOHLCV(
        symbol=symbol,
        timestamp=datetime(2026, 9, day, 10, 0, tzinfo=timezone.utc),
        open=close,
        high=close * 1.02,
        low=close * 0.98,
        close=close,
        volume=1000,
        source="test_feed",
    )


def test_plot_closing_prices_generates_valid_image(tmp_path: Path):
    """Verify plot_closing_prices writes a valid non-empty PNG file to disk."""
    bars = [
        _make_bar(day=1, close=100.0),
        _make_bar(day=2, close=105.0),
        _make_bar(day=3, close=103.0),
        _make_bar(day=4, close=108.0),
    ]

    dest = tmp_path / "test_close_price.png"
    result_path = plot_closing_prices(bars, dest)

    assert result_path == dest
    assert dest.exists()
    assert dest.stat().st_size > 1000  # Reasonable size for a 150 DPI chart
    # Verify standard PNG magic signature
    assert dest.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_plot_daily_returns_generates_valid_image(tmp_path: Path):
    """Verify plot_daily_returns writes a valid PNG bar chart with positive and negative returns."""
    bars = [
        _make_bar(day=1, close=100.0),
        _make_bar(day=2, close=105.0),  # Positive
        _make_bar(day=3, close=98.0),   # Negative
        _make_bar(day=4, close=102.0),  # Positive
    ]
    features = compute_market_returns(bars)

    dest = tmp_path / "test_daily_returns.png"
    result_path = plot_daily_returns(features, dest)

    assert result_path == dest
    assert dest.exists()
    assert dest.stat().st_size > 1000
    assert dest.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_market_charts_creates_both_plots(tmp_path: Path):
    """Verify generate_market_charts produces both price and returns PNGs."""
    bars = [
        _make_bar(day=1, close=1800.0),
        _make_bar(day=2, close=1820.0),
        _make_bar(day=3, close=1810.0),
        _make_bar(day=4, close=1850.0),
    ]
    features = compute_market_returns(bars)

    chart_paths = generate_market_charts(features, output_dir=tmp_path, symbol="BHARTIARTL")

    assert "price_chart" in chart_paths
    assert "returns_chart" in chart_paths

    assert chart_paths["price_chart"].exists()
    assert chart_paths["returns_chart"].exists()
    assert chart_paths["price_chart"].name == "bhartiartl_close_price.png"
    assert chart_paths["returns_chart"].name == "bhartiartl_daily_returns.png"


def test_plot_closing_prices_empty_raises_value_error(tmp_path: Path):
    """Verify empty input sequence raises ValueError."""
    dest = tmp_path / "empty.png"
    with pytest.raises(ValueError, match="input data sequence is empty"):
        plot_closing_prices([], dest)


def test_plot_daily_returns_empty_raises_value_error(tmp_path: Path):
    """Verify empty input or input without valid returns raises ValueError."""
    dest = tmp_path / "empty_rets.png"
    with pytest.raises(ValueError, match="features sequence is empty"):
        plot_daily_returns([], dest)

    # 1 bar has no valid daily returns (first observation is None)
    single_bar = [_make_bar(day=1, close=100.0)]
    features = compute_market_returns(single_bar)
    with pytest.raises(ValueError, match="no valid daily return observations exist"):
        plot_daily_returns(features, dest)


def test_plot_accepts_unsorted_data(tmp_path: Path):
    """Verify visualizer handles unsorted chronological data cleanly."""
    bar1 = _make_bar(day=1, close=100.0)
    bar2 = _make_bar(day=2, close=105.0)
    bar3 = _make_bar(day=3, close=110.0)

    # Shuffled input
    shuffled = [bar3, bar1, bar2]
    dest = tmp_path / "shuffled.png"
    plot_closing_prices(shuffled, dest)
    assert dest.exists()
