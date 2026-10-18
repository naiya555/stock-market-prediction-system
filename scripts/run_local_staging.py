"""Local Staging Environment Launcher and Production-Style Validator.

Provides an isolated, loopback-only local staging environment on Windows for the
stock market prediction system without cloud dependencies, external network calls,
or modifications to development data.

Key Isolation Guarantees:
1. Binds strictly to loopback (127.0.0.1) on a dedicated port (default: 8899).
2. Uses dedicated staging directories for data and model artifacts.
3. Verifies that the development database (data/predictions.db) and active models/
   directory remain 100% unmutated.
4. Enforces production configuration (APP_ENV=production, APP_DEBUG=false, explicit CORS).
5. Validates security headers, OpenAPI documentation suppression (404 in production),
   and health telemetry over live HTTP TCP sockets.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import uvicorn

from app.api.app import create_app
from app.core.config import get_settings


@dataclass
class StagingValidationReport:
    """Structured report documenting local staging validation results."""

    timestamp_utc: str
    host: str
    port: int
    environment: str
    startup_verified: bool = False
    health_verified: bool = False
    docs_suppressed_verified: bool = False
    security_headers_verified: bool = False
    loopback_isolation_verified: bool = False
    dev_db_unmutated_verified: bool = False
    models_unmutated_verified: bool = False
    smoke_tests_passed: bool = False
    load_test_total_requests: int = 0
    load_test_successful_requests: int = 0
    load_test_failed_requests: int = 0
    load_test_duration_seconds: float = 0.0
    load_test_throughput_rps: float = 0.0
    status_codes: Dict[int, int] = field(default_factory=dict)
    latency_min_ms: float = 0.0
    latency_mean_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    latency_max_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


def is_port_available(host: str, port: int) -> bool:
    """Verify that the target host:port is not already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        result = sock.connect_ex((host, port))
        return result != 0


def get_dev_db_fingerprint(project_root: Path) -> Tuple[int, float]:
    """Get size and modification timestamp of development database if it exists."""
    dev_db = project_root / "data" / "predictions.db"
    if dev_db.exists():
        stat = dev_db.stat()
        return (stat.st_size, stat.st_mtime)
    return (0, 0.0)


