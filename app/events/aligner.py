"""Trading Session Aligner for Macroeconomic and Regulatory Events.

Aligns discrete macroeconomic and regulatory events with Indian equity trading sessions (NSE/BSE).
Enforces strict temporal session boundaries (09:15:00 open, 15:30:00 close Asia/Kolkata),
prevents look-ahead bias across session close, preserves original timestamps intact,
and handles non-trading days, weekends, holidays, and date-only publications conservatively.
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from app.core.logging_config import get_logger
from app.events.calendar import (
    BaseTradingCalendar,
    IST,
    MARKET_CLOSE_TIME,
    MARKET_OPEN_TIME,
)
from app.events.schemas import MacroEvent

logger = get_logger(__name__)


class SessionPhase(str, Enum):
    """Timing relationship of an event relative to its aligned trading session."""

    PRE_MARKET = "pre_market"       # Published before 09:15:00 IST on session date, or non-trading days prior
    IN_SESSION = "in_session"       # Published between 09:15:00 and 15:30:00 IST on session date
    POST_MARKET = "post_market"     # Published after 15:30:00 IST (aligned to next trading session)


class AlignmentStatus(str, Enum):
    """Status outcomes for session alignment."""

    ALIGNED = "aligned"
    CALENDAR_EXHAUSTED = "calendar_exhausted"
    MISSING_TIMESTAMP = "missing_timestamp"
    INVALID_TIMEZONE = "invalid_timezone"


@dataclass(frozen=True)
class AlignedEventSession:
    """Canonical representation of a MacroEvent aligned to an Indian trading session."""

    event_id: str
    event: MacroEvent
    session_date: Optional[date]
    session_phase: Optional[SessionPhase]
    event_timestamp_ist: Optional[datetime]
    is_eligible_for_session_open: bool
    is_eligible_for_session_close: bool
    status: AlignmentStatus
    effective_session_date: Optional[date] = None
    is_effective_future: bool = False
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert aligned event record to flat dictionary."""
        return {
            "event_id": self.event_id,
            "session_date": self.session_date.isoformat() if self.session_date else None,
            "session_phase": self.session_phase.value if self.session_phase else None,
            "event_timestamp_ist": self.event_timestamp_ist.isoformat() if self.event_timestamp_ist else None,
            "is_eligible_for_session_open": self.is_eligible_for_session_open,
            "is_eligible_for_session_close": self.is_eligible_for_session_close,
            "status": self.status.value,
            "effective_session_date": self.effective_session_date.isoformat() if self.effective_session_date else None,
            "is_effective_future": self.is_effective_future,
            "details": self.details,
            "event": self.event.to_dict(),
        }


