"""Unit Tests for Trend Engine and Market Structure Analysis Layer.

Validates:
1. Clear uptrend with Higher Highs (HH) and Higher Lows (HL).
2. Clear downtrend with Lower Highs (LH) and Lower Lows (LL).
3. Sideways / range-bound price action (contracting consolidation or equal bounds).
4. Mixed swing structure (e.g., expanding megaphone HH + LL).
5. Insufficient historical candles policy (strictly None classification, never mislabeled as SIDEWAYS).
6. Missing, NaN, infinite, zero, and negative price handling.
7. Duplicate highs/lows and equal-price tie-breaking.
8. Invalid OHLC geometry filtering.
9. Swing confirmation timing (t + k) and prevention of look-ahead leakage.
10. Deterministic results across repeated runs.
11. Configurable swing window (k) and minimum swings requirement.
12. Point-in-time rolling trend series alignment (compute_rolling_trends).
13. Integration into MarketDataPipelineResult and process_market_data.
14. Serialization of SwingPoint and TrendAnalysisResult to dictionaries.
"""

from datetime import datetime, timezone
import math
from typing import List

import pytest

from app.core.schemas import MarketOHLCV
from app.market.pipeline import process_market_data
from app.market.trend import (
    SwingPoint,
    TrendAnalysisResult,
    TrendClassification,
    analyze_market_trend,
    classify_market_structure,
    compute_latest_trend,
    compute_rolling_trends,
    identify_swings,
    label_market_structure,
)


def _bar(
    day: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    symbol: str = "TEST",
) -> MarketOHLCV:
    """Helper to construct a valid MarketOHLCV bar."""
    valid_high = max(high, open_, close)
    valid_low = min(low, open_, close)
    return MarketOHLCV(
        symbol=symbol,
        timestamp=datetime(2026, 9, day, 10, 0, tzinfo=timezone.utc),
        open=open_,
        high=valid_high,
        low=valid_low,
        close=close,
        volume=1000,
        source="unit_test",
    )


def _create_uptrend_bars() -> List[MarketOHLCV]:
    """Create a synthetic 15-bar series with clear Higher Highs and Higher Lows (k=2).

    Pivots:
    High 1 at day 3 (t=2): High=110.0 (confirmed at day 5, t=4)
    Low 1 at day 5 (t=4): Low=95.0 (confirmed at day 7, t=6)
    High 2 at day 8 (t=7): High=125.0 -> HH (confirmed at day 10, t=9)
    Low 2 at day 11 (t=10): Low=105.0 -> HL (confirmed at day 13, t=12)
    High 3 at day 13 (t=12): High=135.0 -> HH (not yet confirmed if series ends at 14, but at 15 confirmed)
    """
    bars: List[MarketOHLCV] = [
        _bar(1, 100.0, 102.0, 98.0, 101.0),   # 0
        _bar(2, 101.0, 105.0, 100.0, 104.0),  # 1
        _bar(3, 104.0, 110.0, 102.0, 108.0),  # 2: Swing High 1 (110.0)
        _bar(4, 108.0, 106.0, 101.0, 102.0),  # 3
        _bar(5, 102.0, 103.0, 95.0, 97.0),    # 4: Swing Low 1 (95.0) - confirms High 1
        _bar(6, 97.0, 108.0, 97.0, 106.0),    # 5
        _bar(7, 106.0, 118.0, 104.0, 116.0),  # 6 - confirms Low 1
        _bar(8, 116.0, 125.0, 114.0, 122.0),  # 7: Swing High 2 (125.0 > 110.0 -> HH)
        _bar(9, 122.0, 120.0, 112.0, 115.0),  # 8
        _bar(10, 115.0, 116.0, 108.0, 110.0), # 9 - confirms High 2
        _bar(11, 110.0, 112.0, 105.0, 107.0), # 10: Swing Low 2 (105.0 > 95.0 -> HL)
        _bar(12, 107.0, 120.0, 106.0, 118.0), # 11
        _bar(13, 118.0, 135.0, 116.0, 132.0), # 12: Swing High 3 (135.0 -> HH) - confirms Low 2
        _bar(14, 132.0, 130.0, 122.0, 125.0), # 13
        _bar(15, 125.0, 126.0, 120.0, 122.0), # 14 - confirms High 3
    ]
    return bars


