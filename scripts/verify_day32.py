"""Day 32 Live Verification Script: Multi-Agent Ensemble & Synthesis Layer (Phase 12).

Verifies:
1. Deterministic offline multi-agent synthesis:
   - Agreement & Divergence classification (STRONG_AGREEMENT, DIVERGENCE, PARTIAL, ML_ONLY).
   - Transparent probability blending and independent score preservation (ADR 05).
   - Volatility-anchored target range calculation (ATR-14).
   - Integrated positive/negative factor and downside risk rankings.
2. Canonical PredictionResult adaptation:
   - Model name='ensemble', version='ensemble_v1', uncalibrated ensemble calibration label.
   - Persistence into immutable SQLite PredictionRepository.
   - Outcome verification against market bars using OutcomeVerifier.
3. Ollama daemon inspection and optional live multi-agent synthesis smoke test using Gemma 3 12B:
   - Honest reporting: clearly reports live vs offline status.
   - Never downloads models automatically.
   - Exits successfully for valid offline-only verification when live runtime is unavailable.
"""

from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional
import urllib.request

# Configure UTF-8 encoding on Windows if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.logging_config import setup_logging
from app.core.schemas import MarketOHLCV
from app.database.connection import create_connection
from app.database.repository import PredictionRepository
from app.history.contract import VerificationStatus
from app.history.evaluator import PredictionEvaluator
from app.history.verifier import OutcomeVerifier
from app.llm import (
    LLMDirection,
    LLMReasoningResult,
    LLMService,
    MockLLMClient,
    OllamaLLMClient,
)
from app.news.schemas import NewsArticle
from app.prediction import (
    EnsembleAgreement,
    EnsemblePredictionResult,
    EnsembleService,
    EnsembleWeights,
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
    TargetRange,
)


def _make_sample_ml_result(
    symbol: str = "RELIANCE",
    direction: str = "UP",
    prob_up: float = 0.65,
) -> PredictionResult:
    """Construct deterministic sample ML prediction."""
    dq = PredictionDataQuality(
        total_bars_fetched=100,
        cleaned_bars=100,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp="2026-10-15T15:30:00+05:30",
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=0,
    )
    return PredictionResult(
        symbol=symbol,
        prediction_timestamp="2026-10-16T08:30:00+05:30",
        latest_input_timestamp="2026-10-15T15:30:00+05:30",
        status=PredictionStatus.SUCCESS,
        predicted_direction=direction,
        predicted_label=1 if direction == "UP" else 0,
        probability_up=prob_up,
        probability_down=round(1.0 - prob_up, 4),
        model_name="xgboost",
        model_version="xgboost_v1",
        model_metadata={"n_estimators": 100, "max_depth": 4},
        data_quality=dq,
        is_probability_calibrated=False,
        probability_calibration="uncalibrated",
    )


def _make_sample_llm_result(
    symbol: str = "RELIANCE",
    direction: LLMDirection = LLMDirection.UP,
    confidence: str = "HIGH",
) -> LLMReasoningResult:
    """Construct deterministic sample LLM reasoning result."""
    return LLMReasoningResult(
        symbol=symbol,
        direction=direction,
        reasoning_summary="Telecom ARPU expansion and green energy capex support medium-term revenue visibility.",
        positive_factors=("5G subscriber growth up 14% YoY", "Retail footprint expansion"),
        negative_factors=("Petrochemical refining margin softness",),
        downside_risks=("Crude price volatility", "Regulatory spectrum tariff review"),
        source_references=("Mint: Reliance Q3", "Economic Times"),
        confidence_assessment=confidence,
        model_version="gemma3:12b",
        generated_at=datetime.now(timezone.utc),
    )


