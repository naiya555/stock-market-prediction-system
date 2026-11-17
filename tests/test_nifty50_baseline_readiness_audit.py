"""Unit and regression tests for NIFTY 50 Baseline Implementation Readiness Audit."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "research" / "datasets" / "nifty50" / "baseline_readiness_audit"
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


def test_all_eight_audit_artifacts_exist():
    """Verify that all eight required audit artifacts exist and are non-empty."""
    required_files = [
        "BASELINE_READINESS_REPORT.md",
        "dataset_membership_audit.json",
        "session_continuity_audit.csv",
        "target_alignment_audit.json",
        "walk_forward_fold_audit.csv",
        "embargo_audit.json",
        "implementation_gap_analysis.md",
        "FINAL_READINESS_DECISION.json",
    ]
    for fn in required_files:
        p = AUDIT_DIR / fn
        assert p.exists(), f"Missing artifact: {fn}"
        assert p.stat().st_size > 0, f"Empty artifact: {fn}"


def test_standard_evidence_status_vocabulary_in_json():
    """Verify only standard evidence status vocabulary is used in JSON reports."""
    # 1. dataset_membership_audit.json
    with (AUDIT_DIR / "dataset_membership_audit.json").open(encoding="utf-8") as f:
        mem_data = json.load(f)
    assert mem_data["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
    assert mem_data["calendar_verification_assessment"]["evidence_status"] in ALLOWED_EVIDENCE_STATUSES

    # 2. target_alignment_audit.json
    with (AUDIT_DIR / "target_alignment_audit.json").open(encoding="utf-8") as f:
        tgt_data = json.load(f)
    assert tgt_data["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
    for item in tgt_data["verification_items"]:
        assert item["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
        assert item["evidence_status"] not in FORBIDDEN_EVIDENCE_STATUSES
        assert item["test_result"] in {"PASS", "FAIL"}

    # 3. embargo_audit.json
    with (AUDIT_DIR / "embargo_audit.json").open(encoding="utf-8") as f:
        emb_data = json.load(f)
    assert emb_data["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
    for h_audit in emb_data["horizons_audited"]:
        assert h_audit["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
        assert h_audit["evidence_status"] not in FORBIDDEN_EVIDENCE_STATUSES
        assert h_audit["test_result"] in {"PASS", "FAIL"}

    # 4. FINAL_READINESS_DECISION.json
    with (AUDIT_DIR / "FINAL_READINESS_DECISION.json").open(encoding="utf-8") as f:
        readiness = json.load(f)
    assert readiness["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
    assert readiness["evidence_status"] not in FORBIDDEN_EVIDENCE_STATUSES
    for crit in readiness["readiness_criteria_evaluation"].values():
        assert crit["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
        assert crit["evidence_status"] not in FORBIDDEN_EVIDENCE_STATUSES


def test_session_continuity_audit_csv_structure():
    """Verify session continuity audit has exact 2,475 rows and zero broken gaps."""
    with (AUDIT_DIR / "session_continuity_audit.csv").open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2475
    assert rows[0]["session_index"] == "0"
    assert rows[-1]["session_index"] == "2474"

    # Check maximum calendar day diff does not exceed 5 days
    max_gap = max(int(r["calendar_day_diff"]) for r in rows)
    assert max_gap <= 5, f"Unexpected large calendar gap: {max_gap} days"

    # Exactly 14 steps bypass an excluded date
    bypass_steps = [r for r in rows if r["continuity_classification"] == "EXCLUDED_DATE_BYPASS_STEP"]
    assert len(bypass_steps) == 14


def test_walk_forward_fold_audit_csv_structure():
    """Verify fold audit covers all 3 horizons (1, 3, 5) with 5 folds each (15 rows)."""
    with (AUDIT_DIR / "walk_forward_fold_audit.csv").open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 15
    for r in rows:
        assert r["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
        assert r["is_strictly_chronological"] == "True"
        assert r["zero_leakage_verified"] == "True"


def test_final_readiness_decision_is_partially_ready():
    """Verify final readiness classification is strictly PARTIALLY_READY."""
    with (AUDIT_DIR / "FINAL_READINESS_DECISION.json").open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["readiness_classification"] == "PARTIALLY_READY"
    assert data["promotion_decision"] == "NOT_PROMOTED"
    assert len(data["implementation_blockers_before_baseline_evaluation"]) == 4


def test_frozen_dataset_and_hashes_unmodified():
    """Verify frozen dataset files and SHA-256 hashes remain strictly unchanged."""
    from research.datasets.nifty50.verify_dataset import run_checks

    report = run_checks()
    assert report["overall_result"] == "PASS_WITH_WARNINGS"
    assert report["checks"]["hash_integrity"]["status"] == "PASS"
    assert report["checks"]["source_record_counts"]["status"] == "PASS"
