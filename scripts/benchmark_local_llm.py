"""Reproducible Local LLM Inference and Resource Benchmark (Day 55).

Measures wall-clock latency, response validity, system RAM, and GPU VRAM utilization
for local Ollama / Gemma 3 12B qualitative context explanation.
Runs cold-start and warm-request benchmarks sequentially using representative,
bounded point-in-time market context.
"""

from datetime import datetime, timezone
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import Settings
from app.events.schemas import EventCategory, MacroEvent, StructuredEventValue
from app.llm.client import MockLLMClient, OllamaLLMClient
from app.llm.schemas import LLMExplanationResult, LLMExplanationStatus
from app.llm.service import LLMService
from app.news.schemas import NewsArticle


def get_gpu_memory_info() -> Dict[str, Optional[float]]:
    """Query NVIDIA GPU memory via nvidia-smi if available."""
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=memory.total,memory.used,memory.free",
            "--format=csv,noheader,nounits",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
        lines = res.stdout.strip().splitlines()
        if lines:
            parts = [float(x.strip()) for x in lines[0].split(",")]
            return {
                "total_mib": parts[0],
                "used_mib": parts[1],
                "free_mib": parts[2],
            }
    except Exception:
        pass
    return {"total_mib": None, "used_mib": None, "free_mib": None}


def get_system_ram_info() -> Dict[str, Optional[float]]:
    """Query system RAM via ctypes (Windows GlobalMemoryStatusEx)."""
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            gb = 1024 ** 3
            return {
                "total_gb": round(stat.ullTotalPhys / gb, 2),
                "avail_gb": round(stat.ullAvailPhys / gb, 2),
                "used_pct": float(stat.dwMemoryLoad),
            }
    except Exception:
        pass
    return {"total_gb": None, "avail_gb": None, "used_pct": None}


def create_representative_context() -> Tuple[List[NewsArticle], List[MacroEvent]]:
    """Create representative bounded market context for BHARTIARTL."""
    now = datetime.now(timezone.utc)

    art1 = NewsArticle(
        headline="Bharti Airtel reports 14% growth in average revenue per user following tariff revisions",
        source="The Economic Times",
        published_at=now,
        ingested_at=now,
        symbols=("BHARTIARTL",),
        url="https://economictimes.indiatimes.com/industry/telecom/airtel-arpu-growth",
        summary="Bharti Airtel recorded improved ARPU of Rs 211 driven by customer upgrades and 5G adoption across urban circles.",
        provider="moneycontrol",
        article_id="art-bharti-001",
    )

    art2 = NewsArticle(
        headline="Telecom subscriber base expands in urban circles as data usage surges",
        source="Reuters India",
        published_at=now,
        ingested_at=now,
        symbols=("BHARTIARTL", "JIO"),
        url="https://reuters.com/business/india-telecom-data-expansion",
        summary="Mobile broadband data traffic climbed 18% year-on-year, supporting pricing power for leading private operators.",
        provider="reuters",
        article_id="art-bharti-002",
    )

    ev1 = MacroEvent(
        title="TRAI releases quarterly telecom performance indicators with stable churn rates",
        category=EventCategory.REGULATORY,
        event_type="regulatory_report",
        source_org="TRAI",
        ingested_at=now,
        published_at=now,
        effective_at=now,
        url="https://trai.gov.in/release/telecom-indicators-q3",
        summary="Sector regulator confirmed post-paid churn remained subdued at 1.1% while rural teledensity grew marginally.",
        affected_symbols=("BHARTIARTL",),
        structured_value=StructuredEventValue(
            metric_name="telecom_churn_rate",
            value=1.1,
            unit="pct",
        ),
        event_id="ev-trai-001",
    )

    return [art1, art2], [ev1]


