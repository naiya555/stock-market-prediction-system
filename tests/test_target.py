"""Unit Tests for Machine Learning Prediction Target Definition Layer.

Validates:
1. Positive next-session return produces strictly 'UP' (binary 1).
2. Negative next-session return produces 'DOWN' (binary 0).
3. Zero return follows the documented baseline rule (grouped into 'DOWN', binary 0).
4. Missing next-session close (final observation) strictly produces None (missing target).
5. Invalid, non-positive, NaN, and infinite prices are handled safely without crashing.
6. Unsorted input records are ordered chronologically by timestamp ascending.
7. Weekends and market holidays do not require a next-calendar-day row.
8. The target is aligned to the correct prediction session timestamp.
9. Future outcome columns cannot leak into the feature set (isolation and point-in-time test).
10. Multi-symbol isolation guarantees targets do not cross ticker boundaries.
11. Results are completely deterministic across repeated runs.
12. TargetObservation serialization to dictionary (.to_dict()).
"""

from datetime import datetime, timezone
import math
from typing import List

import pytest

from app.core.schemas import MarketOHLCV
from app.prediction.target import (
    DirectionTarget,
    TargetObservation,
    calculate_forward_return,
    classify_forward_direction,
    compute_target_series,
    generate_direction_targets,
)


def _make_bar(
    day: int,
    close: float,
    month: int = 9,
    symbol: str = "BHARTIARTL",
    open_: float = 100.0,
    high: float = 110.0,
    low: float = 90.0,
    volume: int = 1000,
) -> MarketOHLCV:
    """Helper to construct valid MarketOHLCV bars."""
    v_high = max(high, open_, close)
    v_low = min(low, open_, close)
    return MarketOHLCV(
        symbol=symbol,
        timestamp=datetime(2026, month, day, 15, 30, tzinfo=timezone.utc),
        open=open_,
        high=v_high,
        low=v_low,
        close=close,
        volume=volume,
        source="unit_test",
    )


def test_positive_next_session_return_produces_up():
    """Verify that close[t+1] > close[t] produces UP and binary 1."""
    # 100.0 -> 105.0 (+5.0%)
    ret = calculate_forward_return(100.0, 105.0)
    assert ret is not None
    assert pytest.approx(ret, rel=1e-6) == 0.05

    direction, binary = classify_forward_direction(ret)
    assert direction == DirectionTarget.UP
    assert binary == DirectionTarget.UP_BINARY


def test_negative_next_session_return_produces_down():
    """Verify that close[t+1] < close[t] produces DOWN and binary 0."""
    # 100.0 -> 95.0 (-5.0%)
    ret = calculate_forward_return(100.0, 95.0)
    assert ret is not None
    assert pytest.approx(ret, rel=1e-6) == -0.05

    direction, binary = classify_forward_direction(ret)
    assert direction == DirectionTarget.DOWN
    assert binary == DirectionTarget.DOWN_BINARY


def test_zero_return_follows_documented_binary_rule():
    """Verify that close[t+1] == close[t] (0.0% return) is grouped into DOWN (binary 0)."""
    # 100.0 -> 100.0 (0.0%)
    ret = calculate_forward_return(100.0, 100.0)
    assert ret is not None
    assert ret == 0.0

    direction, binary = classify_forward_direction(ret)
    # Must follow documented initial binary rule: zero return -> DOWN
    assert direction == DirectionTarget.DOWN
    assert binary == DirectionTarget.DOWN_BINARY


def test_missing_next_session_close_on_final_observation():
    """Verify that the final observation without a known next session has an explicitly missing target."""
    bars = [
        _make_bar(1, 100.0),
        _make_bar(2, 105.0),
        _make_bar(3, 110.0),
    ]

    targets = generate_direction_targets(bars)
    assert len(targets) == 3

    # Bar 0 (day 1): predicts day 2
    assert targets[0].current_close == 100.0
    assert targets[0].next_close == 105.0
    assert targets[0].target_direction == DirectionTarget.UP
    assert targets[0].target_binary == 1
    assert targets[0].has_target is True

    # Bar 1 (day 2): predicts day 3
    assert targets[1].current_close == 105.0
    assert targets[1].next_close == 110.0
    assert targets[1].target_direction == DirectionTarget.UP
    assert targets[1].target_binary == 1
    assert targets[1].has_target is True

    # Bar 2 (day 3 - final session): outcome is in the future and unknown
    assert targets[2].current_close == 110.0
    assert targets[2].next_close is None
    assert targets[2].next_timestamp is None
    assert targets[2].target_return is None
    assert targets[2].target_direction is None
    assert targets[2].target_binary is None
    assert targets[2].has_target is False
    assert targets[2].is_up is None
    assert targets[2].is_down is None


