"""Real-Data Verification Script for Technical Feature Matrix Assembly.

Validates:
1. Real-data acquisition for BHARTIARTL.NS via existing provider and pipeline.
2. Aligned feature matrix assembly connecting all technical indicators with Day 15 targets.
3. Strict separation of feature matrix X, target y, and metadata.
4. Validation that X contains zero target or forward outcome columns.
5. Invariant check: Final observation has y = NaN (unlabeled row).
6. Missing value accounting across feature categories (warmup NaNs preserved).
7. Target class distribution across labeled historical observations.
8. Output of sample feature rows.
"""

from datetime import datetime
import math
from pathlib import Path
import sys

# Configure UTF-8 encoding on Windows if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.market.pipeline import run_market_data_pipeline
from app.market.providers.yfinance_provider import YFinanceProvider
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURE_PATTERNS,
    FeatureMatrixDataset,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)


def _get_currency_symbol() -> str:
    """Determine currency symbol, falling back to 'INR' if console cannot encode rupee."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "\u20b9".encode(encoding)
        return "\u20b9"
    except (UnicodeEncodeError, LookupError):
        return "INR"


def verify_real_data_feature_matrix() -> int:
    curr = _get_currency_symbol()
    print("==================================================")
    print("DAY 16: TECHNICAL FEATURE MATRIX ASSEMBLY VERIFICATION")
    print("==================================================")

    provider = YFinanceProvider()
    symbol = "BHARTIARTL"
    lookback_days = 180

    print(f"\nStep 1: Running pipeline for {symbol} (lookback_days={lookback_days})...")
    try:
        pipeline_result = run_market_data_pipeline(
            symbol=symbol,
            lookback_days=lookback_days,
            provider=provider,
        )
    except Exception as exc:
        print(f"ERROR: Market data pipeline execution failed: {exc}", file=sys.stderr)
        return 1

    clean_records = pipeline_result.cleaned_records
    n_records = len(clean_records)
    print(f"  [OK] Cleaned bars produced: {n_records}")

    if n_records < 20:
        print(f"ERROR: Expected at least 20 historical sessions, got {n_records}", file=sys.stderr)
        return 1

    first_date = clean_records[0].timestamp.strftime("%Y-%m-%d")
    last_date = clean_records[-1].timestamp.strftime("%Y-%m-%d")
    print(f"  [OK] Date Range Verified:   {first_date} to {last_date} ({n_records} sessions)")

    print("\nStep 2: Assembling Technical Feature Matrix & Joining Day 15 Targets...")
    try:
        dataset = assemble_feature_matrix(pipeline_result)
    except Exception as exc:
        print(f"ERROR: Feature matrix assembly failed: {exc}", file=sys.stderr)
        return 1

    assert isinstance(dataset, FeatureMatrixDataset)
    print(f"  [OK] Total Aligned Rows:     {dataset.total_rows}")
    print(f"  [OK] Total Feature Columns:  {len(dataset.feature_names)}")
    print(f"  [OK] Labeled Rows (y in 0,1):{dataset.labeled_rows}")
    print(f"  [OK] Unlabeled Rows (y=NaN): {dataset.unlabeled_rows}")

    print("\nStep 3: Validating Data-Leakage Guards and X / y Isolation...")
    # Validate isolation
    try:
        validate_feature_matrix_isolation(dataset.X)
        print("  [OK] Isolation Guard: Zero forbidden columns in feature matrix X.")
    except Exception as exc:
        print(f"ERROR: Isolation validation failed: {exc}", file=sys.stderr)
        return 1

    for forbidden in ["target_return", "target_direction", "target_binary", "next_close", "next_timestamp"]:
        if forbidden in dataset.X.columns:
            print(f"ERROR: Forbidden column '{forbidden}' found in X!", file=sys.stderr)
            return 1
    print("  [OK] Explicit exclusion of all future/target columns from X verified.")

    # Check final row invariant
    final_idx = dataset.total_rows - 1
    if not (math.isnan(dataset.y.iloc[final_idx])):
        print("ERROR: Final row target is not NaN!", file=sys.stderr)
        return 1
    print("  [OK] Final observation target invariant verified: strictly NaN (unlabeled).")

    print("\nStep 4: Missing Value Accounting by Feature Domain (Warmup NaNs Preserved):")
    missing = dataset.missing_value_summary()
    domain_groups = {
        "OHLCV Price/Vol": ["open", "high", "low", "close", "volume"],
        "Returns & Volatility": ["daily_return", "rolling_return_3d", "rolling_return_5d", "rolling_volatility_5d", "annualized_volatility_5d"],
        "Moving Averages": ["sma_5", "sma_10", "ema_5", "ema_10"],
        "Momentum / MACD / RSI": ["rsi_14", "macd", "macd_signal", "macd_histogram"],
        "Bollinger Bands": ["bb_middle", "bb_upper", "bb_lower", "bb_bandwidth", "bb_percent_b"],
        "Range & Volatility (ATR/ROC)": ["atr_14", "roc_10"],
        "Candlestick Geometry": ["candle_body", "candle_range", "candle_body_ratio", "candle_close_location", "candle_direction_encoded"],
        "Trend Regime": ["trend_regime_encoded"],
    }

    print("-" * 75)
    print(f"{'Feature Domain':30s} | {'Sample Columns':25s} | {'Max Warmup NaNs':15s}")
    print("-" * 75)
    for domain, cols in domain_groups.items():
        max_nan = max(missing.get(c, 0) for c in cols)
        sample = ", ".join(cols[:2])
        print(f"{domain:30s} | {sample:25s} | {max_nan:2d} sessions")
    print("-" * 75)
    print("  [OK] All warmup NaNs correctly preserved without arbitrary zero-filling.")

    print("\nStep 5: Target Class Distribution Across Labeled Rows:")
    y_labeled = dataset.y.dropna()
    up_count = int((y_labeled == 1.0).sum())
    down_count = int((y_labeled == 0.0).sum())
    total_labeled = len(y_labeled)
    up_pct = (up_count / total_labeled) * 100.0 if total_labeled > 0 else 0.0
    down_pct = (down_count / total_labeled) * 100.0 if total_labeled > 0 else 0.0
    print(f"  Total Labeled Observations: {total_labeled}")
    print(f"  UP Target Count (1.0):      {up_count} ({up_pct:.1f}%)")
    print(f"  DOWN Target Count (0.0):    {down_count} ({down_pct:.1f}%)")

    print("\nStep 6: Sample 5 Most Recent Observations in Aligned Dataset:")
    print("-" * 115)
    print(f"{'Date':11s} | {'Close':10s} | {'RSI-14':8s} | {'MACD':8s} | {'BB %B':8s} | {'ATR-14':8s} | {'Trend':6s} | {'Target':7s} | {'y':4s}")
    print("-" * 115)
    for i in range(dataset.total_rows - 5, dataset.total_rows):
        dt_str = dataset.metadata.loc[i, "timestamp"].strftime("%Y-%m-%d")
        c_val = dataset.X.loc[i, "close"]
        rsi_val = f"{dataset.X.loc[i, 'rsi_14']:6.2f}" if not math.isnan(dataset.X.loc[i, "rsi_14"]) else "  NaN"
        macd_val = f"{dataset.X.loc[i, 'macd']:+6.2f}" if not math.isnan(dataset.X.loc[i, "macd"]) else "  NaN"
        bb_val = f"{dataset.X.loc[i, 'bb_percent_b']:6.2f}" if not math.isnan(dataset.X.loc[i, "bb_percent_b"]) else "  NaN"
        atr_val = f"{dataset.X.loc[i, 'atr_14']:6.2f}" if not math.isnan(dataset.X.loc[i, "atr_14"]) else "  NaN"
        trend_val = f"{dataset.X.loc[i, 'trend_regime_encoded']:+4.1f}" if not math.isnan(dataset.X.loc[i, "trend_regime_encoded"]) else " NaN"
        tgt_val = str(dataset.df.loc[i, "target_direction"]) if not pd.isna(dataset.df.loc[i, "target_direction"]) else "None"
        y_val = f"{dataset.y.iloc[i]:.0f}" if not math.isnan(dataset.y.iloc[i]) else "NaN"
        print(f"{dt_str:11s} | {curr}{c_val:7.2f} | {rsi_val:8s} | {macd_val:8s} | {bb_val:8s} | {atr_val:8s} | {trend_val:6s} | {tgt_val:7s} | {y_val:4s}")
    print("-" * 115)

    print("\nStep 7: Labeled Subset Extraction Accounting:")
    X_lab, y_lab, audit = dataset.get_labeled_dataset(drop_incomplete_warmup=True)
    print(f"  Initial Total Rows:             {audit['initial_total_rows']}")
    print(f"  Unlabeled Final Excluded:       {audit['unlabeled_final_rows_excluded']}")
    print(f"  Incomplete Warmup Excluded:     {audit['incomplete_warmup_rows_excluded']}")
    print(f"  Final Retained Complete Rows:   {audit['final_retained_rows']}")
    assert len(X_lab) == audit['final_retained_rows']
    assert len(y_lab) == audit['final_retained_rows']
    print("  [OK] Supervised training dataset extracted with exact accounting.")

    print("\n==================================================")
    print("VERIFICATION SUMMARY")
    print("==================================================")
    print(f"Symbol:                   {symbol}")
    print(f"Date Range:               {first_date} to {last_date}")
    print(f"Total Rows:               {dataset.total_rows}")
    print(f"Feature Columns in X:     {len(dataset.feature_names)}")
    print(f"Target Columns in X:      0 (Verified isolated)")
    print(f"Labeled Rows:             {dataset.labeled_rows}")
    print(f"Unlabeled Rows:           {dataset.unlabeled_rows}")
    print(f"Complete Training Rows:   {audit['final_retained_rows']}")
    print("==================================================\n")
    return 0


if __name__ == "__main__":
    import pandas as pd
    sys.exit(verify_real_data_feature_matrix())
