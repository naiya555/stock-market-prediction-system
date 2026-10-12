"""Unit Tests for Technical Feature Matrix Assembly Layer.

Validates:
1. Correct feature-column schema (exact ordered list of expected features).
2. Correct timestamp alignment with Day 15 targets (matching prediction date and outcome date).
3. Final unlabeled observation (y is strictly NaN on the final historical bar).
4. Duplicate timestamp rejection (raises ValueError with descriptive error).
5. Unsorted input handled chronologically according to project conventions.
6. Missing and non-finite values preserved (indicator warmups produce natural NaNs).
7. Target leakage rejection guard (attempting to inject target columns into X raises ValueError).
8. Future outcome columns (next_close, target_return, target_direction, target_binary) strictly excluded from X.
9. Trend confirmation timing (trend regimes encoded point-in-time without future leakage).
10. Stable row counts and deterministic repeated results across multiple runs.
11. Empty and insufficient input sequences handled gracefully.
12. get_labeled_dataset accounting and optional complete warmup filtering.
13. Compatibility with existing MarketDataPipelineResult and raw MarketOHLCV sequences.
"""

from datetime import datetime, timezone
import math
from typing import List

import numpy as np
import pandas as pd
import pytest

from app.core.schemas import MarketOHLCV
from app.market.pipeline import process_market_data
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURE_PATTERNS,
    METADATA_COLUMNS,
    TARGET_COLUMNS,
    FeatureMatrixDataset,
    assemble_feature_matrix,
    encode_candle_direction,
    encode_trend_regime,
    validate_feature_matrix_isolation,
)


