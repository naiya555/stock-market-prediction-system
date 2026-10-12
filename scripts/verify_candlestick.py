"""Real-Data Verification Script for Candlestick Feature Engine.

Validates:
1. Real-data acquisition for BHARTIARTL via existing provider and pipeline.
2. Verified date range and record counts across ~6-month historical lookback.
3. Recent OHLC records and calculated candle features.
4. Formula identities and ratio bounds verification (body, wicks, ratios sum to 1.0, close location in [0, 1]).
5. Invalid candle geometry and zero-range safe division verification.
6. Original six-session regression scenario.
7. Explicit non-predictive baseline disclaimer.
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

from app.market.candlestick import (
    calculate_single_candlestick,
    compute_candlestick_features,
)
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


def verify_real_data_candlesticks() -> int:
    print("\n--------------------------------------------------")
    print("PART 1: REAL-DATA EXPANDED HISTORICAL VERIFICATION (BHARTIARTL)")
    print("--------------------------------------------------")

    provider = YFinanceProvider()
    symbol = "BHARTIARTL"
    lookback_days = 180

    print(f"Step 1: Running pipeline for {symbol} with lookback_days={lookback_days}...")
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
    candlesticks = pipeline_result.candlesticks

    print(f"  [OK] Collected raw bars:        {len(pipeline_result.raw_records)}")
    print(f"  [OK] Cleaned bars produced:    {len(clean_records)}")
    print(f"  [OK] Candlestick records:      {len(candlesticks)}")

    if len(clean_records) < 20:
        print(
            f"ERROR: Expected at least 20 historical sessions for 180 days, got {len(clean_records)}",
            file=sys.stderr,
        )
        return 1

    first_date = clean_records[0].timestamp.strftime("%Y-%m-%d")
    last_date = clean_records[-1].timestamp.strftime("%Y-%m-%d")
    print(f"  [OK] Date Range Verified:      {first_date} to {last_date} ({len(clean_records)} sessions)")

    print("\nStep 2: Validating chronological alignment and 1:1 bar correspondence...")
    for i in range(len(candlesticks)):
        c = candlesticks[i]
        b = clean_records[i]
        if c.timestamp != b.timestamp:
            print(
                f"ERROR: Timestamp mismatch at bar {i}: candle={c.timestamp} vs clean={b.timestamp}",
                file=sys.stderr,
            )
            return 1
        if c.open != b.open or c.high != b.high or c.low != b.low or c.close != b.close:
            print(f"ERROR: OHLC mismatch at bar {i}", file=sys.stderr)
            return 1

    print("  [OK] All candlestick features aligned 1:1 with cleaned historical bars.")

    print("\nStep 3: Validating mathematical identities and ratio bounds across all sessions...")
    eps = 1e-6
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    for i, c in enumerate(candlesticks):
        # Direction counts
        if c.is_bullish:
            bullish_count += 1
        elif c.is_bearish:
            bearish_count += 1
        else:
            neutral_count += 1

        # Body identity
        expected_body = c.close - c.open
        if abs(c.candle_body - expected_body) > eps:
            print(f"ERROR: Body mismatch at session {i}: {c.candle_body} vs {expected_body}", file=sys.stderr)
            return 1

        # Range identity
        expected_range = c.high - c.low
        if abs(c.candle_range - expected_range) > eps:
            print(f"ERROR: Range mismatch at session {i}: {c.candle_range} vs {expected_range}", file=sys.stderr)
            return 1

        # Geometric partition identity: body_abs + upper_wick + lower_wick == range
        geom_sum = c.candle_body_abs + c.candle_upper_wick + c.candle_lower_wick
        if abs(geom_sum - c.candle_range) > eps:
            print(
                f"ERROR: Geometric sum mismatch at session {i}: {geom_sum} vs {c.candle_range}",
                file=sys.stderr,
            )
            return 1

        # Ratios and bounds (when range > 0)
        if c.candle_range > 0.0:
            if not (0.0 - eps <= c.candle_body_ratio <= 1.0 + eps):
                print(f"ERROR: Body ratio out of bounds [0, 1] at session {i}: {c.candle_body_ratio}", file=sys.stderr)
                return 1
            if not (0.0 - eps <= c.candle_upper_wick_ratio <= 1.0 + eps):
                print(f"ERROR: Upper wick ratio out of bounds [0, 1] at session {i}: {c.candle_upper_wick_ratio}", file=sys.stderr)
                return 1
            if not (0.0 - eps <= c.candle_lower_wick_ratio <= 1.0 + eps):
                print(f"ERROR: Lower wick ratio out of bounds [0, 1] at session {i}: {c.candle_lower_wick_ratio}", file=sys.stderr)
                return 1
            if not (0.0 - eps <= c.candle_close_location <= 1.0 + eps):
                print(f"ERROR: Close location out of bounds [0, 1] at session {i}: {c.candle_close_location}", file=sys.stderr)
                return 1

            # Ratio partition identity: body_ratio + upper_ratio + lower_ratio == 1.0
            ratio_sum = c.candle_body_ratio + c.candle_upper_wick_ratio + c.candle_lower_wick_ratio
            if abs(ratio_sum - 1.0) > eps:
                print(f"ERROR: Ratio sum != 1.0 at session {i}: {ratio_sum}", file=sys.stderr)
                return 1

    print(f"  [OK] Mathematical partition identity (body + upper + lower == range) verified on {len(candlesticks)} bars.")
    print(f"  [OK] Ratio sum identity (body_ratio + upper_ratio + lower_ratio == 1.0) verified on all non-zero bars.")
    print(f"  [OK] Close location within range bounds [0.0, 1.0] verified on all bars.")
    print(f"  [OK] Candle directions: Bullish={bullish_count}, Bearish={bearish_count}, Neutral={neutral_count}.")

    print("\nStep 4: Displaying 5 most recent sessions with calculated candlestick features:")
    curr = _get_currency_symbol()
    print("-" * 120)
    print(
        f"{'Date':<11} | {'Open':>8} | {'High':>8} | {'Low':>8} | {'Close':>8} | "
        f"{'Body':>7} | {'Range':>7} | {'UpWick':>7} | {'LoWick':>7} | {'BodyR':>6} | {'UpR':>6} | {'LoR':>6} | {'ClLoc':>6} | {'Ret%':>7} | {'Dir':<7}"
    )
    print("-" * 120)
    for c in candlesticks[-5:]:
        dt_str = c.timestamp.strftime("%Y-%m-%d")
        print(
            f"{dt_str:<11} | "
            f"{c.open:>8.2f} | {c.high:>8.2f} | {c.low:>8.2f} | {c.close:>8.2f} | "
            f"{c.candle_body:>+7.2f} | {c.candle_range:>7.2f} | {c.candle_upper_wick:>7.2f} | {c.candle_lower_wick:>7.2f} | "
            f"{c.candle_body_ratio:>6.3f} | {c.candle_upper_wick_ratio:>6.3f} | {c.candle_lower_wick_ratio:>6.3f} | "
            f"{c.candle_close_location:>6.3f} | {c.candle_body_return_pct:>+6.2f}% | {c.candle_direction:<7}"
        )
    print("-" * 120)

    return 0


def verify_edge_cases_and_zero_range() -> int:
    print("\n--------------------------------------------------")
    print("PART 2: EDGE-CASE, ZERO-RANGE & GEOMETRY VERIFICATION")
    print("--------------------------------------------------")

    # 1. Zero-range candle
    zr = calculate_single_candlestick(open_=100.0, high=100.0, low=100.0, close=100.0)
    assert zr.candle_range == 0.0
    assert zr.candle_body == 0.0
    assert zr.candle_body_ratio is None
    assert zr.candle_upper_wick_ratio is None
    assert zr.candle_lower_wick_ratio is None
    assert zr.candle_close_location is None
    assert zr.candle_body_return_pct == 0.0
    assert zr.candle_direction == "neutral"
    print("  [OK] Zero-range candle safe division: dimensions=0.0, ratios=None, direction='neutral'.")

    # 2. Invalid geometry
    inv1 = calculate_single_candlestick(open_=100.0, high=95.0, low=90.0, close=105.0)  # High < Close
    assert inv1.candle_body is None
    assert inv1.candle_range is None
    assert inv1.candle_direction is None
    print("  [OK] Invalid geometry (High < Close) correctly masked with None.")

    inv2 = calculate_single_candlestick(open_=100.0, high=110.0, low=102.0, close=95.0)  # Low > Close
    assert inv2.candle_body is None
    assert inv2.candle_direction is None
    print("  [OK] Invalid geometry (Low > Close) correctly masked with None.")

    # 3. Non-positive price
    inv3 = calculate_single_candlestick(open_=0.0, high=110.0, low=0.0, close=105.0)
    assert inv3.candle_body is None
    print("  [OK] Non-positive price correctly masked with None.")

    return 0


def verify_six_session_regression() -> int:
    print("\n--------------------------------------------------")
    print("PART 3: REGRESSION VERIFICATION (ORIGINAL 6-SESSION FIXTURE)")
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
        )
    except Exception as exc:
        print(f"ERROR: Regression pipeline execution failed: {exc}", file=sys.stderr)
        return 1

    candlesticks = pipeline_result.candlesticks
    if len(candlesticks) != 6:
        print(f"ERROR: Expected 6 bars, got {len(candlesticks)}", file=sys.stderr)
        return 1

    valid_candles = sum(1 for c in candlesticks if c.candle_body is not None)
    if valid_candles != 6:
        print(f"ERROR: Expected 6 valid candle feature records, got {valid_candles}", file=sys.stderr)
        return 1

    print(f"  [OK] 6-session regression verified: All 6 bars produced valid candlestick features.")
    for i, c in enumerate(candlesticks):
        dt = c.timestamp.strftime("%Y-%m-%d")
        print(f"    Session {i+1} ({dt}): O={c.open:.2f}, H={c.high:.2f}, L={c.low:.2f}, C={c.close:.2f} -> {c.candle_direction.upper()} (body={c.candle_body:+.2f}, range={c.candle_range:.2f})")

    return 0


def main() -> int:
    print("==================================================")
    print("DAY 13 CANDLESTICK FEATURE ENGINE REAL-DATA VERIFICATION")
    print("==================================================")

    res_real = verify_real_data_candlesticks()
    if res_real != 0:
        return res_real

    res_edge = verify_edge_cases_and_zero_range()
    if res_edge != 0:
        return res_edge

    res_reg = verify_six_session_regression()
    if res_reg != 0:
        return res_reg

    print("\n[SUCCESS] Day 13 candlestick features verified successfully against real market data and regression scenarios.")
    print("Disclaimer: Successful feature calculation does not demonstrate predictive accuracy or trading edge.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
