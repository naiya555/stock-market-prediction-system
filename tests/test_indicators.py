"""Unit Tests for Technical Indicators Layer: Moving Averages (SMA and EMA).

Validates:
- SMA calculation with small, manually verifiable datasets.
- EMA calculation with known recursion weights.
- Insufficient history (warm-up periods returning None).
- Zero future-data leakage (temporal point-in-time preservation).
- Handling of missing, zero, negative, and invalid values.
- Chronological ordering and multi-symbol isolation.
- Integration via compute_moving_averages and MovingAverageFeatures container.
"""

from datetime import datetime, timedelta, timezone
import math
import pytest

from app.core.schemas import MarketOHLCV
from app.market.indicators import (
    BollingerBandsSeries,
    MACDSeries,
    MovingAverageFeatures,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_true_range,
    calculate_atr,
    calculate_roc,
    compute_moving_averages,
    compute_technical_indicators,
)


def _make_bar(
    symbol: str = "BHARTIARTL",
    day: int = 1,
    close: float = 100.0,
) -> MarketOHLCV:
    """Helper to generate valid canonical MarketOHLCV bars."""
    return MarketOHLCV(
        symbol=symbol,
        timestamp=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc) + timedelta(days=day - 1),
        open=close,
        high=close * 1.02,
        low=close * 0.98,
        close=close,
        volume=1000,
        source="test_feed",
    )


# ==============================================================================
# 1. Simple Moving Average (SMA) Tests
# ==============================================================================


def test_sma_known_calculation():
    """Verify SMA calculation on small, manually verifiable sequence."""
    prices = [10.0, 20.0, 30.0, 40.0, 50.0]
    # Window = 3
    # t=0, 1: None (insufficient history)
    # t=2: (10 + 20 + 30) / 3 = 20.0
    # t=3: (20 + 30 + 40) / 3 = 30.0
    # t=4: (30 + 40 + 50) / 3 = 40.0
    sma = calculate_sma(prices, window=3)

    assert len(sma) == 5
    assert sma[0] is None
    assert sma[1] is None
    assert sma[2] == pytest.approx(20.0)
    assert sma[3] == pytest.approx(30.0)
    assert sma[4] == pytest.approx(40.0)


def test_sma_window_5_known_values():
    """Verify SMA-5 on exactly 5 observations."""
    prices = [100.0, 102.0, 104.0, 106.0, 108.0]
    # Sum = 520, Mean = 104.0
    sma = calculate_sma(prices, window=5)

    assert sma[:4] == [None, None, None, None]
    assert sma[4] == pytest.approx(104.0)


def test_sma_insufficient_history():
    """Verify SMA returns None when series length is strictly less than window."""
    prices = [10.0, 20.0, 30.0]
    sma = calculate_sma(prices, window=5)
    assert len(sma) == 3
    assert all(v is None for v in sma)


def test_sma_window_1():
    """Verify window=1 yields identity price series."""
    prices = [10.0, 25.0, 40.0]
    sma = calculate_sma(prices, window=1)
    assert sma == [pytest.approx(10.0), pytest.approx(25.0), pytest.approx(40.0)]


def test_sma_invalid_window_raises():
    """Verify window < 1 raises ValueError."""
    with pytest.raises(ValueError, match="window must be >= 1"):
        calculate_sma([10.0], window=0)


def test_sma_empty_input():
    """Verify empty input returns empty list."""
    assert calculate_sma([], window=3) == []


def test_sma_no_future_leakage():
    """Verify that altering future prices does not alter current or past SMA values."""
    prices_a = [100.0, 110.0, 120.0, 130.0, 140.0]
    prices_b = [100.0, 110.0, 120.0, 130.0, 999.0]  # Only the 5th price differs

    sma_a = calculate_sma(prices_a, window=3)
    sma_b = calculate_sma(prices_b, window=3)

    # For indices 0 through 3, values must be strictly identical
    assert sma_a[:4] == sma_b[:4]
    # Index 4 must differ
    assert sma_a[4] != sma_b[4]


def test_sma_handles_invalid_or_non_positive_prices():
    """Verify non-positive prices or NaN mask the affected rolling window as None."""
    prices = [10.0, 20.0, -5.0, 40.0, 50.0]
    sma = calculate_sma(prices, window=3)

    # Window 3:
    # t=2: includes -5.0 -> None
    # t=3: includes -5.0 -> None
    # t=4: [40, 50, ...] wait, index 4 window is [index 2 (-5), index 3 (40), index 4 (50)] -> includes -5.0 -> None!
    assert sma[2] is None
    assert sma[3] is None
    assert sma[4] is None


# ==============================================================================
# 2. Exponential Moving Average (EMA) Tests
# ==============================================================================


def test_ema_known_calculation():
    """Verify EMA calculation on small, manually verifiable sequence."""
    prices = [10.0, 20.0, 30.0]
    # Window = 3 -> alpha = 2 / (3 + 1) = 0.5
    # adjust = False:
    # y_0 = 10.0
    # y_1 = (1 - 0.5) * 10 + 0.5 * 20 = 15.0
    # y_2 = (1 - 0.5) * 15 + 0.5 * 30 = 22.5
    # With min_periods = 3:
    # t=0, 1: None
    # t=2: 22.5
    ema = calculate_ema(prices, window=3, min_periods=3, adjust=False)

    assert len(ema) == 3
    assert ema[0] is None
    assert ema[1] is None
    assert ema[2] == pytest.approx(22.5)


def test_ema_window_5_known_values():
    """Verify EMA-5 on 5 observations matching manual recursion."""
    prices = [100.0, 102.0, 104.0, 106.0, 108.0]
    # alpha = 2 / 6 = 1/3
    # y0 = 100
    # y1 = 2/3 * 100 + 1/3 * 102 = 100.666667
    # y2 = 2/3 * 100.666667 + 1/3 * 104 = 101.777778
    # y3 = 2/3 * 101.777778 + 1/3 * 106 = 103.185185
    # y4 = 2/3 * 103.185185 + 1/3 * 108 = 104.790123
    ema = calculate_ema(prices, window=5, min_periods=5, adjust=False)

    assert ema[:4] == [None, None, None, None]
    assert ema[4] == pytest.approx(104.790123, abs=1e-5)


def test_ema_insufficient_history():
    """Verify EMA returns None when observations < min_periods."""
    prices = [10.0, 20.0, 30.0]
    ema = calculate_ema(prices, window=5, min_periods=5)
    assert len(ema) == 3
    assert all(v is None for v in ema)


def test_ema_no_future_leakage():
    """Verify altering future prices does not alter earlier EMA values."""
    prices_a = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]
    prices_b = [100.0, 102.0, 104.0, 106.0, 108.0, 999.0]

    ema_a = calculate_ema(prices_a, window=5, min_periods=5)
    ema_b = calculate_ema(prices_b, window=5, min_periods=5)

    # Values up to index 4 must match exactly
    assert ema_a[:5] == ema_b[:5]
    # Value at index 4 must not be None
    assert ema_a[4] is not None
    assert ema_a[4] == pytest.approx(ema_b[4])
    # Index 5 must differ
    assert ema_a[5] != ema_b[5]


def test_ema_invalid_window_raises():
    """Verify window < 1 raises ValueError."""
    with pytest.raises(ValueError, match="window must be >= 1"):
        calculate_ema([10.0], window=0)


def test_ema_empty_input():
    """Verify empty input returns empty list."""
    assert calculate_ema([], window=5) == []


# ==============================================================================
# 3. compute_moving_averages Integration & Feature Container Tests
# ==============================================================================


