"""Deterministic Unit Tests for Market Data Cleaning Pipeline.

Validates:
- Preservation of already-clean records
- Missing value detection and quarantine
- Invalid/impossible OHLCV detection (negative prices, geometry violations, negative volume)
- Identical duplicate collapse
- Conflicting duplicate rejection
- Chronological sorting
- Timestamp and timezone normalization to Asia/Kolkata
- Empty input handling
- CleaningSummary audit accuracy
- MarketOHLCV contract compatibility
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pytest

from app.core.schemas import MarketOHLCV
from app.market import CleaningResult, CleaningSummary, clean_market_data

KOLKATA = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def sample_valid_bars():
    """Synthetic already-clean market records."""
    return [
        MarketOHLCV(
            symbol="BHARTIARTL",
            timestamp=datetime(2026, 9, 1, 9, 15, tzinfo=KOLKATA),
            open=1850.0,
            high=1870.0,
            low=1840.0,
            close=1865.0,
            volume=5000000,
            source="yfinance",
        ),
        MarketOHLCV(
            symbol="BHARTIARTL",
            timestamp=datetime(2026, 9, 2, 9, 15, tzinfo=KOLKATA),
            open=1865.0,
            high=1880.0,
            low=1860.0,
            close=1875.0,
            volume=4200000,
            source="yfinance",
        ),
    ]


def test_already_clean_data_remains_unchanged(sample_valid_bars):
    """Verify that pristine records pass through cleaning with zero modifications or drops."""
    result = clean_market_data(sample_valid_bars)

    assert len(result.records) == 2
    assert result.summary.input_count == 2
    assert result.summary.output_count == 2
    assert result.summary.rejected_count == 0
    assert result.summary.missing_records_count == 0
    assert result.summary.invalid_records_count == 0
    assert result.summary.identical_duplicates_count == 0
    assert result.summary.conflicting_duplicates_count == 0
    assert result.summary.is_sorted is True
    assert result.records[0].close == 1865.0
    assert result.records[1].close == 1875.0


def test_empty_input_handling():
    """Verify empty list produces empty result with accurate zero summary."""
    result = clean_market_data([])

    assert result.records == []
    assert result.summary.input_count == 0
    assert result.summary.output_count == 0
    assert result.summary.rejected_count == 0
    assert result.summary.is_sorted is True


def test_missing_required_values_detected():
    """Verify records missing required fields (null, empty, NaN) are quarantined."""
    raw_dicts = [
        # Missing open
        {
            "symbol": "BHARTIARTL",
            "timestamp": "2026-09-01T09:15:00+05:30",
            "open": None,
            "high": 1870.0,
            "low": 1840.0,
            "close": 1865.0,
            "volume": 5000000,
            "source": "test",
        },
        # Empty symbol
        {
            "symbol": "   ",
            "timestamp": "2026-09-02T09:15:00+05:30",
            "open": 1850.0,
            "high": 1870.0,
            "low": 1840.0,
            "close": 1865.0,
            "volume": 5000000,
            "source": "test",
        },
        # NaN close
        {
            "symbol": "BHARTIARTL",
            "timestamp": "2026-09-03T09:15:00+05:30",
            "open": 1850.0,
            "high": 1870.0,
            "low": 1840.0,
            "close": float("nan"),
            "volume": 5000000,
            "source": "test",
        },
        # Valid record
        {
            "symbol": "BHARTIARTL",
            "timestamp": "2026-09-04T09:15:00+05:30",
            "open": 1850.0,
            "high": 1870.0,
            "low": 1840.0,
            "close": 1865.0,
            "volume": 5000000,
            "source": "test",
        },
    ]

    result = clean_market_data(raw_dicts)

    assert result.summary.input_count == 4
    assert result.summary.output_count == 1
    assert result.summary.missing_records_count == 3
    assert result.summary.rejected_count == 3
    assert len(result.records) == 1
    assert result.records[0].timestamp.date() == datetime(2026, 9, 4).date()


def test_invalid_ohlc_and_negative_volume_rejected():
    """Verify non-positive prices, negative volume, and geometry violations are rejected."""
    bad_records = [
        # Zero price
        {
            "symbol": "BHARTIARTL",
            "timestamp": "2026-09-01T09:15:00+05:30",
            "open": 0.0,
            "high": 1870.0,
            "low": 1840.0,
            "close": 1865.0,
            "volume": 1000,
            "source": "test",
        },
        # Negative volume
        {
            "symbol": "BHARTIARTL",
            "timestamp": "2026-09-02T09:15:00+05:30",
            "open": 1850.0,
            "high": 1870.0,
            "low": 1840.0,
            "close": 1865.0,
            "volume": -500,
            "source": "test",
        },
        # High lower than Open (candle geometry violation)
        {
            "symbol": "BHARTIARTL",
            "timestamp": "2026-09-03T09:15:00+05:30",
            "open": 1850.0,
            "high": 1840.0,
            "low": 1830.0,
            "close": 1835.0,
            "volume": 1000,
            "source": "test",
        },
        # Low higher than Close (candle geometry violation)
        {
            "symbol": "BHARTIARTL",
            "timestamp": "2026-09-04T09:15:00+05:30",
            "open": 1850.0,
            "high": 1870.0,
            "low": 1860.0,
            "close": 1845.0,
            "volume": 1000,
            "source": "test",
        },
    ]

    result = clean_market_data(bad_records)

    assert result.summary.input_count == 4
    assert result.summary.output_count == 0
    assert result.summary.invalid_records_count == 4
    assert result.summary.rejected_count == 4


def test_identical_duplicates_collapsed():
    """Verify duplicate records with identical price and volume collapse to 1 bar."""
    ts = datetime(2026, 9, 1, 9, 15, tzinfo=KOLKATA)
    records = [
        MarketOHLCV("BHARTIARTL", ts, 1850.0, 1870.0, 1840.0, 1865.0, 5000000, "yfinance"),
        MarketOHLCV("BHARTIARTL", ts, 1850.0, 1870.0, 1840.0, 1865.0, 5000000, "yfinance"),
        MarketOHLCV("BHARTIARTL", ts, 1850.0, 1870.0, 1840.0, 1865.0, 5000000, "yfinance"),
    ]

    result = clean_market_data(records)

    assert result.summary.input_count == 3
    assert result.summary.output_count == 1
    assert result.summary.identical_duplicates_count == 2
    assert result.summary.rejected_count == 2
    assert len(result.records) == 1
    assert result.records[0].close == 1865.0


def test_conflicting_duplicates_rejected():
    """Verify duplicate records with conflicting prices are quarantined rather than guessed."""
    ts = datetime(2026, 9, 1, 9, 15, tzinfo=KOLKATA)
    records = [
        MarketOHLCV("BHARTIARTL", ts, 1850.0, 1870.0, 1840.0, 1865.0, 5000000, "src1"),
        MarketOHLCV("BHARTIARTL", ts, 1850.0, 1870.0, 1840.0, 1860.0, 5000000, "src2"),  # Close conflicts (1860 vs 1865)!
    ]

    result = clean_market_data(records)

    assert result.summary.input_count == 2
    assert result.summary.output_count == 0
    assert result.summary.conflicting_duplicates_count == 2
    assert result.summary.rejected_count == 2
    assert len(result.records) == 0


def test_chronological_sorting():
    """Verify out-of-order records are sorted by (symbol, timestamp) ascending."""
    t1 = datetime(2026, 9, 1, tzinfo=KOLKATA)
    t2 = datetime(2026, 9, 2, tzinfo=KOLKATA)
    t3 = datetime(2026, 9, 3, tzinfo=KOLKATA)

    # Inverted order: t3, t1, t2
    records = [
        MarketOHLCV("BHARTIARTL", t3, 1870.0, 1890.0, 1865.0, 1885.0, 3000, "src"),
        MarketOHLCV("BHARTIARTL", t1, 1850.0, 1870.0, 1840.0, 1865.0, 5000, "src"),
        MarketOHLCV("BHARTIARTL", t2, 1865.0, 1880.0, 1860.0, 1875.0, 4000, "src"),
    ]

    result = clean_market_data(records)

    assert len(result.records) == 3
    assert result.summary.is_sorted is True
    assert result.records[0].timestamp == t1
    assert result.records[1].timestamp == t2
    assert result.records[2].timestamp == t3


def test_timestamp_and_timezone_normalization():
    """Verify timezone normalization maps naive and UTC timestamps to Asia/Kolkata preserving session date."""
    # Naive timestamp
    naive_bar = MarketOHLCV(
        symbol="BHARTIARTL",
        timestamp=datetime(2026, 9, 1, 0, 0),
        open=1850.0,
        high=1870.0,
        low=1840.0,
        close=1865.0,
        volume=5000,
        source="src",
    )
    # Aware UTC timestamp corresponding to 2026-09-02 05:30 IST
    utc_bar = MarketOHLCV(
        symbol="BHARTIARTL",
        timestamp=datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc),
        open=1865.0,
        high=1880.0,
        low=1860.0,
        close=1875.0,
        volume=4000,
        source="src",
    )

    result = clean_market_data([naive_bar, utc_bar])

    assert len(result.records) == 2
    r1, r2 = result.records[0], result.records[1]

    # Check both have tzinfo matching Asia/Kolkata
    assert str(r1.timestamp.tzinfo) == "Asia/Kolkata"
    assert str(r2.timestamp.tzinfo) == "Asia/Kolkata"

    # Calendar dates are preserved
    assert r1.timestamp.date() == datetime(2026, 9, 1).date()
    assert r2.timestamp.date() == datetime(2026, 9, 2).date()


def test_cleaning_result_summary_to_dict():
    """Verify CleaningSummary converts cleanly to serializable dictionary."""
    summary = CleaningSummary(
        input_count=10,
        output_count=8,
        missing_records_count=1,
        identical_duplicates_count=1,
        conflicting_duplicates_count=0,
        invalid_records_count=0,
        rejected_count=2,
        is_sorted=True,
        rejection_reasons=["reason1"],
    )
    data = summary.to_dict()
    assert data["input_count"] == 10
    assert data["output_count"] == 8
    assert data["rejected_count"] == 2
    assert data["is_sorted"] is True
    assert data["rejection_reasons"] == ["reason1"]


def test_clean_market_data_iterable_input(sample_valid_bars):
    """Verify that cleaner properly handles iterators/generators without length errors."""
    def bar_generator():
        for bar in sample_valid_bars:
            yield bar

    result = clean_market_data(bar_generator())
    assert len(result.records) == 2
    assert result.summary.input_count == 2
    assert result.summary.output_count == 2

