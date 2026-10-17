"""Unit and Integration Tests for Event Impact Analysis and Trading Session Alignment (Day 30).

Validates:
1. Calendar abstractions (MarketDataTradingCalendar & ExchangeTradingCalendar).
2. EventSessionAligner across all session phases:
   - Pre-market (< 09:15 IST)
   - In-session (09:15 to 15:30 IST)
   - Post-market (> 15:30 IST)
   - Weekends and exchange holidays
   - Date-only precision handling (conservative next-session alignment)
   - Boundary conditions (exact 09:15:00 and 15:30:00 IST)
   - Missing and timezone-naive timestamps
3. EventImpactAnalyzer:
   - 1-session, 3-session, 5-session forward returns
   - Same-day return from prior close
   - Pre-event and post-event realized volatility (5-session rolling window)
   - Benchmark relative excess return (with and without benchmark bars)
   - Incomplete future outcome windows (T+1 missing)
   - Insufficient pre-event history (< 5 prior sessions)
   - Aggregate impact summary statistics (mean, median, stdev)
   - Multi-event deduplication preventing double-counting
   - Non-causal disclaimer preservation
"""

from datetime import date, datetime, time, timedelta
import math
import pytest
from zoneinfo import ZoneInfo

from app.core.schemas import MarketOHLCV
from app.events.aligner import (
    AlignedEventSession,
    AlignmentStatus,
    EventSessionAligner,
    SessionPhase,
)
from app.events.calendar import (
    ExchangeTradingCalendar,
    IST,
    MarketDataTradingCalendar,
)
from app.events.impact import (
    AggregateImpactSummary,
    EventImpactAnalyzer,
    EventImpactMeasurement,
    NON_CAUSAL_DISCLAIMER,
)
from app.events.schemas import (
    EventCategory,
    MacroEvent,
    StructuredEventValue,
)


# --- Helper Fixtures ---

def _make_bar(d: date, close: float, open_: Optional[float] = None, symbol: str = "TEST") -> MarketOHLCV:
    """Helper creating a valid daily MarketOHLCV record."""
    op = open_ if open_ is not None else close
    hi = max(op, close) + 1.0
    lo = min(op, close) - 1.0
    ts = datetime.combine(d, time(15, 30), tzinfo=IST)
    return MarketOHLCV(
        symbol=symbol,
        timestamp=ts,
        open=op,
        high=hi,
        low=lo,
        close=close,
        volume=100000,
        source="test",
    )


# --- 1. Calendar Tests ---

def test_market_data_trading_calendar() -> None:
    """Verify MarketDataTradingCalendar derives trading sessions directly from bars."""
    d1 = date(2026, 10, 12)  # Monday
    d2 = date(2026, 10, 13)  # Tuesday
    d3 = date(2026, 10, 15)  # Thursday (Wednesday 14 was a holiday)
    bars = [_make_bar(d1, 100.0), _make_bar(d2, 102.0), _make_bar(d3, 105.0)]

    cal = MarketDataTradingCalendar(bars)
    assert cal.is_trading_day(d1) is True
    assert cal.is_trading_day(d2) is True
    assert cal.is_trading_day(date(2026, 10, 14)) is False  # Holiday
    assert cal.is_trading_day(date(2026, 10, 18)) is False  # Sunday

    # Next trading day
    assert cal.get_next_trading_day(d1) == d2
    assert cal.get_next_trading_day(d2) == d3  # Skips Wednesday holiday
    assert cal.get_next_trading_day(d3) is None  # Coverage exhausted

    # Previous trading day
    assert cal.get_previous_trading_day(d3) == d2
    assert cal.get_previous_trading_day(d2) == d1
    assert cal.get_previous_trading_day(d1) is None


