"""Yahoo Finance Market Data Provider Adapter.

Implements BaseMarketDataProvider using the yfinance library for Indian equities (NSE/BSE).
Normalizes raw OHLCV series into canonical MarketOHLCV records.
"""

from datetime import datetime, timedelta
from typing import List
import pandas as pd
import yfinance as yf

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV, ValidationError
from app.market.providers.base import BaseMarketDataProvider

logger = get_logger(__name__)


class YFinanceProvider(BaseMarketDataProvider):
    """Historical market data provider backed by Yahoo Finance."""

    def __init__(self, default_exchange_suffix: str = ".NS") -> None:
        """Initialize provider with default exchange suffix for Indian equities.

        Args:
            default_exchange_suffix: Suffix appended if no exchange code is supplied (default '.NS' for NSE).
        """
        self._suffix = default_exchange_suffix

    @property
    def name(self) -> str:
        """Return the unique provider identifier."""
        return "yfinance"

    def _resolve_symbols(self, symbol: str) -> tuple[str, str]:
        """Resolve base symbol and provider-specific ticker.

        Returns:
            Tuple of (base_symbol, query_ticker)
            e.g., ('BHARTIARTL', 'BHARTIARTL.NS')
        """
        clean = symbol.strip().upper()
        if clean.endswith(".NS") or clean.endswith(".BO"):
            base = clean.rsplit(".", 1)[0]
            query_ticker = clean
        else:
            base = clean
            query_ticker = f"{clean}{self._suffix}"
        return base, query_ticker

    def fetch_historical_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[MarketOHLCV]:
        """Fetch historical OHLCV data from Yahoo Finance and map to MarketOHLCV.

        Uses raw unadjusted price series (auto_adjust=False) to preserve true
        traded prices and physical OHLC boundary relationships.

        Args:
            symbol: Ticker symbol (e.g., 'BHARTIARTL' or 'BHARTIARTL.NS').
            start_date: Inclusive start datetime.
            end_date: Inclusive end datetime.
            interval: Bar interval (default '1d').

        Returns:
            List of canonical MarketOHLCV records.

        Raises:
            ValidationError: If symbol, dates, or output records violate validation.
            RuntimeError: If yfinance communication or required columns fail.
        """
        if not symbol or not symbol.strip():
            raise ValidationError("symbol cannot be empty")
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise ValidationError("start_date and end_date must be datetime instances")
        if start_date > end_date:
            raise ValidationError(
                f"start_date ({start_date.isoformat()}) cannot be after end_date ({end_date.isoformat()})"
            )

        base_symbol, query_ticker = self._resolve_symbols(symbol)

        logger.info(
            "Fetching historical OHLCV for %s (%s) from %s to %s [interval=%s]",
            base_symbol,
            query_ticker,
            start_date.date(),
            end_date.date(),
            interval,
        )

        # In yfinance history(), the 'end' date parameter is exclusive.
        # Adding 1 day ensures the requested end_date session is included.
        fetch_start = start_date.strftime("%Y-%m-%d")
        fetch_end = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            ticker = yf.Ticker(query_ticker)
            df = ticker.history(
                start=fetch_start,
                end=fetch_end,
                interval=interval,
                auto_adjust=False,
            )
        except Exception as exc:
            logger.error("Failed to fetch data from yfinance for %s: %s", query_ticker, exc)
            raise RuntimeError(f"yfinance fetch failed for '{query_ticker}': {exc}") from exc

        if df is None or df.empty:
            logger.warning(
                "No market data returned by yfinance for %s between %s and %s",
                query_ticker,
                fetch_start,
                fetch_end,
            )
            return []

        # Validate required price & volume columns exist
        required_cols = {"Open", "High", "Low", "Close", "Volume"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise RuntimeError(
                f"yfinance response missing required columns {missing_cols} for {query_ticker}"
            )

        records: List[MarketOHLCV] = []
        for idx, row in df.iterrows():
            if isinstance(idx, pd.Timestamp):
                ts = idx.to_pydatetime()
            elif isinstance(idx, datetime):
                ts = idx
            else:
                ts = pd.to_datetime(idx).to_pydatetime()

            # Ensure row falls within requested calendar dates
            row_date = ts.date()
            if row_date < start_date.date() or row_date > end_date.date():
                continue

            # Check for NaN / null values
            if (
                pd.isna(row["Open"])
                or pd.isna(row["High"])
                or pd.isna(row["Low"])
                or pd.isna(row["Close"])
                or pd.isna(row["Volume"])
            ):
                logger.warning("Skipping bar with NaN values on %s for %s", ts, base_symbol)
                continue

            # Construct and validate canonical MarketOHLCV record
            record = MarketOHLCV(
                symbol=base_symbol,
                timestamp=ts,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
                source=self.name,
            )
            records.append(record)

        logger.info(
            "Successfully fetched and normalized %d MarketOHLCV records for %s",
            len(records),
            base_symbol,
        )
        return records