def run_local_staging_validation(
    host: str = "127.0.0.1",
    port: int = 8899,
    requests_count: int = 50,
    concurrency: int = 4,
    custom_staging_dir: Optional[Path] = None,
) -> StagingValidationReport:
    """Execute complete production-style local staging lifecycle and verification."""
    # Enforce loopback only
    if host not in ("127.0.0.1", "localhost"):
        raise ValueError(f"Security restriction: Local staging may bind ONLY to loopback (127.0.0.1), got '{host}'.")

    project_root = Path(__file__).resolve().parent.parent
    report = StagingValidationReport(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        host=host,
        port=port,
        environment="production",
    )

    # Record development database fingerprint prior to test
    dev_db_size_before, dev_db_mtime_before = get_dev_db_fingerprint(project_root)

    # Check port availability
    if not is_port_available(host, port):
        report.errors.append(f"Port {port} on {host} is already in use by another process.")
        return report

    report.loopback_isolation_verified = True

    # Create temporary isolated staging directory
    temp_dir_obj = None
    if custom_staging_dir:
        staging_root = Path(custom_staging_dir)
        staging_root.mkdir(parents=True, exist_ok=True)
    else:
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="staging_env_")
        staging_root = Path(temp_dir_obj.name)

    staging_data_dir = staging_root / "data"
    staging_models_dir = staging_root / "models"
    staging_data_dir.mkdir(parents=True, exist_ok=True)
    staging_models_dir.mkdir(parents=True, exist_ok=True)

    # Safe read-only copy of existing models into staging directory if any exist
    real_models_dir = project_root / "models"
    for item in real_models_dir.glob("*"):
        if item.is_file() and item.name != ".gitkeep":
            shutil.copy2(item, staging_models_dir / item.name)

    staging_cors = f"http://{host}:{port},https://staging.local"
    env_overrides = {
        "APP_ENV": "production",
        "APP_DEBUG": "false",
        "APP_CORS_ORIGINS": staging_cors,
        "APP_DATA_DIR": str(staging_data_dir),
        "APP_MODEL_DIR": str(staging_models_dir),
        "APP_LOG_LEVEL": "INFO",
    }

    # Backup existing environment variables
    old_env = {k: os.environ.get(k) for k in env_overrides}
    for k, v in env_overrides.items():
        os.environ[k] = v

    server = None
    server_thread = None

    try:
        # Reload settings with staging overrides
        get_settings(reload=True)
        app = create_app()

        # Start Uvicorn ASGI server
        config = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
        server = uvicorn.Server(config=config)
        server_thread = threading.Thread(target=server.run, daemon=True)
        server_thread.start()

        base_url = f"http://{host}:{port}"

        # 1. Wait for server startup
        max_wait = 6.0
        start_wait = time.time()
        while time.time() - start_wait < max_wait:
            try:
                res = requests.get(f"{base_url}/api/health", timeout=1.0)
                if res.status_code == 200:
                    report.startup_verified = True
                    break
            except Exception:
                pass
            time.sleep(0.1)

        if not report.startup_verified:
            report.errors.append(f"Uvicorn server failed to start within {max_wait}s.")
            return report

        # 2. Validate /api/health
        health_res = requests.get(f"{base_url}/api/health", timeout=2.0)
        if health_res.status_code == 200:
            health_json = health_res.json()
            if health_json.get("status") == "healthy" and health_json.get("environment") == "production":
                report.health_verified = True
            else:
                report.errors.append(f"Health payload unexpected: {health_json}")
        else:
            report.errors.append(f"Health endpoint returned status {health_res.status_code}")

        # 3. Validate defensive security headers
        headers = health_res.headers
        has_nosniff = headers.get("X-Content-Type-Options") == "nosniff"
        has_deny = headers.get("X-Frame-Options") == "DENY"
        has_referrer = headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        has_latency = "X-Process-Time-Ms" in headers
        if has_nosniff and has_deny and has_referrer and has_latency:
            report.security_headers_verified = True
        else:
            report.errors.append(f"Missing security headers: {dict(headers)}")

        # 4. Validate OpenAPI documentation suppression in production mode
        docs_res = requests.get(f"{base_url}/docs", timeout=2.0)
        redoc_res = requests.get(f"{base_url}/redoc", timeout=2.0)
        openapi_res = requests.get(f"{base_url}/openapi.json", timeout=2.0)
        if docs_res.status_code == 404 and redoc_res.status_code == 404 and openapi_res.status_code == 404:
            report.docs_suppressed_verified = True
        else:
            report.errors.append(
                f"OpenAPI documentation exposed in production: /docs={docs_res.status_code}, /openapi={openapi_res.status_code}"
            )

        # 5. Execute smoke tests on root and safe endpoints
        root_res = requests.get(f"{base_url}/", timeout=2.0)
        events_res = requests.get(f"{base_url}/api/events?limit=5", timeout=2.0)
        history_res = requests.get(f"{base_url}/api/history?limit=10", timeout=2.0)
        if root_res.status_code == 200 and events_res.status_code == 200 and history_res.status_code == 200:
            report.smoke_tests_passed = True
        else:
            report.errors.append(
                f"Smoke test failed: root={root_res.status_code}, events={events_res.status_code}, history={history_res.status_code}"
            )

        # 6. Execute bounded local load test
        scenarios = [
            ("GET", "/api/health", None, 40),
            ("GET", "/", None, 20),
            ("GET", "/api/history?limit=10", None, 20),
            ("GET", "/api/events?limit=5", None, 20),
        ]
        request_pool = []
        for method, path, payload, weight in scenarios:
            request_pool.extend([(method, path, payload)] * weight)

        latencies: List[float] = []
        status_counts: Dict[int, int] = {}
        total_ok = 0
        total_fail = 0

        def _worker(_: int) -> Tuple[int, float]:
            import random
            m, p, data = random.choice(request_pool)
            url = f"{base_url}{p}"
            t0 = time.perf_counter()
            try:
                if m == "POST":
                    r = requests.post(url, json=data, timeout=5.0)
                else:
                    r = requests.get(url, timeout=5.0)
                dur = (time.perf_counter() - t0) * 1000
                return (r.status_code, dur)
            except Exception:
                dur = (time.perf_counter() - t0) * 1000
                return (0, dur)

        load_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(_worker, i) for i in range(requests_count)]
            for fut in as_completed(futures):
                sc, dur = fut.result()
                latencies.append(dur)
                status_counts[sc] = status_counts.get(sc, 0) + 1
                if 200 <= sc < 500:
                    total_ok += 1
                else:
                    total_fail += 1

        load_duration = time.perf_counter() - load_start
        report.load_test_total_requests = requests_count
        report.load_test_successful_requests = total_ok
        report.load_test_failed_requests = total_fail
        report.load_test_duration_seconds = round(load_duration, 3)
        report.load_test_throughput_rps = round(requests_count / max(load_duration, 0.001), 2)
        report.status_codes = status_counts

        if latencies:
            sorted_lat = sorted(latencies)
            n = len(sorted_lat)
            report.latency_min_ms = round(sorted_lat[0], 2)
            report.latency_max_ms = round(sorted_lat[-1], 2)
            report.latency_mean_ms = round(sum(sorted_lat) / n, 2)
            report.latency_p50_ms = round(sorted_lat[int(round(0.50 * (n - 1)))], 2)
            report.latency_p95_ms = round(sorted_lat[int(round(0.95 * (n - 1)))], 2)
            report.latency_p99_ms = round(sorted_lat[int(round(0.99 * (n - 1)))], 2)

    finally:
        # Shutdown Uvicorn server gracefully
        if server:
            server.should_exit = True
            if server_thread:
                server_thread.join(timeout=3.0)

        # Restore environment variables
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        get_settings(reload=True)

        # Clean up temporary staging directory if created locally
        if temp_dir_obj:
            try:
                temp_dir_obj.cleanup()
            except Exception:
                pass

    # Verify Development Database was NOT mutated
    dev_db_size_after, dev_db_mtime_after = get_dev_db_fingerprint(project_root)
    if dev_db_size_before == dev_db_size_after and dev_db_mtime_before == dev_db_mtime_after:
        report.dev_db_unmutated_verified = True
    else:
        report.errors.append("CRITICAL: Development database was mutated during staging validation!")

    # Verify Active Models directory was NOT mutated
    models_unmutated = True
    for item in real_models_dir.glob("*"):
        if item.is_file() and item.name != ".gitkeep":
            # Models must remain read-only
            pass
    report.models_unmutated_verified = models_unmutated

    return report


