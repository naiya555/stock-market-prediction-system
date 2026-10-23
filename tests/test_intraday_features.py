"""Deterministic Unit Tests for Day 70 Intraday Feature Extraction Layer.

Validates:
1. Exact mathematical fidelity against hand-calculated values (returns, VWAP, opening range).
2. Insufficient history edge cases (1 to 5 bars).
3. Missing and zero volume handling without fabrication.
4. Session boundary resets and zero cross-day leakage.
5. Opening range completion lifecycle and breakout classification (+1, -1, 0, None).
6. Missing session open handling (quarantined to UNAVAILABLE).
7. Strict Zero-Lookahead Invariant: appending or altering future candles has zero effect on past feature values.
8. Feature availability timestamps (available_at == bar_end_timestamp).
9. Chronological sorting invariance for out-of-order inputs.
10. IntradayEngine integration.
"""

from datetime import date, datetime, timedelta
import math
import pytest

from app.market.intraday import (
    IntradayCandle,
    IntradayEngine,
    IntradayFeatureRecord,
    IntradayInterval,
    OpeningRangeStatus,
    SyntheticTestIntradayProvider,
    compute_intraday_features,
)
from app.market.session import IST


@pytest.fixture
def hand_calculated_session_5m():
    """Deterministic 6-bar 5-minute session with hand-calculated expected values."""
    session_date = date(2026, 10, 14)
    base_time = datetime(2026, 10, 14, 9, 15, tzinfo=IST)

    # (open, high, low, close, volume)
    data = [
        # Bar 0: 09:15-09:20. Typ=(1860+1840+1850)/3 = 1850.0. CumPV=1,850,000, CumV=1000 -> VWAP=1850.0
        (1850.0, 1860.0, 1840.0, 1850.0, 1000),
        # Bar 1: 09:20-09:25. Typ=(1870+1850+1860)/3 = 1860.0. CumPV=1.85M + 3.72M = 5.57M, CumV=3000 -> VWAP=1856.6667
        (1850.0, 1870.0, 1850.0, 1860.0, 2000),
        # Bar 2: 09:25-09:30. Typ=(1865+1845+1855)/3 = 1855.0. CumPV=5.57M + 1.855M = 7.425M, CumV=4000 -> VWAP=1856.25
        # OR completes at 09:30! OR High=max(1860, 1870, 1865)=1870.0, OR Low=min(1840, 1850, 1845)=1840.0
        (1860.0, 1865.0, 1845.0, 1855.0, 1000),
        # Bar 3: 09:30-09:35. Close=1875 > OR High 1870 -> Breakout = +1. 3-bar return vs Bar 0 (1850) = 25/1850
        (1855.0, 1880.0, 1855.0, 1875.0, 1500),
        # Bar 4: 09:35-09:40. Close=1835 < OR Low 1840 -> Breakout = -1.
        (1875.0, 1875.0, 1830.0, 1835.0, 2500),
        # Bar 5: 09:40-09:45. Close=1850 inside [1840, 1870] -> Breakout = 0. 5 returns available -> Volatility computed!
        (1835.0, 1855.0, 1835.0, 1850.0, 1200),
    ]

    candles = []
    for i, (op, hi, lo, cl, vol) in enumerate(data):
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


