"""Indian Equity Market Session and Calendar Engine.

Provides deterministic detection of National Stock Exchange (NSE) and Bombay
Stock Exchange (BSE) trading session states in Indian Standard Time (Asia/Kolkata).

Session Phases (IST = UTC+05:30):
- PRE_OPEN:      09:00:00 to 09:15:00 IST on trading days.
- REGULAR_HOURS: 09:15:00 to 15:30:00 IST on trading days (continuous trading).
- POST_CLOSE:    15:30:00 to 16:00:00 IST on trading days.
- CLOSED:        Outside 09:00-16:00 IST, weekends (Sat/Sun), and exchange holidays.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Optional, Set
from zoneinfo import ZoneInfo

# Canonical Indian market timezone
IST = ZoneInfo("Asia/Kolkata")

# Session boundary times (IST)
PRE_OPEN_START = time(9, 0, 0)
REGULAR_MARKET_OPEN = time(9, 15, 0)
REGULAR_MARKET_CLOSE = time(15, 30, 0)
POST_CLOSE_END = time(16, 0, 0)

# Standard NSE declared trading holidays for 2026 (calendar year)
# Source: NSE India Master Circular / Circulars on Trading Holidays
NSE_HOLIDAYS_2026: Set[date] = {
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 3),   # Holi
    date(2026, 3, 20),  # Id-Ul-Fitr (Ramzan Id)
    date(2026, 3, 27),  # Ram Navami
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 14),  # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 5, 27),  # Bakri Id / Eid ul-Adha
    date(2026, 8, 15),  # Independence Day (Saturday)
    date(2026, 8, 26),  # Milad-un-Nabi
    date(2026, 10, 2),  # Mahatma Gandhi Jayanti
    date(2026, 10, 20), # Dussehra
    date(2026, 11, 8),  # Diwali Laxmi Pujan (Special Muhurat Trading session)
    date(2026, 11, 9),  # Diwali Balipratipada
    date(2026, 11, 24), # Gurunanak Jayanti
    date(2026, 12, 25), # Christmas
}


class MarketSessionState(str, Enum):
    """Discrete operational phases of Indian equity trading sessions."""

    PRE_OPEN = "PRE_OPEN"
    REGULAR_HOURS = "REGULAR_HOURS"
    POST_CLOSE = "POST_CLOSE"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class MarketSessionInfo:
    """Detailed market session state and boundary timestamps."""

    state: MarketSessionState
    is_trading_active: bool
    current_time: datetime
    session_date: date
    is_weekend: bool
    is_holiday: bool
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert session info to dictionary with ISO formatted timestamps."""
        return {
            "state": self.state.value,
            "is_trading_active": self.is_trading_active,
            "current_time": self.current_time.isoformat(),
            "session_date": self.session_date.isoformat(),
            "is_weekend": self.is_weekend,
            "is_holiday": self.is_holiday,
            "next_open": self.next_open.isoformat() if self.next_open else None,
            "next_close": self.next_close.isoformat() if self.next_close else None,
        }


def _localize_to_ist(dt: Optional[datetime] = None) -> datetime:
    """Ensure datetime is localized to Asia/Kolkata (IST)."""
    if dt is None:
        return datetime.now(IST)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def _is_trading_day(d: date, holidays: Set[date]) -> bool:
    """Return True if date is a Monday-Friday non-holiday."""
    return d.weekday() < 5 and d not in holidays


def _get_next_trading_day(from_date: date, holidays: Set[date]) -> date:
    """Find the next upcoming trading day strictly after from_date."""
    curr = from_date + timedelta(days=1)
    while not _is_trading_day(curr, holidays):
        curr += timedelta(days=1)
    return curr


def get_market_session(
    dt: Optional[datetime] = None,
    holidays: Optional[Set[date]] = None,
) -> MarketSessionInfo:
    """Determine the current Indian equity market session state for a given timestamp.

    Args:
        dt: Datetime to evaluate. If naive, assumed to be IST. If timezone-aware,
            converted to Asia/Kolkata. If None, uses datetime.now(IST).
        holidays: Optional set of calendar dates designated as market holidays.
            Defaults to NSE_HOLIDAYS_2026.

    Returns:
        MarketSessionInfo describing the active phase, trading status, and transition points.
    """
    now_ist = _localize_to_ist(dt)
    curr_date = now_ist.date()
    curr_time = now_ist.time()
    active_holidays = holidays if holidays is not None else NSE_HOLIDAYS_2026

    is_weekend = curr_date.weekday() >= 5
    is_holiday = curr_date in active_holidays

    if is_weekend or is_holiday:
        # Market is fully closed for the day
        next_day = _get_next_trading_day(curr_date, active_holidays)
        next_open = datetime.combine(next_day, REGULAR_MARKET_OPEN, tzinfo=IST)
        return MarketSessionInfo(
            state=MarketSessionState.CLOSED,
            is_trading_active=False,
            current_time=now_ist,
            session_date=curr_date,
            is_weekend=is_weekend,
            is_holiday=is_holiday,
            next_open=next_open,
            next_close=None,
        )

    # Weekday non-holiday: check intra-day session boundaries
    if curr_time < PRE_OPEN_START:
        state = MarketSessionState.CLOSED
        is_active = False
        next_open = datetime.combine(curr_date, REGULAR_MARKET_OPEN, tzinfo=IST)
        next_close = datetime.combine(curr_date, REGULAR_MARKET_CLOSE, tzinfo=IST)
    elif curr_time < REGULAR_MARKET_OPEN:
        state = MarketSessionState.PRE_OPEN
        is_active = False
        next_open = datetime.combine(curr_date, REGULAR_MARKET_OPEN, tzinfo=IST)
        next_close = datetime.combine(curr_date, REGULAR_MARKET_CLOSE, tzinfo=IST)
    elif curr_time < REGULAR_MARKET_CLOSE:
        state = MarketSessionState.REGULAR_HOURS
        is_active = True
        next_open = None
        next_close = datetime.combine(curr_date, REGULAR_MARKET_CLOSE, tzinfo=IST)
    elif curr_time < POST_CLOSE_END:
        state = MarketSessionState.POST_CLOSE
        is_active = False
        next_day = _get_next_trading_day(curr_date, active_holidays)
        next_open = datetime.combine(next_day, REGULAR_MARKET_OPEN, tzinfo=IST)
        next_close = None
    else:
        state = MarketSessionState.CLOSED
        is_active = False
        next_day = _get_next_trading_day(curr_date, active_holidays)
        next_open = datetime.combine(next_day, REGULAR_MARKET_OPEN, tzinfo=IST)
        next_close = None

    return MarketSessionInfo(
        state=state,
        is_trading_active=is_active,
        current_time=now_ist,
        session_date=curr_date,
        is_weekend=False,
        is_holiday=False,
        next_open=next_open,
        next_close=next_close,
    )
