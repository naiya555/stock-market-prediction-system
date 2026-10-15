"""Real-Data Verification Script for Day 26: NIFTY Benchmark & Sector Context Engine.

Demonstrates:
1. Ingestion and resolution of broad market benchmark (^NSEI / NIFTY 50) and sectoral index (^NSEBANK)
   via YFinanceProvider without extraneous exchange suffixes.
2. Temporal alignment of stock bars with benchmark bars preventing look-ahead bias and handling missing sessions.
3. Point-in-time calculation of relative performance features:
   - Daily excess return (alpha).
   - Relative strength ratio.
   - 5-day and 20-day relative strength momentum.
   - 20-day rolling beta (sample covariance / sample variance) and 20-day rolling correlation.
4. Cross-sectional market breadth calculation across a representative NSE basket:
   - Advances, declines, unchanged counts.
   - Advance/Decline ratio and breadth thrust.
   - Point-in-time 20-day SMA breadth participation percentage.
"""

from datetime import datetime, timedelta
import json
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

from app.core.logging_config import get_logger, setup_logging
from app.market.benchmark import (
    BROAD_MARKET_BENCHMARK,
    BANKING_BENCHMARK,
    MarketBreadthObservation,
    RelativePerformanceFeature,
    align_benchmark_series,
    compute_market_breadth,
    compute_multi_symbol_breadth_series,
    compute_relative_performance,
    get_sector_benchmark,
)
from app.market.cleaner import clean_market_data
from app.market.providers.yfinance_provider import YFinanceProvider

logger = get_logger("scripts.verify_day26")


