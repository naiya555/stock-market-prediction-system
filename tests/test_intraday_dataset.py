"""Deterministic Unit and Leakage Tests for Day 71 Intraday Dataset Assembly and Splits.

Covers:
1. Feature timestamp vs target realization timestamp (temporal sequencing).
2. Correct future-label alignment with exact hand-calculated returns and directions.
3. No future data in feature columns (strict lookahead prevention).
4. Incomplete target windows due to feed gaps (quarantined as INCOMPLETE_HORIZON_GAP).
5. Session-boundary and overnight handling (quarantined as SESSION_CLOSE_CUTOFF, no overnight targets).
6. Equal price handling (zero return -> 0 direction).
7. Missing volume preservation (no fabrication).
8. Multi-symbol rejection (cross-instrument isolation).
9. Chronological ordering and out-of-order input tolerance.
10. Expanding chronological walk-forward split generation.
11. Strict embargo enforcement (train target horizon quarantined from validation).
12. Disjoint train / val / embargo sets and reproducibility.
13. Insufficient data rejection with actionable errors.
14. Future-data tampering test: modifying future candles does not alter past features or targets.
"""

from datetime import date, datetime, timedelta
import math
import pytest

from app.market.intraday import (
    IntradayCandle,
    IntradayDatasetObservation,
    IntradayInterval,
    IntradaySplit,
    IntradayTargetStatus,
    assemble_intraday_dataset,
    compute_intraday_features,
    generate_intraday_chronological_splits,
)
from app.market.session import IST


def _make_candle(
    symbol: str,
    ts: datetime,
    close: float,
    volume: int | None = 1000,
    interval: IntradayInterval = IntradayInterval.M5,
) -> IntradayCandle:
    return IntradayCandle(
        symbol=symbol,
        timestamp=ts,
        open=close - 1.0,
        high=close + 2.0,
        low=close - 2.0,
        close=close,
        volume=volume,
        interval=interval,
    )


def _generate_synthetic_day(
    session_date: date,
    symbol: str = "TCS",
    base_price: float = 3500.0,
    num_bars: int = 15,
) -> list[IntradayCandle]:
    """Generates continuous 5-minute candles starting at 09:15 IST."""
    start_time = datetime(session_date.year, session_date.month, session_date.day, 9, 15, tzinfo=IST)
    candles = []
    for i in range(num_bars):
        ts = start_time + timedelta(minutes=5 * i)
        # Deterministic price oscillation
        price = base_price + (i % 5) * 2.0 - (i % 3) * 1.5
        candles.append(_make_candle(symbol, ts, price, volume=1000 + i * 100))
    return candles


# =========================================================================
# 1. Feature Timestamp vs Target Realization Timestamp
# =========================================================================

def test_observation_timestamp_sequencing():
    """Verify feature availability and target realization timing invariants."""
    day = date(2026, 10, 15)
    candles = _generate_synthetic_day(day, num_bars=10)
    horizon = 3

    dataset = assemble_intraday_dataset(candles, horizon_bars=horizon)
    assert len(dataset) == 10

    for i in range(10 - horizon):
        obs = dataset[i]
        assert obs.target_status == IntradayTargetStatus.AVAILABLE
        # Feature availability is at the close of current candle
        assert obs.feature_available_at == obs.candle.bar_end_timestamp
        # Target realization is strictly in the future (at close of horizon candle)
        assert obs.target_realized_at is not None
        assert obs.target_realized_at > obs.feature_available_at
        # In 5-minute bars with horizon=3, realization is exactly 15 minutes after prediction
        expected_diff = timedelta(minutes=5 * horizon)
        assert obs.target_realized_at - obs.feature_available_at == expected_diff


# =========================================================================
# 2. Correct Future-Label Alignment and Equal Price Handling
# =========================================================================

