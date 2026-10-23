"""Deterministic Unit Tests for Day 69 Intraday Engine & Data Contracts.

Validates:
1. Valid candle acceptance and property calculations.
2. Invalid OHLC rejection (non-positive prices, NaN, geometry bounds violations).
3. Duplicate and out-of-order timestamp handling (identical collapsed, conflicting rejected, chronological sorting).
4. Missing candle and session gap detection without candle fabrication.
5. Optional and unavailable volume handling (explicit None, volume_reported flag, non-negative checks).
6. Market-session and timezone normalization (IST conversion, regular hours 09:15-15:30 filtering).
7. Unsupported instrument rejection (BHARTIARTL supported; TCS, RELIANCE, indices blocked).
8. Provider independence via synthetic test fixtures and graceful failure.
9. Forecast safety guard (verifying that daily models are never run on intraday candles and zero unvalidated predictions are emitted).
"""

from datetime import date, datetime, timedelta
import math
import pytest
from zoneinfo import ZoneInfo

from app.core.schemas import ValidationError
from app.market.intraday import (
    BaseIntradayDataProvider,
    IntradayCandle,
    IntradayCleaningResult,
    IntradayEngine,
    IntradayInterval,
    IntradayQualitySummary,
    SyntheticTestIntradayProvider,
    clean_intraday_candles,
)
from app.market.session import IST


@pytest.fixture
def sample_valid_intraday_candles():
    """Series of clean, sequential 5-minute candles on a normal NSE trading session."""
    session_date = date(2026, 10, 14)  # Wednesday
    base_time = datetime(2026, 10, 14, 9, 15, tzinfo=IST)
    candles = []
    prices = [
        (1850.0, 1855.0, 1848.0, 1852.0, 50000),
        (1852.0, 1858.0, 1851.0, 1856.0, 42000),
        (1856.0, 1860.0, 1854.0, 1858.0, 61000),
        (1858.0, 1862.0, 1857.0, 1861.0, 39000),
    ]
    for i, (op, hi, lo, cl, vol) in enumerate(prices):
        ts = base_time + timedelta(minutes=5 * i)
        candles.append(
            IntradayCandle(
                symbol="BHARTIARTL",
                timestamp=ts,
                interval=IntradayInterval.M5,
                open=op,
                high=hi,
                low=lo,
                close=cl,
                volume=vol,
                source="synthetic_test",
            )
        )
    return candles


class TestIntradayCandleContract:
    """Tests for the canonical IntradayCandle data contract."""

    def test_valid_candle_creation(self):
        """Verify clean initialization, normalization to IST, and properties."""
        ts = datetime(2026, 10, 14, 9, 15)  # naive datetime
        candle = IntradayCandle(
            symbol="bhartiartl ",
            timestamp=ts,
            interval=IntradayInterval.M5,
            open=1850.0,
            high=1860.0,
            low=1845.0,
            close=1855.0,
            volume=25000,
            source="test_source",
        )
        assert candle.symbol == "BHARTIARTL"
        assert candle.timestamp.tzinfo == IST
        assert candle.interval == IntradayInterval.M5
        assert candle.volume_reported is True
        assert candle.is_regular_hours is True
        assert candle.bar_end_timestamp == datetime(2026, 10, 14, 9, 20, tzinfo=IST)

        d = candle.to_dict()
        assert d["symbol"] == "BHARTIARTL"
        assert d["interval"] == "5m"
        assert d["is_regular_hours"] is True

    def test_optional_volume_without_zero_fabrication(self):
        """Verify that volume=None is preserved without silently converting to 0."""
        ts = datetime(2026, 10, 14, 9, 15, tzinfo=IST)
        candle = IntradayCandle(
            symbol="BHARTIARTL",
            timestamp=ts,
            interval=IntradayInterval.M5,
            open=1850.0,
            high=1860.0,
            low=1845.0,
            close=1855.0,
            volume=None,
            source="test_source",
        )
        assert candle.volume is None
        assert candle.volume_reported is False

        # Genuine 0 volume
        candle_zero = IntradayCandle(
            symbol="BHARTIARTL",
            timestamp=ts,
            interval=IntradayInterval.M5,
            open=1850.0,
            high=1860.0,
            low=1845.0,
            close=1855.0,
            volume=0,
            source="test_source",
        )
        assert candle_zero.volume == 0
        assert candle_zero.volume_reported is True

    @pytest.mark.parametrize(
        "op,hi,lo,cl,err_match",
        [
            (-1850.0, 1860.0, 1845.0, 1855.0, "open must be strictly positive"),
            (1850.0, -1860.0, 1845.0, 1855.0, "high must be strictly positive"),
            (1850.0, 1860.0, 0.0, 1855.0, "low must be strictly positive"),
            (1850.0, 1860.0, 1845.0, -10.0, "close must be strictly positive"),
            (1850.0, 1840.0, 1845.0, 1855.0, "high .* cannot be less than low"),
            (1850.0, 1852.0, 1845.0, 1855.0, "high .* cannot be lower than open .* or close"),
            (1850.0, 1860.0, 1852.0, 1850.0, "low .* cannot be greater than open .* or close"),
            (float("nan"), 1860.0, 1845.0, 1855.0, "non-NaN numeric"),
        ],
    )
    def test_invalid_ohlc_rejection(self, op, hi, lo, cl, err_match):
        """Verify strict rejection of invalid or physically impossible OHLC boundaries."""
        ts = datetime(2026, 10, 14, 9, 15, tzinfo=IST)
        with pytest.raises(ValidationError, match=err_match):
            IntradayCandle(
                symbol="BHARTIARTL",
                timestamp=ts,
                interval=IntradayInterval.M5,
                open=op,
                high=hi,
                low=lo,
                close=cl,
                source="test",
            )

    def test_invalid_volume_and_metadata_rejection(self):
        """Verify negative volume or empty symbol/source rejection."""
        ts = datetime(2026, 10, 14, 9, 15, tzinfo=IST)
        with pytest.raises(ValidationError, match="volume cannot be negative"):
            IntradayCandle(
                symbol="BHARTIARTL",
                timestamp=ts,
                interval=IntradayInterval.M5,
                open=1850.0,
                high=1860.0,
                low=1845.0,
                close=1855.0,
                volume=-500,
                source="test",
            )

        with pytest.raises(ValidationError, match="symbol cannot be empty"):
            IntradayCandle(
                symbol="",
                timestamp=ts,
                interval=IntradayInterval.M5,
                open=1850.0,
                high=1860.0,
                low=1845.0,
                close=1855.0,
                source="test",
            )

        with pytest.raises(ValidationError, match="source cannot be empty"):
            IntradayCandle(
                symbol="BHARTIARTL",
                timestamp=ts,
                interval=IntradayInterval.M5,
                open=1850.0,
                high=1860.0,
                low=1845.0,
                close=1855.0,
                source="   ",
            )


