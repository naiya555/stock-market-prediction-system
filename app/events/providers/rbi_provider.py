"""Reserve Bank of India (RBI) Press Releases and Monetary Policy Event Provider.

Acquires and normalizes official press releases, Monetary Policy Committee (MPC)
decisions, and regulatory announcements directly from the official RBI RSS feed.
"""

from datetime import datetime, timezone
import email.utils
import html
import re
from typing import Callable, List, Optional
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from app.core.logging_config import get_logger
from app.events.providers.base import BaseEventProvider, EventProviderError
from app.events.schemas import EventCategory, MacroEvent, StructuredEventValue

logger = get_logger(__name__)

RBI_RSS_ENDPOINT = "https://rbi.org.in/pressreleases_rss.xml"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StockMarketPrediction/1.0"
IST = ZoneInfo("Asia/Kolkata")


MAX_RBI_PAYLOAD_CHARS = 5_000_000


def _strip_html(text: str, max_length: int = 100_000) -> str:
    """Remove HTML markup, unescape entities, and collapse whitespace in linear O(N) time."""
    if not text:
        return ""
    if len(text) > max_length:
        text = text[:max_length]
    out = []
    in_tag = False
    for ch in text:
        if ch == "<":
            in_tag = True
            out.append(" ")
        elif ch == ">":
            in_tag = False
        elif not in_tag:
            out.append(ch)
    clean = html.unescape("".join(out))
    return " ".join(clean.split())


def _parse_rbi_date(date_str: str) -> datetime:
    """Parse RBI publication timestamp and localize to Asia/Kolkata (IST)."""
    clean_date = date_str.strip()
    try:
        dt = email.utils.parsedate_to_datetime(clean_date)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=IST)
        return dt.astimezone(IST)
    except Exception:
        # Fallback strptime patterns
        for fmt in (
            "%a, %d %b %Y %H:%M:%S",
            "%d %b %Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
        ):
            try:
                naive = datetime.strptime(clean_date, fmt)
                return naive.replace(tzinfo=IST)
            except ValueError:
                continue
    raise ValueError(f"Could not parse RBI date: '{date_str}'")


def _extract_repo_rate_value(text: str, max_length: int = 20_000) -> Optional[StructuredEventValue]:
    """Scan title and summary for explicit repo rate percentage changes or levels with linear bounded search."""
    if not text:
        return None
    bounded = text[:max_length]
    lower = bounded.lower()
    start = 0
    pattern_pct = re.compile(r"^[^\n%]{0,120}?(\d+\.\d+)\s*(?:%|per\s+cent)", re.IGNORECASE)
    while True:
        pos = lower.find("repo rate", start)
        if pos == -1:
            break
        window = bounded[pos + 9 : pos + 150]
        match_pct = pattern_pct.search(window)
        if match_pct:
            try:
                rate = float(match_pct.group(1))
                return StructuredEventValue(
                    metric_name="repo_rate",
                    value=rate,
                    unit="percent",
                )
            except ValueError:
                pass
        start = pos + 9
    return None


