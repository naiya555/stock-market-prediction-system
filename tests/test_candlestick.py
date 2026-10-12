"""Unit Tests for Candlestick Feature Engineering Layer.

Validates:
1. Bullish, bearish, and neutral (doji) candles against exact manual traces.
2. Correct calculation of body, range, upper-wick, and lower-wick dimensions.
3. Ratio formulas (body-to-range, upper-wick-to-range, lower-wick-to-range) and close location.
4. Mathematical partition identity: body_ratio + upper_wick_ratio + lower_wick_ratio == 1.0.
5. Zero-range candle safe division and None ratio policy.
6. Missing, NaN, infinite, zero, negative, and boolean price handling.
7. Physical OHLC candle geometry validation (High >= max(Open, Close), Low <= min(Open, Close)).
8. Input validation, length matching, and empty sequence handling.
9. Chronological alignment and multi-symbol isolation.
10. Future-data independence (strictly point-in-time calculation).
11. Serialization to flat dictionary representation.
12. Integration into MarketDataPipelineResult and MovingAverageFeatures.
"""

from datetime import datetime, timezone
import math

import pytest

from app.core.schemas import MarketOHLCV
from app.market.candlestick import (
    CandlestickFeatures,
    calculate_candlestick_features,
    calculate_single_candlestick,
    compute_candlestick_features,
)
from app.market.pipeline import process_market_data


def _make_bar(
    symbol: str = "BHARTIARTL",
    day: int = 1,
    open_: float = 100.0,
    high: float = 110.0,
    low: float = 90.0,
    close: float = 105.0,
    volume: int = 1000,
) -> MarketOHLCV:
    """Helper to generate valid canonical MarketOHLCV bars."""
    return MarketOHLCV(
        symbol=symbol,
        timestamp=datetime(2026, 9, day, 10, 0, tzinfo=timezone.utc),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        source="test_feed",
    )


def test_bullish_candle_manual_trace():
    """Verify exact formula values for a manually verifiable bullish candle."""
    ts = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    # Open=100.0, High=110.0, Low=90.0, Close=105.0
    feat = calculate_single_candlestick(
        open_=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        timestamp=ts,
        symbol="TEST",
    )

    assert feat.symbol == "TEST"
    assert feat.timestamp == ts
    assert feat.open == 100.0
    assert feat.high == 110.0
    assert feat.low == 90.0
    assert feat.close == 105.0

    # Formulas
    assert feat.candle_body == pytest.approx(5.0)  # Close - Open = 105 - 100
    assert feat.candle_body_abs == pytest.approx(5.0)  # abs(5)
    assert feat.candle_range == pytest.approx(20.0)  # High - Low = 110 - 90
    assert feat.candle_upper_wick == pytest.approx(5.0)  # High - max(O, C) = 110 - 105
    assert feat.candle_lower_wick == pytest.approx(10.0)  # min(O, C) - Low = 100 - 90

    # Ratios
    assert feat.candle_body_ratio == pytest.approx(5.0 / 20.0)  # 0.25
    assert feat.candle_upper_wick_ratio == pytest.approx(5.0 / 20.0)  # 0.25
    assert feat.candle_lower_wick_ratio == pytest.approx(10.0 / 20.0)  # 0.50
    # Ratio partition identity
    assert (
        feat.candle_body_ratio + feat.candle_upper_wick_ratio + feat.candle_lower_wick_ratio
    ) == pytest.approx(1.0)

    # Close location within range
    assert feat.candle_close_location == pytest.approx((105.0 - 90.0) / 20.0)  # 0.75

    # Intra-session return percentage
    assert feat.candle_body_return_pct == pytest.approx(((105.0 / 100.0) - 1.0) * 100.0)  # +5.0%

    # Direction and convenience properties
    assert feat.candle_direction == "bullish"
    assert feat.is_bullish is True
    assert feat.is_bearish is False
    assert feat.is_neutral is False
    assert feat.body == feat.candle_body
    assert feat.body_abs == feat.candle_body_abs
    assert feat.range == feat.candle_range
    assert feat.upper_wick == feat.candle_upper_wick
    assert feat.lower_wick == feat.candle_lower_wick
    assert feat.body_ratio == feat.candle_body_ratio
    assert feat.upper_wick_ratio == feat.candle_upper_wick_ratio
    assert feat.lower_wick_ratio == feat.candle_lower_wick_ratio
    assert feat.close_location == feat.candle_close_location
    assert feat.body_return_pct == feat.candle_body_return_pct
    assert feat.direction == feat.candle_direction


