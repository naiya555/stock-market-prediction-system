"""Adversarial and bounding regression tests for RSS and external-feed parsers.

Verifies remediation of CodeRabbit Deep Scan findings:
- 1ec5f892-7f69-4c52-80dd-1df78aab9991 (app/news/providers/rss_provider.py)
- 11905224-342d-4afb-b670-04d4ddcc860a (app/events/providers/rbi_provider.py)
- 08bc0d39-09ed-4451-842b-5e4369cfabe6 (app/events/providers/rbi_provider.py)
"""

from datetime import datetime, timezone
import pytest

from app.events.providers.rbi_provider import (
    MAX_RBI_PAYLOAD_CHARS,
    RBIEventProvider,
    _extract_repo_rate_value,
    _strip_html,
)
from app.events.providers.sebi_provider import (
    MAX_SEBI_PAYLOAD_CHARS,
    SEBIEventProvider,
)
from app.news.providers.rss_provider import (
    MAX_RSS_PAYLOAD_BYTES,
    RSSNewsProvider,
    _strip_html_tags as rss_strip_html_tags,
)


def test_strip_html_tags_adversarial_unmatched_brackets():
    """Verify linear-time tag stripper handles massive unmatched opening brackets without catastrophic backtracking."""
    # 50,000 unclosed opening brackets that would cause catastrophic backtracking in vulnerable regexes
    adversarial_markup = "<" * 50_000 + "div style='color:red'" + "<span" * 10_000
    cleaned = _strip_html(adversarial_markup)

    assert isinstance(cleaned, str)
    assert len(cleaned) <= len(adversarial_markup)

    # Test RSS tag stripper as well
    rss_cleaned = rss_strip_html_tags(adversarial_markup)
    assert isinstance(rss_cleaned, str)


def test_strip_html_tags_normal_markup():
    """Verify valid HTML markup is correctly stripped down to readable text."""
    markup = "<p>Reserve Bank of India <b>announces</b> repo rate hike. <a href='https://rbi.org.in'>Read more</a></p>"
    stripped = _strip_html(markup)
    assert stripped == "Reserve Bank of India announces repo rate hike. Read more"


def test_extract_repo_rate_adversarial_repeated_prefix():
    """Verify repo rate extraction scanner handles repeated prefixes without exponential rescanning."""
    # Repeated prefix text without any decimal number
    repeated_prefix = "the policy repo rate under the liquidity adjustment facility was kept unchanged at " * 30
    res = _extract_repo_rate_value(repeated_prefix)
    assert res is None

    # Appending a valid rate at the end is extracted correctly
    valid_text = repeated_prefix + "6.50 per cent"
    res_valid = _extract_repo_rate_value(valid_text)
    assert res_valid is not None
    assert res_valid.value == 6.50


def test_extract_repo_rate_normal_patterns():
    """Verify standard RBI circular rate announcement phrasing is extracted accurately."""
    samples = [
        ("The Monetary Policy Committee decided to keep the policy repo rate unchanged at 6.50%", 6.50),
        ("The policy repo rate under the liquidity adjustment facility (LAF) was reduced by 25 bps to 6.25 per cent", 6.25),
        ("decided to increase the policy repo rate by 50 basis points to 5.40 per cent with immediate effect", 5.40),
    ]
    for text, expected_rate in samples:
        event_val = _extract_repo_rate_value(text)
        assert event_val is not None, f"Failed for '{text}': returned None"
        assert event_val.value == expected_rate, f"Failed for '{text}': expected {expected_rate}, got {event_val.value}"


def test_oversized_payload_rejection_in_providers():
    """Verify RBI, SEBI, and RSS providers guard against oversized payloads beyond bounded limits."""
    from app.events.providers.base import EventProviderError
    from app.news.providers.base import NewsProviderError

    rbi = RBIEventProvider()
    sebi = SEBIEventProvider()
    rss = RSSNewsProvider()

    huge_content = "<item><title>Test</title></item>" * (MAX_RBI_PAYLOAD_CHARS // 30 + 10)

    # Parsing payloads exceeding max characters should safely raise EventProviderError
    with pytest.raises(EventProviderError, match="exceeds maximum allowed size"):
        rbi._parse_xml(huge_content)

    with pytest.raises(EventProviderError, match="exceeds maximum allowed size"):
        sebi._parse_xml(huge_content)

    huge_bytes = b"<rss><channel><item><title>X</title></item></channel></rss>" * (MAX_RSS_PAYLOAD_BYTES // 50 + 10)
    with pytest.raises(NewsProviderError, match="exceeds maximum allowed size"):
        rss.parse_rss_payload(huge_bytes, "RELIANCE")
