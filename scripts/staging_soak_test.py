"""Staging Soak and Load Testing Simulation Script.

Executes a bounded, concurrent load test across core system endpoints (/health, /predict, /history, /events).
Supports running against an external base URL or in-process via FastAPI TestClient.

Note:
This script provides a reproducible local/staging benchmark. A real, multi-hour deployment
soak test on production-equivalent infrastructure under live market conditions remains a
pending staging acceptance criterion.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from app.api.app import create_app


def create_worker_session(pool_size: int = 10) -> requests.Session:
    """Create a thread-confined requests.Session with connection pooling and zero automatic retries."""
    session = requests.Session()
    no_retry = Retry(total=0, connect=0, read=0, redirect=0, status=0)
    adapter = HTTPAdapter(
        pool_connections=pool_size,
        pool_maxsize=pool_size,
        max_retries=no_retry,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def compute_percentile(sorted_values: List[float], percentile: float) -> float:
    """Compute percentile from sorted float list using linear interpolation.

    Equivalent to standard NumPy (method='linear') and Excel PERCENTILE.
    Handles small sample sizes gracefully.
    """
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    if n == 1:
        return round(float(sorted_values[0]), 2)
    p = max(0.0, min(100.0, float(percentile)))
    idx = (p / 100.0) * (n - 1)
    lower = int(math.floor(idx))
    upper = int(math.ceil(idx))
    weight = idx - lower
    val = sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight
    return round(float(val), 2)


def classify_http_outcome(status_code: int, is_timeout: bool = False) -> str:
    """Classify request outcome into standard categories."""
    if is_timeout:
        return "timeout"
    if status_code == 0:
        return "network_error"
    if 200 <= status_code < 300:
        return "2xx"
    if 300 <= status_code < 400:
        return "3xx"
    if 400 <= status_code < 500:
        return "4xx"
    if 500 <= status_code < 600:
        return "5xx"
    return "other"


@dataclass
class EndpointStats:
    """Metrics broken down per endpoint."""

    endpoint: str
    total_requests: int = 0
    http_2xx: int = 0
    http_3xx: int = 0
    http_4xx: int = 0
    http_5xx: int = 0
    timeouts: int = 0
    network_errors: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    latency_min_ms: float = 0.0
    latency_max_ms: float = 0.0
    latency_mean_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p90_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    p95_sample_sufficient: bool = False
    p99_sample_sufficient: bool = False

    def compute(self) -> None:
        """Compute endpoint percentiles and stability indicators."""
        if self.latencies_ms:
            sorted_lat = sorted(self.latencies_ms)
            n = len(sorted_lat)
            self.latency_min_ms = round(sorted_lat[0], 2)
            self.latency_max_ms = round(sorted_lat[-1], 2)
            self.latency_mean_ms = round(sum(sorted_lat) / n, 2)
            self.latency_p50_ms = compute_percentile(sorted_lat, 50.0)
            self.latency_p90_ms = compute_percentile(sorted_lat, 90.0)
            self.latency_p95_ms = compute_percentile(sorted_lat, 95.0)
            self.latency_p99_ms = compute_percentile(sorted_lat, 99.0)
            self.p95_sample_sufficient = (n >= 20)
            self.p99_sample_sufficient = (n >= 100)


@dataclass
class RequestResult:
    """Outcome of an individual load test request."""

    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    success: bool
    is_timeout: bool = False
    error_type: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SoakSummary:
    """Aggregated metrics across a soak test run."""

    total_requests: int = 0
    completed_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    http_2xx: int = 0
    http_3xx: int = 0
    http_4xx: int = 0
    http_5xx: int = 0
    timeouts: int = 0
    network_errors: int = 0
    duration_seconds: float = 0.0
    throughput_rps: float = 0.0
    status_counts: Dict[int, int] = field(default_factory=dict)
    endpoint_counts: Dict[str, int] = field(default_factory=dict)
    latencies_ms: List[float] = field(default_factory=list)
    latency_min_ms: float = 0.0
    latency_max_ms: float = 0.0
    latency_mean_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p90_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    p95_sample_sufficient: bool = False
    p99_sample_sufficient: bool = False
    endpoint_stats: Dict[str, EndpointStats] = field(default_factory=dict)

    def compute(self) -> None:
        """Compute summary percentiles, stability flags, and throughput."""
        self.completed_requests = len(self.latencies_ms)
        if self.duration_seconds > 0:
            self.throughput_rps = round(self.completed_requests / max(self.duration_seconds, 0.001), 2)
        if self.latencies_ms:
            sorted_lat = sorted(self.latencies_ms)
            n = len(sorted_lat)
            self.latency_min_ms = round(sorted_lat[0], 2)
            self.latency_max_ms = round(sorted_lat[-1], 2)
            self.latency_mean_ms = round(sum(sorted_lat) / n, 2)
            self.latency_p50_ms = compute_percentile(sorted_lat, 50.0)
            self.latency_p90_ms = compute_percentile(sorted_lat, 90.0)
            self.latency_p95_ms = compute_percentile(sorted_lat, 95.0)
            self.latency_p99_ms = compute_percentile(sorted_lat, 99.0)
            self.p95_sample_sufficient = (n >= 20)
            self.p99_sample_sufficient = (n >= 100)

        for stats in self.endpoint_stats.values():
            stats.compute()


TRAFFIC_SCENARIOS = [
    {"method": "GET", "path": "/api/health", "payload": None, "weight": 40},
    {"method": "GET", "path": "/", "payload": None, "weight": 15},
    {"method": "GET", "path": "/api/history?limit=10", "payload": None, "weight": 20},
    {"method": "GET", "path": "/api/events?limit=5", "payload": None, "weight": 15},
    {
        "method": "POST",
        "path": "/api/predict",
        "payload": {
            "symbol": "TCS.NS",
            "model_name": "xgboost",
            "persist": False,
            "include_live_quote": False,
        },
        "weight": 10,
    },
]


def execute_request_external(
    base_url: str,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0,
    session: Optional[requests.Session] = None,
) -> RequestResult:
    """Execute a single HTTP request against an external server."""
    url = f"{base_url.rstrip('/')}{path}"
    endpoint = path.split("?")[0]
    start = time.perf_counter()
    resp = None
    try:
        requester = session if session is not None else requests
        if method == "POST":
            resp = requester.post(url, json=payload, timeout=timeout)
        else:
            resp = requester.get(url, timeout=timeout)
        _ = resp.content
        duration_ms = (time.perf_counter() - start) * 1000
        is_success = 200 <= resp.status_code < 300
        category = classify_http_outcome(resp.status_code)
        return RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=resp.status_code,
            duration_ms=duration_ms,
            success=is_success,
            is_timeout=False,
            error_type=None if is_success else category,
        )
    except requests.exceptions.Timeout as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=0,
            duration_ms=duration_ms,
            success=False,
            is_timeout=True,
            error_type="timeout",
            error=str(exc),
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=0,
            duration_ms=duration_ms,
            success=False,
            is_timeout=False,
            error_type="network_error",
            error=str(exc),
        )
    finally:
        if resp is not None:
            resp.close()


def execute_request_inprocess(
    client: Any,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
) -> RequestResult:
    """Execute a single HTTP request using FastAPI TestClient in-process."""
    endpoint = path.split("?")[0]
    start = time.perf_counter()
    try:
        if method == "POST":
            resp = client.post(path, json=payload)
        else:
            resp = client.get(path)
        duration_ms = (time.perf_counter() - start) * 1000
        is_success = 200 <= resp.status_code < 300
        category = classify_http_outcome(resp.status_code)
        return RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=resp.status_code,
            duration_ms=duration_ms,
            success=is_success,
            is_timeout=False,
            error_type=None if is_success else category,
        )
    except requests.exceptions.Timeout as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=0,
            duration_ms=duration_ms,
            success=False,
            is_timeout=True,
            error_type="timeout",
            error=str(exc),
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=0,
            duration_ms=duration_ms,
            success=False,
            is_timeout=False,
            error_type="network_error",
            error=str(exc),
        )


def run_soak_simulation(
    total_requests: int = 100,
    concurrency: int = 5,
    base_url: Optional[str] = None,
    in_process: bool = True,
) -> SoakSummary:
    """Run a bounded soak load test either in-process or against a target base URL."""
    summary = SoakSummary(total_requests=total_requests)
    client = None
    if in_process or not base_url:
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

    # Prepare request schedule based on scenario weights
    endpoints = []
    for sc in TRAFFIC_SCENARIOS:
        endpoints.extend([sc] * sc["weight"])

    start_total = time.perf_counter()
    results: List[RequestResult] = []

    thread_sessions: Dict[int, requests.Session] = {}
    thread_sessions_lock = threading.Lock()

    def _get_thread_session() -> requests.Session:
        tid = threading.get_ident()
        with thread_sessions_lock:
            if tid not in thread_sessions:
                thread_sessions[tid] = create_worker_session(pool_size=10)
            return thread_sessions[tid]

    def _worker(_: int) -> RequestResult:
        scenario = random.choice(endpoints)
        if in_process or not base_url:
            return execute_request_inprocess(
                client=client,
                method=scenario["method"],
                path=scenario["path"],
                payload=scenario["payload"],
            )
        session = _get_thread_session()
        return execute_request_external(
            base_url=base_url,
            method=scenario["method"],
            path=scenario["path"],
            payload=scenario["payload"],
            session=session,
        )

    try:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(_worker, i) for i in range(total_requests)]
            for f in as_completed(futures):
                results.append(f.result())
    finally:
        with thread_sessions_lock:
            for s in thread_sessions.values():
                s.close()
            thread_sessions.clear()

    summary.duration_seconds = round(time.perf_counter() - start_total, 3)

    for r in results:
        summary.latencies_ms.append(r.duration_ms)
        summary.status_counts[r.status_code] = summary.status_counts.get(r.status_code, 0) + 1
        summary.endpoint_counts[r.endpoint] = summary.endpoint_counts.get(r.endpoint, 0) + 1

        if r.endpoint not in summary.endpoint_stats:
            summary.endpoint_stats[r.endpoint] = EndpointStats(endpoint=r.endpoint)
        ep = summary.endpoint_stats[r.endpoint]
        ep.total_requests += 1
        ep.latencies_ms.append(r.duration_ms)

        category = classify_http_outcome(r.status_code, is_timeout=r.is_timeout)
        if category == "2xx":
            summary.http_2xx += 1
            ep.http_2xx += 1
            summary.successful_requests += 1
        elif category == "3xx":
            summary.http_3xx += 1
            ep.http_3xx += 1
            summary.failed_requests += 1
        elif category == "4xx":
            summary.http_4xx += 1
            ep.http_4xx += 1
            summary.failed_requests += 1
        elif category == "5xx":
            summary.http_5xx += 1
            ep.http_5xx += 1
            summary.failed_requests += 1
        elif category == "timeout":
            summary.timeouts += 1
            ep.timeouts += 1
            summary.failed_requests += 1
        else:
            summary.network_errors += 1
            ep.network_errors += 1
            summary.failed_requests += 1

    summary.compute()
    return summary


def main() -> int:
    """CLI runner for staging soak test."""
    parser = argparse.ArgumentParser(description="Staging Soak Test Simulation Runner")
    parser.add_argument("--requests", type=int, default=100, help="Total requests to dispatch")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent worker threads")
    parser.add_argument("--base-url", type=str, default="", help="Target base URL (e.g. http://127.0.0.1:8000)")
    parser.add_argument("--in-process", action="store_true", default=False, help="Run in-process via TestClient")

    args = parser.parse_args()
    in_process = args.in_process or not bool(args.base_url)

    print("=" * 75)
    print("STAGING SOAK & LOAD TEST SIMULATION")
    print("=" * 75)
    print(f"Timestamp:   {datetime.now(timezone.utc).isoformat()}")
    print(f"Requests:    {args.requests}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Mode:        {'In-Process TestClient' if in_process else f'External URL ({args.base_url})'}")
    print("=" * 75)

    summary = run_soak_simulation(
        total_requests=args.requests,
        concurrency=args.concurrency,
        base_url=args.base_url,
        in_process=in_process,
    )

    print("\nRESULTS SUMMARY:")
    print(f"  Duration:         {summary.duration_seconds:.2f} s")
    print(f"  Throughput:       {summary.throughput_rps} req/s")
    print(f"  Total Requests:   {summary.total_requests} (completed: {summary.completed_requests})")
    print(f"  Successful (2xx): {summary.http_2xx} ({summary.http_2xx/max(summary.completed_requests, 1)*100:.1f}%)")
    print(f"  Non-2xx / Errors: {summary.failed_requests}")
    print(f"    - HTTP 4xx:     {summary.http_4xx}")
    print(f"    - HTTP 5xx:     {summary.http_5xx}")
    print(f"    - Timeouts:     {summary.timeouts}")
    print(f"    - Net Errors:   {summary.network_errors}")

    print("\nLATENCY DISTRIBUTION (ms):")
    print(f"  Min:  {summary.latency_min_ms:8.2f} ms")
    print(f"  Mean: {summary.latency_mean_ms:8.2f} ms")
    print(f"  p50:  {summary.latency_p50_ms:8.2f} ms")
    print(f"  p90:  {summary.latency_p90_ms:8.2f} ms")
    p95_note = "" if summary.p95_sample_sufficient else " (sample < 20)"
    p99_note = "" if summary.p99_sample_sufficient else " (sample < 100)"
    print(f"  p95:  {summary.latency_p95_ms:8.2f} ms{p95_note}")
    print(f"  p99:  {summary.latency_p99_ms:8.2f} ms{p99_note}")
    print(f"  Max:  {summary.latency_max_ms:8.2f} ms")

    if summary.endpoint_stats:
        print("\nENDPOINT LATENCY BREAKDOWN:")
        print(f"  {'Endpoint':<22} {'Reqs':>6} {'2xx':>6} {'4xx/5xx':>8} {'p50(ms)':>10} {'p95(ms)':>10} {'Max(ms)':>10}")
        print("  " + "-" * 72)
        for ep_name, ep in sorted(summary.endpoint_stats.items()):
            err_count = ep.http_4xx + ep.http_5xx + ep.timeouts + ep.network_errors
            print(
                f"  {ep_name:<22} {ep.total_requests:>6d} {ep.http_2xx:>6d} {err_count:>8d} "
                f"{ep.latency_p50_ms:>10.2f} {ep.latency_p95_ms:>10.2f} {ep.latency_max_ms:>10.2f}"
            )

    print("\nHTTP STATUS BREAKDOWN:")
    for status_code, count in sorted(summary.status_counts.items()):
        print(f"  HTTP {status_code}: {count:5d} requests ({count/max(summary.completed_requests, 1)*100:.1f}%)")

    print("\n" + "=" * 75)
    print("STAGING SOAK READINESS DISCLAIMER:")
    print("This simulation validates local concurrency, endpoint stability, and error isolation.")
    print("A real, multi-hour deployment soak test on a production-equivalent cloud staging cluster")
    print("under live exchange market hours remains a documented, pending Phase 16 acceptance criterion.")
    print("=" * 75)

    return 0 if summary.failed_requests == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
