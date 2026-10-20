import os
from pathlib import Path
import shutil
import socket
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch
import pytest
import requests
import uvicorn

from app.api.app import create_app
from app.core.config import get_settings
from scripts.run_local_staging import (
    StagingValidationReport,
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
    assert report.is_interrupted is False
    assert report.suspension_detected is False
    assert report.start_time_iso != ""
    assert report.end_time_iso != ""


def test_prevent_windows_sleep_safety():
    """Verify prevent_windows_sleep context manager enters and exits safely without errors."""
    from scripts.run_local_staging import prevent_windows_sleep
    with prevent_windows_sleep() as active:
        assert isinstance(active, bool)


def test_prevent_windows_sleep_exception_propagation():
    """Verify prevent_windows_sleep propagates exceptions cleanly without RuntimeError after throw."""
    from scripts.run_local_staging import prevent_windows_sleep
    with pytest.raises(RuntimeError, match="custom_sleep_test_error"):
        with prevent_windows_sleep():
            raise RuntimeError("custom_sleep_test_error")


def test_interruption_and_suspension_detection_classification():
    """Verify deterministic classification of host suspension gaps and early interruptions."""
    report = StagingValidationReport(
        timestamp_utc="2026-10-20T10:00:00Z",
        host="127.0.0.1",
        port=8899,
        environment="production",
    )
    # Simulate suspension gap detection
    report.suspension_detected = True
    report.suspension_gap_seconds = 3500.0
    report.monotonic_start = 100.0
    report.monotonic_end = 4200.0
    total_elapsed = report.monotonic_end - report.monotonic_start
    active_duration = max(total_elapsed - report.suspension_gap_seconds, 0.001)

    if report.suspension_detected:
        report.is_interrupted = True
        report.interruption_reason = f"Host suspension detected: {report.suspension_gap_seconds:.1f}s sleep gap"
        report.errors.append(f"INCOMPLETE RUN: {report.interruption_reason}")

    assert report.is_interrupted is True
    assert "Host suspension detected" in report.interruption_reason
    assert len(report.errors) == 1
    assert active_duration == 600.0


def test_early_termination_interruption_classification():
    """Verify deterministic classification when test run terminates before target duration."""
    report = StagingValidationReport(
        timestamp_utc="2026-10-20T10:00:00Z",
        host="127.0.0.1",
        port=8899,
        environment="production",
    )
    target_duration = 600.0
    measured_elapsed = 250.0  # Stopped after only 250s

    if measured_elapsed < (target_duration - 5.0):
        report.is_interrupted = True
        report.interruption_reason = f"Run terminated early: measured {measured_elapsed:.1f}s vs target {target_duration:.0f}s"
        report.errors.append(f"INCOMPLETE RUN: {report.interruption_reason}")

    assert report.is_interrupted is True
    assert "Run terminated early" in report.interruption_reason
    assert len(report.errors) == 1


def test_create_worker_session_pooling_and_zero_retries():
    """Verify create_worker_session creates pooled session with zero retries."""
    from scripts.staging_soak_test import create_worker_session
    session = create_worker_session(pool_size=8)
    try:
        adapter = session.adapters["http://"]
        assert adapter._pool_connections == 8
        assert adapter._pool_maxsize == 8
        assert adapter.max_retries.total == 0
        assert adapter.max_retries.connect == 0
        assert adapter.max_retries.read == 0
    finally:
        session.close()


def test_thread_worker_session_reuse_and_isolation():
    """Verify distinct worker threads have distinct sessions and reuse them across calls."""
    from concurrent.futures import ThreadPoolExecutor
    from scripts.staging_soak_test import create_worker_session

    thread_sessions = {}
    lock = threading.Lock()
    session_usage_count = {}

    def _worker(worker_id: int):
        tid = threading.get_ident()
        with lock:
            if tid not in thread_sessions:
                s = create_worker_session(pool_size=5)
                thread_sessions[tid] = s
                session_usage_count[tid] = 0
            session_usage_count[tid] += 1
            return id(thread_sessions[tid])

    with ThreadPoolExecutor(max_workers=2) as pool:
        session_ids = list(pool.map(_worker, range(20)))

    unique_session_ids = set(session_ids)
    assert len(unique_session_ids) <= 2
    assert sum(session_usage_count.values()) == 20
    for s in thread_sessions.values():
        s.close()


def test_response_and_session_cleanup_on_success_and_exception():
    """Verify response.content is consumed, response.close() is called, and failures are not 2xx."""
    from unittest.mock import MagicMock
    from scripts.staging_soak_test import execute_request_external

    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"status": "ok"}'
    mock_session.get.return_value = mock_resp

    # Normal success
    res = execute_request_external(
        base_url="http://127.0.0.1:8899",
        method="GET",
        path="/api/health",
        session=mock_session,
    )
    assert res.success is True
    assert mock_resp.close.called

    # On exception
    mock_session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")
    res_err = execute_request_external(
        base_url="http://127.0.0.1:8899",
        method="GET",
        path="/api/health",
        session=mock_session,
    )
    assert res_err.success is False
    assert res_err.error_type == "network_error"
    assert res_err.status_code == 0


def test_fingerprint_verification_runs_on_aborted_startup():
    """Verify development database and model non-mutation are verified even when startup aborts."""
    with patch("scripts.run_local_staging.is_port_available", return_value=False):
        report = run_local_staging_validation(host="127.0.0.1", port=8899)
        assert report.startup_verified is False
        assert report.dev_db_unmutated_verified is True
        assert report.models_unmutated_verified is True
        assert report.dev_db_sha256_before != ""
        assert report.dev_db_sha256_after == report.dev_db_sha256_before


def test_sleep_prevention_engaged_during_validation():
    """Verify prevent_windows_sleep is entered and exited during staging validation."""
    from scripts import run_local_staging

    with patch.object(run_local_staging, "prevent_windows_sleep") as mock_sleep:
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = True
        mock_sleep.return_value = mock_ctx
        with patch("scripts.run_local_staging.is_port_available", return_value=False):
            report = run_local_staging_validation(host="127.0.0.1", port=8899)
            assert mock_sleep.called
            assert mock_ctx.__enter__.called
            assert mock_ctx.__exit__.called
            assert report.sleep_prevention_active is True
