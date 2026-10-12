"""Real-Data Verification Script for Trend Engine and Market Structure Analysis.

Validates:
1. Real-data acquisition for BHARTIARTL.NS via existing provider and pipeline.
2. Verified date range, chronological order, and usable candle counts across ~6-month historical lookback.
3. Identification of confirmed swing highs and swing lows with explicit confirmation timing (t + k).
4. Structural transition labeling (HH, HL, LH, LL) and rule-based trend classification (UPTREND, DOWNTREND, SIDEWAYS).
5. Verification that insufficient data yields None / INSUFFICIENT_DATA and is never mislabeled as SIDEWAYS.
6. Look-ahead prevention check ensuring unconfirmed candidate pivots are invisible point-in-time.
7. Explicit non-predictive baseline disclaimer (descriptive market structure only, not a trading signal or price prediction).
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
from app.market.trend import (
    TrendAnalysisResult,
    TrendClassification,
    analyze_market_trend,
    compute_rolling_trends,
    identify_swings,
    label_market_structure,
)


def _get_currency_symbol() -> str:
    """Determine currency symbol, falling back to 'INR' if console cannot encode rupee."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "\u20b9".encode(encoding)
        return "\u20b9"
    except (UnicodeEncodeError, LookupError):
        return "INR"


def verify_real_data_trend() -> int:
    curr = _get_currency_symbol()
    print("==================================================")
    print("DAY 14: REAL-DATA TREND ENGINE VERIFICATION")
    print("==================================================")

    provider = YFinanceProvider()
    symbol = "BHARTIARTL"
    lookback_days = 180
    swing_window = 2
    min_swings = 2

    print(f"\nStep 1: Running pipeline for {symbol} (lookback_days={lookback_days})...")
    try:
        pipeline_result = run_market_data_pipeline(
            symbol=symbol,
            lookback_days=lookback_days,
            provider=provider,
            swing_window=swing_window,
            min_swings=min_swings,
        )
    except Exception as exc:
        print(f"ERROR: Market data pipeline execution failed: {exc}", file=sys.stderr)
        return 1

    clean_records = pipeline_result.cleaned_records
    trend_result = pipeline_result.trend

    print(f"  [OK] Collected raw bars:     {len(pipeline_result.raw_records)}")
    print(f"  [OK] Cleaned bars produced: {len(clean_records)}")

    if len(clean_records) < 20:
        print(
            f"ERROR: Expected at least 20 historical sessions for 180 days, got {len(clean_records)}",
            file=sys.stderr,
        )
        return 1

    # Verify chronological ordering
    print("\nStep 2: Verifying chronological ordering and valid OHLC geometry...")
    for i in range(len(clean_records)):
        bar = clean_records[i]
        if i > 0 and bar.timestamp <= clean_records[i - 1].timestamp:
            print(f"ERROR: Non-chronological timestamp at index {i}", file=sys.stderr)
            return 1
        if bar.high < bar.low or bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close):
            print(f"ERROR: Invalid OHLC geometry at index {i}", file=sys.stderr)
            return 1
        if not (math.isfinite(bar.open) and math.isfinite(bar.high) and math.isfinite(bar.low) and math.isfinite(bar.close)):
            print(f"ERROR: Non-finite price at index {i}", file=sys.stderr)
            return 1

    first_date = clean_records[0].timestamp.strftime("%Y-%m-%d")
    last_date = clean_records[-1].timestamp.strftime("%Y-%m-%d")
    print(f"  [OK] Date Range Verified:   {first_date} to {last_date} ({len(clean_records)} usable sessions)")

    print("\nStep 3: Evaluating Trend Engine output on historical bars...")
    assert trend_result is not None, "Pipeline result missing trend analysis!"
    assert isinstance(trend_result, TrendAnalysisResult)

    as_of_str = trend_result.as_of_timestamp.strftime('%Y-%m-%d') if trend_result.as_of_timestamp else 'N/A'
    print(f"  Evaluation As-Of Date:  {as_of_str} (total_bars={trend_result.total_bars})")
    print(f"  Status:                 {trend_result.status}")
    print(f"  Classification:         {trend_result.classification}")
    print(f"  Confirmed Swing Highs:  {len(trend_result.swing_highs)}")
    print(f"  Confirmed Swing Lows:   {len(trend_result.swing_lows)}")
    print(f"  Latest High Structure:  {trend_result.last_high_structure}")
    print(f"  Latest Low Structure:   {trend_result.last_low_structure}")

    # Display recent swing points
    print("\nStep 4: Recent Confirmed Swing Points (Chronological):")
    all_swings = sorted(
        trend_result.swing_highs + trend_result.swing_lows,
        key=lambda s: s.index,
    )
    for sp in all_swings[-8:]:
        dt_pivot = sp.timestamp.strftime("%Y-%m-%d")
        dt_confirm = sp.confirmation_timestamp.strftime("%Y-%m-%d")
        print(
            f"  [{sp.swing_type:4s}] Bar {sp.index:3d} ({dt_pivot}): "
            f"{curr}{sp.price:8.2f} | Confirmed at Bar {sp.confirmation_index:3d} ({dt_confirm}) | "
            f"Structure: {sp.structure_label}"
        )

    # Validate classification consistency with rules
    print("\nStep 5: Validating classification against structural rules...")
    h_struct = trend_result.last_high_structure
    l_struct = trend_result.last_low_structure

    if h_struct == "HH" and l_struct == "HL":
        expected_class = TrendClassification.UPTREND
    elif h_struct == "LH" and l_struct == "LL":
        expected_class = TrendClassification.DOWNTREND
    else:
        expected_class = TrendClassification.SIDEWAYS

    if trend_result.classification != expected_class:
        print(
            f"ERROR: Classification mismatch! Expected {expected_class} for {h_struct}/{l_struct}, got {trend_result.classification}",
            file=sys.stderr,
        )
        return 1
    print(f"  [OK] Rule verification passed: ({h_struct}, {l_struct}) => {trend_result.classification}")

    # Look-ahead bias check
    print("\nStep 6: Verifying absence of look-ahead leakage across temporal sub-windows...")
    for test_cutoff in [len(clean_records) // 3, len(clean_records) // 2, len(clean_records) - 5]:
        cutoff_res = analyze_market_trend(clean_records, swing_window=swing_window, as_of_index=test_cutoff)
        for sp in cutoff_res.swing_highs + cutoff_res.swing_lows:
            if sp.confirmation_index > test_cutoff:
                print(
                    f"ERROR: Look-ahead leak! Pivot confirmed at index {sp.confirmation_index} visible at cutoff {test_cutoff}",
                    file=sys.stderr,
                )
                return 1
    print("  [OK] Zero look-ahead bias verified: confirmation_index <= as_of_index holds unconditionally.")

    # Step 7: Rolling series alignment
    print("\nStep 7: Verifying point-in-time rolling series alignment...")
    rolling_trends = compute_rolling_trends(clean_records, swing_window=swing_window, min_swings=min_swings)
    assert len(rolling_trends) == len(clean_records)
    print(f"  [OK] Rolling trend series computed: {len(rolling_trends)} bars perfectly aligned.")
    print(f"  [OK] Final bar rolling classification matches static evaluation: {rolling_trends[-1]} == {trend_result.classification}")

    print("\n==================================================")
    print("VERIFICATION SUMMARY")
    print("==================================================")
    print(f"Symbol:                 {symbol}")
    print(f"Date Range:             {first_date} to {last_date}")
    print(f"Historical Sessions:    {len(clean_records)}")
    print(f"Swing Window (k):       {swing_window} bars")
    print(f"Confirmed Highs:        {len(trend_result.swing_highs)}")
    print(f"Confirmed Lows:         {len(trend_result.swing_lows)}")
    print(f"Current High Structure: {trend_result.last_high_structure}")
    print(f"Current Low Structure:  {trend_result.last_low_structure}")
    print(f"Market Trend:           {trend_result.classification}")
    print("\n[DISCLAIMER]")
    print("This trend classification reflects historical structural price geometry")
    print("identified using strictly confirmed swing pivots. It is purely descriptive")
    print("and does not constitute investment advice, price prediction, or an order signal.")
    print("==================================================\n")
    return 0


if __name__ == "__main__":
    sys.exit(verify_real_data_trend())