def _create_downtrend_bars() -> List[MarketOHLCV]:
    """Create a synthetic 15-bar series with clear Lower Highs and Lower Lows (k=2)."""
    bars: List[MarketOHLCV] = [
        _bar(1, 140.0, 142.0, 138.0, 140.0),  # 0
        _bar(2, 140.0, 146.0, 139.0, 145.0),  # 1
        _bar(3, 145.0, 150.0, 142.0, 148.0),  # 2: Swing High 1 (150.0)
        _bar(4, 148.0, 145.0, 135.0, 136.0),  # 3
        _bar(5, 136.0, 138.0, 130.0, 132.0),  # 4: Swing Low 1 (130.0) - confirms High 1
        _bar(6, 132.0, 139.0, 131.0, 137.0),  # 5
        _bar(7, 137.0, 142.0, 135.0, 140.0),  # 6 - confirms Low 1
        _bar(8, 140.0, 144.0, 136.0, 138.0),  # 7: Swing High 2 (144.0 < 150.0 -> LH)
        _bar(9, 138.0, 135.0, 125.0, 126.0),  # 8
        _bar(10, 126.0, 128.0, 122.0, 123.0), # 9 - confirms High 2
        _bar(11, 123.0, 124.0, 118.0, 120.0), # 10: Swing Low 2 (118.0 < 130.0 -> LL)
        _bar(12, 120.0, 128.0, 119.0, 126.0), # 11
        _bar(13, 126.0, 132.0, 125.0, 128.0), # 12 - confirms Low 2
        _bar(14, 128.0, 127.0, 115.0, 116.0), # 13
        _bar(15, 116.0, 118.0, 114.0, 115.0), # 14
    ]
    return bars


def test_uptrend_higher_highs_and_higher_lows():
    """Verify Trend Engine correctly identifies clear UPTREND with HH and HL."""
    bars = _create_uptrend_bars()
    result = analyze_market_trend(bars, swing_window=2, min_swings=2)

    assert result.symbol == "TEST"
    assert result.classification == TrendClassification.UPTREND
    assert result.status == TrendClassification.CONFIRMED
    assert result.is_uptrend is True
    assert result.is_downtrend is False
    assert result.is_sideways is False
    assert result.is_confirmed is True

    # Check confirmed swing counts
    assert len(result.swing_highs) >= 2
    assert len(result.swing_lows) >= 2
    assert result.last_high_structure == "HH"
    assert result.last_low_structure == "HL"

    # Verify swing points sequence
    h1, h2 = result.swing_highs[0], result.swing_highs[1]
    assert h1.price == 110.0
    assert h1.structure_label is None  # Initial base high
    assert h2.price == 125.0
    assert h2.structure_label == "HH"

    l1, l2 = result.swing_lows[0], result.swing_lows[1]
    assert l1.price == 95.0
    assert l1.structure_label is None  # Initial base low
    assert l2.price == 105.0
    assert l2.structure_label == "HL"


def test_downtrend_lower_highs_and_lower_lows():
    """Verify Trend Engine correctly identifies clear DOWNTREND with LH and LL."""
    bars = _create_downtrend_bars()
    result = analyze_market_trend(bars, swing_window=2, min_swings=2)

    assert result.classification == TrendClassification.DOWNTREND
    assert result.status == TrendClassification.CONFIRMED
    assert result.is_downtrend is True
    assert result.is_uptrend is False
    assert result.is_sideways is False

    assert result.last_high_structure == "LH"
    assert result.last_low_structure == "LL"

    assert result.swing_highs[1].structure_label == "LH"
    assert result.swing_lows[1].structure_label == "LL"


def test_sideways_contracting_triangle():
    """Verify Trend Engine identifies SIDEWAYS when high structure is LH and low structure is HL."""
    # Symmetrical triangle: H1=120, L1=90, H2=115 (LH), L2=95 (HL)
    bars = [
        _bar(1, 100.0, 105.0, 98.0, 102.0),
        _bar(2, 102.0, 112.0, 100.0, 110.0),
        _bar(3, 110.0, 120.0, 108.0, 118.0),  # High 1: 120.0
        _bar(4, 118.0, 112.0, 102.0, 104.0),
        _bar(5, 104.0, 102.0, 90.0, 92.0),    # Low 1: 90.0 (confirms High 1)
        _bar(6, 92.0, 104.0, 92.0, 102.0),
        _bar(7, 102.0, 110.0, 101.0, 108.0),  # (confirms Low 1)
        _bar(8, 108.0, 115.0, 106.0, 114.0),  # High 2: 115.0 < 120.0 -> LH
        _bar(9, 114.0, 110.0, 102.0, 104.0),
        _bar(10, 104.0, 105.0, 98.0, 100.0),  # (confirms High 2)
        _bar(11, 100.0, 102.0, 95.0, 97.0),   # Low 2: 95.0 > 90.0 -> HL
        _bar(12, 97.0, 106.0, 96.0, 104.0),
        _bar(13, 104.0, 110.0, 103.0, 108.0), # (confirms Low 2)
        _bar(14, 108.0, 107.0, 102.0, 105.0),
        _bar(15, 105.0, 106.0, 101.0, 103.0),
    ]

    result = analyze_market_trend(bars, swing_window=2, min_swings=2)

    assert result.classification == TrendClassification.SIDEWAYS
    assert result.status == TrendClassification.CONFIRMED
    assert result.is_sideways is True
    assert result.is_uptrend is False
    assert result.is_downtrend is False
    assert result.last_high_structure == "LH"
    assert result.last_low_structure == "HL"