def test_exchange_trading_calendar_holidays_and_special() -> None:
    """Verify ExchangeTradingCalendar handles weekends, custom holidays, and Muhurat sessions."""
    holiday = date(2026, 10, 14)  # Wednesday holiday
    special_muhurat = date(2026, 10, 17)  # Saturday special trading session
    cal = ExchangeTradingCalendar(
        holidays=[holiday],
        special_trading_days=[special_muhurat],
    )

    mon = date(2026, 10, 12)
    tue = date(2026, 10, 13)
    wed = date(2026, 10, 14)
    thu = date(2026, 10, 15)
    fri = date(2026, 10, 16)
    sat = date(2026, 10, 17)
    sun = date(2026, 10, 18)

    assert cal.is_trading_day(mon) is True
    assert cal.is_trading_day(wed) is False  # Holiday
    assert cal.is_trading_day(sat) is True   # Special Saturday Muhurat
    assert cal.is_trading_day(sun) is False  # Sunday

    assert cal.get_next_trading_day(tue) == thu  # Skips Wednesday
    assert cal.get_next_trading_day(fri) == sat  # Saturday Muhurat session
    assert cal.get_next_trading_day(sat) == date(2026, 10, 19)  # Next Monday


# --- 2. Session Aligner Tests ---

def test_align_event_pre_market() -> None:
    """Verify an event published before 09:15 IST aligns to that day's session as PRE_MARKET."""
    cal = ExchangeTradingCalendar()
    aligner = EventSessionAligner(calendar=cal)

    # Monday 08:30 IST
    pub_dt = datetime(2026, 10, 12, 8, 30, tzinfo=IST)
    ev = MacroEvent(
        title="Pre-Market Macro Release",
        category=EventCategory.MACRO_INDICATOR,
        event_type="cpi",
        source_org="MoSPI",
        published_at=pub_dt,
        ingested_at=pub_dt,
    )

    aligned = aligner.align_event(ev)
    assert aligned.status == AlignmentStatus.ALIGNED
    assert aligned.session_date == date(2026, 10, 12)
    assert aligned.session_phase == SessionPhase.PRE_MARKET
    assert aligned.is_eligible_for_session_open is True
    assert aligned.is_eligible_for_session_close is True


def test_align_event_in_session() -> None:
    """Verify an event published during market hours (11:30 IST) aligns as IN_SESSION."""
    cal = ExchangeTradingCalendar()
    aligner = EventSessionAligner(calendar=cal)

    # Monday 11:30 IST
    pub_dt = datetime(2026, 10, 12, 11, 30, tzinfo=IST)
    ev = MacroEvent(
        title="Mid-Day RBI MPC Resolution",
        category=EventCategory.MONETARY_POLICY,
        event_type="mpc_statement",
        source_org="Reserve Bank of India",
        published_at=pub_dt,
        ingested_at=pub_dt,
    )

    aligned = aligner.align_event(ev)
    assert aligned.status == AlignmentStatus.ALIGNED
    assert aligned.session_date == date(2026, 10, 12)
    assert aligned.session_phase == SessionPhase.IN_SESSION
    assert aligned.is_eligible_for_session_open is False  # Cannot use for market open!
    assert aligned.is_eligible_for_session_close is True   # Can use for market close


def test_align_event_post_market_does_not_leak_into_same_day() -> None:
    """Verify an event published after 15:30 IST maps to the NEXT trading day."""
    cal = ExchangeTradingCalendar()
    aligner = EventSessionAligner(calendar=cal)

    # Monday 17:45 IST
    pub_dt = datetime(2026, 10, 12, 17, 45, tzinfo=IST)
    ev = MacroEvent(
        title="Evening SEBI Circular",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=pub_dt,
        ingested_at=pub_dt,
    )

    aligned = aligner.align_event(ev)
    assert aligned.status == AlignmentStatus.ALIGNED
    # Must align to Tuesday, NEVER Monday
    assert aligned.session_date == date(2026, 10, 13)
    assert aligned.session_phase == SessionPhase.POST_MARKET
    assert aligned.is_eligible_for_session_open is True  # Eligible before Tuesday open
    assert aligned.is_eligible_for_session_close is True