class TestIntradayCleaningAndQualityAudit:
    """Tests for clean_intraday_candles cleaning and audit engine."""

    def test_clean_series_passes_unmodified(self, sample_valid_intraday_candles):
        """Verify that already-clean series passes with 0 rejections."""
        res = clean_intraday_candles(sample_valid_intraday_candles, expected_interval=IntradayInterval.M5)
        assert len(res.candles) == 4
        assert res.summary.input_count == 4
        assert res.summary.output_count == 4
        assert res.summary.rejected_count == 0
        assert res.summary.missing_candle_gaps_count == 0

    def test_identical_duplicate_collapsing(self, sample_valid_intraday_candles):
        """Verify identical duplicate candles are collapsed into one without data loss."""
        duplicated = [
            sample_valid_intraday_candles[0],
            sample_valid_intraday_candles[0],  # Duplicate
            sample_valid_intraday_candles[1],
        ]
        res = clean_intraday_candles(duplicated)
        assert len(res.candles) == 2
        assert res.summary.identical_duplicates_count == 1
        assert res.summary.output_count == 2

    def test_conflicting_duplicate_rejection(self, sample_valid_intraday_candles):
        """Verify conflicting candles on same timestamp are quarantined/rejected."""
        bar1 = sample_valid_intraday_candles[0]
        # Conflicting price on identical timestamp
        bar1_conflict = IntradayCandle(
            symbol=bar1.symbol,
            timestamp=bar1.timestamp,
            interval=bar1.interval,
            open=1870.0,
            high=1880.0,
            low=1865.0,
            close=1875.0,
            volume=99999,
            source="other_source",
        )
        res = clean_intraday_candles([bar1, bar1_conflict, sample_valid_intraday_candles[1]])
        # Conflicting bars on 09:15 rejected; only 09:20 bar remains
        assert len(res.candles) == 1
        assert res.candles[0].timestamp == sample_valid_intraday_candles[1].timestamp
        assert res.summary.conflicting_duplicates_count == 2

    def test_chronological_sorting_and_out_of_order_handling(self, sample_valid_intraday_candles):
        """Verify out-of-order candles are sorted strictly chronologically."""
        shuffled = [
            sample_valid_intraday_candles[2],
            sample_valid_intraday_candles[0],
            sample_valid_intraday_candles[3],
            sample_valid_intraday_candles[1],
        ]
        res = clean_intraday_candles(shuffled)
        assert len(res.candles) == 4
        for i in range(len(res.candles) - 1):
            assert res.candles[i].timestamp < res.candles[i + 1].timestamp

    def test_missing_candle_gap_detection_without_fabrication(self):
        """Verify that missing intervals during continuous session are flagged as gaps without fabricating fake bars."""
        ts1 = datetime(2026, 10, 14, 9, 15, tzinfo=IST)
        # ts2 skips 09:20 and 09:25, jumps directly to 09:30
        ts2 = datetime(2026, 10, 14, 9, 30, tzinfo=IST)

        candle1 = IntradayCandle("BHARTIARTL", ts1, IntradayInterval.M5, 1850, 1855, 1845, 1852, 1000, True, "test")
        candle2 = IntradayCandle("BHARTIARTL", ts2, IntradayInterval.M5, 1853, 1858, 1850, 1855, 1200, True, "test")

        res = clean_intraday_candles([candle1, candle2])
        assert len(res.candles) == 2  # No fabricated bars added!
        assert res.summary.missing_candle_gaps_count == 1
        gap_start, gap_end = res.summary.gap_intervals[0]
        assert "09:20:00" in gap_start
        assert "09:30:00" in gap_end

    def test_out_of_session_filtering(self):
        """Verify pre-open and post-close bars are quarantined when allow_out_of_session=False."""
        ts_pre = datetime(2026, 10, 14, 9, 5, tzinfo=IST)  # Pre-open
        ts_reg = datetime(2026, 10, 14, 10, 0, tzinfo=IST)  # Regular
        ts_post = datetime(2026, 10, 14, 15, 45, tzinfo=IST)  # Post-close

        c_pre = IntradayCandle("BHARTIARTL", ts_pre, IntradayInterval.M5, 1850, 1855, 1845, 1850, 100, True, "test")
        c_reg = IntradayCandle("BHARTIARTL", ts_reg, IntradayInterval.M5, 1850, 1855, 1845, 1850, 100, True, "test")
        c_post = IntradayCandle("BHARTIARTL", ts_post, IntradayInterval.M5, 1850, 1855, 1845, 1850, 100, True, "test")

        res_filtered = clean_intraday_candles([c_pre, c_reg, c_post], allow_out_of_session=False)
        assert len(res_filtered.candles) == 1
        assert res_filtered.candles[0].timestamp == ts_reg
        assert res_filtered.summary.out_of_session_count == 2

        res_allowed = clean_intraday_candles([c_pre, c_reg, c_post], allow_out_of_session=True)
        assert len(res_allowed.candles) == 3


