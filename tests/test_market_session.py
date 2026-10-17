"""Deterministic Unit Tests for Indian Equity Market Session Engine.

Validates session boundaries, transitions, weekend closures, holiday schedules,
timezone normalization, and dictionary serialization across Indian markets (NSE/BSE).
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
import pytest

from app.market.session import (
    IST,
    NSE_HOLIDAYS_2026,
    MarketSessionInfo,
    MarketSessionState,
    get_market_session,
)


def test_pre_open_session_state() -> None:
    """Verify 09:00 to 09:15 IST on a trading day is classified as PRE_OPEN."""
    dt = datetime(2026, 10, 14, 9, 5, 0, tzinfo=IST)  # Wednesday
    info = get_market_session(dt)

    assert info.state == MarketSessionState.PRE_OPEN
    assert info.is_trading_active is False
    assert info.is_weekend is False
    assert info.is_holiday is False
    assert info.session_date == date(2026, 10, 14)
    assert info.next_open == datetime(2026, 10, 14, 9, 15, tzinfo=IST)
    assert info.next_close == datetime(2026, 10, 14, 15, 30, tzinfo=IST)


def test_regular_trading_hours_session_state() -> None:
    """Verify 09:15 to 15:30 IST on a trading day is classified as REGULAR_HOURS with active trading."""
    dt = datetime(2026, 10, 14, 11, 30, 0, tzinfo=IST)  # Wednesday
    info = get_market_session(dt)

    assert info.state == MarketSessionState.REGULAR_HOURS
    assert info.is_trading_active is True
    assert info.is_weekend is False
    assert info.is_holiday is False
    assert info.next_open is None
    assert info.next_close == datetime(2026, 10, 14, 15, 30, tzinfo=IST)


def test_boundary_times() -> None:
    """Verify exact second boundary behavior for session state transitions."""
    # Exactly 09:00:00 -> PRE_OPEN
    info_open_pre = get_market_session(datetime(2026, 10, 14, 9, 0, 0, tzinfo=IST))
    assert info_open_pre.state == MarketSessionState.PRE_OPEN

    # Exactly 09:15:00 -> REGULAR_HOURS
    info_reg = get_market_session(datetime(2026, 10, 14, 9, 15, 0, tzinfo=IST))
    assert info_reg.state == MarketSessionState.REGULAR_HOURS
    assert info_reg.is_trading_active is True

    # Exactly 15:30:00 -> POST_CLOSE
    info_post = get_market_session(datetime(2026, 10, 14, 15, 30, 0, tzinfo=IST))
    assert info_post.state == MarketSessionState.POST_CLOSE
    assert info_post.is_trading_active is False

    # Exactly 16:00:00 -> CLOSED
    info_closed = get_market_session(datetime(2026, 10, 14, 16, 0, 0, tzinfo=IST))
    assert info_closed.state == MarketSessionState.CLOSED


def test_post_close_session_state() -> None:
    """Verify 15:30 to 16:00 IST on a trading day is classified as POST_CLOSE."""
    dt = datetime(2026, 10, 14, 15, 45, 0, tzinfo=IST)  # Wednesday
    info = get_market_session(dt)

    assert info.state == MarketSessionState.POST_CLOSE
    assert info.is_trading_active is False
    assert info.next_open == datetime(2026, 10, 15, 9, 15, tzinfo=IST)
    assert info.next_close is None


def test_closed_before_pre_open_and_evening() -> None:
    """Verify early morning and evening hours are classified as CLOSED."""
    early = datetime(2026, 10, 14, 7, 30, 0, tzinfo=IST)
    info_early = get_market_session(early)
    assert info_early.state == MarketSessionState.CLOSED
    assert info_early.is_trading_active is False
    assert info_early.next_open == datetime(2026, 10, 14, 9, 15, tzinfo=IST)

    night = datetime(2026, 10, 14, 21, 0, 0, tzinfo=IST)
    info_night = get_market_session(night)
    assert info_night.state == MarketSessionState.CLOSED
    assert info_night.next_open == datetime(2026, 10, 15, 9, 15, tzinfo=IST)


def test_weekend_closure() -> None:
    """Verify Saturday and Sunday are CLOSED with next_open set to Monday 09:15 IST."""
    saturday = datetime(2026, 10, 17, 12, 0, 0, tzinfo=IST)
    info_sat = get_market_session(saturday)

    assert info_sat.state == MarketSessionState.CLOSED
    assert info_sat.is_trading_active is False
    assert info_sat.is_weekend is True
    assert info_sat.is_holiday is False
    # Next trading day is Monday, Oct 19, 2026
    assert info_sat.next_open == datetime(2026, 10, 19, 9, 15, tzinfo=IST)

    sunday = datetime(2026, 10, 18, 14, 0, 0, tzinfo=IST)
    info_sun = get_market_session(sunday)
    assert info_sun.state == MarketSessionState.CLOSED
    assert info_sun.is_weekend is True
    assert info_sun.next_open == datetime(2026, 10, 19, 9, 15, tzinfo=IST)


def test_official_holiday_closure() -> None:
    """Verify designated market holidays are CLOSED and advance to next non-holiday."""
    republic_day = datetime(2026, 1, 26, 10, 0, 0, tzinfo=IST)  # Monday holiday
    info = get_market_session(republic_day)

    assert info.state == MarketSessionState.CLOSED
    assert info.is_trading_active is False
    assert info.is_holiday is True
    assert info.is_weekend is False
    # Next open is Tuesday Jan 27, 2026 at 09:15 IST
    assert info.next_open == datetime(2026, 1, 27, 9, 15, tzinfo=IST)


def test_timezone_conversion_and_naive_inputs() -> None:
    """Verify UTC and naive datetimes are correctly converted/localized to IST."""
    # 04:30 UTC = 10:00 IST (REGULAR_HOURS)
    dt_utc = datetime(2026, 10, 14, 4, 30, 0, tzinfo=timezone.utc)
    info_utc = get_market_session(dt_utc)
    assert info_utc.state == MarketSessionState.REGULAR_HOURS
    assert info_utc.current_time.tzinfo == IST
    assert info_utc.current_time.hour == 10
    assert info_utc.current_time.minute == 0

    # Naive datetime is treated as IST
    dt_naive = datetime(2026, 10, 14, 10, 0, 0)
    info_naive = get_market_session(dt_naive)
    assert info_naive.state == MarketSessionState.REGULAR_HOURS
    assert info_naive.current_time.tzinfo == IST


def test_session_info_to_dict_serialization() -> None:
    """Verify dictionary serialization preserves ISO-formatted datetimes and string enums."""
    dt = datetime(2026, 10, 14, 10, 0, 0, tzinfo=IST)
    info = get_market_session(dt)
    d = info.to_dict()

    assert d["state"] == "REGULAR_HOURS"
    assert d["is_trading_active"] is True
    assert "2026-10-14T10:00:00+05:30" in d["current_time"]
    assert d["session_date"] == "2026-10-14"
    assert d["is_weekend"] is False
    assert d["is_holiday"] is False
    assert d["next_close"] is not None
