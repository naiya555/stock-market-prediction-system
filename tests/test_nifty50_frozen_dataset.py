"""Unit and regression tests for NIFTY 50 frozen research dataset.

Validates source snapshot preservation, precision, date alignment, tolerance,
unmatched date investigation, calendar classifications, inclusion/exclusion policy,
hash integrity, and non-mutation.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "research" / "datasets" / "nifty50"

EXPECTED_HASHES = {
    "nifty50_nse_indices_raw.csv": "fd65f0dad5fb81c2f693df8c423447067ca9240584913881b3b6cf85b04af4c1",
    "nifty50_yahoo_raw.csv": "dae00e6673cdc8f1768b8d92886798221662a8d2d30de9d97d1561194fa87e55",
    "nifty50_aligned.csv": "9fc9bdf536c3402c8fe0e9ed7f1eea4723cb19d6a841824b4480f781143bb869",
    "excluded_observations.csv": "1547ae741481d2eb4b4e7c0e418e57430ae366797325bb43ba4fcb743b94cb0c",
    "dataset_manifest.json": "95a91a3f5fbd8ed5dff70d6eb6162206b3d9042224f60b9c1d2a64cb5783d233",
}


def _calc_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_source_snapshot_preservation_and_counts():
    """Verify raw source files exist with exact expected record counts and schemas."""
    nse_path = DATASET_DIR / "nifty50_nse_indices_raw.csv"
    yf_path = DATASET_DIR / "nifty50_yahoo_raw.csv"

    assert nse_path.exists(), "NSE raw snapshot must exist"
    assert yf_path.exists(), "Yahoo raw snapshot must exist"

    with nse_path.open(encoding="utf-8") as f:
        nse_rows = list(csv.DictReader(f))
    with yf_path.open(encoding="utf-8") as f:
        yf_rows = list(csv.DictReader(f))

    assert len(nse_rows) == 2489, f"NSE raw count must be 2489 (got {len(nse_rows)})"
    assert len(yf_rows) == 2476, f"Yahoo raw count must be 2476 (got {len(yf_rows)})"

    # Check precision preservation
    assert nse_rows[0]["open"] == "8653.15"
    assert yf_rows[0]["open"] == "8653.150390625"
    assert nse_rows[0]["source"] == "nifty_indices"
    assert yf_rows[0]["source"] == "yfinance"


def test_no_duplicate_dates():
    """Verify zero duplicate dates exist in any of the raw or derived dataset files."""
    for filename in ["nifty50_nse_indices_raw.csv", "nifty50_yahoo_raw.csv", "nifty50_aligned.csv", "excluded_observations.csv"]:
        path = DATASET_DIR / filename
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        dates = [r["date"] for r in rows]
        assert len(dates) == len(set(dates)), f"Duplicates found in {filename}"


def test_date_alignment_and_tolerance():
    """Verify alignment, zero mismatches, and adherence to 0.01 / 0.0001 tolerances."""
    aligned_path = DATASET_DIR / "nifty50_aligned.csv"
    with aligned_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2489
    matched = [r for r in rows if r["reconciliation_status"] == "MATCHED"]
    nse_only = [r for r in rows if r["reconciliation_status"] == "NSE_ONLY"]
    mismatched = [r for r in rows if r["reconciliation_status"] == "MISMATCHED"]

    assert len(matched) == 2476
    assert len(nse_only) == 13
    assert len(mismatched) == 0

    # Test tolerance constraint on all matched rows
    for r in matched:
        abs_diff = float(r["absolute_difference"])
        rel_diff = float(r["relative_difference"])
        assert abs_diff <= 0.01 or rel_diff <= 0.0001, f"Tolerance exceeded on {r['date']}"


def test_missing_source_observations_investigated():
    """Verify the 13 NSE-only observations are captured with complete metadata."""
    excluded_path = DATASET_DIR / "excluded_observations.csv"
    with excluded_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 14  # 13 NSE-only + 1 calendar unverified
    nse_only_excluded = [r for r in rows if r["available_source"] == "NSE Indices" and r["missing_source"] == "Yahoo Finance"]
    assert len(nse_only_excluded) == 13

    # Check that each record has non-empty fields
    for r in nse_only_excluded:
        assert r["date"]
        assert float(r["available_close_value"]) > 0
        assert r["calendar_classification"] in {"SPECIAL_SESSION", "UNVERIFIED"}
        assert r["verification_status"] in {"VERIFIED", "UNVERIFIED"}
        assert r["inclusion_exclusion_decision"] == "EXCLUDED"
        assert len(r["reason"]) > 10


def test_unresolved_calendar_dates_explicitly_documented():
    """Verify the 5 documented unverified calendar dates are identified."""
    expected_unresolved = {"2016-11-16", "2018-01-01", "2019-01-01", "2019-02-13", "2019-03-29"}

    excluded_path = DATASET_DIR / "excluded_observations.csv"
    with excluded_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    unresolved_rows = [r for r in rows if r["verification_status"] == "UNVERIFIED"]
    unresolved_dates = {r["date"] for r in unresolved_rows}

    assert unresolved_dates == expected_unresolved, f"Mismatch in unresolved dates: {unresolved_dates} vs {expected_unresolved}"


def test_inclusion_exclusion_policy_counts():
    """Verify strict execution of inclusion/exclusion policy."""
    aligned_path = DATASET_DIR / "nifty50_aligned.csv"
    with aligned_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    status_counts = {}
    for r in rows:
        st = r["inclusion_status"]
        status_counts[st] = status_counts.get(st, 0) + 1

    assert status_counts.get("INCLUDED") == 2475
    assert status_counts.get("EXCLUDED_UNRESOLVED_CALENDAR") == 1
    assert status_counts.get("EXCLUDED_SECONDARY_UNAVAILABLE_SPECIAL_SESSION") == 9
    assert status_counts.get("EXCLUDED_SECONDARY_UNAVAILABLE_UNVERIFIED") == 4
    assert sum(status_counts.values()) == 2489


def test_hash_manifest_integrity():
    """Verify that all stored SHA-256 hashes match re-computed hashes exactly."""
    manifest_path = DATASET_DIR / "hash_manifest.json"
    with manifest_path.open(encoding="utf-8") as f:
        manifest = json.load(f)

    for filename, expected_hash in EXPECTED_HASHES.items():
        actual_hash = _calc_sha256(DATASET_DIR / filename)
        assert actual_hash == expected_hash, f"Hash mismatch for {filename}"
        assert manifest["hashes"][filename] == actual_hash


def test_verification_script_repeatability():
    """Verify verify_dataset.py runs cleanly and reports PASS_WITH_WARNINGS."""
    from research.datasets.nifty50.verify_dataset import run_checks

    report1 = run_checks()
    report2 = run_checks()

    assert report1["overall_result"] == "PASS_WITH_WARNINGS"
    assert report2["overall_result"] == "PASS_WITH_WARNINGS"
    assert report1 == report2


def test_source_data_non_mutation():
    """Verify that reading or checking does not modify source files."""
    for filename, expected_hash in EXPECTED_HASHES.items():
        assert _calc_sha256(DATASET_DIR / filename) == expected_hash
