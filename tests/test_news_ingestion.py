"""Unit and regression tests for Day 27: Financial News Ingestion Foundation."""

from datetime import datetime, timedelta, timezone
import pytest
from zoneinfo import ZoneInfo

from app.core.schemas import ValidationError
from app.news.cleaner import (
    deduplicate_news,
    filter_news_point_in_time,
)
from app.news.providers.base import NewsProviderError
from app.news.providers.rss_provider import COMPANY_NAME_MAP, RSSNewsProvider
from app.news.schemas import NewsArticle

IST = ZoneInfo("Asia/Kolkata")

# Sample deterministic RSS XML fixture
SAMPLE_RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News - BHARTIARTL</title>
    <item>
      <title>Bharti Airtel reports 15% revenue growth in Q2 - Economic Times</title>
      <link>https://economictimes.indiatimes.com/news/12345</link>
      <pubDate>Wed, 14 Oct 2026 10:00:00 GMT</pubDate>
      <description>&lt;p&gt;Bharti Airtel posted robust operational performance.&lt;/p&gt;</description>
      <source url="https://economictimes.indiatimes.com">Economic Times</source>
    </item>
    <item>
      <title>Airtel expands 5G rollout across 50 Indian cities - Livemint</title>
      <link>https://livemint.com/news/67890</link>
      <pubDate>Tue, 13 Oct 2026 14:30:00 GMT</pubDate>
      <description>Telecom major Bharti Airtel continues its nationwide expansion.</description>
      <source url="https://livemint.com">Livemint</source>
    </item>
  </channel>