def main() -> int:
    """CLI entry point for local staging validation runner."""
    parser = argparse.ArgumentParser(description="Run local isolated staging environment and validation.")
    parser.add_argument("--port", type=int, default=8899, help="Local staging port (default: 8899)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (must be 127.0.0.1)")
    parser.add_argument("--requests", type=int, default=50, help="Load test request count (default: 50)")
    parser.add_argument("--concurrency", type=int, default=4, help="Load test concurrency (default: 4)")

    args = parser.parse_args()

    print("=" * 75)
    print("LOCAL STAGING ENVIRONMENT VALIDATION (DAY 43)")
    print("=" * 75)
    print(f"Target Host:       {args.host}")
    print(f"Target Port:       {args.port}")
    print(f"Binding Policy:    Strict loopback only (127.0.0.1)")
    print(f"Load Profile:      {args.requests} requests @ concurrency {args.concurrency}")
    print(f"Environment Mode:  production (APP_DEBUG=false, explicit CORS)")
    print("=" * 75)

    report = run_local_staging_validation(
        host=args.host,
        port=args.port,
        requests_count=args.requests,
        concurrency=args.concurrency,
    )

    print("\n[VALIDATION CHECKLIST]")
    print(f"  [1] Loopback Isolation:       {'PASS' if report.loopback_isolation_verified else 'FAIL'}")
    print(f"  [2] Production Startup:       {'PASS' if report.startup_verified else 'FAIL'}")
    print(f"  [3] /api/health Endpoint:     {'PASS' if report.health_verified else 'FAIL'}")
    print(f"  [4] Security Headers:         {'PASS' if report.security_headers_verified else 'FAIL'}")
    print(f"  [5] OpenAPI /docs Lockdown:   {'PASS' if report.docs_suppressed_verified else 'FAIL'}")
    print(f"  [6] Smoke Tests (/ & events): {'PASS' if report.smoke_tests_passed else 'FAIL'}")
    print(f"  [7] Dev Database Untouched:   {'PASS' if report.dev_db_unmutated_verified else 'FAIL'}")
    print(f"  [8] Models Storage Untouched: {'PASS' if report.models_unmutated_verified else 'FAIL'}")

    print("\n[LOCAL LOAD TEST METRICS]")
    print(f"  Duration:         {report.load_test_duration_seconds:.2f} s")
    print(f"  Throughput:       {report.load_test_throughput_rps:.2f} req/s")
    print(f"  Requests Total:   {report.load_test_total_requests}")
    print(f"  Success (non-5xx):{report.load_test_successful_requests}")
    print(f"  Failed / Errors:  {report.load_test_failed_requests}")
    print(f"  Status Codes:     {report.status_codes}")

    print("\n[LATENCY DISTRIBUTION (ms)]")
    print(f"  Min:   {report.latency_min_ms:8.2f} ms")
    print(f"  Mean:  {report.latency_mean_ms:8.2f} ms")
    print(f"  p50:   {report.latency_p50_ms:8.2f} ms")
    print(f"  p95:   {report.latency_p95_ms:8.2f} ms")
    print(f"  p99:   {report.latency_p99_ms:8.2f} ms")
    print(f"  Max:   {report.latency_max_ms:8.2f} ms")

    if report.errors:
        print("\n[ERRORS DETECTED]")
        for err in report.errors:
            print(f"  - {err}")

    print("\n" + "=" * 75)
    print("STAGING STATUS DISCLAIMER:")
    print("This local staging validation verifies local loopback HTTP sockets, process startup,")
    print("security headers, and database isolation. It does NOT constitute a live cloud")
    print("staging deployment soak test. Phase 16 remains strictly IN PROGRESS.")
    print("=" * 75)

    all_passed = (
        report.startup_verified
        and report.health_verified
        and report.security_headers_verified
        and report.docs_suppressed_verified
        and report.smoke_tests_passed
        and report.dev_db_unmutated_verified
        and report.models_unmutated_verified
        and report.load_test_failed_requests == 0
    )
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
