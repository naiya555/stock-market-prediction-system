from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import requests

from scripts.run_dependency_audit import perform_dependency_audit
from scripts.staging_soak_test import (
    EndpointStats,
    RequestResult,
    SoakSummary,
    classify_http_outcome,
    compute_percentile,
    execute_request_external,
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
    """Verify SoakSummary computes percentiles, means, and throughput using linear interpolation."""
    summary = SoakSummary(
        total_requests=5,
        latencies_ms=[10.0, 20.0, 30.0, 40.0, 50.0],
        duration_seconds=2.0,
    )
    summary.compute()

    assert summary.completed_requests == 5
    assert summary.throughput_rps == 2.5
    assert summary.latency_min_ms == 10.0
    assert summary.latency_max_ms == 50.0
    assert summary.latency_mean_ms == 30.0
    assert summary.latency_p50_ms == 30.0
    assert summary.latency_p90_ms == 46.0
    assert summary.latency_p95_ms == 48.0
    assert summary.latency_p99_ms == 49.6
    assert summary.p95_sample_sufficient is False
    assert summary.p99_sample_sufficient is False


def test_compute_percentile_deterministic_known_vectors():
    """Verify compute_percentile handles empty lists, singletons, and known vectors with linear interpolation."""
    # 1. Empty list
    assert compute_percentile([], 50.0) == 0.0

    # 2. Singleton
    assert compute_percentile([42.5], 50.0) == 42.5
    assert compute_percentile([42.5], 99.0) == 42.5

    # 3. Two elements
    assert compute_percentile([10.0, 20.0], 0.0) == 10.0
    assert compute_percentile([10.0, 20.0], 50.0) == 15.0
    assert compute_percentile([10.0, 20.0], 100.0) == 20.0

    # 4. Known 10-element vector [1..10]
    vec = [float(i) for i in range(1, 11)]
    assert compute_percentile(vec, 0.0) == 1.0
    assert compute_percentile(vec, 50.0) == 5.5
    assert compute_percentile(vec, 90.0) == 9.1
    assert compute_percentile(vec, 100.0) == 10.0


def test_classify_http_outcome():
    """Verify HTTP outcome categorization matches 2xx, 3xx, 4xx, 5xx, timeout, and network errors."""
    assert classify_http_outcome(200) == "2xx"
    assert classify_http_outcome(204) == "2xx"
    assert classify_http_outcome(301) == "3xx"
    assert classify_http_outcome(400) == "4xx"
    assert classify_http_outcome(404) == "4xx"
    assert classify_http_outcome(422) == "4xx"
    assert classify_http_outcome(500) == "5xx"
    assert classify_http_outcome(503) == "5xx"
    assert classify_http_outcome(0, is_timeout=True) == "timeout"
    assert classify_http_outcome(0, is_timeout=False) == "network_error"


def test_soak_summary_partial_run_accurate_throughput():
    """Verify SoakSummary throughput divides completed requests, not scheduled total on partial runs."""
    summary = SoakSummary(
        total_requests=100,  # Scheduled 100
        latencies_ms=[10.0] * 20,  # Only 20 completed before interruption
        duration_seconds=2.0,
    )
    summary.compute()

    assert summary.completed_requests == 20
    assert summary.total_requests == 100
    assert summary.throughput_rps == 10.0  # 20 / 2.0s = 10.0 req/s, NOT 50.0 req/s


def test_soak_summary_empty():
    """Verify SoakSummary handles empty latencies safely without exceptions."""
    summary = SoakSummary(total_requests=0, latencies_ms=[], duration_seconds=0.0)
    summary.compute()
    assert summary.throughput_rps == 0.0
    assert summary.latency_min_ms == 0.0
    assert summary.latency_max_ms == 0.0


def test_execute_request_external_timeout_classification():
    """Verify execute_request_external classifies request timeouts cleanly."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout("Request timed out after 1.0s")):
        res = execute_request_external("http://127.0.0.1:8899", "GET", "/api/health", timeout=1.0)
        assert res.success is False
        assert res.status_code == 0
        assert res.is_timeout is True
        assert res.error_type == "timeout"
        assert "timed out" in (res.error or "")


def test_execute_request_external_5xx_classification():
    """Verify execute_request_external classifies HTTP 5xx responses as failures."""
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    with patch("requests.get", return_value=mock_resp):
        res = execute_request_external("http://127.0.0.1:8899", "GET", "/api/health", timeout=1.0)
        assert res.success is False
        assert res.status_code == 503
        assert res.is_timeout is False
        assert res.error_type == "5xx"


def test_soak_simulation_bounded_inprocess():
    """Verify run_soak_simulation executes bounded requests with per-endpoint tracking."""
    summary = run_soak_simulation(
        total_requests=10,
        concurrency=2,
        in_process=True,
    )
    assert summary.total_requests == 10
    assert summary.completed_requests == 10
    assert summary.successful_requests == 10
    assert summary.failed_requests == 0
    assert len(summary.latencies_ms) == 10
    assert summary.latency_min_ms > 0.0
    assert summary.throughput_rps > 0.0
    assert len(summary.endpoint_stats) > 0
    for ep_name, ep in summary.endpoint_stats.items():
        assert ep.total_requests > 0
        assert ep.http_2xx == ep.total_requests
