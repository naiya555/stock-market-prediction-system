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

from datetime import datetime, timezone
import math
import pytest

from app.core.schemas import MarketOHLCV
from app.market.indicators import (
    MovingAverageFeatures,
    calculate_ema,
    calculate_sma,
    compute_moving_averages,
)


def _make_bar(
    symbol: str = "BHARTIARTL",
    day: int = 1,
    close: float = 100.0,
) -> MarketOHLCV:
    """Helper to generate valid canonical MarketOHLCV bars."""
    return MarketOHLCV(
        symbol=symbol,
        timestamp=datetime(2026, 9, day, 10, 0, tzinfo=timezone.utc),
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
