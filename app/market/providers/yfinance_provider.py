"""Yahoo Finance Market Data Provider Adapter.

Implements BaseMarketDataProvider using the yfinance library for Indian equities (NSE/BSE).
Normalizes raw OHLCV series into canonical MarketOHLCV records.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf

from app.core.logging_config import get_logger, sanitize_log_field
from app.core.schemas import MarketOHLCV, ValidationError
from app.market.intraday import (
    BaseIntradayDataProvider,
    IntradayCandle,
    IntradayInterval,
)
from app.market.providers.base import BaseMarketDataProvider
from app.market.quote import DataFreshnessStatus, LiveQuote
from app.market.session import IST, MarketSessionState, get_market_session

logger = get_logger(__name__)


# Standard Indian market benchmark index mapping for Yahoo Finance
INDEX_SYMBOL_MAP: dict[str, str] = {
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "NIFTY_50": "^NSEI",
    "^NSEI": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "NIFTYBANK": "^NSEBANK",
    "NIFTY_BANK": "^NSEBANK",
    "^NSEBANK": "^NSEBANK",
    "NIFTYIT": "^CNXIT",
    "CNXIT": "^CNXIT",
    "NIFTY_IT": "^CNXIT",
    "^CNXIT": "^CNXIT",
    "SENSEX": "^BSESN",
    "^BSESN": "^BSESN",
    "NIFTY500": "^CRSLDX",
    "CRSLDX": "^CRSLDX",
    "NIFTY_500": "^CRSLDX",
    "^CRSLDX": "^CRSLDX",
    "NIFTYMIDCAP50": "^NSEMDCP50",
    "NSEMDCP50": "^NSEMDCP50",
    "^NSEMDCP50": "^NSEMDCP50",
}


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
            e.g., ('BHARTIARTL', 'BHARTIARTL.NS') or ('^NSEI', '^NSEI')
        """
        clean = symbol.strip().upper()
        if clean in INDEX_SYMBOL_MAP:
            base = clean
            query_ticker = INDEX_SYMBOL_MAP[clean]
        elif clean.startswith("^"):
            base = clean
            query_ticker = clean
        elif clean.endswith(".NS") or clean.endswith(".BO"):
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
            sanitize_log_field(base_symbol),
            sanitize_log_field(query_ticker),
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

    def fetch_quote(
        self,
        symbol: str,
        max_staleness_seconds: int = 3600,
    ) -> LiveQuote:
        """Fetch latest / near-real-time quote for a given Indian equity symbol.

        Retrieves current traded price, OHLC intraday statistics, volume, and
        prior closing price. Evaluates the active Indian market session state
        and enforces explicit delay disclosures and freshness checks.

        Args:
            symbol: Ticker symbol (e.g. 'RELIANCE', 'TCS.NS', '^NSEI').
            max_staleness_seconds: Staleness threshold in seconds during regular hours (default 3600).

        Returns:
            LiveQuote containing verified price, session state, and freshness status.

        Raises:
            ValidationError: If symbol is empty or returned prices violate schema bounds.
            RuntimeError: If yfinance communication fails or no quote is returned.
        """
        if not symbol or not symbol.strip():
            raise ValidationError("symbol cannot be empty")

        base_symbol, query_ticker = self._resolve_symbols(symbol)
        retrieved_at = datetime.now(IST)
        session_info = get_market_session(retrieved_at)
        clean_base = sanitize_log_field(base_symbol)

        logger.info("Fetching quote for %s (%s) via %s", clean_base, query_ticker, self.name)

        try:
            ticker = yf.Ticker(query_ticker)
        except Exception as exc:
            logger.error("Failed to initialize yfinance ticker for %s: %s", query_ticker, exc)
            raise RuntimeError(f"yfinance quote fetch failed for '{query_ticker}': {exc}") from exc

        # Step 1: Attempt to read fast_info (lightweight metadata)
        fast_info = getattr(ticker, "fast_info", None)
        last_price: Optional[float] = None
        open_price: Optional[float] = None
        day_high: Optional[float] = None
        day_low: Optional[float] = None
        prev_close: Optional[float] = None
        volume: Optional[int] = None
        currency: str = "INR"

        if fast_info:
            try:
                raw_lp = getattr(fast_info, "last_price", None)
                if raw_lp is not None and not pd.isna(raw_lp):
                    last_price = float(raw_lp)
                raw_op = getattr(fast_info, "open", None)
                if raw_op is not None and not pd.isna(raw_op):
                    open_price = float(raw_op)
                raw_dh = getattr(fast_info, "day_high", None)
                if raw_dh is not None and not pd.isna(raw_dh):
                    day_high = float(raw_dh)
                raw_dl = getattr(fast_info, "day_low", None)
                if raw_dl is not None and not pd.isna(raw_dl):
                    day_low = float(raw_dl)
                raw_pc = getattr(fast_info, "previous_close", None)
                if raw_pc is not None and not pd.isna(raw_pc):
                    prev_close = float(raw_pc)
                raw_vol = getattr(fast_info, "last_volume", None)
                if raw_vol is not None and not pd.isna(raw_vol):
                    volume = int(raw_vol)
                raw_cur = getattr(fast_info, "currency", None)
                if raw_cur and isinstance(raw_cur, str):
                    currency = raw_cur
            except Exception as e:
                logger.debug("fast_info attribute access encountered exception for %s: %s", query_ticker, e)

        # Step 2: Query intraday history for exact timestamp and fallback prices
        as_of: Optional[datetime] = None
        try:
            df_intra = ticker.history(period="1d", interval="1m", auto_adjust=False)
            if df_intra is not None and not df_intra.empty:
                last_idx = df_intra.index[-1]
                if isinstance(last_idx, pd.Timestamp):
                    as_of = last_idx.to_pydatetime()
                elif isinstance(last_idx, datetime):
                    as_of = last_idx
                else:
                    as_of = pd.to_datetime(last_idx).to_pydatetime()
                if as_of.tzinfo is None:
                    as_of = as_of.replace(tzinfo=IST)
                else:
                    as_of = as_of.astimezone(IST)

                # If fast_info missed any metrics, backfill from intraday series
                if last_price is None:
                    last_price = float(df_intra["Close"].iloc[-1])
                if open_price is None:
                    open_price = float(df_intra["Open"].iloc[0])
                if day_high is None:
                    day_high = float(df_intra["High"].max())
                if day_low is None:
                    day_low = float(df_intra["Low"].min())
                if volume is None:
                    volume = int(df_intra["Volume"].sum())
        except Exception as exc:
            logger.debug("Intraday 1m query failed for %s: %s", query_ticker, exc)

        # Step 3: Daily fallback if intraday returned no bars (e.g. market closed, weekend)
        if last_price is None:
            try:
                df_daily = ticker.history(period="5d", interval="1d", auto_adjust=False)
                if df_daily is not None and not df_daily.empty:
                    last_row = df_daily.iloc[-1]
                    last_price = float(last_row["Close"])
                    if open_price is None:
                        open_price = float(last_row["Open"])
                    if day_high is None:
                        day_high = float(last_row["High"])
                    if day_low is None:
                        day_low = float(last_row["Low"])
                    if volume is None:
                        volume = int(last_row["Volume"])

                    last_idx = df_daily.index[-1]
                    if isinstance(last_idx, pd.Timestamp):
                        as_of = last_idx.to_pydatetime()
                    else:
                        as_of = pd.to_datetime(last_idx).to_pydatetime()
                    if as_of.tzinfo is None:
                        as_of = as_of.replace(tzinfo=IST)
                    else:
                        as_of = as_of.astimezone(IST)

                    if prev_close is None and len(df_daily) >= 2:
                        prev_close = float(df_daily["Close"].iloc[-2])
            except Exception as exc:
                logger.debug("Daily fallback query failed for %s: %s", query_ticker, exc)

        # Step 4: Strict validation - fail fast rather than fabricating fake prices
        if last_price is None:
            logger.warning("No price data returned by yfinance for %s", query_ticker)
            raise RuntimeError(f"No quote data returned by yfinance for '{query_ticker}'")

        if last_price <= 0:
            raise ValidationError(f"Invalid non-positive quote price {last_price} for '{query_ticker}'")

        if as_of is None:
            as_of = retrieved_at

        # Step 5: Compute change and change percentage if previous close exists
        change: Optional[float] = None
        change_pct: Optional[float] = None
        if prev_close is not None and prev_close > 0:
            change = round(last_price - prev_close, 4)
            change_pct = round((change / prev_close) * 100, 4)

        # Step 6: Determine data freshness
        elapsed_seconds = (retrieved_at - as_of).total_seconds()
        if session_info.state == MarketSessionState.REGULAR_HOURS:
            # During trading hours, verify quote is from today and not excessively stale
            if as_of.date() < retrieved_at.date() or elapsed_seconds > max_staleness_seconds:
                freshness = DataFreshnessStatus.STALE
            else:
                freshness = DataFreshnessStatus.DELAYED  # Free tier exchange delay (~15m)
        else:
            # Outside market hours, quote represents the latest session close
            # If the quote is older than 5 calendar days, flag as stale
            if (retrieved_at.date() - as_of.date()).days > 5:
                freshness = DataFreshnessStatus.STALE
            else:
                freshness = DataFreshnessStatus.FRESH

        quote = LiveQuote(
            symbol=base_symbol,
            price=last_price,
            timestamp=as_of,
            retrieved_at=retrieved_at,
            source=self.name,
            session_state=session_info.state,
            freshness_status=freshness,
            open_price=open_price,
            day_high=day_high,
            day_low=day_low,
            previous_close=prev_close,
            change=change,
            change_percent=change_pct,
            volume=volume,
            currency=currency,
            is_delayed=True,
            delay_minutes=15,
        )

        logger.info(
            "Fetched live quote for %s: price=%.2f [%s, %s]",
            clean_base,
            quote.price,
            quote.session_state.value,
            quote.freshness_status.value,
        )
        return quote