class EventSessionAligner:
    """Service aligning MacroEvent records with Indian equity trading sessions."""

    def __init__(
        self,
        calendar: BaseTradingCalendar,
        conservative_date_only: bool = True,
    ) -> None:
        """Initialize session aligner with an injectable trading calendar.

        Args:
            calendar: BaseTradingCalendar implementation providing trading day validation.
            conservative_date_only: If True, events lacking time-of-day precision (e.g. SEBI circulars
                publishing only '16 Oct 2026') are conservatively aligned to the next trading session
                to prevent unverified same-session closing look-ahead.
        """
        self._calendar = calendar
        self._conservative_date_only = conservative_date_only

    def align_event(self, event: MacroEvent) -> AlignedEventSession:
        """Align a single MacroEvent to its appropriate Indian equity trading session.

        Rules:
        1. Timestamps: Primary availability timestamp (`event.primary_timestamp`) is converted
           to Asia/Kolkata (IST). Original event timestamps are never mutated.
        2. Non-Trading Days (Weekends/Holidays): Any event published on a non-trading day is mapped
           to the immediately following active trading day as PRE_MARKET (eligible for open and close).
        3. Pre-Market (< 09:15 IST): Published on a trading day before 09:15 IST is associated
           with that day's session as PRE_MARKET (eligible for open and close).
        4. In-Session (09:15 to 15:30 IST): Published on a trading day during market hours is associated
           with that day's session as IN_SESSION (NOT eligible for session open, eligible for session close).
        5. Post-Market (> 15:30 IST): Published after 15:30 IST on a trading day cannot inform that day's
           closing prediction. It is aligned to the NEXT trading day as PRE_MARKET for that upcoming session.
        6. Date-Only Precision: If the event indicates date-only precision and conservative mode is active,
           it aligns to the next trading day to guarantee zero same-day look-ahead.
        7. Effective Date: Preserved separately; if effective_at is future-dated relative to publication,
           is_effective_future is set to True without affecting publication availability.

        Args:
            event: MacroEvent record to align.

        Returns:
            AlignedEventSession instance detailing session date, phase, and availability flags.
        """
        # 1. Resolve timestamp
        raw_dt = event.primary_timestamp
        if raw_dt is None:
            return AlignedEventSession(
                event_id=event.event_id,
                event=event,
                session_date=None,
                session_phase=None,
                event_timestamp_ist=None,
                is_eligible_for_session_open=False,
                is_eligible_for_session_close=False,
                status=AlignmentStatus.MISSING_TIMESTAMP,
                details="Event has no primary availability timestamp.",
            )

        if raw_dt.tzinfo is None:
            return AlignedEventSession(
                event_id=event.event_id,
                event=event,
                session_date=None,
                session_phase=None,
                event_timestamp_ist=None,
                is_eligible_for_session_open=False,
                is_eligible_for_session_close=False,
                status=AlignmentStatus.INVALID_TIMEZONE,
                details=f"Timestamp '{raw_dt}' is timezone-naive.",
            )

        dt_ist = raw_dt.astimezone(IST)
        event_date = dt_ist.date()
        event_time = dt_ist.time()

        # Check effective date relationship
        is_eff_future = False
        eff_session_date: Optional[date] = None
        if event.effective_at is not None:
            eff_ist = event.effective_at.astimezone(IST)
            eff_date = eff_ist.date()
            if self._calendar.is_trading_day(eff_date):
                eff_session_date = eff_date
            else:
                eff_session_date = self._calendar.get_next_trading_day(eff_date)
            is_eff_future = eff_ist > dt_ist

        # Check date-only precision
        is_date_only = event.raw_metadata.get("time_precision") == "date_only"
        if is_date_only and self._conservative_date_only:
            # Conservative rule: Treat date-only announcement as post-close of event_date,
            # mapping it to the next trading day
            next_day = self._calendar.get_next_trading_day(event_date)
            if next_day is None:
                return AlignedEventSession(
                    event_id=event.event_id,
                    event=event,
                    session_date=None,
                    session_phase=None,
                    event_timestamp_ist=dt_ist,
                    is_eligible_for_session_open=False,
                    is_eligible_for_session_close=False,
                    status=AlignmentStatus.CALENDAR_EXHAUSTED,
                    details=f"Calendar coverage exhausted after date-only event date {event_date}.",
                )
            return AlignedEventSession(
                event_id=event.event_id,
                event=event,
                session_date=next_day,
                session_phase=SessionPhase.POST_MARKET,
                event_timestamp_ist=dt_ist,
                is_eligible_for_session_open=True,
                is_eligible_for_session_close=True,
                status=AlignmentStatus.ALIGNED,
                effective_session_date=eff_session_date,
                is_effective_future=is_eff_future,
                details=f"Date-only event conservatively mapped to next trading day {next_day}.",
            )

        # 2. Evaluate calendar day
        if self._calendar.is_trading_day(event_date):
            if event_time < MARKET_OPEN_TIME:
                # Pre-Market: published before 09:15 IST
                return AlignedEventSession(
                    event_id=event.event_id,
                    event=event,
                    session_date=event_date,
                    session_phase=SessionPhase.PRE_MARKET,
                    event_timestamp_ist=dt_ist,
                    is_eligible_for_session_open=True,
                    is_eligible_for_session_close=True,
                    status=AlignmentStatus.ALIGNED,
                    effective_session_date=eff_session_date,
                    is_effective_future=is_eff_future,
                )
            elif event_time <= MARKET_CLOSE_TIME:
                # In-Session: published between 09:15:00 and 15:30:00 IST
                return AlignedEventSession(
                    event_id=event.event_id,
                    event=event,
                    session_date=event_date,
                    session_phase=SessionPhase.IN_SESSION,
                    event_timestamp_ist=dt_ist,
                    is_eligible_for_session_open=False,
                    is_eligible_for_session_close=True,
                    status=AlignmentStatus.ALIGNED,
                    effective_session_date=eff_session_date,
                    is_effective_future=is_eff_future,
                )
            else:
                # Post-Market: published after 15:30:00 IST
                # Must NOT inform this session's close; maps to next trading session
                next_day = self._calendar.get_next_trading_day(event_date)
                if next_day is None:
                    return AlignedEventSession(
                        event_id=event.event_id,
                        event=event,
                        session_date=None,
                        session_phase=None,
                        event_timestamp_ist=dt_ist,
                        is_eligible_for_session_open=False,
                        is_eligible_for_session_close=False,
                        status=AlignmentStatus.CALENDAR_EXHAUSTED,
                        details=f"Calendar coverage exhausted after post-market session {event_date}.",
                    )
                return AlignedEventSession(
                    event_id=event.event_id,
                    event=event,
                    session_date=next_day,
                    session_phase=SessionPhase.POST_MARKET,
                    event_timestamp_ist=dt_ist,
                    is_eligible_for_session_open=True,
                    is_eligible_for_session_close=True,
                    status=AlignmentStatus.ALIGNED,
                    effective_session_date=eff_session_date,
                    is_effective_future=is_eff_future,
                    details=f"Post-close event from {event_date} aligned to next session {next_day}.",
                )
        else:
            # Weekend or exchange holiday
            next_day = self._calendar.get_next_trading_day(event_date)
            if next_day is None:
                return AlignedEventSession(
                    event_id=event.event_id,
                    event=event,
                    session_date=None,
                    session_phase=None,
                    event_timestamp_ist=dt_ist,
                    is_eligible_for_session_open=False,
                    is_eligible_for_session_close=False,
                    status=AlignmentStatus.CALENDAR_EXHAUSTED,
                    details=f"Calendar coverage exhausted after non-trading date {event_date}.",
                )
            return AlignedEventSession(
                event_id=event.event_id,
                event=event,
                session_date=next_day,
                session_phase=SessionPhase.PRE_MARKET,
                event_timestamp_ist=dt_ist,
                is_eligible_for_session_open=True,
                is_eligible_for_session_close=True,
                status=AlignmentStatus.ALIGNED,
                effective_session_date=eff_session_date,
                is_effective_future=is_eff_future,
                details=f"Non-trading day event ({event_date}) aligned to next trading day {next_day}.",
            )

    def align_events(
        self,
        events: Sequence[MacroEvent],
    ) -> List[AlignedEventSession]:
        """Align a collection of MacroEvent records chronologically."""
        return [self.align_event(e) for e in events]