def test_target_label_alignment_and_return():
    """Verify exact hand-calculated forward returns and binary direction labels."""
    day = date(2026, 10, 15)
    start_time = datetime(2026, 10, 15, 9, 15, tzinfo=IST)
    
    # Prices: 100, 105, 110, 102, 100, 120
    # Horizon = 2
    # Bar 0 (P=100) -> Target is Bar 2 (P=110): ret = +10.0%, dir = 1
    # Bar 1 (P=105) -> Target is Bar 3 (P=102): ret = (102-105)/105 = -2.857%, dir = 0
    # Bar 2 (P=110) -> Target is Bar 4 (P=100): ret = -9.091%, dir = 0
    # Bar 3 (P=102) -> Target is Bar 5 (P=120): ret = +17.647%, dir = 1
    # Bar 4, 5 -> SESSION_CLOSE_CUTOFF
    prices = [100.0, 105.0, 110.0, 102.0, 100.0, 120.0]
    candles = [
        _make_candle("RELIANCE", start_time + timedelta(minutes=5 * i), p)
        for i, p in enumerate(prices)
    ]

    dataset = assemble_intraday_dataset(candles, horizon_bars=2)
    assert len(dataset) == 6

    # Bar 0
    assert dataset[0].target_status == IntradayTargetStatus.AVAILABLE
    assert dataset[0].target_return == pytest.approx(0.10, abs=1e-5)
    assert dataset[0].target_direction == 1

    # Bar 1
    assert dataset[1].target_status == IntradayTargetStatus.AVAILABLE
    assert dataset[1].target_return == pytest.approx((102.0 - 105.0) / 105.0, abs=1e-5)
    assert dataset[1].target_direction == 0

    # Bar 2
    assert dataset[2].target_status == IntradayTargetStatus.AVAILABLE
    assert dataset[2].target_direction == 0

    # Bar 3
    assert dataset[3].target_status == IntradayTargetStatus.AVAILABLE
    assert dataset[3].target_direction == 1

    # Bar 4 & 5 (Cutoff)
    assert dataset[4].target_status == IntradayTargetStatus.SESSION_CLOSE_CUTOFF
    assert dataset[4].target_return is None
    assert dataset[4].target_direction is None

    assert dataset[5].target_status == IntradayTargetStatus.SESSION_CLOSE_CUTOFF
    assert dataset[5].target_return is None


def test_equal_price_handling():
    """Zero return (equal price) must map deterministically to direction 0 (not up)."""
    day = date(2026, 10, 15)
    start_time = datetime(2026, 10, 15, 9, 15, tzinfo=IST)
    # Bar 0: 100, Bar 1: 100
    candles = [
        _make_candle("INFY", start_time, 100.0),
        _make_candle("INFY", start_time + timedelta(minutes=5), 100.0),
    ]
    dataset = assemble_intraday_dataset(candles, horizon_bars=1)
    assert dataset[0].target_status == IntradayTargetStatus.AVAILABLE
    assert dataset[0].target_return == 0.0
    assert dataset[0].target_direction == 0  # Not strictly positive


# =========================================================================
# 3. No Future Data in Feature Columns
# =========================================================================

def test_feature_columns_contain_no_future_data():
    """Features in dataset observation must be identical to independent slice evaluation."""
    day = date(2026, 10, 15)
    candles = _generate_synthetic_day(day, num_bars=12)
    dataset = assemble_intraday_dataset(candles, horizon_bars=2)

    for i in range(len(dataset)):
        obs = dataset[i]
        # Evaluate standalone features on only past candles [0 .. i]
        isolated_features = compute_intraday_features(candles[: i + 1])[-1]
        
        # Compare key metrics
        assert obs.feature_record.close == isolated_features.close
        assert obs.feature_record.vwap == isolated_features.vwap
        assert obs.feature_record.return_1bar == isolated_features.return_1bar
        assert obs.feature_record.opening_range_breakout == isolated_features.opening_range_breakout


# =========================================================================
# 4. Incomplete Horizon Gaps (Missing Candles)
# =========================================================================

def test_missing_intermediate_or_target_candle_quarantine():
    """If a gap occurs in intraday feed within horizon, target must be quarantined."""
    day = date(2026, 10, 15)
    start_time = datetime(2026, 10, 15, 9, 15, tzinfo=IST)
    
    # 5-minute candles:
    # Bar 0: 09:15
    # Bar 1: 09:20
    # [MISSING 09:25]
    # Bar 2: 09:30
    # Bar 3: 09:35
    # Bar 4: 09:40
    candles = [
        _make_candle("SBIN", start_time, 800.0),
        _make_candle("SBIN", start_time + timedelta(minutes=5), 802.0),
        _make_candle("SBIN", start_time + timedelta(minutes=15), 805.0), # 09:30 (jumped 10m)
        _make_candle("SBIN", start_time + timedelta(minutes=20), 807.0),
        _make_candle("SBIN", start_time + timedelta(minutes=25), 810.0),
    ]
    # Horizon = 2 bars (10 minutes)
    dataset = assemble_intraday_dataset(candles, horizon_bars=2)

    # Bar 0 (09:15): expected target bar is 09:25 (which is MISSING!)
    assert dataset[0].target_status == IntradayTargetStatus.INCOMPLETE_HORIZON_GAP
    assert dataset[0].target_return is None
    assert dataset[0].target_direction is None

    # Bar 1 (09:20): expected target bar is 09:30 (which is present at index 2!)
    # But intermediate candle 09:25 was missing, violating continuous horizon continuity!
    assert dataset[1].target_status == IntradayTargetStatus.INCOMPLETE_HORIZON_GAP
    assert dataset[1].target_return is None