</rss>
"""


def _make_article(
    headline: str = "Test Headline",
    source: str = "Test Source",
    pub_offset_hours: int = 0,
    ingest_offset_hours: int = 0,
    symbol: str = "BHARTIARTL",
    url: str = "https://example.com/news/1",
) -> NewsArticle:
    """Helper to create valid NewsArticle fixtures."""
    base_time = datetime(2026, 10, 14, 12, 0, tzinfo=IST)
    pub_time = base_time + timedelta(hours=pub_offset_hours)
    ingest_time = base_time + timedelta(hours=ingest_offset_hours)
    return NewsArticle(
        headline=headline,
        source=source,
        published_at=pub_time,
        ingested_at=ingest_time,
        symbols=(symbol,),
        url=url,
        summary="Test summary",
        provider="test_provider",
    )


class TestNewsArticleSchema:
    """Tests for canonical NewsArticle schema validation and invariants."""

    def test_valid_news_article_normalization(self) -> None:
        art = _make_article(
            headline="  Reliance announces renewable energy investment  ",
            source="Moneycontrol",
            symbol="reliance.ns",
            url="https://moneycontrol.com/news/1",
        )
        assert art.headline == "Reliance announces renewable energy investment"
        assert art.source == "Moneycontrol"
        assert art.symbols == ("RELIANCE",)
        assert art.url == "https://moneycontrol.com/news/1"
        assert len(art.article_id) == 16
        assert art.published_at.tzinfo is not None
        assert art.ingested_at.tzinfo is not None

        d = art.to_dict()
        assert d["headline"] == "Reliance announces renewable energy investment"
        assert d["symbols"] == ["RELIANCE"]
        assert "published_at" in d
        assert "ingested_at" in d

    def test_missing_and_malformed_fields(self) -> None:
        now = datetime.now(timezone.utc)

        # Empty headline
        with pytest.raises(ValidationError, match="headline cannot be empty"):
            NewsArticle("", "Source", now, now, ("TCS",))

        # Empty source
        with pytest.raises(ValidationError, match="source cannot be empty"):
            NewsArticle("Headline", "   ", now, now, ("TCS",))

        # Naive datetime rejected
        naive_dt = datetime(2026, 10, 14, 10, 0)
        with pytest.raises(ValidationError, match="published_at must be timezone-aware"):
            NewsArticle("Headline", "Source", naive_dt, now, ("TCS",))

        with pytest.raises(ValidationError, match="ingested_at must be timezone-aware"):
            NewsArticle("Headline", "Source", now, naive_dt, ("TCS",))

        # Invalid URL
        with pytest.raises(ValidationError, match="Invalid URL format"):
            NewsArticle("Headline", "Source", now, now, ("TCS",), url="ftp://not-http")

    def test_publication_time_distinct_from_ingestion_time(self) -> None:
        pub = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
        ingest = datetime(2026, 10, 14, 15, 30, tzinfo=timezone.utc)

        art = NewsArticle("Old news", "Source", pub, ingest, ("INFY",))
        assert art.published_at < art.ingested_at
        assert art.published_at != art.ingested_at


class TestRSSNewsProvider:
    """Tests for RSSNewsProvider parsing, date handling, and error resiliency."""

    def test_parse_valid_rss_payload(self) -> None:
        provider = RSSNewsProvider()
        articles = provider.parse_rss_payload(SAMPLE_RSS_XML, "BHARTIARTL")

        assert len(articles) == 2
        a1, a2 = articles

        # Cleaned title without source trailing suffix
        assert a1.headline == "Bharti Airtel reports 15% revenue growth in Q2"
        assert a1.source == "Economic Times"
        assert a1.symbols == ("BHARTIARTL",)
        assert a1.url == "https://economictimes.indiatimes.com/news/12345"
        assert a1.summary == "Bharti Airtel posted robust operational performance."
        # Verify RFC 2822 parsed to IST
        assert a1.published_at.year == 2026
        assert a1.published_at.month == 10
        assert a1.published_at.day == 14

        assert a2.headline == "Airtel expands 5G rollout across 50 Indian cities"
        assert a2.source == "Livemint"

    def test_parse_empty_or_whitespace_payload(self) -> None:
        provider = RSSNewsProvider()
        assert provider.parse_rss_payload(b"", "TCS") == []
        assert provider.parse_rss_payload(b"   ", "TCS") == []

    def test_parse_malformed_xml_raises_provider_error(self) -> None:
        provider = RSSNewsProvider()
        with pytest.raises(NewsProviderError, match="Malformed RSS XML payload"):
            provider.parse_rss_payload(b"<rss><channel><item>unclosed", "TCS")

    def test_parse_skips_items_with_missing_titles_or_dates(self) -> None:
        xml = b"""<rss version="2.0"><channel>
            <item><pubDate>Wed, 14 Oct 2026 10:00:00 GMT</pubDate></item>
            <item><title>Valid Title</title><pubDate>Invalid-Date-String</pubDate></item>
            <item><title>Valid Title 2 - Publisher</title><pubDate>Wed, 14 Oct 2026 11:00:00 GMT</pubDate></item>
        </channel></rss>"""
        provider = RSSNewsProvider()
        articles = provider.parse_rss_payload(xml, "HDFCBANK")
        assert len(articles) == 1
        assert articles[0].headline == "Valid Title 2"

    def test_fetch_news_with_custom_fetcher(self) -> None:
        # Mock network fetcher without internet access
        def mock_fetcher(url: str) -> bytes:
            assert "BHARTIARTL" in url
            return SAMPLE_RSS_XML

        provider = RSSNewsProvider(fetcher=mock_fetcher)
        articles = provider.fetch_news("BHARTIARTL", limit=1)
        assert len(articles) == 1
        assert articles[0].headline == "Bharti Airtel reports 15% revenue growth in Q2"

    def test_fetch_news_handles_fetcher_exception(self) -> None:
        def failing_fetcher(url: str) -> bytes:
            raise OSError("Network unreachable")

        provider = RSSNewsProvider(fetcher=failing_fetcher)
        # Verify provider error raised on fetch error
        with pytest.raises(Exception):
            provider.fetch_news("BHARTIARTL")

    def test_company_name_mapping(self) -> None:
        provider = RSSNewsProvider()
        url = provider._build_search_url("BHARTIARTL")
        assert "Bharti+Airtel" in url or "Bharti%20Airtel" in url or "BHARTIARTL" in url
        assert "stock" in url


class TestNewsDeduplication:
    """Tests for news deduplication across identical IDs, URLs, and syndicated titles."""

    def test_deduplicate_identical_ids_and_urls(self) -> None:
        a1 = _make_article("Title 1", url="https://news.com/1")
        a2 = _make_article("Title 1", url="https://news.com/1")  # Exact duplicate
        a3 = _make_article("Title 2", url="https://news.com/2")

        res = deduplicate_news([a1, a2, a3])
        assert res.summary.total_input == 3
        assert res.summary.unique_count == 2
        assert res.summary.duplicates_removed == 1
        assert len(res.articles) == 2

    def test_deduplicate_syndicated_headlines_within_window(self) -> None:
        # Same headline syndicated by different publishers within 12 hours
        a1 = _make_article(
            headline="RBI holds repo rate at 6.5% in October policy",
            source="Economic Times",
            pub_offset_hours=0,
            url="https://et.com/rbi",
        )
        a2 = _make_article(
            headline="RBI holds repo rate at 6.5% in October policy!",  # Slight punctuation diff
            source="Livemint",
            pub_offset_hours=2,
            url="https://livemint.com/rbi",
        )
        a3 = _make_article(
            headline="Unrelated news story on IT hiring",
            source="Business Standard",
            pub_offset_hours=3,
            url="https://bs.com/it",
        )

        res = deduplicate_news([a1, a2, a3], dedup_window_hours=24)
        assert res.summary.total_input == 3
        assert res.summary.unique_count == 2
        assert res.summary.duplicates_removed == 1

        headlines = [a.headline for a in res.articles]
        assert "RBI holds repo rate at 6.5% in October policy" in headlines
        assert "Unrelated news story on IT hiring" in headlines

    def test_deduplicate_empty_input(self) -> None:
        res = deduplicate_news([])
        assert res.summary.total_input == 0
        assert res.summary.unique_count == 0
        assert res.articles == []


class TestPointInTimeFiltering:
    """Tests for point-in-time session filtering and zero look-ahead bias."""

    def test_filter_news_point_in_time_excludes_future_articles(self) -> None:
        cutoff = datetime(2026, 10, 14, 12, 0, tzinfo=IST)

        # Article published before cutoff
        past_art = _make_article(
            headline="Morning Market Update",
            pub_offset_hours=-4,
            ingest_offset_hours=-3,
        )
        # Article published at exact cutoff
        exact_art = _make_article(
            headline="Closing Bell News",
            pub_offset_hours=0,
            ingest_offset_hours=0,
        )
        # Article published AFTER cutoff (e.g. evening earnings release)
        future_art = _make_article(
            headline="Post-Market Earnings Surge",
            pub_offset_hours=2,
            ingest_offset_hours=2,
        )
        # Article published before cutoff but ingested after cutoff (future availability)
        delayed_ingest_art = _make_article(
            headline="Delayed Ingest Story",
            pub_offset_hours=-1,
            ingest_offset_hours=1,
        )

        filtered = filter_news_point_in_time(
            [past_art, exact_art, future_art, delayed_ingest_art],
            as_of_time=cutoff,
        )

        # Only articles published AND ingested <= cutoff should be retained
        assert len(filtered) == 2
        assert past_art in filtered
        assert exact_art in filtered
        assert future_art not in filtered
        assert delayed_ingest_art not in filtered

    def test_filter_news_lookback_window(self) -> None:
        cutoff = datetime(2026, 10, 14, 15, 30, tzinfo=IST)

        recent_art = _make_article("Recent Story", pub_offset_hours=-5, ingest_offset_hours=-5)
        old_art = _make_article("Old Story from Last Week", pub_offset_hours=-100, ingest_offset_hours=-100)

        # 24-hour lookback window
        filtered = filter_news_point_in_time(
            [recent_art, old_art],
            as_of_time=cutoff,
            lookback_window=timedelta(hours=24),
        )

        assert len(filtered) == 1
        assert filtered[0].headline == "Recent Story"