def test_bearish_candle_manual_trace():
    """Verify exact formula values for a manually verifiable bearish candle."""
    # Open=105.0, High=110.0, Low=90.0, Close=95.0
    feat = calculate_single_candlestick(
        open_=105.0,
        high=110.0,
        low=90.0,
        close=95.0,
        symbol="TEST",
    )

    assert feat.candle_body == pytest.approx(-10.0)  # Close - Open = 95 - 105
    assert feat.candle_body_abs == pytest.approx(10.0)
    assert feat.candle_range == pytest.approx(20.0)  # High - Low = 110 - 90
    assert feat.candle_upper_wick == pytest.approx(5.0)  # High - max(O, C) = 110 - 105
    assert feat.candle_lower_wick == pytest.approx(5.0)  # min(O, C) - Low = 95 - 90

    # Ratios
    assert feat.candle_body_ratio == pytest.approx(10.0 / 20.0)  # 0.50
    assert feat.candle_upper_wick_ratio == pytest.approx(5.0 / 20.0)  # 0.25
    assert feat.candle_lower_wick_ratio == pytest.approx(5.0 / 20.0)  # 0.25
    assert (
        feat.candle_body_ratio + feat.candle_upper_wick_ratio + feat.candle_lower_wick_ratio
    ) == pytest.approx(1.0)

    # Close location within range
    assert feat.candle_close_location == pytest.approx((95.0 - 90.0) / 20.0)  # 0.25

    # Intra-session return percentage
    expected_pct = ((95.0 / 105.0) - 1.0) * 100.0
    assert feat.candle_body_return_pct == pytest.approx(expected_pct)

    # Direction
    assert feat.candle_direction == "bearish"
    assert feat.is_bearish is True
    assert feat.is_bullish is False
    assert feat.is_neutral is False


def test_neutral_doji_candle_manual_trace():
    """Verify exact formula values for a neutral candle with non-zero wicks (Doji)."""
    # Open=100.0, High=110.0, Low=90.0, Close=100.0
    feat = calculate_single_candlestick(
        open_=100.0,
        high=110.0,
        low=90.0,
        close=100.0,
        symbol="TEST",
    )

    assert feat.candle_body == pytest.approx(0.0)
    assert feat.candle_body_abs == pytest.approx(0.0)
    assert feat.candle_range == pytest.approx(20.0)
    assert feat.candle_upper_wick == pytest.approx(10.0)  # 110 - 100
    assert feat.candle_lower_wick == pytest.approx(10.0)  # 100 - 90

    # Ratios
    assert feat.candle_body_ratio == pytest.approx(0.0)
    assert feat.candle_upper_wick_ratio == pytest.approx(10.0 / 20.0)  # 0.50
    assert feat.candle_lower_wick_ratio == pytest.approx(10.0 / 20.0)  # 0.50
    assert (
        feat.candle_body_ratio + feat.candle_upper_wick_ratio + feat.candle_lower_wick_ratio
    ) == pytest.approx(1.0)

    assert feat.candle_close_location == pytest.approx((100.0 - 90.0) / 20.0)  # 0.50
    assert feat.candle_body_return_pct == pytest.approx(0.0)
    assert feat.candle_direction == "neutral"
    assert feat.is_neutral is True
    assert feat.is_bullish is False
    assert feat.is_bearish is False


def test_zero_range_candle_safe_division():
    """Verify zero-range flat candle preserves zero dimensions and safely sets ratios to None."""
    feat = calculate_single_candlestick(
        open_=100.0,
        high=100.0,
        low=100.0,
        close=100.0,
        symbol="TEST",
    )

    # Valid zero dimensions are preserved
    assert feat.candle_body == pytest.approx(0.0)
    assert feat.candle_body_abs == pytest.approx(0.0)
    assert feat.candle_range == pytest.approx(0.0)
    assert feat.candle_upper_wick == pytest.approx(0.0)
    assert feat.candle_lower_wick == pytest.approx(0.0)

    # Ratios with zero range in denominator must evaluate strictly to None
    assert feat.candle_body_ratio is None
    assert feat.candle_upper_wick_ratio is None
    assert feat.candle_lower_wick_ratio is None
    assert feat.candle_close_location is None

    # Open > 0 so return percentage is 0.0%
    assert feat.candle_body_return_pct == pytest.approx(0.0)
    assert feat.candle_direction == "neutral"


def test_close_location_extremes():
    """Verify close location at boundary conditions (at Low=0.0, at High=1.0)."""
    # Close at High (marubozu or pinbar)
    feat_high = calculate_single_candlestick(open_=95.0, high=100.0, low=90.0, close=100.0)
    assert feat_high.candle_close_location == pytest.approx(1.0)

    # Close at Low
    feat_low = calculate_single_candlestick(open_=95.0, high=100.0, low=90.0, close=90.0)
    assert feat_low.candle_close_location == pytest.approx(0.0)


