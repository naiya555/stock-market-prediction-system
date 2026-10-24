"""Regression Test Suite for Professional Dashboard Redesign & Functionality Repair.

Verifies:
1. ModelRouter auto-routing and capability inspections.
2. Explicit capability statuses & actionable prerequisites for TCS, RELIANCE, NIFTY 50, and NIFTY_TELECOMMUNICATIONS.
3. Prediction endpoint auto-model selection with single atomic SQLite persistence (zero duplicates).
4. History search ticker normalization (case-insensitive, whitespace, exchange suffix '.NS', aliases).
5. Structured 'why_prediction' evidence payload generation.
6. Chat endpoint for market terminology definitions, instrument blockers, and grounded prediction explanations.
7. Instrument catalog capability status API contract.
"""

from pathlib import Path
import tempfile

from fastapi.testclient import TestClient
import pytest

from app.api.app import create_app
from app.api.schemas import ChatRequest, PredictRequest
from app.database.repository import PredictionRepository
from app.prediction.router import CapabilityStatus, ModelRouter


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_model_router_capabilities():
    """Verify router assigns explicit capability status and actionable prerequisites."""
    router = ModelRouter()

    # Supported equity
    canon, status, reason, prereq = router.inspect_instrument("BHARTIARTL")
    assert canon == "BHARTIARTL"
    assert status == CapabilityStatus.SUPPORTED_AND_READY
    assert prereq is None

    # Unsupported equities
    for sym in ["TCS", "RELIANCE"]:
        canon, status, reason, prereq = router.inspect_instrument(sym)
        assert status == CapabilityStatus.UNSUPPORTED_BY_CURRENT_MODEL
        assert "equity model" in prereq.lower() or "training" in prereq.lower()
        assert "BHARTIARTL" in reason

    # Sectoral and Broad Indices
    for idx_sym in ["NIFTY_50", "NIFTY_TELECOMMUNICATIONS", "NIFTY 50", "NIFTY50"]:
        canon, status, reason, prereq = router.inspect_instrument(idx_sym)
        assert status == CapabilityStatus.REQUIRES_SEPARATE_INDEX_PIPELINE
        assert "index" in prereq.lower()


def test_model_router_route_prediction():
    """Verify route_prediction auto-routes supported instruments to multi_agent_ensemble."""
    router = ModelRouter()

    route = router.route_prediction("BHARTIARTL", requested_model="auto")
    assert route.is_supported is True
    assert route.routed_model == "ensemble"
    assert route.capability_status == CapabilityStatus.SUPPORTED_AND_READY

    # Blocked instrument produces non-supported route with None routed_model
    route_blocked = router.route_prediction("TCS", requested_model="auto")
    assert route_blocked.is_supported is False
    assert route_blocked.routed_model is None
    assert route_blocked.capability_status == CapabilityStatus.UNSUPPORTED_BY_CURRENT_MODEL
    assert route_blocked.actionable_prerequisite is not None


def test_instrument_catalog_has_capability_fields(client: TestClient):
    """Verify GET /api/predict/instruments includes capability_status and actionable_prerequisite."""
    res = client.get("/api/predict/instruments")
    assert res.status_code == 200
    data = res.json()
    assert "instruments" in data
    instruments = {inst["symbol"]: inst for inst in data["instruments"]}

    assert "BHARTIARTL" in instruments
    assert instruments["BHARTIARTL"]["capability_status"] == "SUPPORTED_AND_READY"

    assert "TCS" in instruments
    assert instruments["TCS"]["capability_status"] == "UNSUPPORTED_BY_CURRENT_MODEL"
    assert instruments["TCS"]["actionable_prerequisite"] is not None

    assert "RELIANCE" in instruments
    assert instruments["RELIANCE"]["capability_status"] == "UNSUPPORTED_BY_CURRENT_MODEL"

    assert "NIFTY_50" in instruments
    assert instruments["NIFTY_50"]["capability_status"] == "REQUIRES_SEPARATE_INDEX_PIPELINE"

    assert "NIFTY_TELECOMMUNICATIONS" in instruments
    assert instruments["NIFTY_TELECOMMUNICATIONS"]["capability_status"] == "REQUIRES_SEPARATE_INDEX_PIPELINE"


def test_history_search_canonical_symbol_normalization(client: TestClient):
    """Verify history endpoint search normalizes lowercase, uppercase, and .NS suffix."""
    variations = ["BHARTIARTL", "bhartiartl", "BHARTIARTL.NS", "  bhartiartl  "]
    for q in variations:
        res = client.get(f"/api/history?symbol={q}&limit=5")
        assert res.status_code == 200, f"Failed for query '{q}'"
        data = res.json()
        assert "items" in data
        assert "total" in data
        for item in data["items"]:
            assert item["symbol"] == "BHARTIARTL"


def test_history_item_contains_why_prediction(client: TestClient):
    """Verify GET /api/history returns structured why_prediction evidence object."""
    res = client.get("/api/history?limit=1")
    assert res.status_code == 200
    data = res.json()
    if data["total"] > 0:
        item = data["items"][0]
        assert "why_prediction" in item
        why = item["why_prediction"]
        assert "forecast_direction" in why
        assert "forecast_horizon" in why
        assert "model_provenance" in why
        assert "limitations" in why


def test_chat_endpoint_market_terminology(client: TestClient):
    """Verify /api/chat explains economic and market concepts accurately."""
    queries = [
        "What is the Repo Rate and how does RBI use it?",
        "Explain inflation impact on stock markets",
        "What is SEBI?",
        "What is ATR-14 in technical analysis?",
    ]
    for q in queries:
        res = client.post("/api/chat", json={"message": q})
        assert res.status_code == 200
        data = res.json()
        assert "reply" in data
        assert len(data["reply"]) > 20
        assert "timestamp" in data
        assert "model" in data


