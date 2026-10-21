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
import contextlib
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
from app.api.dependencies import get_event_providers
from app.core.config import get_settings
from app.events.providers.base import BaseEventProvider
from app.events.schemas import EventCategory, MacroEvent
from scripts.staging_soak_test import (
    EndpointStats,
    classify_http_outcome,
    compute_percentile,
    create_worker_session,
)


ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


@contextlib.contextmanager
def prevent_windows_sleep():
    """Temporarily prevent Windows from entering idle sleep during test execution.

    Uses thread-scoped kernel32.SetThreadExecutionState. Safe, temporary, and
    automatically releases upon process exit or context exit without altering
    persistent system power settings.
    """
    enabled = False
    kernel32 = None
    if sys.platform == "win32":
        try:
            import ctypes
            windll = getattr(ctypes, "windll", None)
            if windll is not None and hasattr(windll, "kernel32"):
                kernel32 = windll.kernel32
                kernel32.SetThreadExecutionState.restype = ctypes.c_uint32
                kernel32.SetThreadExecutionState.argtypes = [ctypes.c_uint32]

                prev_state = kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
                if prev_state != 0:
                    confirmed_state = kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
                    if confirmed_state != 0 and (confirmed_state & ES_SYSTEM_REQUIRED):
                        enabled = True
                    else:
                        kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception:
            enabled = False
    try:
        yield enabled
    finally:
        if enabled and kernel32 is not None:
            try:
                kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            except Exception:
                pass


class OfflineStagingEventProvider(BaseEventProvider):
    """Isolated local event provider ensuring zero external network calls during staging."""

    @property
    def name(self) -> str:
        return "offline_staging_provider"

    def fetch_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        ingested_at: Optional[datetime] = None,
    ) -> List[MacroEvent]:
        from zoneinfo import ZoneInfo
        ist = ZoneInfo("Asia/Kolkata")
        now = ingested_at or datetime.now(timezone.utc).astimezone(ist)
        return [
            MacroEvent(
                title="Staging Isolated Monetary Policy Announcement",
                category=EventCategory.MONETARY_POLICY,
                event_type="monetary_policy_statement",
                source_org="Reserve Bank of India",
                ingested_at=now,
                published_at=now,
                announced_at=now,
                url="https://rbi.org.in/pressreleases_mock.xml",
                affected_sectors=("BANKING", "FINANCIAL_SERVICES"),
                summary="Isolated local staging event (zero external network dependency)",
                provider=self.name,
                is_verified=True,
            )
        ]


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
    load_test_completed_requests: int = 0
    load_test_successful_requests: int = 0
    load_test_failed_requests: int = 0
    http_2xx: int = 0
    http_3xx: int = 0
    http_4xx: int = 0
    http_5xx: int = 0
    timeouts: int = 0
    network_errors: int = 0
    load_test_duration_seconds: float = 0.0
    load_test_throughput_rps: float = 0.0
    status_codes: Dict[int, int] = field(default_factory=dict)
    latency_min_ms: float = 0.0
    latency_mean_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p90_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    latency_max_ms: float = 0.0
    p95_sample_sufficient: bool = False
    p99_sample_sufficient: bool = False
    endpoint_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    dev_db_sha256_before: str = ""
    dev_db_sha256_after: str = ""
    models_sha256_before: Dict[str, str] = field(default_factory=dict)
    models_sha256_after: Dict[str, str] = field(default_factory=dict)
    cpu_process_time_seconds: float = 0.0
    cpu_utilization_pct: float = 0.0
    start_time_iso: str = ""
    end_time_iso: str = ""
    monotonic_start: float = 0.0
    monotonic_end: float = 0.0
    target_duration_seconds: Optional[float] = None
    active_duration_seconds: float = 0.0
    suspension_detected: bool = False
    suspension_gap_seconds: float = 0.0
    is_interrupted: bool = False
    interruption_reason: str = ""
    sleep_prevention_active: bool = False
    errors: List[str] = field(default_factory=list)


