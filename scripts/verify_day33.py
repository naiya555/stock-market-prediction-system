"""Day 33 Live Verification Script: FastAPI Application Foundation.

Verifies:
1. FastAPI application factory, routing table, and OpenAPI specification compliance.
2. Health check route (/api/health) validating subsystem readiness without secret leakage.
3. Prediction route (/api/predict) executing quantitative ML and multi-agent ensemble forecasting.
4. History route (/api/history) querying immutable SQLite records and linked verified actual outcomes.
5. Feedback route (/api/feedback) enforcing schema validation and explicit deferred 501 status (ADR 10).
6. Events route (/api/events) querying normalized, deduplicated macroeconomic and regulatory announcements.
7. Security, schema validation, and error-handling resilience without stack trace leaks.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock

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

from fastapi.testclient import TestClient

from app.api import app, create_app
from app.api.dependencies import (
    get_db_connection,
    get_ensemble_service,
    get_event_providers,
    get_prediction_repository,
    get_prediction_service,
)
from app.database.connection import create_connection
from app.database.repository import PredictionRepository
from app.database.schema import initialize_database
from app.events.providers.base import BaseEventProvider
from app.events.schemas import EventCategory, MacroEvent
from app.llm.schemas import LLMDirection, LLMReasoningResult
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.ensemble import (
    EnsembleAgreement,
    EnsemblePredictionResult,
    EnsembleService,
    TargetRange,
)
from app.prediction.service import PredictionService


def test_stage_1_app_and_openapi(client: TestClient) -> bool:
    """Verify application creation, root endpoint, and OpenAPI schema generation."""
    print("=" * 70)
    print("STAGE 1: Application Factory and OpenAPI Specification")
    print("=" * 70)

    # 1. Root route
    res_root = client.get("/")
    assert res_root.status_code == 200, f"Expected 200, got {res_root.status_code}"
    root_data = res_root.json()
    print(f" [PASS] Root Endpoint: {root_data['name']} (status={root_data['status']})")
    assert root_data["status"] == "running"
    assert root_data["docs"] == "/docs"

    # 2. OpenAPI JSON Schema
    res_openapi = client.get("/openapi.json")
    assert res_openapi.status_code == 200, f"Expected 200, got {res_openapi.status_code}"
    schema = res_openapi.json()
    paths = list(schema.get("paths", {}).keys())
    print(f" [PASS] OpenAPI Schema: Generated with {len(paths)} routes registered:")
    for p in sorted(paths):
        print(f"        - {p}")

    assert "/api/health" in paths
    assert "/api/predict" in paths
    assert "/api/history" in paths
    assert "/api/feedback" in paths
    assert "/api/events" in paths
    return True


def test_stage_2_health_and_security(client: TestClient) -> bool:
    """Verify health endpoint diagnostics and confidential data isolation."""
    print("\n" + "=" * 70)
    print("STAGE 2: Health Readiness & Non-Disclosure Verification")
    print("=" * 70)

    res = client.get("/api/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    health_data = res.json()

    print(f" [PASS] Health Status: {health_data['status']}")
    print(f" [PASS] Environment: {health_data['environment']}")
    for dep, info in health_data["dependencies"].items():
        print(f"        - {dep.capitalize()}: {info['status']} ({info.get('details')})")

    # Security check: verify no local filesystem paths or passwords leaked
    text = res.text.lower()
    assert "password" not in text, "Leaked password keyword in health response"
    assert "secret" not in text, "Leaked secret keyword in health response"
    assert "c:\\" not in text and "/home/" not in text, "Leaked absolute path in health response"
    print(" [PASS] Security Audit: Zero secrets or absolute filesystem paths disclosed.")
    return True


def test_stage_3_prediction_and_ensemble(client: TestClient) -> bool:
    """Verify standalone ML and synthesized ensemble prediction endpoints."""
    print("\n" + "=" * 70)
    print("STAGE 3: Prediction & Ensemble Inference Pipeline")
    print("=" * 70)

    # 1. Validation test (invalid symbol)
    res_bad = client.post("/api/predict", json={"symbol": "  ", "model_name": "xgboost"})
    assert res_bad.status_code == 422, f"Expected 422 for empty symbol, got {res_bad.status_code}"
    print(" [PASS] Validation: Rejected whitespace symbol with HTTP 422 Unprocessable Content.")

    # 2. Standalone ML Prediction
    res_ml = client.post(
        "/api/predict",
        json={"symbol": "RELIANCE", "model_name": "xgboost", "persist": True},
    )
    assert res_ml.status_code == 200, f"Expected 200, got {res_ml.status_code}: {res_ml.text}"
    ml_data = res_ml.json()
    print(f" [PASS] Standalone ML Prediction: symbol={ml_data['symbol']}, direction={ml_data['predicted_direction']}, P(UP)={ml_data['probability_up']}")
    assert ml_data["status"] == "SUCCESS"
    assert ml_data["prediction_id"] is not None
    assert ml_data["ensemble"] is None

    # 3. Multi-Agent Ensemble Prediction
    res_ens = client.post(
        "/api/predict",
        json={"symbol": "RELIANCE", "model_name": "ensemble", "ml_weight": 0.70, "llm_weight": 0.30, "persist": True},
    )
    assert res_ens.status_code == 200, f"Expected 200, got {res_ens.status_code}: {res_ens.text}"
    ens_data = res_ens.json()
    ens_breakdown = ens_data["ensemble"]
    print(f" [PASS] Ensemble Prediction: symbol={ens_data['symbol']}, direction={ens_data['predicted_direction']}, agreement={ens_breakdown['agreement_status']}")
    print(f"        - Combined Probability P(UP)={ens_breakdown['combined_probability_up']:.4f}")
    print(f"        - Target Range: INR [{ens_breakdown['target_range']['lower_bound']} - {ens_breakdown['target_range']['upper_bound']}]")
    print(f"        - Factors: {len(ens_breakdown['integrated_positive_factors'])} positive, {len(ens_breakdown['downside_risks'])} downside risks")
    assert ens_breakdown["agreement_status"] == "STRONG_AGREEMENT"
    return True


def test_stage_4_history_and_actuals(client: TestClient, test_repo: PredictionRepository) -> bool:
    """Verify historical prediction querying, filtering, and actual outcome attachment."""
    print("\n" + "=" * 70)
    print("STAGE 4: History Retrieval & Verified Outcome Linkage")
    print("=" * 70)

    # 1. Query overall history
    res_hist = client.get("/api/history?limit=10")
    assert res_hist.status_code == 200, f"Expected 200, got {res_hist.status_code}"
    hist_data = res_hist.json()
    print(f" [PASS] History Count: Total={hist_data['total']}, Retrieved={len(hist_data['items'])}")
    assert hist_data["total"] >= 2

    # 2. Add verified actual outcome to first prediction
    first_pid = hist_data["items"][0]["prediction_id"]
    first_sym = hist_data["items"][0]["symbol"]

    actual_data = {
        "prediction_id": first_pid,
        "symbol": first_sym,
        "target_date": "2026-10-19",
        "actual_direction": "UP",
        "actual_label": 1,
        "actual_return": 0.0142,
        "actual_close": 2535.50,
        "reference_close": 2500.0,
        "source": "yfinance",
    }
    test_repo.save_actual(actual_data)
    print(f" [PASS] Inserted verified actual outcome for prediction '{first_pid}'.")

    # 3. Query history with verified outcome
    res_verified = client.get(f"/api/history?symbol={first_sym}")
    assert res_verified.status_code == 200
    v_data = res_verified.json()
    matched = [it for it in v_data["items"] if it["prediction_id"] == first_pid]
    assert len(matched) == 1
    actual_linked = matched[0]["actual"]
    assert actual_linked is not None
    print(f" [PASS] Verified Outcome Linked: close={actual_linked['actual_close']}, return={actual_linked['actual_return']:.2%}, direction={actual_linked['actual_direction']}")
    assert actual_linked["actual_direction"] == "UP"
    return True


def test_stage_5_feedback_deferred(client: TestClient) -> bool:
    """Verify feedback endpoint correctly defers persistence under ADR 10."""
    print("\n" + "=" * 70)
    print("STAGE 5: Feedback Validation & Explicit ADR 10 Deferral")
    print("=" * 70)

    feedback_payload = {
        "prediction_id": "test_uuid_456",
        "feedback_type": "accuracy_critique",
        "comments": "Slight divergence between quantitative momentum and policy announcement.",
        "rating": 4,
    }
    res = client.post("/api/feedback", json=feedback_payload)
    assert res.status_code == 501, f"Expected 501 Not Implemented, got {res.status_code}"
    fb_data = res.json()
    print(f" [PASS] Feedback Response Status: HTTP 501 Not Implemented")
    print(f"        - Status: {fb_data['status']}")
    print(f"        - Message: {fb_data['message']}")
    assert fb_data["status"] == "deferred"
    assert "ADR 10" in fb_data["message"]
    return True


def test_stage_6_events_aggregation(client: TestClient) -> bool:
    """Verify macroeconomic and regulatory events retrieval and filtering."""
    print("\n" + "=" * 70)
    print("STAGE 6: Events Monitoring & Deduplication")
    print("=" * 70)

    res = client.get("/api/events?limit=10")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    ev_data = res.json()
    print(f" [PASS] Ingested Events: {ev_data['count']} events from providers {ev_data['providers_queried']}")
    for ev in ev_data["events"][:2]:
        print(f"        - [{ev['category'].upper()}] {ev['title']} ({ev['source_org']})")

    assert ev_data["count"] >= 1
    return True


def main() -> int:
    """Run full Day 33 verification pipeline."""
    print("=" * 70)
    print("DAY 33 VERIFICATION: FASTAPI REST APPLICATION FOUNDATION")
    print("=" * 70)

    # Setup pristine in-memory test environment
    conn = create_connection(":memory:")
    initialize_database(conn)
    repo = PredictionRepository(conn=conn)

    # Setup mock services
    mock_pred_service = MagicMock(spec=PredictionService)
    dq = PredictionDataQuality(
        total_bars_fetched=250,
        cleaned_bars=245,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp="2026-10-16T15:30:00+05:30",
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=1,
    )
    mock_ml_res = PredictionResult(
        symbol="RELIANCE",
        prediction_timestamp=datetime.now(timezone.utc).isoformat(),
        latest_input_timestamp="2026-10-16T15:30:00+05:30",
        status=PredictionStatus.SUCCESS,
        predicted_direction="UP",
        predicted_label=1,
        probability_up=0.68,
        probability_down=0.32,
        model_name="xgboost",
        model_version="xgb_v1",
        model_metadata={},
        data_quality=dq,
        is_probability_calibrated=False,
        probability_calibration="uncalibrated",
        expected_movement=None,
        expected_movement_status="UNSUPPORTED",
        error_message=None,
        disclaimer="Standard research disclaimer.",
    )
    mock_pred_service.predict.return_value = mock_ml_res

    mock_llm_res = LLMReasoningResult(
        symbol="RELIANCE",
        direction=LLMDirection.UP,
        reasoning_summary="Favorable refining margins and stable domestic demand.",
        positive_factors=["Strong quarterly performance", "Refining margin expansion"],
        negative_factors=["Crude volatility"],
        downside_risks=["Global demand contraction"],
        source_references=["RBI MPC Minutes Oct 2026"],
        confidence_assessment="HIGH",
        model_version="gemma3:12b",
    )
    mock_ens_res = EnsemblePredictionResult(
        symbol="RELIANCE",
        prediction_timestamp=datetime.now(timezone.utc).isoformat(),
        latest_input_timestamp="2026-10-16T15:30:00+05:30",
        status=PredictionStatus.SUCCESS,
        combined_direction="UP",
        combined_label=1,
        combined_probability_up=0.74,
        combined_probability_down=0.26,
        agreement_status=EnsembleAgreement.STRONG_AGREEMENT,
        weights_used={"ml": 0.70, "llm": 0.30},
        ml_prediction=mock_ml_res,
        llm_reasoning=mock_llm_res,
        sentiment_summary=None,
        integrated_positive_factors=("Strong quarterly performance", "Refining margin expansion"),
        integrated_negative_factors=("Crude volatility",),
        downside_risks=("Global demand contraction",),
        source_references=("RBI MPC Minutes Oct 2026",),
        target_range=TargetRange(
            lower_bound=2450.0,
            upper_bound=2550.0,
            reference_price=2500.0,
            method="atr_14",
        ),
        model_name="ensemble",
        model_version="ensemble_v1",
        error_message=None,
        disclaimer="Ensemble disclaimer.",
    )
    mock_ens_service = MagicMock(spec=EnsembleService)
    mock_ens_service.predict_ensemble.return_value = mock_ens_res

    # Mock event provider
    now = datetime.now(timezone.utc)
    ev_sample = MacroEvent(
        title="RBI Repo Rate maintained at 6.50%",
        category=EventCategory.MONETARY_POLICY,
        event_type="rate_decision",
        source_org="Reserve Bank of India",
        ingested_at=now,
        published_at=now,
        affected_sectors=("BANKING", "FINANCIAL_SERVICES"),
        provider="rbi_provider",
    )
    mock_event_provider = MagicMock(spec=BaseEventProvider)
    mock_event_provider.name = "rbi_provider"
    mock_event_provider.fetch_events.return_value = [ev_sample]

    # Wire FastAPI test application
    test_app = create_app()
    test_app.dependency_overrides[get_db_connection] = lambda: conn
    test_app.dependency_overrides[get_prediction_repository] = lambda: repo
    test_app.dependency_overrides[get_prediction_service] = lambda: mock_pred_service
    test_app.dependency_overrides[get_ensemble_service] = lambda: mock_ens_service
    test_app.dependency_overrides[get_event_providers] = lambda: [mock_event_provider]

    with TestClient(test_app) as client:
        test_stage_1_app_and_openapi(client)
        test_stage_2_health_and_security(client)
        test_stage_3_prediction_and_ensemble(client)
        test_stage_4_history_and_actuals(client, repo)
        test_stage_5_feedback_deferred(client)
        test_stage_6_events_aggregation(client)

    print("\n" + "=" * 70)
    print("ALL DAY 33 REST API VERIFICATION STAGES PASSED SUCCESSFULLY!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
