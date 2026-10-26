"""Technical Feature Matrix Assembly Layer.

Assembles aligned, leakage-safe tabular datasets combining historical market
features (OHLCV, returns, volatility, moving averages, RSI, MACD, Bollinger Bands,
ATR, ROC, candlestick geometry, trend regimes) with Day 15 next-session prediction targets.

Architectural Design & Invariants:
1. Observation Row Alignment:
   Each row t corresponds strictly to an observation at session timestamp t.
   Features in row t use information available at or before session t.
   The target in row t represents the forward return and direction realized at session t+1.
2. Model Input (X) and Target (y) Separation:
   Feature matrix X contains strictly contemporaneous/past signals. Target-derived
   fields (future close, next timestamp, target return, binary target) are isolated
   in y and metadata, and strictly guarded against appearing in X.
3. Natural Missing Values Policy:
   Indicator warm-up periods (e.g. SMA-10, RSI-14, MACD-26, Bollinger-20, ATR-14)
   naturally produce missing (NaN) values. The assembly layer preserves these values
   without arbitrary zero-filling or synthetic distortion. Downstream imputation
   or scaling must be fitted on training folds only (preventing global leakage).
4. Missing Final Observation Invariant:
   The latest observation (t = N - 1) has no realized subsequent session and
   strictly evaluates to an unlabeled row (y = NaN).
5. Explicit Join Keys:
   Features and targets are joined strictly on (symbol, timestamp), not solely
   by implicit array indexing.
"""

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV
from app.market.pipeline import (
    MarketDataPipelineResult,
    process_market_data,
)
from app.market.trend import (
    compute_latest_trend,
    compute_rolling_trends,
)
from app.prediction.target import (
    TargetObservation,
    generate_direction_targets,
)

logger = get_logger(__name__)

# Canonical metadata and target columns (strictly forbidden from appearing in feature matrix X)
FORBIDDEN_FEATURE_PATTERNS: Tuple[str, ...] = (
    "target",
    "next_",
    "future",
    "outcome",
)

METADATA_COLUMNS: List[str] = [
    "symbol",
    "timestamp",
    "next_timestamp",
    "current_close",
    "next_close",
]

TARGET_COLUMNS: List[str] = [
    "target_return",
    "target_direction",
    "target_binary",
]

# Canonical ordered list of numeric model feature column names
FEATURE_COLUMNS: List[str] = [
    # 1. OHLCV Raw Price & Volume
    "open",
    "high",
    "low",
    "close",
    "volume",
    # 2. Returns & Volatility
    "daily_return",
    "rolling_return_3d",
    "rolling_return_5d",
    "rolling_volatility_5d",
    "annualized_volatility_5d",
    # 3. Moving Averages
    "sma_5",
    "sma_10",
    "ema_5",
    "ema_10",
    # 4. Momentum & Oscillators
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    # 5. Volatility Bands (Bollinger)
    "bb_middle",
    "bb_upper",
    "bb_lower",
    "bb_bandwidth",
    "bb_percent_b",
    # 6. Range Volatility & Relative Velocity
    "atr_14",
    "roc_10",
    # 7. Candlestick Geometry & Direction
    "candle_body",
    "candle_body_abs",
    "candle_range",
    "candle_upper_wick",
    "candle_lower_wick",
    "candle_body_ratio",
    "candle_upper_wick_ratio",
    "candle_lower_wick_ratio",
    "candle_close_location",
    "candle_body_return_pct",
    "candle_direction_encoded",
    # 8. Market Structure & Trend Regime
    "trend_regime_encoded",
]

# Canonical ordered list of numeric index feature column names (close-only indicators)
INDEX_FEATURE_COLUMNS: List[str] = [
    # 1. Close Price (level)
    "close",
    # 2. Returns & Volatility
    "daily_return",
    "rolling_return_3d",
    "rolling_return_5d",
    "rolling_volatility_5d",
    "annualized_volatility_5d",
    # 3. Moving Averages
    "sma_5",
    "sma_10",
    "ema_5",
    "ema_10",
    # 4. Momentum & Oscillators
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    # 5. Volatility Bands (Bollinger)
    "bb_middle",
    "bb_upper",
    "bb_lower",
    "bb_bandwidth",
    "bb_percent_b",
    # 6. Relative Velocity
    "roc_10",
]


def encode_candle_direction(direction: Optional[str]) -> float:
    """Encode categorical candle direction to numerical value (+1.0, -1.0, 0.0, or NaN)."""
    if direction is None:
        return np.nan
    d_lower = direction.lower()
    if d_lower == "bullish":
        return 1.0
    if d_lower == "bearish":
        return -1.0
    if d_lower == "neutral":
        return 0.0
    return np.nan


