"""Unit and regression tests for NIFTY 50 Combined Acceptance & Validation Audit."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "research" / "datasets" / "nifty50" / "combined_acceptance_audit"
FROZEN_DIR = ROOT / "research" / "datasets" / "nifty50"

ALLOWED_EVIDENCE_STATUSES = {
    "VERIFIED",
    "CORROBORATED",
    "PARTIALLY_VERIFIED",
    "UNVERIFIED",
    "CONTRADICTED",
    "NOT_APPLICABLE",
    "NOT_TESTED",
}

FORBIDDEN_EVIDENCE_STATUSES = {"PASS", "FAIL", "CONFIRMED", "PENDING", "UNKNOWN"}


def test_all_nine_audit_artifacts_exist():
    """Verify that all nine required audit artifacts exist and are non-empty."""
    required_files = [
        "COMBINED_AUDIT_REPORT.md",
        "snapshot_equivalence_review.json",
        "unresolved_dates_assessment.csv",
        "nse_only_observations_policy.csv",
        "session_inclusion_policy.md",
        "leakage_audit_checklist.json",
        "baseline_validation_specification.md",
        "readiness_decision.json",
        "FINAL_READINESS_REPORT.md",
    ]
    for fn in required_files:
        p = AUDIT_DIR / fn
        assert p.exists(), f"Missing artifact: {fn}"
        assert p.stat().st_size > 0, f"Empty artifact: {fn}"


def test_standard_evidence_status_vocabulary_in_json():
    """Verify only standard evidence status vocabulary is used in JSON reports."""
    # 1. snapshot_equivalence_review.json
    with (AUDIT_DIR / "snapshot_equivalence_review.json").open(encoding="utf-8") as f:
        data = json.load(f)
    assert data["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
    assert data["evidence_status"] not in FORBIDDEN_EVIDENCE_STATUSES

    # 2. leakage_audit_checklist.json
    with (AUDIT_DIR / "leakage_audit_checklist.json").open(encoding="utf-8") as f:
        leak_data = json.load(f)
    for check in leak_data["checks"]:
        assert check["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
        assert check["evidence_status"] not in FORBIDDEN_EVIDENCE_STATUSES
        assert check["test_result"] in {"PASS", "FAIL"}

    # 3. readiness_decision.json
    with (AUDIT_DIR / "readiness_decision.json").open(encoding="utf-8") as f:
        readiness = json.load(f)
    assert readiness["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
    assert readiness["evidence_status"] not in FORBIDDEN_EVIDENCE_STATUSES
    for crit in readiness["acceptance_criteria_evaluation"].values():
        assert crit["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
        assert crit["evidence_status"] not in FORBIDDEN_EVIDENCE_STATUSES


def test_standard_evidence_status_vocabulary_in_csv():
    """Verify only standard evidence status vocabulary is used in CSV reports."""
    # 1. unresolved_dates_assessment.csv
    with (AUDIT_DIR / "unresolved_dates_assessment.csv").open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        unres_rows = list(reader)
    assert len(unres_rows) == 5
    for r in unres_rows:
        assert r["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
        assert r["evidence_status"] not in FORBIDDEN_EVIDENCE_STATUSES
        assert r["decision"] == "EXCLUDE"

    # 2. nse_only_observations_policy.csv
    with (AUDIT_DIR / "nse_only_observations_policy.csv").open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        nse_only_rows = list(reader)
    assert len(nse_only_rows) == 13
    for r in nse_only_rows:
        assert r["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
        assert r["evidence_status"] not in FORBIDDEN_EVIDENCE_STATUSES
        assert r["dual_source_decision"] == "EXCLUDE"


def test_readiness_decision_remains_partially_ready():
    """Verify final readiness classification is strictly PARTIALLY_READY."""
    with (AUDIT_DIR / "readiness_decision.json").open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["readiness_classification"] == "PARTIALLY_READY"
    assert data["promotion_decision"] == "NOT_PROMOTED"
    assert len(data["remaining_blockers"]) == 3


def test_frozen_dataset_and_hashes_unmodified():
    """Verify frozen dataset files and SHA-256 hashes remain strictly unchanged."""
    from research.datasets.nifty50.verify_dataset import run_checks

    report = run_checks()
    assert report["overall_result"] == "PASS_WITH_WARNINGS"
    assert report["checks"]["hash_integrity"]["status"] == "PASS"
    assert report["checks"]["source_record_counts"]["status"] == "PASS"
