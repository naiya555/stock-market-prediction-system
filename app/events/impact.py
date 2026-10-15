"""Event Impact Analysis and Trading Session Measurement Layer.

Provides descriptive, point-in-time calculation of market outcomes following
macroeconomic and regulatory announcements aligned with Indian trading sessions.
Calculates subsequent 1-session, 3-session, and 5-session forward returns,
pre- and post-event realized volatilities, and benchmark-relative excess returns
without making causal assertions or introducing forward look-ahead leakage.
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime
import math
import statistics
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV
from app.events.aligner import AlignedEventSession, AlignmentStatus, SessionPhase
from app.events.calendar import IST
from app.market.returns import calculate_standard_deviation

logger = get_logger(__name__)

NON_CAUSAL_DISCLAIMER = (
    "Descriptive historical observations only; does not assert causal relationship "
    "or predictable future price movement."
)


@dataclass(frozen=True)
class EventImpactMeasurement:
    """Canonical representation of realized market metrics following an aligned event."""

    event_id: str
    symbol: str
    session_date: date
    session_phase: SessionPhase
    session_open: Optional[float]
    session_close: Optional[float]
    prior_close: Optional[float]
    same_day_return: Optional[float]
    forward_return_1d: Optional[float]
    forward_return_3d: Optional[float]
    forward_return_5d: Optional[float]
    pre_event_volatility_5d: Optional[float]
    post_event_volatility_5d: Optional[float]
    benchmark_symbol: Optional[str] = None
    benchmark_forward_return_1d: Optional[float] = None
    relative_forward_return_1d: Optional[float] = None
    status: str = "MEASURED"
    exclusion_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert impact measurement record to flat dictionary."""
        return {
            "event_id": self.event_id,
            "symbol": self.symbol,
            "session_date": self.session_date.isoformat(),
            "session_phase": self.session_phase.value,
            "session_open": self.session_open,
            "session_close": self.session_close,
            "prior_close": self.prior_close,
            "same_day_return": self.same_day_return,
            "forward_return_1d": self.forward_return_1d,
            "forward_return_3d": self.forward_return_3d,
            "forward_return_5d": self.forward_return_5d,
            "pre_event_volatility_5d": self.pre_event_volatility_5d,
            "post_event_volatility_5d": self.post_event_volatility_5d,
            "benchmark_symbol": self.benchmark_symbol,
            "benchmark_forward_return_1d": self.benchmark_forward_return_1d,
            "relative_forward_return_1d": self.relative_forward_return_1d,
            "status": self.status,
            "exclusion_reason": self.exclusion_reason,
        }