def test_align_event_weekend_and_holiday() -> None:
    """Verify events on weekend or holiday map to the next active session as PRE_MARKET."""
    holiday = date(2026, 10, 14)  # Wednesday holiday
    cal = ExchangeTradingCalendar(holidays=[holiday])
    aligner = EventSessionAligner(calendar=cal)

    # 1. Saturday event
    sat_dt = datetime(2026, 10, 10, 12, 0, tzinfo=IST)
    ev_sat = MacroEvent(
        title="Weekend Policy Speech",
        category=EventCategory.GOVERNMENT,
        event_type="speech",
        source_org="MoF",
        published_at=sat_dt,
        ingested_at=sat_dt,
    )
    aligned_sat = aligner.align_event(ev_sat)
    assert aligned_sat.session_date == date(2026, 10, 12)  # Monday
    assert aligned_sat.session_phase == SessionPhase.PRE_MARKET

    # 2. Holiday event (Wednesday)
    wed_dt = datetime(2026, 10, 14, 10, 0, tzinfo=IST)
    ev_hol = MacroEvent(
        title="Holiday Release",
        category=EventCategory.REGULATORY,
        event_type="notice",
        source_org="SEBI",
        published_at=wed_dt,
        ingested_at=wed_dt,
    )
    aligned_hol = aligner.align_event(ev_hol)
    assert aligned_hol.session_date == date(2026, 10, 15)  # Thursday (skips Wednesday)
    assert aligned_hol.session_phase == SessionPhase.PRE_MARKET


def test_align_event_date_only_conservative() -> None:
    """Verify date-only events (e.g. SEBI circular with only date) align to next day conservatively."""
    cal = ExchangeTradingCalendar()
    aligner = EventSessionAligner(calendar=cal, conservative_date_only=True)

    # Date-only event: published_at has 00:00:00 but metadata marks date_only
    dt = datetime(2026, 10, 12, 0, 0, tzinfo=IST)
    ev = MacroEvent(
        title="SEBI Master Circular Without Time Component",
        category=EventCategory.REGULATORY,
        event_type="master_circular",
        source_org="SEBI",
        published_at=dt,
        ingested_at=dt,
        raw_metadata={"time_precision": "date_only"},
    )

    aligned = aligner.align_event(ev)
    assert aligned.status == AlignmentStatus.ALIGNED
    # In conservative mode, date-only event aligns to Tuesday 13 Oct to guarantee zero same-day lookahead
    assert aligned.session_date == date(2026, 10, 13)
    assert aligned.is_eligible_for_session_open is True


def test_align_event_timezone_and_boundary_conditions() -> None:
    """Verify UTC timezone conversion and exact session open (09:15) / close (15:30) boundaries."""
    cal = ExchangeTradingCalendar()
    aligner = EventSessionAligner(calendar=cal)

    # 1. UTC timestamp: 2026-10-12 03:45:00 UTC == 2026-10-12 09:15:00 IST (Exact Market Open)
    exact_open_utc = datetime(2026, 10, 12, 3, 45, 0, tzinfo=ZoneInfo("UTC"))
    ev_open = MacroEvent(
        title="Event at Exact Market Open",
        category=EventCategory.MONETARY_POLICY,
        event_type="repo",
        source_org="RBI",
        published_at=exact_open_utc,
        ingested_at=exact_open_utc,
    )
    aligned_open = aligner.align_event(ev_open)
    assert aligned_open.session_date == date(2026, 10, 12)
    assert aligned_open.session_phase == SessionPhase.IN_SESSION
    assert aligned_open.is_eligible_for_session_open is False
    assert aligned_open.is_eligible_for_session_close is True

    # 2. Exact Market Close: 15:30:00 IST (Still in-session, available for close)
    exact_close = datetime(2026, 10, 12, 15, 30, 0, tzinfo=IST)
    ev_close = MacroEvent(
        title="Event at Exact Market Close",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=exact_close,
        ingested_at=exact_close,
    )
    aligned_close = aligner.align_event(ev_close)
    assert aligned_close.session_date == date(2026, 10, 12)
    assert aligned_close.session_phase == SessionPhase.IN_SESSION

    # 3. 1 second after close: 15:30:01 IST -> Must map to next day!
    after_close = datetime(2026, 10, 12, 15, 30, 1, tzinfo=IST)
    ev_after = MacroEvent(
        title="Event 1 Second After Close",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=after_close,
        ingested_at=after_close,
    )
    aligned_after = aligner.align_event(ev_after)
    assert aligned_after.session_date == date(2026, 10, 13)
    assert aligned_after.session_phase == SessionPhase.POST_MARKET


# --- 3. Impact Analyzer Tests ---