def is_port_available(host: str, port: int) -> bool:
    """Verify that the target host:port is not already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        result = sock.connect_ex((host, port))
        return result != 0


def get_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file if it exists."""
    import hashlib
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


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
    requests_count: Optional[int] = 50,
    concurrency: int = 4,
    duration_seconds: Optional[float] = None,
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
    report.dev_db_sha256_before = get_file_sha256(project_root / "data" / "predictions.db")

    real_models_dir = project_root / "models"
    report.models_sha256_before = {
        item.name: get_file_sha256(item)
        for item in real_models_dir.glob("*")
        if item.is_file()
    }

    def _verify_unmutated() -> None:
        dev_db_size_after, dev_db_mtime_after = get_dev_db_fingerprint(project_root)
        report.dev_db_sha256_after = get_file_sha256(project_root / "data" / "predictions.db")
        if (
            dev_db_size_before == dev_db_size_after
            and dev_db_mtime_before == dev_db_mtime_after
            and report.dev_db_sha256_before == report.dev_db_sha256_after
        ):
            report.dev_db_unmutated_verified = True
        else:
            report.errors.append("CRITICAL: Development database was mutated during staging validation!")

        report.models_sha256_after = {
            item.name: get_file_sha256(item)
            for item in real_models_dir.glob("*")
            if item.is_file()
        }
        if report.models_sha256_before == report.models_sha256_after:
            report.models_unmutated_verified = True
        else:
            report.errors.append("CRITICAL: Active models directory was mutated during staging validation!")
    temp_dir_obj = None
    old_env = {}
    server = None
    server_thread = None

    sleep_mgr = prevent_windows_sleep()
    sleep_active = sleep_mgr.__enter__()
    report.sleep_prevention_active = bool(sleep_active)

    try:
        # Check port availability
        if not is_port_available(host, port):
            report.errors.append(f"Port {port} on {host} is already in use by another process.")
            return report

        report.loopback_isolation_verified = True

        # Create temporary isolated staging directory
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

        # Reload settings with staging overrides
        get_settings(reload=True)
        app = create_app()

        # Isolate event provider to prevent outbound network calls during staging
        app.dependency_overrides[get_event_providers] = lambda: [OfflineStagingEventProvider()]

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

        # 6. Execute bounded or duration-based local load test
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
        endpoint_stats: Dict[str, EndpointStats] = {}
        results_lock = threading.Lock()

        report.start_time_iso = datetime.now(timezone.utc).isoformat()
        report.monotonic_start = time.monotonic()
        report.target_duration_seconds = duration_seconds
        process_time_start = time.process_time()
        load_start = time.perf_counter()

        if duration_seconds is not None and duration_seconds > 0:
            # Continuous sustained load test for duration_seconds
            stop_time = load_start + duration_seconds
            stop_mono = report.monotonic_start + duration_seconds

            def _duration_worker(worker_id: int) -> None:
                import random
                session = create_worker_session(pool_size=10)
                try:
                    while time.perf_counter() < stop_time and time.monotonic() < stop_mono:
                        m, p, data = random.choice(request_pool)
                        ep = p.split("?")[0]
                        url = f"{base_url}{p}"
                        t0 = time.perf_counter()
                        r = None
                        try:
                            if m == "POST":
                                r = session.post(url, json=data, timeout=(2.0, 5.0))
                            else:
                                r = session.get(url, timeout=(2.0, 5.0))
                            _ = r.content
                            dur = (time.perf_counter() - t0) * 1000
                            sc = r.status_code
                            is_to = False
                        except requests.exceptions.Timeout:
                            dur = (time.perf_counter() - t0) * 1000
                            sc = 0
                            is_to = True
                        except Exception:
                            dur = (time.perf_counter() - t0) * 1000
                            sc = 0
                            is_to = False
                        finally:
                            if r is not None:
                                r.close()

                        with results_lock:
                            latencies.append(dur)
                            status_counts[sc] = status_counts.get(sc, 0) + 1

                            if ep not in endpoint_stats:
                                endpoint_stats[ep] = EndpointStats(endpoint=ep)
                            ep_stat = endpoint_stats[ep]
                            ep_stat.total_requests += 1
                            ep_stat.latencies_ms.append(dur)

                            cat = classify_http_outcome(sc, is_timeout=is_to)
                            if cat == "2xx":
                                report.http_2xx += 1
                                ep_stat.http_2xx += 1
                                report.load_test_successful_requests += 1
                            elif cat == "3xx":
                                report.http_3xx += 1
                                ep_stat.http_3xx += 1
                                report.load_test_failed_requests += 1
                            elif cat == "4xx":
                                report.http_4xx += 1
                                ep_stat.http_4xx += 1
                                report.load_test_failed_requests += 1
                            elif cat == "5xx":
                                report.http_5xx += 1
                                ep_stat.http_5xx += 1
                                report.load_test_failed_requests += 1
                            elif cat == "timeout":
                                report.timeouts += 1
                                ep_stat.timeouts += 1
                                report.load_test_failed_requests += 1
                            else:
                                report.network_errors += 1
                                ep_stat.network_errors += 1
                                report.load_test_failed_requests += 1
                finally:
                    session.close()

            threads = []
            for i in range(concurrency):
                t = threading.Thread(target=_duration_worker, args=(i,), daemon=True)
                t.start()
                threads.append(t)

            try:
                last_tick = time.monotonic()
                next_log = load_start + 30.0
                while any(t.is_alive() for t in threads):
                    now_mono = time.monotonic()
                    tick_delta = now_mono - last_tick
                    # 1.0s heartbeat; tick_delta > 4.0s indicates host OS suspension/sleep gap
                    if tick_delta > 4.0:
                        report.suspension_detected = True
                        report.suspension_gap_seconds += round(tick_delta - 1.0, 3)
                    last_tick = now_mono

                    now = time.perf_counter()
                    if now >= next_log:
                        elapsed = now - load_start
                        with results_lock:
                            req_count = len(latencies)
                            rate = req_count / max(elapsed - report.suspension_gap_seconds, 0.001)
                        print(
                            f"  [SOAK PROGRESS] Elapsed: {elapsed:6.1f}s / {duration_seconds:.0f}s | "
                            f"Requests: {req_count:6d} | Rate: {rate:6.1f} req/s | "
                            f"2xx: {report.http_2xx:6d} | Errors: {report.load_test_failed_requests}"
                        )
                        next_log += 30.0
                    time.sleep(1.0)
            finally:
                for t in threads:
                    t.join(timeout=5.0)
                    if t.is_alive():
                        report.errors.append(f"Worker thread {t.name} did not terminate within join timeout.")

            report.load_test_total_requests = len(latencies)
        else:
            # Fixed requests_count load test
            actual_count = requests_count or 50
            thread_sessions: Dict[int, requests.Session] = {}
            thread_sessions_lock = threading.Lock()

            def _get_worker_session() -> requests.Session:
                tid = threading.get_ident()
                with thread_sessions_lock:
                    if tid not in thread_sessions:
                        thread_sessions[tid] = create_worker_session(pool_size=10)
                    return thread_sessions[tid]

            def _worker(_: int) -> Tuple[str, int, float, bool]:
                import random
                m, p, data = random.choice(request_pool)
                ep = p.split("?")[0]
                url = f"{base_url}{p}"
                session = _get_worker_session()
                t0 = time.perf_counter()
                r = None
                try:
                    if m == "POST":
                        r = session.post(url, json=data, timeout=(2.0, 5.0))
                    else:
                        r = session.get(url, timeout=(2.0, 5.0))
                    _ = r.content
                    dur = (time.perf_counter() - t0) * 1000
                    return (ep, r.status_code, dur, False)
                except requests.exceptions.Timeout:
                    dur = (time.perf_counter() - t0) * 1000
                    return (ep, 0, dur, True)
                except Exception:
                    dur = (time.perf_counter() - t0) * 1000
                    return (ep, 0, dur, False)
                finally:
                    if r is not None:
                        r.close()

            try:
                with ThreadPoolExecutor(max_workers=concurrency) as pool:
                    futures = [pool.submit(_worker, i) for i in range(actual_count)]
                    for fut in as_completed(futures):
                        ep, sc, dur, is_timeout = fut.result()
                        latencies.append(dur)
                        status_counts[sc] = status_counts.get(sc, 0) + 1

                        if ep not in endpoint_stats:
                            endpoint_stats[ep] = EndpointStats(endpoint=ep)
                        ep_stat = endpoint_stats[ep]
                        ep_stat.total_requests += 1
                        ep_stat.latencies_ms.append(dur)

                        cat = classify_http_outcome(sc, is_timeout=is_timeout)
                        if cat == "2xx":
                            report.http_2xx += 1
                            ep_stat.http_2xx += 1
                            report.load_test_successful_requests += 1
                        elif cat == "3xx":
                            report.http_3xx += 1
                            ep_stat.http_3xx += 1
                            report.load_test_failed_requests += 1
                        elif cat == "4xx":
                            report.http_4xx += 1
                            ep_stat.http_4xx += 1
                            report.load_test_failed_requests += 1
                        elif cat == "5xx":
                            report.http_5xx += 1
                            ep_stat.http_5xx += 1
                            report.load_test_failed_requests += 1
                        elif cat == "timeout":
                            report.timeouts += 1
                            ep_stat.timeouts += 1
                            report.load_test_failed_requests += 1
                        else:
                            report.network_errors += 1
                            ep_stat.network_errors += 1
                            report.load_test_failed_requests += 1
            finally:
                with thread_sessions_lock:
                    for s in thread_sessions.values():
                        s.close()
                    thread_sessions.clear()

            report.load_test_total_requests = actual_count

        report.monotonic_end = time.monotonic()
        report.end_time_iso = datetime.now(timezone.utc).isoformat()
        total_elapsed = report.monotonic_end - report.monotonic_start
        report.load_test_duration_seconds = round(total_elapsed, 3)
        active_duration = max(total_elapsed - report.suspension_gap_seconds, 0.001)
        report.active_duration_seconds = round(active_duration, 3)

        if report.suspension_detected:
            report.is_interrupted = True
            report.interruption_reason = (
                f"Host suspension detected: {report.suspension_gap_seconds:.1f}s sleep gap"
            )
            report.errors.append(f"INCOMPLETE RUN: {report.interruption_reason}")
        elif duration_seconds is not None:
            if total_elapsed < (duration_seconds - 5.0):
                report.is_interrupted = True
                report.interruption_reason = (
                    f"Run terminated early: measured {total_elapsed:.1f}s vs target {duration_seconds:.0f}s"
                )
                report.errors.append(f"INCOMPLETE RUN: {report.interruption_reason}")

        cpu_process_elapsed = time.process_time() - process_time_start
        report.cpu_process_time_seconds = round(cpu_process_elapsed, 2)
        report.cpu_utilization_pct = round(
            (cpu_process_elapsed / max(active_duration, 0.001)) * 100, 1
        )

        report.load_test_completed_requests = len(latencies)
        report.load_test_throughput_rps = round(
            report.load_test_completed_requests / max(active_duration, 0.001), 2
        )
        report.status_codes = status_counts

        if latencies:
            sorted_lat = sorted(latencies)
            n = len(sorted_lat)
            report.latency_min_ms = round(sorted_lat[0], 2)
            report.latency_max_ms = round(sorted_lat[-1], 2)
            report.latency_mean_ms = round(sum(sorted_lat) / n, 2)
            report.latency_p50_ms = compute_percentile(sorted_lat, 50.0)
            report.latency_p90_ms = compute_percentile(sorted_lat, 90.0)
            report.latency_p95_ms = compute_percentile(sorted_lat, 95.0)
            report.latency_p99_ms = compute_percentile(sorted_lat, 99.0)
            report.p95_sample_sufficient = (n >= 20)
            report.p99_sample_sufficient = (n >= 100)

        for ep_name, ep_stat in endpoint_stats.items():
            ep_stat.compute()
            report.endpoint_metrics[ep_name] = {
                "total_requests": ep_stat.total_requests,
                "http_2xx": ep_stat.http_2xx,
                "errors": ep_stat.http_4xx + ep_stat.http_5xx + ep_stat.timeouts + ep_stat.network_errors,
                "latency_min_ms": ep_stat.latency_min_ms,
                "latency_mean_ms": ep_stat.latency_mean_ms,
                "latency_p50_ms": ep_stat.latency_p50_ms,
                "latency_p90_ms": ep_stat.latency_p90_ms,
                "latency_p95_ms": ep_stat.latency_p95_ms,
                "latency_p99_ms": ep_stat.latency_p99_ms,
                "latency_max_ms": ep_stat.latency_max_ms,
                "p95_sufficient": ep_stat.p95_sample_sufficient,
                "p99_sufficient": ep_stat.p99_sample_sufficient,
            }

    finally:
        try:
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

            # Verify Development Database and Active Models were NOT mutated
            _verify_unmutated()
        finally:
            sleep_mgr.__exit__(*sys.exc_info())

    return report


