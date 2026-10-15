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

    # Inspect sample serialized JSON safely
    if dedup_result.events:
        sample_ev = dedup_result.events[0]
        print("\n  Sample Serialized MacroEvent JSON Payload:")
        print(json.dumps(sample_ev.to_dict(), indent=2))
    else:
        print("\n  [WARNING] No events available to serialize sample payload.")

    # --- 5. Point-in-Time Temporal Isolation Audit ---
    print("\n--- 5. Point-in-Time Temporal Isolation Guard ---")
    # Part A: Test live events against a past cutoff. Since they were ingested just now at now_ist,
    # 100% of live events must be filtered out when decision_cutoff < now_ist.
    past_cutoff = now_ist - timedelta(hours=48)
    filtered_live = filter_events_point_in_time(
        dedup_result.events,
        as_of_time=past_cutoff,
    )
    print(f"  Past Cutoff: {past_cutoff.strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  Live Events Retained Before Past Cutoff: {len(filtered_live)} (Expected 0 due to ingested_at = now)")
    assert len(filtered_live) == 0, "Future-ingested live records leaked into past decision cutoff!"

    # Part B: Rigorous PIT test with known pre-cutoff, exact boundary, and post-cutoff events
    t_cutoff = now_ist - timedelta(days=2)
    ev_past = MacroEvent(
        title="Historical MPC Repo Rate Hold",
        category=EventCategory.MONETARY_POLICY,
        event_type="rate_decision",
        source_org="Reserve Bank of India",
        published_at=t_cutoff - timedelta(hours=2),
        ingested_at=t_cutoff - timedelta(hours=1),
        effective_at=t_cutoff + timedelta(days=5),  # Future effective date
    )
    ev_boundary = MacroEvent(
        title="Boundary SEBI Circular on Margin Trading",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="Securities and Exchange Board of India",
        published_at=t_cutoff,
        ingested_at=t_cutoff,
    )
    ev_future_pub = MacroEvent(
        title="Future Government Fiscal Update",
        category=EventCategory.GOVERNMENT,
        event_type="fiscal_release",
        source_org="Ministry of Finance",
        published_at=t_cutoff + timedelta(hours=1),
        ingested_at=t_cutoff - timedelta(hours=1),  # Ingested early, but future publication
    )
    ev_future_ingest = MacroEvent(
        title="Belatedly Ingested Macro Indicator",
        category=EventCategory.MACRO_INDICATOR,
        event_type="cpi_inflation",
        source_org="MoSPI",
        published_at=t_cutoff - timedelta(hours=5),
        ingested_at=t_cutoff + timedelta(hours=1),  # Published in past, but ingested after cutoff
    )

    test_pool = [ev_past, ev_boundary, ev_future_pub, ev_future_ingest]
    pit_results = filter_events_point_in_time(test_pool, as_of_time=t_cutoff)

    print(f"  Synthetic Boundary Test: Input = {len(test_pool)}, Eligible Output = {len(pit_results)}")
    assert len(pit_results) == 2, f"Expected exactly 2 eligible events, got {len(pit_results)}"
    eligible_ids = {e.event_id for e in pit_results}
    assert ev_past.event_id in eligible_ids, "Historical event with future effective date was incorrectly dropped!"
    assert ev_boundary.event_id in eligible_ids, "Exact cutoff boundary event was incorrectly dropped!"
    assert ev_future_pub.event_id not in eligible_ids, "Future-published event leaked through filter!"
    assert ev_future_ingest.event_id not in eligible_ids, "Future-ingested event leaked through filter!"

    for ev in pit_results:
        assert ev.primary_timestamp <= t_cutoff, f"Leakage breach: {ev.primary_timestamp} > {t_cutoff}"
        assert ev.ingested_at <= t_cutoff, f"Leakage breach: {ev.ingested_at} > {t_cutoff}"
    print("  [SUCCESS] Point-in-time isolation verified: past and boundary retained, future pub/ingest eliminated.")

    print("\n" + "=" * 80)
    print("DAY 29 VERIFICATION COMPLETE: ALL MACRO & REGULATORY INVARIANTS SATISFIED")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