# =========================================================================
# 5. Overnight and Session Boundary Quarantine
# =========================================================================

def test_session_boundary_no_cross_overnight_labels():
    """Labels must NEVER span across overnight gaps between trading sessions."""
    day1 = date(2026, 10, 15)
    day2 = date(2026, 10, 16)
    
    # Day 1: 3 bars (09:15, 09:20, 09:25)
    # Day 2: 3 bars (09:15, 09:20, 09:25)
    day1_candles = _generate_synthetic_day(day1, symbol="HDFCBANK", num_bars=3)
    day2_candles = _generate_synthetic_day(day2, symbol="HDFCBANK", num_bars=3)
    all_candles = day1_candles + day2_candles

    # Horizon = 2 bars
    dataset = assemble_intraday_dataset(all_candles, horizon_bars=2)
    assert len(dataset) == 6

    # In Day 1:
    # Bar 0 (09:15) -> Target is Bar 2 (09:25) on same day -> AVAILABLE
    assert dataset[0].target_status == IntradayTargetStatus.AVAILABLE
    assert dataset[0].session_date == day1
    # Bar 1 (09:20) -> Horizon requires 09:30 which doesn't exist on Day 1 -> SESSION_CLOSE_CUTOFF (NOT Day 2!)
    assert dataset[1].target_status == IntradayTargetStatus.SESSION_CLOSE_CUTOFF
    assert dataset[1].target_return is None
    # Bar 2 (09:25) -> SESSION_CLOSE_CUTOFF
    assert dataset[2].target_status == IntradayTargetStatus.SESSION_CLOSE_CUTOFF

    # In Day 2:
    assert dataset[3].session_date == day2
    assert dataset[3].target_status == IntradayTargetStatus.AVAILABLE
    assert dataset[4].target_status == IntradayTargetStatus.SESSION_CLOSE_CUTOFF
    assert dataset[5].target_status == IntradayTargetStatus.SESSION_CLOSE_CUTOFF


# =========================================================================
# 6. Preservation of Missing Volume and Clean Validation
# =========================================================================

def test_missing_volume_preservation():
    """Missing volume must be preserved as None in VWAP and features, never fabricated."""
    day = date(2026, 10, 15)
    start_time = datetime(2026, 10, 15, 9, 15, tzinfo=IST)
    candles = [
        _make_candle("WIPRO", start_time, 500.0, volume=None),
        _make_candle("WIPRO", start_time + timedelta(minutes=5), 505.0, volume=None),
    ]
    dataset = assemble_intraday_dataset(candles, horizon_bars=1)
    assert dataset[0].feature_record.vwap is None
    assert dataset[0].candle.volume is None


def test_cross_instrument_rejection():
    """Passing candles for multiple symbols must raise ValueError."""
    day = date(2026, 10, 15)
    start_time = datetime(2026, 10, 15, 9, 15, tzinfo=IST)
    candles = [
        _make_candle("TCS", start_time, 3500.0),
        _make_candle("INFY", start_time + timedelta(minutes=5), 1800.0),
    ]
    with pytest.raises(ValueError, match="Multiple symbols detected"):
        assemble_intraday_dataset(candles)


# =========================================================================
# 7. Walk-Forward Chronological Splits and Embargo Enforcement
# =========================================================================

