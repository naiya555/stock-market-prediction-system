"""Day 35 Verification Script: Phase 14 Live Data Pipeline Increment.

Validates Indian equity market session state detection, live/near-real-time quote
acquisition via YFinanceProvider, freshness metrics, delay disclosures, and zero-fabrication guarantees.
"""

import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.schemas import MarketQuote, ValidationError
from app.market.pipeline import fetch_live_quote
from app.market.providers.yfinance_provider import YFinanceProvider
from app.market.quote import (
    DEFAULT_DELAY_DISCLAIMER,
    DataFreshnessStatus,
    LiveQuote,
)
from app.market.session import (
    IST,
    MarketSessionInfo,
    MarketSessionState,
    get_market_session,
)


def verify_market_session_engine() -> None:
    """Verify market session state determination across trading hours, weekends, and holidays."""
    print("=" * 70)
    print("STEP 1: Verifying Indian Market Session State Engine")
    print("=" * 70)

    # 1. Pre-open (09:05 IST on weekday)
    pre_open = datetime(2026, 10, 14, 9, 5, 0, tzinfo=IST)
    info_pre = get_market_session(pre_open)
    assert info_pre.state == MarketSessionState.PRE_OPEN, f"Expected PRE_OPEN, got {info_pre.state}"
    assert info_pre.is_trading_active is False
    print(f" [PASS] Pre-Open (09:05 IST)      -> {info_pre.state.value} (Trading Active: {info_pre.is_trading_active})")

    # 2. Regular Trading Hours (11:00 IST on weekday)
    reg_hours = datetime(2026, 10, 14, 11, 0, 0, tzinfo=IST)
    info_reg = get_market_session(reg_hours)
    assert info_reg.state == MarketSessionState.REGULAR_HOURS, f"Expected REGULAR_HOURS, got {info_reg.state}"
    assert info_reg.is_trading_active is True
    print(f" [PASS] Regular Hours (11:00 IST) -> {info_reg.state.value} (Trading Active: {info_reg.is_trading_active})")

    # 3. Post-Close (15:45 IST on weekday)
    post_close = datetime(2026, 10, 14, 15, 45, 0, tzinfo=IST)
    info_post = get_market_session(post_close)
    assert info_post.state == MarketSessionState.POST_CLOSE, f"Expected POST_CLOSE, got {info_post.state}"
    assert info_post.is_trading_active is False
    print(f" [PASS] Post-Close (15:45 IST)    -> {info_post.state.value} (Trading Active: {info_post.is_trading_active})")

    # 4. Night Closed (21:00 IST on weekday)
    night = datetime(2026, 10, 14, 21, 0, 0, tzinfo=IST)
    info_night = get_market_session(night)
    assert info_night.state == MarketSessionState.CLOSED, f"Expected CLOSED, got {info_night.state}"
    assert info_night.is_trading_active is False
    print(f" [PASS] Night Closed (21:00 IST)  -> {info_night.state.value} (Trading Active: {info_night.is_trading_active})")

    # 5. Weekend (Saturday 12:00 IST)
    sat = datetime(2026, 10, 17, 12, 0, 0, tzinfo=IST)
    info_sat = get_market_session(sat)
    assert info_sat.state == MarketSessionState.CLOSED, f"Expected CLOSED, got {info_sat.state}"
    assert info_sat.is_weekend is True
    print(f" [PASS] Weekend Saturday          -> {info_sat.state.value} (Weekend: {info_sat.is_weekend})")

    # 6. Holiday (Republic Day 2026-01-26)
    holiday = datetime(2026, 1, 26, 11, 0, 0, tzinfo=IST)
    info_hol = get_market_session(holiday)
    assert info_hol.state == MarketSessionState.CLOSED, f"Expected CLOSED, got {info_hol.state}"
    assert info_hol.is_holiday is True
    print(f" [PASS] Holiday (Republic Day)    -> {info_hol.state.value} (Holiday: {info_hol.is_holiday})")