def test_invalid_and_non_positive_prices_handled_safely():
    """Verify that non-positive, zero, NaN, and Infinite prices evaluate safely to None."""
    # Zero or negative current price
    assert calculate_forward_return(0.0, 100.0) is None
    assert calculate_forward_return(-10.0, 100.0) is None

    # Zero or negative next price
    assert calculate_forward_return(100.0, 0.0) is None
    assert calculate_forward_return(100.0, -5.0) is None

    # NaN / Inf prices
    assert calculate_forward_return(float("nan"), 100.0) is None
    assert calculate_forward_return(100.0, float("nan")) is None
    assert calculate_forward_return(float("inf"), 100.0) is None
    assert calculate_forward_return(100.0, float("inf")) is None

    # Direction classification on None
    dir_none, bin_none = classify_forward_direction(None)
    assert dir_none is None
    assert bin_none is None


def test_unsorted_input_handled_according_to_chronological_conventions():
    """Verify that unsorted bars are safely ordered chronologically per symbol."""
    bars_unsorted = [
        _make_bar(3, 110.0),  # day 3
        _make_bar(1, 100.0),  # day 1
        _make_bar(2, 105.0),  # day 2
    ]

    targets = generate_direction_targets(bars_unsorted)
    assert len(targets) == 3

    # Output must be ordered by timestamp ascending
    assert targets[0].timestamp == bars_unsorted[1].timestamp  # day 1
    assert targets[0].current_close == 100.0
    assert targets[0].next_close == 105.0

    assert targets[1].timestamp == bars_unsorted[2].timestamp  # day 2
    assert targets[1].current_close == 105.0
    assert targets[1].next_close == 110.0

    assert targets[2].timestamp == bars_unsorted[0].timestamp  # day 3
    assert targets[2].current_close == 110.0
    assert targets[2].next_close is None


def test_weekends_and_market_holidays_do_not_require_calendar_daily_spacing():
    """Verify that session t+1 pairs with the next available trading day, not calendar day."""
    # Friday Sep 4 -> Monday Sep 7 (skipping Saturday Sep 5 and Sunday Sep 6)
    # Monday Sep 7 -> Wednesday Sep 9 (simulated exchange holiday on Tuesday Sep 8)
    bars = [
        _make_bar(4, 100.0),  # Friday
        _make_bar(7, 104.0),  # Monday (+4.0%)
        _make_bar(9, 102.0),  # Wednesday (-1.92%)
    ]

    targets = generate_direction_targets(bars)
    assert len(targets) == 3

    # Friday targets Monday
    assert targets[0].timestamp.day == 4
    assert targets[0].next_timestamp is not None
    assert targets[0].next_timestamp.day == 7
    assert targets[0].next_close == 104.0
    assert targets[0].target_direction == DirectionTarget.UP

    # Monday targets Wednesday
    assert targets[1].timestamp.day == 7
    assert targets[1].next_timestamp is not None
    assert targets[1].next_timestamp.day == 9
    assert targets[1].next_close == 102.0
    assert targets[1].target_direction == DirectionTarget.DOWN

    # Wednesday is final bar
    assert targets[2].timestamp.day == 9
    assert targets[2].next_timestamp is None
    assert targets[2].has_target is False


def test_target_aligned_to_correct_prediction_date():
    """Verify that row t represents prediction made at session t date for session t+1 outcome."""
    bars = [
        _make_bar(1, 100.0),
        _make_bar(2, 98.0),
    ]

    targets = generate_direction_targets(bars)
    # Row 0 is dated Day 1
    assert targets[0].timestamp == bars[0].timestamp
    assert targets[0].current_close == 100.0
    # Its target is the outcome realized on Day 2
    assert targets[0].next_timestamp == bars[1].timestamp
    assert targets[0].next_close == 98.0
    assert targets[0].target_return == pytest.approx(-0.02)
    assert targets[0].target_direction == DirectionTarget.DOWN
    assert targets[0].target_binary == 0


