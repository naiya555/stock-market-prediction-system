"""Real-Data Verification Script for ML Prediction Target Definition.

Validates:
1. Real-data acquisition for BHARTIARTL.NS via existing provider and pipeline.
2. Verified date alignment: session t prediction date pairs with session t+1 outcome date.
3. Accurate handling of weekends and exchange holidays without calendar-day gaps.
4. Mathematical return calculation: target_return[t] == close[t+1] / close[t] - 1.0.
5. Directional classification: UP (1) if target_return > 0 else DOWN (0).
6. Missing target invariant on the final observation (future is unknown).
7. Empirical target class distribution across real market sessions.
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
from app.prediction.target import (
    DirectionTarget,
    TargetObservation,
    generate_direction_targets,
)


def _get_currency_symbol() -> str:
    """Determine currency symbol, falling back to 'INR' if console cannot encode rupee."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "\u20b9".encode(encoding)
        return "\u20b9"
    except (UnicodeEncodeError, LookupError):
        return "INR"


def verify_real_data_targets() -> int:
    curr = _get_currency_symbol()
    print("==================================================")
    print("DAY 15: ML PREDICTION TARGET REAL-DATA VERIFICATION")
    print("==================================================")

    provider = YFinanceProvider()
    symbol = "BHARTIARTL"
    lookback_days = 180

    print(f"\nStep 1: Running pipeline for {symbol} (lookback_days={lookback_days})...")
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
    n_records = len(clean_records)
    print(f"  [OK] Cleaned bars produced: {n_records}")

    if n_records < 20:
        print(f"ERROR: Expected at least 20 historical sessions, got {n_records}", file=sys.stderr)
        return 1

    first_date = clean_records[0].timestamp.strftime("%Y-%m-%d")
    last_date = clean_records[-1].timestamp.strftime("%Y-%m-%d")
    print(f"  [OK] Date Range Verified:   {first_date} to {last_date} ({n_records} usable sessions)")

    print("\nStep 2: Generating ML prediction targets...")
    targets = generate_direction_targets(clean_records)
    assert len(targets) == n_records, f"Mismatch: {len(targets)} targets vs {n_records} records"
    print(f"  [OK] Generated {len(targets)} target observations aligned 1:1 with historical sessions.")

    print("\nStep 3: Validating mathematical formulas, alignments, and weekend transitions...")
    up_count = 0
    down_count = 0

    for t in range(n_records):
        curr_bar = clean_records[t]
        obs = targets[t]

        # Invariant: Timestamp and current_close must match exactly
        if obs.timestamp != curr_bar.timestamp or obs.current_close != curr_bar.close:
            print(f"ERROR: Alignment mismatch at session {t}", file=sys.stderr)
            return 1

        if t < n_records - 1:
            next_bar = clean_records[t + 1]
            # Must point to next available trading session
            if obs.next_timestamp != next_bar.timestamp:
                print(f"ERROR: next_timestamp mismatch at session {t}", file=sys.stderr)
                return 1
            if obs.next_close != next_bar.close:
                print(f"ERROR: next_close mismatch at session {t}", file=sys.stderr)
                return 1

            # Verify forward return formula
            expected_ret = (next_bar.close / curr_bar.close) - 1.0
            if obs.target_return is None or abs(obs.target_return - expected_ret) > 1e-9:
                print(f"ERROR: Return calculation mismatch at session {t}", file=sys.stderr)
                return 1

            # Verify directional rule
            if expected_ret > 0.0:
                if obs.target_direction != DirectionTarget.UP or obs.target_binary != 1:
                    print(f"ERROR: UP classification failed at session {t}", file=sys.stderr)
                    return 1
                up_count += 1
            else:
                if obs.target_direction != DirectionTarget.DOWN or obs.target_binary != 0:
                    print(f"ERROR: DOWN classification failed at session {t}", file=sys.stderr)
                    return 1
                down_count += 1
        else:
            # Final session invariant: future outcome MUST be None
            if (
                obs.next_close is not None
                or obs.next_timestamp is not None
                or obs.target_return is not None
                or obs.target_direction is not None
                or obs.target_binary is not None
            ):
                print("ERROR: Final observation leaked future outcome!", file=sys.stderr)
                return 1
            if obs.has_target is not False:
                print("ERROR: Final observation has_target must be False!", file=sys.stderr)
                return 1

    print("  [OK] Mathematical identity verified across all labeled sessions.")
    print("  [OK] Weekend / holiday transitions verified: all targets link to next available trading day.")
    print("  [OK] Final session missing-target invariant strictly verified (zero future leakage).")

    print("\nStep 4: Sample Recent Prediction Target Observations:")
    print("-" * 105)
    print(f"{'Pred Date':11s} | {'Curr Close':12s} | {'Next Date':11s} | {'Next Close':12s} | {'Fwd Return':11s} | {'Target':7s} | {'Binary':6s}")
    print("-" * 105)
    for obs in targets[-6:]:
        p_dt = obs.timestamp.strftime("%Y-%m-%d")
        n_dt = obs.next_timestamp.strftime("%Y-%m-%d") if obs.next_timestamp else "UNKNOWN"
        c_str = f"{curr}{obs.current_close:8.2f}"
        nc_str = f"{curr}{obs.next_close:8.2f}" if obs.next_close is not None else "N/A"
        ret_str = f"{obs.target_return * 100:+.2f}%" if obs.target_return is not None else "N/A"
        dir_str = obs.target_direction if obs.target_direction else "MISSING"
        bin_str = str(obs.target_binary) if obs.target_binary is not None else "None"
        print(f"{p_dt:11s} | {c_str:12s} | {n_dt:11s} | {nc_str:12s} | {ret_str:11s} | {dir_str:7s} | {bin_str:6s}")
    print("-" * 105)

    print("\nStep 5: Target Class Distribution Across Historical Dataset:")
    total_labeled = up_count + down_count
    up_pct = (up_count / total_labeled) * 100.0 if total_labeled > 0 else 0.0
    down_pct = (down_count / total_labeled) * 100.0 if total_labeled > 0 else 0.0
    print(f"  Total Historical Sessions: {n_records}")
    print(f"  Total Labeled Sessions:    {total_labeled} (excluding final session)")
    print(f"  UP Target Count:           {up_count} ({up_pct:.1f}%)")
    print(f"  DOWN Target Count:         {down_count} ({down_pct:.1f}%)")

    print("\n==================================================")
    print("VERIFICATION SUMMARY")
    print("==================================================")
    print(f"Symbol:                 {symbol}")
    print(f"Historical Range:       {first_date} to {last_date}")
    print(f"Formula Verified:       target_return[t] = close[t+1] / close[t] - 1.0")
    print(f"Binary Rule:            UP if return > 0.0 else DOWN (zero return -> DOWN)")
    print(f"Final Row Policy:       Strictly None (Missing Target)")
    print(f"Temporal Leakage:       Zero (features isolated from outcome)")
    print("==================================================\n")
    return 0


if __name__ == "__main__":
    sys.exit(verify_real_data_targets())