def test_compute_moving_averages_multi_window():
    """Verify compute_moving_averages generates both SMA and EMA across specified windows."""
    bars = [_make_bar(day=i, close=100.0 + i * 2) for i in range(1, 11)]  # 10 bars
    features = compute_moving_averages(bars, sma_windows=(5, 10), ema_windows=(5, 10))

    assert len(features) == 10

    # At session 5 (index 4, 5th bar): 5-period metrics available, 10-period metrics None
    feat_5 = features[4]
    assert feat_5.sma_5 is not None
    assert feat_5.ema_5 is not None
    assert feat_5.sma_10 is None
    assert feat_5.ema_10 is None

    # At session 10 (index 9, 10th bar): Both 5-period and 10-period metrics available
    feat_10 = features[9]
    assert feat_10.sma_5 is not None
    assert feat_10.ema_5 is not None
    assert feat_10.sma_10 is not None
    assert feat_10.ema_10 is not None


def test_compute_moving_averages_multi_symbol_isolation():
    """Verify indicators for different tickers do not cross-contaminate."""
    bars_a = [_make_bar(symbol="BHARTIARTL", day=i, close=100.0 + i) for i in range(1, 6)]
    bars_b = [_make_bar(symbol="TCS", day=i, close=3000.0 + i * 10) for i in range(1, 6)]

    # Interleave records
    interleaved = [bars_a[0], bars_b[0], bars_a[1], bars_b[1], bars_a[2], bars_b[2], bars_a[3], bars_b[3], bars_a[4], bars_b[4]]

    features = compute_moving_averages(interleaved, sma_windows=(5,), ema_windows=(5,))
    assert len(features) == 10

    bharti_feats = [f for f in features if f.symbol == "BHARTIARTL"]
    tcs_feats = [f for f in features if f.symbol == "TCS"]

    assert len(bharti_feats) == 5
    assert len(tcs_feats) == 5

    # Check 5th session SMA
    # Bharti: mean of [101, 102, 103, 104, 105] = 103.0
    assert bharti_feats[4].sma_5 == pytest.approx(103.0)
    # TCS: mean of [3010, 3020, 3030, 3040, 3050] = 3030.0
    assert tcs_feats[4].sma_5 == pytest.approx(3030.0)


def test_compute_moving_averages_unsorted_input():
    """Verify unsorted input is sorted chronologically before indicator calculation."""
    bars = [_make_bar(day=i, close=100.0 + i) for i in range(1, 6)]
    shuffled = [bars[4], bars[0], bars[2], bars[1], bars[3]]

    features = compute_moving_averages(shuffled, sma_windows=(5,), ema_windows=(5,))

    assert len(features) == 5
    assert [f.timestamp for f in features] == [b.timestamp for b in bars]
    assert features[4].sma_5 == pytest.approx(103.0)


def test_moving_average_features_to_dict():
    """Verify MovingAverageFeatures dictionary serialization."""
    bar = _make_bar(day=1, close=150.0)
    feat = MovingAverageFeatures(
        symbol=bar.symbol,
        timestamp=bar.timestamp,
        close=bar.close,
        smas={5: 148.5, 10: None},
        emas={5: 149.2, 10: None},
    )

    d = feat.to_dict()
    assert d["symbol"] == "BHARTIARTL"
    assert d["close"] == 150.0
    assert d["sma_5"] == 148.5
    assert d["sma_10"] is None
    assert d["ema_5"] == 149.2
    assert d["ema_10"] is None


def test_compute_moving_averages_empty():
    """Verify compute_moving_averages returns empty list on empty input."""
    assert compute_moving_averages([]) == []


# ==============================================================================
# 4. Relative Strength Index (RSI) Tests
# ==============================================================================


def test_rsi_known_calculation():
    """Verify RSI calculation against manual step-by-step textbook calculations.

    Period: 3
    Prices: [100.0, 102.0, 101.0, 104.0, 103.0]
    Changes:
      1: +2.0 (gain 2.0, loss 0.0)
      2: -1.0 (gain 0.0, loss 1.0)
      3: +3.0 (gain 3.0, loss 0.0)
      Initial AvgGain = 5/3 = 1.666667, AvgLoss = 1/3 = 0.333333
      RSI[3] = 100 * (1.666667 / 2.0) = 83.333333

      4: -1.0 (gain 0.0, loss 1.0)
      AvgGain = (1.666667 * 2 + 0.0) / 3 = 10/9 = 1.111111
      AvgLoss = (0.333333 * 2 + 1.0) / 3 = 5/9 = 0.555556
      RSI[4] = 100 * (1.111111 / 1.666667) = 66.666667
    """
    prices = [100.0, 102.0, 101.0, 104.0, 103.0]
    rsi = calculate_rsi(prices, period=3)

    assert len(rsi) == 5
    assert rsi[0] is None
    assert rsi[1] is None
    assert rsi[2] is None
    assert rsi[3] == pytest.approx(83.333333, rel=1e-5)
    assert rsi[4] == pytest.approx(66.666667, rel=1e-5)


def test_rsi_standard_14_period_monotone_cases():
    """Verify standard 14-period RSI on strictly increasing, decreasing, and flat series."""
    # 15 sessions required for 14 price changes (period=14)
    increasing = [100.0 + i * 2.0 for i in range(15)]
    rsi_inc = calculate_rsi(increasing, period=14)
    assert rsi_inc[13] is None  # Only 13 changes
    assert rsi_inc[14] == pytest.approx(100.0)  # Pure gains -> RSI=100.0

    decreasing = [200.0 - i * 2.0 for i in range(15)]
    rsi_dec = calculate_rsi(decreasing, period=14)
    assert rsi_dec[14] == pytest.approx(0.0)  # Pure losses -> RSI=0.0

    flat = [150.0] * 15
    rsi_flat = calculate_rsi(flat, period=14)
    assert rsi_flat[14] == pytest.approx(50.0)  # Zero gains & zero losses -> neutral 50.0


def test_rsi_insufficient_history():
    """Verify RSI returns None for all sessions when input prices <= period."""
    prices = [100.0 + i for i in range(14)]  # 14 prices has only 13 changes (< 14 period)
    rsi = calculate_rsi(prices, period=14)
    assert len(rsi) == 14
    assert all(r is None for r in rsi)


def test_rsi_boundedness():
    """Verify RSI is strictly bounded in [0.0, 100.0] across volatile price sequences."""
    oscillating = [100.0, 105.0, 95.0, 110.0, 90.0, 115.0, 85.0, 120.0, 80.0, 125.0, 75.0, 130.0, 70.0, 135.0, 65.0, 140.0]
    rsi = calculate_rsi(oscillating, period=5)
    for val in rsi:
        if val is not None:
            assert 0.0 <= val <= 100.0


def test_rsi_no_future_leakage():
    """Verify modifying future prices does not alter earlier RSI observations."""
    prices_base = [100.0, 102.0, 101.0, 104.0, 103.0, 105.0, 107.0]
    prices_altered = [100.0, 102.0, 101.0, 104.0, 103.0, 999.0, 888.0]

    rsi_base = calculate_rsi(prices_base, period=3)
    rsi_altered = calculate_rsi(prices_altered, period=3)

    # Observations at indices 0, 1, 2, 3, 4 must match exactly
    for i in range(5):
        if rsi_base[i] is None:
            assert rsi_altered[i] is None
        else:
            assert rsi_base[i] == pytest.approx(rsi_altered[i])

    # Index 5 must differ because of price change at 5
    assert rsi_base[5] != rsi_altered[5]


def test_rsi_invalid_period_raises():
    """Verify non-positive RSI period raises ValueError."""
    with pytest.raises(ValueError, match="RSI period must be >= 1"):
        calculate_rsi([100.0, 102.0], period=0)


def test_rsi_empty_input():
    """Verify empty input returns empty list."""
    assert calculate_rsi([], period=14) == []


def test_rsi_handles_invalid_or_negative_prices():
    """Verify non-positive or NaN prices yield None safely without raising uncaught exceptions."""
    bad_prices = [100.0, 102.0, -10.0, 104.0, 105.0]
    rsi = calculate_rsi(bad_prices, period=3)
    assert len(rsi) == 5
    assert rsi[0] is None
    # Index 3 and 4 involve the invalid -10.0 price, so must be None
    assert rsi[3] is None


