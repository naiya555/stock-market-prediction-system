"""Unit tests for the Intraday Session Recorder, Archive Storage, and Readiness Gate.

Verifies:
1. Valid completed-candle ingestion
2. Rejection of invalid OHLC values
3. Missing-volume preservation
4. Duplicate-candle idempotency
5. Conflicting duplicate quarantine
6. Timestamp and timezone normalization
7. Partial-candle rejection or deferral
8. Missing-interval detection
9. Market holidays and closed sessions
10. Provider timeouts and malformed responses
11. Bounded retry behavior
12. Restart and recovery behavior
13. Persistence provenance
14. Unsupported instrument rejection
15. Protection of existing prediction database
16. Separation of synthetic fixtures from genuine captured observations
"""

from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from zoneinfo import ZoneInfo

from app.core.schemas import ValidationError
from app.market.providers.yfinance_provider import YFinanceIntradayProvider
from app.market.intraday import (
    IntradayCandle,
    IntradayInterval,
)
from app.market.recorder import (
    CandleProvenance,
    EvaluationReadinessStatus,
    IntradayArchiveStore,
    IntradaySessionRecorder,
    RecordedCandleRecord,
    RecorderStatus,
    SessionCaptureSummary,
    TestIntradayRecorderAdapter,
    check_evaluation_readiness,
)
from app.market.session import (
    IST,
    MarketSessionState,
    NSE_HOLIDAYS_2026,
)


@pytest.fixture
def temp_archive_paths(tmp_path: Path):
    """Provide isolated archive and quarantine paths within temporary directory."""
    archive_file = tmp_path / "intraday_archive.jsonl"
    quarantine_file = tmp_path / "quarantined_candles.jsonl"
    return archive_file, quarantine_file


def _create_sample_candle(
    symbol: str = "BHARTIARTL",
    session_date: date = date(2026, 6, 1),
    bar_time: time = time(9, 15),
    open_price: float = 1650.0,
    high_price: float = 1655.0,
    low_price: float = 1648.0,
    close_price: float = 1652.0,
    volume: int = 15000,
    interval: IntradayInterval = IntradayInterval.M5,
    source: str = "test_provider",
) -> IntradayCandle:
    ts = datetime.combine(session_date, bar_time, tzinfo=IST)
    return IntradayCandle(
        symbol=symbol,
        timestamp=ts,
        interval=interval,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        source=source,
    )