class TestIntradayEngineAndSafetyGuards:
    """Tests for IntradayEngine orchestration, instrument guards, and forecast safety."""

    def test_supported_instrument_query(self, sample_valid_intraday_candles):
        """Verify BHARTIARTL session query passes through synthetic provider and cleaner."""
        provider = SyntheticTestIntradayProvider()
        provider.register_candles(
            symbol="BHARTIARTL",
            session_date=date(2026, 10, 14),
            interval=IntradayInterval.M5,
            candles=sample_valid_intraday_candles,
        )

        engine = IntradayEngine(provider=provider)
        candles, summary = engine.get_session_candles(
            symbol="BHARTIARTL",
            session_date=date(2026, 10, 14),
            interval=IntradayInterval.M5,
        )
        assert len(candles) == 4
        assert summary.output_count == 4
        assert summary.rejected_count == 0

    @pytest.mark.parametrize("blocked_symbol", ["TCS", "RELIANCE", "NIFTY_TELECOMMUNICATIONS", "NIFTY_50"])
    def test_unsupported_instrument_rejection(self, blocked_symbol):
        """Verify strict fast-failure when attempting intraday processing on unauthorized instruments."""
        provider = SyntheticTestIntradayProvider()
        engine = IntradayEngine(provider=provider, supported_symbols={"BHARTIARTL"})

        with pytest.raises(ValidationError, match=f"Instrument '{blocked_symbol}' is not supported"):
            engine.get_session_candles(
                symbol=blocked_symbol,
                session_date=date(2026, 10, 14),
            )

    def test_forecast_safety_guard_blocks_premature_prediction(self):
        """Verify that intraday forecast readiness strictly returns MODEL_UNAVAILABLE.

        Guarantees that daily models (e.g. models/xgboost_direction.*) are never evaluated
        on intraday candle series without explicit training and validation.
        """
        provider = SyntheticTestIntradayProvider()
        engine = IntradayEngine(provider=provider)

        status_bharti = engine.verify_forecast_readiness("BHARTIARTL")
        assert status_bharti["is_ready"] is False
        assert status_bharti["status"] == "MODEL_UNAVAILABLE"
        assert "Daily models" in status_bharti["message"]

        status_unsupp = engine.verify_forecast_readiness("RELIANCE")
        assert status_unsupp["is_ready"] is False
        assert status_unsupp["status"] == "UNSUPPORTED_INSTRUMENT"