def test_moving_average_features_with_rsi():
    """Verify MovingAverageFeatures encapsulates RSI and exposes rsi_14 property."""
    bar = _make_bar(day=1, close=150.0)
    feat = MovingAverageFeatures(
        symbol=bar.symbol,
        timestamp=bar.timestamp,
        close=bar.close,
        smas={5: 148.5},
        emas={5: 149.2},
        rsi={14: 62.5},
    )

    assert feat.rsi_14 == pytest.approx(62.5)
    d = feat.to_dict()
    assert d["rsi_14"] == pytest.approx(62.5)


# ==============================================================================
# 5. Regression Tests: 6-Record Case vs. Expanded-History Case
# ==============================================================================


def test_six_record_regression_case():
    """Regression Test: The original Day 8 six-record dataset.

    Confirms expected warm-up states:
    - 6 bars total (indices 0..5).
    - SMA-5 and EMA-5 become available at index 4 and 5.
    - SMA-10 and EMA-10 are None for all 6 sessions (6 < 10).
    - RSI-14 is None for all 6 sessions (6 <= 14).
    - MACD, signal line, and histogram are None for all 6 sessions (6 < 26).
    - Bollinger Bands (middle, upper, lower, bandwidth, percent_b) are None for all 6 sessions (6 < 20).
    """
    bars = [
        _make_bar(day=1, close=1877.20),
        _make_bar(day=2, close=1862.80),
        _make_bar(day=3, close=1869.00),
        _make_bar(day=4, close=1840.00),
        _make_bar(day=5, close=1854.00),
        _make_bar(day=6, close=1844.00),
    ]

    features = compute_moving_averages(bars, sma_windows=(5, 10), ema_windows=(5, 10), rsi_periods=(14,))
    assert len(features) == 6

    # Sessions 0 to 3: all indicators un-warmed
    for i in range(4):
        assert features[i].sma_5 is None
        assert features[i].ema_5 is None
        assert features[i].sma_10 is None
        assert features[i].ema_10 is None
        assert features[i].rsi_14 is None
        assert features[i].macd_line is None
        assert features[i].signal_line is None
        assert features[i].histogram is None
        assert features[i].bollinger_middle is None
        assert features[i].bollinger_upper is None
        assert features[i].bollinger_lower is None
        assert features[i].bollinger_bandwidth is None
        assert features[i].bollinger_percent_b is None
        assert features[i].atr_14 is None
        assert features[i].roc_10 is None

    # Session 4 (5th bar): 5-period available, others None
    assert features[4].sma_5 == pytest.approx((1877.20 + 1862.80 + 1869.00 + 1840.00 + 1854.00) / 5.0)
    assert features[4].ema_5 is not None
    assert features[4].sma_10 is None
    assert features[4].ema_10 is None
    assert features[4].rsi_14 is None
    assert features[4].macd_line is None
    assert features[4].signal_line is None
    assert features[4].histogram is None
    assert features[4].bollinger_middle is None
    assert features[4].bollinger_upper is None
    assert features[4].bollinger_lower is None
    assert features[4].bollinger_bandwidth is None
    assert features[4].bollinger_percent_b is None
    assert features[4].atr_14 is None
    assert features[4].roc_10 is None

    # Session 5 (6th bar): 5-period available, others None
    assert features[5].sma_5 is not None
    assert features[5].ema_5 is not None
    assert features[5].sma_10 is None
    assert features[5].ema_10 is None
    assert features[5].rsi_14 is None
    assert features[5].macd_line is None
    assert features[5].signal_line is None
    assert features[5].histogram is None
    assert features[5].bollinger_middle is None
    assert features[5].bollinger_upper is None
    assert features[5].bollinger_lower is None
    assert features[5].bollinger_bandwidth is None
    assert features[5].bollinger_percent_b is None
    assert features[5].atr_14 is None
    assert features[5].roc_10 is None


def test_expanded_history_case():
    """Expanded History Test: 40-record dataset.

    Confirms that:
    - SMA-5 and EMA-5 warm up at index 4 (5th bar).
    - SMA-10 and EMA-10 warm up at index 9 (10th bar).
    - RSI-14 warms up at index 14 (15th bar, 14 price changes).
    - Bollinger Bands warm up at index 19 (20th bar).
    - MACD line warms up at index 25 (26th bar).
    - Signal line and Histogram warm up at index 33 (34th bar).
    - By index 39 (40th bar), ALL indicators are fully available.
    """
    bars = [_make_bar(day=i, close=100.0 + (i % 5) * 2.0 + (i * 0.5)) for i in range(1, 41)]  # 40 bars
    features = compute_technical_indicators(bars, sma_windows=(5, 10), ema_windows=(5, 10), rsi_periods=(14,))

    assert len(features) == 40

    # Index 4 (5th bar): 5-session MA active; others None
    assert features[4].sma_5 is not None
    assert features[4].ema_5 is not None
    assert features[4].sma_10 is None
    assert features[4].ema_10 is None
    assert features[4].rsi_14 is None
    assert features[4].bollinger_middle is None
    assert features[4].macd_line is None
    assert features[4].signal_line is None
    assert features[4].histogram is None

    # Index 9 (10th bar): 5-session and 10-session MAs active; others None
    assert features[9].sma_5 is not None
    assert features[9].ema_5 is not None
    assert features[9].sma_10 is not None
    assert features[9].ema_10 is not None
    assert features[9].rsi_14 is None
    assert features[9].bollinger_middle is None
    assert features[9].macd_line is None
    assert features[9].signal_line is None
    assert features[9].histogram is None
    assert features[9].roc_10 is None
    assert features[9].atr_14 is None

    # Index 10 (11th bar): ROC-10 becomes active (requires 10 prior sessions)
    assert features[10].roc_10 is not None
    assert features[10].atr_14 is None

    # Index 13 (14th bar): ATR-14 becomes active (first 14 True Range values)
    assert features[12].atr_14 is None
    assert features[13].atr_14 is not None

    # Index 14 (15th bar): RSI-14 active; Bollinger and MACD None
    assert features[14].sma_5 is not None
    assert features[14].ema_5 is not None
    assert features[14].sma_10 is not None
    assert features[14].ema_10 is not None
    assert features[14].rsi_14 is not None
    assert features[14].bollinger_middle is None
    assert features[14].macd_line is None
    assert features[14].signal_line is None
    assert features[14].histogram is None
    assert features[14].atr_14 is not None
    assert features[14].roc_10 is not None

    # Index 19 (20th bar): Bollinger Bands active; MACD line None
    assert features[19].bollinger_middle is not None
    assert features[19].bollinger_upper is not None
    assert features[19].bollinger_lower is not None
    assert features[19].bollinger_bandwidth is not None
    assert features[19].bollinger_percent_b is not None
    assert features[19].bollinger_upper > features[19].bollinger_lower
    assert features[19].macd_line is None
    assert features[19].signal_line is None
    assert features[19].histogram is None

    # Index 25 (26th bar): MACD line active; Signal line and Histogram None
    assert features[25].bollinger_middle is not None
    assert features[25].macd_line is not None
    assert features[25].signal_line is None
    assert features[25].histogram is None

    # Index 33 (34th bar): ALL indicators active, including Signal line and Histogram
    assert features[33].bollinger_middle is not None
    assert features[33].macd_line is not None
    assert features[33].signal_line is not None
    assert features[33].histogram is not None
    assert features[33].histogram == pytest.approx(features[33].macd_line - features[33].signal_line)

    # Index 39 (40th bar): ALL indicators active
    assert features[39].sma_5 is not None
    assert features[39].ema_5 is not None
    assert features[39].sma_10 is not None
    assert features[39].ema_10 is not None
    assert features[39].rsi_14 is not None
    assert 0.0 <= features[39].rsi_14 <= 100.0
    assert features[39].macd_line is not None
    assert features[39].signal_line is not None
    assert features[39].histogram is not None
    assert features[39].bollinger_middle is not None
    assert features[39].bollinger_upper is not None
    assert features[39].bollinger_lower is not None
    assert features[39].bollinger_bandwidth is not None
    assert features[39].bollinger_percent_b is not None
    assert features[39].atr_14 is not None
    assert features[39].roc_10 is not None


