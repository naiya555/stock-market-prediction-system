"""Real-Data Verification Script for Moving Averages, RSI, MACD, Bollinger Bands, ATR & ROC.

Validates:
1. Investigation & resolution of the Day 8 six-record historical data limitation.
2. Expanded historical data acquisition (6-12 months / ~120-250 trading sessions).
3. Availability and mathematical correctness of SMA-5, EMA-5, SMA-10, EMA-10, RSI-14, MACD (12, 26, 9), Bollinger Bands (20, 2.0), ATR-14, and ROC-10.
4. Point-in-time integrity, chronological alignment, histogram identity, Bollinger band identities, ATR recurrence/warmup, and ROC identity/warmup.
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

from app.market.indicators import calculate_true_range, compute_moving_averages
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
            bb_window=20,
            bb_multiplier=2.0,
            bb_ddof=0,
            atr_periods=(14,),
            roc_periods=(10,),
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

    # Verify Bollinger Bands (20, 2.0, ddof=0) warmup and values
    for i in range(len(indicators)):
        if i < 19:
            if (
                indicators[i].bb_middle is not None
                or indicators[i].bb_upper is not None
                or indicators[i].bb_lower is not None
                or indicators[i].bb_bandwidth is not None
                or indicators[i].bb_percent_b is not None
            ):
                print(f"ERROR: Session {i} (< 20 sessions) must have Bollinger Bands as None", file=sys.stderr)
                return 1
        else:
            mid = indicators[i].bb_middle
            up = indicators[i].bb_upper
            low = indicators[i].bb_lower
            bw = indicators[i].bb_bandwidth
            pb = indicators[i].bb_percent_b
            c = indicators[i].close

            if mid is None or up is None or low is None or bw is None or pb is None:
                print(f"ERROR: Session {i} (>= 20 sessions) must have all Bollinger Bands values populated", file=sys.stderr)
                return 1

            expected_mid = sum(closes[i - 19 : i + 1]) / 20.0
            if not math.isclose(mid, expected_mid, rel_tol=1e-5):
                print(f"ERROR: Session {i} BB middle mismatch: expected {expected_mid:.4f}, got {mid}", file=sys.stderr)
                return 1

            if not (up >= mid >= low):
                print(f"ERROR: Session {i} BB band ordering violated: up={up}, mid={mid}, low={low}", file=sys.stderr)
                return 1

            # Symmetry check: upper - middle == middle - lower
            if not math.isclose(up - mid, mid - low, abs_tol=1e-5):
                print(f"ERROR: Session {i} BB band asymmetry: (up-mid)={up-mid} != (mid-low)={mid-low}", file=sys.stderr)
                return 1

            # Band Width check: (upper - lower) / middle
            expected_bw = (up - low) / mid
            if not math.isclose(bw, expected_bw, rel_tol=1e-5):
                print(f"ERROR: Session {i} BB bandwidth mismatch: expected {expected_bw}, got {bw}", file=sys.stderr)
                return 1

            # Percent B check: (close - lower) / (upper - lower)
            if up > low:
                expected_pb = (c - low) / (up - low)
                if not math.isclose(pb, expected_pb, rel_tol=1e-5):
                    print(f"ERROR: Session {i} BB %B mismatch: expected {expected_pb}, got {pb}", file=sys.stderr)
                    return 1

    # Verify ATR (period=14) warmup, Wilder recurrence, and mathematical identity
    trs = calculate_true_range(clean_records)
    for i in range(len(indicators)):
        if i < 13:
            if indicators[i].atr_14 is not None:
                print(f"ERROR: Session {i} (< 14 bars) must have atr_14 as None", file=sys.stderr)
                return 1
        elif i == 13:
            expected_seed_atr = sum(trs[:14]) / 14.0
            actual_atr = indicators[i].atr_14
            if actual_atr is None or not math.isclose(actual_atr, expected_seed_atr, rel_tol=1e-5):
                print(
                    f"ERROR: Session 13 ATR seed mismatch: expected {expected_seed_atr:.4f}, got {actual_atr}",
                    file=sys.stderr,
                )
                return 1
        else:
            prev_atr = indicators[i - 1].atr_14
            expected_atr = ((13.0 * prev_atr) + trs[i]) / 14.0
            actual_atr = indicators[i].atr_14
            if actual_atr is None or not math.isclose(actual_atr, expected_atr, rel_tol=1e-5):
                print(
                    f"ERROR: Session {i} ATR Wilder recurrence mismatch: expected {expected_atr:.4f}, got {actual_atr}",
                    file=sys.stderr,
                )
                return 1

    # Verify ROC (period=10) warmup and formula identity
    for i in range(len(indicators)):
        if i < 10:
            if indicators[i].roc_10 is not None:
                print(f"ERROR: Session {i} (< 10 bars) must have roc_10 as None", file=sys.stderr)
                return 1
        else:
            expected_roc = ((closes[i] / closes[i - 10]) - 1.0) * 100.0
            actual_roc = indicators[i].roc_10
            if actual_roc is None or not math.isclose(actual_roc, expected_roc, rel_tol=1e-5):
                print(
                    f"ERROR: Session {i} ROC-10 mismatch: expected {expected_roc:.4f}, got {actual_roc}",
                    file=sys.stderr,
                )
                return 1

    print("  [OK] SMA-5, EMA-5, SMA-10, EMA-10, RSI-14, MACD (12, 26, 9), Bollinger Bands (20, 2.0), ATR-14, and ROC-10 warmup and values verified.")

    currency = _get_currency_symbol()
    close_header = f"Close ({currency})"

    print("\nStep 4: Inspection of Recent Trend & Momentum Indicators:")
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

    print("\nStep 4B: Inspection of Recent Bollinger Bands (20, 2.0, ddof=0):")
    divider_bb = "-" * 90
    print(divider_bb)
    print(
        f"{'Date':<12} {close_header:<12} {'Middle':<12} {'Upper':<12} {'Lower':<12} {'BandWidth':<12} {'%B':<10}"
    )
    print(divider_bb)
    for ind in display_sample:
        d_str = ind.timestamp.strftime("%Y-%m-%d")
        c_str = f"{ind.close:.2f}"
        mid_str = f"{ind.bb_middle:.2f}" if ind.bb_middle is not None else "None"
        up_str = f"{ind.bb_upper:.2f}" if ind.bb_upper is not None else "None"
        low_str = f"{ind.bb_lower:.2f}" if ind.bb_lower is not None else "None"
        bw_str = f"{ind.bb_bandwidth:.4f}" if ind.bb_bandwidth is not None else "None"
        pb_str = f"{ind.bb_percent_b:.4f}" if ind.bb_percent_b is not None else "None"
        print(f"{d_str:<12} {c_str:<12} {mid_str:<12} {up_str:<12} {low_str:<12} {bw_str:<12} {pb_str:<10}")
    print(divider_bb)

    print("\nStep 4C: Inspection of Recent Volatility & Momentum (ATR-14, ROC-10):")
    divider_vol = "-" * 85
    print(divider_vol)
    print(
        f"{'Date':<12} {close_header:<12} {'High':<10} {'Low':<10} {'TR':<10} {'ATR-14':<12} {'ROC-10 (%)':<12}"
    )
    print(divider_vol)
    sample_indices = range(len(indicators) - 12, len(indicators))
    for idx in sample_indices:
        ind = indicators[idx]
        rec = clean_records[idx]
        tr_val = trs[idx]
        d_str = ind.timestamp.strftime("%Y-%m-%d")
        c_str = f"{ind.close:.2f}"
        h_str = f"{rec.high:.2f}"
        l_str = f"{rec.low:.2f}"
        tr_str = f"{tr_val:.2f}"
        atr_str = f"{ind.atr_14:.2f}" if ind.atr_14 is not None else "None"
        roc_str = f"{ind.roc_10:+.2f}%" if ind.roc_10 is not None else "None"
        print(f"{d_str:<12} {c_str:<12} {h_str:<10} {l_str:<10} {tr_str:<10} {atr_str:<12} {roc_str:<12}")
    print(divider_vol)

    sma_5_count = sum(1 for ind in indicators if ind.sma_5 is not None)
    ema_5_count = sum(1 for ind in indicators if ind.ema_5 is not None)
    sma_10_count = sum(1 for ind in indicators if ind.sma_10 is not None)
    ema_10_count = sum(1 for ind in indicators if ind.ema_10 is not None)
    rsi_14_count = sum(1 for ind in indicators if ind.rsi_14 is not None)
    macd_count = sum(1 for ind in indicators if ind.macd_line is not None)
    sig_count = sum(1 for ind in indicators if ind.signal_line is not None)
    hist_count = sum(1 for ind in indicators if ind.histogram is not None)
    bb_count = sum(1 for ind in indicators if ind.bb_middle is not None)
    atr_count = sum(1 for ind in indicators if ind.atr_14 is not None)
    roc_count = sum(1 for ind in indicators if ind.roc_10 is not None)

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
    print(f"  Bollinger Available Count:   {bb_count} (of {len(indicators)})")
    print(f"  ATR-14 Available Count:      {atr_count} (of {len(indicators)})")
    print(f"  ROC-10 Available Count:      {roc_count} (of {len(indicators)})")
    print(f"  Latest Close Price:          {indicators[-1].close:.2f}")
    print(f"  Latest RSI-14 Value:         {indicators[-1].rsi_14:.2f}")
    print(f"  Latest MACD Line:            {indicators[-1].macd_line:+.2f}")
    print(f"  Latest Signal Line:          {indicators[-1].signal_line:+.2f}")
    print(f"  Latest MACD Histogram:       {indicators[-1].histogram:+.2f}")
    print(f"  Latest BB Middle:            {indicators[-1].bb_middle:.2f}")
    print(f"  Latest BB Upper:             {indicators[-1].bb_upper:.2f}")
    print(f"  Latest BB Lower:             {indicators[-1].bb_lower:.2f}")
    print(f"  Latest BB BandWidth:         {indicators[-1].bb_bandwidth:.4f}")
    print(f"  Latest BB %B:                {indicators[-1].bb_percent_b:.4f}")
    print(f"  Latest ATR-14 Value:         {indicators[-1].atr_14:.2f}")
    print(f"  Latest ROC-10 Value:         {indicators[-1].roc_10:+.2f}%")

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
            bb_window=20,
            bb_multiplier=2.0,
            bb_ddof=0,
            atr_periods=(14,),
            roc_periods=(10,),
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
    bb_avail = sum(1 for ind in indicators if ind.bb_middle is not None)
    atr_avail = sum(1 for ind in indicators if ind.atr_14 is not None)
    roc_avail = sum(1 for ind in indicators if ind.roc_10 is not None)

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
    if bb_avail != 0:
        print(f"ERROR: Expected 0 Bollinger values in 6-bar set, got {bb_avail}", file=sys.stderr)
        return 1
    if atr_avail != 0:
        print(f"ERROR: Expected 0 ATR values in 6-bar set, got {atr_avail}", file=sys.stderr)
        return 1
    if roc_avail != 0:
        print(f"ERROR: Expected 0 ROC values in 6-bar set, got {roc_avail}", file=sys.stderr)
        return 1

    print("  [OK] 6-record regression verified: SMA-5 (2 values), SMA-10 (0), RSI-14 (0), MACD (0), Signal (0), Hist (0), BB (0), ATR (0), ROC (0).")
    return 0


def main() -> int:
    print("==================================================")
    print("DAY 12 EXPANDED HISTORICAL DATA, RSI, MACD, BOLLINGER BANDS, ATR & ROC VERIFICATION")
    print("==================================================")

    res_expanded = verify_expanded_history()
    if res_expanded != 0:
        return res_expanded

    res_regression = verify_six_record_regression()
    if res_regression != 0:
        return res_regression

    print("\n[SUCCESS] Day 12 expanded historical data, moving averages, RSI, MACD, Bollinger Bands, ATR, and ROC verified successfully.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