def main() -> int:
    """CLI entry point for local staging validation runner."""
    parser = argparse.ArgumentParser(description="Run local isolated staging environment and validation.")
    parser.add_argument("--port", type=int, default=8899, help="Local staging port (default: 8899)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (must be 127.0.0.1)")
    parser.add_argument("--requests", type=int, default=50, help="Load test request count (default: 50)")
    parser.add_argument("--concurrency", type=int, default=4, help="Load test concurrency (default: 4)")
    parser.add_argument("--duration", type=float, default=None, help="Sustained load test duration in seconds (e.g. 600)")

    args = parser.parse_args()

    print("=" * 75)
    print("LOCAL STAGING ENVIRONMENT VALIDATION (DAY 45)")
    print("=" * 75)
    print(f"Target Host:       {args.host}")
    print(f"Target Port:       {args.port}")
    print(f"Binding Policy:    Strict loopback only (127.0.0.1)")
    if args.duration:
        print(f"Load Profile:      Sustained load for {args.duration:.1f}s @ concurrency {args.concurrency}")
    else:
        print(f"Load Profile:      {args.requests} requests @ concurrency {args.concurrency}")
    print(f"Environment Mode:  production (APP_DEBUG=false, explicit CORS)")
    print("=" * 75)

    report = run_local_staging_validation(
        host=args.host,
        port=args.port,
        requests_count=args.requests,
        concurrency=args.concurrency,
        duration_seconds=args.duration,
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

    print("\n[DATA INTEGRITY FINGERPRINTS]")
    print(f"  Dev DB SHA-256 Before: {report.dev_db_sha256_before}")
    print(f"  Dev DB SHA-256 After:  {report.dev_db_sha256_after}")
    print(f"  Dev DB Match Verified: {report.dev_db_unmutated_verified}")
    print(f"  Models Tracked:        {len(report.models_sha256_before)} items")
    print(f"  Models Match Verified: {report.models_unmutated_verified}")

    print("\n[TIMING & RUN HEALTH]")
    print(f"  Wall-Clock Start:       {report.start_time_iso}")
    print(f"  Wall-Clock End:         {report.end_time_iso}")
    if report.target_duration_seconds:
        print(f"  Target Duration:        {report.target_duration_seconds:.1f} s")
    print(f"  Monotonic Elapsed:      {report.load_test_duration_seconds:.2f} s")
    print(f"  Active Duration:        {report.active_duration_seconds:.2f} s")
    print(f"  Suspension Gap:         {report.suspension_gap_seconds:.2f} s ({'DETECTED' if report.suspension_detected else 'None detected'})")
    print(f"  Sleep Prevention:       {'ACTIVE (Win32 ES_CONTINUOUS|ES_SYSTEM_REQUIRED)' if report.sleep_prevention_active else 'INACTIVE / Non-Windows or API call failed'}")
    print(f"  Run Integrity:          {'INCOMPLETE / INTERRUPTED' if report.is_interrupted else 'COMPLETE (Uninterrupted)'}")
    if report.is_interrupted:
        print(f"  Interruption Reason:    {report.interruption_reason}")

    print("\n[LOCAL LOAD TEST METRICS]")
    print(f"  Duration:         {report.load_test_duration_seconds:.2f} s")
    print(f"  Throughput:       {report.load_test_throughput_rps:.2f} req/s")
    print(f"  Requests Total:   {report.load_test_total_requests} (completed: {report.load_test_completed_requests})")
    print(f"  Successful (2xx): {report.http_2xx} ({report.http_2xx/max(report.load_test_completed_requests, 1)*100:.2f}%)")
    print(f"  Failed / Errors:  {report.load_test_failed_requests}")
    print(f"    - HTTP 4xx:     {report.http_4xx}")
    print(f"    - HTTP 5xx:     {report.http_5xx}")
    print(f"    - Timeouts:     {report.timeouts}")
    print(f"    - Net Errors:   {report.network_errors}")
    print(f"  Status Codes:     {report.status_codes}")
    print(f"  CPU Process Time: {report.cpu_process_time_seconds:.2f} s ({report.cpu_utilization_pct:.1f}% load-thread process utilization)")

    print("\n[LATENCY DISTRIBUTION (ms)]")
    print(f"  Min:   {report.latency_min_ms:8.2f} ms")
    print(f"  Mean:  {report.latency_mean_ms:8.2f} ms")
    print(f"  p50:   {report.latency_p50_ms:8.2f} ms")
    print(f"  p90:   {report.latency_p90_ms:8.2f} ms")
    p95_note = "" if report.p95_sample_sufficient else " (sample < 20)"
    p99_note = "" if report.p99_sample_sufficient else " (sample < 100)"
    print(f"  p95:   {report.latency_p95_ms:8.2f} ms{p95_note}")
    print(f"  p99:   {report.latency_p99_ms:8.2f} ms{p99_note}")
    print(f"  Max:   {report.latency_max_ms:8.2f} ms")

    if report.endpoint_metrics:
        print("\n[ENDPOINT LATENCY BREAKDOWN]")
        print(f"  {'Endpoint':<22} {'Reqs':>6} {'2xx':>6} {'Errors':>8} {'p50(ms)':>10} {'p95(ms)':>10} {'Max(ms)':>10}")
        print("  " + "-" * 72)
        for ep_name, ep in sorted(report.endpoint_metrics.items()):
            print(
                f"  {ep_name:<22} {ep['total_requests']:>6d} {ep['http_2xx']:>6d} {ep['errors']:>8d} "
                f"{ep['latency_p50_ms']:>10.2f} {ep['latency_p95_ms']:>10.2f} {ep['latency_max_ms']:>10.2f}"
            )

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
        and not report.is_interrupted
        and not report.suspension_detected
        and report.load_test_failed_requests == 0
    )
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
