"""Run the read-only market data quality monitor for the four research instruments."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.market.instruments import is_index
from app.market.pipeline import run_market_data_pipeline
from app.market.providers.nifty_indices_provider import NiftyIndicesProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.market.quality.monitor import monitor_records

OUTPUT = ROOT / "research" / "data_quality_monitoring"
SYMBOLS = ["BHARTIARTL", "TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    end = datetime.now(timezone.utc)
    results = []
    errors = []
    for symbol in SYMBOLS:
        try:
            provider = NiftyIndicesProvider() if is_index(symbol) else YFinanceProvider()
            pipeline = run_market_data_pipeline(symbol, end - timedelta(days=3650), end, provider=provider)
            results.append(monitor_records(
                symbol, pipeline.raw_records, provider=provider.name, retrieved_at=end,
            ))
        except Exception as exc:
            errors.append({"instrument": symbol, "error": f"{type(exc).__name__}: {exc}"})
    findings = [finding for result in results for finding in result["findings"]]
    with (OUTPUT / "quality_findings.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["instrument", "date_or_range", "check_name", "status", "observed_value",
                  "expected_condition", "explanation", "source", "detected_at"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(findings)
    summary = {result["instrument"]: {key: value for key, value in result.items() if key != "findings"} for result in results}
    (OUTPUT / "instrument_quality_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUTPUT / "baseline_quality_report.json").write_text(json.dumps({
        "overall_status": "FAIL" if errors or any(r["overall_status"] == "FAIL" for r in results)
        else "WARNING" if any(r["overall_status"] == "WARNING" for r in results)
        else "UNVERIFIED" if any(r["overall_status"] == "UNVERIFIED" for r in results) else "PASS",
        "instrument_count": len(results), "finding_count": len(findings), "errors": errors,
        "results": results,
    }, indent=2), encoding="utf-8")
    (OUTPUT / "provider_reliability.json").write_text(json.dumps({
        result["instrument"]: {"provider": result["provider"], "retrieved_at": result["retrieved_at"],
                               "records_returned": result["record_count"], "status": "AVAILABLE"}
        for result in results
    } | {error["instrument"]: {"status": "FAILED", "error": error["error"]} for error in errors}, indent=2), encoding="utf-8")
    (OUTPUT / "monitoring_metadata.json").write_text(json.dumps({
        "generated_at": end.isoformat(), "read_only": True, "symbols": SYMBOLS,
        "stale_after_days": 3, "price_jump_warning": 0.20, "volume_ratio_warning": 10.0,
        "errors": errors, "source_data_modified": False, "database_modified": False,
    }, indent=2), encoding="utf-8")
    return 3 if errors else 2 if any(r["overall_status"] == "FAIL" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
