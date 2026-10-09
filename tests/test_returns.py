"""Deterministic Unit Tests for Returns and Volatility Calculations.

Validates:
- Daily simple returns (positive, negative, zero, first observation, chronological ordering)
- Rolling returns (known windows, insufficient history, no future-row leakage)
- Standard deviation (known mathematical calculation, sample ddof=1, insufficient history)
- Rolling volatility (raw standard deviation, annualized volatility, window behavior)
- Input handling (unsorted input, zero/negative prices, timestamp alignment, multi-symbol separation)
"""

from datetime import datetime, timezone
import math
import pytest

from app.core.schemas import MarketOHLCV
from app.market.returns import (
    ReturnFeatures,
    calculate_daily_returns,
    calculate_rolling_returns,
    calculate_rolling_volatility,
    calculate_standard_deviation,
    compute_market_returns,
)


def _make_bar(
    symbol: str = "BHARTIARTL",
    day: int = 1,
    close: float = 100.0,
    open_: float = 100.0,
    high: float = 105.0,
    low: float = 95.0,
    volume: int = 1000,
) -> MarketOHLCV:
    """Helper fixture to create valid canonical MarketOHLCV bars."""
    # Ensure high and low bound open and close properly
    h = max(high, open_, close)
    l = min(low, open_, close)
    return MarketOHLCV(
        symbol=symbol,
        timestamp=datetime(2026, 9, day, 10, 0, tzinfo=timezone.utc),
        open=open_,
        high=h,
        low=l,
        close=close,
        volume=volume,
        source="test_fixture",
    )


# ==============================================================================
# 1. Daily Returns Tests
# ==============================================================================


def test_daily_returns_normal_positive():
    """Test 1: Verify correct daily return calculation for a positive price move."""
    prices = [100.0, 105.0]
    rets = calculate_daily_returns(prices)
    assert len(rets) == 2
    assert rets[0] is None
    assert rets[1] == pytest.approx(0.05, abs=1e-6)  # (105 / 100) - 1 = +5%


def test_daily_returns_normal_negative():
    """Test 2: Verify correct daily return calculation for a negative price move."""
    prices = [100.0, 90.0]
    rets = calculate_daily_returns(prices)
    assert len(rets) == 2
    assert rets[0] is None
    assert rets[1] == pytest.approx(-0.10, abs=1e-6)  # (90 / 100) - 1 = -10%


def test_daily_returns_zero_and_small():
    """Test 3: Verify correct daily return calculation for zero or very small price changes."""
    prices = [100.0, 100.0, 100.01]
    rets = calculate_daily_returns(prices)
    assert rets[0] is None
    assert rets[1] == pytest.approx(0.0, abs=1e-9)
    assert rets[2] == pytest.approx(0.0001, abs=1e-6)


def test_daily_returns_first_observation_handling():
    """Test 4: Verify the very first observation explicitly returns None (no previous close)."""
    prices = [150.0]
    rets = calculate_daily_returns(prices)
    assert len(rets) == 1
    assert rets[0] is None


def test_daily_returns_chronological_ordering():
    """Test 5: Verify chronological direction of returns (P_t / P_{t-1} - 1, not forward looking)."""
    prices = [100.0, 110.0, 121.0]
    rets = calculate_daily_returns(prices)
    # Day 1 -> Day 2: 10%
    # Day 2 -> Day 3: (121 / 110) - 1 = 10%
    assert rets == [None, pytest.approx(0.10), pytest.approx(0.10)]


# ==============================================================================
# 2. Rolling Returns Tests
# ==============================================================================


def test_rolling_returns_correct_value():
    """Test 6: Verify rolling return calculation matches cumulative multi-session move."""
    # Prices: 100 -> 105 -> 110 -> 120
    prices = [100.0, 105.0, 110.0, 120.0]
    # 3-session window:
    # t=0, 1, 2: None
    # t=3: (120 / 100) - 1 = +20%
    rolling_3 = calculate_rolling_returns(prices, window=3)
    assert len(rolling_3) == 4
    assert rolling_3[0] is None
    assert rolling_3[1] is None
    assert rolling_3[2] is None
    assert rolling_3[3] == pytest.approx(0.20, abs=1e-6)


def test_rolling_returns_insufficient_history():
    """Test 7: Verify rolling returns are None when history is less than the window."""
    prices = [100.0, 102.0, 104.0]
    rolling_5 = calculate_rolling_returns(prices, window=5)
    assert len(rolling_5) == 3
    assert all(r is None for r in rolling_5)


