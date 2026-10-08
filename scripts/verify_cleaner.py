"""Real-Data Verification Script for Historical Market Data Cleaner.

Proves the end-to-end pipeline:
Day 4 YFinanceProvider -> Raw MarketOHLCV -> Day 5 clean_market_data -> Cleaned MarketOHLCV.
Verifies audit summary metrics, deduplication checks, and chronological sorting
against real market observations for BHARTIARTL.NS.
"""

from datetime import datetime
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.schemas import MarketOHLCV
from app.market.cleaner import clean_market_data
from app.market.providers.yfinance_provider import YFinanceProvider


def main() -> int:
    print("==================================================")
    print("DAY 5 REAL-DATA CLEANING PIPELINE VERIFICATION")
    print("==================================================")

    provider = YFinanceProvider()
    symbol = "BHARTIARTL"
    start_dt = datetime(2026, 9, 1)
    end_dt = datetime(2026, 9, 8)

    print(f"Step 1: Collecting real data via {provider.name} for {symbol}...")
    try:
        raw_records = provider.fetch_historical_ohlcv(
            symbol=symbol,
            start_date=start_dt,
            end_date=end_dt,
            interval="1d",
        )
    except Exception as exc:
        print(f"ERROR: Provider collection failed: {exc}")
        return 1

    print(f"  [OK] Collected {len(raw_records)} raw canonical bars from provider.")

    print("\nStep 2: Passing raw bars into clean_market_data()...")
    cleaning_result = clean_market_data(raw_records)
    summary = cleaning_result.summary

    print("  Cleaning Audit Summary:")
    print(f"    Input Count:                {summary.input_count}")
    print(f"    Output Count:               {summary.output_count}")
    print(f"    Missing Records Rejected:   {summary.missing_records_count}")
    print(f"    Invalid Records Rejected:   {summary.invalid_records_count}")
    print(f"    Identical Duplicates:       {summary.identical_duplicates_count}")
    print(f"    Conflicting Duplicates:     {summary.conflicting_duplicates_count}")
    print(f"    Total Rejected:             {summary.rejected_count}")
    print(f"    Chronologically Sorted:     {summary.is_sorted}")

    # Assert integrity invariants
    assert summary.input_count == len(raw_records), "Input count mismatch"
    assert summary.output_count == len(cleaning_result.records), "Output count mismatch"
    assert summary.is_sorted is True, "Output must be chronologically sorted"
    assert summary.output_count == summary.input_count - summary.rejected_count, "Audit count equation violated"

    for r in cleaning_result.records:
        assert isinstance(r, MarketOHLCV)
        assert r.symbol == "BHARTIARTL"
        assert str(r.timestamp.tzinfo) == "Asia/Kolkata"

    print("\n[SUCCESS] End-to-end cleaning pipeline verified against real BHARTIARTL market data.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
