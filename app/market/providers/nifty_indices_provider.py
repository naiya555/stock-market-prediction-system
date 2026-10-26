"""Official Nifty Indices Market Data Provider Adapter.

Implements BaseMarketDataProvider for official sectoral and benchmark indices
sourced directly from NSE Indices Limited (niftyindices.com).
"""

from datetime import datetime, time, timedelta, timezone
import json
import re
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
import httpx

from app.core.logging_config import get_logger, sanitize_log_field
from app.core.schemas import MarketOHLCV, ValidationError
from app.market.instruments import (
    NIFTY_TELECOM_CANONICAL,
    get_instrument,
    is_equity,
    resolve_canonical_symbol,
)
from app.market.providers.base import BaseMarketDataProvider
from app.market.quote import DataFreshnessStatus, LiveQuote
from app.market.session import IST, MarketSessionState, get_market_session

logger = get_logger(__name__)

# Official index names recognized by Nifty Indices backend
OFFICIAL_INDEX_NAMES: Dict[str, str] = {
    NIFTY_TELECOM_CANONICAL: "Nifty Telecommunications",
    "NIFTY_50": "Nifty 50",
    "NIFTY_BANK": "Nifty Bank",
    "NIFTY_IT": "Nifty IT",
}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.niftyindices.com/reports/historical-data",
    "Origin": "https://www.niftyindices.com",
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


