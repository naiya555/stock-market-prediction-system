"""Unit Tests for Macroeconomic, Regulatory, and External Events Ingestion Foundation.

Validates schema invariants, serialization, deterministic identifiers, deduplication,
point-in-time temporal isolation, RBI and SEBI XML parsing, external market observations,
and offline deterministic execution without live network dependencies.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest

from app.core.schemas import ValidationError
from app.events import (
    BaseEventProvider,
    EventCategory,
    EventCleaningResult,
    EventDeduplicationSummary,
    EventProviderError,
    ExternalMarketObservation,
    ExternalMarketProvider,
    MacroEvent,
    RBIEventProvider,
    SEBIEventProvider,
    StructuredEventValue,
    deduplicate_events,
    filter_events_point_in_time,
)

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RBI_XML = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Reserve Bank of India - Press Releases</title>
    <link>https://www.rbi.org.in</link>
    <description>RBI Press Releases</description>
    <item>
      <title>Monetary Policy Committee (MPC) Decision: Repo rate increased to 6.50%</title>
      <link>https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=1001</link>
      <pubDate>Thu, 15 Oct 2026 10:00:00</pubDate>
      <description>&lt;p&gt;The Monetary Policy Committee decided to increase the policy repo rate by 25 bps to 6.50%.&lt;/p&gt;</description>
    </item>
    <item>
      <title>Auction of State Government Securities</title>
      <link>https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=1002</link>
      <pubDate>Wed, 14 Oct 2026 15:30:00</pubDate>
      <description>The Reserve Bank of India announces auction of state government securities for Rs. 5,000 crore.</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_SEBI_XML = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>SEBI Circulars and Orders</title>
    <link>https://www.sebi.gov.in</link>
    <item>
      <title>Master Circular for Mutual Funds on Portfolio Disclosures</title>
      <link>https://www.sebi.gov.in/legal/circulars/oct-2026/master-circular-mf.html</link>
      <pubDate>15 Oct, 2026 +0530</pubDate>
      <description>SEBI issues Master Circular updating portfolio disclosure guidelines for asset management companies.</description>
    </item>
    <item>
      <title>Adjudication Order in respect of ABC Securities Ltd</title>
      <link>https://www.sebi.gov.in/enforcement/orders/oct-2026/order-abc.html</link>
      <pubDate>14 Oct, 2026 +0530</pubDate>
      <description>Adjudication order imposing penalty for reporting non-compliance.</description>
    </item>
  </channel>
</rss>
"""


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------

def test_structured_event_value_valid() -> None:
    val = StructuredEventValue(
        metric_name="repo_rate",
        value=6.50,
        unit="percent",
        prior_value=6.25,
        reference_period="FY2026-Q3",
    )
    assert val.metric_name == "repo_rate"
    assert val.value == 6.50
    assert val.prior_value == 6.25
    assert val.change == 0.25
    assert val.unit == "percent"
    assert val.reference_period == "FY2026-Q3"

    d = val.to_dict()
    assert d["metric_name"] == "repo_rate"
    assert d["value"] == 6.50
    assert d["change"] == 0.25


def test_structured_event_value_rejects_invalid_numbers() -> None:
    with pytest.raises(ValidationError, match="value must be a numeric float or int"):
        StructuredEventValue(metric_name="repo_rate", value="high", unit="percent")  # type: ignore

    with pytest.raises(ValidationError, match="value must be a finite number"):
        StructuredEventValue(metric_name="repo_rate", value=float("nan"), unit="percent")

    with pytest.raises(ValidationError, match="unit cannot be empty"):
        StructuredEventValue(metric_name="repo_rate", value=6.50, unit="")