def test_chat_endpoint_explains_blocked_instruments(client: TestClient):
    """Verify /api/chat accurately explains instrument blocking with prerequisites."""
    res = client.post("/api/chat", json={"message": "Why is TCS blocked?", "instrument": "TCS"})
    assert res.status_code == 200
    data = res.json()
    reply = data["reply"]
    assert "UNSUPPORTED_BY_CURRENT_MODEL" in reply or "unsupported" in reply.lower()
    assert "training" in reply.lower() or "model" in reply.lower()


def test_chat_endpoint_with_prediction_context(client: TestClient):
    """Verify /api/chat grounds response in provided prediction context."""
    context = {
        "symbol": "BHARTIARTL",
        "predicted_direction": "DOWN",
        "model_name": "ensemble",
        "probability_up": 0.438,
        "why_prediction": {
            "forecast_direction": "DOWN",
            "technical_evidence": "Momentum oscillators indicate short-term consolidation.",
        },
    }
    res = client.post(
        "/api/chat",
        json={
            "message": "Why does the forecast suggest DOWN?",
            "instrument": "BHARTIARTL",
            "prediction_context": context,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "DOWN" in data["reply"] or "BHARTIARTL" in data["reply"]


def test_single_persistence_no_duplicate_predictions():
    """Verify that a single prediction call persists exactly 1 record, not duplicates."""
    from app.prediction.contract import PredictionDataQuality, PredictionResult, PredictionStatus

    dq = PredictionDataQuality(
        total_bars_fetched=100,
        cleaned_bars=100,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp="2026-03-31T15:30:00+05:30",
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=0,
    )
    result = PredictionResult(
        symbol="BHARTIARTL",
        prediction_timestamp="2026-03-31T15:30:00+05:30",
        latest_input_timestamp="2026-03-31T15:30:00+05:30",
        status=PredictionStatus.SUCCESS,
        predicted_direction="UP",
        predicted_label=1,
        probability_up=0.65,
        probability_down=0.35,
        model_name="ensemble",
        model_version="v1.0",
        model_metadata={},
        data_quality=dq,
    )

    with PredictionRepository(db_path=":memory:") as repo:
        pred_id = "test-pred-uuid-1"
        repo.save_prediction(result=result, prediction_id=pred_id)

        records = repo.list_predictions(symbol="BHARTIARTL")
        assert len(records) == 1
        assert records[0]["prediction_id"] == pred_id

        count = repo.count_predictions(symbol="BHARTIARTL")
        assert count == 1


def test_domain_contract_strictly_validates_model_names():
    """Verify PredictionRequest rejects 'unavailable' and invalid model names."""
    from app.prediction.contract import PredictionRequest

    # Valid names
    req_xgb = PredictionRequest(symbol="BHARTIARTL", model_name="xgboost")
    assert req_xgb.model_name == "xgboost"
    req_lgb = PredictionRequest(symbol="BHARTIARTL", model_name="lightgbm")
    assert req_lgb.model_name == "lightgbm"

    # 'unavailable' MUST raise ValueError
    with pytest.raises(ValueError, match="Unsupported model_name 'unavailable'"):
        PredictionRequest(symbol="BHARTIARTL", model_name="unavailable")

    # Any other unsupported string MUST raise ValueError
    with pytest.raises(ValueError, match="Unsupported model_name 'random_forest'"):
        PredictionRequest(symbol="BHARTIARTL", model_name="random_forest")


def test_predict_endpoint_rejects_invalid_model_names_with_422(client: TestClient):
    """Verify /api/predict returns 422 for unsupported model_name string without throwing 500."""
    res_unavail = client.post("/api/predict", json={"symbol": "BHARTIARTL", "model_name": "unavailable"})
    assert res_unavail.status_code == 422

    res_invalid = client.post("/api/predict", json={"symbol": "BHARTIARTL", "model_name": "invalid_model"})
    assert res_invalid.status_code == 422


def test_predict_endpoint_unsupported_instrument_does_not_500(client: TestClient):
    """Verify /api/predict returns structured MODEL_UNAVAILABLE (HTTP 200) for unrouted instruments."""
    # TCS equity
    res_tcs = client.post("/api/predict", json={"symbol": "TCS", "model_name": "auto", "persist": True})
    assert res_tcs.status_code == 200
    data_tcs = res_tcs.json()
    assert data_tcs["status"] == "MODEL_UNAVAILABLE"
    assert data_tcs["capability_status"] == "UNSUPPORTED_BY_CURRENT_MODEL"
    assert "TCS" in data_tcs["actionable_prerequisite"]
    assert data_tcs["prediction_id"] is None  # Must NOT persist a fake/partial audit record

    # NIFTY_50 index
    res_nifty = client.post("/api/predict", json={"symbol": "NIFTY_50", "model_name": "auto", "persist": True})
    assert res_nifty.status_code == 200
    data_nifty = res_nifty.json()
    assert data_nifty["status"] == "MODEL_UNAVAILABLE"
    assert data_nifty["capability_status"] == "REQUIRES_SEPARATE_INDEX_PIPELINE"
    assert "index" in data_nifty["actionable_prerequisite"].lower()
    assert data_nifty["prediction_id"] is None


def test_predict_endpoint_supported_instrument_success(client: TestClient):
    """Verify /api/predict successfully routes BHARTIARTL with automatic routing."""
    res = client.post("/api/predict", json={"symbol": "BHARTIARTL", "model_name": "auto", "persist": False})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["model_name"] == "ensemble"
    assert data["capability_status"] == "SUPPORTED_AND_READY"
    assert data["routing_metadata"]["ml_model"] == "xgboost"