def test_rolling_returns_no_future_row_leakage():
    """Test 8: Verify altering future rows does not change past or current rolling return."""
    prices_a = [100.0, 110.0, 120.0, 130.0, 140.0]
    prices_b = [100.0, 110.0, 120.0, 130.0, 999.0]  # Only the last price differs

    res_a = calculate_rolling_returns(prices_a, window=3)
    res_b = calculate_rolling_returns(prices_b, window=3)

    # For indices 0, 1, 2, 3 (before the change), results must be exactly identical
    assert res_a[:4] == res_b[:4]
    # Index 3: (130 / 100) - 1 = 0.30 in both
    assert res_a[3] == pytest.approx(0.30)
    assert res_b[3] == pytest.approx(0.30)
    # Only index 4 differs
    assert res_a[4] != res_b[4]


# ==============================================================================
# 3. Standard Deviation Tests
# ==============================================================================


def test_standard_deviation_known_calculation():
    """Test 9: Verify sample standard deviation on known values with ddof=1."""
    # Values: [0.01, 0.02, 0.03]
    # Mean: 0.02
    # Variance (ddof=1): ((0.01-0.02)^2 + 0 + (0.03-0.02)^2) / 2 = 0.0002 / 2 = 0.0001
    # Stdev: sqrt(0.0001) = 0.01
    vals = [0.01, 0.02, 0.03]
    stdev = calculate_standard_deviation(vals, ddof=1)
    assert stdev is not None
    assert stdev == pytest.approx(0.01, abs=1e-8)


def test_standard_deviation_zero_variance():
    """Test 10: Verify sample standard deviation is 0.0 when all values are equal."""
    vals = [0.05, 0.05, 0.05, 0.05]
    stdev = calculate_standard_deviation(vals, ddof=1)
    assert stdev == pytest.approx(0.0, abs=1e-9)


def test_standard_deviation_insufficient_samples():
    """Test 11: Verify standard deviation returns None when samples <= ddof."""
    assert calculate_standard_deviation([], ddof=1) is None
    assert calculate_standard_deviation([0.05], ddof=1) is None
    # For ddof=2, need at least 3 samples
    assert calculate_standard_deviation([0.01, 0.02], ddof=2) is None


# ==============================================================================
# 4. Volatility Tests
# ==============================================================================


def test_rolling_volatility_correctness():
    """Test 12: Verify rolling volatility matches expected sample standard deviation."""
    # 5 daily returns: [0.01, 0.02, 0.03, 0.02, 0.01]
    # Mean: 0.018
    # Squared diffs: (-0.008)^2 + (0.002)^2 + (0.012)^2 + (0.002)^2 + (-0.008)^2
    # = 0.000064 + 0.000004 + 0.000144 + 0.000004 + 0.000064 = 0.000280
    # Variance (ddof=1): 0.000280 / 4 = 0.000070
    # Stdev: sqrt(0.000070) = 0.008366600265
    daily_rets = [None, 0.01, 0.02, 0.03, 0.02, 0.01]
    # Window of 5 returns requires index 5 (which includes returns at indices 1, 2, 3, 4, 5)
    vols = calculate_rolling_volatility(daily_rets, window=5, ddof=1, annualized=False)
    assert len(vols) == 6
    assert all(v is None for v in vols[:5])
    assert vols[5] is not None
    assert vols[5] == pytest.approx(math.sqrt(0.000070), abs=1e-7)

    # Annualized volatility: vols[5] * sqrt(252)
    ann_vols = calculate_rolling_volatility(daily_rets, window=5, ddof=1, annualized=True, trading_days=252)
    assert ann_vols[5] == pytest.approx(vols[5] * math.sqrt(252), abs=1e-7)


def test_rolling_volatility_insufficient_history():
    """Test 13: Verify rolling volatility is None when fewer than `window` valid returns exist."""
    daily_rets = [None, 0.01, -0.02, 0.015]  # Only 3 valid returns
    vols = calculate_rolling_volatility(daily_rets, window=5)
    assert len(vols) == 4
    assert all(v is None for v in vols)


def test_rolling_volatility_consistent_return_series():
    """Test 14: Verify volatility is computed consistently across the return series."""
    # 7 bars, constant return of 0.02 every day
    daily_rets = [None, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02]
    vols = calculate_rolling_volatility(daily_rets, window=3)
    # Window 3:
    # t=0: None
    # t=1: [None, 0.02] -> None (contains None)
    # t=2: [None, 0.02, 0.02] -> None (contains None)
    # t=3: [0.02, 0.02, 0.02] -> stdev is 0.0
    # t=4, 5, 6: stdev is 0.0
    assert vols[0] is None
    assert vols[1] is None
    assert vols[2] is None
    assert vols[3] == pytest.approx(0.0, abs=1e-9)
    assert vols[4] == pytest.approx(0.0, abs=1e-9)
    assert vols[5] == pytest.approx(0.0, abs=1e-9)
    assert vols[6] == pytest.approx(0.0, abs=1e-9)


# ==============================================================================
# 5. Validation and Edge Cases
# ==============================================================================