def test_macro_event_valid_construction() -> None:
    now_ist = datetime(2026, 10, 15, 12, 0, tzinfo=IST)
    ev = MacroEvent(
        title="RBI Repo Rate Decision",
        category=EventCategory.MONETARY_POLICY,
        event_type="repo_rate_decision",
        source_org="Reserve Bank of India",
        ingested_at=now_ist,
        published_at=now_ist,
        url="https://rbi.org.in/press/1001",
        affected_sectors=("BANKING", "FINANCIAL_SERVICES"),
        structured_value=StructuredEventValue(metric_name="repo_rate", value=6.50, unit="percent"),
        summary="MPC maintained repo rate at 6.50%.",
        provider="rbi_rss_provider",
    )

    assert ev.title == "RBI Repo Rate Decision"
    assert ev.category == EventCategory.MONETARY_POLICY
    assert ev.event_type == "repo_rate_decision"
    assert ev.source_org == "Reserve Bank of India"
    assert ev.published_at == now_ist
    assert ev.primary_timestamp == now_ist
    assert len(ev.event_id) == 16
    assert ev.affected_sectors == ("BANKING", "FINANCIAL_SERVICES")

    d = ev.to_dict()
    assert d["event_id"] == ev.event_id
    assert d["category"] == "monetary_policy"
    assert d["structured_value"]["value"] == 6.50
    assert d["affected_sectors"] == ["BANKING", "FINANCIAL_SERVICES"]


def test_macro_event_rejects_missing_temporal_anchors() -> None:
    now_ist = datetime(2026, 10, 15, 12, 0, tzinfo=IST)
    with pytest.raises(ValidationError, match="Event must have at least one temporal anchor"):
        MacroEvent(
            title="Policy Notice",
            category=EventCategory.REGULATORY,
            event_type="notice",
            source_org="SEBI",
            ingested_at=now_ist,
            published_at=None,
            announced_at=None,
            effective_at=None,
        )


def test_macro_event_rejects_naive_timestamps() -> None:
    naive_dt = datetime(2026, 10, 15, 12, 0)  # No tzinfo
    aware_dt = datetime(2026, 10, 15, 12, 0, tzinfo=IST)

    with pytest.raises(ValidationError, match="ingested_at must be timezone-aware"):
        MacroEvent(
            title="Notice",
            category=EventCategory.REGULATORY,
            event_type="notice",
            source_org="SEBI",
            ingested_at=naive_dt,
            published_at=aware_dt,
        )

    with pytest.raises(ValidationError, match="published_at must be timezone-aware"):
        MacroEvent(
            title="Notice",
            category=EventCategory.REGULATORY,
            event_type="notice",
            source_org="SEBI",
            ingested_at=aware_dt,
            published_at=naive_dt,
        )


def test_macro_event_rejects_invalid_url() -> None:
    aware_dt = datetime(2026, 10, 15, 12, 0, tzinfo=IST)
    with pytest.raises(ValidationError, match="Invalid URL format"):
        MacroEvent(
            title="Notice",
            category=EventCategory.REGULATORY,
            event_type="notice",
            source_org="SEBI",
            ingested_at=aware_dt,
            published_at=aware_dt,
            url="ftp://invalid-url.com",
        )


def test_macro_event_stable_deterministic_id() -> None:
    dt1 = datetime(2026, 10, 15, 12, 0, tzinfo=IST)
    ev1 = MacroEvent(
        title="Repo Rate Announcement",
        category=EventCategory.MONETARY_POLICY,
        event_type="repo_rate",
        source_org="RBI",
        ingested_at=dt1,
        published_at=dt1,
    )
    ev2 = MacroEvent(
        title="Repo Rate Announcement",
        category=EventCategory.MONETARY_POLICY,
        event_type="repo_rate",
        source_org="RBI",
        ingested_at=dt1 + timedelta(minutes=5),  # Different ingested time
        published_at=dt1,                       # Same published time
    )
    assert ev1.event_id == ev2.event_id


# ---------------------------------------------------------------------------
# External Market Observation Tests
# ---------------------------------------------------------------------------

def test_external_market_observation_valid_construction() -> None:
    now_ist = datetime(2026, 10, 15, 18, 0, tzinfo=IST)
    obs = ExternalMarketObservation(
        series_id="BRENT_CRUDE",
        timestamp=now_ist,
        ingested_at=now_ist,
        close=105.80,
        unit="USD/barrel",
        open=104.50,
        high=106.20,
        low=104.10,
        daily_return=0.01244,
        source="yfinance",
    )

    assert obs.series_id == "BRENT_CRUDE"
    assert obs.close == 105.80
    assert obs.unit == "USD/barrel"
    assert obs.daily_return == 0.01244
    assert len(obs.observation_id) == 16

    # Verify conversion to MacroEvent
    ev = obs.to_event()
    assert ev.category == EventCategory.EXTERNAL_MARKET
    assert ev.event_type == "brent_crude_observation"
    assert ev.structured_value is not None
    assert ev.structured_value.metric_name == "brent_crude"
    assert ev.structured_value.value == 105.80