def run_benchmark(num_runs: int = 3, timeout_sec: float = 60.0) -> List[Dict[str, Any]]:
    """Execute reproducible benchmark runs measuring latency and resource utilization."""
    print("=" * 80)
    print("DAY 55: EVIDENCE-GROUNDED LOCAL LLM INTEGRATION BENCHMARK")
    print("=" * 80)

    settings = Settings()
    ollama_client = OllamaLLMClient(
        base_url=settings.ollama_base_url,
        model_name=settings.ollama_model,
        timeout_seconds=timeout_sec,
    )

    is_online = False
    model_available = False
    try:
        is_online = ollama_client.is_available()
        if is_online:
            model_available = ollama_client.check_model_availability()
    except Exception as exc:
        print(f"[!] Warning checking Ollama status: {exc}")

    print(f"Ollama Endpoint:     {settings.ollama_base_url}")
    print(f"Target Model:        {settings.ollama_model}")
    print(f"Daemon Reachable:    {is_online}")
    print(f"Model Resident:      {model_available}")

    ram_initial = get_system_ram_info()
    gpu_initial = get_gpu_memory_info()
    if ram_initial["total_gb"]:
        print(f"System RAM:          {ram_initial['total_gb']} GB total ({ram_initial['avail_gb']} GB available, {ram_initial['used_pct']}% load)")
    if gpu_initial["total_mib"]:
        print(f"GPU VRAM:            {gpu_initial['total_mib']:.0f} MiB total ({gpu_initial['free_mib']:.0f} MiB free, {gpu_initial['used_mib']:.0f} MiB used)")

    use_live_client = is_online and model_available
    if use_live_client:
        print("\n>>> Executing Live Local Inference via Ollama / Gemma 3 12B <<<")
        service = LLMService(client=ollama_client)
    else:
        print("\n>>> Local Model Unavailable — Using Deterministic Mock Client for Benchmark Verification <<<")
        mock_response = json.dumps({
            "summary": "Bharti Airtel demonstrates resilient operational metrics driven by tariff revisions and ARPU expansion.",
            "supporting_evidence": [
                "Citing [News 1] (The Economic Times): ARPU expanded to Rs 211 supported by 5G user migrations.",
                "Citing [Event 1] (TRAI): Monthly post-paid churn remained contained at 1.1%.",
            ],
            "limitations": [
                "Potential macroeconomic pressure on rural discretionary spending.",
                "Intensified promotional competition in entry-level 5G plans.",
            ],
            "direction": "UP",
            "confidence": "MEDIUM",
        })
        mock_client = MockLLMClient(model_name="mock-gemma3:12b", default_response=mock_response)
        service = LLMService(client=mock_client)

    articles, events = create_representative_context()
    print(f"\nContext Payload:     {len(articles)} articles, {len(events)} events (BHARTIARTL)")

    results: List[Dict[str, Any]] = []

    for i in range(1, num_runs + 1):
        run_type = "Cold Start (Run 1)" if i == 1 else f"Warm Request (Run {i})"
        print(f"\n--- Benchmark {run_type} ---")

        ram_pre = get_system_ram_info()
        gpu_pre = get_gpu_memory_info()

        t_start = time.perf_counter()
        try:
            explanation = service.explain_prediction(
                symbol="BHARTIARTL",
                articles=articles,
                events=events,
                quantitative_direction="UP",
                quantitative_probability=0.584,
            )
            t_elapsed = time.perf_counter() - t_start
            success = explanation.status == LLMExplanationStatus.SUCCESS
        except Exception as exc:
            t_elapsed = time.perf_counter() - t_start
            success = False
            explanation = LLMExplanationResult.failed(
                symbol="BHARTIARTL",
                model=service.client.model_name,
                error_message=str(exc),
            )

        ram_post = get_system_ram_info()
        gpu_post = get_gpu_memory_info()

        record = {
            "run_index": i,
            "run_type": run_type,
            "wall_clock_seconds": round(t_elapsed, 3),
            "status": explanation.status.value,
            "success": success,
            "model": explanation.model,
            "direction": explanation.direction,
            "confidence": explanation.confidence,
            "summary_chars": len(explanation.summary),
            "supporting_evidence_count": len(explanation.supporting_evidence),
            "limitations_count": len(explanation.limitations),
            "ram_avail_gb": ram_post.get("avail_gb"),
            "gpu_used_mib": gpu_post.get("used_mib"),
            "gpu_free_mib": gpu_post.get("free_mib"),
        }
        results.append(record)

        print(f"Status:               {record['status']}")
        print(f"Wall-Clock Latency:   {record['wall_clock_seconds']:.3f} s")
        print(f"Direction & Conf:     {record['direction']} ({record['confidence']})")
        print(f"Summary Length:       {record['summary_chars']} chars")
        print(f"Supporting Evidence:  {record['supporting_evidence_count']} items")
        print(f"Limitations Noted:    {record['limitations_count']} items")
        if gpu_post["used_mib"]:
            delta_vram = (gpu_post["used_mib"] or 0) - (gpu_pre["used_mib"] or 0)
            print(f"GPU VRAM Post-Run:    {gpu_post['used_mib']:.0f} MiB (delta: {delta_vram:+.0f} MiB)")
        if ram_post["avail_gb"]:
            print(f"System RAM Free:      {ram_post['avail_gb']} GB")

    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY SCOREBOARD")
    print("=" * 80)
    print(f"{'Run':<22} | {'Latency (s)':<12} | {'Status':<10} | {'Evidence':<9} | {'Limitations':<12} | {'GPU Used':<10}")
    print("-" * 80)
    for r in results:
        vram_str = f"{r['gpu_used_mib']:.0f} MiB" if r["gpu_used_mib"] else "N/A"
        print(f"{r['run_type']:<22} | {r['wall_clock_seconds']:<12.3f} | {r['status']:<10} | {r['supporting_evidence_count']:<9} | {r['limitations_count']:<12} | {vram_str:<10}")

    return results


if __name__ == "__main__":
    runs = 3
    if len(sys.argv) > 1:
        try:
            runs = int(sys.argv[1])
        except ValueError:
            pass
    run_benchmark(num_runs=runs)
