"""Unit and Integration Tests for Local Staging Environment Launcher (Day 43).

Validates:
1. Strict loopback binding constraint enforcement.
2. Port availability detection.
3. Development database fingerprinting and non-mutation verification.
4. Complete local staging lifecycle (startup, health, security headers, OpenAPI suppression, shutdown).
"""

from pathlib import Path
import pytest

from scripts.run_local_staging import (
    get_dev_db_fingerprint,
    is_port_available,
    run_local_staging_validation,
)


def test_loopback_binding_restriction():
    """Verify local staging rejects non-loopback host bindings for safety."""
    with pytest.raises(ValueError, match="Local staging may bind ONLY to loopback"):
        run_local_staging_validation(host="0.0.0.0")

    with pytest.raises(ValueError, match="Local staging may bind ONLY to loopback"):
        run_local_staging_validation(host="192.168.1.100")


def test_is_port_available_logic():
    """Verify port availability helper accurately reports open high ports."""
    # High unassigned port should be available
    high_port = 58988
    assert is_port_available("127.0.0.1", high_port) is True


def test_dev_db_fingerprint():
    """Verify development database fingerprinting logic."""
    project_root = Path(__file__).resolve().parent.parent
    size, mtime = get_dev_db_fingerprint(project_root)
    dev_db = project_root / "data" / "predictions.db"
    if dev_db.exists():
        assert size > 0
        assert mtime > 0.0
    else:
        assert size == 0
        assert mtime == 0.0


def test_local_staging_lifecycle_and_non_mutation():
    """Execute bounded local staging validation lifecycle and verify zero data mutation."""
    test_port = 8897
    report = run_local_staging_validation(
        host="127.0.0.1",
        port=test_port,
        requests_count=10,
        concurrency=2,
    )

    assert report.startup_verified is True
    assert report.health_verified is True
    assert report.security_headers_verified is True
    assert report.docs_suppressed_verified is True
    assert report.smoke_tests_passed is True
    assert report.dev_db_unmutated_verified is True
    assert report.models_unmutated_verified is True
    assert report.load_test_total_requests == 10
    assert report.load_test_successful_requests == 10
    assert report.load_test_failed_requests == 0
    assert report.load_test_throughput_rps > 0.0
    assert report.latency_mean_ms > 0.0
    assert len(report.errors) == 0
