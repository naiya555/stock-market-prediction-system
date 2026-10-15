"""Securities and Exchange Board of India (SEBI) Regulatory Event Provider.

Acquires and normalizes official circulars, regulatory guidelines, and enforcement orders
directly from the official SEBI RSS feed.
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
from app.events.schemas import EventCategory, MacroEvent

logger = get_logger(__name__)

SEBI_RSS_ENDPOINT = "https://www.sebi.gov.in/sebirss.xml"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StockMarketPrediction/1.0"
IST = ZoneInfo("Asia/Kolkata")


def _strip_html(text: str) -> str:
    """Remove HTML markup, unescape entities, and collapse whitespace."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return " ".join(clean.split())


def _parse_sebi_date(date_str: str) -> datetime:
    """Parse SEBI publication timestamp and localize to Asia/Kolkata (IST).

    Supports formats like '16 Oct, 2026 +0530' or standard RFC 2822.
    """
    clean_date = date_str.strip()

    # Try standard email.utils parser first
    try:
        dt = email.utils.parsedate_to_datetime(clean_date)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=IST)
        return dt.astimezone(IST)
    except Exception:
        pass

    # Try SEBI custom format: '%d %b, %Y %z' or '%d %b, %Y'
    for fmt in (
        "%d %b, %Y %z",
        "%d %B, %Y %z",
        "%d %b, %Y",
        "%d %b %Y",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(clean_date, fmt)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=IST)
            return parsed.astimezone(IST)
        except ValueError:
            continue

    raise ValueError(f"Could not parse SEBI date: '{date_str}'")


class SEBIEventProvider(BaseEventProvider):
    """Event provider adapter for official SEBI circulars and announcements."""

    def __init__(
        self,
        endpoint_url: str = SEBI_RSS_ENDPOINT,
        fetcher: Optional[Callable[[str], str]] = None,
    ) -> None:
        """Initialize provider with endpoint URL and optional injected fetcher.

        Args:
            endpoint_url: Official SEBI RSS feed URL.
            fetcher: Optional custom callable taking a URL string and returning raw XML payload.
        """
        self._url = endpoint_url
        self._fetcher = fetcher or self._default_fetcher

    @property
    def name(self) -> str:
        """Return the unique provider identifier."""
        return "sebi_rss_provider"

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
            raise EventProviderError(f"Failed to fetch SEBI RSS feed from '{url}': {e}") from e

    def fetch_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[MacroEvent]:
        """Fetch and normalize official SEBI announcements.

        Args:
            start_date: Optional inclusive start datetime filter.
            end_date: Optional inclusive end datetime filter.
            limit: Maximum number of events to return.

        Returns:
            List of canonical MacroEvent records.
        """
        raw_xml = self._fetcher(self._url)
        return self._parse_xml(raw_xml, start_date=start_date, end_date=end_date, limit=limit)

    def _parse_xml(
        self,
        xml_content: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[MacroEvent]:
        """Parse raw RSS XML into validated MacroEvent instances."""
        if not xml_content or not xml_content.strip():
            logger.warning("Received empty SEBI RSS XML payload")
            return []

        try:
            root = ET.fromstring(xml_content.strip())
        except ET.ParseError as e:
            raise EventProviderError(f"Malformed SEBI RSS XML payload: {e}") from e

        now_ist = datetime.now(timezone.utc).astimezone(IST)
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
                    published_at = _parse_sebi_date(pub_date_node.text)
                except Exception as e:
                    logger.debug("Failed to parse SEBI pubDate '%s': %s", pub_date_node.text, e)
                    published_at = None

            # Filter by date range if specified
            if published_at is not None:
                if start_date is not None and published_at < start_date:
                    continue
                if end_date is not None and published_at > end_date:
                    continue

            # Classify event type
            lower_title = raw_title.lower()
            if "master circular" in lower_title:
                event_type = "master_circular"
            elif "circular" in lower_title:
                event_type = "circular"
            elif "order" in lower_title or "adjudication" in lower_title or "recovery" in lower_title:
                event_type = "enforcement_order"
            else:
                event_type = "regulatory_notice"

            try:
                ev = MacroEvent(
                    title=raw_title,
                    category=EventCategory.REGULATORY,
                    event_type=event_type,
                    source_org="Securities and Exchange Board of India",
                    ingested_at=now_ist,
                    published_at=published_at,
                    announced_at=published_at,
                    url=raw_url,
                    affected_sectors=("EQUITY_MARKET",),
                    summary=cleaned_summary,
                    provider=self.name,
                    is_verified=True,
                )
                events.append(ev)
            except Exception as e:
                logger.debug("Skipping unparseable SEBI event '%s': %s", raw_title, e)

            if len(events) >= limit:
                break

        events.sort(key=lambda e: e.primary_timestamp, reverse=True)
        return events
