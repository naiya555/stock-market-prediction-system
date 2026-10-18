"""Tests for Staging Soak Test and Dependency Audit Utilities.

Validates the local load/soak test execution, telemetry aggregation, and dependency audit runners.
"""

from pathlib import Path
import pytest

from scripts.run_dependency_audit import perform_dependency_audit
from scripts.staging_soak_test import (
    RequestResult,
    SoakSummary,
    run_soak_simulation,
)


def test_dependency_audit_runner():
    """Verify perform_dependency_audit returns structured report."""
    report = perform_dependency_audit()
    assert isinstance(report, dict)
    assert "pip_check_passed" in report
    assert "pip_audit_available" in report
    assert "status" in report
    assert report["pip_check_passed"] is True


def test_soak_summary_percentile_computation():
    """Verify SoakSummary computes percentiles, means, and throughput correctly."""
    summary = SoakSummary(
        total_requests=5,
        latencies_ms=[10.0, 20.0, 30.0, 40.0, 50.0],
        duration_seconds=2.0,
    )
    summary.compute()

    assert summary.throughput_rps == 2.5
    assert summary.latency_min_ms == 10.0
    assert summary.latency_max_ms == 50.0
    assert summary.latency_mean_ms == 30.0
    assert summary.latency_p50_ms == 30.0
    assert summary.latency_p95_ms == 50.0
    assert summary.latency_p99_ms == 50.0


def test_soak_summary_empty():
    """Verify SoakSummary handles empty latencies safely without exceptions."""
    summary = SoakSummary(total_requests=0, latencies_ms=[], duration_seconds=0.0)
    summary.compute()
    assert summary.throughput_rps == 0.0
    assert summary.latency_min_ms == 0.0
    assert summary.latency_max_ms == 0.0


def test_soak_simulation_bounded_inprocess():
    """Verify run_soak_simulation executes bounded requests with zero failures."""
    summary = run_soak_simulation(
        total_requests=10,
        concurrency=2,
        in_process=True,
    )
    assert summary.total_requests == 10
    assert summary.successful_requests == 10
    assert summary.failed_requests == 0
    assert len(summary.latencies_ms) == 10
    assert summary.latency_min_ms > 0.0
    assert summary.throughput_rps > 0.0