def _make_bar(
    day: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int = 1000,
    month: int = 9,
    symbol: str = "TEST",
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


def _create_synthetic_series(n_bars: int = 30) -> List[MarketOHLCV]:
    """Create a synthetic sequence of n_bars valid daily bars with trending/fluctuating prices."""
    bars = []
    base_price = 100.0
    for i in range(1, n_bars + 1):
        # Deterministic variation
        delta = 2.0 * math.sin(i * 0.5) + (0.5 * i)
        close = base_price + delta
        open_ = close - 0.5
        high = close + 1.5
        low = close - 1.5
        bars.append(
            _make_bar(
                day=((i - 1) % 28) + 1,
                month=9 if i <= 28 else 10,
                open_=open_,
                high=high,
                low=low,
                close=close,
                volume=1000 + (i * 50),
            )
        )
    # Sort strictly by timestamp
    bars.sort(key=lambda b: b.timestamp)
    return bars


def test_correct_feature_column_schema():
    """Verify that feature matrix X has the exact canonical column schema and order."""
    bars = _create_synthetic_series(25)
    dataset = assemble_feature_matrix(bars)

    assert isinstance(dataset, FeatureMatrixDataset)
    assert dataset.feature_names == FEATURE_COLUMNS
    assert list(dataset.X.columns) == FEATURE_COLUMNS
    assert len(dataset.X.columns) == len(FEATURE_COLUMNS)

    # Check key feature domains are present
    assert "open" in dataset.X.columns
    assert "daily_return" in dataset.X.columns
    assert "sma_5" in dataset.X.columns
    assert "rsi_14" in dataset.X.columns
    assert "macd" in dataset.X.columns
    assert "bb_upper" in dataset.X.columns
    assert "atr_14" in dataset.X.columns
    assert "candle_body_ratio" in dataset.X.columns
    assert "trend_regime_encoded" in dataset.X.columns


def test_correct_timestamp_alignment_with_day15_targets():
    """Verify each feature row t aligns strictly with the target realized at t+1."""
    bars = [
        _make_bar(1, 100.0, 105.0, 95.0, 102.0),
        _make_bar(2, 102.0, 108.0, 100.0, 106.0),
        _make_bar(3, 106.0, 110.0, 104.0, 103.0),
    ]
    dataset = assemble_feature_matrix(bars)

    assert dataset.total_rows == 3
    assert dataset.labeled_rows == 2
    assert dataset.unlabeled_rows == 1

    # Row 0: current_close=102.0, next_close=106.0 -> fwd_ret = (106/102 - 1) > 0 -> UP (1.0)
    assert dataset.df.loc[0, "timestamp"] == bars[0].timestamp
    assert dataset.df.loc[0, "current_close"] == 102.0
    assert dataset.df.loc[0, "next_timestamp"] == bars[1].timestamp
    assert dataset.df.loc[0, "next_close"] == 106.0
    assert dataset.df.loc[0, "target_direction"] == "UP"
    assert dataset.y.iloc[0] == 1.0

    # Row 1: current_close=106.0, next_close=103.0 -> fwd_ret = (103/106 - 1) < 0 -> DOWN (0.0)
    assert dataset.df.loc[1, "timestamp"] == bars[1].timestamp
    assert dataset.df.loc[1, "current_close"] == 106.0
    assert dataset.df.loc[1, "next_timestamp"] == bars[2].timestamp
    assert dataset.df.loc[1, "next_close"] == 103.0
    assert dataset.df.loc[1, "target_direction"] == "DOWN"
    assert dataset.y.iloc[1] == 0.0


def test_final_unlabeled_observation():
    """Verify the final row has no future outcome and strictly evaluates to y = NaN."""
    bars = _create_synthetic_series(15)
    dataset = assemble_feature_matrix(bars)

    final_idx = dataset.total_rows - 1
    assert pd.isna(dataset.y.iloc[final_idx])
    assert pd.isna(dataset.df.loc[final_idx, "target_binary"])
    assert pd.isna(dataset.df.loc[final_idx, "target_return"])
    assert pd.isna(dataset.df.loc[final_idx, "target_direction"])
    assert pd.isna(dataset.df.loc[final_idx, "next_close"])
    assert pd.isna(dataset.df.loc[final_idx, "next_timestamp"])


def test_duplicate_timestamp_rejection():
    """Verify that duplicate timestamps raise a clear ValueError and halt assembly."""
    ts = datetime(2026, 9, 5, 15, 30, tzinfo=timezone.utc)
    dup_bars = [
        MarketOHLCV(
            symbol="TEST",
            timestamp=ts,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000,
            source="unit_test",
        ),
        MarketOHLCV(
            symbol="TEST",
            timestamp=ts,  # Duplicate!
            open=102.0,
            high=106.0,
            low=98.0,
            close=104.0,
            volume=1200,
            source="unit_test",
        ),
    ]

    with pytest.raises(ValueError, match="Duplicate timestamp detected"):
        assemble_feature_matrix(dup_bars)


def test_unsorted_input_ordered_chronologically():
    """Verify that unsorted input is sorted chronologically by timestamp ascending."""
    bars = [
        _make_bar(3, 106.0, 110.0, 104.0, 103.0),
        _make_bar(1, 100.0, 105.0, 95.0, 102.0),
        _make_bar(2, 102.0, 108.0, 100.0, 106.0),
    ]
    # process_market_data cleans and sorts records
    dataset = assemble_feature_matrix(bars)

    assert dataset.total_rows == 3
    # First row must be day 1
    assert dataset.df.loc[0, "timestamp"] == bars[1].timestamp
    assert dataset.df.loc[1, "timestamp"] == bars[2].timestamp
    assert dataset.df.loc[2, "timestamp"] == bars[0].timestamp


def test_missing_values_preserved_for_indicator_warmup():
    """Verify that indicator warm-up NaNs are preserved and not arbitrarily zero-filled."""
    bars = _create_synthetic_series(12)
    dataset = assemble_feature_matrix(bars)

    # SMA-10 requires 10 sessions; rows 0..8 must have NaN for sma_10
    missing = dataset.missing_value_summary()
    assert missing["sma_10"] == 9  # rows 0 to 8 are NaN
    assert pd.isna(dataset.X.loc[0, "sma_10"])
    assert pd.isna(dataset.X.loc[8, "sma_10"])
    assert not pd.isna(dataset.X.loc[9, "sma_10"])  # 10th row is computed!


def test_target_leakage_rejection_guard():
    """Verify that validate_feature_matrix_isolation rejects any forbidden future/target column."""
    # Construct a contaminated DataFrame
    bad_df = pd.DataFrame({
        "open": [100.0],
        "close": [102.0],
        "target_return": [0.05],  # LEAKAGE!
    })

    with pytest.raises(ValueError, match="Data leakage detected.*target"):
        validate_feature_matrix_isolation(bad_df)

    bad_df_future = pd.DataFrame({
        "close": [102.0],
        "next_close": [105.0],  # LEAKAGE!
    })
    with pytest.raises(ValueError, match="Data leakage detected.*next_"):
        validate_feature_matrix_isolation(bad_df_future)


def test_future_outcome_columns_strictly_excluded_from_x():
    """Verify that none of the target or outcome columns appear in dataset.X."""
    bars = _create_synthetic_series(20)
    dataset = assemble_feature_matrix(bars)

    # Strictly forbidden column names
    forbidden = [
        "target_return",
        "target_direction",
        "target_binary",
        "next_close",
        "next_timestamp",
    ]
    for col in forbidden:
        assert col not in dataset.X.columns
        assert col in dataset.df.columns  # preserved in full df for auditing


def test_trend_confirmation_timing_in_feature_matrix():
    """Verify trend_regime_encoded uses strictly point-in-time confirmed pivots."""
    bars = _create_synthetic_series(10)
    dataset = assemble_feature_matrix(bars)

    # First few bars have insufficient swings (k=2 requires at least 5 bars for 1 swing)
    # So trend_regime_encoded must be NaN
    assert pd.isna(dataset.X.loc[0, "trend_regime_encoded"])
    assert pd.isna(dataset.X.loc[2, "trend_regime_encoded"])


def test_stable_row_counts_and_deterministic_results():
    """Verify that assembling the feature matrix repeatedly produces identical results."""
    bars = _create_synthetic_series(25)
    ds1 = assemble_feature_matrix(bars)
    ds2 = assemble_feature_matrix(bars)

    assert ds1.total_rows == ds2.total_rows == 25
    assert ds1.labeled_rows == ds2.labeled_rows == 24
    assert ds1.unlabeled_rows == ds2.unlabeled_rows == 1
    pd.testing.assert_frame_equal(ds1.X, ds2.X)
    pd.testing.assert_series_equal(ds1.y, ds2.y)


def test_empty_and_insufficient_input():
    """Verify that an empty input produces an empty FeatureMatrixDataset without crashing."""
    dataset = assemble_feature_matrix([])
    assert dataset.total_rows == 0
    assert dataset.labeled_rows == 0
    assert dataset.unlabeled_rows == 0
    assert dataset.X.empty
    assert list(dataset.X.columns) == FEATURE_COLUMNS


def test_get_labeled_dataset_accounting():
    """Verify get_labeled_dataset row accounting and optional warmup filtering."""
    bars = _create_synthetic_series(25)
    dataset = assemble_feature_matrix(bars)

    # 1. Without dropping warmup: only drops final unlabeled row
    X_lab, y_lab, audit1 = dataset.get_labeled_dataset(drop_incomplete_warmup=False)
    assert len(X_lab) == len(y_lab) == 24
    assert audit1["initial_total_rows"] == 25
    assert audit1["unlabeled_final_rows_excluded"] == 1
    assert audit1["incomplete_warmup_rows_excluded"] == 0
    assert audit1["final_retained_rows"] == 24

    # 2. With dropping warmup: drops rows where MACD / Bollinger / ATR are un-warmed
    X_clean, y_clean, audit2 = dataset.get_labeled_dataset(drop_incomplete_warmup=True)
    assert audit2["incomplete_warmup_rows_excluded"] > 0
    assert audit2["final_retained_rows"] == len(X_clean) == len(y_clean)
    assert not X_clean.isna().any().any()  # strictly zero NaNs in clean slice


def test_compatibility_with_pipeline_result():
    """Verify assemble_feature_matrix accepts MarketDataPipelineResult directly."""
    bars = _create_synthetic_series(20)
    pipeline_result = process_market_data(bars)
    dataset = assemble_feature_matrix(pipeline_result)

    assert dataset.total_rows == 20
    assert dataset.labeled_rows == 19
    assert dataset.unlabeled_rows == 1
    assert dataset.symbol == pipeline_result.symbol


def test_encoders():
    """Verify categorical encoders map expected values and handle invalid/None."""
    assert encode_candle_direction("bullish") == 1.0
    assert encode_candle_direction("bearish") == -1.0
    assert encode_candle_direction("neutral") == 0.0
    assert np.isnan(encode_candle_direction(None))
    assert np.isnan(encode_candle_direction("invalid"))

    assert encode_trend_regime("UPTREND") == 1.0
    assert encode_trend_regime("DOWNTREND") == -1.0
    assert encode_trend_regime("SIDEWAYS") == 0.0
    assert np.isnan(encode_trend_regime(None))
    assert np.isnan(encode_trend_regime("unknown"))