@dataclass(frozen=True)
class AggregateImpactSummary:
    """Audit summary of empirical market reactions across multiple aligned events."""

    symbol: str
    total_events: int
    eligible_events: int
    completed_outcomes_1d: int
    mean_return_1d: Optional[float]
    median_return_1d: Optional[float]
    std_return_1d: Optional[float]
    completed_outcomes_5d: int
    mean_return_5d: Optional[float]
    mean_pre_volatility_5d: Optional[float]
    mean_post_volatility_5d: Optional[float]
    incomplete_or_unavailable_count: int
    disclaimer: str = NON_CAUSAL_DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregate summary to flat dictionary."""
        return asdict(self)


class EventImpactAnalyzer:
    """Service computing empirical price and volatility metrics for aligned events."""

    def _resolve_bar_date(self, bar: MarketOHLCV) -> date:
        """Resolve bar date in IST timezone."""
        ts = bar.timestamp
        if ts.tzinfo is not None:
            return ts.astimezone(IST).date()
        return ts.date()

    def measure_event_impact(
        self,
        aligned_event: AlignedEventSession,
        market_bars: Sequence[MarketOHLCV],
        benchmark_bars: Optional[Sequence[MarketOHLCV]] = None,
        benchmark_symbol: Optional[str] = None,
    ) -> EventImpactMeasurement:
        """Calculate subsequent returns and realized volatility for an aligned event.

        Args:
            aligned_event: AlignedEventSession record output from EventSessionAligner.
            market_bars: Chronological sequence of historical bars for the measured asset.
            benchmark_bars: Optional chronological sequence of benchmark bars (e.g. NIFTY 50).
            benchmark_symbol: Optional identifier for benchmark index (e.g. '^NSEI').

        Returns:
            EventImpactMeasurement record capturing empirical outcome or explicit exclusion reason.
        """
        # Guard: check alignment status
        if aligned_event.status != AlignmentStatus.ALIGNED or aligned_event.session_date is None:
            return EventImpactMeasurement(
                event_id=aligned_event.event_id,
                symbol="UNKNOWN",
                session_date=date.min,
                session_phase=SessionPhase.PRE_MARKET,
                session_open=None,
                session_close=None,
                prior_close=None,
                same_day_return=None,
                forward_return_1d=None,
                forward_return_3d=None,
                forward_return_5d=None,
                pre_event_volatility_5d=None,
                post_event_volatility_5d=None,
                status="ALIGNMENT_FAILED",
                exclusion_reason=aligned_event.details or f"Event alignment status: {aligned_event.status.value}",
            )

        target_date = aligned_event.session_date
        phase = aligned_event.session_phase or SessionPhase.PRE_MARKET

        if not market_bars:
            return EventImpactMeasurement(
                event_id=aligned_event.event_id,
                symbol="UNKNOWN",
                session_date=target_date,
                session_phase=phase,
                session_open=None,
                session_close=None,
                prior_close=None,
                same_day_return=None,
                forward_return_1d=None,
                forward_return_3d=None,
                forward_return_5d=None,
                pre_event_volatility_5d=None,
                post_event_volatility_5d=None,
                status="BARS_UNAVAILABLE",
                exclusion_reason="Empty market bars sequence supplied to impact analyzer.",
            )

        # Sort bars chronologically
        sorted_bars = sorted(market_bars, key=lambda b: b.timestamp)
        symbol = sorted_bars[0].symbol

        # Find target session bar index
        target_idx: Optional[int] = None
        for i, bar in enumerate(sorted_bars):
            if self._resolve_bar_date(bar) == target_date:
                target_idx = i
                break

        if target_idx is None:
            return EventImpactMeasurement(
                event_id=aligned_event.event_id,
                symbol=symbol,
                session_date=target_date,
                session_phase=phase,
                session_open=None,
                session_close=None,
                prior_close=None,
                same_day_return=None,
                forward_return_1d=None,
                forward_return_3d=None,
                forward_return_5d=None,
                pre_event_volatility_5d=None,
                post_event_volatility_5d=None,
                status="BARS_UNAVAILABLE",
                exclusion_reason=f"No market bar found for aligned session date {target_date}.",
            )

        curr_bar = sorted_bars[target_idx]
        curr_open = curr_bar.open
        curr_close = curr_bar.close

        # Prior session close & same-day return
        prior_close: Optional[float] = None
        same_day_ret: Optional[float] = None
        if target_idx > 0:
            prior_close = sorted_bars[target_idx - 1].close
            if prior_close > 0.0:
                same_day_ret = round((curr_close / prior_close) - 1.0, 6)

        # Forward multi-session returns (1d, 3d, 5d)
        n_bars = len(sorted_bars)
        fwd_1d: Optional[float] = None
        fwd_3d: Optional[float] = None
        fwd_5d: Optional[float] = None

        if target_idx + 1 < n_bars:
            next_close = sorted_bars[target_idx + 1].close
            if curr_close > 0.0:
                fwd_1d = round((next_close / curr_close) - 1.0, 6)

        if target_idx + 3 < n_bars:
            c3 = sorted_bars[target_idx + 3].close
            if curr_close > 0.0:
                fwd_3d = round((c3 / curr_close) - 1.0, 6)

        if target_idx + 5 < n_bars:
            c5 = sorted_bars[target_idx + 5].close
            if curr_close > 0.0:
                fwd_5d = round((c5 / curr_close) - 1.0, 6)

        # Pre-event realized volatility (5 sessions prior: [target_idx - 5 ... target_idx - 1])
        pre_vol_5d: Optional[float] = None
        if target_idx >= 5:
            pre_returns: List[float] = []
            valid_pre = True
            for k in range(target_idx - 4, target_idx + 1):
                p0 = sorted_bars[k - 1].close
                p1 = sorted_bars[k].close
                if p0 <= 0.0 or math.isnan(p0) or math.isnan(p1):
                    valid_pre = False
                    break
                pre_returns.append((p1 / p0) - 1.0)
            if valid_pre and len(pre_returns) >= 2:
                raw_stdev = calculate_standard_deviation(pre_returns, ddof=1)
                pre_vol_5d = round(raw_stdev, 6) if raw_stdev is not None else None

        # Post-event realized volatility (5 sessions after: [target_idx + 1 ... target_idx + 5])
        post_vol_5d: Optional[float] = None
        if target_idx + 5 < n_bars:
            post_returns: List[float] = []
            valid_post = True
            for k in range(target_idx + 1, target_idx + 6):
                p0 = sorted_bars[k - 1].close
                p1 = sorted_bars[k].close
                if p0 <= 0.0 or math.isnan(p0) or math.isnan(p1):
                    valid_post = False
                    break
                post_returns.append((p1 / p0) - 1.0)
            if valid_post and len(post_returns) >= 2:
                raw_stdev = calculate_standard_deviation(post_returns, ddof=1)
                post_vol_5d = round(raw_stdev, 6) if raw_stdev is not None else None

        # Benchmark excess return
        bench_fwd_1d: Optional[float] = None
        rel_fwd_1d: Optional[float] = None
        if benchmark_bars:
            sorted_bench = sorted(benchmark_bars, key=lambda b: b.timestamp)
            b_idx: Optional[int] = None
            for idx, b in enumerate(sorted_bench):
                if self._resolve_bar_date(b) == target_date:
                    b_idx = idx
                    break

            if b_idx is not None and b_idx + 1 < len(sorted_bench):
                b0 = sorted_bench[b_idx].close
                b1 = sorted_bench[b_idx + 1].close
                if b0 > 0.0:
                    bench_fwd_1d = round((b1 / b0) - 1.0, 6)
                    if fwd_1d is not None:
                        rel_fwd_1d = round(fwd_1d - bench_fwd_1d, 6)

        # Status and exclusion details
        status = "MEASURED"
        exclusion_reasons: List[str] = []

        if fwd_1d is None:
            status = "INCOMPLETE_OUTCOME_WINDOW"
            exclusion_reasons.append(
                f"T+1 outcome session has not occurred (latest available session is {self._resolve_bar_date(sorted_bars[-1])})."
            )

        if pre_vol_5d is None and target_idx < 5:
            exclusion_reasons.append(f"Insufficient pre-event history ({target_idx} bars available, 5 required).")

        if post_vol_5d is None and target_idx + 5 >= n_bars:
            exclusion_reasons.append(f"Incomplete post-event 5d volatility window ({n_bars - 1 - target_idx} bars available, 5 required).")

        reason_str = " | ".join(exclusion_reasons) if exclusion_reasons else None

        return EventImpactMeasurement(
            event_id=aligned_event.event_id,
            symbol=symbol,
            session_date=target_date,
            session_phase=phase,
            session_open=curr_open,
            session_close=curr_close,
            prior_close=prior_close,
            same_day_return=same_day_ret,
            forward_return_1d=fwd_1d,
            forward_return_3d=fwd_3d,
            forward_return_5d=fwd_5d,
            pre_event_volatility_5d=pre_vol_5d,
            post_event_volatility_5d=post_vol_5d,
            benchmark_symbol=benchmark_symbol,
            benchmark_forward_return_1d=bench_fwd_1d,
            relative_forward_return_1d=rel_fwd_1d,
            status=status,
            exclusion_reason=reason_str,
        )

    def analyze_events(
        self,
        aligned_events: Sequence[AlignedEventSession],
        market_bars: Sequence[MarketOHLCV],
        benchmark_bars: Optional[Sequence[MarketOHLCV]] = None,
        benchmark_symbol: Optional[str] = None,
        deduplicate: bool = True,
    ) -> Tuple[List[EventImpactMeasurement], AggregateImpactSummary]:
        """Analyze a collection of aligned events, computing individual measurements and aggregate metrics.

        Args:
            aligned_events: Sequence of aligned event sessions.
            market_bars: Sequence of historical bars for the measured asset.
            benchmark_bars: Optional sequence of benchmark bars.
            benchmark_symbol: Optional benchmark ticker.
            deduplicate: If True, filters input events by unique event_id to prevent double-counting.

        Returns:
            Tuple of (list_of_measurements, AggregateImpactSummary).
        """
        # Deduplication guard: eliminate duplicate event IDs to prevent multi-counting
        events_to_process: List[AlignedEventSession] = []
        seen_ids: Set[str] = set()

        for a_ev in aligned_events:
            if deduplicate:
                if a_ev.event_id in seen_ids:
                    continue
                seen_ids.add(a_ev.event_id)
            events_to_process.append(a_ev)

        measurements = [
            self.measure_event_impact(
                aligned_event=e,
                market_bars=market_bars,
                benchmark_bars=benchmark_bars,
                benchmark_symbol=benchmark_symbol,
            )
            for e in events_to_process
        ]

        # Aggregate statistics
        total = len(aligned_events)
        eligible = len(events_to_process)
        symbol = market_bars[0].symbol if market_bars else "UNKNOWN"

        valid_1d_returns = [m.forward_return_1d for m in measurements if m.forward_return_1d is not None]
        valid_5d_returns = [m.forward_return_5d for m in measurements if m.forward_return_5d is not None]
        valid_pre_vols = [m.pre_event_volatility_5d for m in measurements if m.pre_event_volatility_5d is not None]
        valid_post_vols = [m.post_event_volatility_5d for m in measurements if m.post_event_volatility_5d is not None]

        mean_1d = round(statistics.mean(valid_1d_returns), 6) if valid_1d_returns else None
        median_1d = round(statistics.median(valid_1d_returns), 6) if valid_1d_returns else None
        std_1d = round(statistics.stdev(valid_1d_returns), 6) if len(valid_1d_returns) >= 2 else None

        mean_5d = round(statistics.mean(valid_5d_returns), 6) if valid_5d_returns else None
        mean_pre_vol = round(statistics.mean(valid_pre_vols), 6) if valid_pre_vols else None
        mean_post_vol = round(statistics.mean(valid_post_vols), 6) if valid_post_vols else None

        incomplete_count = sum(1 for m in measurements if m.status != "MEASURED")

        summary = AggregateImpactSummary(
            symbol=symbol,
            total_events=total,
            eligible_events=eligible,
            completed_outcomes_1d=len(valid_1d_returns),
            mean_return_1d=mean_1d,
            median_return_1d=median_1d,
            std_return_1d=std_1d,
            completed_outcomes_5d=len(valid_5d_returns),
            mean_return_5d=mean_5d,
            mean_pre_volatility_5d=mean_pre_vol,
            mean_post_volatility_5d=mean_post_vol,
            incomplete_or_unavailable_count=incomplete_count,
        )

        return measurements, summary