def test_invalid_candle_geometry_handling():
    """Verify invalid OHLC candle geometry masks features with None."""
    # High < Low
    feat1 = calculate_single_candlestick(open_=100.0, high=90.0, low=110.0, close=105.0)
    assert feat1.candle_body is None
    assert feat1.candle_range is None
    assert feat1.candle_direction is None

    # High < max(Open, Close)
    feat2 = calculate_single_candlestick(open_=100.0, high=102.0, low=90.0, close=105.0)
    assert feat2.candle_body is None
    assert feat2.candle_upper_wick is None
    assert feat2.candle_direction is None

    # Low > min(Open, Close)
    feat3 = calculate_single_candlestick(open_=100.0, high=110.0, low=98.0, close=95.0)
    assert feat3.candle_body is None
    assert feat3.candle_lower_wick is None
    assert feat3.candle_direction is None


def test_missing_nan_inf_negative_prices():
    """Verify non-finite, missing, zero, and negative prices safely evaluate to None."""
    # None price
    feat_none = calculate_single_candlestick(open_=None, high=110.0, low=90.0, close=100.0)
    assert feat_none.candle_body is None
    assert feat_none.candle_direction is None

    # NaN price
    feat_nan = calculate_single_candlestick(open_=100.0, high=float("nan"), low=90.0, close=100.0)
    assert feat_nan.candle_body is None
    assert feat_nan.candle_range is None

    # Infinite price
    feat_inf = calculate_single_candlestick(open_=100.0, high=float("inf"), low=90.0, close=100.0)
    assert feat_inf.candle_body is None

    # Zero price (non-positive)
    feat_zero = calculate_single_candlestick(open_=0.0, high=110.0, low=0.0, close=100.0)
    assert feat_zero.candle_body is None

    # Negative price
    feat_neg = calculate_single_candlestick(open_=100.0, high=110.0, low=-10.0, close=100.0)
    assert feat_neg.candle_body is None

    # Boolean price
    feat_bool = calculate_single_candlestick(open_=True, high=110.0, low=90.0, close=100.0)
    assert feat_bool.candle_body is None


def test_input_validation_and_empty_inputs():
    """Verify empty input handling and sequence length mismatch validation."""
    assert calculate_candlestick_features(None) == []
    assert calculate_candlestick_features([]) == []
    assert compute_candlestick_features([]) == []

    # Sequence length mismatch
    with pytest.raises(ValueError, match="Price sequences must have identical lengths"):
        calculate_candlestick_features(
            open_prices=[100.0, 101.0],
            high_prices=[110.0],
            low_prices=[90.0, 91.0],
            close_prices=[105.0, 106.0],
        )

    # Timestamp length mismatch
    with pytest.raises(ValueError, match="Timestamps sequence length"):
        calculate_candlestick_features(
            open_prices=[100.0],
            high_prices=[110.0],
            low_prices=[90.0],
            close_prices=[105.0],
            timestamps=[datetime.now(), datetime.now()],
        )

    # Invalid sequence objects without OHLC attributes
    with pytest.raises(TypeError, match="must have open, high, low, close attributes"):
        calculate_candlestick_features(["not_a_bar"])


def test_candlestick_from_market_ohlcv_records():
    """Verify calculate_candlestick_features accepts a sequence of MarketOHLCV records."""
    bars = [
        _make_bar(day=1, open_=100.0, high=110.0, low=90.0, close=105.0),
        _make_bar(day=2, open_=105.0, high=115.0, low=95.0, close=100.0),
    ]

    features = calculate_candlestick_features(bars)
    assert len(features) == 2
    assert features[0].candle_direction == "bullish"
    assert features[0].candle_body == pytest.approx(5.0)
    assert features[1].candle_direction == "bearish"
    assert features[1].candle_body == pytest.approx(-5.0)


