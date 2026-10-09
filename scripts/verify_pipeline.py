"""Real-Data Verification Script for Historical Market Data Pipeline & Visualizer.

Proves the complete end-to-end Phase 1/Phase 2 data pipeline:
Historical Collector (YFinanceProvider)
        ↓
Data Cleaner (clean_market_data)
        ↓
Feature Layer (compute_market_returns)
        ↓
Market Visualizer (generate_market_charts)

Executes on live/cached BHARTIARTL.NS data and generates publication-quality
closing price and daily return charts saved to data/processed/charts/.
"""

from datetime import datetime
from pathlib import Path
import sys

# Attempt to configure UTF-8 encoding on Windows if supported
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
from app.market.visualizer import generate_market_charts


def _get_currency_symbol() -> str:
    """Determine currency symbol, falling back to 'INR' if console cannot encode rupee."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "\u20b9".encode(encoding)
        return "\u20b9"
    except (UnicodeEncodeError, LookupError):
        return "INR"


def main() -> int:
    print("==================================================")
    print("DAY 7 REAL-DATA PIPELINE & VISUALIZER VERIFICATION")
    print("==================================================")

    symbol = "BHARTIARTL"
    start_dt = datetime(2026, 9, 1)
    end_dt = datetime(2026, 9, 8)
    provider = YFinanceProvider()

    print(f"Step 1: Running market data pipeline for {symbol} [{start_dt.date()} to {end_dt.date()}]...")
    try:
        pipeline_result = run_market_data_pipeline(
            symbol=symbol,
            start_date=start_dt,
            end_date=end_dt,
            provider=provider,
            interval="1d",
            rolling_return_windows=(3, 5),
            volatility_windows=(5,),
        )
    except Exception as exc:
        print(f"ERROR: Market data pipeline execution failed: {exc}", file=sys.stderr)
        return 1

    # Explicit validation checks
    if pipeline_result.is_empty:
        print("ERROR: Pipeline produced 0 valid cleaned records.", file=sys.stderr)
        return 1

    raw_count = len(pipeline_result.raw_records)
    clean_count = len(pipeline_result.cleaned_records)
    feat_count = len(pipeline_result.features)

    print(f"  [OK] Raw bars collected:     {raw_count}")
    print(f"  [OK] Cleaned bars produced:  {clean_count}")
    print(f"  [OK] Feature bars produced:  {feat_count}")

    if clean_count != feat_count:
        print(f"ERROR: Cleaned count ({clean_count}) != Feature count ({feat_count})", file=sys.stderr)
        return 1

    summary = pipeline_result.cleaning_summary
    print("\nStep 2: Pipeline Cleaning Audit Summary:")
    print(f"  Input Count:                {summary.input_count}")
    print(f"  Output Count:               {summary.output_count}")
    print(f"  Missing Records:            {summary.missing_records_count}")
    print(f"  Invalid Records:            {summary.invalid_records_count}")
    print(f"  Identical Duplicates:       {summary.identical_duplicates_count}")
    print(f"  Conflicting Duplicates:     {summary.conflicting_duplicates_count}")
    print(f"  Total Rejected:             {summary.rejected_count}")

    print("\nStep 3: Generating historical market charts...")
    charts_output_dir = project_root / "data" / "processed" / "charts"
    try:
        chart_paths = generate_market_charts(
            features=pipeline_result.features,
            output_dir=charts_output_dir,
            symbol=symbol,
        )
    except Exception as exc:
        print(f"ERROR: Chart generation failed: {exc}", file=sys.stderr)
        return 1

    price_chart = chart_paths.get("price_chart")
    returns_chart = chart_paths.get("returns_chart")

    # Explicit checks on generated charts
    if not price_chart or not price_chart.exists() or price_chart.stat().st_size == 0:
        print(f"ERROR: Price chart missing or empty at {price_chart}", file=sys.stderr)
        return 1

    if not returns_chart or not returns_chart.exists() or returns_chart.stat().st_size == 0:
        print(f"ERROR: Returns chart missing or empty at {returns_chart}", file=sys.stderr)
        return 1

    print("  [OK] Closing price chart generated:")
    print(f"       -> {price_chart} ({price_chart.stat().st_size:,} bytes)")
    print("  [OK] Daily percentage returns chart generated:")
    print(f"       -> {returns_chart} ({returns_chart.stat().st_size:,} bytes)")

    # Display session metrics with aligned table widths
    curr = _get_currency_symbol()
    close_header = f"Close ({curr})"
    divider = "-" * 85
    print("\nStep 4: Historical Session Feature Inspection:")
    print(divider)
    print(
        f"{'Date':<12} {close_header:<12} {'Daily Ret':<14} {'Roll Ret 3d':<14} {'Roll Ret 5d':<14} {'Vol 5d (raw)':<14}"
    )
    print(divider)

    for f in pipeline_result.features:
        d_str = f.timestamp.strftime("%Y-%m-%d")
        c_str = f"{f.close:.2f}"
        dr_str = f"{f.daily_return:+.4%}" if f.daily_return is not None else "None (first)"
        r3_str = f"{f.rolling_return_3d:+.4%}" if f.rolling_return_3d is not None else "None (<3d)"
        r5_str = f"{f.rolling_return_5d:+.4%}" if f.rolling_return_5d is not None else "None (<5d)"
        v5_str = f"{f.volatility_5d:.6f}" if f.volatility_5d is not None else "None (<5d)"
        print(f"{d_str:<12} {c_str:<12} {dr_str:<14} {r3_str:<14} {r5_str:<14} {v5_str:<14}")

    print(divider)
    print("\n[SUCCESS] Day 7 market data pipeline and visualization verified on real BHARTIARTL.NS data.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