def test_external_market_observation_rejects_negative_or_nan_prices() -> None:
    now_ist = datetime(2026, 10, 15, 18, 0, tzinfo=IST)
    with pytest.raises(ValidationError, match="close must be a positive finite number"):
        ExternalMarketObservation(
            series_id="BRENT_CRUDE",
            timestamp=now_ist,
            ingested_at=now_ist,
            close=-10.0,
            unit="USD/barrel",
        )

    with pytest.raises(ValidationError, match="close must be a positive finite number"):
        ExternalMarketObservation(
            series_id="BRENT_CRUDE",
            timestamp=now_ist,
            ingested_at=now_ist,
            close=float("nan"),
            unit="USD/barrel",
        )


# ---------------------------------------------------------------------------
# Deduplication Tests
# ---------------------------------------------------------------------------

def test_deduplicate_events_identical_ids_and_urls() -> None:
    dt1 = datetime(2026, 10, 15, 10, 0, tzinfo=IST)
    dt2 = datetime(2026, 10, 15, 11, 0, tzinfo=IST)

    ev1 = MacroEvent(
        title="SEBI Master Circular for Intermediaries",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        ingested_at=dt1,
        published_at=dt1,
        url="https://sebi.gov.in/circ/100",
        event_id="sebi_circ_100",
    )
    # Duplicate ID
    ev2 = MacroEvent(
        title="SEBI Master Circular for Intermediaries (Duplicate)",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        ingested_at=dt2,
        published_at=dt2,
        event_id="sebi_circ_100",
    )
    # Duplicate URL
    ev3 = MacroEvent(
        title="SEBI Master Circular (Alt Title)",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        ingested_at=dt2,
        published_at=dt2,
        url="https://sebi.gov.in/circ/100",
        event_id="sebi_circ_101",
    )

    res = deduplicate_events([ev1, ev2, ev3])
    assert res.summary.total_input == 3
    assert res.summary.unique_count == 1
    assert res.summary.duplicates_removed == 2
    assert len(res.events) == 1
    assert res.events[0].event_id == "sebi_circ_100"


def test_deduplicate_events_syndicated_titles_within_window() -> None:
    t0 = datetime(2026, 10, 15, 10, 0, tzinfo=IST)
    t1 = t0 + timedelta(hours=12)
    t2 = t0 + timedelta(hours=80)  # Outside 72h window

    ev1 = MacroEvent(
        title="RBI Monetary Policy Committee Announcement",
        category=EventCategory.MONETARY_POLICY,
        event_type="mpc",
        source_org="RBI",
        ingested_at=t0,
        published_at=t0,
        event_id="ev_rbi_1",
    )
    # Identical title within 72h -> duplicate
    ev2 = MacroEvent(
        title="RBI Monetary Policy Committee Announcement!",
        category=EventCategory.MONETARY_POLICY,
        event_type="mpc",
        source_org="RBI",
        ingested_at=t1,
        published_at=t1,
        event_id="ev_rbi_2",
    )
    # Same title after 80h -> not a duplicate
    ev3 = MacroEvent(
        title="RBI Monetary Policy Committee Announcement",
        category=EventCategory.MONETARY_POLICY,
        event_type="mpc",
        source_org="RBI",
        ingested_at=t2,
        published_at=t2,
        event_id="ev_rbi_3",
    )

    res = deduplicate_events([ev1, ev2, ev3], window_hours=72)
    assert res.summary.total_input == 3
    assert res.summary.unique_count == 2
    assert res.summary.duplicates_removed == 1
    # Both ev3 and ev1 are retained
    retained_ids = {e.event_id for e in res.events}
    assert retained_ids == {"ev_rbi_1", "ev_rbi_3"}


