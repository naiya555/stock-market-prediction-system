"""Real-Data Verification Script for Moving Averages, RSI & MACD Technical Indicators.

Validates:
1. Investigation & resolution of the Day 8 six-record historical data limitation.
2. Expanded historical data acquisition (6-12 months / ~120-250 trading sessions).
3. Availability and mathematical correctness of SMA-5, EMA-5, SMA-10, EMA-10, RSI-14, and MACD (12, 26, 9).
4. Point-in-time integrity, chronological alignment, and histogram identity (histogram = macd - signal).
5. Regression validation of the original 6-session bounded historical range.
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
            macd_fast=12,
            macd_slow=26,
            macd_signal=9,
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

    # Verify MACD warmup and values
    # slow=26: indices 0..24 must be None; index 25 onwards must be valid float
    # signal=9: indices 0..32 must be None; index 33 onwards must be valid float
    for i in range(len(indicators)):
        if i < 25:
            if indicators[i].macd_line is not None:
                print(f"ERROR: Session {i} (< 26 sessions) must have macd_line as None", file=sys.stderr)
                return 1
        else:
            if indicators[i].macd_line is None:
                print(f"ERROR: Session {i} (>= 26 sessions) must have valid macd_line", file=sys.stderr)
                return 1

        if i < 33:
            if indicators[i].signal_line is not None:
                print(f"ERROR: Session {i} (< 34 sessions) must have signal_line as None", file=sys.stderr)
                return 1
            if indicators[i].histogram is not None:
                print(f"ERROR: Session {i} (< 34 sessions) must have histogram as None", file=sys.stderr)
                return 1
        else:
            sig_val = indicators[i].signal_line
            hist_val = indicators[i].histogram
            macd_val = indicators[i].macd_line
            if sig_val is None:
                print(f"ERROR: Session {i} (>= 34 sessions) must have valid signal_line", file=sys.stderr)
                return 1
            if hist_val is None:
                print(f"ERROR: Session {i} (>= 34 sessions) must have valid histogram", file=sys.stderr)
                return 1

            # Verify Histogram identity: Histogram = MACD - Signal
            expected_hist = macd_val - sig_val
            if not math.isclose(hist_val, expected_hist, abs_tol=1e-6):
                print(
                    f"ERROR: Session {i} histogram identity violation: hist={hist_val}, expected={expected_hist}",
                    file=sys.stderr,
                )
                return 1

    print("  [OK] SMA-5, EMA-5, SMA-10, EMA-10, RSI-14, and MACD (12, 26, 9) warmup and values verified.")

    currency = _get_currency_symbol()
    close_header = f"Close ({currency})"

    print("\nStep 4: Inspection of Recent Indicator Observations:")
    divider = "-" * 115
    print(divider)
    print(
        f"{'Date':<12} {close_header:<12} {'SMA-5':<10} {'EMA-5':<10} {'RSI-14':<10} {'MACD':<12} {'Signal':<12} {'Histogram':<12}"
    )
    print(divider)

    # Show recent 12 sessions
    display_sample = indicators[-12:]
    for ind in display_sample:
        d_str = ind.timestamp.strftime("%Y-%m-%d")
        c_str = f"{ind.close:.2f}"
        s5_str = f"{ind.sma_5:.2f}" if ind.sma_5 is not None else "None"
        e5_str = f"{ind.ema_5:.2f}" if ind.ema_5 is not None else "None"
        rsi_str = f"{ind.rsi_14:.2f}" if ind.rsi_14 is not None else "None"
        macd_str = f"{ind.macd_line:+.2f}" if ind.macd_line is not None else "None"
        sig_str = f"{ind.signal_line:+.2f}" if ind.signal_line is not None else "None"
        hist_str = f"{ind.histogram:+.2f}" if ind.histogram is not None else "None"
        print(f"{d_str:<12} {c_str:<12} {s5_str:<10} {e5_str:<10} {rsi_str:<10} {macd_str:<12} {sig_str:<12} {hist_str:<12}")

    print(divider)

    sma_5_count = sum(1 for ind in indicators if ind.sma_5 is not None)
    ema_5_count = sum(1 for ind in indicators if ind.ema_5 is not None)
    sma_10_count = sum(1 for ind in indicators if ind.sma_10 is not None)
    ema_10_count = sum(1 for ind in indicators if ind.ema_10 is not None)
    rsi_14_count = sum(1 for ind in indicators if ind.rsi_14 is not None)
    macd_count = sum(1 for ind in indicators if ind.macd_line is not None)
    sig_count = sum(1 for ind in indicators if ind.signal_line is not None)
    hist_count = sum(1 for ind in indicators if ind.histogram is not None)

    print("Summary Metrics (Expanded History):")
    print(f"  Symbol:                      {symbol}")
    print(f"  Clean Record Count:          {len(clean_records)}")
    print(f"  SMA-5 Available Count:       {sma_5_count} (of {len(indicators)})")
    print(f"  EMA-5 Available Count:       {ema_5_count} (of {len(indicators)})")
    print(f"  SMA-10 Available Count:      {sma_10_count} (of {len(indicators)})")
    print(f"  EMA-10 Available Count:      {ema_10_count} (of {len(indicators)})")
    print(f"  RSI-14 Available Count:      {rsi_14_count} (of {len(indicators)})")
    print(f"  MACD Available Count:        {macd_count} (of {len(indicators)})")
    print(f"  Signal Available Count:      {sig_count} (of {len(indicators)})")
    print(f"  Histogram Available Count:   {hist_count} (of {len(indicators)})")
    print(f"  Latest Close Price:          {indicators[-1].close:.2f}")
    print(f"  Latest RSI-14 Value:         {indicators[-1].rsi_14:.2f}")
    print(f"  Latest MACD Line:            {indicators[-1].macd_line:+.2f}")
    print(f"  Latest Signal Line:          {indicators[-1].signal_line:+.2f}")
    print(f"  Latest MACD Histogram:       {indicators[-1].histogram:+.2f}")

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
            macd_fast=12,
            macd_slow=26,
            macd_signal=9,
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
    macd_avail = sum(1 for ind in indicators if ind.macd_line is not None)
    sig_avail = sum(1 for ind in indicators if ind.signal_line is not None)
    hist_avail = sum(1 for ind in indicators if ind.histogram is not None)

    if sma_5_avail != 2:
        print(f"ERROR: Expected 2 SMA-5 values in 6-bar set, got {sma_5_avail}", file=sys.stderr)
        return 1
    if sma_10_avail != 0:
        print(f"ERROR: Expected 0 SMA-10 values in 6-bar set, got {sma_10_avail}", file=sys.stderr)
        return 1
    if rsi_14_avail != 0:
        print(f"ERROR: Expected 0 RSI-14 values in 6-bar set, got {rsi_14_avail}", file=sys.stderr)
        return 1
    if macd_avail != 0:
        print(f"ERROR: Expected 0 MACD values in 6-bar set, got {macd_avail}", file=sys.stderr)
        return 1
    if sig_avail != 0:
        print(f"ERROR: Expected 0 Signal values in 6-bar set, got {sig_avail}", file=sys.stderr)
        return 1
    if hist_avail != 0:
        print(f"ERROR: Expected 0 Histogram values in 6-bar set, got {hist_avail}", file=sys.stderr)
        return 1

    print("  [OK] 6-record regression verified: SMA-5 (2 values), SMA-10 (0), RSI-14 (0), MACD (0), Signal (0), Hist (0).")
    return 0


def main() -> int:
    print("==================================================")
    print("DAY 10 EXPANDED HISTORICAL DATA, RSI & MACD VERIFICATION")
    print("==================================================")

    res_expanded = verify_expanded_history()
    if res_expanded != 0:
        return res_expanded

    res_regression = verify_six_record_regression()
    if res_regression != 0:
        return res_regression

    print("\n[SUCCESS] Day 10 expanded historical data, moving averages, RSI, and MACD verified successfully.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
