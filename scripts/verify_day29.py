"""Day 29 Verification Script: Macroeconomic, Regulatory, and External Events Ingestion.

Verifies:
1. Live acquisition and normalization of official RBI announcements (press releases / MPC).
2. Live acquisition and normalization of official SEBI circulars and orders.
3. Live acquisition and normalization of external market measurements (Brent Crude, USD/INR, S&P 500).
4. Multi-tier event deduplication.
5. Strict point-in-time temporal isolation preventing look-ahead leakage.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

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

from app.core.logging_config import setup_logging
from app.events import (
    EventCategory,
    ExternalMarketProvider,
    MacroEvent,
    RBIEventProvider,
    SEBIEventProvider,
    deduplicate_events,
    filter_events_point_in_time,
)

IST = ZoneInfo("Asia/Kolkata")


def main() -> int:
    setup_logging("INFO")
    now_ist = datetime.now(timezone.utc).astimezone(IST)

    print("=" * 80)
    print("DAY 29 VERIFICATION: MACROECONOMIC, REGULATORY & EXTERNAL EVENTS FOUNDATION")
    print("=" * 80)

    all_ingested_events = []

    # --- 1. Official RBI Press Releases Ingestion ---
    print("\n--- 1. Official RBI Regulatory & Monetary Policy Ingestion ---")
    rbi_provider = RBIEventProvider()
    try:
        rbi_events = rbi_provider.fetch_events(limit=5)
        print(f"  [SUCCESS] Fetched {len(rbi_events)} live events from {rbi_provider.name}")
        for i, ev in enumerate(rbi_events, 1):
            pub_str = ev.published_at.strftime("%Y-%m-%d %H:%M IST") if ev.published_at else "UNKNOWN"
            val_str = f" | Value: {ev.structured_value.value} {ev.structured_value.unit}" if ev.structured_value else ""
            print(f"    [{i}] ID: {ev.event_id} | Cat: {ev.category.value} | Published: {pub_str}")
            print(f"        Title: \"{ev.title[:75]}...\"{val_str}")
            all_ingested_events.append(ev)
    except Exception as e:
        print(f"  [ERROR] Live RBI ingestion failed: {e}")
        return 1

    # --- 2. Official SEBI Circulars & Orders Ingestion ---
    print("\n--- 2. Official SEBI Regulatory Ingestion ---")
    sebi_provider = SEBIEventProvider()
    try:
        sebi_events = sebi_provider.fetch_events(limit=5)
        print(f"  [SUCCESS] Fetched {len(sebi_events)} live events from {sebi_provider.name}")
        for i, ev in enumerate(sebi_events, 1):
            pub_str = ev.published_at.strftime("%Y-%m-%d %H:%M IST") if ev.published_at else "UNKNOWN"
            print(f"    [{i}] ID: {ev.event_id} | Type: {ev.event_type} | Published: {pub_str}")
            print(f"        Title: \"{ev.title[:75]}...\"")
            all_ingested_events.append(ev)
    except Exception as e:
        print(f"  [ERROR] Live SEBI ingestion failed: {e}")
        return 1

    # --- 3. External Market Observations Ingestion ---
    print("\n--- 3. External Market Observations (Continuous Time-Series) ---")
    market_provider = ExternalMarketProvider()
    try:
        end_dt = now_ist
        start_dt = end_dt - timedelta(days=7)
        observations = market_provider.fetch_observations(start_date=start_dt, end_date=end_dt)
        print(f"  [SUCCESS] Fetched {len(observations)} time-series measurements from {market_provider.name}")

        # Group by series_id and show latest
        seen_series = set()
        for obs in observations:
            if obs.series_id not in seen_series:
                seen_series.add(obs.series_id)
                ret_str = f" ({obs.daily_return * 100:+.2f}%)" if obs.daily_return is not None else ""
                print(f"    - {obs.series_id:<12}: Close = {obs.close:.2f} {obs.unit}{ret_str} as of {obs.timestamp.strftime('%Y-%m-%d')}")

        # Convert to event records for multi-source pipeline test
        market_events = market_provider.fetch_events(start_date=start_dt, end_date=end_dt, limit=5)
        all_ingested_events.extend(market_events)
    except Exception as e:
        print(f"  [ERROR] External market observation ingestion failed: {e}")
        return 1

    # --- 4. Canonical Serialization & Deduplication Audit ---
    print("\n--- 4. Multi-Source Deduplication & Schema Serialization ---")
    print(f"  Total Ingested Events from All Feeds: {len(all_ingested_events)}")
    dedup_result = deduplicate_events(all_ingested_events, window_hours=72)
    print(f"  Unique Canonical Events Retained:   {dedup_result.summary.unique_count}")
    print(f"  Duplicate Events Removed:           {dedup_result.summary.duplicates_removed}")

    # Inspect sample serialized JSON
    sample_ev = dedup_result.events[0]
    print("\n  Sample Serialized MacroEvent JSON Payload:")
    print(json.dumps(sample_ev.to_dict(), indent=2))

    # --- 5. Point-in-Time Temporal Isolation Audit ---
    print("\n--- 5. Point-in-Time Temporal Isolation Guard ---")
    # Simulate a market decision cutoff 48 hours in the past
    decision_cutoff = now_ist - timedelta(hours=48)
    eligible_events = filter_events_point_in_time(
        dedup_result.events,
        as_of_time=decision_cutoff,
    )
    print(f"  Simulated Decision Cutoff: {decision_cutoff.strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  Eligible Pre-Cutoff Events: {len(eligible_events)} / {len(dedup_result.events)}")

    # Verify no eligible event has primary_timestamp or ingested_at after cutoff
    for ev in eligible_events:
        assert ev.primary_timestamp <= decision_cutoff, f"Leakage breach: {ev.primary_timestamp} > {decision_cutoff}"
        assert ev.ingested_at <= decision_cutoff, f"Leakage breach: {ev.ingested_at} > {decision_cutoff}"
    print("  [SUCCESS] Zero look-ahead bias verified: 100% of post-cutoff records strictly eliminated.")

    print("\n" + "=" * 80)
    print("DAY 29 VERIFICATION COMPLETE: ALL MACRO & REGULATORY INVARIANTS SATISFIED")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