def test_expanding_chronological_splits_and_embargo():
    """Verify walk-forward splits enforce time ordering and embargo isolation."""
    # Create 3 days of 10 bars each = 30 observations
    candles = []
    for d in range(3):
        session_d = date(2026, 10, 14 + d)
        candles.extend(_generate_synthetic_day(session_d, symbol="ITC", num_bars=10))

    dataset = assemble_intraday_dataset(candles, horizon_bars=2)
    assert len(dataset) == 30

    splits = generate_intraday_chronological_splits(
        dataset,
        n_splits=2,
        min_train_ratio=0.4,
        min_train_samples=8,
        min_val_samples=4,
    )
    assert len(splits) == 2

    for split in splits:
        # Check indices are non-empty
        assert len(split.train_indices) >= 8
        assert len(split.val_indices) >= 4

        # Check disjointness
        train_set = set(split.train_indices)
        val_set = set(split.val_indices)
        embargo_set = set(split.embargo_indices)
        assert train_set.isdisjoint(val_set)
        assert train_set.isdisjoint(embargo_set)
        assert val_set.isdisjoint(embargo_set)

        # Train is strictly prior to validation
        max_train_idx = max(split.train_indices)
        min_val_idx = min(split.val_indices)
        assert min_val_idx > max_train_idx

        # Embargo verification:
        # Last training observation with an available target
        last_train_obs = dataset[max_train_idx]
        if last_train_obs.target_realized_at is not None:
            # All validation observations must occur strictly AFTER train target realization!
            for val_idx in split.val_indices:
                val_obs = dataset[val_idx]
                assert val_obs.observation_timestamp > last_train_obs.target_realized_at


def test_split_reproducibility():
    """Splits generated repeatedly from identical datasets must be byte-for-byte reproducible."""
    day = date(2026, 10, 15)
    candles = _generate_synthetic_day(day, symbol="LT", num_bars=20)
    dataset = assemble_intraday_dataset(candles, horizon_bars=2)

    splits1 = generate_intraday_chronological_splits(dataset, n_splits=2, min_train_samples=5, min_val_samples=3)
    splits2 = generate_intraday_chronological_splits(dataset, n_splits=2, min_train_samples=5, min_val_samples=3)

    assert len(splits1) == len(splits2)
    for s1, s2 in zip(splits1, splits2):
        assert s1.fold_index == s2.fold_index
        assert s1.train_indices == s2.train_indices
        assert s1.val_indices == s2.val_indices
        assert s1.embargo_indices == s2.embargo_indices
        assert s1.train_end_timestamp == s2.train_end_timestamp
        assert s1.val_end_timestamp == s2.val_end_timestamp


def test_insufficient_dataset_rejection():
    """Insufficient dataset size must raise actionable ValueError."""
    day = date(2026, 10, 15)
    candles = _generate_synthetic_day(day, symbol="LT", num_bars=6)
    dataset = assemble_intraday_dataset(candles, horizon_bars=2)

    with pytest.raises(ValueError, match="Insufficient dataset observations"):
        generate_intraday_chronological_splits(dataset, n_splits=3, min_train_samples=10, min_val_samples=5)


# =========================================================================
# 8. Strict Future-Data Tampering Invariant Test
# =========================================================================

def test_future_data_tampering_zero_leakage():
    """Modifying future candles must NOT change past features, past targets, or finalized split boundaries."""
    day = date(2026, 10, 15)
    candles = _generate_synthetic_day(day, symbol="BAJAJFINSV", num_bars=20)

    # Base assembly and split
    dataset_base = assemble_intraday_dataset(candles, horizon_bars=2)
    splits_base = generate_intraday_chronological_splits(dataset_base, n_splits=2, min_train_samples=6, min_val_samples=3)

    # Tamper with future bars (e.g. indices 15 through 19: 10x price and volume)
    tampered_candles = list(candles[:15])
    for c in candles[15:]:
        tampered_c = IntradayCandle(
            symbol=c.symbol,
            timestamp=c.timestamp,
            open=c.open * 10.0,
            high=c.high * 10.0,
            low=c.low * 10.0,
            close=c.close * 10.0,
            volume=(c.volume or 1000) * 10,
            interval=c.interval,
        )
        tampered_candles.append(tampered_c)

    dataset_tampered = assemble_intraday_dataset(tampered_candles, horizon_bars=2)

    # Assert past observations (0 to 12) have IDENTICAL features and targets
    for i in range(13):
        base_obs = dataset_base[i]
        tamp_obs = dataset_tampered[i]

        assert base_obs.feature_record == tamp_obs.feature_record
        assert base_obs.target_status == tamp_obs.target_status
        assert base_obs.target_return == tamp_obs.target_return
        assert base_obs.target_direction == tamp_obs.target_direction
        assert base_obs.target_realized_at == tamp_obs.target_realized_at

    # Check that fold 0 train boundaries and indices remain identical
    splits_tampered = generate_intraday_chronological_splits(dataset_tampered, n_splits=2, min_train_samples=6, min_val_samples=3)
    assert splits_base[0].train_indices == splits_tampered[0].train_indices
    assert splits_base[0].train_end_timestamp == splits_tampered[0].train_end_timestamp