def test_deduplicate_events_empty_input() -> None:
    res = deduplicate_events([])
    assert res.summary.total_input == 0
    assert res.summary.unique_count == 0
    assert len(res.events) == 0


# ---------------------------------------------------------------------------
# Point-in-Time Filtering Tests
# ---------------------------------------------------------------------------

def test_filter_events_point_in_time_exact_cutoff_and_exclusion() -> None:
    cutoff = datetime(2026, 10, 15, 15, 30, tzinfo=IST)

    # 1. Exactly at cutoff -> eligible
    ev_at = MacroEvent(
        title="At Cutoff",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=cutoff,
        ingested_at=cutoff,
        event_id="ev_at",
    )
    # 2. Before cutoff -> eligible
    ev_before = MacroEvent(
        title="Before Cutoff",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=cutoff - timedelta(hours=2),
        ingested_at=cutoff - timedelta(hours=1),
        event_id="ev_before",
    )
    # 3. Published after cutoff -> strictly excluded
    ev_future_pub = MacroEvent(
        title="Future Published",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=cutoff + timedelta(minutes=1),
        ingested_at=cutoff - timedelta(hours=1),
        event_id="ev_fut_pub",
    )
    # 4. Ingested after cutoff -> strictly excluded
    ev_future_ing = MacroEvent(
        title="Future Ingested",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=cutoff - timedelta(hours=2),
        ingested_at=cutoff + timedelta(minutes=1),
        event_id="ev_fut_ing",
    )

    eligible = filter_events_point_in_time([ev_at, ev_before, ev_future_pub, ev_future_ing], as_of_time=cutoff)
    assert len(eligible) == 2
    eligible_ids = {e.event_id for e in eligible}
    assert eligible_ids == {"ev_at", "ev_before"}


def test_filter_events_point_in_time_preserves_effective_dates() -> None:
    cutoff = datetime(2026, 10, 15, 15, 30, tzinfo=IST)
    effective_future = datetime(2026, 10, 19, 9, 15, tzinfo=IST)  # Monday morning

    # Circular announced before cutoff, but takes effect in the future
    ev_effective_future = MacroEvent(
        title="Rule Change Effective Next Week",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=cutoff - timedelta(hours=3),
        ingested_at=cutoff - timedelta(hours=2),
        effective_at=effective_future,
        event_id="ev_effective_future",
    )

    eligible = filter_events_point_in_time([ev_effective_future], as_of_time=cutoff)
    assert len(eligible) == 1
    assert eligible[0].effective_at == effective_future  # Preserved uncorrupted


def test_filter_events_point_in_time_lookback_window() -> None:
    cutoff = datetime(2026, 10, 15, 15, 30, tzinfo=IST)

    ev_recent = MacroEvent(
        title="Recent Notice",
        category=EventCategory.REGULATORY,
        event_type="notice",
        source_org="SEBI",
        published_at=cutoff - timedelta(days=2),
        ingested_at=cutoff - timedelta(days=2),
        event_id="ev_recent",
    )
    ev_old = MacroEvent(
        title="Old Notice",
        category=EventCategory.REGULATORY,
        event_type="notice",
        source_org="SEBI",
        published_at=cutoff - timedelta(days=10),
        ingested_at=cutoff - timedelta(days=10),
        event_id="ev_old",
    )

    eligible = filter_events_point_in_time([ev_recent, ev_old], as_of_time=cutoff, lookback_window=timedelta(days=7))
    assert len(eligible) == 1
    assert eligible[0].event_id == "ev_recent"


# ---------------------------------------------------------------------------
# Provider Tests (RBI & SEBI & External Market)
# ---------------------------------------------------------------------------