def test_mixed_swing_structure_broadening_megaphone():
    """Verify Trend Engine handles conflicting/broadening structure (HH + LL) as SIDEWAYS."""
    # Megaphone: H1=110, L1=100, H2=120 (HH), L2=90 (LL)
    bars = [
        _bar(1, 102.0, 105.0, 100.0, 104.0),
        _bar(2, 104.0, 108.0, 102.0, 106.0),
        _bar(3, 106.0, 110.0, 104.0, 108.0),  # High 1: 110.0
        _bar(4, 108.0, 106.0, 102.0, 103.0),
        _bar(5, 103.0, 104.0, 100.0, 101.0),  # Low 1: 100.0 (confirms High 1)
        _bar(6, 101.0, 112.0, 101.0, 110.0),
        _bar(7, 110.0, 116.0, 108.0, 114.0),  # (confirms Low 1)
        _bar(8, 114.0, 120.0, 112.0, 118.0),  # High 2: 120.0 > 110.0 -> HH
        _bar(9, 118.0, 115.0, 98.0, 100.0),
        _bar(10, 100.0, 102.0, 94.0, 96.0),   # (confirms High 2)
        _bar(11, 96.0, 98.0, 90.0, 92.0),     # Low 2: 90.0 < 100.0 -> LL
        _bar(12, 92.0, 96.0, 91.0, 94.0),
        _bar(13, 94.0, 97.0, 92.0, 95.0),     # (confirms Low 2)
        _bar(14, 95.0, 98.0, 93.0, 96.0),
        _bar(15, 96.0, 99.0, 94.0, 97.0),
    ]

    result = analyze_market_trend(bars, swing_window=2, min_swings=2)

    assert result.classification == TrendClassification.SIDEWAYS
    assert result.status == TrendClassification.CONFIRMED
    assert result.last_high_structure == "HH"
    assert result.last_low_structure == "LL"


def test_insufficient_historical_candles_policy():
    """Verify insufficient data safely returns None classification and is NOT mislabeled as SIDEWAYS."""
    # 1. Empty sequence
    empty_res = analyze_market_trend([])
    assert empty_res.classification is None
    assert empty_res.status == TrendClassification.INSUFFICIENT_DATA
    assert empty_res.is_sideways is False

    # 2. Insufficient bars for window (3 bars with k=2 requires at least 5 bars)
    short_bars = [
        _bar(1, 100.0, 105.0, 95.0, 102.0),
        _bar(2, 102.0, 108.0, 100.0, 106.0),
        _bar(3, 106.0, 107.0, 102.0, 105.0),
    ]
    short_res = analyze_market_trend(short_bars, swing_window=2, min_swings=2)
    assert short_res.classification is None
    assert short_res.status == TrendClassification.INSUFFICIENT_DATA
    assert short_res.is_sideways is False

    # 3. 6 bars where only 1 swing high is confirmed (less than min_swings=2)
    partial_bars = [
        _bar(1, 100.0, 102.0, 98.0, 101.0),
        _bar(2, 101.0, 105.0, 100.0, 104.0),
        _bar(3, 104.0, 110.0, 102.0, 108.0),  # High 1 at t=2
        _bar(4, 108.0, 106.0, 101.0, 102.0),
        _bar(5, 102.0, 103.0, 95.0, 97.0),    # Confirms High 1 at t=4
        _bar(6, 97.0, 100.0, 96.0, 98.0),
    ]
    partial_res = analyze_market_trend(partial_bars, swing_window=2, min_swings=2)
    assert partial_res.classification is None
    assert partial_res.status == TrendClassification.INSUFFICIENT_DATA
    assert partial_res.is_sideways is False
    assert len(partial_res.swing_highs) == 1
    assert len(partial_res.swing_lows) == 0