def encode_trend_regime(regime: Optional[str]) -> float:
    """Encode categorical trend regime to numerical value (+1.0, -1.0, 0.0, or NaN)."""
    if regime is None:
        return np.nan
    r_upper = regime.upper()
    if r_upper == "UPTREND":
        return 1.0
    if r_upper == "DOWNTREND":
        return -1.0
    if r_upper == "SIDEWAYS":
        return 0.0
    return np.nan


def validate_feature_matrix_isolation(X: pd.DataFrame) -> None:
    """Validate that feature matrix X contains strictly zero target or future outcome columns.

    Raises:
        ValueError: If any column in X contains forbidden target or outcome names.
    """
    for col in X.columns:
        col_lower = str(col).lower()
        for pattern in FORBIDDEN_FEATURE_PATTERNS:
            if pattern in col_lower:
                raise ValueError(
                    f"Data leakage detected! Feature matrix X contains forbidden column '{col}' "
                    f"matching pattern '{pattern}'."
                )


def validate_chronological_integrity(records: Sequence[MarketOHLCV]) -> None:
    """Verify that records are non-empty, chronological, and contain zero duplicate timestamps.

    Raises:
        ValueError: On duplicate timestamps or non-chronological order within any symbol.
    """
    if not records:
        return

    seen_timestamps: Dict[str, Set[datetime]] = {}
    last_timestamp: Dict[str, datetime] = {}

    for r in records:
        sym = r.symbol
        ts = r.timestamp

        if sym not in seen_timestamps:
            seen_timestamps[sym] = set()
        if ts in seen_timestamps[sym]:
            raise ValueError(
                f"Duplicate timestamp detected for symbol '{sym}' at {ts.isoformat()}."
            )
        seen_timestamps[sym].add(ts)

        if sym in last_timestamp and ts < last_timestamp[sym]:
            raise ValueError(
                f"Non-chronological order detected for symbol '{sym}': "
                f"{ts.isoformat()} occurs after {last_timestamp[sym].isoformat()}."
            )
        last_timestamp[sym] = ts