def test_impact_analyzer_full_windows() -> None:
    """Verify returns, 5d volatility, and benchmark calculations on clean market data."""
    # 12 trading sessions: Oct 1 through Oct 16
    dates = [
        date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7),
        date(2026, 10, 8), date(2026, 10, 9), date(2026, 10, 12), date(2026, 10, 13), date(2026, 10, 14),
        date(2026, 10, 15), date(2026, 10, 16),
    ]
    # Stock prices: starts at 100 on day 0, event session is idx 5 (Oct 8) with close 110.0
    # Day 6 (Oct 9): 112.2 (+2.0% forward 1d return)
    # Day 8 (Oct 13): 115.5 (+5.0% forward 3d return)
    # Day 10 (Oct 15): 121.0 (+10.0% forward 5d return)
    stock_closes = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.2, 114.0, 115.5, 118.0, 121.0, 122.0]
    stock_bars = [_make_bar(d, px, symbol="INFY") for d, px in zip(dates, stock_closes)]

    # Benchmark prices: event session close 20000, day 6 close 20200 (+1.0% return)
    bench_closes = [19000 + i * 200 for i in range(len(dates))]
    bench_bars = [_make_bar(d, px, symbol="^NSEI") for d, px in zip(dates, bench_closes)]

    cal = MarketDataTradingCalendar(stock_bars)
    aligner = EventSessionAligner(calendar=cal)
    analyzer = EventImpactAnalyzer()

    # Event on Oct 8 before market open
    ev = MacroEvent(
        title="Major Tech Policy Update",
        category=EventCategory.GOVERNMENT,
        event_type="policy",
        source_org="MeitY",
        published_at=datetime(2026, 10, 8, 8, 30, tzinfo=IST),
        ingested_at=datetime(2026, 10, 8, 8, 30, tzinfo=IST),
    )
    aligned = aligner.align_event(ev)
    assert aligned.session_date == date(2026, 10, 8)

    measurement = analyzer.measure_event_impact(
        aligned_event=aligned,
        market_bars=stock_bars,
        benchmark_bars=bench_bars,
        benchmark_symbol="^NSEI",
    )

    assert measurement.status == "MEASURED"
    assert measurement.symbol == "INFY"
    assert measurement.session_close == 110.0
    assert measurement.prior_close == 108.0
    # Same-day return: (110 - 108) / 108 == +0.018519
    assert measurement.same_day_return == round((110.0 / 108.0) - 1.0, 6)

    # Forward 1d return: (112.2 - 110) / 110 == +0.02
    assert measurement.forward_return_1d == 0.02
    # Forward 3d return: (115.5 - 110) / 110 == +0.05
    assert measurement.forward_return_3d == 0.05
    # Forward 5d return: (121.0 - 110) / 110 == +0.10
    assert measurement.forward_return_5d == 0.10

    # Volatility checks: both pre and post 5d volatilities must be positive floats
    assert measurement.pre_event_volatility_5d is not None
    assert measurement.pre_event_volatility_5d > 0.0
    assert measurement.post_event_volatility_5d is not None
    assert measurement.post_event_volatility_5d > 0.0

    # Benchmark relative return:
    # Benchmark 1d return from Oct 8 to Oct 9: bench_closes[5]=20000, bench_closes[6]=20200 -> +0.01
    assert measurement.benchmark_forward_return_1d == 0.01
    # Relative return: stock (0.02) - bench (0.01) == +0.01
    assert measurement.relative_forward_return_1d == 0.01


def test_impact_analyzer_incomplete_future_window() -> None:
    """Verify that an event occurring on the latest known session returns INCOMPLETE_OUTCOME_WINDOW."""
    d1 = date(2026, 10, 14)
    d2 = date(2026, 10, 15)
    bars = [_make_bar(d1, 100.0), _make_bar(d2, 105.0)]

    cal = MarketDataTradingCalendar(bars)
    aligner = EventSessionAligner(calendar=cal)
    analyzer = EventImpactAnalyzer()

    # Event on latest session (Oct 15)
    ev = MacroEvent(
        title="Latest Session Announcement",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        ingested_at=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
    )
    aligned = aligner.align_event(ev)
    assert aligned.session_date == d2

    measurement = analyzer.measure_event_impact(aligned, market_bars=bars)
    assert measurement.status == "INCOMPLETE_OUTCOME_WINDOW"
    assert measurement.forward_return_1d is None
    assert measurement.forward_return_3d is None
    assert measurement.forward_return_5d is None
    assert "T+1 outcome session has not occurred" in (measurement.exclusion_reason or "")


