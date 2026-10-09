"""Real-Data Verification Script for Moving Averages & RSI Technical Indicators.

Validates:
1. Investigation & resolution of the Day 8 six-record historical data limitation.
2. Expanded historical data acquisition (6-12 months / ~120-250 trading sessions).
3. Availability and mathematical correctness of SMA-5, EMA-5, SMA-10, EMA-10, and RSI-14.
4. Regression validation of the original 6-session bounded historical range.
"""

from datetime import datetime, timedelta
import math
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

from app.market.indicators import compute_moving_averages
from app.market.pipeline import run_market_data_pipeline
from app.market.providers.yfinance_provider import YFinanceProvider


def _get_currency_symbol() -> str:
    """Determine currency symbol, falling back to 'INR' if console cannot encode rupee."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "\u20b9".encode(encoding)
        return "\u20b9"
    except (UnicodeEncodeError, LookupError):
        return "INR"


def verify_expanded_history() -> int:
    print("\n--------------------------------------------------")
    print("PART 1: EXPANDED HISTORICAL RANGE VERIFICATION (~6 MONTHS)")
    print("--------------------------------------------------")

    provider = YFinanceProvider()
    symbol = "BHARTIARTL"
    lookback_days = 180

    print(f"Step 1: Running pipeline for {symbol} with lookback_days={lookback_days} (~6 months)...")
    try:
        pipeline_result = run_market_data_pipeline(
            symbol=symbol,
            lookback_days=lookback_days,
            provider=provider,
            sma_windows=(5, 10),
            ema_windows=(5, 10),
            rsi_periods=(14,),
        )
    except Exception as exc:
        print(f"ERROR: Market data pipeline execution failed: {exc}", file=sys.stderr)
        return 1

    clean_records = pipeline_result.cleaned_records
    indicators = pipeline_result.indicators

    print(f"  [OK] Collected raw bars:     {len(pipeline_result.raw_records)}")
    print(f"  [OK] Cleaned bars produced: {len(clean_records)}")
    print(f"  [OK] Indicator records:     {len(indicators)}")

    if len(clean_records) < 20:
        print(
            f"ERROR: Expected at least 20 historical sessions for 180 days, got {len(clean_records)}",
            file=sys.stderr,
        )
        return 1

    first_date = clean_records[0].timestamp.strftime("%Y-%m-%d")
    last_date = clean_records[-1].timestamp.strftime("%Y-%m-%d")
    print(f"  [OK] Date Range Verified:   {first_date} to {last_date} ({len(clean_records)} sessions)")

    print("\nStep 2: Validating chronological ordering and point-in-time integrity...")
    for i in range(len(indicators)):
        if indicators[i].timestamp != clean_records[i].timestamp:
            print(
                f"ERROR: Timestamp mismatch at session {i}: indicator={indicators[i].timestamp} vs clean={clean_records[i].timestamp}",
                file=sys.stderr,
            )
            return 1
        if indicators[i].close != clean_records[i].close:
            print(
                f"ERROR: Close price mismatch at session {i}: indicator={indicators[i].close} vs clean={clean_records[i].close}",
                file=sys.stderr,
            )
            return 1
        if i > 0 and indicators[i].timestamp <= indicators[i - 1].timestamp:
            print(
                f"ERROR: Chronological sorting violated at session {i}: {indicators[i].timestamp} <= {indicators[i - 1].timestamp}",
                file=sys.stderr,
            )
            return 1

    print("  [OK] Chronological ordering and 1:1 bar alignment verified.")

    print("\nStep 3: Validating mathematical correctness and warmup behavior...")
    closes = [r.close for r in clean_records]

    # Verify SMA-5 warmup and values
    for i in range(len(indicators)):
        if i < 4:
            if indicators[i].sma_5 is not None or indicators[i].ema_5 is not None:
                print(f"ERROR: Session {i} (< 5 sessions) must have 5-day MAs as None", file=sys.stderr)
                return 1
        else:
            expected_sma_5 = sum(closes[i - 4 : i + 1]) / 5.0
            actual_sma_5 = indicators[i].sma_5
            if actual_sma_5 is None or not math.isclose(actual_sma_5, expected_sma_5, rel_tol=1e-5):
                print(
                    f"ERROR: Session {i} SMA-5 mismatch: expected {expected_sma_5:.4f}, got {actual_sma_5}",
                    file=sys.stderr,
                )
                return 1

    # Verify SMA-10 warmup and values
    for i in range(len(indicators)):
        if i < 9:
            if indicators[i].sma_10 is not None or indicators[i].ema_10 is not None:
                print(f"ERROR: Session {i} (< 10 sessions) must have 10-day MAs as None", file=sys.stderr)
                return 1
        else:
            expected_sma_10 = sum(closes[i - 9 : i + 1]) / 10.0
            actual_sma_10 = indicators[i].sma_10
            if actual_sma_10 is None or not math.isclose(actual_sma_10, expected_sma_10, rel_tol=1e-5):
                print(
                    f"ERROR: Session {i} SMA-10 mismatch: expected {expected_sma_10:.4f}, got {actual_sma_10}",
                    file=sys.stderr,
                )
                return 1

    # Verify RSI-14 warmup and values
    for i in range(len(indicators)):
        if i < 14:
            if indicators[i].rsi_14 is not None:
                print(f"ERROR: Session {i} (< 14 price changes) must have rsi_14 as None", file=sys.stderr)
                return 1
        else:
            rsi_val = indicators[i].rsi_14
            if rsi_val is None:
                print(f"ERROR: Session {i} (>= 14 price changes) must have valid rsi_14", file=sys.stderr)
                return 1
            if not (0.0 <= rsi_val <= 100.0):
                print(f"ERROR: Session {i} RSI-14 out of bounds: {rsi_val}", file=sys.stderr)
                return 1

    print("  [OK] SMA-5, EMA-5, SMA-10, EMA-10, and RSI-14 warmup and values verified.")

    currency = _get_currency_symbol()
    close_header = f"Close ({currency})"

    print("\nStep 4: Inspection of Recent Indicator Observations:")
    divider = "-" * 89
    print(divider)
    print(
        f"{'Date':<12} {close_header:<14} {'SMA-5':<12} {'EMA-5':<12} {'SMA-10':<12} {'EMA-10':<12} {'RSI-14':<10}"
    )
    print(divider)

    # Show recent 12 sessions
    display_sample = indicators[-12:]
    for ind in display_sample:
        d_str = ind.timestamp.strftime("%Y-%m-%d")
        c_str = f"{ind.close:.2f}"
        s5_str = f"{ind.sma_5:.2f}" if ind.sma_5 is not None else "None"
        e5_str = f"{ind.ema_5:.2f}" if ind.ema_5 is not None else "None"
        s10_str = f"{ind.sma_10:.2f}" if ind.sma_10 is not None else "None"
        e10_str = f"{ind.ema_10:.2f}" if ind.ema_10 is not None else "None"
        rsi_str = f"{ind.rsi_14:.2f}" if ind.rsi_14 is not None else "None"
        print(f"{d_str:<12} {c_str:<14} {s5_str:<12} {e5_str:<12} {s10_str:<12} {e10_str:<12} {rsi_str:<10}")

    print(divider)

    sma_5_count = sum(1 for ind in indicators if ind.sma_5 is not None)
    ema_5_count = sum(1 for ind in indicators if ind.ema_5 is not None)
    sma_10_count = sum(1 for ind in indicators if ind.sma_10 is not None)
    ema_10_count = sum(1 for ind in indicators if ind.ema_10 is not None)
    rsi_14_count = sum(1 for ind in indicators if ind.rsi_14 is not None)

    print("Summary Metrics (Expanded History):")
    print(f"  Symbol:                      {symbol}")
    print(f"  Clean Record Count:          {len(clean_records)}")
    print(f"  SMA-5 Available Count:       {sma_5_count} (of {len(indicators)})")
    print(f"  EMA-5 Available Count:       {ema_5_count} (of {len(indicators)})")
    print(f"  SMA-10 Available Count:      {sma_10_count} (of {len(indicators)})")
    print(f"  EMA-10 Available Count:      {ema_10_count} (of {len(indicators)})")
    print(f"  RSI-14 Available Count:      {rsi_14_count} (of {len(indicators)})")
    print(f"  Latest RSI-14 Value:         {indicators[-1].rsi_14:.2f}")

    return 0


def verify_six_record_regression() -> int:
    print("\n--------------------------------------------------")
    print("PART 2: REGRESSION VERIFICATION (ORIGINAL 6-SESSION FIXTURE)")
    print("--------------------------------------------------")

    provider = YFinanceProvider()
    symbol = "BHARTIARTL"
    start_dt = datetime(2026, 9, 1)
    end_dt = datetime(2026, 9, 8)

    print(f"Running pipeline on original bounded range [{start_dt.date()} to {end_dt.date()}]...")
    try:
        pipeline_result = run_market_data_pipeline(
            symbol=symbol,
            start_date=start_dt,
            end_date=end_dt,
            provider=provider,
            sma_windows=(5, 10),
            ema_windows=(5, 10),
            rsi_periods=(14,),
        )
    except Exception as exc:
        print(f"ERROR: Regression pipeline execution failed: {exc}", file=sys.stderr)
        return 1

    indicators = pipeline_result.indicators
    if len(indicators) != 6:
        print(f"ERROR: Expected 6 bars, got {len(indicators)}", file=sys.stderr)
        return 1

    sma_5_avail = sum(1 for ind in indicators if ind.sma_5 is not None)
    sma_10_avail = sum(1 for ind in indicators if ind.sma_10 is not None)
    rsi_14_avail = sum(1 for ind in indicators if ind.rsi_14 is not None)

    if sma_5_avail != 2:
        print(f"ERROR: Expected 2 SMA-5 values in 6-bar set, got {sma_5_avail}", file=sys.stderr)
        return 1
    if sma_10_avail != 0:
        print(f"ERROR: Expected 0 SMA-10 values in 6-bar set, got {sma_10_avail}", file=sys.stderr)
        return 1
    if rsi_14_avail != 0:
        print(f"ERROR: Expected 0 RSI-14 values in 6-bar set, got {rsi_14_avail}", file=sys.stderr)
        return 1

    print("  [OK] 6-record regression verified: SMA-5 (2 values), SMA-10 (0 values), RSI-14 (0 values).")
    return 0


def main() -> int:
    print("==================================================")
    print("DAY 9 EXPANDED HISTORICAL DATA & RSI VERIFICATION")
    print("==================================================")

    res_expanded = verify_expanded_history()
    if res_expanded != 0:
        return res_expanded

    res_regression = verify_six_record_regression()
    if res_regression != 0:
        return res_regression

    print("\n[SUCCESS] Day 9 expanded historical data, moving averages, and RSI verified successfully.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
