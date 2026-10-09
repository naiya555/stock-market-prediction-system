"""Real-Data Verification Script for Returns and Volatility Features.

Validates the complete end-to-end data pipeline:
Day 4 YFinanceProvider -> Day 5 clean_market_data -> Day 6 compute_market_returns.
Verifies daily returns, rolling returns, standard deviation, and rolling volatility
metrics on real cleaned historical bars for BHARTIARTL.NS.
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
from app.market.returns import ReturnFeatures, compute_market_returns


def main() -> int:
    print("==================================================")
    print("DAY 6 REAL-DATA RETURNS & VOLATILITY VERIFICATION")
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

    print(f"  [OK] Collected {len(raw_records)} raw canonical bars.")

    print("\nStep 2: Cleaning historical data via clean_market_data()...")
    cleaning_result = clean_market_data(raw_records)
    clean_records = cleaning_result.records
    print(f"  [OK] Cleaned bars count: {len(clean_records)}")
    assert len(clean_records) > 0, "No cleaned records available"

    print("\nStep 3: Computing Day 6 returns and volatility features...")
    # Rolling windows: 3-session and 5-session rolling returns; 5-session rolling volatility
    features = compute_market_returns(
        clean_records,
        rolling_return_windows=(3, 5),
        volatility_windows=(5,),
        trading_days=252,
    )

    print(f"  [OK] Computed features for {len(features)} records.")

    # Invariant assertions
    assert len(features) == len(clean_records), "Feature count must match clean records count"
    assert features[0].daily_return is None, "First observation daily return must be None"

    daily_rets_count = sum(1 for f in features if f.daily_return is not None)
    rolling_3_count = sum(1 for f in features if f.rolling_return_3d is not None)
    rolling_5_count = sum(1 for f in features if f.rolling_return_5d is not None)
    vol_5_count = sum(1 for f in features if f.volatility_5d is not None)

    print("\nStep 4: Inspection of Calculated Features across Sessions:")
    print("-----------------------------------------------------------------------------------------")
    print(f"{'Date':<12} {'Close (INR)':<12} {'Daily Ret':<14} {'Roll Ret 3d':<14} {'Roll Ret 5d':<14} {'Vol 5d (raw)':<14}")
    print("-----------------------------------------------------------------------------------------")

    for f in features:
        d_str = f.timestamp.strftime("%Y-%m-%d")
        c_str = f"{f.close:.2f}"
        dr_str = f"{f.daily_return:+.4%}" if f.daily_return is not None else "None (first)"
        r3_str = f"{f.rolling_return_3d:+.4%}" if f.rolling_return_3d is not None else "None (<3d)"
        r5_str = f"{f.rolling_return_5d:+.4%}" if f.rolling_return_5d is not None else "None (<5d)"
        v5_str = f"{f.volatility_5d:.6f}" if f.volatility_5d is not None else "None (<5d)"
        print(f"{d_str:<12} {c_str:<10} {dr_str:<12} {r3_str:<14} {r5_str:<14} {v5_str:<14}")

    print("-----------------------------------------------------------------------------------------")
    print(f"Summary Metrics:")
    print(f"  Clean Record Count:               {len(clean_records)}")
    print(f"  Daily Returns Available:          {daily_rets_count} (of {len(features)})")
    print(f"  First Daily Return:               {features[0].daily_return} (strictly None)")
    print(f"  3-Session Rolling Returns:        {rolling_3_count} available")
    print(f"  5-Session Rolling Returns:        {rolling_5_count} available")
    print(f"  5-Session Rolling Volatility:     {vol_5_count} available")
    print(f"  Timestamp Alignment 1:1:          All {len(features)} records aligned perfectly")

    # Verify chronological sorting and timestamp alignment
    for i in range(len(features)):
        assert features[i].timestamp == clean_records[i].timestamp
        assert features[i].close == clean_records[i].close
        assert features[i].symbol == clean_records[i].symbol
        if i > 0:
            assert features[i].timestamp > features[i - 1].timestamp

    print("\n[SUCCESS] Day 6 returns and volatility pipeline verified on real BHARTIARTL.NS data.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