def test_rbi_provider_parses_sample_xml() -> None:
    provider = RBIEventProvider(fetcher=lambda url: SAMPLE_RBI_XML)
    events = provider.fetch_events(limit=10)

    assert len(events) == 2
    # Verify Monetary Policy classification and repo rate extraction
    mpc_ev = next(e for e in events if e.category == EventCategory.MONETARY_POLICY)
    assert "Repo rate" in mpc_ev.title
    assert mpc_ev.event_type == "monetary_policy_statement"
    assert mpc_ev.source_org == "Reserve Bank of India"
    assert mpc_ev.structured_value is not None
    assert mpc_ev.structured_value.metric_name == "repo_rate"
    assert mpc_ev.structured_value.value == 6.50
    assert mpc_ev.structured_value.unit == "percent"
    assert mpc_ev.affected_sectors == ("BANKING", "FINANCIAL_SERVICES")

    # Verify standard regulatory press release
    auction_ev = next(e for e in events if e.category == EventCategory.REGULATORY)
    assert "Auction of State Government" in auction_ev.title
    assert auction_ev.event_type == "press_release"


def test_rbi_provider_handles_malformed_xml() -> None:
    provider = RBIEventProvider(fetcher=lambda url: "<broken><xml>")
    with pytest.raises(EventProviderError, match="Malformed RBI RSS XML"):
        provider.fetch_events()


def test_rbi_provider_handles_empty_response() -> None:
    provider = RBIEventProvider(fetcher=lambda url: "")
    events = provider.fetch_events()
    assert events == []


def test_sebi_provider_parses_sample_xml() -> None:
    provider = SEBIEventProvider(fetcher=lambda url: SAMPLE_SEBI_XML)
    events = provider.fetch_events(limit=10)

    assert len(events) == 2
    circ_ev = next(e for e in events if e.event_type == "master_circular")
    assert "Master Circular for Mutual Funds" in circ_ev.title
    assert circ_ev.category == EventCategory.REGULATORY
    assert circ_ev.source_org == "Securities and Exchange Board of India"
    assert circ_ev.affected_sectors == ("EQUITY_MARKET",)
    assert circ_ev.published_at is not None
    assert circ_ev.published_at.tzinfo is not None

    order_ev = next(e for e in events if e.event_type == "enforcement_order")
    assert "Adjudication Order" in order_ev.title


def test_sebi_provider_handles_malformed_xml() -> None:
    provider = SEBIEventProvider(fetcher=lambda url: "<broken><sebi>")
    with pytest.raises(EventProviderError, match="Malformed SEBI RSS XML"):
        provider.fetch_events()


def test_external_market_provider_offline_mock() -> None:
    dt1 = datetime(2026, 10, 14, 18, 0, tzinfo=IST)
    dt2 = datetime(2026, 10, 15, 18, 0, tzinfo=IST)

    mock_data = {
        "BZ=F": [
            {"timestamp": dt1, "open": 100.0, "high": 102.0, "low": 99.0, "close": 100.0},
            {"timestamp": dt2, "open": 100.0, "high": 105.0, "low": 99.5, "close": 104.0},
        ],
        "INR=X": [
            {"timestamp": dt1, "open": 95.0, "high": 95.2, "low": 94.9, "close": 95.0},
            {"timestamp": dt2, "open": 95.0, "high": 95.5, "low": 94.9, "close": 95.2},
        ],
    }

    def mock_downloader(ticker: str, start: datetime, end: datetime):
        return mock_data.get(ticker, [])

    provider = ExternalMarketProvider(downloader=mock_downloader)
    observations = provider.fetch_observations(series_ids=["BRENT_CRUDE", "USD_INR"])

    assert len(observations) == 4
    brent_obs = [o for o in observations if o.series_id == "BRENT_CRUDE"]
    assert len(brent_obs) == 2
    # Verify daily return calculation
    latest_brent = next(o for o in brent_obs if o.timestamp == dt2)
    assert latest_brent.close == 104.0
    assert latest_brent.daily_return == 0.04  # (104 - 100) / 100

    # Verify event mapping
    events = provider.fetch_events(limit=5)
    assert len(events) == 4
    assert all(e.category == EventCategory.EXTERNAL_MARKET for e in events)