def verify_day26() -> int:
    """Run real-data verification of benchmark ingestion, relative performance, and breadth."""
    setup_logging("INFO")
    print("================================================================================")
    print("DAY 26 VERIFICATION: NIFTY BENCHMARK & SECTOR CONTEXT ENGINE")
    print("================================================================================")

    provider = YFinanceProvider()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # ~60 trading sessions

    # 1. Verify Provider Symbol Resolution
    print("\n--- 1. Provider Benchmark Symbol Resolution ---")
    test_symbols = ["^NSEI", "NIFTY", "NIFTY50", "^NSEBANK", "BANKNIFTY", "BHARTIARTL"]
    for sym in test_symbols:
        base, query = provider._resolve_symbols(sym)
        print(f"  Input: {sym:<12} -> Base: {base:<12} Query: {query}")
        if sym.startswith("^") or sym.startswith("NIFTY") or sym.startswith("BANK"):
            assert not query.endswith(".NS"), f"Index query ticker {query} must not have .NS suffix!"
    print("  [SUCCESS] All benchmark index symbols and aliases resolved correctly.")

    # 2. Fetch Real Historical Benchmark Data
    print(f"\n--- 2. Fetching Real Benchmark and Equity Data ({start_date.date()} to {end_date.date()}) ---")
    bench_symbol = BROAD_MARKET_BENCHMARK  # ^NSEI
    stock_symbol = "BHARTIARTL.NS"

    raw_bench = provider.fetch_historical_ohlcv(bench_symbol, start_date=start_date, end_date=end_date)
    raw_stock = provider.fetch_historical_ohlcv(stock_symbol, start_date=start_date, end_date=end_date)

    clean_bench_result = clean_market_data(raw_bench)
    clean_stock_result = clean_market_data(raw_stock)

    bench_bars = clean_bench_result.records
    stock_bars = clean_stock_result.records

    print(f"  Fetched {len(bench_bars)} benchmark bars for {bench_symbol}")
    print(f"  Fetched {len(stock_bars)} stock bars for {stock_symbol}")
    assert len(bench_bars) > 25, "Expected at least 25 benchmark bars"
    assert len(stock_bars) > 25, "Expected at least 25 stock bars"

    # 3. Verify Session Alignment
    print("\n--- 3. Verifying Point-in-Time Temporal Alignment ---")
    aligned = align_benchmark_series(stock_bars, bench_bars)
    print(f"  Total aligned pairs: {len(aligned)}")
    assert len(aligned) == len(stock_bars)
    matching_dates = sum(1 for s, b in aligned if b is not None and s.timestamp.date() == b.timestamp.date())
    print(f"  Matching session dates: {matching_dates}/{len(aligned)}")
    assert matching_dates >= len(aligned) - 2, "Almost all sessions should share exact date"

    # 4. Compute Relative Performance Features
    print("\n--- 4. Computing Relative Performance Features ---")
    features = compute_relative_performance(stock_bars, bench_bars, beta_window=20, min_periods=10)
    assert len(features) == len(stock_bars)

    # Inspect the most recent feature observations
    recent = features[-5:]
    print("  Recent Sessions Relative Performance Summary:")
    print(f"  {'Date':<12} {'Stock Cls':<10} {'NIFTY Cls':<10} {'Alpha (%)':<10} {'RS Ratio':<10} {'RS Mom 5d':<12} {'Beta 20d':<10} {'Corr 20d':<10}")
    print("  " + "-" * 88)
    for f in recent:
        d_str = f.timestamp.strftime("%Y-%m-%d")
        s_cls = f"{f.stock_close:.2f}"
        b_cls = f"{f.benchmark_close:.2f}" if f.benchmark_close else "N/A"
        alpha_str = f"{f.relative_return * 100:.2f}%" if f.relative_return is not None else "N/A"
        rs_str = f"{f.relative_strength:.4f}" if f.relative_strength else "N/A"
        mom5_str = f"{f.relative_strength_momentum_5d * 100:.2f}%" if f.relative_strength_momentum_5d is not None else "N/A"
        beta_str = f"{f.rolling_beta_20d:.3f}" if f.rolling_beta_20d is not None else "N/A"
        corr_str = f"{f.rolling_correlation_20d:.3f}" if f.rolling_correlation_20d is not None else "N/A"
        print(f"  {d_str:<12} {s_cls:<10} {b_cls:<10} {alpha_str:<10} {rs_str:<10} {mom5_str:<12} {beta_str:<10} {corr_str:<10}")

    latest_f = features[-1]
    assert latest_f.rolling_beta_20d is not None, "Mature rolling beta should not be None"
    assert latest_f.rolling_correlation_20d is not None, "Mature rolling correlation should not be None"
    assert -1.0 <= latest_f.rolling_correlation_20d <= 1.0, "Correlation must lie between -1 and 1"
    print(f"  [SUCCESS] Computed valid rolling beta ({latest_f.rolling_beta_20d:.3f}) and correlation ({latest_f.rolling_correlation_20d:.3f})")

    # 5. Cross-Sectional Market Breadth
    print("\n--- 5. Computing Multi-Symbol Market Breadth ---")
    basket = ["BHARTIARTL.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
    multi_bars: dict[str, list] = {}
    for sym in basket:
        raw = provider.fetch_historical_ohlcv(sym, start_date=start_date, end_date=end_date)
        cleaned = clean_market_data(raw).records
        multi_bars[sym] = cleaned
        print(f"  Fetched {len(cleaned)} bars for basket constituent {sym}")

    breadth_series = compute_multi_symbol_breadth_series(multi_bars, sma_window=20)
    print(f"  Calculated {len(breadth_series)} cross-sectional breadth sessions.")
    assert len(breadth_series) > 20

    latest_breadth = breadth_series[-1]
    print(f"  Latest Breadth Snapshot ({latest_breadth.timestamp.date()}):")
    print(f"    Total Active Stocks:     {latest_breadth.total_stocks}")
    print(f"    Advances:               {latest_breadth.advances}")
    print(f"    Declines:               {latest_breadth.declines}")
    print(f"    Unchanged:              {latest_breadth.unchanged}")
    print(f"    Advance/Decline Ratio:  {latest_breadth.advance_decline_ratio}")
    print(f"    Breadth Thrust:         {latest_breadth.breadth_thrust}")
    print(f"    % Above 20-day SMA:     {latest_breadth.pct_above_sma20}")

    print("\n================================================================================")
    print("DAY 26 VERIFICATION COMPLETE: ALL BENCHMARK & BREADTH INVARIANTS SATISFIED")
    print("================================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(verify_day26())