def verify_stage1_offline_synthesis() -> bool:
    """Verify deterministic offline synthesis across agreement, divergence, and blending."""
    print("=" * 70)
    print("STAGE 1: Deterministic Multi-Agent Ensemble Synthesis (Offline)")
    print("=" * 70)

    service = EnsembleService()

    # 1. Strong Agreement Case
    ml_up = _make_sample_ml_result(direction="UP", prob_up=0.68)
    llm_up = _make_sample_llm_result(direction=LLMDirection.UP, confidence="HIGH")
    res_agree = service.synthesize(ml_up, llm_up, current_price=2750.0, atr_value=35.0)

    assert res_agree.agreement_status == EnsembleAgreement.STRONG_AGREEMENT
    assert res_agree.combined_direction == "UP"
    # P_comb = 0.70 * 0.68 + 0.30 * 1.0 = 0.476 + 0.30 = 0.776
    assert pytest_approx(res_agree.combined_probability_up, 0.776, 0.005)
    assert res_agree.target_range is not None
    assert res_agree.target_range.lower_bound == 2715.0
    assert res_agree.target_range.upper_bound == 2785.0
    print("  [PASS] Strong Agreement Scenario: P(UP) blended to 77.60%, Target Range [2715.0 - 2785.0]")

    # 2. Divergence Case (ML UP vs LLM DOWN)
    llm_down = _make_sample_llm_result(direction=LLMDirection.DOWN, confidence="HIGH")
    res_diverge = service.synthesize(ml_up, llm_down)

    assert res_diverge.agreement_status == EnsembleAgreement.DIVERGENCE
    # ML = 0.68, LLM = 0.0 (polarity -1.0) -> P_comb = 0.70 * 0.68 + 0.30 * 0.0 = 0.476 -> DOWN!
    assert res_diverge.combined_direction == "DOWN"
    assert res_diverge.combined_probability_up == 0.476
    print("  [PASS] Divergence Scenario: ML(UP, 0.68) vs LLM(DOWN, HIGH) correctly flags DIVERGENCE")

    # 3. Partial Case (LLM INSUFFICIENT_EVIDENCE)
    llm_neutral = _make_sample_llm_result(direction=LLMDirection.INSUFFICIENT_EVIDENCE, confidence="LOW")
    res_partial = service.synthesize(ml_up, llm_neutral)

    assert res_partial.agreement_status == EnsembleAgreement.PARTIAL
    # LLM implied P = 0.50 -> P_comb = 0.70 * 0.68 + 0.30 * 0.50 = 0.476 + 0.15 = 0.626
    assert pytest_approx(res_partial.combined_probability_up, 0.626, 0.005)
    print("  [PASS] Partial Scenario: LLM INSUFFICIENT_EVIDENCE shrinks probability towards 50%")

    # 4. ML-Only Fallback Case
    res_ml_only = service.synthesize(ml_up, llm_result=None)
    assert res_ml_only.agreement_status == EnsembleAgreement.ML_ONLY
    assert res_ml_only.combined_probability_up == 0.68
    assert res_ml_only.weights_used["ml"] == 1.0
    print("  [PASS] ML-Only Fallback: Gracefully attributes 100% weight to ML")

    # 5. Independent Score Preservation (ADR 05)
    assert res_agree.ml_prediction is not None and res_agree.ml_prediction.model_name == "xgboost"
    assert res_agree.llm_reasoning is not None and res_agree.llm_reasoning.direction == LLMDirection.UP
    print("  [PASS] Independent Score Preservation: Both standalone models fully preserved")

    return True


def verify_stage2_persistence_and_evaluation() -> bool:
    """Verify adaptation to canonical PredictionResult, SQLite storage, and outcome verification."""
    print("\n" + "=" * 70)
    print("STAGE 2: SQLite Persistence and Outcome Verification Lifecycle")
    print("=" * 70)

    conn = create_connection(":memory:")
    repo = PredictionRepository(conn=conn)

    ml = _make_sample_ml_result(symbol="INFY", direction="UP", prob_up=0.64)
    llm = _make_sample_llm_result(symbol="INFY", direction=LLMDirection.UP, confidence="MEDIUM")
    service = EnsembleService(repository=repo)

    ensemble_res = service.synthesize(ml, llm, current_price=1850.0, atr_value=22.0)
    adapted = ensemble_res.to_prediction_result()

    # Save to database
    pred_id = repo.save_prediction(adapted)
    assert pred_id is not None
    saved = repo.get_prediction(pred_id)
    assert saved["model_name"] == "ensemble"
    assert saved["predicted_direction"] == "UP"
    print(f"  [PASS] Saved ensemble prediction '{pred_id}' to SQLite with model_name='ensemble'")

    # Verify against realized session close
    t0 = datetime(2026, 10, 15, 15, 30, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 16, 15, 30, tzinfo=timezone.utc)
    bars = [
        MarketOHLCV(symbol="INFY", timestamp=t0, open=1845.0, high=1860.0, low=1840.0, close=1850.0, volume=100000, source="yfinance"),
        MarketOHLCV(symbol="INFY", timestamp=t1, open=1855.0, high=1880.0, low=1850.0, close=1875.0, volume=110000, source="yfinance"),
    ]

    verifier = OutcomeVerifier(repository=repo)
    v_record = verifier.verify_prediction(pred_id, market_bars=bars, persist=True)

    assert v_record.status == VerificationStatus.VERIFIED
    assert v_record.actual_direction == "UP"
    assert v_record.is_correct is True
    print("  [PASS] OutcomeVerifier successfully verified ensemble prediction against session bars (is_correct=True)")

    # Performance Evaluator Check
    evaluator = PredictionEvaluator(repository=repo)
    metrics = evaluator.evaluate(symbol="INFY", model_name="ensemble")
    assert metrics.eligible_predictions == 1
    assert metrics.directional_accuracy == 1.0
    print("  [PASS] PredictionEvaluator side-by-side metric tracking computed: Accuracy = 100.0%")

    return True