class NiftyIndicesProvider(BaseMarketDataProvider):
    """Provider adapter fetching official index observations directly from niftyindices.com."""

    BASE_URL = "https://www.niftyindices.com"
    HISTORICAL_ENDPOINT = "https://www.niftyindices.com/BackPage/getHistoricaldatatabletoString"
    WARMUP_ENDPOINT = "https://www.niftyindices.com/reports/historical-data"

    def __init__(
        self,
        http_client: Optional[httpx.Client] = None,
        timeout: float = 20.0,
    ) -> None:
        """Initialize provider with optional injected httpx.Client for testing."""
        self._custom_client = http_client
        self._timeout = timeout

    @property
    def name(self) -> str:
        """Return unique provider identifier."""
        return "nifty_indices"

    def _get_client(self) -> httpx.Client:
        """Return active httpx.Client instance."""
        if self._custom_client is not None:
            return self._custom_client
        return httpx.Client(headers=DEFAULT_HEADERS, timeout=self._timeout, follow_redirects=True)

    def _resolve_index_name(self, symbol: str) -> str:
        """Resolve incoming symbol to official Nifty Indices name.

        Raises:
            ValueError: If symbol represents single-stock equity or an unrecognized index.
        """
        canonical = resolve_canonical_symbol(symbol)
        if is_equity(canonical):
            raise ValueError(
                f"Symbol '{symbol}' is a single-stock equity, not an index. "
                f"NiftyIndicesProvider strictly services official benchmark indices. "
                f"Use YFinanceProvider for equity '{canonical}'."
            )

        if canonical in OFFICIAL_INDEX_NAMES:
            return OFFICIAL_INDEX_NAMES[canonical]

        # Check clean names
        clean = symbol.strip().replace("_", " ").title()
        return clean

    @staticmethod
    def _format_date(dt: datetime) -> str:
        """Format datetime into Nifty Indices expected 'DD-Mon-YYYY' string."""
        return dt.strftime("%d-%b-%Y")

    @staticmethod
    def _parse_nifty_date(date_str: str) -> datetime:
        """Parse Nifty Indices date string (e.g. '15 Oct 2024' or '15-Oct-2024')."""
        clean = date_str.strip()
        for fmt in ("%d %b %Y", "%d-%b-%Y", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(clean, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        raise ValueError(f"Unrecognized date format from Nifty Indices: '{date_str}'")

    def fetch_historical_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[MarketOHLCV]:
        """Fetch historical daily index values from official Nifty Indices backend.

        Args:
            symbol: Index symbol or alias (e.g. 'NIFTY_TELECOMMUNICATIONS').
            start_date: Inclusive start datetime.
            end_date: Inclusive end datetime.
            interval: Bar aggregation interval (strictly '1d' for official index data).

        Returns:
            List of canonical MarketOHLCV records sorted chronologically.

        Raises:
            ValueError: If symbol is an equity, or interval is not '1d'.
            RuntimeError: If remote server communication fails.
        """
        if interval != "1d":
            raise ValueError(f"NiftyIndicesProvider only supports '1d' daily interval (got '{interval}').")

        canonical_symbol = resolve_canonical_symbol(symbol)
        official_name = self._resolve_index_name(canonical_symbol)

        start_str = self._format_date(start_date)
        end_str = self._format_date(end_date)

        logger.info(
            "Fetching official Nifty Indices data: %s ('%s') [%s to %s]",
            canonical_symbol,
            official_name,
            start_str,
            end_str,
        )

        json_inner = f"{{'name':'{official_name.upper()}','startDate':'{start_str}','endDate':'{end_str}','indexName':'{official_name}'}}"
        payload = {"cinfo": json_inner}

        client = self._get_client()
        owns_client = self._custom_client is None

        try:
            # Step A: Warmup / cookie acquisition
            try:
                client.get(self.WARMUP_ENDPOINT)
            except Exception as w_exc:
                logger.debug("Warmup endpoint ping non-critical warning: %s", w_exc)

            # Step B: Query backend ASMX WebMethod
            resp = client.post(self.HISTORICAL_ENDPOINT, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Official Nifty Indices endpoint returned HTTP {resp.status_code}: {resp.text[:200]}"
                )

            try:
                data = resp.json()
            except Exception as json_exc:
                raise RuntimeError(
                    f"Failed to parse Nifty Indices JSON response: {json_exc}. Content: {resp.text[:200]}"
                )

            # In some server responses, data is wrapped in a 'd' string
            if isinstance(data, dict) and "d" in data:
                raw_rows = json.loads(data["d"])
            elif isinstance(data, list):
                raw_rows = data
            else:
                raw_rows = []

        except Exception as exc:
            logger.error("Failed to acquire official index data for %s: %s", canonical_symbol, exc)
            raise RuntimeError(f"Official Nifty Indices retrieval failed for '{canonical_symbol}': {exc}") from exc
        finally:
            if owns_client:
                client.close()

        return self._parse_rows(raw_rows, canonical_symbol, start_date, end_date)

    def _parse_rows(
        self,
        raw_rows: List[Dict[str, Any]],
        canonical_symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[MarketOHLCV]:
        """Normalize raw Nifty Indices JSON rows into canonical MarketOHLCV records."""
        # Normalize start_date and end_date to UTC/IST if naive to prevent comparison errors
        norm_start = start_date.replace(tzinfo=ZoneInfo("Asia/Kolkata")) if start_date and start_date.tzinfo is None else start_date
        norm_end = end_date.replace(tzinfo=ZoneInfo("Asia/Kolkata")) if end_date and end_date.tzinfo is None else end_date

        records: List[MarketOHLCV] = []
        seen_timestamps = set()

        for row in raw_rows:
            date_raw = row.get("HistoricalDate") or row.get("Date")
            if not date_raw:
                continue

            try:
                ts = self._parse_nifty_date(date_raw)
            except Exception as dt_err:
                logger.warning("Skipping row with invalid date '%s': %s", date_raw, dt_err)
                continue

            # Point-in-time boundary filter
            if norm_start and ts < norm_start:
                continue
            if norm_end and ts > norm_end:
                continue

            if ts in seen_timestamps:
                continue

            # Parse Close price (mandatory strictly positive float)
            close_raw = row.get("CLOSE") or row.get("TotalReturnsIndex")
            if close_raw in (None, "-", ""):
                continue
            try:
                close = round(float(str(close_raw).replace(",", "")), 4)
                if close <= 0:
                    continue
            except ValueError:
                continue

            # Parse Open, High, Low
            # Nifty sectoral indices publish daily closing levels and return '-' for OHL.
            # Never copy closing values into open/high/low as observed market data.
            # When OHL are unavailable ('-'), preserve truthful semantics with open=None, high=None, low=None, is_close_only=True.
            open_raw = row.get("OPEN")
            high_raw = row.get("HIGH")
            low_raw = row.get("LOW")

            open_: Optional[float] = None
            high: Optional[float] = None
            low: Optional[float] = None
            is_close_only = False

            if (
                open_raw not in (None, "-", "")
                and high_raw not in (None, "-", "")
                and low_raw not in (None, "-", "")
            ):
                try:
                    open_candidate = round(float(str(open_raw).replace(",", "")), 4)
                    high_candidate = round(float(str(high_raw).replace(",", "")), 4)
                    low_candidate = round(float(str(low_raw).replace(",", "")), 4)
                    if open_candidate > 0 and high_candidate > 0 and low_candidate > 0:
                        open_ = open_candidate
                        high = high_candidate
                        low = low_candidate
                    else:
                        is_close_only = True
                except ValueError:
                    is_close_only = True
            else:
                is_close_only = True

            # Volume: Zero-fabrication guarantee. Nifty Indices does not report index volume.
            # volume=0 with volume_reported=False denotes unavailable / not reported trading volume.
            volume = 0

            try:
                record = MarketOHLCV(
                    symbol=canonical_symbol,
                    timestamp=ts,
                    open=open_,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    source=self.name,
                    is_close_only=is_close_only,
                    volume_reported=False,
                )
                records.append(record)
                seen_timestamps.add(ts)
            except ValidationError as val_err:
                logger.warning("Record validation failed for '%s' at %s: %s", canonical_symbol, ts, val_err)
                continue

        # Sort chronologically ascending
        records.sort(key=lambda r: r.timestamp)
        logger.info("Successfully normalized %d official MarketOHLCV records for %s", len(records), canonical_symbol)
        return records

    def fetch_quote(self, symbol: str) -> LiveQuote:
        """Acquire latest daily index observation from Nifty Indices."""
        canonical_symbol = resolve_canonical_symbol(symbol)
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(days=14)

        records = self.fetch_historical_ohlcv(canonical_symbol, start_date=start_utc, end_date=now_utc)
        if not records:
            raise RuntimeError(f"No recent official index quotes available for '{canonical_symbol}'.")

        latest = records[-1]
        session_info = get_market_session(latest.timestamp.astimezone(IST))

        return LiveQuote(
            symbol=canonical_symbol,
            price=latest.close,
            timestamp=latest.timestamp,
            retrieved_at=now_utc,
            source=self.name,
            session_state=session_info.state,
            freshness_status=DataFreshnessStatus.FRESH,
            open_price=latest.open,
            day_high=latest.high,
            day_low=latest.low,
            previous_close=records[-2].close if len(records) > 1 else None,
            volume=latest.volume if latest.is_volume_available else None,
            is_delayed=True,
            delay_minutes=0,
            disclaimer=(
                "Official end-of-day index closing level from NSE Indices Limited. "
                "Intraday OHLC and volume not reported by exchange for this index."
            ),
        )