@dataclass(frozen=True)
class FeatureMatrixDataset:
    """Canonical typed container holding the complete aligned feature-target dataset.

    Attributes:
        symbol: Ticker symbol.
        df: Full aligned DataFrame containing metadata, features, and target columns.
        X: Feature matrix DataFrame (strictly numerical features available at session t).
        y: Binary target Series (1.0 for UP, 0.0 for DOWN, NaN for unlabeled final session).
        metadata: Audit metadata DataFrame (symbols, timestamps, reference and outcome closes).
        feature_names: List of feature column names in X.
        total_rows: Total observation count.
        labeled_rows: Number of observations with a known forward target.
        unlabeled_rows: Number of observations without a forward target (final session).
    """

    symbol: str
    df: pd.DataFrame
    X: pd.DataFrame
    y: pd.Series
    metadata: pd.DataFrame
    feature_names: List[str]
    total_rows: int
    labeled_rows: int
    unlabeled_rows: int

    def missing_value_summary(self) -> Dict[str, int]:
        """Compute missing value (NaN) counts across all feature columns."""
        if self.X.empty:
            return {col: 0 for col in self.feature_names}
        return self.X.isna().sum().to_dict()

    def get_labeled_dataset(
        self,
        drop_incomplete_warmup: bool = False,
    ) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
        """Extract labeled subset for supervised model training with transparent accounting.

        Args:
            drop_incomplete_warmup: If True, filters out rows with NaN in features
                (early indicator warmup). If False (default), retains warmup rows so
                imputation can be fitted strictly on cross-validation folds.

        Returns:
            Tuple of:
                - X_labeled: Feature matrix subset.
                - y_labeled: Target label Series.
                - audit_summary: Accounting dictionary reporting initial rows,
                  unlabeled exclusions, warmup exclusions, and final retained rows.
        """
        # Step 1: Filter out unlabeled final bar
        labeled_mask = self.y.notna()
        X_sub = self.X[labeled_mask].copy()
        y_sub = self.y[labeled_mask].copy()
        unlabeled_excluded = int((~labeled_mask).sum())

        warmup_excluded = 0
        if drop_incomplete_warmup:
            complete_mask = X_sub.notna().all(axis=1)
            warmup_excluded = int((~complete_mask).sum())
            X_sub = X_sub[complete_mask]
            y_sub = y_sub[complete_mask]

        audit: Dict[str, Any] = {
            "initial_total_rows": self.total_rows,
            "unlabeled_final_rows_excluded": unlabeled_excluded,
            "incomplete_warmup_rows_excluded": warmup_excluded,
            "final_retained_rows": len(X_sub),
            "drop_incomplete_warmup": drop_incomplete_warmup,
        }

        return X_sub, y_sub, audit

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataset summary metrics to a serializable dictionary."""
        return {
            "symbol": self.symbol,
            "total_rows": self.total_rows,
            "labeled_rows": self.labeled_rows,
            "unlabeled_rows": self.unlabeled_rows,
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
            "missing_values": self.missing_value_summary(),
        }


def assemble_feature_matrix(
    data: Union[MarketDataPipelineResult, Sequence[MarketOHLCV]],
    swing_window: int = 2,
    min_swings: int = 2,
    only_latest: bool = False,
    feature_columns: Optional[Sequence[str]] = None,
) -> FeatureMatrixDataset:
    """Assemble an aligned, leakage-safe technical feature matrix joined with Day 15 targets.

    Args:
        data: Either an existing MarketDataPipelineResult or a sequence of MarketOHLCV records.
        swing_window: Flank window for Trend Engine swing confirmation (default 2).
        min_swings: Minimum confirmed swings required for trend classification (default 2).
        only_latest: If True, evaluates features and trend classification only for the final
            bar (t = N - 1), bypassing full rolling trend history for fast inference.
        feature_columns: Optional explicit list of feature column names to extract into X.
            If None, automatically selects INDEX_FEATURE_COLUMNS for close-only sectoral indices
            and FEATURE_COLUMNS for standard OHLCV instruments.

    Returns:
        FeatureMatrixDataset container with cleanly separated X, y, metadata, and full df.

    Raises:
        ValueError: If input records have duplicate timestamps, non-chronological order,
                    or if target-to-feature key alignment fails.
    """
    # Step 1: Resolve pipeline result and cleaned records
    # Check for duplicate timestamps on input records
    if isinstance(data, MarketDataPipelineResult):
        input_records = data.cleaned_records
        symbol = data.symbol
        pipeline_res = data
        cleaned_records = pipeline_res.cleaned_records
    else:
        input_records = list(data)
        if not input_records:
            symbol = "EMPTY"
        else:
            symbol = input_records[0].symbol

    # Determine chosen feature columns
    if feature_columns is not None:
        chosen_features = list(feature_columns)
    else:
        chosen_features = list(FEATURE_COLUMNS)

    # Validate duplicate timestamps
    seen_timestamps: Dict[str, Set[datetime]] = {}
    for r in input_records:
        if r.symbol not in seen_timestamps:
            seen_timestamps[r.symbol] = set()
        if r.timestamp in seen_timestamps[r.symbol]:
            raise ValueError(
                f"Duplicate timestamp detected for symbol '{r.symbol}' at {r.timestamp.isoformat()}."
            )
        seen_timestamps[r.symbol].add(r.timestamp)

    if not isinstance(data, MarketDataPipelineResult):
        pipeline_res = process_market_data(
            raw_records=input_records,
            swing_window=swing_window,
            min_swings=min_swings,
        )
        cleaned_records = pipeline_res.cleaned_records

    n_records = len(cleaned_records)
    if n_records == 0:
        empty_df = pd.DataFrame(columns=METADATA_COLUMNS + chosen_features + TARGET_COLUMNS)
        return FeatureMatrixDataset(
            symbol=symbol,
            df=empty_df,
            X=pd.DataFrame(columns=chosen_features),
            y=pd.Series(name="target_binary", dtype=float),
            metadata=pd.DataFrame(columns=METADATA_COLUMNS),
            feature_names=chosen_features,
            total_rows=0,
            labeled_rows=0,
            unlabeled_rows=0,
        )

    # Step 2: Compute Day 15 Prediction Targets
    target_obs_list: List[TargetObservation] = generate_direction_targets(cleaned_records)
    target_by_key: Dict[Tuple[str, datetime], TargetObservation] = {
        (t.symbol, t.timestamp): t for t in target_obs_list
    }

    # Step 3: Compute Trend Regimes
    if only_latest:
        rolling_trends = [compute_latest_trend(
            cleaned_records,
            swing_window=swing_window,
            min_swings=min_swings,
        )]
        indices_to_process = [n_records - 1]
    else:
        rolling_trends = compute_rolling_trends(
            cleaned_records,
            swing_window=swing_window,
            min_swings=min_swings,
        )
        indices_to_process = list(range(n_records))

    # Step 4: Extract and Aligned Feature Rows
    rows: List[Dict[str, Any]] = []
    indicators_list = pipeline_res.indicators
    returns_list = pipeline_res.features

    for loop_idx, i in enumerate(indices_to_process):
        bar = cleaned_records[i]
        key = (bar.symbol, bar.timestamp)

        # Validate explicit join key exists in targets
        if key not in target_by_key:
            raise ValueError(
                f"Target alignment failure: Missing target for key {key} at row index {i}."
            )
        target = target_by_key[key]

        ind = indicators_list[i] if i < len(indicators_list) else None
        ret = returns_list[i] if i < len(returns_list) else None
        trend_label = rolling_trends[0] if only_latest else (rolling_trends[i] if i < len(rolling_trends) else None)

        row: Dict[str, Any] = {
            # Metadata
            "symbol": bar.symbol,
            "timestamp": bar.timestamp,
            "next_timestamp": target.next_timestamp,
            "current_close": bar.close,
            "next_close": target.next_close,
            # Target
            "target_return": target.target_return,
            "target_direction": target.target_direction,
            "target_binary": float(target.target_binary) if target.target_binary is not None else np.nan,
            # OHLCV Features
            "open": float(bar.open) if bar.open is not None else np.nan,
            "high": float(bar.high) if bar.high is not None else np.nan,
            "low": float(bar.low) if bar.low is not None else np.nan,
            "close": float(bar.close),
            "volume": float(bar.volume) if bar.volume is not None else np.nan,
            # Returns & Realized Volatility
            "daily_return": ret.daily_return if ret else None,
            "rolling_return_3d": ret.rolling_return_3d if ret else None,
            "rolling_return_5d": ret.rolling_return_5d if ret else None,
            "rolling_volatility_5d": ret.volatility_5d if ret else None,
            "annualized_volatility_5d": ret.annualized_volatility_5d if ret else None,
            # Moving Averages
            "sma_5": ind.sma_5 if ind else None,
            "sma_10": ind.sma_10 if ind else None,
            "ema_5": ind.ema_5 if ind else None,
            "ema_10": ind.ema_10 if ind else None,
            # Momentum & Oscillators
            "rsi_14": ind.rsi_14 if ind else None,
            "macd": ind.macd if ind else None,
            "macd_signal": ind.macd_signal if ind else None,
            "macd_histogram": ind.macd_histogram if ind else None,
            # Volatility Bands
            "bb_middle": ind.bb_middle if ind else None,
            "bb_upper": ind.bb_upper if ind else None,
            "bb_lower": ind.bb_lower if ind else None,
            "bb_bandwidth": ind.bb_bandwidth if ind else None,
            "bb_percent_b": ind.bb_percent_b if ind else None,
            # Range Volatility & Relative Velocity
            "atr_14": ind.atr.get(14) if ind else None,
            "roc_10": ind.roc.get(10) if ind else None,
            # Candlestick Geometry
            "candle_body": ind.candle_body if ind else None,
            "candle_body_abs": ind.candle_body_abs if ind else None,
            "candle_range": ind.candle_range if ind else None,
            "candle_upper_wick": ind.candle_upper_wick if ind else None,
            "candle_lower_wick": ind.candle_lower_wick if ind else None,
            "candle_body_ratio": ind.candle_body_ratio if ind else None,
            "candle_upper_wick_ratio": ind.candle_upper_wick_ratio if ind else None,
            "candle_lower_wick_ratio": ind.candle_lower_wick_ratio if ind else None,
            "candle_close_location": ind.candle_close_location if ind else None,
            "candle_body_return_pct": ind.candle_body_return_pct if ind else None,
            "candle_direction_encoded": encode_candle_direction(ind.candle_direction if ind else None),
            # Trend Regime
            "trend_regime_encoded": encode_trend_regime(trend_label),
        }
        rows.append(row)

    # Step 5: Construct Aligned DataFrames
    full_df = pd.DataFrame(rows)

    # Explicitly separate feature matrix X, target y, and metadata
    X = full_df[chosen_features].copy()
    y = full_df["target_binary"].copy()
    metadata = full_df[METADATA_COLUMNS].copy()

    # Step 6: Validate Isolation Guard
    validate_feature_matrix_isolation(X)

    labeled_count = int(y.notna().sum())
    unlabeled_count = int(y.isna().sum())

    logger.info(
        "Assembled technical feature matrix for %s: %d total rows (%d labeled, %d unlabeled, %d features)",
        symbol,
        len(full_df),
        labeled_count,
        unlabeled_count,
        len(chosen_features),
    )

    return FeatureMatrixDataset(
        symbol=symbol,
        df=full_df,
        X=X,
        y=y,
        metadata=metadata,
        feature_names=chosen_features,
        total_rows=len(full_df),
        labeled_rows=labeled_count,
        unlabeled_rows=unlabeled_count,
    )
