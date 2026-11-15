"""Tests for NIFTY 50 snapshot equivalence audit between Nov 14 and Nov 15 snapshots."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "research" / "datasets" / "nifty50" / "snapshot_audit"
FROZEN_DIR = ROOT / "research" / "datasets" / "nifty50"


def test_audit_artifacts_exist():
    """Verify all four required audit artifact files exist and are non-empty."""
    required_files = [
        "SNAPSHOT_EQUIVALENCE_REPORT.md",
        "snapshot_comparison.csv",
        "date_set_differences.csv",
        "snapshot_audit.json",
    ]
    for fn in required_files:
        p = AUDIT_DIR / fn
        assert p.exists(), f"Missing audit artifact: {fn}"
        assert p.stat().st_size > 0, f"Empty audit artifact: {fn}"


def test_audit_verdict_is_partial_match():
    """Verify the audit json confirms PARTIAL_MATCH verdict and structured evaluation."""
    json_path = AUDIT_DIR / "snapshot_audit.json"
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["verdict"] == "PARTIAL_MATCH"
    assert data["verdict_criteria_evaluation"]["PARTIAL_MATCH"] is True
    assert data["verdict_criteria_evaluation"]["EXACT_MATCH"] is False
    assert data["verdict_criteria_evaluation"]["COUNT_ONLY_MATCH"] is False
    assert data["verdict_criteria_evaluation"]["NOT_VERIFIABLE"] is False


def test_record_level_price_identity_on_shared_dates():
    """Verify 0 price discrepancies across all overlapping observations."""
    json_path = AUDIT_DIR / "snapshot_audit.json"
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)

    nse_comp = data["comparison_metrics"]["nse_close_price_comparison"]
    yf_comp = data["comparison_metrics"]["yahoo_close_price_comparison"]

    assert nse_comp["overlapping_dates_count"] == 2478
    assert nse_comp["exact_matches_count"] == 2478
    assert nse_comp["differences_count"] == 0

    assert yf_comp["overlapping_dates_count"] == 2466
    assert yf_comp["exact_matches_count"] == 2466
    assert yf_comp["differences_count"] == 0


def test_date_set_differences_breakdown():
    """Verify exactly 11 date set differences are documented (10 pre-start + 2016-11-16)."""
    diff_path = AUDIT_DIR / "date_set_differences.csv"
    with diff_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 11
    pre_start = [r for r in rows if r["category"] == "NEW_DATE_IN_NOV15_PRE_START"]
    endpoint_change = [r for r in rows if r["category"] == "ENDPOINT_COVERAGE_CHANGE_20161116"]

    assert len(pre_start) == 10
    assert len(endpoint_change) == 1
    assert endpoint_change[0]["date"] == "2016-11-16"
    assert endpoint_change[0]["nov14_status"] == "MISSING_FROM_PRIMARY"
    assert endpoint_change[0]["nov15_status"] == "MATCHED"


def test_frozen_dataset_hashes_remain_unchanged():
    """Verify running audit did not mutate frozen CSV files or hash manifest."""
    from research.datasets.nifty50.verify_dataset import run_checks

    report = run_checks()
    assert report["overall_result"] == "PASS_WITH_WARNINGS"
    assert report["checks"]["hash_integrity"]["status"] == "PASS"