# ==============================================================================
# 6. Moving Average Convergence Divergence (MACD) Tests
# ==============================================================================


def test_macd_known_calculation():
    """Verify MACD on small, manually verifiable price sequence."""
    prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    # Configuration: fast=2, slow=4, signal=2
    # Manual trace:
    # fast EMA (span=2, min_periods=2):
    #   t=0: None
    #   t=1: 10.666667
    #   t=2: 11.555556
    #   t=3: 12.518519
    #   t=4: 13.506173
    #   t=5: 14.502058
    #   t=6: 15.500686
    # slow EMA (span=4, min_periods=4):
    #   t=0..2: None
    #   t=3: 11.824000
    #   t=4: 12.694400
    #   t=5: 13.616640
    #   t=6: 14.569984
    # MACD line:
    #   t=0..2: None
    #   t=3: 12.518519 - 11.824000 = 0.694519
    #   t=4: 13.506173 - 12.694400 = 0.811773
    #   t=5: 14.502058 - 13.616640 = 0.885418
    #   t=6: 15.500686 - 14.569984 = 0.930702
    # Signal line (EMA span=2 of MACD, min_periods=2):
    #   t=0..3: None (at t=3, only 1 valid MACD; requires 2)
    #   t=4: (2/3)*0.811773 + (1/3)*0.694519 = 0.772688
    #   t=5: (2/3)*0.885418 + (1/3)*0.772688 = 0.847841
    #   t=6: (2/3)*0.930702 + (1/3)*0.847841 = 0.903082
    # Histogram (MACD - Signal):
    #   t=0..3: None
    #   t=4: 0.811773 - 0.772688 = 0.039085
    #   t=5: 0.885418 - 0.847841 = 0.037577
    #   t=6: 0.930702 - 0.903082 = 0.027620
    macd_res = calculate_macd(prices, fast_period=2, slow_period=4, signal_period=2)

    assert len(macd_res) == 7
    # Test unpacking support
    macd_l, sig_l, hist_l = macd_res
    assert macd_l == macd_res.macd
    assert sig_l == macd_res.signal
    assert hist_l == macd_res.histogram

    # Verify MACD line
    assert macd_res.macd[:3] == [None, None, None]
    assert macd_res.macd[3] == pytest.approx(0.694519, rel=1e-4)
    assert macd_res.macd[4] == pytest.approx(0.811773, rel=1e-4)
    assert macd_res.macd[5] == pytest.approx(0.885418, rel=1e-4)
    assert macd_res.macd[6] == pytest.approx(0.930702, rel=1e-4)

    # Verify Signal line
    assert macd_res.signal[:4] == [None, None, None, None]
    assert macd_res.signal[4] == pytest.approx(0.772688, rel=1e-4)
    assert macd_res.signal[5] == pytest.approx(0.847841, rel=1e-4)
    assert macd_res.signal[6] == pytest.approx(0.903082, rel=1e-4)

    # Verify Histogram
    assert macd_res.histogram[:4] == [None, None, None, None]
    assert macd_res.histogram[4] == pytest.approx(0.039085, rel=1e-4)
    assert macd_res.histogram[5] == pytest.approx(0.037577, rel=1e-4)
    assert macd_res.histogram[6] == pytest.approx(0.027620, rel=1e-4)


def test_macd_fast_slow_subtraction_and_histogram_identity():
    """Verify MACD line = fast EMA - slow EMA and Histogram = MACD line - Signal line."""
    prices = [100.0 + i * 1.5 + (-1) ** i * 0.7 for i in range(50)]
    fast_ema = calculate_ema(prices, window=12, min_periods=12)
    slow_ema = calculate_ema(prices, window=26, min_periods=26)
    macd_res = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

    for i in range(len(prices)):
        if fast_ema[i] is not None and slow_ema[i] is not None:
            expected_macd = fast_ema[i] - slow_ema[i]
            assert macd_res.macd[i] == pytest.approx(expected_macd)
        else:
            assert macd_res.macd[i] is None

        if macd_res.signal[i] is not None:
            assert macd_res.macd[i] is not None
            expected_hist = macd_res.macd[i] - macd_res.signal[i]
            assert macd_res.histogram[i] == pytest.approx(expected_hist, abs=1e-9)
        else:
            assert macd_res.histogram[i] is None


def test_macd_insufficient_history_and_warmup():
    """Verify warm-up requirements: slow_period for MACD line and slow+signal-1 for signal/hist."""
    # Fewer than slow_period (20 bars with default slow=26)
    prices_20 = [100.0 + i for i in range(20)]
    res_20 = calculate_macd(prices_20, fast_period=12, slow_period=26, signal_period=9)
    assert all(v is None for v in res_20.macd)
    assert all(v is None for v in res_20.signal)
    assert all(v is None for v in res_20.histogram)

    # Exactly 26 bars: index 25 is first valid MACD, signal and hist still None
    prices_26 = [100.0 + i for i in range(26)]
    res_26 = calculate_macd(prices_26, fast_period=12, slow_period=26, signal_period=9)
    assert res_26.macd[:25] == [None] * 25
    assert res_26.macd[25] is not None
    assert all(v is None for v in res_26.signal)
    assert all(v is None for v in res_26.histogram)

    # Exactly 34 bars: index 33 is first valid signal and histogram
    prices_34 = [100.0 + i for i in range(34)]
    res_34 = calculate_macd(prices_34, fast_period=12, slow_period=26, signal_period=9)
    assert res_34.signal[:33] == [None] * 33
    assert res_34.signal[33] is not None
    assert res_34.histogram[:33] == [None] * 33
    assert res_34.histogram[33] is not None


def test_macd_invalid_periods():
    """Verify invalid periods raise ValueError or TypeError."""
    prices = [10.0, 20.0, 30.0]

    # fast >= slow
    with pytest.raises(ValueError, match="strictly less than slow_period"):
        calculate_macd(prices, fast_period=26, slow_period=12, signal_period=9)

    with pytest.raises(ValueError, match="strictly less than slow_period"):
        calculate_macd(prices, fast_period=12, slow_period=12, signal_period=9)

    # non-positive periods
    with pytest.raises(ValueError, match="fast_period must be >= 1"):
        calculate_macd(prices, fast_period=0, slow_period=26, signal_period=9)

    with pytest.raises(ValueError, match="slow_period must be >= 1"):
        calculate_macd(prices, fast_period=12, slow_period=0, signal_period=9)

    with pytest.raises(ValueError, match="signal_period must be >= 1"):
        calculate_macd(prices, fast_period=12, slow_period=26, signal_period=0)

    # type errors
    with pytest.raises(TypeError, match="must be an integer"):
        calculate_macd(prices, fast_period="12", slow_period=26, signal_period=9)  # type: ignore

    with pytest.raises(TypeError, match="must be an integer"):
        calculate_macd(prices, fast_period=12, slow_period=26, signal_period=True)  # type: ignore


def test_macd_empty_input():
    """Verify empty prices input yields empty MACDSeries."""
    res = calculate_macd([])
    assert res.macd == []
    assert res.signal == []
    assert res.histogram == []
    assert len(res) == 0