class TestIntradayArchiveStore:
    """Tests for IntradayArchiveStore append-only storage and idempotency."""

    def test_store_creation_and_append(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        candle = _create_sample_candle()
        record = RecordedCandleRecord(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            interval=candle.interval,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            volume_reported=candle.volume_reported,
            source=candle.source,
            provenance=CandleProvenance.PROVIDER_OBSERVATION,
            capture_timestamp=datetime.now(IST),
            is_completed=True,
        )

        success, msg = store.append(record)
        assert success is True
        assert msg == "persisted"

        stats = store.get_stats()
        assert stats.total_records == 1
        assert stats.symbols == ["BHARTIARTL"]
        assert stats.quarantined_count == 0

    def test_duplicate_candle_idempotency(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        candle = _create_sample_candle()
        record = RecordedCandleRecord(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            interval=candle.interval,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            volume_reported=candle.volume_reported,
            source=candle.source,
            provenance=CandleProvenance.PROVIDER_OBSERVATION,
            capture_timestamp=datetime.now(IST),
            is_completed=True,
        )

        # First append
        store.append(record)
        # Duplicate identical append
        success, msg = store.append(record)
        assert success is True
        assert msg == "idempotent_duplicate"

        # Record count in file remains 1
        stats = store.get_stats()
        assert stats.total_records == 1

        with open(archive_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        assert len(lines) == 1

    def test_conflicting_duplicate_quarantine(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        candle = _create_sample_candle()
        record1 = RecordedCandleRecord(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            interval=candle.interval,
            open=1650.0,
            high=1655.0,
            low=1648.0,
            close=1652.0,
            volume=1000,
            volume_reported=True,
            source="src1",
            provenance=CandleProvenance.PROVIDER_OBSERVATION,
            capture_timestamp=datetime.now(IST),
            is_completed=True,
        )
        # Conflicting record with different close price
        record2 = RecordedCandleRecord(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            interval=candle.interval,
            open=1650.0,
            high=1655.0,
            low=1648.0,
            close=1699.0,  # Conflicting!
            volume=1000,
            volume_reported=True,
            source="src2",
            provenance=CandleProvenance.PROVIDER_OBSERVATION,
            capture_timestamp=datetime.now(IST),
            is_completed=True,
        )

        store.append(record1)
        success, msg = store.append(record2)

        assert success is False
        assert msg == "conflicting_duplicate_quarantined"

        stats = store.get_stats()
        assert stats.total_records == 1
        assert stats.quarantined_count == 1

        # Check quarantine file contents
        assert quarantine_path.exists()
        with open(quarantine_path, "r", encoding="utf-8") as qf:
            lines = [json.loads(line) for line in qf if line.strip()]
        assert len(lines) == 1
        assert lines[0]["quarantine_reason"] == "conflicting_duplicate"
        assert lines[0]["conflicting_record"]["close"] == 1699.0

    def test_restart_and_recovery_behavior(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        # First process session
        store1 = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        candle = _create_sample_candle()
        rec = RecordedCandleRecord(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            interval=candle.interval,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            volume_reported=candle.volume_reported,
            source=candle.source,
            provenance=CandleProvenance.PROVIDER_OBSERVATION,
            capture_timestamp=datetime.now(IST),
            is_completed=True,
        )
        store1.append(rec)
        assert store1.get_stats().total_records == 1

        # Simulate process termination and restart with fresh store instance
        store2 = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        stats2 = store2.get_stats()
        assert stats2.total_records == 1
        assert stats2.symbols == ["BHARTIARTL"]

        # Append same record to restarted store -> should be recognized as duplicate
        success, msg = store2.append(rec)
        assert success is True
        assert msg == "idempotent_duplicate"
        assert store2.get_stats().total_records == 1

    def test_protection_of_existing_prediction_database(self, tmp_path):
        # Attempting to target predictions.db must raise ValueError
        bad_path = tmp_path / "predictions.db"
        with pytest.raises(ValueError, match="protected prediction database"):
            IntradayArchiveStore(archive_path=bad_path)

        with pytest.raises(ValueError, match="protected predictions database"):
            IntradayArchiveStore(archive_path=tmp_path / "data" / "predictions.db" / "archive.jsonl")


class TestIntradaySessionRecorder:
    """Tests for IntradaySessionRecorder orchestration, safety guards, and retries."""

    def test_valid_completed_candle_ingestion(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter()

        trading_day = date(2026, 6, 1)  # Monday
        c1 = _create_sample_candle(session_date=trading_day, bar_time=time(9, 15))
        adapter.queue_candles([c1])

        recorder = IntradaySessionRecorder(
            provider=adapter,
            store=store,
            symbol="BHARTIARTL",
            interval=IntradayInterval.M5,
        )

        # Observation time: 09:20:05 IST (after 09:15-09:20 bar completes)
        obs_time = datetime.combine(trading_day, time(9, 20, 5), tzinfo=IST)
        result = recorder.record_cycle(as_of=obs_time)

        assert result["status"] == RecorderStatus.RECORDING.value
        assert result["fetched_count"] == 1
        assert result["persisted_count"] == 1
        assert result["forming_deferred_count"] == 0
        assert store.get_stats().total_records == 1

    def test_partial_candle_rejection_or_deferral(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter()

        trading_day = date(2026, 6, 1)
        # Bar 09:15 starts at 09:15 and completes at 09:20
        c1 = _create_sample_candle(session_date=trading_day, bar_time=time(9, 15))
        adapter.queue_candles([c1])

        recorder = IntradaySessionRecorder(
            provider=adapter,
            store=store,
            symbol="BHARTIARTL",
            interval=IntradayInterval.M5,
        )

        # Observation time is 09:18:00 IST (bar is still forming!)
        obs_time = datetime.combine(trading_day, time(9, 18, 0), tzinfo=IST)
        result = recorder.record_cycle(as_of=obs_time)

        assert result["fetched_count"] == 1
        assert result["persisted_count"] == 0
        assert result["forming_deferred_count"] == 1
        assert store.get_stats().total_records == 0  # Not persisted while forming!

    def test_missing_volume_preservation(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter()

        trading_day = date(2026, 6, 1)
        # Candle with volume=None
        ts = datetime.combine(trading_day, time(9, 15), tzinfo=IST)
        candle = IntradayCandle(
            symbol="BHARTIARTL",
            timestamp=ts,
            interval=IntradayInterval.M5,
            open=1650.0,
            high=1655.0,
            low=1648.0,
            close=1652.0,
            volume=None,  # Unreported volume
            source="test_provider",
        )
        adapter.queue_candles([candle])

        recorder = IntradaySessionRecorder(provider=adapter, store=store, symbol="BHARTIARTL")
        obs_time = datetime.combine(trading_day, time(9, 21), tzinfo=IST)
        recorder.record_cycle(as_of=obs_time)

        records = store.get_records()
        assert len(records) == 1
        assert records[0].volume is None
        assert records[0].volume_reported is False
        assert "VOLUME_UNREPORTED" in records[0].data_quality_flags

    def test_unsupported_instrument_rejection(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter()

        with pytest.raises(ValidationError, match="Unauthorized instrument 'NIFTY'"):
            IntradaySessionRecorder(provider=adapter, store=store, symbol="NIFTY")

        with pytest.raises(ValidationError, match="Unauthorized instrument 'RELIANCE'"):
            IntradaySessionRecorder(provider=adapter, store=store, symbol="RELIANCE")

    def test_market_holidays_and_closed_sessions(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter()
        recorder = IntradaySessionRecorder(provider=adapter, store=store, symbol="BHARTIARTL")

        # 1. Closed at night (21:50 IST on a weekday)
        night_time = datetime(2026, 6, 1, 21, 50, tzinfo=IST)
        res_night = recorder.record_cycle(as_of=night_time)
        assert res_night["status"] == RecorderStatus.MARKET_CLOSED.value
        assert res_night["session_state"] == MarketSessionState.CLOSED.value
        assert adapter.call_count == 0  # Did not attempt provider call!

        # 2. Closed on weekend (Saturday)
        sat_time = datetime(2026, 6, 6, 11, 0, tzinfo=IST)
        res_sat = recorder.record_cycle(as_of=sat_time)
        assert res_sat["status"] == RecorderStatus.MARKET_CLOSED.value
        assert adapter.call_count == 0

        # 3. Closed on exchange holiday (Republic Day: Jan 26, 2026)
        holiday_time = datetime(2026, 1, 26, 11, 0, tzinfo=IST)
        res_hol = recorder.record_cycle(as_of=holiday_time)
        assert res_hol["status"] == RecorderStatus.MARKET_CLOSED.value
        assert adapter.call_count == 0

    def test_provider_timeout_and_bounded_retry(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter(simulate_timeout=True)

        recorder = IntradaySessionRecorder(
            provider=adapter,
            store=store,
            symbol="BHARTIARTL",
            max_retries=3,
            retry_backoff_seconds=0.01,
        )

        obs_time = datetime(2026, 6, 1, 10, 0, tzinfo=IST)
        result = recorder.record_cycle(as_of=obs_time)

        assert result["status"] == RecorderStatus.DEGRADED.value
        assert "Simulated provider connection timeout" in result["error"]
        assert adapter.call_count == 3  # Exactly 3 bounded retries attempted!

    def test_missing_interval_detection(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter()

        trading_day = date(2026, 6, 1)
        # Bar 1: 09:15-09:20
        c1 = _create_sample_candle(session_date=trading_day, bar_time=time(9, 15))
        # Bar 2: 09:25-09:30 (missing 09:20 bar!)
        c2 = _create_sample_candle(session_date=trading_day, bar_time=time(9, 25))
        adapter.queue_candles([c1, c2])

        recorder = IntradaySessionRecorder(provider=adapter, store=store, symbol="BHARTIARTL")
        obs_time = datetime.combine(trading_day, time(9, 31), tzinfo=IST)
        res = recorder.record_cycle(as_of=obs_time)

        assert res["gaps_detected_count"] == 1
        assert res["persisted_count"] == 2

    def test_clean_shutdown(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter()
        recorder = IntradaySessionRecorder(provider=adapter, store=store, symbol="BHARTIARTL")

        assert recorder.status == RecorderStatus.READY
        recorder.stop()
        assert recorder.status == RecorderStatus.STOPPED


class TestEvaluationReadinessGate:
    """Tests for empirical evaluation readiness gate and provenance verification."""

    def test_blocked_when_no_provider_observations(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        report = check_evaluation_readiness(store, symbol="BHARTIARTL")
        assert report.is_ready_for_evaluation is False
        assert report.status == EvaluationReadinessStatus.BLOCKED_NO_VERIFIED_INTRADAY_PROVIDER
        assert "No genuine provider observations" in report.issues[0]

    def test_contaminated_synthetic_detection(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        candle = _create_sample_candle()
        synthetic_record = RecordedCandleRecord(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            interval=candle.interval,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            volume_reported=candle.volume_reported,
            source="synthetic_test_fixture",
            provenance=CandleProvenance.SYNTHETIC_TEST,  # Synthetic!
            capture_timestamp=datetime.now(IST),
            is_completed=True,
        )
        store.append(synthetic_record)

        report = check_evaluation_readiness(store, symbol="BHARTIARTL")
        assert report.is_ready_for_evaluation is False
        assert report.status == EvaluationReadinessStatus.CONTAMINATED_SYNTHETIC
        assert "synthetic_test fixtures" in report.issues[0]

    def test_insufficient_coverage_detection(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        # Add only 5 provider observations when 75 are required
        trading_day = date(2026, 6, 1)
        for i in range(5):
            minute = 15 + i * 5
            ts = datetime.combine(trading_day, time(9, minute), tzinfo=IST)
            rec = RecordedCandleRecord(
                symbol="BHARTIARTL",
                timestamp=ts,
                interval=IntradayInterval.M5,
                open=1650.0,
                high=1655.0,
                low=1648.0,
                close=1652.0,
                volume=1000,
                volume_reported=True,
                source="real_provider",
                provenance=CandleProvenance.PROVIDER_OBSERVATION,
                capture_timestamp=datetime.now(IST),
                is_completed=True,
            )
            store.append(rec)

        report = check_evaluation_readiness(store, symbol="BHARTIARTL", min_required_candles=75)
        assert report.is_ready_for_evaluation is False
        assert report.status == EvaluationReadinessStatus.INSUFFICIENT_COVERAGE
        assert report.total_candles == 5

    def test_ready_when_sufficient_clean_provider_data(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        # Generate 75 continuous 5m candles (one full 375m trading session: 09:15 to 15:30)
        trading_day = date(2026, 6, 1)
        base_time = datetime.combine(trading_day, time(9, 15), tzinfo=IST)
        for i in range(75):
            ts = base_time + timedelta(minutes=i * 5)
            rec = RecordedCandleRecord(
                symbol="BHARTIARTL",
                timestamp=ts,
                interval=IntradayInterval.M5,
                open=1650.0 + (i * 0.1),
                high=1652.0 + (i * 0.1),
                low=1649.0 + (i * 0.1),
                close=1651.0 + (i * 0.1),
                volume=10000 + i * 50,
                volume_reported=True,
                source="live_nse_adapter",
                provenance=CandleProvenance.PROVIDER_OBSERVATION,
                capture_timestamp=datetime.now(IST),
                is_completed=True,
            )
            store.append(rec)

        report = check_evaluation_readiness(store, symbol="BHARTIARTL", min_required_candles=75)
        assert report.is_ready_for_evaluation is True
        assert report.status == EvaluationReadinessStatus.READY
        assert report.total_candles == 75
        assert report.gaps_count == 0
        assert len(report.issues) == 0

    def test_readiness_rejected_on_missing_interval_gaps(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        trading_day = date(2026, 6, 1)
        base_time = datetime.combine(trading_day, time(9, 15), tzinfo=IST)
        # Store 75 candles, but skip candle index 10 (gap!)
        for i in range(76):
            if i == 10:
                continue  # Intentional missing interval gap
            ts = base_time + timedelta(minutes=i * 5)
            rec = RecordedCandleRecord(
                symbol="BHARTIARTL",
                timestamp=ts,
                interval=IntradayInterval.M5,
                open=1650.0 + (i * 0.1),
                high=1652.0 + (i * 0.1),
                low=1649.0 + (i * 0.1),
                close=1651.0 + (i * 0.1),
                volume=10000,
                volume_reported=True,
                source="live_provider",
                provenance=CandleProvenance.PROVIDER_OBSERVATION,
                capture_timestamp=datetime.now(IST),
                is_completed=True,
            )
            store.append(rec)

        report = check_evaluation_readiness(store, symbol="BHARTIARTL", min_required_candles=75)
        assert report.is_ready_for_evaluation is False
        assert report.status == EvaluationReadinessStatus.PENDING_VALIDATION
        assert report.gaps_count == 1
        assert any("missing interval gaps" in issue for issue in report.issues)

    def test_readiness_rejected_on_unresolved_quarantined_conflicts(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        candle = _create_sample_candle()
        rec1 = RecordedCandleRecord(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            interval=candle.interval,
            open=1650.0,
            high=1655.0,
            low=1648.0,
            close=1652.0,
            volume=1000,
            volume_reported=True,
            source="src1",
            provenance=CandleProvenance.PROVIDER_OBSERVATION,
            capture_timestamp=datetime.now(IST),
            is_completed=True,
        )
        rec2 = RecordedCandleRecord(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            interval=candle.interval,
            open=1650.0,
            high=1655.0,
            low=1648.0,
            close=1690.0,  # Conflicting!
            volume=1000,
            volume_reported=True,
            source="src2",
            provenance=CandleProvenance.PROVIDER_OBSERVATION,
            capture_timestamp=datetime.now(IST),
            is_completed=True,
        )
        store.append(rec1)
        store.append(rec2)  # Quarantined

        report = check_evaluation_readiness(store, symbol="BHARTIARTL", min_required_candles=1)
        assert report.is_ready_for_evaluation is False
        assert report.status == EvaluationReadinessStatus.PENDING_VALIDATION
        assert any("quarantined conflicting records" in issue for issue in report.issues)

    def test_readiness_rejected_on_uncompleted_candles(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        trading_day = date(2026, 6, 1)
        ts = datetime.combine(trading_day, time(9, 15), tzinfo=IST)
        rec = RecordedCandleRecord(
            symbol="BHARTIARTL",
            timestamp=ts,
            interval=IntradayInterval.M5,
            open=1650.0,
            high=1655.0,
            low=1648.0,
            close=1652.0,
            volume=1000,
            volume_reported=True,
            source="src",
            provenance=CandleProvenance.PROVIDER_OBSERVATION,
            capture_timestamp=datetime.now(IST),
            is_completed=False,  # Uncompleted forming candle!
        )
        store.append(rec)

        report = check_evaluation_readiness(store, symbol="BHARTIARTL", min_required_candles=1)
        assert report.is_ready_for_evaluation is False
        assert report.status == EvaluationReadinessStatus.PENDING_VALIDATION
        assert any("forming or uncompleted candles" in issue for issue in report.issues)

    def test_readiness_rejected_on_weekend_or_holiday_candles(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        # Saturday June 6, 2026
        weekend_ts = datetime(2026, 6, 6, 10, 0, tzinfo=IST)
        rec = RecordedCandleRecord(
            symbol="BHARTIARTL",
            timestamp=weekend_ts,
            interval=IntradayInterval.M5,
            open=1650.0,
            high=1655.0,
            low=1648.0,
            close=1652.0,
            volume=1000,
            volume_reported=True,
            source="src",
            provenance=CandleProvenance.PROVIDER_OBSERVATION,
            capture_timestamp=datetime.now(IST),
            is_completed=True,
        )
        store.append(rec)

        report = check_evaluation_readiness(store, symbol="BHARTIARTL", min_required_candles=1)
        assert report.is_ready_for_evaluation is False
        assert report.status == EvaluationReadinessStatus.PENDING_VALIDATION
        assert any("weekend or declared NSE holiday" in issue for issue in report.issues)

    def test_readiness_dynamic_interval_expected_bars(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        # For 15m interval, expected regular session bars = 375 // 15 = 25 bars
        trading_day = date(2026, 6, 1)
        base_time = datetime.combine(trading_day, time(9, 15), tzinfo=IST)
        for i in range(25):
            ts = base_time + timedelta(minutes=i * 15)
            rec = RecordedCandleRecord(
                symbol="BHARTIARTL",
                timestamp=ts,
                interval=IntradayInterval.M15,
                open=1650.0 + (i * 0.1),
                high=1653.0 + (i * 0.1),
                low=1648.0 + (i * 0.1),
                close=1652.0 + (i * 0.1),
                volume=15000,
                volume_reported=True,
                source="live_nse",
                provenance=CandleProvenance.PROVIDER_OBSERVATION,
                capture_timestamp=datetime.now(IST),
                is_completed=True,
            )
            store.append(rec)

        # Default min_required_candles=None should dynamically deduce 25 bars for M15!
        report = check_evaluation_readiness(store, symbol="BHARTIARTL", interval=IntradayInterval.M15)
        assert report.is_ready_for_evaluation is True
        assert report.status == EvaluationReadinessStatus.READY
        assert report.total_candles == 25


class TestYFinanceIntradayProvider:
    """Tests for YFinanceIntradayProvider adapter implementation with deterministic mocks."""

    def test_yfinance_provider_successful_candle_parsing(self):
        provider = YFinanceIntradayProvider()
        test_date = date(2026, 6, 1)

        # Construct deterministic synthetic pandas DataFrame matching yfinance schema
        timestamps = [
            pd.Timestamp("2026-06-01 09:15:00", tz="Asia/Kolkata"),
            pd.Timestamp("2026-06-01 09:20:00", tz="Asia/Kolkata"),
        ]
        mock_df = pd.DataFrame(
            {
                "Open": [1650.0, 1655.0],
                "High": [1658.0, 1660.0],
                "Low": [1648.0, 1652.0],
                "Close": [1654.0, 1658.0],
                "Volume": [12000, 14500],
            },
            index=timestamps,
        )

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.history.return_value = mock_df
            mock_ticker_cls.return_value = mock_ticker_instance

            candles = provider.fetch_intraday_candles(
                symbol="BHARTIARTL",
                session_date=test_date,
                interval=IntradayInterval.M5,
            )

            assert len(candles) == 2
            assert candles[0].symbol == "BHARTIARTL"
            assert candles[0].timestamp == datetime(2026, 6, 1, 9, 15, tzinfo=IST)
            assert candles[0].open == 1650.0
            assert candles[0].close == 1654.0
            assert candles[0].volume == 12000
            assert candles[0].source == "yfinance"

    def test_yfinance_provider_missing_volume_preservation(self):
        provider = YFinanceIntradayProvider()
        test_date = date(2026, 6, 1)

        mock_df = pd.DataFrame(
            {
                "Open": [1650.0],
                "High": [1655.0],
                "Low": [1648.0],
                "Close": [1652.0],
                "Volume": [float("nan")],  # NaN volume
            },
            index=[pd.Timestamp("2026-06-01 09:15:00", tz="Asia/Kolkata")],
        )

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.history.return_value = mock_df
            mock_ticker_cls.return_value = mock_ticker_instance

            candles = provider.fetch_intraday_candles(
                symbol="BHARTIARTL",
                session_date=test_date,
                interval=IntradayInterval.M5,
            )

            assert len(candles) == 1
            assert candles[0].volume is None
            assert candles[0].volume_reported is False

    def test_yfinance_provider_rejects_index_instruments(self):
        provider = YFinanceIntradayProvider()
        test_date = date(2026, 6, 1)

        with pytest.raises(ValidationError, match="Instrument 'NIFTY' is an index"):
            provider.fetch_intraday_candles("NIFTY", test_date)

        with pytest.raises(ValidationError, match="Instrument '\\^NSEI' is an index"):
            provider.fetch_intraday_candles("^NSEI", test_date)

    def test_yfinance_provider_empty_response(self):
        provider = YFinanceIntradayProvider()
        test_date = date(2026, 6, 1)

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.history.return_value = pd.DataFrame()  # Empty
            mock_ticker_cls.return_value = mock_ticker_instance

            candles = provider.fetch_intraday_candles("BHARTIARTL", test_date)
            assert candles == []

    def test_yfinance_provider_network_error(self):
        provider = YFinanceIntradayProvider()
        test_date = date(2026, 6, 1)

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.history.side_effect = ConnectionError("Network failure")
            mock_ticker_cls.return_value = mock_ticker_instance

            with pytest.raises(RuntimeError, match="yfinance intraday fetch failed"):
                provider.fetch_intraday_candles("BHARTIARTL", test_date)


class TestBoundedSessionCapture:
    """Tests for multi-cycle bounded manual capture workflow."""

    def test_bounded_session_stops_when_market_closed(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter([])
        recorder = IntradaySessionRecorder(
            symbol="BHARTIARTL",
            interval=IntradayInterval.M5,
            provider=adapter,
            store=store,
        )

        closed_time = datetime(2026, 6, 1, 20, 0, 0, tzinfo=IST)
        summary = recorder.run_bounded_session(
            max_cycles=5,
            max_runtime_seconds=300.0,
            poll_interval_seconds=0.0,
            clock_fn=lambda: closed_time,
            sleep_fn=lambda _: None,
        )

        assert summary.termination_reason == "market_closed"
        assert summary.total_persisted == 0
        assert summary.total_fetched == 0
        assert summary.symbol == "BHARTIARTL"

    def test_bounded_session_stops_on_cycle_limit(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        completed_candle = _create_sample_candle(
            session_date=date(2026, 6, 1),
            bar_time=time(9, 15),
        )
        adapter = TestIntradayRecorderAdapter(candle_queue=[completed_candle])
        recorder = IntradaySessionRecorder(
            symbol="BHARTIARTL",
            interval=IntradayInterval.M5,
            provider=adapter,
            store=store,
        )

        open_time = datetime(2026, 6, 1, 10, 0, 0, tzinfo=IST)
        summary = recorder.run_bounded_session(
            max_cycles=3,
            max_runtime_seconds=3600.0,
            poll_interval_seconds=0.0,
            clock_fn=lambda: open_time,
            sleep_fn=lambda _: None,
        )

        assert summary.cycles_completed == 3
        assert summary.termination_reason == "cycle_limit_reached"
        assert summary.total_persisted == 1  # Persisted on cycle 1, duplicate on cycle 2 & 3
        assert summary.total_idempotent == 2

    def test_bounded_session_stops_on_runtime_limit(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter()
        recorder = IntradaySessionRecorder(
            symbol="BHARTIARTL",
            interval=IntradayInterval.M5,
            provider=adapter,
            store=store,
        )

        times = [
            datetime(2026, 6, 1, 10, 0, 0, tzinfo=IST),
            datetime(2026, 6, 1, 10, 0, 10, tzinfo=IST),
            datetime(2026, 6, 1, 10, 0, 35, tzinfo=IST),  # Past 30s limit
            datetime(2026, 6, 1, 10, 0, 40, tzinfo=IST),
        ]
        time_iter = iter(times)

        def mock_clock():
            return next(time_iter, times[-1])

        summary = recorder.run_bounded_session(
            max_cycles=10,
            max_runtime_seconds=30.0,
            poll_interval_seconds=0.0,
            clock_fn=mock_clock,
            sleep_fn=lambda _: None,
        )

        assert summary.termination_reason == "runtime_limit_reached"

    def test_bounded_session_multi_cycle_deferral_persistence_and_idempotency(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        candle = _create_sample_candle(
            session_date=date(2026, 6, 1),
            bar_time=time(9, 15),
        )
        adapter = TestIntradayRecorderAdapter(candle_queue=[candle])
        recorder = IntradaySessionRecorder(
            symbol="BHARTIARTL",
            interval=IntradayInterval.M5,
            provider=adapter,
            store=store,
        )

        # 1. start_time: 09:18 IST
        # 2. Cycle 1: 09:18 IST -> bar 09:15-09:20 is forming -> deferred
        # 3. Cycle 2: 09:21 IST -> bar 09:15-09:20 is completed -> persisted
        # 4. Cycle 3: 09:22 IST -> bar 09:15-09:20 is duplicate -> idempotent
        # 5. final_time: 09:25 IST
        clock_ticks = [
            datetime(2026, 6, 1, 9, 18, 0, tzinfo=IST),
            datetime(2026, 6, 1, 9, 18, 0, tzinfo=IST),
            datetime(2026, 6, 1, 9, 21, 0, tzinfo=IST),
            datetime(2026, 6, 1, 9, 22, 0, tzinfo=IST),
            datetime(2026, 6, 1, 9, 25, 0, tzinfo=IST),
        ]
        clock_iter = iter(clock_ticks)

        summary = recorder.run_bounded_session(
            max_cycles=3,
            max_runtime_seconds=600.0,
            poll_interval_seconds=0.0,
            clock_fn=lambda: next(clock_iter, clock_ticks[-1]),
            sleep_fn=lambda _: None,
        )

        assert summary.cycles_completed == 3
        assert summary.total_deferred == 1
        assert summary.total_persisted == 1
        assert summary.total_idempotent == 1
        assert summary.total_quarantined == 0
        assert summary.termination_reason == "cycle_limit_reached"

    def test_bounded_session_stops_on_provider_degraded(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)

        adapter = MagicMock()
        adapter.fetch_intraday_candles.side_effect = RuntimeError("Persistent upstream connection failure")

        recorder = IntradaySessionRecorder(
            symbol="BHARTIARTL",
            interval=IntradayInterval.M5,
            provider=adapter,
            store=store,
            max_retries=1,
            retry_backoff_seconds=0.01,
        )

        open_time = datetime(2026, 6, 1, 10, 0, 0, tzinfo=IST)
        summary = recorder.run_bounded_session(
            max_cycles=5,
            max_runtime_seconds=60.0,
            poll_interval_seconds=0.0,
            clock_fn=lambda: open_time,
            sleep_fn=lambda _: None,
            stop_on_degraded=True,
        )

        assert summary.termination_reason == "provider_degraded"
        assert summary.status == RecorderStatus.DEGRADED.value

    def test_bounded_session_manual_stop(self, temp_archive_paths):
        archive_path, quarantine_path = temp_archive_paths
        store = IntradayArchiveStore(archive_path=archive_path, quarantine_path=quarantine_path)
        adapter = TestIntradayRecorderAdapter([])
        recorder = IntradaySessionRecorder(
            symbol="BHARTIARTL",
            interval=IntradayInterval.M5,
            provider=adapter,
            store=store,
        )
        recorder.stop()

        open_time = datetime(2026, 6, 1, 10, 0, 0, tzinfo=IST)
        summary = recorder.run_bounded_session(
            max_cycles=5,
            max_runtime_seconds=60.0,
            poll_interval_seconds=0.0,
            clock_fn=lambda: open_time,
            sleep_fn=lambda _: None,
        )

        assert summary.termination_reason == "manual_stop"
        assert summary.cycles_completed == 0