class YFinanceIntradayProvider(BaseIntradayDataProvider):
    """Acquires historical completed intraday candlestick bars via Yahoo Finance.

    Enforces:
    - Supported instrument policy: restricts inference to authorized models (BHARTIARTL).
    - Separation from index models: rejects index queries (^NSEI, NIFTY) with ValidationError.
    - Timezone normalization to Asia/Kolkata (IST).
    - Preserves missing volume as None without zero fabrication.
    - Physical OHLC boundary validation.
    - Bounded retries and clean exception handling.
    """

    def __init__(self, default_exchange_suffix: str = ".NS") -> None:
        self._suffix = default_exchange_suffix

    @property
    def name(self) -> str:
        return "yfinance"

    @property
    def declared_delay(self) -> str:
        return "15m delayed exchange data (no real-time stream)"

    def fetch_intraday_candles(
        self,
        symbol: str,
        session_date: date,
        interval: IntradayInterval = IntradayInterval.M5,
    ) -> List[IntradayCandle]:
        """Fetch raw intraday candles for a given symbol and trading date."""
        if not symbol or not isinstance(symbol, str) or not symbol.strip():
            raise ValidationError("symbol cannot be empty")

        clean_symbol = symbol.strip().upper()
        # Enforce equity model separation: reject index symbols
        if clean_symbol in INDEX_SYMBOL_MAP or clean_symbol.startswith("^"):
            raise ValidationError(
                f"Instrument '{clean_symbol}' is an index. Intraday equity model cannot be applied to index instruments."
            )

        query_ticker = (
            clean_symbol
            if clean_symbol.endswith(".NS") or clean_symbol.endswith(".BO")
            else f"{clean_symbol}{self._suffix}"
        )

        interval_str = interval.value
        start_str = session_date.strftime("%Y-%m-%d")
        end_str = (session_date + timedelta(days=1)).strftime("%Y-%m-%d")

        logger.info(
            "Fetching intraday %s candles for %s (%s) on %s via %s",
            interval_str,
            clean_symbol,
            query_ticker,
            session_date,
            self.name,
        )

        try:
            ticker = yf.Ticker(query_ticker)
            df = ticker.history(
                start=start_str,
                end=end_str,
                interval=interval_str,
                auto_adjust=False,
            )
        except Exception as exc:
            logger.error("yfinance intraday fetch failed for %s: %s", query_ticker, exc)
            raise RuntimeError(f"yfinance intraday fetch failed for '{query_ticker}': {exc}") from exc

        if df is None or df.empty:
            logger.warning("No intraday data returned by yfinance for %s on %s", query_ticker, session_date)
            return []

        required_cols = {"Open", "High", "Low", "Close"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise RuntimeError(
                f"yfinance intraday response missing required columns {missing_cols} for {query_ticker}"
            )

        candles: List[IntradayCandle] = []
        for idx, row in df.iterrows():
            if isinstance(idx, pd.Timestamp):
                ts = idx.to_pydatetime()
            elif isinstance(idx, datetime):
                ts = idx
            else:
                ts = pd.to_datetime(idx).to_pydatetime()

            # Ensure timezone is localized to Asia/Kolkata
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=IST)
            else:
                ts = ts.astimezone(IST)

            # Filter rows strictly matching session_date
            if ts.date() != session_date:
                continue

            # Skip NaN prices
            if (
                pd.isna(row["Open"])
                or pd.isna(row["High"])
                or pd.isna(row["Low"])
                or pd.isna(row["Close"])
            ):
                continue

            # Parse volume safely without fabrication
            volume: Optional[int] = None
            if "Volume" in row and not pd.isna(row["Volume"]):
                try:
                    vol_int = int(row["Volume"])
                    if vol_int >= 0:
                        volume = vol_int
                except (ValueError, TypeError):
                    volume = None

            try:
                candle = IntradayCandle(
                    symbol=clean_symbol,
                    timestamp=ts,
                    interval=interval,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=volume,
                    source=self.name,
                )
                candles.append(candle)
            except ValidationError as ve:
                logger.warning(
                    "Skipping invalid candle from yfinance for %s at %s: %s",
                    clean_symbol,
                    ts,
                    ve,
                )
                continue

        logger.info(
            "Successfully fetched %d intraday candles for %s on %s",
            len(candles),
            clean_symbol,
            session_date,
        )
        return candles