def test_missing_and_non_finite_values():
    """Verify non-finite, missing, zero, and negative values do not crash swing detection."""
    bars = _create_uptrend_bars()

    class MockBadBar:
        open = 100.0
        high = float("nan")
        low = 90.0
        close = 100.0
        timestamp = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)
        symbol = "TEST"

    corrupted_bars = list(bars)
    corrupted_bars[7] = MockBadBar()  # type: ignore

    # analyze_market_trend safely rejects the bad bar during flank verification
    res = analyze_market_trend(corrupted_bars, swing_window=2, min_swings=2)
    assert isinstance(res, TrendAnalysisResult)


def test_invalid_ohlc_data():
    """Verify unphysical bars (high < low, negative prices) are safely filtered and do not crash."""
    bars = _create_uptrend_bars()

    class MockUnphysicalBar:
        open = 100.0
        high = 80.0  # high < low is unphysical
        low = 120.0
        close = 90.0
        timestamp = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)
        symbol = "TEST"

    class MockNegativeBar:
        open = -10.0
        high = -5.0
        low = -20.0
        close = -10.0
        timestamp = datetime(2026, 9, 9, 10, 0, tzinfo=timezone.utc)
        symbol = "TEST"

    corrupted_bars = list(bars)
    corrupted_bars[6] = MockUnphysicalBar()  # type: ignore
    corrupted_bars[7] = MockNegativeBar()    # type: ignore

    res = analyze_market_trend(corrupted_bars, swing_window=2, min_swings=2)
    assert isinstance(res, TrendAnalysisResult)
    # Flank checking safely skipped the unphysical and negative bars



def test_duplicate_highs_and_equal_price_tie_breaking():
    """Verify consecutive duplicate highs are tie-broken deterministically without duplicates."""
    bars = [
        _bar(1, 100.0, 102.0, 98.0, 100.0),
        _bar(2, 100.0, 105.0, 99.0, 104.0),
        _bar(3, 104.0, 110.0, 102.0, 108.0),  # Peak 1: 110.0 (strictly > preceding)
        _bar(4, 108.0, 110.0, 101.0, 102.0),  # Equal peak: 110.0 (not > bar 3, so not a pivot)
        _bar(5, 102.0, 104.0, 95.0, 98.0),    # Confirms bar 3 (110.0 >= 110.0 and 104.0)
        _bar(6, 98.0, 100.0, 96.0, 99.0),
        _bar(7, 99.0, 101.0, 97.0, 100.0),
    ]

    highs, lows = identify_swings(bars, swing_window=2)
    # Exactly one swing high at index 2 (day 3) must be identified, not two
    assert len(highs) == 1
    assert highs[0].index == 2
    assert highs[0].price == 110.0


def test_swing_confirmation_timing_and_no_lookahead_leakage():
    """Verify swing points are strictly confirmed at t + k and invisible before confirmation."""
    bars = _create_uptrend_bars()
    # High 1 occurs at index t=2 (day 3) with price 110.0
    # For k=2, confirmation happens strictly at index t + k = 4 (day 5)

    # At as_of_index=3 (day 4), High 1 must NOT be confirmed
    res_t3 = analyze_market_trend(bars, swing_window=2, as_of_index=3)
    assert len(res_t3.swing_highs) == 0

    # At as_of_index=4 (day 5), High 1 IS confirmed
    res_t4 = analyze_market_trend(bars, swing_window=2, as_of_index=4)
    assert len(res_t4.swing_highs) == 1
    assert res_t4.swing_highs[0].index == 2
    assert res_t4.swing_highs[0].confirmation_index == 4

    # Point-in-time invariant: As of day 5, result is identical whether later bars exist or not
    truncated_bars = bars[:5]
    res_trunc = analyze_market_trend(truncated_bars, swing_window=2)
    assert res_t4.swing_highs[0].to_dict() == res_trunc.swing_highs[0].to_dict()


def test_deterministic_results_repeated_runs():
    """Verify analyze_market_trend produces bit-for-bit identical results on identical inputs."""
    bars = _create_uptrend_bars()

    res1 = analyze_market_trend(bars, swing_window=2, min_swings=2)
    res2 = analyze_market_trend(bars, swing_window=2, min_swings=2)

    assert res1.to_dict() == res2.to_dict()