class TestIntradayFeatureCalculations:
    """Tests verifying exact mathematical formulas and edge cases."""

    def test_hand_calculated_known_values(self, hand_calculated_session_5m):
        """Verify mathematical definitions against exact pre-calculated values."""
        features = compute_intraday_features(hand_calculated_session_5m, opening_range_minutes=15)
        assert len(features) == 6

        # --- Bar 0 (09:15 to 09:20) ---
        f0 = features[0]
        assert f0.candle_timestamp == datetime(2026, 10, 14, 9, 15, tzinfo=IST)
        assert f0.available_at == datetime(2026, 10, 14, 9, 20, tzinfo=IST)
        assert f0.return_1bar is None
        assert f0.rolling_return_3bar is None
        assert f0.rolling_volatility_5bar is None
        assert f0.session_vwap == 1850.0
        assert f0.opening_range_status == OpeningRangeStatus.IN_PROGRESS
        assert f0.opening_range_high is None
        assert f0.opening_range_low is None
        assert f0.opening_range_breakout is None

        # --- Bar 1 (09:20 to 09:25) ---
        f1 = features[1]
        assert f1.available_at == datetime(2026, 10, 14, 9, 25, tzinfo=IST)
        assert math.isclose(f1.return_1bar, (1860.0 - 1850.0) / 1850.0, abs_tol=1e-6)
        assert f1.rolling_return_3bar is None
        assert f1.session_vwap == 1856.6667
        assert f1.opening_range_status == OpeningRangeStatus.IN_PROGRESS

        # --- Bar 2 (09:25 to 09:30) - 15m Range Completes! ---
        f2 = features[2]
        assert f2.available_at == datetime(2026, 10, 14, 9, 30, tzinfo=IST)
        assert math.isclose(f2.return_1bar, (1855.0 - 1860.0) / 1860.0, abs_tol=1e-6)
        assert f2.rolling_return_3bar is None
        assert f2.session_vwap == 1856.25
        assert f2.opening_range_status == OpeningRangeStatus.COMPLETED
        assert f2.opening_range_high == 1870.0
        assert f2.opening_range_low == 1840.0
        assert f2.opening_range_breakout == 0  # close 1855 inside [1840, 1870]

        # --- Bar 3 (09:30 to 09:35) - Bullish Breakout ---
        f3 = features[3]
        assert f3.available_at == datetime(2026, 10, 14, 9, 35, tzinfo=IST)
        assert math.isclose(f3.rolling_return_3bar, (1875.0 - 1850.0) / 1850.0, abs_tol=1e-6)
        assert f3.opening_range_high == 1870.0
        assert f3.opening_range_low == 1840.0
        assert f3.opening_range_breakout == 1  # close 1875 > 1870.0!

        # --- Bar 4 (09:35 to 09:40) - Bearish Breakdown ---
        f4 = features[4]
        assert f4.opening_range_breakout == -1  # close 1835 < 1840.0!

        # --- Bar 5 (09:40 to 09:45) - 5-bar Volatility Available ---
        f5 = features[5]
        assert f5.opening_range_breakout == 0  # close 1850 inside [1840, 1870]
        assert f5.rolling_volatility_5bar is not None
        # Hand-calculated returns:
        r1 = (1860.0 - 1850.0) / 1850.0
        r2 = (1855.0 - 1860.0) / 1860.0
        r3 = (1875.0 - 1855.0) / 1855.0
        r4 = (1835.0 - 1875.0) / 1875.0
        r5 = (1850.0 - 1835.0) / 1835.0
        returns = [r1, r2, r3, r4, r5]
        mean_r = sum(returns) / 5.0
        sample_std = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / 4.0)
        assert math.isclose(f5.rolling_volatility_5bar, sample_std, abs_tol=1e-6)

    def test_missing_and_zero_volume_behavior(self, hand_calculated_session_5m):
        """Verify that missing volume invalidates VWAP without silent zero fabrication."""
        # Replace Bar 1 volume with None
        corrupted_candles = list(hand_calculated_session_5m)
        corrupted_candles[1] = IntradayCandle(
            symbol="BHARTIARTL",
            timestamp=corrupted_candles[1].timestamp,
            interval=corrupted_candles[1].interval,
            open=corrupted_candles[1].open,
            high=corrupted_candles[1].high,
            low=corrupted_candles[1].low,
            close=corrupted_candles[1].close,
            volume=None,  # Missing volume!
            source="test",
        )

        features = compute_intraday_features(corrupted_candles)
        # Bar 0 has known volume
        assert features[0].session_vwap == 1850.0
        # Bar 1 has missing volume -> VWAP is None!
        assert features[1].session_vwap is None
        # Bar 2 onwards: because prior volume was unknown, VWAP remains None (zero fabrication!)
        assert features[2].session_vwap is None

    def test_session_boundary_reset_and_zero_cross_day_leakage(self, hand_calculated_session_5m):
        """Verify that all metrics reset cleanly across session dates without overnight leakage."""
        day1 = list(hand_calculated_session_5m)
        # Create Day 2 bars (next trading day: 2026-10-15 Thursday)
        day2_base = datetime(2026, 10, 15, 9, 15, tzinfo=IST)
        day2 = [
            IntradayCandle("BHARTIARTL", day2_base, IntradayInterval.M5, 1860, 1865, 1855, 1862, 3000, True, "test"),
            IntradayCandle("BHARTIARTL", day2_base + timedelta(minutes=5), IntradayInterval.M5, 1862, 1870, 1860, 1868, 2000, True, "test"),
        ]

        multi_day_candles = day1 + day2
        features = compute_intraday_features(multi_day_candles)
        assert len(features) == 8

        # Day 2 Bar 0 (Index 6)
        d2_f0 = features[6]
        assert d2_f0.candle_timestamp == day2_base
        # Must NOT compute return vs Day 1 close!
        assert d2_f0.return_1bar is None
        assert d2_f0.rolling_return_3bar is None
        # Must reset VWAP to Day 2 open
        typ = (1865 + 1855 + 1862) / 3.0
        assert math.isclose(d2_f0.session_vwap, typ, abs_tol=1e-4)
        # Opening range must reset to IN_PROGRESS
        assert d2_f0.opening_range_status == OpeningRangeStatus.IN_PROGRESS
        assert d2_f0.opening_range_high is None

    def test_opening_range_unavailable_when_open_is_missing(self):
        """Verify that opening range is UNAVAILABLE if the session does not start at 09:15:00 IST."""
        # Data starts late at 09:20 instead of 09:15
        late_ts = datetime(2026, 10, 14, 9, 20, tzinfo=IST)
        late_candles = [
            IntradayCandle("BHARTIARTL", late_ts, IntradayInterval.M5, 1850, 1860, 1845, 1855, 1000, True, "test"),
            IntradayCandle("BHARTIARTL", late_ts + timedelta(minutes=5), IntradayInterval.M5, 1855, 1865, 1850, 1860, 1000, True, "test"),
            IntradayCandle("BHARTIARTL", late_ts + timedelta(minutes=10), IntradayInterval.M5, 1860, 1870, 1855, 1865, 1000, True, "test"),
        ]
        features = compute_intraday_features(late_candles)
        for f in features:
            assert f.opening_range_status == OpeningRangeStatus.UNAVAILABLE
            assert f.opening_range_high is None
            assert f.opening_range_low is None
            assert f.opening_range_breakout is None


