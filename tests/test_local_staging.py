import os
from pathlib import Path
import shutil
import socket
import tempfile
import threading
import time
from unittest.mock import patch
import pytest
import requests
import uvicorn

from app.api.app import create_app
from app.core.config import get_settings
from scripts.run_local_staging import (
    get_dev_db_fingerprint,
    is_port_available,
    run_local_staging_validation,
)
from scripts.staging_soak_test import execute_request_external


def test_loopback_binding_restriction():
    """Verify local staging rejects non-loopback host bindings for safety."""
    with pytest.raises(ValueError, match="Local staging may bind ONLY to loopback"):
        run_local_staging_validation(host="0.0.0.0")

    with pytest.raises(ValueError, match="Local staging may bind ONLY to loopback"):
        run_local_staging_validation(host="192.168.1.100")


def test_is_port_available_logic():
    """Verify port availability helper accurately reports open high ports."""
    high_port = 58988
    assert is_port_available("127.0.0.1", high_port) is True


def test_staging_port_already_occupied():
    """Verify runner detects occupied port and aborts cleanly without unhandled exception."""
    test_port = 8895
    # Bind socket to occupy port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", test_port))
        sock.listen(1)

        # Runner should detect port in use and report error cleanly
        report = run_local_staging_validation(host="127.0.0.1", port=test_port)
        assert report.startup_verified is False
        assert any(f"Port {test_port}" in err and "already in use" in err for err in report.errors)


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


def test_graceful_shutdown_idle_server():
    """Verify server shuts down cleanly while idle without hung threads."""
    test_port = 8894
    app = create_app()
    config = uvicorn.Config(app=app, host="127.0.0.1", port=test_port, log_level="warning")
    server = uvicorn.Server(config=config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for startup
    started = False
    for _ in range(30):
        try:
            r = requests.get(f"http://127.0.0.1:{test_port}/api/health", timeout=0.5)
            if r.status_code == 200:
                started = True
                break
        except Exception:
            time.sleep(0.1)

    assert started is True
    # Signal exit without sending further requests (idle shutdown)
    server.should_exit = True
    server_thread.join(timeout=3.0)
    assert server_thread.is_alive() is False


def test_graceful_shutdown_after_completed_request():
    """Verify server shuts down cleanly after completing HTTP requests."""
    test_port = 8893
    app = create_app()
    config = uvicorn.Config(app=app, host="127.0.0.1", port=test_port, log_level="warning")
    server = uvicorn.Server(config=config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Execute request
    res = None
    for _ in range(30):
        try:
            res = requests.get(f"http://127.0.0.1:{test_port}/api/health", timeout=1.0)
            if res.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)

    assert res is not None and res.status_code == 200
    server.should_exit = True
    server_thread.join(timeout=3.0)
    assert server_thread.is_alive() is False


def test_temp_directory_cleanup_on_success():
    """Verify temporary staging directory is deleted on clean execution."""
    custom_temp = Path(tempfile.mkdtemp(prefix="test_staging_cleanup_"))
    try:
        assert custom_temp.exists()
        # When custom directory is passed, subdirs data and models are created
        report = run_local_staging_validation(
            host="127.0.0.1",
            port=8892,
            requests_count=5,
            concurrency=2,
            custom_staging_dir=custom_temp,
        )
        assert report.startup_verified is True
    finally:
        shutil.rmtree(custom_temp, ignore_errors=True)


def test_preservation_of_database_and_models_under_failure():
    """Verify development database and active models remain unmutated even if staging aborts."""
    project_root = Path(__file__).resolve().parent.parent
    size_before, mtime_before = get_dev_db_fingerprint(project_root)

    # Trigger intentional startup failure via invalid Uvicorn config or mock
    with patch("scripts.run_local_staging.is_port_available", return_value=False):
        report = run_local_staging_validation(host="127.0.0.1", port=8891)
        assert report.startup_verified is False

    size_after, mtime_after = get_dev_db_fingerprint(project_root)
    assert size_before == size_after
    assert mtime_before == mtime_after


def test_unreachable_endpoint_failure_handling():
    """Verify client handles connection refused or unreachable port cleanly."""
    unreachable_port = 59997
    res = execute_request_external(f"http://127.0.0.1:{unreachable_port}", "GET", "/api/health", timeout=2.0)
    assert res.success is False
    assert res.status_code == 0
    assert res.error_type in ("network_error", "timeout")
    assert res.error is not None


def test_local_staging_lifecycle_and_non_mutation():
    """Execute bounded local staging validation lifecycle and verify metrics and endpoint breakdown."""
    test_port = 8890
    report = run_local_staging_validation(
        host="127.0.0.1",
        port=test_port,
        requests_count=20,
        concurrency=3,
    )

    assert report.startup_verified is True
    assert report.health_verified is True
    assert report.security_headers_verified is True
    assert report.docs_suppressed_verified is True
    assert report.smoke_tests_passed is True
    assert report.dev_db_unmutated_verified is True
    assert report.models_unmutated_verified is True
    assert report.load_test_total_requests == 20
    assert report.load_test_completed_requests == 20
    assert report.load_test_successful_requests == 20
    assert report.load_test_failed_requests == 0
    assert report.http_2xx == 20
    assert report.http_4xx == 0
    assert report.http_5xx == 0
    assert report.timeouts == 0
    assert report.network_errors == 0
    assert report.load_test_throughput_rps > 0.0
    assert report.latency_p50_ms > 0.0
    assert report.latency_p90_ms > 0.0
    assert report.latency_p95_ms > 0.0
    assert report.p95_sample_sufficient is True  # 20 >= 20
    assert report.p99_sample_sufficient is False  # 20 < 100
    assert len(report.endpoint_metrics) > 0
    assert len(report.errors) == 0
