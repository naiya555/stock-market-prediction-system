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
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from app.api.app import create_app


@dataclass
class RequestResult:
    """Outcome of an individual load test request."""

    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class SoakSummary:
    """Aggregated metrics across a soak test run."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    duration_seconds: float = 0.0
    throughput_rps: float = 0.0
    status_counts: Dict[int, int] = field(default_factory=dict)
    endpoint_counts: Dict[str, int] = field(default_factory=dict)
    latencies_ms: List[float] = field(default_factory=list)
    latency_min_ms: float = 0.0
    latency_max_ms: float = 0.0
    latency_mean_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0

    def compute(self) -> None:
        """Compute summary percentiles and rates."""
        if self.duration_seconds > 0:
            self.throughput_rps = round(self.total_requests / self.duration_seconds, 2)
        if self.latencies_ms:
            sorted_lat = sorted(self.latencies_ms)
            n = len(sorted_lat)
            self.latency_min_ms = round(sorted_lat[0], 2)
            self.latency_max_ms = round(sorted_lat[-1], 2)
            self.latency_mean_ms = round(sum(sorted_lat) / n, 2)
            self.latency_p50_ms = round(sorted_lat[int(round(0.50 * (n - 1)))], 2)
            self.latency_p95_ms = round(sorted_lat[int(round(0.95 * (n - 1)))], 2)
            self.latency_p99_ms = round(sorted_lat[int(round(0.99 * (n - 1)))], 2)


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
) -> RequestResult:
    """Execute a single HTTP request against an external server."""
    url = f"{base_url.rstrip('/')}{path}"
    start = time.perf_counter()
    try:
        if method == "POST":
            resp = requests.post(url, json=payload, timeout=timeout)
        else:
            resp = requests.get(url, timeout=timeout)
        duration_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=path.split("?")[0],
            method=method,
            status_code=resp.status_code,
            duration_ms=duration_ms,
            success=resp.status_code < 500,
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=path.split("?")[0],
            method=method,
            status_code=0,
            duration_ms=duration_ms,
            success=False,
            error=str(exc),
        )


def execute_request_inprocess(
    client: Any,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
) -> RequestResult:
    """Execute a single HTTP request using FastAPI TestClient in-process."""
    start = time.perf_counter()
    try:
        if method == "POST":
            resp = client.post(path, json=payload)
        else:
            resp = client.get(path)
        duration_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=path.split("?")[0],
            method=method,
            status_code=resp.status_code,
            duration_ms=duration_ms,
            success=resp.status_code < 500,
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            endpoint=path.split("?")[0],
            method=method,
            status_code=0,
            duration_ms=duration_ms,
            success=False,
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

    def _worker(_: int) -> RequestResult:
        scenario = random.choice(endpoints)
        if in_process or not base_url:
            return execute_request_inprocess(
                client=client,
                method=scenario["method"],
                path=scenario["path"],
                payload=scenario["payload"],
            )
        return execute_request_external(
            base_url=base_url,
            method=scenario["method"],
            path=scenario["path"],
            payload=scenario["payload"],
        )

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_worker, i) for i in range(total_requests)]
        for f in as_completed(futures):
            results.append(f.result())

    summary.duration_seconds = round(time.perf_counter() - start_total, 3)

    for r in results:
        summary.latencies_ms.append(r.duration_ms)
        summary.status_counts[r.status_code] = summary.status_counts.get(r.status_code, 0) + 1
        summary.endpoint_counts[r.endpoint] = summary.endpoint_counts.get(r.endpoint, 0) + 1
        if r.success:
            summary.successful_requests += 1
        else:
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
    print(f"  Total Requests:   {summary.total_requests}")
    print(f"  Success (non-5xx):{summary.successful_requests} ({summary.successful_requests/summary.total_requests*100:.1f}%)")
    print(f"  Failed / Errors:  {summary.failed_requests}")

    print("\nLATENCY DISTRIBUTION (ms):")
    print(f"  Min:  {summary.latency_min_ms:8.2f} ms")
    print(f"  Mean: {summary.latency_mean_ms:8.2f} ms")
    print(f"  p50:  {summary.latency_p50_ms:8.2f} ms")
    print(f"  p95:  {summary.latency_p95_ms:8.2f} ms")
    print(f"  p99:  {summary.latency_p99_ms:8.2f} ms")
    print(f"  Max:  {summary.latency_max_ms:8.2f} ms")

    print("\nHTTP STATUS BREAKDOWN:")
    for status_code, count in sorted(summary.status_counts.items()):
        print(f"  HTTP {status_code}: {count:5d} requests ({count/summary.total_requests*100:.1f}%)")

    print("\n" + "=" * 75)
    print("STAGING SOAK READINESS DISCLAIMER:")
    print("This simulation validates local concurrency, endpoint stability, and error isolation.")
    print("A real, multi-hour deployment soak test on a production-equivalent cloud staging cluster")
    print("under live exchange market hours remains a documented, pending Phase 16 acceptance criterion.")
    print("=" * 75)

    return 0 if summary.failed_requests == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