def test_primary_timestamp_does_not_conflate_effective_at() -> None:
    """Verify that effective_at is never conflated with information availability."""
    ingested_time = datetime(2026, 10, 14, 10, 0, tzinfo=IST)
    pub_time = datetime(2026, 10, 14, 11, 0, tzinfo=IST)
    ann_time = datetime(2026, 10, 14, 10, 30, tzinfo=IST)
    eff_time = datetime(2026, 10, 20, 0, 0, tzinfo=IST)  # Future legal effective date

    # Case 1: published_at present
    ev1 = MacroEvent(
        title="Event With Publication and Effective",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        ingested_at=ingested_time,
        published_at=pub_time,
        effective_at=eff_time,
    )
    assert ev1.primary_timestamp == pub_time
    assert ev1.effective_at == eff_time

    # Case 2: Only announced_at and effective_at present
    ev2 = MacroEvent(
        title="Event With Announcement and Effective",
        category=EventCategory.MONETARY_POLICY,
        event_type="policy",
        source_org="RBI",
        ingested_at=ingested_time,
        announced_at=ann_time,
        effective_at=eff_time,
    )
    assert ev2.primary_timestamp == ann_time
    assert ev2.effective_at == eff_time

    # Case 3: Only effective_at present (no published_at, no announced_at)
    # primary_timestamp must fall back to ingested_at, NEVER future effective_at
    ev3 = MacroEvent(
        title="Event With Only Effective Date",
        category=EventCategory.REGULATORY,
        event_type="guideline",
        source_org="SEBI",
        ingested_at=ingested_time,
        effective_at=eff_time,
    )
    assert ev3.primary_timestamp == ingested_time
    assert ev3.primary_timestamp != eff_time
    assert ev3.effective_at == eff_time


def test_rbi_provider_sort_before_limit_and_word_boundaries() -> None:
    """Verify RBI provider sorts chronologically before limiting and doesn't trigger false positive substrings."""
    # Feed with older item first, newer item second, and a title with substring 'occurrence' and 'referral'
    xml_data = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <title>Reserve Bank of India - Press Releases</title>
        <item>
          <title>Occurrence of Operational Audit and Referral Process</title>
          <link>https://rbi.org.in/pr1.html</link>
          <pubDate>Wed, 14 Oct 2026 10:00:00</pubDate>
          <description>General operational review.</description>
        </item>
        <item>
          <title>Monetary Policy Committee Resolution: Policy Repo Rate Remains at 6.50%</title>
          <link>https://rbi.org.in/pr2.html</link>
          <pubDate>Thu, 15 Oct 2026 14:00:00</pubDate>
          <description>Repo rate maintained by MPC resolution.</description>
        </item>
      </channel>
    </rss>
    """
    provider = RBIEventProvider(fetcher=lambda url: xml_data)
    # Limit to 1: Must return the NEWEST item (Oct 15), not the first item in the feed (Oct 14)
    events = provider.fetch_events(limit=1)
    assert len(events) == 1
    assert "Monetary Policy Committee" in events[0].title
    assert events[0].category == EventCategory.MONETARY_POLICY

    # Fetch all items to verify word-boundary classification
    all_events = provider.fetch_events(limit=10)
    assert len(all_events) == 2
    # The 'Occurrence ... Referral' item must NOT be classified as monetary_policy (no false positive on 'crr' or 'slr')
    non_monetary_event = next(e for e in all_events if "Occurrence" in e.title)
    assert non_monetary_event.category == EventCategory.REGULATORY
    assert non_monetary_event.event_type == "press_release"


def test_sebi_provider_parsing_and_precision() -> None:
    """Verify SEBI provider XML parsing, custom date format, date_only precision tracking, and sort-before-limit."""
    xml_data = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <title>SEBI Press Releases and Circulars</title>
        <item>
          <title>Circular on Framework for Margin Trading Facility</title>
          <link>https://sebi.gov.in/circ1.html</link>
          <pubDate>14 Oct, 2026 +0530</pubDate>
          <description>Circular guidelines for brokers.</description>
        </item>
        <item>
          <title>Master Circular for Mutual Funds</title>
          <link>https://sebi.gov.in/circ2.html</link>
          <pubDate>16 Oct, 2026 +0530</pubDate>
          <description>Master circular compilation.</description>
        </item>
      </channel>
    </rss>
    """
    provider = SEBIEventProvider(fetcher=lambda url: xml_data)
    # Limit to 1: Must return the NEWEST item (Oct 16 Master Circular), not the first item (Oct 14)
    events = provider.fetch_events(limit=1)
    assert len(events) == 1
    assert events[0].event_type == "master_circular"
    assert events[0].published_at.date() == datetime(2026, 10, 16).date()
    assert events[0].raw_metadata.get("time_precision") == "date_only"


