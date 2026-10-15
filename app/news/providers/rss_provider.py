"""Financial News RSS Provider Adapter.

Implements BaseNewsProvider using RSS feeds (e.g. Google News RSS for Indian financial media).
Normalizes raw RSS item XML elements into canonical NewsArticle records.
"""

from datetime import datetime, timezone
import email.utils
import html
import re
from typing import Callable, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from app.core.logging_config import get_logger
from app.core.schemas import ValidationError
from app.news.providers.base import BaseNewsProvider, NewsProviderError
from app.news.schemas import NewsArticle

logger = get_logger(__name__)

# Indian Market Target Timezone
IST = ZoneInfo("Asia/Kolkata")

# Mapping of common NSE symbols to corporate entity names for targeted headline matching
COMPANY_NAME_MAP: Dict[str, str] = {
    "BHARTIARTL": "Bharti Airtel",
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank",
    "INFY": "Infosys",
    "ICICIBANK": "ICICI Bank",
    "SBIN": "State Bank of India",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen & Toubro",
    "ITC": "ITC",
    "^NSEI": "NIFTY 50",
    "^NSEBANK": "Bank Nifty",
    "^CNXIT": "NIFTY IT",
}


def _strip_html_tags(text: str) -> str:
    """Remove HTML markup and unescape HTML entities from summary text."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return " ".join(clean.split())


class RSSNewsProvider(BaseNewsProvider):
    """Financial news provider backed by RSS feeds with point-in-time normalization."""

    def __init__(
        self,
        base_url: str = "https://news.google.com/rss/search",
        timeout: float = 10.0,
        user_agent: str = "StockMarketPredictionSystem/1.0",
        fetcher: Optional[Callable[[str], bytes]] = None,
    ) -> None:
        """Initialize RSS provider.

        Args:
            base_url: Base RSS endpoint URL.
            timeout: Network timeout in seconds (default 10.0s).
            user_agent: User-Agent string for HTTP requests.
            fetcher: Optional custom fetch callable for testing/dependency injection.
        """
        self._base_url = base_url
        self._timeout = timeout
        self._user_agent = user_agent
        self._fetcher = fetcher or self._default_fetcher

    @property
    def name(self) -> str:
        """Return provider unique identifier."""
        return "rss_news_provider"

    def _default_fetcher(self, url: str) -> bytes:
        """Fetch raw content from URL using urllib with configured headers and timeout."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/rss+xml, application/xml, text/xml",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            logger.error("Failed to fetch RSS feed from %s: %s", url, exc)
            raise NewsProviderError(f"HTTP fetch failed for news feed '{url}': {exc}") from exc

    def _build_search_url(self, symbol: str) -> str:
        """Build provider search query URL for an Indian equity or index symbol."""
        clean = symbol.strip().upper()
        if clean.endswith(".NS") or clean.endswith(".BO"):
            base_sym = clean.rsplit(".", 1)[0]
        else:
            base_sym = clean

        company_name = COMPANY_NAME_MAP.get(base_sym)
        if company_name:
            query = f'"{company_name}" OR "{base_sym}" stock NSE'
        else:
            query = f'"{base_sym}" stock NSE'

        params = {
            "q": query,
            "hl": "en-IN",
            "gl": "IN",
            "ceid": "IN:en",
        }
        return f"{self._base_url}?{urllib.parse.urlencode(params)}"

    def parse_rss_payload(
        self,
        xml_bytes: bytes,
        symbol: str,
        ingested_at: Optional[datetime] = None,
    ) -> List[NewsArticle]:
        """Parse raw RSS XML bytes into canonical NewsArticle records.

        Args:
            xml_bytes: Raw XML response bytes.
            symbol: Ticker symbol associated with the query.
            ingested_at: Optional explicit ingestion timestamp (defaults to current IST time).

        Returns:
            List of normalized NewsArticle records.
        """
        if not xml_bytes or not xml_bytes.strip():
            logger.warning("Empty XML bytes supplied to parse_rss_payload")
            return []

        clean_symbol = symbol.strip().upper()
        if clean_symbol.endswith(".NS") or clean_symbol.endswith(".BO"):
            base_sym = clean_symbol.rsplit(".", 1)[0]
        else:
            base_sym = clean_symbol

        ingestion_time = ingested_at or datetime.now(timezone.utc).astimezone(IST)

        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as exc:
            logger.error("XML parse error while reading news payload: %s", exc)
            raise NewsProviderError(f"Malformed RSS XML payload: {exc}") from exc

        items = root.findall(".//item")
        if not items:
            logger.info("Zero <item> entries found in RSS feed for %s", base_sym)
            return []

        articles: List[NewsArticle] = []
        for idx, item in enumerate(items):
            title_elem = item.find("title")
            raw_title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            if not raw_title:
                logger.debug("Skipping item %d with missing title", idx)
                continue

            # Extract source publisher
            source_elem = item.find("source")
            if source_elem is not None and source_elem.text and source_elem.text.strip():
                source_name = source_elem.text.strip()
                headline = raw_title
                # If headline ends with " - Source Name", clean it up
                if headline.endswith(f" - {source_name}"):
                    headline = headline[: -len(f" - {source_name}")].strip()
            elif " - " in raw_title:
                headline, source_name = raw_title.rsplit(" - ", 1)
                headline = headline.strip()
                source_name = source_name.strip()
            else:
                headline = raw_title
                source_name = "Financial Media"

            # Extract publication timestamp
            pub_date_elem = item.find("pubDate")
            raw_pub_date = pub_date_elem.text.strip() if pub_date_elem is not None and pub_date_elem.text else ""
            published_dt: Optional[datetime] = None
            if raw_pub_date:
                try:
                    # RFC 2822 / 822 format (e.g. "Wed, 14 Oct 2026 13:29:00 GMT")
                    dt = email.utils.parsedate_to_datetime(raw_pub_date)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    published_dt = dt.astimezone(IST)
                except Exception as exc:
                    logger.debug("Failed RFC 2822 date parse for '%s': %s", raw_pub_date, exc)
                    try:
                        # Fallback to ISO format
                        dt = datetime.fromisoformat(raw_pub_date)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        published_dt = dt.astimezone(IST)
                    except Exception:
                        published_dt = None

            if published_dt is None:
                logger.warning("Skipping article with unparseable publication date: '%s'", raw_pub_date)
                continue

            # Extract link / URL
            link_elem = item.find("link")
            url = link_elem.text.strip() if link_elem is not None and link_elem.text else None

            # Extract description / summary
            desc_elem = item.find("description")
            raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
            summary = _strip_html_tags(raw_desc) if raw_desc else None

            try:
                article = NewsArticle(
                    headline=headline,
                    source=source_name,
                    published_at=published_dt,
                    ingested_at=ingestion_time,
                    symbols=(base_sym,),
                    url=url,
                    summary=summary,
                    provider=self.name,
                )
                articles.append(article)
            except ValidationError as exc:
                logger.warning("Article validation failed on item %d: %s", idx, exc)
                continue

        logger.info(
            "Successfully parsed %d valid NewsArticle records for %s",
            len(articles),
            base_sym,
        )
        return articles

    def fetch_news(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[NewsArticle]:
        """Fetch and normalize news articles for a symbol.

        Args:
            symbol: Ticker symbol (e.g., 'BHARTIARTL').
            start_date: Optional inclusive start datetime filter.
            end_date: Optional inclusive end datetime filter.
            limit: Maximum number of articles to return (default 50).

        Returns:
            List of NewsArticle sorted descending by publication date.
        """
        if not symbol or not symbol.strip():
            raise ValidationError("symbol cannot be empty")
        if limit < 1:
            raise ValidationError(f"limit must be >= 1, got {limit}")

        url = self._build_search_url(symbol)
        logger.info("Fetching news for %s from RSS endpoint: %s", symbol, url)

        xml_bytes = self._fetcher(url)
        articles = self.parse_rss_payload(xml_bytes, symbol)

        # Apply optional date filters point-in-time
        filtered: List[NewsArticle] = []
        for art in articles:
            if start_date is not None and art.published_at < start_date:
                continue
            if end_date is not None and art.published_at > end_date:
                continue
            filtered.append(art)

        # Sort descending by published_at (most recent first)
        filtered.sort(key=lambda a: a.published_at, reverse=True)

        return filtered[:limit]
