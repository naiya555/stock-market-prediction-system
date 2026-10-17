"""Indian Equity Market Trading Calendar Interface and Implementations.

Provides deterministic trading calendar abstractions for Indian equity markets (NSE/BSE).
Supports extracting trading sessions directly from observed market data (MarketOHLCV)
or through injectable exchange calendar definitions without hardcoded assumptions.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV

logger = get_logger(__name__)

# Canonical Indian Equity Market Timezone
IST = ZoneInfo("Asia/Kolkata")

# Standard NSE/BSE Equity Session Market Times (IST)
MARKET_OPEN_TIME = time(9, 15, 0)
MARKET_CLOSE_TIME = time(15, 30, 0)


class BaseTradingCalendar(ABC):
    """Abstract base contract for Indian equity trading session calendars."""

    @abstractmethod
    def is_trading_day(self, day: date) -> bool:
        """Return True if the given date is an active equity trading session."""

    @abstractmethod
    def get_next_trading_day(self, day: date) -> Optional[date]:
        """Return the immediately succeeding trading day strictly after `day`.

        Returns None if calendar coverage is exhausted.
        """

    @abstractmethod
    def get_previous_trading_day(self, day: date) -> Optional[date]:
        """Return the immediately preceding trading day strictly before `day`.

        Returns None if calendar coverage is exhausted.
        """

    @abstractmethod
    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """Return chronological list of trading days in [start_date, end_date]."""

    def get_session_times(self, day: date) -> Tuple[datetime, datetime]:
        """Return (session_open, session_close) datetimes in Asia/Kolkata timezone."""
        return (
            datetime.combine(day, MARKET_OPEN_TIME, tzinfo=IST),
            datetime.combine(day, MARKET_CLOSE_TIME, tzinfo=IST),
        )


class MarketDataTradingCalendar(BaseTradingCalendar):
    """Trading calendar derived strictly from observed market bars.

    Eliminates guesswork regarding unscheduled holidays, muhurat trading sessions,
    cyclone closures, or national mourning days by anchoring to realized bars.
    """

    def __init__(self, bars_or_dates: Iterable[Any]) -> None:
        """Initialize calendar from a collection of MarketOHLCV records or date objects."""
        dates_set: Set[date] = set()
        for item in bars_or_dates:
            if isinstance(item, MarketOHLCV):
                # Ensure date is interpreted in IST if timestamp is tz-aware
                ts = item.timestamp
                if ts.tzinfo is not None:
                    dates_set.add(ts.astimezone(IST).date())
                else:
                    dates_set.add(ts.date())
            elif isinstance(item, datetime):
                if item.tzinfo is not None:
                    dates_set.add(item.astimezone(IST).date())
                else:
                    dates_set.add(item.date())
            elif isinstance(item, date):
                dates_set.add(item)
            else:
                raise TypeError(f"Unsupported item type for trading calendar: {type(item).__name__}")

        self._trading_days: List[date] = sorted(dates_set)
        self._trading_set: Set[date] = set(self._trading_days)

    def is_trading_day(self, day: date) -> bool:
        """Check if day exists in observed market bars."""
        return day in self._trading_set

    def get_next_trading_day(self, day: date) -> Optional[date]:
        """Find first observed trading day strictly after `day`."""
        for d in self._trading_days:
            if d > day:
                return d
        return None

    def get_previous_trading_day(self, day: date) -> Optional[date]:
        """Find last observed trading day strictly before `day`."""
        for d in reversed(self._trading_days):
            if d < day:
                return d
        return None

    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """Return observed trading days within date range [start_date, end_date]."""
        return [d for d in self._trading_days if start_date <= d <= end_date]


class ExchangeTradingCalendar(BaseTradingCalendar):
    """Configurable trading calendar with explicit holidays and weekday rules.

    Suitable for simulations, testing, and forward planning when historical
    price bars are not yet loaded.
    """

    def __init__(
        self,
        holidays: Optional[Iterable[date]] = None,
        weekend_days: Tuple[int, ...] = (5, 6),  # 5=Saturday, 6=Sunday
        special_trading_days: Optional[Iterable[date]] = None,
        max_forward_search_days: int = 60,
    ) -> None:
        """Initialize exchange calendar with configurable holidays and weekend rules.

        Args:
            holidays: Iterable of dates designated as official exchange holidays. If omitted,
                only weekend rules are applied; for production equity simulations without market bars,
                official exchange holiday lists should be supplied.
            weekend_days: Tuple of weekday integers (0=Mon, 6=Sun) considered non-trading.
            special_trading_days: Iterable of weekend/holiday dates that host special sessions
                (e.g., Diwali Muhurat trading).
            max_forward_search_days: Maximum days to search forward before declaring exhaustion.
        """
        self._holidays: Set[date] = set(holidays or [])
        self._weekend_days: Set[int] = set(weekend_days)
        self._special_trading_days: Set[date] = set(special_trading_days or [])
        self._max_search_days: int = max_forward_search_days

    def is_trading_day(self, day: date) -> bool:
        """Determine if a date is an active trading session."""
        if day in self._special_trading_days:
            return True
        if day.weekday() in self._weekend_days:
            return False
        if day in self._holidays:
            return False
        return True

    def get_next_trading_day(self, day: date) -> Optional[date]:
        """Find the next trading day strictly after `day` within max search bounds."""
        curr = day + timedelta(days=1)
        for _ in range(self._max_search_days):
            if self.is_trading_day(curr):
                return curr
            curr += timedelta(days=1)
        return None

    def get_previous_trading_day(self, day: date) -> Optional[date]:
        """Find the previous trading day strictly before `day` within max search bounds."""
        curr = day - timedelta(days=1)
        for _ in range(self._max_search_days):
            if self.is_trading_day(curr):
                return curr
            curr -= timedelta(days=1)
        return None

    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """Return all trading days within [start_date, end_date]."""
        if start_date > end_date:
            return []
        days: List[date] = []
        curr = start_date
        while curr <= end_date:
            if self.is_trading_day(curr):
                days.append(curr)
            curr += timedelta(days=1)
        return days