def test_external_market_provider_zero_return_and_custom_ingested_at() -> None:
    """Verify zero return is preserved as 0.0 and custom ingested_at timestamp is supported."""
    dt1 = datetime(2026, 10, 14, 18, 0, tzinfo=IST)
    dt2 = datetime(2026, 10, 15, 18, 0, tzinfo=IST)
    custom_ingest = datetime(2026, 10, 15, 20, 0, tzinfo=IST)

    # Identical prices on both days -> 0.0% return
    mock_data = {
        "BZ=F": [
            {"timestamp": dt1, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
            {"timestamp": dt2, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
        ],
    }

    provider = ExternalMarketProvider(downloader=lambda ticker, s, e: mock_data.get(ticker, []))
    observations = provider.fetch_observations(
        series_ids=["BRENT_CRUDE"],
        ingested_at=custom_ingest,
    )
    assert len(observations) == 2
    # Check that day 2 has explicit 0.0 daily return, not None
    day2_obs = next(o for o in observations if o.timestamp == dt2)
    assert day2_obs.daily_return == 0.0
    assert day2_obs.ingested_at == custom_ingest

    # Check event translation
    ev = day2_obs.to_event()
    assert ev.structured_value.change == 0.0


def test_sebi_provider_safe_keyword_classification() -> None:
    """Regression test: verify 'in order to' and 'border' are not misclassified as enforcement orders."""
    xml_data = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <title>SEBI Notices</title>
        <item>
          <title>Advisory in order to enhance cybersecurity and operational resilience</title>
          <link>https://sebi.gov.in/advisory.html</link>
          <pubDate>16 Oct, 2026 +0530</pubDate>
          <description>Advisory guidelines.</description>
        </item>
        <item>
          <title>Framework for cross border securities issuance</title>
          <link>https://sebi.gov.in/border.html</link>
          <pubDate>15 Oct, 2026 +0530</pubDate>
          <description>Border framework.</description>
        </item>
        <item>
          <title>Adjudication Order in respect of ABC Securities Ltd</title>
          <link>https://sebi.gov.in/order1.html</link>
          <pubDate>14 Oct, 2026 +0530</pubDate>
          <description>Penalty order.</description>
        </item>
      </channel>
    </rss>
    """
    provider = SEBIEventProvider(fetcher=lambda url: xml_data)
    events = provider.fetch_events(limit=10)

    advisory_ev = next(e for e in events if "in order to" in e.title.lower())
    border_ev = next(e for e in events if "cross border" in e.title.lower())
    order_ev = next(e for e in events if "adjudication order" in e.title.lower())

    # 'in order to' and 'cross border' must NOT be enforcement_order
    assert advisory_ev.event_type == "regulatory_notice"
    assert border_ev.event_type == "regulatory_notice"
    # Genuine adjudication order must be enforcement_order
    assert order_ev.event_type == "enforcement_order"


def test_rbi_and_sebi_custom_ingested_at_support() -> None:
    """Regression test: verify explicit ingested_at can be passed to RBI and SEBI providers."""
    custom_dt = datetime(2026, 10, 10, 10, 0, tzinfo=IST)
    rbi_provider = RBIEventProvider(fetcher=lambda url: SAMPLE_RBI_XML)
    rbi_events = rbi_provider.fetch_events(limit=5, ingested_at=custom_dt)
    assert len(rbi_events) > 0
    assert all(e.ingested_at == custom_dt for e in rbi_events)

    sebi_provider = SEBIEventProvider(fetcher=lambda url: SAMPLE_SEBI_XML)
    sebi_events = sebi_provider.fetch_events(limit=5, ingested_at=custom_dt)
    assert len(sebi_events) > 0
    assert all(e.ingested_at == custom_dt for e in sebi_events)