def test_macd_no_future_leakage():
    """Verify altering future prices does not alter earlier MACD, signal, or histogram values."""
    prices_a = [100.0 + i * 2.0 for i in range(40)]
    prices_b = list(prices_a)
    prices_b[39] = 9999.0  # Mutate only the last price

    res_a = calculate_macd(prices_a, fast_period=12, slow_period=26, signal_period=9)
    res_b = calculate_macd(prices_b, fast_period=12, slow_period=26, signal_period=9)

    # Sessions 0..38 must be strictly identical
    assert res_a.macd[:39] == res_b.macd[:39]
    assert res_a.signal[:39] == res_b.signal[:39]
    assert res_a.histogram[:39] == res_b.histogram[:39]

    # Session 39 must differ
    assert res_a.macd[39] != res_b.macd[39]
    assert res_a.signal[39] != res_b.signal[39]
    assert res_a.histogram[39] != res_b.histogram[39]


def test_macd_negative_values():
    """Verify MACD line, signal line, and histogram handle negative values gracefully."""
    # Monotonically declining series: fast EMA will be below slow EMA -> negative MACD
    prices = [200.0 - i * 3.0 for i in range(40)]
    res = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

    # Check that MACD values from session 25 onwards are negative
    for m in res.macd[25:]:
        assert m is not None
        assert m < 0.0

    # Check that signal line from session 33 onwards is negative
    for s in res.signal[33:]:
        assert s is not None
        assert s < 0.0

    # Check histogram identity
    for i in range(33, 40):
        assert res.histogram[i] == pytest.approx(res.macd[i] - res.signal[i])


def test_macd_handles_invalid_or_non_positive_prices():
    """Verify invalid or non-positive prices mask the affected session."""
    prices = [100.0 + i for i in range(35)]
    prices[20] = -50.0  # Invalid non-positive price
    res = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

    assert res.macd[20] is None
    assert res.signal[20] is None
    assert res.histogram[20] is None


def test_compute_moving_averages_multi_symbol_macd():
    """Verify multi-symbol isolation and chronological sorting for MACD computation."""
    bars = []
    # Interleave bars for SYMA and SYMB across 40 days
    for day in range(1, 41):
        bars.append(_make_bar(symbol="SYMB", day=day, close=200.0 + day))
        bars.append(_make_bar(symbol="SYMA", day=day, close=100.0 + day))

    features = compute_moving_averages(bars, macd_fast=12, macd_slow=26, macd_signal=9)
    assert len(features) == 80

    # Group results by symbol
    syma_feats = [f for f in features if f.symbol == "SYMA"]
    symb_feats = [f for f in features if f.symbol == "SYMB"]
    assert len(syma_feats) == 40
    assert len(symb_feats) == 40

    # Ensure chronological order
    for sym_list in (syma_feats, symb_feats):
        for i in range(1, len(sym_list)):
            assert sym_list[i].timestamp > sym_list[i - 1].timestamp

    # Check MACD availability
    assert syma_feats[25].macd_line is not None
    assert syma_feats[33].signal_line is not None
    assert symb_feats[25].macd_line is not None
    assert symb_feats[33].signal_line is not None


def test_moving_average_features_with_macd_to_dict():
    """Verify MovingAverageFeatures dictionary serialization contains MACD keys."""
    bar = _make_bar(day=1, close=150.0)
    feat = MovingAverageFeatures(
        symbol=bar.symbol,
        timestamp=bar.timestamp,
        close=bar.close,
        smas={5: 148.5},
        emas={5: 149.2},
        rsi={14: 62.5},
        macd=1.25,
        macd_signal=0.85,
        macd_histogram=0.40,
    )

    assert feat.macd_line == pytest.approx(1.25)
    assert feat.signal_line == pytest.approx(0.85)
    assert feat.histogram == pytest.approx(0.40)

    d = feat.to_dict()
    assert d["macd"] == pytest.approx(1.25)
    assert d["macd_signal"] == pytest.approx(0.85)
    assert d["macd_histogram"] == pytest.approx(0.40)


# ==============================================================================
# 7. Bollinger Bands Tests
# ==============================================================================


def test_bollinger_bands_known_calculation():
    """Verify Bollinger Bands on small, manually verifiable price sequence."""
    prices = [10.0, 20.0, 30.0, 40.0, 50.0]
    # Window = 3, Multiplier = 2.0, ddof = 0
    # Manual trace:
    #   t=0, 1: None (< 3 window)
    #   t=2: Window [10, 20, 30]
    #     Middle = (10 + 20 + 30) / 3 = 20.0
    #     Population Variance = ((10-20)^2 + (20-20)^2 + (30-20)^2) / 3 = 200 / 3
    #     Population Std = sqrt(200 / 3) = 8.16496580927726
    #     Upper = 20.0 + 2.0 * 8.1649658 = 36.3299316
    #     Lower = 20.0 - 2.0 * 8.1649658 = 3.6700684
    #     Band Width = (Upper - Lower) / Middle = 32.6598632 / 20.0 = 1.63299316
    #     Percent B = (Close - Lower) / (Upper - Lower) = (30 - 3.6700684) / 32.6598632 = 0.8061862
    bb = calculate_bollinger_bands(prices, window=3, multiplier=2.0, ddof=0)

    assert len(bb) == 5
    # Sequence unpacking protocol
    mid, up, low, bw, pb = bb
    assert mid == bb.middle
    assert up == bb.upper
    assert low == bb.lower
    assert bw == bb.bandwidth
    assert pb == bb.percent_b
    assert bb.band_width == bb.bandwidth

    # Check indices 0 and 1
    assert bb.middle[:2] == [None, None]
    assert bb.upper[:2] == [None, None]
    assert bb.lower[:2] == [None, None]
    assert bb.bandwidth[:2] == [None, None]
    assert bb.percent_b[:2] == [None, None]

    # Check index 2
    assert bb.middle[2] == pytest.approx(20.0)
    assert bb.upper[2] == pytest.approx(36.3299316)
    assert bb.lower[2] == pytest.approx(3.6700684)
    assert bb.bandwidth[2] == pytest.approx(1.63299316)
    assert bb.percent_b[2] == pytest.approx(0.8061862)

    # Check index 3: Window [20, 30, 40] -> Middle = 30.0, Std = sqrt(200/3)
    assert bb.middle[3] == pytest.approx(30.0)
    assert bb.upper[3] == pytest.approx(30.0 + 2.0 * 8.164965809)
    assert bb.lower[3] == pytest.approx(30.0 - 2.0 * 8.164965809)
    assert bb.bandwidth[3] == pytest.approx((bb.upper[3] - bb.lower[3]) / 30.0)
    assert bb.percent_b[3] == pytest.approx((40.0 - bb.lower[3]) / (bb.upper[3] - bb.lower[3]))


def test_bollinger_bands_ddof_1():
    """Verify Bollinger Bands sample standard deviation convention (ddof=1)."""
    prices = [10.0, 20.0, 30.0]
    # Sample Variance = ((10-20)^2 + 0 + (30-20)^2) / (3 - 1) = 200 / 2 = 100.0
    # Sample Std = 10.0
    # Middle = 20.0, Upper = 40.0, Lower = 0.0
    # Band Width = (40 - 0) / 20 = 2.0
    # Percent B = (30 - 0) / (40 - 0) = 0.75
    bb = calculate_bollinger_bands(prices, window=3, multiplier=2.0, ddof=1)

    assert bb.middle[2] == pytest.approx(20.0)
    assert bb.upper[2] == pytest.approx(40.0)
    assert bb.lower[2] == pytest.approx(0.0)
    assert bb.bandwidth[2] == pytest.approx(2.0)
    assert bb.percent_b[2] == pytest.approx(0.75)


def test_bollinger_bands_configurable_window_and_multiplier():
    """Verify configurable window and multiplier (including num_std alias)."""
    prices = [100.0 + i for i in range(10)]
    bb1 = calculate_bollinger_bands(prices, window=5, multiplier=1.5)
    bb2 = calculate_bollinger_bands(prices, window=5, num_std=1.5)

    assert bb1.middle == bb2.middle
    assert bb1.upper == bb2.upper
    assert bb1.lower == bb2.lower
    assert bb1.middle[4] is not None
    assert bb1.upper[4] is not None


