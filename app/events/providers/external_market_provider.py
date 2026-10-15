"""External Market Observation Provider.

Acquires and normalizes macro time-series measurements for global variables
including Brent Crude Oil (BZ=F), USD/INR (INR=X), and S&P 500 (^GSPC).
Maintains strict separation between continuous market time-series observations
and discrete regulatory/policy announcements.
"""

from datetime import datetime, timedelta, timezone
import math
from typing import Any, Callable, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from app.core.logging_config import get_logger
from app.events.providers.base import BaseEventProvider, EventProviderError
from app.events.schemas import EventCategory, ExternalMarketObservation, MacroEvent, StructuredEventValue

logger = get_logger(__name__)

IST = ZoneInfo("Asia/Kolkata")

# Mapping of canonical series ID to provider ticker and unit
SUPPORTED_EXTERNAL_SERIES: Dict[str, Dict[str, str]] = {
    "BRENT_CRUDE": {
        "ticker": "BZ=F",
        "name": "Brent Crude Oil",
        "unit": "USD/barrel",
    },
    "USD_INR": {
        "ticker": "INR=X",
        "name": "USD/INR Exchange Rate",
        "unit": "INR/USD",
    },
    "SP500": {
        "ticker": "^GSPC",
        "name": "S&P 500 Index",
        "unit": "points",
    },
}


class ExternalMarketProvider(BaseEventProvider):
    """Provider for continuous external-market time-series observations."""

    def __init__(
        self,
        downloader: Optional[Callable[[str, datetime, datetime], List[Dict[str, Any]]]] = None,
    ) -> None:
        """Initialize provider with optional injected downloader callable for offline testing.

        Args:
            downloader: Callable(ticker, start_date, end_date) returning list of raw bar dicts:
                        [{'timestamp': dt, 'open': float, 'high': float, 'low': float, 'close': float}]
        """
        self._downloader = downloader or self._default_yfinance_downloader

    @property
    def name(self) -> str:
        """Return the unique provider identifier."""
        return "external_market_provider"

    def _default_yfinance_downloader(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Fetch historical series from Yahoo Finance via yfinance."""
        import yfinance as yf

        try:
            # In yfinance, the 'end' date parameter is exclusive.
            # Adding 1 day ensures the requested end_date session is included.
            fetch_start = start_date.strftime("%Y-%m-%d")
            fetch_end = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
            df = yf.download(
                ticker,
                start=fetch_start,
                end=fetch_end,
                interval="1d",
                auto_adjust=False,
                progress=False,
            )
            if df.empty:
                return []

            results: List[Dict[str, Any]] = []
            for idx, row in df.iterrows():
                ts = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=IST)
                else:
                    ts = ts.astimezone(IST)

                # Extract scalar values safely
                close_val = float(row["Close"].iloc[0]) if hasattr(row["Close"], "iloc") else float(row["Close"])
                open_val = float(row["Open"].iloc[0]) if hasattr(row["Open"], "iloc") else float(row["Open"])
                high_val = float(row["High"].iloc[0]) if hasattr(row["High"], "iloc") else float(row["High"])
                low_val = float(row["Low"].iloc[0]) if hasattr(row["Low"], "iloc") else float(row["Low"])

                results.append({
                    "timestamp": ts,
                    "open": open_val,
                    "high": high_val,
                    "low": low_val,
                    "close": close_val,
                })
            return results
        except Exception as e:
            raise EventProviderError(f"Failed to fetch external market data for '{ticker}': {e}") from e

    def fetch_observations(
        self,
        series_ids: Optional[Sequence[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ingested_at: Optional[datetime] = None,
    ) -> List[ExternalMarketObservation]:
        """Fetch structured time-series measurements for requested external macro variables.

        Args:
            series_ids: List of canonical series identifiers (e.g., ['BRENT_CRUDE', 'USD_INR']).
                        If None, fetches all supported external series.
            start_date: Start datetime.
            end_date: End datetime.
            ingested_at: Optional explicit acquisition timestamp for backtesting/PIT integrity.
                         Defaults to current time in IST.

        Returns:
            List of ExternalMarketObservation records sorted chronologically.
        """
        target_series = [s.strip().upper() for s in series_ids] if series_ids else list(SUPPORTED_EXTERNAL_SERIES.keys())
        now_ist = datetime.now(timezone.utc).astimezone(IST)
        start = start_date or (now_ist.replace(hour=0, minute=0, second=0, microsecond=0))
        end = end_date or now_ist
        acq_time = ingested_at or now_ist

        observations: List[ExternalMarketObservation] = []

        for sid in target_series:
            meta = SUPPORTED_EXTERNAL_SERIES.get(sid)
            if not meta:
                logger.warning("Unsupported external market series: '%s'", sid)
                continue

            ticker = meta["ticker"]
            unit = meta["unit"]

            try:
                raw_bars = self._downloader(ticker, start, end)
            except Exception as e:
                logger.error("Error downloading external series '%s': %s", sid, e)
                raise EventProviderError(f"External market series '{sid}' fetch failed: {e}") from e

            # Compute daily returns across sequential observations
            prev_close: Optional[float] = None
            for bar in sorted(raw_bars, key=lambda b: b["timestamp"]):
                close_px = float(bar["close"])
                daily_ret: Optional[float] = None
                if prev_close is not None and prev_close > 0.0:
                    daily_ret = round((close_px / prev_close) - 1.0, 6)
                prev_close = close_px

                obs = ExternalMarketObservation(
                    series_id=sid,
                    timestamp=bar["timestamp"],
                    ingested_at=acq_time,
                    close=close_px,
                    open=float(bar.get("open", close_px)),
                    high=float(bar.get("high", close_px)),
                    low=float(bar.get("low", close_px)),
                    daily_return=daily_ret,
                    unit=unit,
                    source="yfinance",
                )
                observations.append(obs)

        observations.sort(key=lambda o: (o.timestamp, o.series_id), reverse=True)
        return observations

    def fetch_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        ingested_at: Optional[datetime] = None,
    ) -> List[MacroEvent]:
        """Fetch observations and map into canonical MacroEvent records for unified pipeline consumption."""
        observations = self.fetch_observations(
            start_date=start_date,
            end_date=end_date,
            ingested_at=ingested_at,
        )
        events = [obs.to_event() for obs in observations]
        return events[:limit]