class RBIEventProvider(BaseEventProvider):
    """Event provider adapter for official Reserve Bank of India announcements."""

    def __init__(
        self,
        endpoint_url: str = RBI_RSS_ENDPOINT,
        fetcher: Optional[Callable[[str], str]] = None,
    ) -> None:
        """Initialize provider with endpoint URL and optional injected fetcher.

        Args:
            endpoint_url: Official RBI RSS feed URL.
            fetcher: Optional custom callable taking a URL string and returning raw XML payload.
        """
        self._url = endpoint_url
        self._fetcher = fetcher or self._default_fetcher

    @property
    def name(self) -> str:
        """Return the unique provider identifier."""
        return "rbi_rss_provider"

    def _default_fetcher(self, url: str) -> str:
        """Fetch remote payload via standard library urllib with user-agent."""
        req = urllib.request.Request(
            url,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                content_bytes: bytes = response.read()
                return content_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            raise EventProviderError(f"Failed to fetch RBI RSS feed from '{url}': {e}") from e

    def fetch_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        ingested_at: Optional[datetime] = None,
    ) -> List[MacroEvent]:
        """Fetch and normalize official RBI announcements.

        Args:
            start_date: Optional inclusive start datetime filter.
            end_date: Optional inclusive end datetime filter.
            limit: Maximum number of events to return.
            ingested_at: Optional explicit ingestion timestamp for historical replay/point-in-time checks.

        Returns:
            List of canonical MacroEvent records.
        """
        raw_xml = self._fetcher(self._url)
        return self._parse_xml(
            raw_xml,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            ingested_at=ingested_at,
        )

    def _parse_xml(
        self,
        xml_content: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        ingested_at: Optional[datetime] = None,
    ) -> List[MacroEvent]:
        """Parse raw RSS XML into validated MacroEvent instances."""
        if not xml_content or not xml_content.strip():
            logger.warning("Received empty RBI RSS XML payload")
            return []

        if len(xml_content) > MAX_RBI_PAYLOAD_CHARS:
            raise EventProviderError(
                f"RBI RSS payload exceeds maximum allowed size ({len(xml_content)} > {MAX_RBI_PAYLOAD_CHARS} chars)"
            )

        try:
            root = ET.fromstring(xml_content.strip())
        except ET.ParseError as e:
            raise EventProviderError(f"Malformed RBI RSS XML payload: {e}") from e

        now_ist = ingested_at or datetime.now(timezone.utc).astimezone(IST)
        events: List[MacroEvent] = []

        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else root.findall(".//item")

        for item in items:
            title_node = item.find("title")
            link_node = item.find("link")
            pub_date_node = item.find("pubDate")
            desc_node = item.find("description")

            raw_title = title_node.text.strip() if title_node is not None and title_node.text else ""
            if not raw_title:
                continue

            raw_url = link_node.text.strip() if link_node is not None and link_node.text else None
            raw_desc = desc_node.text if desc_node is not None and desc_node.text else ""
            cleaned_summary = _strip_html(raw_desc) if raw_desc else None

            # Parse publication date
            published_at = None
            if pub_date_node is not None and pub_date_node.text:
                try:
                    published_at = _parse_rbi_date(pub_date_node.text)
                except Exception as e:
                    logger.debug("Failed to parse pubDate '%s': %s", pub_date_node.text, e)
                    published_at = None

            # Filter by date range if specified
            if published_at is not None:
                norm_start = start_date.replace(tzinfo=published_at.tzinfo) if start_date and start_date.tzinfo is None else start_date
                norm_end = end_date.replace(tzinfo=published_at.tzinfo) if end_date and end_date.tzinfo is None else end_date
                if norm_start is not None and published_at < norm_start:
                    continue
                if norm_end is not None and published_at > norm_end:
                    continue

            # Classify event with word-boundary checks for abbreviations
            full_text = f"{raw_title} {cleaned_summary or ''}".lower()
            is_monetary = bool(
                re.search(
                    r"\b(?:monetary policy|mpc resolution|repo rate|reverse repo|policy rate|crr|slr)\b",
                    full_text,
                )
            )

            if is_monetary:
                category = EventCategory.MONETARY_POLICY
                event_type = "monetary_policy_statement"
                affected_sectors = ("BANKING", "FINANCIAL_SERVICES")
                structured_val = _extract_repo_rate_value(full_text)
            else:
                category = EventCategory.REGULATORY
                event_type = "press_release"
                affected_sectors = ("BANKING",)
                structured_val = None

            try:
                ev = MacroEvent(
                    title=raw_title,
                    category=category,
                    event_type=event_type,
                    source_org="Reserve Bank of India",
                    ingested_at=now_ist,
                    published_at=published_at,
                    announced_at=published_at,
                    url=raw_url,
                    affected_sectors=affected_sectors,
                    structured_value=structured_val,
                    summary=cleaned_summary,
                    provider=self.name,
                    is_verified=True,
                )
                events.append(ev)
            except Exception as e:
                logger.debug("Skipping unparseable RBI event '%s': %s", raw_title, e)

        # Sort descending by primary timestamp and apply limit after chronological ordering
        events.sort(key=lambda e: e.primary_timestamp, reverse=True)
        return events[:limit]