def test_bollinger_bands_warmup_and_insufficient_history():
    """Verify warm-up periods return None rather than fabricating numbers."""
    prices_10 = [100.0 + i for i in range(10)]
    bb_10 = calculate_bollinger_bands(prices_10, window=20)
    assert all(v is None for v in bb_10.middle)
    assert all(v is None for v in bb_10.upper)
    assert all(v is None for v in bb_10.lower)
    assert all(v is None for v in bb_10.bandwidth)
    assert all(v is None for v in bb_10.percent_b)

    prices_20 = [100.0 + i for i in range(20)]
    bb_20 = calculate_bollinger_bands(prices_20, window=20)
    assert bb_20.middle[:19] == [None] * 19
    assert bb_20.middle[19] is not None
    assert bb_20.upper[19] is not None
    assert bb_20.lower[19] is not None
    assert bb_20.bandwidth[19] is not None
    assert bb_20.percent_b[19] is not None


def test_bollinger_bands_invalid_parameters():
    """Verify parameter validations for window, multiplier, and ddof."""
    prices = [10.0, 20.0, 30.0]

    # Non-positive window
    with pytest.raises(ValueError, match="window must be >= 1"):
        calculate_bollinger_bands(prices, window=0)
    with pytest.raises(ValueError, match="window must be >= 1"):
        calculate_bollinger_bands(prices, window=-5)

    # Non-integer window
    with pytest.raises(TypeError, match="window must be an integer"):
        calculate_bollinger_bands(prices, window=20.5)  # type: ignore
    with pytest.raises(TypeError, match="window must be an integer"):
        calculate_bollinger_bands(prices, window=True)  # type: ignore

    # Non-positive or non-finite multiplier
    with pytest.raises(ValueError, match="multiplier must be positive and finite"):
        calculate_bollinger_bands(prices, multiplier=0.0)
    with pytest.raises(ValueError, match="multiplier must be positive and finite"):
        calculate_bollinger_bands(prices, multiplier=-2.0)
    with pytest.raises(ValueError, match="multiplier must be positive and finite"):
        calculate_bollinger_bands(prices, multiplier=float("nan"))
    with pytest.raises(ValueError, match="multiplier must be positive and finite"):
        calculate_bollinger_bands(prices, multiplier=float("inf"))

    # Non-numeric multiplier
    with pytest.raises(TypeError, match="multiplier must be a number"):
        calculate_bollinger_bands(prices, multiplier="2.0")  # type: ignore

    # Invalid ddof
    with pytest.raises(ValueError, match="ddof must satisfy"):
        calculate_bollinger_bands(prices, window=3, ddof=-1)
    with pytest.raises(ValueError, match="ddof must satisfy"):
        calculate_bollinger_bands(prices, window=3, ddof=3)  # ddof must be < window
    with pytest.raises(TypeError, match="ddof must be an integer"):
        calculate_bollinger_bands(prices, window=3, ddof=1.5)  # type: ignore


def test_bollinger_bands_empty_input():
    """Verify empty prices returns empty BollingerBandsSeries."""
    bb = calculate_bollinger_bands([])
    assert len(bb) == 0
    assert bb.middle == []
    assert bb.upper == []
    assert bb.lower == []
    assert bb.bandwidth == []
    assert bb.percent_b == []


def test_bollinger_bands_no_future_leakage():
    """Verify modifying a future price does not alter past or current Bollinger values."""
    prices_a = [100.0 + i for i in range(30)]
    prices_b = list(prices_a)
    prices_b[29] = 9999.0  # Only the last price is changed

    bb_a = calculate_bollinger_bands(prices_a, window=20)
    bb_b = calculate_bollinger_bands(prices_b, window=20)

    # Sessions 0..28 must be strictly identical
    assert bb_a.middle[:29] == bb_b.middle[:29]
    assert bb_a.upper[:29] == bb_b.upper[:29]
    assert bb_a.lower[:29] == bb_b.lower[:29]
    assert bb_a.bandwidth[:29] == bb_b.bandwidth[:29]
    assert bb_a.percent_b[:29] == bb_b.percent_b[:29]

    # Session 29 must differ
    assert bb_a.middle[29] != bb_b.middle[29]
    assert bb_a.upper[29] != bb_b.upper[29]


def test_bollinger_bands_invalid_prices():
    """Verify non-positive or NaN prices mask the affected rolling window as None."""
    prices = [100.0 + i for i in range(10)]
    prices[5] = -50.0  # Invalid price at session 5

    bb = calculate_bollinger_bands(prices, window=3)

    # Windows spanning index 5 must evaluate to None:
    # index 5: window [3, 4, 5] -> None
    # index 6: window [4, 5, 6] -> None
    # index 7: window [5, 6, 7] -> None
    assert bb.middle[5] is None
    assert bb.middle[6] is None
    assert bb.middle[7] is None
    assert bb.upper[5] is None
    assert bb.lower[5] is None
    assert bb.bandwidth[5] is None
    assert bb.percent_b[5] is None

    # Windows before and after must be valid
    assert bb.middle[4] is not None
    assert bb.middle[8] is not None


def test_bollinger_bands_zero_denominator_and_flat_series():
    """Verify safe handling of flat prices where upper == lower == middle (zero denominator)."""
    prices = [100.0] * 5
    bb = calculate_bollinger_bands(prices, window=3)

    # At index 2:
    # Middle = 100.0, Std = 0.0, Upper = 100.0, Lower = 100.0
    # Band Width = (100 - 100) / 100 = 0.0 (middle > 0, so valid)
    # Percent B = (100 - 100) / (100 - 100) -> denominator is 0.0, must return None safely
    assert bb.middle[2] == pytest.approx(100.0)
    assert bb.upper[2] == pytest.approx(100.0)
    assert bb.lower[2] == pytest.approx(100.0)
    assert bb.bandwidth[2] == pytest.approx(0.0)
    assert bb.percent_b[2] is None


def test_compute_moving_averages_multi_symbol_bollinger():
    """Verify multi-symbol isolation and chronological sorting for Bollinger Bands."""
    bars = []
    for day in range(1, 26):
        bars.append(_make_bar(symbol="TCS", day=day, close=3000.0 + day * 5))
        bars.append(_make_bar(symbol="INFY", day=day, close=1500.0 + day * 3))

    features = compute_moving_averages(bars, bb_window=20, bb_multiplier=2.0)
    assert len(features) == 50

    infy_feats = [f for f in features if f.symbol == "INFY"]
    tcs_feats = [f for f in features if f.symbol == "TCS"]
    assert len(infy_feats) == 25
    assert len(tcs_feats) == 25

    # Check chronological ordering
    for sym_list in (infy_feats, tcs_feats):
        for i in range(1, len(sym_list)):
            assert sym_list[i].timestamp > sym_list[i - 1].timestamp

    # Check Bollinger availability (window=20 warms up at index 19)
    assert infy_feats[18].bollinger_middle is None
    assert infy_feats[19].bollinger_middle is not None
    assert infy_feats[19].bollinger_upper is not None
    assert infy_feats[19].bollinger_lower is not None
    assert infy_feats[19].bollinger_bandwidth is not None
    assert infy_feats[19].bollinger_percent_b is not None

    assert tcs_feats[18].bollinger_middle is None
    assert tcs_feats[19].bollinger_middle is not None
    assert tcs_feats[19].bollinger_upper is not None