class TestZeroLookaheadAndTemporalIntegrity:
    """Strict empirical verification of zero lookahead bias and temporal immutability."""

    def test_future_candle_invariance(self, hand_calculated_session_5m):
        """Verify that appending future candles leaves all earlier feature values 100% bit-for-bit unchanged."""
        base_3 = hand_calculated_session_5m[:3]
        features_base = compute_intraday_features(base_3)

        # Append future candle 4
        all_4 = hand_calculated_session_5m[:4]
        features_with_future = compute_intraday_features(all_4)

        # Earlier 3 records must be completely identical
        for i in range(3):
            assert features_base[i] == features_with_future[i]

    def test_future_price_tampering_isolation(self, hand_calculated_session_5m):
        """Verify that altering future prices has zero effect on past computed features."""
        original_features = compute_intraday_features(hand_calculated_session_5m)

        # Tamper with future Bar 5 price
        tampered_candles = list(hand_calculated_session_5m)
        c5 = tampered_candles[5]
        tampered_candles[5] = IntradayCandle(
            symbol=c5.symbol,
            timestamp=c5.timestamp,
            interval=c5.interval,
            open=c5.open,
            high=9999.0,  # Huge spike
            low=c5.low,
            close=9990.0,
            volume=9999999,
            source=c5.source,
        )

        tampered_features = compute_intraday_features(tampered_candles)

        # Bars 0, 1, 2, 3, 4 must remain exactly identical to original
        for i in range(5):
            assert original_features[i] == tampered_features[i]

    def test_availability_timestamps_strictly_lag_open(self, hand_calculated_session_5m):
        """Verify that every feature record availability timestamp equals the bar close time."""
        features = compute_intraday_features(hand_calculated_session_5m)
        for f in features:
            expected_close = f.candle_timestamp + timedelta(seconds=f.interval.duration_seconds)
            assert f.available_at == expected_close
            assert f.available_at > f.candle_timestamp

    def test_chronological_sorting_invariance(self, hand_calculated_session_5m):
        """Verify that out-of-order input candles produce identical sorted features."""
        shuffled = [
            hand_calculated_session_5m[3],
            hand_calculated_session_5m[0],
            hand_calculated_session_5m[4],
            hand_calculated_session_5m[1],
            hand_calculated_session_5m[5],
            hand_calculated_session_5m[2],
        ]
        features_shuffled = compute_intraday_features(shuffled)
        features_ordered = compute_intraday_features(hand_calculated_session_5m)

        assert len(features_shuffled) == len(features_ordered)
        for i in range(len(features_ordered)):
            assert features_shuffled[i] == features_ordered[i]

    def test_intraday_engine_compute_features_integration(self, hand_calculated_session_5m):
        """Verify IntradayEngine compute_features method interface."""
        provider = SyntheticTestIntradayProvider()
        engine = IntradayEngine(provider=provider)
        features = engine.compute_features(hand_calculated_session_5m, opening_range_minutes=15)
        assert len(features) == 6
        assert features[3].opening_range_breakout == 1
