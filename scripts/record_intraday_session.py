#!/usr/bin/env python3
"""Intraday Session Recorder CLI.

Controlled operational entry point for recording intraday candlestick sessions,
inspecting the isolated archive, and auditing empirical evaluation readiness.

Usage:
    # Check status and evaluation readiness gate
    python scripts/record_intraday_session.py --status

    # Run single-cycle recording poll
    python scripts/record_intraday_session.py --symbol BHARTIARTL --interval 5m --once

    # Run readiness audit with custom minimum candle depth
    python scripts/record_intraday_session.py --readiness-check --min-candles 75
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Optional

# Ensure repository root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.logging_config import get_logger
from app.market.intraday import IntradayInterval
from app.market.providers.yfinance_provider import YFinanceIntradayProvider
from app.market.recorder import (
    CandleProvenance,
    EvaluationReadinessStatus,
    IntradayArchiveStore,
    IntradaySessionRecorder,
    TestIntradayRecorderAdapter,
    check_evaluation_readiness,
)
from app.market.session import IST, get_market_session

logger = get_logger("record_intraday_session")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Controlled Intraday Session Recorder and Archive Audit CLI."
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BHARTIARTL",
        help="Target equity symbol (default: BHARTIARTL).",
    )
    parser.add_argument(
        "--interval",
        type=str,
        default="5m",
        help="Intraday candle interval (default: 5m).",
    )
    parser.add_argument(
        "--archive-path",
        type=str,
        default="data/intraday/intraday_archive.jsonl",
        help="Path to isolated append-only archive.",
    )
    parser.add_argument(
        "--quarantine-path",
        type=str,
        default="data/intraday/quarantined_candles.jsonl",
        help="Path to quarantine log.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute a single polling cycle and exit cleanly.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display current archive statistics and market session status.",
    )
    parser.add_argument(
        "--readiness-check",
        action="store_true",
        help="Evaluate whether the archive satisfies empirical evaluation criteria.",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["yfinance", "test"],
        default="yfinance",
        help="Market data provider to use (default: yfinance).",
    )
    parser.add_argument(
        "--min-candles",
        type=int,
        default=None,
        help="Minimum required candles for readiness evaluation (default: dynamically based on interval session expectation).",
    )
    return parser.parse_args()


def display_status(store: IntradayArchiveStore, symbol: str, interval: IntradayInterval) -> None:
    now_ist = datetime.now(IST)
    session_info = get_market_session(now_ist)
    stats = store.get_stats()

    print("=" * 65)
    print("INTRADAY RECORDER STATUS & MARKET SESSION")
    print("=" * 65)
    print(f"Current Time (IST):      {now_ist.isoformat()}")
    print(f"Market Session State:    {session_info.state.value}")
    print(f"Trading Active:          {session_info.is_trading_active}")
    print(f"Session Date:            {session_info.session_date}")
    print(f"Next Session Open:       {session_info.next_open or 'N/A'}")
    print("-" * 65)
    print("ARCHIVE STORAGE METRICS (ISOLATED):")
    print(f"Archive File:            {store.archive_path}")
    print(f"Total Stored Candles:    {stats.total_records}")
    print(f"Symbols Recorded:        {stats.symbols}")
    print(f"Intervals Recorded:      {stats.intervals}")
    print(f"Timestamp Span:          {stats.min_timestamp} -> {stats.max_timestamp}")
    print(f"Provenance Breakdown:    {json.dumps(stats.provenance_counts)}")
    print(f"Quarantined Records:     {stats.quarantined_count}")
    print("=" * 65)


def run_readiness_audit(
    store: IntradayArchiveStore,
    symbol: str,
    interval: IntradayInterval,
    min_candles: Optional[int] = None,
) -> int:
    report = check_evaluation_readiness(
        store=store,
        symbol=symbol,
        interval=interval,
        min_required_candles=min_candles,
    )

    print("=" * 65)
    print("EMPIRICAL EVALUATION READINESS AUDIT")
    print("=" * 65)
    print(f"Symbol:                  {report.symbol}")
    print(f"Interval:                {report.interval}")
    print(f"Gate Status:             {report.status.value}")
    print(f"Ready For Evaluation:    {report.is_ready_for_evaluation}")
    print(f"Summary Reason:          {report.reason}")
    print(f"Total Captured Candles:  {report.total_candles}")
    print(f"Provenance Breakdown:    {json.dumps(report.provenance_counts)}")
    print(f"Gaps Count:              {report.gaps_count}")

    if report.issues:
        print("\nIdentified Issues:")
        for issue in report.issues:
            print(f"  - {issue}")
    print("=" * 65)

    return 0 if report.is_ready_for_evaluation else 1


def main() -> int:
    args = parse_args()
    parsed_interval = IntradayInterval.from_string(args.interval)

    # Initialize isolated archive store
    store = IntradayArchiveStore(
        archive_path=args.archive_path,
        quarantine_path=args.quarantine_path,
    )

    if args.status:
        display_status(store, args.symbol, parsed_interval)
        return 0

    if args.readiness_check:
        return run_readiness_audit(store, args.symbol, parsed_interval, args.min_candles)

    # If --once is specified, run a single observation cycle
    now_ist = datetime.now(IST)
    session_info = get_market_session(now_ist)

    # Instantiate chosen provider
    if args.provider == "yfinance":
        provider = YFinanceIntradayProvider()
        print("Configured Provider:     yfinance (15m delayed exchange data disclosed; no real-time stream)")
    else:
        provider = TestIntradayRecorderAdapter(name="cli_offline_adapter")
        print("Configured Provider:     test (Deterministic test adapter; offline fixtures only)")

    recorder = IntradaySessionRecorder(
        provider=provider,
        store=store,
        symbol=args.symbol,
        interval=parsed_interval,
        provenance=CandleProvenance.PROVIDER_OBSERVATION,
    )

    print(f"Initiating single polling cycle for {args.symbol} [{parsed_interval.value}]...")
    result = recorder.record_cycle(as_of=now_ist)
    print(f"Cycle completed with result: {json.dumps(result, indent=2)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