def test_future_outcome_columns_cannot_leak_into_feature_set():
    """Verify strict temporal boundary: modifying future price changes target but not current bar."""
    bars_v1 = [
        _make_bar(1, 100.0),
        _make_bar(2, 105.0),
    ]
    bars_v2 = [
        _make_bar(1, 100.0),
        _make_bar(2, 90.0),  # Different future outcome
    ]

    t1 = generate_direction_targets(bars_v1)
    t2 = generate_direction_targets(bars_v2)

    # Current bar state at t=0 is strictly identical
    assert t1[0].current_close == t2[0].current_close == 100.0
    assert t1[0].timestamp == t2[0].timestamp

    # Target reflects the respective future outcomes
    assert t1[0].target_direction == DirectionTarget.UP
    assert t2[0].target_direction == DirectionTarget.DOWN


def test_multi_symbol_isolation():
    """Verify that target generation separates tickers and does not leak targets across symbols."""
    bars = [
        _make_bar(1, 100.0, symbol="INFY"),
        _make_bar(2, 110.0, symbol="INFY"),
        _make_bar(1, 500.0, symbol="TCS"),
        _make_bar(2, 490.0, symbol="TCS"),
    ]

    targets = generate_direction_targets(bars)
    assert len(targets) == 4

    infy_targets = [t for t in targets if t.symbol == "INFY"]
    tcs_targets = [t for t in targets if t.symbol == "TCS"]

    assert len(infy_targets) == 2
    assert len(tcs_targets) == 2

    # INFY day 1 -> INFY day 2
    assert infy_targets[0].next_close == 110.0
    assert infy_targets[0].target_direction == DirectionTarget.UP
    assert infy_targets[1].next_close is None  # final INFY bar

    # TCS day 1 -> TCS day 2
    assert tcs_targets[0].next_close == 490.0
    assert tcs_targets[0].target_direction == DirectionTarget.DOWN
    assert tcs_targets[1].next_close is None  # final TCS bar


def test_deterministic_results_repeated_runs():
    """Verify that repeated target calculations yield strictly identical results."""
    bars = [
        _make_bar(1, 100.0),
        _make_bar(2, 105.0),
        _make_bar(3, 102.0),
        _make_bar(4, 102.0),
    ]

    run1 = [t.to_dict() for t in generate_direction_targets(bars)]
    run2 = [t.to_dict() for t in generate_direction_targets(bars)]
    assert run1 == run2


def test_compute_target_series_low_level():
    """Verify compute_target_series helper with float sequences."""
    prices = [100.0, 105.0, 100.0, 100.0]
    returns, directions, binaries = compute_target_series(prices)

    assert len(returns) == 4
    assert len(directions) == 4
    assert len(binaries) == 4

    # 100 -> 105 (+5%) -> UP (1)
    assert pytest.approx(returns[0]) == 0.05
    assert directions[0] == "UP"
    assert binaries[0] == 1

    # 105 -> 100 (-4.76%) -> DOWN (0)
    assert pytest.approx(returns[1]) == (100.0 / 105.0 - 1.0)
    assert directions[1] == "DOWN"
    assert binaries[1] == 0

    # 100 -> 100 (0.0%) -> DOWN (0)
    assert returns[2] == 0.0
    assert directions[2] == "DOWN"
    assert binaries[2] == 0

    # Final bar -> None
    assert returns[3] is None
    assert directions[3] is None
    assert binaries[3] is None


def test_target_observation_serialization():
    """Verify TargetObservation.to_dict() serialization."""
    ts = datetime(2026, 9, 1, 15, 30, tzinfo=timezone.utc)
    next_ts = datetime(2026, 9, 2, 15, 30, tzinfo=timezone.utc)

    obs = TargetObservation(
        symbol="TEST",
        timestamp=ts,
        current_close=100.0,
        next_timestamp=next_ts,
        next_close=105.0,
        target_return=0.05,
        target_direction="UP",
        target_binary=1,
    )

    d = obs.to_dict()
    assert d["symbol"] == "TEST"
    assert d["timestamp"] == ts.isoformat()
    assert d["current_close"] == 100.0
    assert d["next_timestamp"] == next_ts.isoformat()
    assert d["next_close"] == 105.0
    assert d["target_return"] == 0.05
    assert d["target_direction"] == "UP"
    assert d["target_binary"] == 1