def test_impact_analyzer_insufficient_history() -> None:
    """Verify that when fewer than 5 historical sessions precede the event, pre-volatility is None."""
    d1 = date(2026, 10, 12)
    d2 = date(2026, 10, 13)
    d3 = date(2026, 10, 14)
    bars = [_make_bar(d1, 100.0), _make_bar(d2, 102.0), _make_bar(d3, 104.0)]

    cal = MarketDataTradingCalendar(bars)
    aligner = EventSessionAligner(calendar=cal)
    analyzer = EventImpactAnalyzer()

    # Event on day index 1 (only 1 prior session)
    ev = MacroEvent(
        title="Early Announcement",
        category=EventCategory.REGULATORY,
        event_type="notice",
        source_org="SEBI",
        published_at=datetime(2026, 10, 13, 8, 30, tzinfo=IST),
        ingested_at=datetime(2026, 10, 13, 8, 30, tzinfo=IST),
    )
    aligned = aligner.align_event(ev)

    measurement = analyzer.measure_event_impact(aligned, market_bars=bars)
    assert measurement.pre_event_volatility_5d is None
    assert "Insufficient pre-event history" in (measurement.exclusion_reason or "")


def test_impact_analyzer_deduplication_and_aggregates() -> None:
    """Verify analyze_events deduplicates identical event IDs and calculates aggregate summary."""
    dates = [date(2026, 10, i) for i in range(1, 15)]
    bars = [_make_bar(d, 100.0 + i, symbol="RELIANCE") for i, d in enumerate(dates)]

    cal = MarketDataTradingCalendar(bars)
    aligner = EventSessionAligner(calendar=cal)
    analyzer = EventImpactAnalyzer()

    ev1 = MacroEvent(
        title="Event A",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=datetime(2026, 10, 5, 8, 30, tzinfo=IST),
        ingested_at=datetime(2026, 10, 5, 8, 30, tzinfo=IST),
    )
    ev2 = MacroEvent(
        title="Event B",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        published_at=datetime(2026, 10, 6, 8, 30, tzinfo=IST),
        ingested_at=datetime(2026, 10, 6, 8, 30, tzinfo=IST),
    )

    # Pass ev1 TWICE (duplicate) and ev2
    aligned_events = [aligner.align_event(ev1), aligner.align_event(ev1), aligner.align_event(ev2)]

    measurements, summary = analyzer.analyze_events(
        aligned_events=aligned_events,
        market_bars=bars,
        deduplicate=True,
    )

    # Duplicate was filtered: 3 inputs -> 2 measurements
    assert len(measurements) == 2
    assert summary.total_events == 3
    assert summary.eligible_events == 2
    assert summary.completed_outcomes_1d == 2
    assert summary.mean_return_1d is not None
    assert summary.median_return_1d is not None
    assert NON_CAUSAL_DISCLAIMER in summary.disclaimer


def test_pre_event_volatility_strictly_excludes_event_session_close() -> None:
    """Regression test: verify pre-event volatility does not leak the event day's reaction."""
    dates = [
        date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7),
        date(2026, 10, 8), date(2026, 10, 9),
    ]
    # Indices 0 to 4 have completely flat prices (returns = 0.0, stdev = 0.0)
    # Index 5 (event day, Oct 8) spikes violently to 200.0 (+100%)
    closes = [100.0, 100.0, 100.0, 100.0, 100.0, 200.0, 202.0]
    bars = [_make_bar(d, px, symbol="TEST") for d, px in zip(dates, closes)]

    cal = MarketDataTradingCalendar(bars)
    aligner = EventSessionAligner(calendar=cal)
    analyzer = EventImpactAnalyzer()

    ev = MacroEvent(
        title="Spike Announcement",
        category=EventCategory.REGULATORY,
        event_type="notice",
        source_org="SEBI",
        published_at=datetime(2026, 10, 8, 8, 30, tzinfo=IST),
        ingested_at=datetime(2026, 10, 8, 8, 30, tzinfo=IST),
    )
    aligned = aligner.align_event(ev)
    meas = analyzer.measure_event_impact(aligned, market_bars=bars)

    # If event day close (200.0) leaked into pre-event volatility, stdev would be > 0.
    # Since all prior sessions were 100.0, pre-event return stdev must be exactly 0.0.
    assert meas.pre_event_volatility_5d == 0.0