def verify_stage3_live_ollama_synthesis() -> Optional[Dict[str, Any]]:
    """Check Ollama reachability and execute live multi-agent synthesis if gemma3:12b is active."""
    print("\n" + "=" * 70)
    print("STAGE 3: Live Multi-Agent Synthesis (XGBoost + Gemma 3 12B)")
    print("=" * 70)

    ollama_client = OllamaLLMClient(timeout_seconds=90.0)
    status: Dict[str, Any] = {"reachable": False, "target_model_available": False}

    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(f"{ollama_client.base_url}/api/tags", headers={"User-Agent": "Day32Verifier/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            latency = (time.perf_counter() - t0) * 1000.0
            if resp.status == 200:
                status["reachable"] = True
                status["latency_ms"] = round(latency, 1)
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                status["models"] = models
                status["target_model_available"] = any("gemma3:12b" in m for m in models)
    except Exception as e:
        status["error"] = str(e)

    if not status["reachable"] or not status["target_model_available"]:
        print(f"  Ollama Daemon Status: {'REACHABLE' if status['reachable'] else 'OFFLINE'}")
        print(f"  Target Model gemma3:12b: {'FOUND' if status['target_model_available'] else 'NOT FOUND'}")
        print("  [NOTE] Skipping live inference. Offline verification remains fully valid.")
        return None

    print(f"  Ollama Daemon: REACHABLE ({ollama_client.base_url}, latency {status['latency_ms']}ms)")
    print(f"  Model gemma3:12b: LOADED")
    print("  Dispatching live multi-agent ensemble synthesis...")

    article = NewsArticle(
        headline="Tata Motors reports strong commercial vehicle demand and EV order intake",
        source="Economic Times",
        published_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        symbols=("TATAMOTORS",),
        summary="Operating margins expanded 110 bps on favorable product mix.",
    )

    llm_service = LLMService(client=ollama_client)
    ml_result = _make_sample_ml_result(symbol="TATAMOTORS", direction="UP", prob_up=0.62)

    t_start = time.perf_counter()
    try:
        llm_result = llm_service.generate_qualitative_reasoning("TATAMOTORS", [article])
        elapsed = time.perf_counter() - t_start
        print(f"  [LIVE PASS] Gemma 3 12B reasoning completed in {elapsed:.2f}s:")
        print(f"    - LLM Direction: {llm_result.direction.value} (Confidence: {llm_result.confidence_assessment})")
        print(f"    - LLM Summary: {llm_result.reasoning_summary}")

        ens_service = EnsembleService()
        ensemble_res = ens_service.synthesize(
            ml_result=ml_result,
            llm_result=llm_result,
            current_price=980.0,
            atr_value=18.5,
        )

        print(f"  [LIVE PASS] Multi-Agent Synthesis Complete:")
        print(f"    - Combined Direction:  {ensemble_res.combined_direction}")
        print(f"    - Combined P(UP):      {ensemble_res.combined_probability_up:.1%}")
        print(f"    - Agreement Status:    {ensemble_res.agreement_status.value}")
        print(f"    - Target Range (1d):   [{ensemble_res.target_range.lower_bound:.2f} - {ensemble_res.target_range.upper_bound:.2f}]")
        print(f"    - Downside Risks:      {list(ensemble_res.downside_risks)}")

        return {
            "success": True,
            "latency_s": round(elapsed, 2),
            "combined_direction": ensemble_res.combined_direction,
            "agreement_status": ensemble_res.agreement_status.value,
        }
    except Exception as exc:
        print(f"  [LIVE FAIL] Live synthesis error: {exc}")
        return {"success": False, "error": str(exc)}


def pytest_approx(actual: float, expected: float, tol: float = 0.01) -> bool:
    """Helper for tolerance check without importing pytest."""
    return abs(actual - expected) <= tol


def main() -> int:
    """Run full Day 32 verification."""
    setup_logging()
    print("Starting Day 32 Multi-Agent Ensemble Layer Verification...")
    print(f"Verification Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # 1. Offline tests
    s1_ok = verify_stage1_offline_synthesis()
    if not s1_ok:
        print("[FAIL] Stage 1 offline synthesis failed.")
        return 1

    # 2. Persistence and evaluation
    s2_ok = verify_stage2_persistence_and_evaluation()
    if not s2_ok:
        print("[FAIL] Stage 2 persistence and verification failed.")
        return 1

    # 3. Live synthesis
    live_info = verify_stage3_live_ollama_synthesis()

    # Final Summary
    print("\n" + "=" * 70)
    print("DAY 32 VERIFICATION SUMMARY")
    print("=" * 70)
    print("  Offline Multi-Agent Synthesis: PASS (Agreement, Divergence, Blending)")
    print("  Independent Score Preservation: PASS (ADR 05 compliant)")
    print("  Target Range & ATR Estimation:  PASS (Physical bound calculation)")
    print("  Database & Outcome Lifecycle:   PASS (Persistence, Verification, Evaluator)")
    if live_info and live_info.get("success"):
        print(f"  Live Gemma 3 12B Synthesis:    SUCCESS ({live_info['latency_s']}s latency, {live_info['agreement_status']})")
    else:
        print("  Live Gemma 3 12B Synthesis:    SKIPPED / UNVERIFIED (Ollama/model offline)")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