def test_chronological_alignment_and_multi_symbol_isolation():
    """Verify compute_candlestick_features isolates symbols and sorts chronologically."""
    # Mix symbols and timestamps
    bar_b2 = _make_bar(symbol="INFY", day=2, open_=50.0, high=55.0, low=45.0, close=52.0)
    bar_a2 = _make_bar(symbol="BHARTIARTL", day=2, open_=105.0, high=115.0, low=95.0, close=110.0)
    bar_b1 = _make_bar(symbol="INFY", day=1, open_=48.0, high=52.0, low=46.0, close=50.0)
    bar_a1 = _make_bar(symbol="BHARTIARTL", day=1, open_=100.0, high=110.0, low=90.0, close=105.0)

    features = compute_candlestick_features([bar_b2, bar_a2, bar_b1, bar_a1])

    assert len(features) == 4
    # Expected ordering: sorted by (symbol, timestamp) -> BHARTIARTL day 1, BHARTIARTL day 2, INFY day 1, INFY day 2
    assert features[0].symbol == "BHARTIARTL"
    assert features[0].timestamp == bar_a1.timestamp
    assert features[1].symbol == "BHARTIARTL"
    assert features[1].timestamp == bar_a2.timestamp
    assert features[2].symbol == "INFY"
    assert features[2].timestamp == bar_b1.timestamp
    assert features[3].symbol == "INFY"
    assert features[3].timestamp == bar_b2.timestamp


def test_future_data_independence():
    """Verify candlestick calculations use solely contemporaneous data; future prices do not affect earlier features."""
    bar1 = _make_bar(day=1, open_=100.0, high=110.0, low=90.0, close=105.0)
    bar2_scenario_a = _make_bar(day=2, open_=105.0, high=150.0, low=80.0, close=140.0)
    bar2_scenario_b = _make_bar(day=2, open_=105.0, high=106.0, low=40.0, close=50.0)

    feat_a = calculate_candlestick_features([bar1, bar2_scenario_a])
    feat_b = calculate_candlestick_features([bar1, bar2_scenario_b])

    # Bar 1 features must be identical across both future scenarios
    assert feat_a[0].to_dict() == feat_b[0].to_dict()


def test_serialization_and_to_dict():
    """Verify CandlestickFeatures.to_dict produces flat dictionary with exact keys and ISO timestamp."""
    ts = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    feat = calculate_single_candlestick(
        open_=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        timestamp=ts,
        symbol="BHARTIARTL",
    )

    d = feat.to_dict()
    assert d["symbol"] == "BHARTIARTL"
    assert d["timestamp"] == ts.isoformat()
    assert d["open"] == 100.0
    assert d["high"] == 110.0
    assert d["low"] == 90.0
    assert d["close"] == 105.0
    assert d["candle_body"] == pytest.approx(5.0)
    assert d["candle_body_abs"] == pytest.approx(5.0)
    assert d["candle_range"] == pytest.approx(20.0)
    assert d["candle_upper_wick"] == pytest.approx(5.0)
    assert d["candle_lower_wick"] == pytest.approx(10.0)
    assert d["candle_body_ratio"] == pytest.approx(0.25)
    assert d["candle_upper_wick_ratio"] == pytest.approx(0.25)
    assert d["candle_lower_wick_ratio"] == pytest.approx(0.50)
    assert d["candle_close_location"] == pytest.approx(0.75)
    assert d["candle_body_return_pct"] == pytest.approx(5.0)
    assert d["candle_direction"] == "bullish"


def test_pipeline_candlestick_integration():
    """Verify candlestick features integrate seamlessly into process_market_data and MarketDataPipelineResult."""
    bars = [
        _make_bar(day=1, open_=100.0, high=110.0, low=90.0, close=105.0),
        _make_bar(day=2, open_=105.0, high=115.0, low=95.0, close=100.0),
        _make_bar(day=3, open_=100.0, high=108.0, low=92.0, close=100.0),
    ]

    result = process_market_data(bars)

    # 1. Pipeline container has candlesticks attribute
    assert len(result.candlesticks) == 3
    assert result.candlesticks[0].is_bullish is True
    assert result.candlesticks[1].is_bearish is True
    assert result.candlesticks[2].is_neutral is True

    # 2. to_candlestick_dicts serialization
    c_dicts = result.to_candlestick_dicts()
    assert len(c_dicts) == 3
    assert c_dicts[0]["candle_direction"] == "bullish"
    assert c_dicts[1]["candle_direction"] == "bearish"
    assert c_dicts[2]["candle_direction"] == "neutral"

    # 3. Pipeline summary dictionary has candlestick_count
    summary = result.to_dict()
    assert summary["candlestick_count"] == 3

    # 4. MovingAverageFeatures in indicators also has candlestick fields populated
    assert len(result.indicators) == 3
    assert result.indicators[0].candle_body == pytest.approx(5.0)
    assert result.indicators[0].candle_direction == "bullish"
    assert result.indicators[1].candle_body == pytest.approx(-5.0)
    assert result.indicators[1].candle_direction == "bearish"

    ind_dicts = result.to_indicator_dicts()
    assert ind_dicts[0]["candle_body"] == pytest.approx(5.0)
    assert ind_dicts[0]["candle_direction"] == "bullish"