def test_moving_average_features_with_bollinger_to_dict():
    """Verify MovingAverageFeatures dictionary serialization contains Bollinger keys."""
    bar = _make_bar(day=1, close=150.0)
    feat = MovingAverageFeatures(
        symbol=bar.symbol,
        timestamp=bar.timestamp,
        close=bar.close,
        smas={5: 148.5},
        emas={5: 149.2},
        rsi={14: 62.5},
        macd=1.25,
        macd_signal=0.85,
        macd_histogram=0.40,
        bb_middle=149.0,
        bb_upper=155.0,
        bb_lower=143.0,
        bb_bandwidth=0.0805,
        bb_percent_b=0.5833,
    )

    assert feat.bollinger_middle == pytest.approx(149.0)
    assert feat.bollinger_upper == pytest.approx(155.0)
    assert feat.bollinger_lower == pytest.approx(143.0)
    assert feat.bollinger_bandwidth == pytest.approx(0.0805)
    assert feat.bollinger_band_width == pytest.approx(0.0805)
    assert feat.bollinger_percent_b == pytest.approx(0.5833)

    d = feat.to_dict()
    assert d["bb_middle"] == pytest.approx(149.0)
    assert d["bb_upper"] == pytest.approx(155.0)
    assert d["bb_lower"] == pytest.approx(143.0)
    assert d["bb_bandwidth"] == pytest.approx(0.0805)
    assert d["bb_percent_b"] == pytest.approx(0.5833)


# ==============================================================================
# 8. Average True Range (ATR) & Rate of Change (ROC) Tests
# ==============================================================================


def test_true_range_known_calculation():
    """Verify True Range calculation against manually verified OHLC examples."""
    # Bar 0: H=105, L=100, C=102 -> TR = 105 - 100 = 5.0
    # Bar 1: H=108, L=103, C=106 -> prev_C=102 -> max(108-103=5, |108-102|=6, |103-102|=1) = 6.0
    # Bar 2: H=104, L=98, C=100  -> prev_C=106 -> max(104-98=6, |104-106|=2, |98-106|=8) = 8.0
    # Bar 3: H=101, L=99, C=100  -> prev_C=100 -> max(101-99=2, |101-100|=1, |99-100|=1) = 2.0
    highs = [105.0, 108.0, 104.0, 101.0]
    lows = [100.0, 103.0, 98.0, 99.0]
    closes = [102.0, 106.0, 100.0, 100.0]

    tr_vals = calculate_true_range(highs, lows, closes)
    assert len(tr_vals) == 4
    assert tr_vals[0] == pytest.approx(5.0)
    assert tr_vals[1] == pytest.approx(6.0)
    assert tr_vals[2] == pytest.approx(8.0)
    assert tr_vals[3] == pytest.approx(2.0)

    # Also verify sequence of MarketOHLCV records
    bars = [
        MarketOHLCV(
            symbol="BHARTIARTL",
            timestamp=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc) + timedelta(days=i),
            open=closes[i],
            high=highs[i],
            low=lows[i],
            close=closes[i],
            volume=1000,
            source="test",
        )
        for i in range(4)
    ]
    tr_from_bars = calculate_true_range(bars)
    assert tr_from_bars == tr_vals


def test_true_range_first_session_initialization():
    """Verify first-session True Range uses High - Low when valid, and None when invalid."""
    # Valid first session: High=110, Low=100 -> TR=10.0
    assert calculate_true_range([110.0], [100.0], [105.0]) == [10.0]

    # Invalid first session: High < Low -> None
    assert calculate_true_range([95.0], [100.0], [98.0]) == [None]

    # Invalid first session: non-positive prices
    assert calculate_true_range([0.0], [0.0], [0.0]) == [None]
    assert calculate_true_range([-5.0], [-10.0], [-8.0]) == [None]


def test_true_range_invalid_ohlc_handling():
    """Verify True Range handles invalid, NaN, boolean, and mismatched length inputs safely."""
    # Mismatched lengths
    with pytest.raises(ValueError, match="must have identical lengths"):
        calculate_true_range([105.0, 110.0], [100.0], [102.0])

    # Missing low or close when high is a numeric sequence
    with pytest.raises(ValueError, match="Both low and close must be provided"):
        calculate_true_range([105.0, 110.0], None, [102.0, 105.0])

    # Empty input
    assert calculate_true_range([], [], []) == []
    assert calculate_true_range([]) == []

    # High < Low at second session
    highs = [105.0, 95.0, 105.0]
    lows = [100.0, 100.0, 100.0]
    closes = [102.0, 98.0, 102.0]
    tr = calculate_true_range(highs, lows, closes)
    assert tr[0] == pytest.approx(5.0)
    assert tr[1] is None  # High < Low is invalid
    assert tr[2] == pytest.approx(7.0)  # max(105-100=5, |105-98|=7, |100-98|=2) = 7.0

    # Non-finite or boolean values
    assert calculate_true_range([float("nan")], [100.0], [102.0]) == [None]
    assert calculate_true_range([True], [100.0], [102.0]) == [None]


def test_atr_known_calculation_and_wilder_recurrence():
    """Verify ATR-3 initial simple average seed and subsequent Wilder smoothing recurrence."""
    # 4 bars from test_true_range_known_calculation: TR = [5.0, 6.0, 8.0, 2.0]
    # Period = 3:
    # Index 0: None (< 3 bars)
    # Index 1: None (< 3 bars)
    # Index 2: First ATR = (5.0 + 6.0 + 8.0) / 3 = 19.0 / 3 ≈ 6.3333333333
    # Index 3: Wilder recurrence = ((3 - 1) * (19/3) + 2.0) / 3 = (38/3 + 6/3) / 3 = 44/9 ≈ 4.8888888889
    highs = [105.0, 108.0, 104.0, 101.0]
    lows = [100.0, 103.0, 98.0, 99.0]
    closes = [102.0, 106.0, 100.0, 100.0]

    atr_vals = calculate_atr(highs, lows, closes, period=3)
    assert len(atr_vals) == 4
    assert atr_vals[0] is None
    assert atr_vals[1] is None
    assert atr_vals[2] == pytest.approx(19.0 / 3.0)
    assert atr_vals[3] == pytest.approx(44.0 / 9.0)


def test_atr_insufficient_history_and_warmup():
    """Verify ATR-14 warmup behavior across sufficient and insufficient history sequences."""
    # 20 bars: indices 0..12 are None; index 13 (14th bar) is first valid ATR
    bars = [_make_bar(day=i, close=100.0 + i) for i in range(1, 21)]
    atr_vals = calculate_atr(bars, period=14)
    assert len(atr_vals) == 20

    for i in range(13):
        assert atr_vals[i] is None, f"Expected ATR to be None at index {i}"

    assert atr_vals[13] is not None
    assert atr_vals[13] > 0.0

    for i in range(14, 20):
        assert atr_vals[i] is not None
        assert atr_vals[i] > 0.0

    # Insufficient history: fewer than 14 bars (10 bars) -> all None
    short_bars = bars[:10]
    assert calculate_atr(short_bars, period=14) == [None] * 10


def test_atr_invalid_parameters_and_missing_values():
    """Verify ATR parameter validation and missing/corrupt value handling."""
    highs = [105.0, 108.0, 104.0]
    lows = [100.0, 103.0, 98.0]
    closes = [102.0, 106.0, 100.0]

    # Period validation
    with pytest.raises(ValueError, match="period must be >= 1"):
        calculate_atr(highs, lows, closes, period=0)

    with pytest.raises(ValueError, match="period must be >= 1"):
        calculate_atr(highs, lows, closes, period=-5)

    with pytest.raises(TypeError, match="period must be an integer"):
        calculate_atr(highs, lows, closes, period=14.5)  # type: ignore

    with pytest.raises(TypeError, match="period must be an integer"):
        calculate_atr(highs, lows, closes, period=True)  # type: ignore

    # Empty input
    assert calculate_atr([], [], [], period=14) == []
    assert calculate_atr([], period=14) == []

    # Corrupt bar inside seed window invalidates the seed
    highs_corrupt = [105.0, float("nan"), 104.0]
    lows_corrupt = [100.0, 103.0, 98.0]
    closes_corrupt = [102.0, 106.0, 100.0]
    atr_corrupt = calculate_atr(highs_corrupt, lows_corrupt, closes_corrupt, period=3)
    assert atr_corrupt[2] is None