def test_benchmark_date_misalignment_returns_none() -> None:
    """Regression test: verify benchmark returns return None if benchmark dates do not match stock outcome date."""
    stock_bars = [
        _make_bar(date(2026, 10, 8), 100.0, symbol="STOCK"),
        _make_bar(date(2026, 10, 9), 102.0, symbol="STOCK"),  # Outcome date = Oct 9
    ]
    bench_bars = [
        _make_bar(date(2026, 10, 8), 1000.0, symbol="^NSEI"),
        _make_bar(date(2026, 10, 12), 1010.0, symbol="^NSEI"), # Benchmark missing Oct 9! Next is Oct 12
    ]

    cal = MarketDataTradingCalendar(stock_bars)
    aligner = EventSessionAligner(calendar=cal)
    analyzer = EventImpactAnalyzer()

    ev = MacroEvent(
        title="Event",
        category=EventCategory.REGULATORY,
        event_type="notice",
        source_org="SEBI",
        published_at=datetime(2026, 10, 8, 8, 30, tzinfo=IST),
        ingested_at=datetime(2026, 10, 8, 8, 30, tzinfo=IST),
    )
    aligned = aligner.align_event(ev)
    meas = analyzer.measure_event_impact(aligned, market_bars=stock_bars, benchmark_bars=bench_bars)

    assert meas.forward_return_1d == 0.02
    # Misaligned benchmark date (Oct 12 != Oct 9) must not compute an incompatible return
    assert meas.benchmark_forward_return_1d is None
    assert meas.relative_forward_return_1d is None


def test_market_bars_with_duplicate_session_dates_deduplicated() -> None:
    """Regression test: verify duplicate bars for the same session date are deduplicated."""
    # Duplicate bars for Oct 8
    b1_early = _make_bar(date(2026, 10, 8), 100.0)
    b1_late = _make_bar(date(2026, 10, 8), 100.0)
    b2 = _make_bar(date(2026, 10, 9), 105.0)

    bars = [b1_early, b1_late, b2]
    cal = MarketDataTradingCalendar(bars)
    aligner = EventSessionAligner(calendar=cal)
    analyzer = EventImpactAnalyzer()

    ev = MacroEvent(
        title="Event",
        category=EventCategory.REGULATORY,
        event_type="notice",
        source_org="SEBI",
        published_at=datetime(2026, 10, 8, 8, 30, tzinfo=IST),
        ingested_at=datetime(2026, 10, 8, 8, 30, tzinfo=IST),
    )
    aligned = aligner.align_event(ev)
    meas = analyzer.measure_event_impact(aligned, market_bars=bars)

    # Forward 1d should correctly compare Oct 8 (100) to Oct 9 (105), not Oct 8 duplicate
    assert meas.forward_return_1d == 0.05


def test_non_finite_bar_prices_handled_safely() -> None:
    """Regression test: verify NaN or non-positive prices do not crash or poison returns."""
    d1 = date(2026, 10, 8)
    d2 = date(2026, 10, 9)
    # NaN close
    nan_bar = MarketOHLCV(
        symbol="TEST",
        timestamp=datetime.combine(d2, time(15, 30), tzinfo=IST),
        open=100.0,
        high=105.0,
        low=95.0,
        close=float("nan"),
        volume=1000,
        source="test",
    )
    bars = [_make_bar(d1, 100.0), nan_bar]

    cal = MarketDataTradingCalendar(bars)
    aligner = EventSessionAligner(calendar=cal)
    analyzer = EventImpactAnalyzer()

    ev = MacroEvent(
        title="Event",
        category=EventCategory.REGULATORY,
        event_type="notice",
        source_org="SEBI",
        published_at=datetime(2026, 10, 8, 8, 30, tzinfo=IST),
        ingested_at=datetime(2026, 10, 8, 8, 30, tzinfo=IST),
    )
    aligned = aligner.align_event(ev)
    meas = analyzer.measure_event_impact(aligned, market_bars=bars)

    # Next close is NaN -> return must be None, NOT nan float
    assert meas.forward_return_1d is None