def test_unsorted_input_handled_safely():
    """Test 15: Verify unsorted input records are sorted chronologically before calculating features."""
    bar1 = _make_bar(day=1, close=100.0)
    bar2 = _make_bar(day=2, close=110.0)
    bar3 = _make_bar(day=3, close=121.0)

    # Pass in shuffled order: day 3, day 1, day 2
    shuffled = [bar3, bar1, bar2]
    features = compute_market_returns(shuffled, rolling_return_windows=(2,), volatility_windows=(2,))

    assert len(features) == 3
    # Result must be in chronological order
    assert [f.timestamp for f in features] == [bar1.timestamp, bar2.timestamp, bar3.timestamp]
    assert [f.close for f in features] == [100.0, 110.0, 121.0]

    # Daily returns: Day 1=None, Day 2=10%, Day 3=10%
    assert features[0].daily_return is None
    assert features[1].daily_return == pytest.approx(0.10)
    assert features[2].daily_return == pytest.approx(0.10)


def test_invalid_or_zero_price_handled_safely():
    """Test 16: Verify zero/negative prices do not cause division-by-zero or crash."""
    prices = [100.0, 0.0, 105.0]
    rets = calculate_daily_returns(prices)
    assert rets[0] is None
    assert rets[1] is None  # Current price is 0
    assert rets[2] is None  # Previous price was 0, division prevented safely

    rolling = calculate_rolling_returns([0.0, 100.0, 110.0], window=2)
    assert rolling[0] is None
    assert rolling[1] is None
    assert rolling[2] is None  # Base was 0.0


def test_output_alignment_with_timestamps():
    """Test 17: Verify 1:1 alignment between input MarketOHLCV timestamps and output ReturnFeatures."""
    bars = [_make_bar(day=i, close=100.0 + i) for i in range(1, 6)]
    features = compute_market_returns(bars)

    assert len(features) == len(bars)
    for bar, feat in zip(bars, features):
        assert feat.symbol == bar.symbol
        assert feat.timestamp == bar.timestamp
        assert feat.close == bar.close


def test_empty_and_single_input():
    """Test 18: Verify behavior on empty list and single bar."""
    assert compute_market_returns([]) == []

    single = [_make_bar(day=1, close=100.0)]
    feats = compute_market_returns(single)
    assert len(feats) == 1
    assert feats[0].daily_return is None
    assert feats[0].rolling_returns[3] is None
    assert feats[0].rolling_returns[5] is None
    assert feats[0].rolling_volatilities[5] is None


def test_multi_symbol_separation():
    """Test 19: Verify records for different symbols are isolated and do not cross-contaminate."""
    bar_a1 = _make_bar(symbol="BHARTIARTL", day=1, close=100.0)
    bar_a2 = _make_bar(symbol="BHARTIARTL", day=2, close=110.0)
    bar_b1 = _make_bar(symbol="TCS", day=1, close=3000.0)
    bar_b2 = _make_bar(symbol="TCS", day=2, close=3300.0)

    features = compute_market_returns([bar_b2, bar_a1, bar_b1, bar_a2])
    assert len(features) == 4

    bharti_feats = [f for f in features if f.symbol == "BHARTIARTL"]
    tcs_feats = [f for f in features if f.symbol == "TCS"]

    assert len(bharti_feats) == 2
    assert bharti_feats[0].daily_return is None
    assert bharti_feats[1].daily_return == pytest.approx(0.10)

    assert len(tcs_feats) == 2
    assert tcs_feats[0].daily_return is None
    assert tcs_feats[1].daily_return == pytest.approx(0.10)


def test_return_features_to_dict_and_properties():
    """Test 20: Verify ReturnFeatures convenience properties and dictionary export."""
    bar = _make_bar(day=1, close=100.0)
    feat = ReturnFeatures(
        symbol=bar.symbol,
        timestamp=bar.timestamp,
        close=bar.close,
        daily_return=0.05,
        rolling_returns={3: 0.12, 5: 0.18},
        rolling_volatilities={5: 0.015},
        annualized_volatilities={5: 0.238},
    )

    assert feat.rolling_return_3d == 0.12
    assert feat.rolling_return_5d == 0.18
    assert feat.volatility_5d == 0.015
    assert feat.annualized_volatility_5d == 0.238

    d = feat.to_dict()
    assert d["symbol"] == "BHARTIARTL"
    assert d["close"] == 100.0
    assert d["daily_return"] == 0.05
    assert d["rolling_return_3d"] == 0.12
    assert d["rolling_return_5d"] == 0.18
    assert d["rolling_volatility_5d"] == 0.015
    assert d["annualized_volatility_5d"] == 0.238


def test_invalid_windows_raise_value_error():
    """Test 21: Verify ValueError is raised for invalid window parameters."""
    with pytest.raises(ValueError, match="must be >= 1"):
        calculate_rolling_returns([100.0], window=0)

    with pytest.raises(ValueError, match="must be >= 2"):
        calculate_rolling_volatility([0.01], window=1)