def test_atr_no_future_leakage():
    """Verify point-in-time integrity: mutating future bars has zero effect on past ATR values."""
    bars = [_make_bar(day=i, close=100.0 + i * 2.0) for i in range(1, 25)]
    base_atr = calculate_atr(bars, period=14)

    # Mutate bar at index 20
    mutated_bars = list(bars)
    mutated_bars[20] = MarketOHLCV(
        symbol="BHARTIARTL",
        timestamp=bars[20].timestamp,
        open=300.0,
        high=350.0,
        low=290.0,
        close=340.0,
        volume=50000,
        source="test",
    )
    mutated_atr = calculate_atr(mutated_bars, period=14)

    # Bars 0 to 19 must be strictly identical
    for i in range(20):
        if base_atr[i] is None:
            assert mutated_atr[i] is None
        else:
            assert base_atr[i] == pytest.approx(mutated_atr[i])

    # Bar 20 should diverge
    assert base_atr[20] != mutated_atr[20]


def test_roc_known_calculation():
    """Verify Rate of Change (ROC) calculation against known manual calculations."""
    # Prices: [100.0, 105.0, 110.0, 104.0, 120.0], lookback=2
    # t=0: None (< 2)
    # t=1: None (< 2)
    # t=2: ((110 / 100) - 1) * 100 = 10.0%
    # t=3: ((104 / 105) - 1) * 100 = -0.952380952%
    # t=4: ((120 / 110) - 1) * 100 = 9.09090909%
    prices = [100.0, 105.0, 110.0, 104.0, 120.0]
    roc = calculate_roc(prices, period=2)

    assert len(roc) == 5
    assert roc[0] is None
    assert roc[1] is None
    assert roc[2] == pytest.approx(10.0)
    assert roc[3] == pytest.approx(((104.0 / 105.0) - 1.0) * 100.0)
    assert roc[4] == pytest.approx(((120.0 / 110.0) - 1.0) * 100.0)

    # Also test lookback alias
    assert calculate_roc(prices, lookback=2) == roc


def test_roc_warmup_and_insufficient_history():
    """Verify ROC-10 warmup: first 10 bars are None, 11th bar is first valid value."""
    prices = [100.0 + i for i in range(15)]
    roc = calculate_roc(prices, period=10)

    assert len(roc) == 15
    for i in range(10):
        assert roc[i] is None, f"Expected ROC to be None at index {i}"

    assert roc[10] is not None
    # Index 10: ((prices[10] / prices[0]) - 1) * 100 = ((110 / 100) - 1) * 100 = 10.0%
    assert roc[10] == pytest.approx(10.0)

    # Insufficient history (8 prices < 10)
    assert calculate_roc(prices[:8], period=10) == [None] * 8


def test_roc_flat_prices_zero_behavior():
    """Verify ROC produces exact 0.0 for flat price series without division errors."""
    flat_prices = [150.0] * 6
    roc = calculate_roc(flat_prices, period=3)

    assert len(roc) == 6
    assert roc[0] is None
    assert roc[1] is None
    assert roc[2] is None
    assert roc[3] == 0.0
    assert roc[4] == 0.0
    assert roc[5] == 0.0


def test_roc_invalid_parameters_and_prices():
    """Verify ROC parameter validation and handling of non-positive or NaN prices."""
    # Invalid period / lookback
    with pytest.raises(ValueError, match="period must be >= 1"):
        calculate_roc([100.0, 105.0], period=0)

    with pytest.raises(ValueError, match="period must be >= 1"):
        calculate_roc([100.0, 105.0], period=-2)

    with pytest.raises(TypeError, match="period must be an integer"):
        calculate_roc([100.0, 105.0], period="10")  # type: ignore

    with pytest.raises(TypeError, match="period must be an integer"):
        calculate_roc([100.0, 105.0], period=False)  # type: ignore

    # Empty input
    assert calculate_roc([], period=10) == []

    # Non-positive or NaN prices
    bad_prices = [100.0, 0.0, 110.0, -50.0, float("nan"), 120.0]
    roc = calculate_roc(bad_prices, period=1)
    assert roc[0] is None
    assert roc[1] is None  # price=0 is invalid
    assert roc[2] is None  # prev_price=0 is invalid denominator
    assert roc[3] is None  # price=-50 is invalid
    assert roc[4] is None  # NaN is invalid
    assert roc[5] is None  # prev_price=NaN is invalid


def test_roc_no_future_leakage():
    """Verify point-in-time integrity: mutating future price has zero effect on earlier ROC."""
    prices = [100.0 + i * 2.0 for i in range(20)]
    base_roc = calculate_roc(prices, period=5)

    mutated_prices = list(prices)
    mutated_prices[15] = 999.0
    mutated_roc = calculate_roc(mutated_prices, period=5)

    # Indices 0 to 14 must be identical
    for i in range(15):
        if base_roc[i] is None:
            assert mutated_roc[i] is None
        else:
            assert base_roc[i] == pytest.approx(mutated_roc[i])

    # Index 15 must diverge
    assert base_roc[15] != mutated_roc[15]


def test_compute_moving_averages_multi_symbol_atr_roc():
    """Verify compute_moving_averages isolates ATR and ROC per ticker and sorts chronologically."""
    infy_bars = [_make_bar(symbol="INFY", day=i, close=1000.0 + i * 10.0) for i in range(1, 20)]
    tcs_bars = [_make_bar(symbol="TCS", day=i, close=3000.0 + i * 20.0) for i in range(1, 20)]

    # Interleave to verify sorting and isolation
    mixed = []
    for a, b in zip(infy_bars, tcs_bars):
        mixed.extend([b, a])

    features = compute_moving_averages(mixed, atr_periods=(14,), roc_periods=(10,))
    assert len(features) == 38

    infy_feats = [f for f in features if f.symbol == "INFY"]
    tcs_feats = [f for f in features if f.symbol == "TCS"]

    assert len(infy_feats) == 19
    assert len(tcs_feats) == 19

    # Chronological sort check
    for feats in (infy_feats, tcs_feats):
        for i in range(1, len(feats)):
            assert feats[i].timestamp > feats[i - 1].timestamp

    # Check ATR-14: index 12 is None, index 13 is not None
    assert infy_feats[12].atr_14 is None
    assert infy_feats[13].atr_14 is not None
    assert tcs_feats[12].atr_14 is None
    assert tcs_feats[13].atr_14 is not None

    # Check ROC-10: index 9 is None, index 10 is not None
    assert infy_feats[9].roc_10 is None
    assert infy_feats[10].roc_10 is not None
    assert tcs_feats[9].roc_10 is None
    assert tcs_feats[10].roc_10 is not None


def test_moving_average_features_with_atr_roc_to_dict():
    """Verify MovingAverageFeatures dictionary serialization contains atr_14 and roc_10."""
    bar = _make_bar(day=1, close=150.0)
    feat = MovingAverageFeatures(
        symbol=bar.symbol,
        timestamp=bar.timestamp,
        close=bar.close,
        smas={5: 148.5},
        emas={5: 149.2},
        rsi={14: 62.5},
        macd=1.25,
        macd_signal=0.85,
        macd_histogram=0.40,
        bb_middle=149.0,
        bb_upper=155.0,
        bb_lower=143.0,
        bb_bandwidth=0.0805,
        bb_percent_b=0.5833,
        atr={14: 4.25},
        roc={10: 3.85},
    )

    assert feat.atr_14 == pytest.approx(4.25)
    assert feat.roc_10 == pytest.approx(3.85)

    d = feat.to_dict()
    assert d["atr_14"] == pytest.approx(4.25)
    assert d["roc_10"] == pytest.approx(3.85)

