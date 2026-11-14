from datetime import datetime, timedelta
from pathlib import Path

from app.core.schemas import MarketOHLCV
from app.market.quality.monitor import monitor_records


def bar(day: int, close: float = 100.0, *, close_only: bool = False, volume: int = 100) -> MarketOHLCV:
    return MarketOHLCV(
        symbol="NIFTY_TELECOMMUNICATIONS" if close_only else "BHARTIARTL",
        timestamp=datetime(2026, 9, day, 10, 0),
        open=None if close_only else close,
        high=None if close_only else close,
        low=None if close_only else close,
        close=close,
        volume=0 if close_only else volume,
        source="test",
        is_close_only=close_only,
        volume_reported=not close_only,
    )


def test_valid_equity_and_close_only_index_records_pass():
    equity = monitor_records("BHARTIARTL", [bar(1), bar(2, 101)], provider="test")
    index = monitor_records("NIFTY_TELECOMMUNICATIONS", [bar(1, close_only=True), bar(2, 101, close_only=True)], provider="test")
    assert equity["instrument_type"] == "EQUITY"
    assert index["close_only"] is True
    assert not any(f["check_name"] == "ohlc_completeness" for f in index["findings"])


def test_duplicates_invalid_geometry_and_negative_volume_are_reported():
    records = [bar(1), bar(1)]
    result = monitor_records("BHARTIARTL", records, provider="test")
    assert any(f["check_name"] == "duplicate_timestamp" and f["status"] == "FAIL" for f in result["findings"])

    invalid = {
        "symbol": "BHARTIARTL",
        "timestamp": datetime(2026, 9, 2, 10, 0),
        "open": 100.0, "high": 99.0, "low": 98.0, "close": 100.0,
        "volume": -1, "source": "test",
    }
    from app.market.cleaner import clean_market_data
    cleaned = clean_market_data([invalid])
    assert cleaned.summary.rejected_count == 1
    assert monitor_records("BHARTIARTL", [], provider="test")["overall_status"] == "FAIL"


def test_gap_weekend_stale_and_anomaly_findings_are_non_destructive():
    records = [bar(1, 100), bar(5, 130, volume=2000)]
    before = [(record.timestamp, record.close, record.volume) for record in records]
    result = monitor_records("BHARTIARTL", records, provider="test", stale_after_days=0)
    checks = {finding["check_name"] for finding in result["findings"]}
    assert {"missing_sessions", "price_jump", "volume_change", "stale_data"} <= checks
    assert before == [(record.timestamp, record.close, record.volume) for record in records]


def test_source_provenance_is_required_and_no_files_are_written(tmp_path: Path):
    result = monitor_records("BHARTIARTL", [bar(1)], provider="test")
    assert result["provider"] == "test"
    assert not list(tmp_path.iterdir())
