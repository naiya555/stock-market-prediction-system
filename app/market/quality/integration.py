"""Advisory quality-monitor integration for research and prediction workflows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from app.core.logging_config import get_logger, sanitize_log_field
from app.core.schemas import MarketOHLCV
from app.market.quality.monitor import monitor_records
from app.market.quality.nse_calendar import load_calendar_evidence

logger = get_logger(__name__)
REPORT_PATH = Path("research/data_quality_monitoring/baseline_quality_report.json")
CALENDAR_PATH = Path("research/forecasting_readiness/calendar_classifications.csv")


def run_advisory_monitor(
    symbol: str,
    records: Sequence[MarketOHLCV],
    *,
    provider: str,
    retrieved_at: datetime | None = None,
) -> dict[str, Any]:
    """Run monitoring before a workflow continues; never converts failures to PASS."""
    try:
        result = monitor_records(
            symbol,
            records,
            provider=provider,
            retrieved_at=retrieved_at,
            calendar_evidence=load_calendar_evidence(CALENDAR_PATH) if CALENDAR_PATH.exists() else None,
        )
    except Exception as exc:
        logger.error(
            "Data quality monitoring failed for %s; workflow remains advisory: %s",
            sanitize_log_field(symbol),
            exc,
        )
        return {
            "instrument": symbol,
            "overall_status": "FAILED",
            "finding_counts": {},
            "error": f"{type(exc).__name__}: {exc}",
            "report_path": str(REPORT_PATH),
        }

    logger.info(
        "Data quality status for %s: %s (PASS=%d WARNING=%d FAIL=%d UNVERIFIED=%d); report=%s",
        sanitize_log_field(symbol),
        result["overall_status"],
        result["finding_counts"]["PASS"],
        result["finding_counts"]["WARNING"],
        result["finding_counts"]["FAIL"],
        result["finding_counts"]["UNVERIFIED"],
        REPORT_PATH,
    )
    if result["overall_status"] in {"FAIL", "UNVERIFIED"}:
        logger.warning(
            "Data quality issues for %s are advisory only; prediction/research workflow was not blocked.",
            sanitize_log_field(symbol),
        )
    return {**result, "report_path": str(REPORT_PATH)}