def test_configurable_swing_window_and_min_swings():
    """Verify configurable parameters swing_window and min_swings."""
    bars = _create_uptrend_bars()

    # Wider window k=4 requires more bars to confirm
    res_k4 = analyze_market_trend(bars, swing_window=4, min_swings=2)
    assert res_k4.swing_window == 4
    # On 15 bars with k=4, fewer pivots are confirmed
    assert len(res_k4.swing_highs) <= len(analyze_market_trend(bars, swing_window=2).swing_highs)

    # Invalid parameter validation
    with pytest.raises(ValueError, match="swing_window must be >= 1"):
        analyze_market_trend(bars, swing_window=0)

    with pytest.raises(ValueError, match="min_swings must be >= 1"):
        analyze_market_trend(bars, min_swings=0)


def test_compute_rolling_trends_alignment():
    """Verify compute_rolling_trends returns 1:1 aligned point-in-time trend series."""
    bars = _create_uptrend_bars()
    rolling = compute_rolling_trends(bars, swing_window=2, min_swings=2)

    assert len(rolling) == len(bars)
    # First few bars must be None due to insufficient confirmed swings
    assert rolling[0] is None
    assert rolling[4] is None

    # Later bars transition into confirmed UPTREND
    assert rolling[-1] == TrendClassification.UPTREND


def test_pipeline_trend_integration():
    """Verify Trend Engine integrates into process_market_data and MarketDataPipelineResult."""
    bars = _create_uptrend_bars()
    result = process_market_data(bars, swing_window=2, min_swings=2)

    # Pipeline container has trend attribute
    assert result.trend is not None
    assert isinstance(result.trend, TrendAnalysisResult)
    assert result.trend.classification == TrendClassification.UPTREND
    assert result.trend.is_uptrend is True

    # Summary dictionary has trend keys
    summary = result.to_dict()
    assert "trend" in summary
    assert "trend_classification" in summary
    assert summary["trend_classification"] == "UPTREND"


def test_serialization_to_dict():
    """Verify SwingPoint and TrendAnalysisResult serialize to clean flat dictionaries."""
    ts = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)
    confirm_ts = datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc)

    sp = SwingPoint(
        index=2,
        timestamp=ts,
        price=110.0,
        swing_type="HIGH",
        confirmation_index=4,
        confirmation_timestamp=confirm_ts,
        structure_label="HH",
    )

    d = sp.to_dict()
    assert d["index"] == 2
    assert d["timestamp"] == ts.isoformat()
    assert d["price"] == 110.0
    assert d["swing_type"] == "HIGH"
    assert d["confirmation_index"] == 4
    assert d["confirmation_timestamp"] == confirm_ts.isoformat()
    assert d["structure_label"] == "HH"


def test_incremental_rolling_trends_exact_equivalence_with_naive_analysis():
    """Verify incremental O(N) compute_rolling_trends matches repeated analyze_market_trend 100% exactly.

    Remediates CodeRabbit Deep Scan finding 3bb2c072-3523-41f5-9f47-3a836cd17ce9.
    """
    bars = _create_uptrend_bars() + _create_downtrend_bars()
    rolling = compute_rolling_trends(bars, swing_window=2, min_swings=2)

    # Reference calculation: independent naive analyze_market_trend at each cutoff t
    naive_expected = [
        analyze_market_trend(bars, swing_window=2, min_swings=2, as_of_index=t).classification
        for t in range(len(bars))
    ]

    assert rolling == naive_expected


def test_compute_latest_trend_matches_rolling_tail():
    """Verify compute_latest_trend matches the final element of compute_rolling_trends."""
    bars = _create_uptrend_bars()
    rolling = compute_rolling_trends(bars, swing_window=2, min_swings=2)
    latest = compute_latest_trend(bars, swing_window=2, min_swings=2)

    assert latest == rolling[-1]
    assert latest == TrendClassification.UPTREND


def test_assemble_feature_matrix_only_latest_speedup_and_equivalence():
    """Verify assemble_feature_matrix(only_latest=True) produces identical latest row to full matrix."""
    from app.training.feature_matrix import assemble_feature_matrix

    bars = _create_uptrend_bars()
    full_ds = assemble_feature_matrix(bars, swing_window=2, min_swings=2, only_latest=False)
    fast_ds = assemble_feature_matrix(bars, swing_window=2, min_swings=2, only_latest=True)

    assert len(fast_ds.X) == 1
    assert len(full_ds.X) == len(bars)

    # Values in the latest row must be strictly identical across all 37 features
    full_last_row = full_ds.X.iloc[-1].to_dict()
    fast_row = fast_ds.X.iloc[0].to_dict()

    for col, val in fast_row.items():
        expected = full_last_row[col]
        if val is None or (isinstance(val, float) and (val != val)):
            assert expected is None or (isinstance(expected, float) and (expected != expected))
        else:
            assert val == expected, f"Mismatch in feature '{col}': {val} vs {expected}"
