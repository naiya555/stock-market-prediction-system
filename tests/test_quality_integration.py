from datetime import datetime

from app.core.schemas import MarketOHLCV
from app.market.quality.integration import run_advisory_monitor


def _bar(day: int, close: float = 100.0) -> MarketOHLCV:
    return MarketOHLCV(
        symbol="BHARTIARTL",
        timestamp=datetime(2026, 9, day, 10, 0),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=100,
        source="test",
    )


def test_advisory_status_is_instrument_specific_and_visible(caplog):
    with caplog.at_level("INFO"):
        result = run_advisory_monitor("BHARTIARTL", [_bar(1), _bar(2)], provider="test")
    assert result["instrument"] == "BHARTIARTL"
    assert result["overall_status"] in {"PASS", "WARNING", "UNVERIFIED"}
    assert "report_path" in result
    assert "Data quality status for BHARTIARTL" in caplog.text


def test_monitoring_error_is_not_pass(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("monitor unavailable")

    monkeypatch.setattr("app.market.quality.integration.monitor_records", fail)
    result = run_advisory_monitor("TCS", [], provider="test")
    assert result["overall_status"] == "FAILED"
    assert result["overall_status"] != "PASS"