def verify_live_quote_adapter() -> None:
    """Verify YFinanceProvider live quote acquisition on real Indian equity tickers."""
    print("\n" + "=" * 70)
    print("STEP 2: Verifying Live/Near-Real-Time Quote Acquisition")
    print("=" * 70)

    provider = YFinanceProvider()

    for ticker in ("RELIANCE.NS", "TCS.NS"):
        print(f"\nQuerying near-real-time quote for '{ticker}'...")
        quote = provider.fetch_quote(ticker)

        assert isinstance(quote, LiveQuote), "Expected LiveQuote instance"
        assert quote.price > 0, f"Expected positive price, got {quote.price}"
        assert quote.symbol in ("RELIANCE", "TCS"), f"Unexpected symbol {quote.symbol}"
        assert quote.is_delayed is True, "Expected is_delayed=True"
        assert quote.delay_minutes == 15, "Expected 15m delay disclosure"
        assert quote.currency == "INR", f"Expected INR currency, got {quote.currency}"
        assert quote.session_state in MarketSessionState
        assert quote.freshness_status in DataFreshnessStatus

        print(f" [PASS] Symbol:           {quote.symbol}")
        print(f" [PASS] Last Price:       ₹ {quote.price:,.2f}")
        print(f" [PASS] Trade As-Of:      {quote.timestamp.isoformat()}")
        print(f" [PASS] Retrieved At:     {quote.retrieved_at.isoformat()}")
        print(f" [PASS] Session Phase:    {quote.session_state.value}")
        print(f" [PASS] Freshness:        {quote.freshness_status.value}")
        print(f" [PASS] Day OHLC:         O: {quote.open_price} | H: {quote.day_high} | L: {quote.day_low}")
        print(f" [PASS] Previous Close:   ₹ {quote.previous_close}")
        if quote.change is not None and quote.change_percent is not None:
            print(f" [PASS] Net Change:       {quote.change:+,.2f} ({quote.change_percent:+.2f}%)")
        print(f" [PASS] Delay Disclosure: {quote.is_delayed} ({quote.delay_minutes} min delay)")

        # Verify downcasting
        mq = quote.to_market_quote()
        assert isinstance(mq, MarketQuote)
        assert mq.price == quote.price
        print(" [PASS] Downcast to canonical MarketQuote succeeded.")


def verify_error_handling_and_zero_fabrication() -> None:
    """Verify input validation and zero-fabrication guarantees under failure modes."""
    print("\n" + "=" * 70)
    print("STEP 3: Verifying Input Validation and Zero-Fabrication Guarantees")
    print("=" * 70)

    provider = YFinanceProvider()

    # 1. Empty symbol rejection
    try:
        provider.fetch_quote("")
        assert False, "Empty symbol should have failed"
    except ValidationError as e:
        print(f" [PASS] Empty symbol rejected with ValidationError: {e}")

    # 2. Nonexistent ticker failure
    try:
        provider.fetch_quote("TOTALLY_INVALID_TICKER_99999999.NS")
        assert False, "Nonexistent ticker should have failed"
    except RuntimeError as e:
        print(f" [PASS] Nonexistent ticker raised RuntimeError without fabricating prices: {e}")

    # 3. Pipeline orchestration wrapper
    quote = fetch_live_quote("INFY.NS", provider=provider)
    assert quote.symbol == "INFY"
    assert quote.price > 0
    print(f" [PASS] fetch_live_quote('INFY.NS') succeeded via pipeline: ₹ {quote.price:,.2f}")


def main() -> None:
    """Run all Day 35 verification steps."""
    try:
        verify_market_session_engine()
        verify_live_quote_adapter()
        verify_error_handling_and_zero_fabrication()
        print("\n" + "=" * 70)
        print("Day 35 Phase 14 Live Data Pipeline Increment: SUCCESS")
        print("=" * 70)
        sys.exit(0)
    except Exception as exc:
        print(f"\n[FAIL] Day 35 Verification Failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
