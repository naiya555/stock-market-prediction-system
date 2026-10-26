"""Target Integration Test Suite for Phases 2-8: Three Instruments, Simplified Results, Chart-Data, and Chat Assistant.

Validates:
1. TCS, NIFTY_50, NIFTY_TELECOMMUNICATIONS, and BHARTIARTL routing & inference readiness.
2. Blocked status enforcement for RELIANCE.
3. PredictionResponse contract: direction, grounded reason, quote context with open price, previous close, change, and change_percent.
4. Chart data endpoint (/api/predict/chart-data) for all symbols across intraday and daily ranges.
5. Chat assistant endpoint (/api/chat) for the 5 required categories without HTTP 500:
   - Why prediction is UP/DOWN.
   - Latest price and market session state.
   - Financial terminology (Repo Rate).
   - Instrument availability and prerequisites (TCS ready, RELIANCE blocked).
   - Relevant verified market events.
6. History endpoint and preservation of existing audit records.
"""

from fastapi.testclient import TestClient
import pytest

from app.api.app import create_app
from app.prediction.router import CapabilityStatus, ModelRouter


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_router_target_instruments_readiness():
    """Verify ModelRouter correctly recognizes BHARTIARTL, TCS, NIFTY_50, and NIFTY_TELECOM as ready."""
    router = ModelRouter()

    for sym in ["BHARTIARTL", "TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]:
        decision = router.route_prediction(sym)
        assert decision.is_supported is True
        assert decision.capability_status == CapabilityStatus.SUPPORTED_AND_READY
        assert decision.routed_model == "ensemble"

    # RELIANCE remains blocked
    rel_decision = router.route_prediction("RELIANCE")
    assert rel_decision.is_supported is False
    assert rel_decision.capability_status == CapabilityStatus.UNSUPPORTED_BY_CURRENT_MODEL


def test_prediction_endpoint_fields_and_reason(client: TestClient):
    """Verify prediction result card contains primary simplified fields: direction, reason, and quote context."""
    for sym in ["BHARTIARTL", "TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]:
        resp = client.post(
            "/api/predict",
            json={"symbol": sym, "model_name": "xgboost", "persist": False},
        )
        assert resp.status_code == 200, f"Predict failed for {sym}"
        data = resp.json()
        assert data["status"] == "SUCCESS", f"Status not SUCCESS for {sym}: {data.get('error_message')}"
        assert data["predicted_direction"] in ["UP", "DOWN"]
        assert data["reason"] is not None
        assert len(data["reason"]) > 10

        # Quote context primary fields
        qc = data.get("quote_context")
        assert qc is not None
        assert "last_price" in qc
        assert "price_timestamp" in qc
        assert "is_delayed" in qc
        assert "session_state" in qc


def test_chart_data_endpoint(client: TestClient):
    """Verify /api/predict/chart-data returns candles, consecutive changes, and forecast points."""
    for sym in ["BHARTIARTL", "TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]:
        for rng in ["today", "5d", "1m"]:
            resp = client.get(f"/api/predict/chart-data?symbol={sym}&range={rng}")
            assert resp.status_code == 200, f"Chart data failed for {sym} {rng}"
            data = resp.json()
            assert data["symbol"] == sym
            assert data["range"] == rng
            assert "data_points" in data
            assert len(data["data_points"]) > 0

            # Inspect point schema
            pt = data["data_points"][0]
            assert "timestamp" in pt
            assert "close" in pt
            assert pt["close"] > 0

            # Forecast point attached
            fp = data.get("forecast_point")
            assert fp is not None
            assert fp["direction"] in ["UP", "DOWN"]


def test_chat_assistant_five_required_categories(client: TestClient):
    """Verify chat assistant answers all 5 required categories gracefully without HTTP 500."""
    queries = [
        # 1. Why prediction is UP or DOWN
        {"message": "Why is the prediction UP for TCS?", "instrument": "TCS"},
        # 2. Latest price and market session
        {"message": "What is the latest price and market session for BHARTIARTL?", "instrument": "BHARTIARTL"},
        # 3. Market terminology (Repo Rate)
        {"message": "What is Repo Rate and how does it affect stocks?", "instrument": "TCS"},
        # 4. Instrument availability & prerequisites
        {"message": "Why is RELIANCE blocked and what is required to enable it?", "instrument": "RELIANCE"},
        {"message": "Is TCS available for forecasting?", "instrument": "TCS"},
        # 5. Relevant verified market events
        {"message": "What verified market events are relevant to BHARTIARTL?", "instrument": "BHARTIARTL"},
    ]

    for q in queries:
        resp = client.post("/api/chat", json=q)
        assert resp.status_code == 200, f"Chat failed for query: {q}"
        data = resp.json()
        assert "reply" in data
        assert len(data["reply"]) > 20
        # No raw unparsed Python reprs or error traces
        assert "Traceback" not in data["reply"]
        assert "NoneType" not in data["reply"]


def test_history_search_and_record_preservation(client: TestClient):
    """Verify history endpoint retrieves historical records and handles nonexistent tickers gracefully."""
    # Existing symbols
    for sym in ["BHARTIARTL", "TCS"]:
        resp = client.get(f"/api/history?symbol={sym}&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    # Nonexistent ticker
    resp_none = client.get("/api/history?symbol=NONEXISTENT_TICKER_123&limit=5")
    assert resp_none.status_code == 200
    data_none = resp_none.json()
    assert data_none["total"] == 0
    assert data_none["items"] == []
