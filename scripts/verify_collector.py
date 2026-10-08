"""Real-Data Verification Script for Historical Collector.

Executes a small, isolated live retrieval for BHARTIARTL.NS via YFinanceProvider.
Verifies network connectivity, parsing, canonical MarketOHLCV conversion,
and domain validation rules against live market data.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.schemas import MarketOHLCV
from app.market.providers.yfinance_provider import YFinanceProvider


def main() -> int:
    print("==================================================")
    print("DAY 4 LIVE MARKET DATA VERIFICATION (BHARTIARTL)")
    print("==================================================")

    provider = YFinanceProvider()
    print(f"Provider Name: {provider.name}")

    # Use a small bounded historical window of 6 trading sessions (8 calendar days)
    start_dt = datetime(2026, 9, 1)
    end_dt = datetime(2026, 9, 8)
    symbol = "BHARTIARTL"

    print(f"Query Symbol:  {symbol} (resolved as {symbol}.NS)")
    print(f"Date Range:    {start_dt.date()} to {end_dt.date()} (Interval: 1d)")

    try:
        records = provider.fetch_historical_ohlcv(
            symbol=symbol,
            start_date=start_dt,
            end_date=end_dt,
            interval="1d",
        )
    except Exception as exc:
        print(f"ERROR: Live provider fetch failed: {exc}")
        return 1

    if not records:
        print("ERROR: Provider returned zero records for trading days.")
        return 1

    print(f"\n[OK] Retrieved {len(records)} canonical MarketOHLCV bars.")

    # Verify canonical contract properties across all retrieved bars
    for i, r in enumerate(records):
        assert isinstance(r, MarketOHLCV), f"Record {i} is not MarketOHLCV"
        assert r.symbol == "BHARTIARTL", f"Unexpected symbol: {r.symbol}"
        assert r.source == "yfinance", f"Unexpected source: {r.source}"
        assert r.high >= max(r.open, r.close), f"Physical bound violated on {r.timestamp}"
        assert r.low <= min(r.open, r.close), f"Physical bound violated on {r.timestamp}"
        assert r.volume >= 0, f"Negative volume on {r.timestamp}"

    # Print safe summary (first and last bar) without dumping massive data
    first_bar = records[0]
    last_bar = records[-1]

    print("\nSample Summary:")
    print(f"  First Bar: {first_bar.timestamp.date()} | Open: {first_bar.open:.2f} | High: {first_bar.high:.2f} | Low: {first_bar.low:.2f} | Close: {first_bar.close:.2f} | Vol: {first_bar.volume:,}")
    print(f"  Last Bar:  {last_bar.timestamp.date()} | Open: {last_bar.open:.2f} | High: {last_bar.high:.2f} | Low: {last_bar.low:.2f} | Close: {last_bar.close:.2f} | Vol: {last_bar.volume:,}")
    print("\n[SUCCESS] BHARTIARTL historical collection verified against live provider.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
