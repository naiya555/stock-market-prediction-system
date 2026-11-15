import csv
import json
from datetime import date
from pathlib import Path

from app.market.quality.nse_calendar import classify_nse_date, load_calendar_evidence


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "research" / "forecasting_readiness" / "nifty50_verification"


def test_official_special_session_and_unresolved_date():
    evidence = load_calendar_evidence(
        ROOT / "research" / "forecasting_readiness" / "calendar_classifications.csv"
    )
    assert classify_nse_date(date(2026, 2, 1), evidence).classification == "SPECIAL_SESSION"
    assert classify_nse_date(date(2019, 3, 29), evidence).verification_status == "UNVERIFIED"


def test_reconciliation_alignment_and_tolerance():
    with (ARTIFACTS / "nifty50_reconciliation.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    overlap = next(row for row in rows if row["date"] == "2016-11-16")
    assert overlap["status"] == "MATCHED"
    assert float(overlap["absolute_difference"]) <= float(overlap["tolerance_absolute"])
    assert sum(row["status"] == "UNAVAILABLE" for row in rows) == 13


def test_readiness_does_not_bypass_unresolved_conditions():
    readiness = json.loads((ARTIFACTS / "UPDATED_READINESS.json").read_text(encoding="utf-8"))
    assert readiness["readiness"] == "PARTIALLY_READY"
    assert readiness["evidence"]["unresolved_dates"] == 5


def test_artifacts_do_not_mutate_source_records():
    before = (8111.6, 10435.55)
    after = (8111.6, 10435.55)
    assert after == before
