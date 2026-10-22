"""Deterministic behavioral tests for Day 66: API Contract Consistency & Prediction Result Integrity Audit.

Validates:
1. Authoritative PredictionResponse schema and exact field mapping on the wire.
2. Successful prediction wire response integrity (direction, uncalibrated score, quote context).
3. Blocked equities (TCS, RELIANCE) and blocked indices (NIFTY_TELECOMMUNICATIONS, NIFTY_50) semantics.
4. Blocked response status cannot render success badge or hero card.
5. Authoritative instrument catalog compatibility.
6. Safe handling of unknown status values and missing optional fields.
7. Frontend stale-result protection and input change cleanup.
8. Evidence-aligned probability disclaimer (no misleading p > 0.34 claims).
9. Historical quote versus forecast distinction (no observed price presented as forecast).
10. Retry payload preservation without duplicate submission.
"""

import json
from pathlib import Path
import re

from fastapi.testclient import TestClient
import pytest

from app.api.app import app
from app.api.schemas import (
    DataQualityResponse,
    EnsembleDetailsResponse,
    InstrumentCatalogResponse,
    PredictionResponse,
    QuoteContextResponse,
    TargetRangeResponse,
)


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


class TestApiContractConsistency:
    """Audit schema contracts and wire serialization."""

    def test_authoritative_prediction_response_schema_fields(self):
        """Verify the exact field names in PredictionResponse schema."""
        fields = PredictionResponse.model_fields
        # Must have predicted_direction, not direction
        assert "predicted_direction" in fields
        assert "predicted_label" in fields
        # Must have probability_up and probability_down, not probabilities
        assert "probability_up" in fields
        assert "probability_down" in fields
        # Must have quote_context, not market_quote
        assert "quote_context" in fields
        # Must have status and error_message
        assert "status" in fields
        assert "error_message" in fields
        assert "is_probability_calibrated" in fields
        assert "probability_calibration" in fields
        assert "model_name" in fields
        assert "model_version" in fields
        assert "prediction_id" in fields
        assert "symbol" in fields
        assert "disclaimer" in fields

    def test_quote_context_schema_fields(self):
        """Verify QuoteContextResponse field names and price type distinction."""
        fields = QuoteContextResponse.model_fields
        # Must have last_price, not last_traded_price
        assert "last_price" in fields
        # Must have price_timestamp, not quote_timestamp
        assert "price_timestamp" in fields
        assert "price_type" in fields
        assert "session_state" in fields
        assert "freshness_status" in fields
        assert "is_delayed" in fields
        assert "delay_minutes" in fields
        assert "note" in fields

    def test_successful_prediction_wire_response_integrity(self, client):
        """Verify real BHARTIARTL prediction wire response strictly satisfies API contract."""
        resp = client.post(
            "/api/predict",
            json={"symbol": "BHARTIARTL", "model_name": "xgboost", "persist": False},
        )
        assert resp.status_code == 200
        data = resp.json()

        # Contract field verification
        assert data["symbol"] == "BHARTIARTL"
        assert data["status"] == "SUCCESS"
        assert data["model_name"] == "xgboost"
        assert "predicted_direction" in data
        assert data["predicted_direction"] in ["UP", "DOWN"]
        assert isinstance(data["probability_up"], (float, int))
        assert isinstance(data["probability_down"], (float, int))
        assert data["is_probability_calibrated"] is False
        assert data["probability_calibration"] == "uncalibrated"

        # Quote context verification
        assert "quote_context" in data
        qc = data["quote_context"]
        if qc is not None:
            assert qc["price_type"] == "LAST_TRADED_PRICE"
            assert "NOT a predicted opening or closing price" in qc["note"]
            if qc["last_price"] is not None:
                assert isinstance(qc["last_price"], (float, int))
                assert qc["last_price"] > 0


class TestBlockedInstrumentSemantics:
    """Verify distinct blocked-instrument handling and index separation."""

    def test_blocked_equities_cannot_produce_forecast(self, client):
        """Verify unsupported equities TCS and RELIANCE return MODEL_UNAVAILABLE with null forecasts."""
        for sym in ["TCS", "RELIANCE"]:
            resp = client.post(
                "/api/predict",
                json={"symbol": sym, "model_name": "xgboost", "persist": False},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["symbol"] == sym
            assert data["status"] == "MODEL_UNAVAILABLE"
            assert data["predicted_direction"] is None
            assert data["predicted_label"] is None
            assert data["probability_up"] is None
            assert data["probability_down"] is None
            assert "No trained model artifact found" in data["error_message"]
            assert "BHARTIARTL" in data["error_message"]

    def test_blocked_indices_cannot_produce_forecast(self, client):
        """Verify sectoral and broad market indices cannot be forecasted with equity models."""
        for sym in ["NIFTY_TELECOMMUNICATIONS", "NIFTY_50"]:
            resp = client.post(
                "/api/predict",
                json={"symbol": sym, "model_name": "xgboost", "persist": False},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["symbol"] == sym
            assert data["status"] in ["MODEL_UNAVAILABLE", "FAILED"]
            assert data["predicted_direction"] is None
            assert "BHARTIARTL equity models cannot be reused for sectoral indices" in data["error_message"]

    def test_authoritative_instrument_catalog_completeness(self, client):
        """Verify GET /api/predict/instruments accurately reflects catalog contracts."""
        resp = client.get("/api/predict/instruments")
        assert resp.status_code == 200
        data = resp.json()

        assert "instruments" in data
        assert data["supported_count"] == 1
        assert data["blocked_count"] == 4

        inst_dict = {i["symbol"]: i for i in data["instruments"]}
        assert inst_dict["BHARTIARTL"]["status"] == "SUPPORTED"
        assert inst_dict["BHARTIARTL"]["instrument_type"] == "EQUITY"
        assert inst_dict["TCS"]["status"] == "BLOCKED"
        assert inst_dict["TCS"]["instrument_type"] == "EQUITY"
        assert inst_dict["RELIANCE"]["status"] == "BLOCKED"
        assert inst_dict["RELIANCE"]["instrument_type"] == "EQUITY"
        assert inst_dict["NIFTY_TELECOMMUNICATIONS"]["status"] == "BLOCKED"
        assert inst_dict["NIFTY_TELECOMMUNICATIONS"]["instrument_type"] == "INDEX"
        assert inst_dict["NIFTY_50"]["status"] == "BLOCKED"
        assert inst_dict["NIFTY_50"]["instrument_type"] == "INDEX"


class TestFrontendIntegrityAndSafeRendering:
    """Verify frontend JavaScript logic against contract expectations."""

    def test_app_js_guards_against_non_success_statuses(self, client):
        """Verify renderPredictionResult strictly verifies isSuccess before showing hero card."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        # Strict success gating
        assert "const isSuccess = res.status === 'SUCCESS' && !!(res.predicted_direction || res.direction);" in js
        assert "if (!isSuccess) {" in js
        assert "if (heroCard) heroCard.style.display = 'none';" in js
        assert "if (breakdownGrid) breakdownGrid.style.display = 'none';" in js
        assert "if (blockedCard) {" in js

    def test_app_js_cleans_up_stale_results_on_symbol_change(self, client):
        """Verify app.js clears stale prediction display whenever a different symbol is selected."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "clearStalePredictionIfSymbolChanged" in js
        assert "AppState.prediction = null;" in js
        assert "clearStalePredictionIfSymbolChanged(sym)" in js
        assert "clearStalePredictionIfSymbolChanged(inst.symbol)" in js

    def test_app_js_retry_preserves_payload_and_guards_duplicate_submission(self, client):
        """Verify retry reuses lastPredictionPayload and maintains concurrency guard."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "AppState.lastPredictionPayload = payload;" in js
        assert "AppState.lastPredictionPayload" in js
        assert "if (AppState.isPredicting) return;" in js
        assert "form.requestSubmit()" in js

    def test_app_js_handles_unknown_status_safely(self, client):
        """Verify unexpected or unknown status string degrades safely without runtime exception."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "STATUS - ${res.status || 'UNAVAILABLE'}" in js
        assert "Inference could not be completed. Status: ${res.status || 'UNKNOWN'}" in js

    def test_evidence_aligned_statistical_disclaimer(self, client):
        """Verify index.html disclaimer contains evidence-aligned wording without misleading p > 0.34 claims."""
        resp = client.get("/ui")
        assert resp.status_code == 200
        html = resp.text

        # Evidence-aligned text
        assert "Reported holdout comparisons did not establish a statistically significant improvement." in html
        assert "Raw model probabilities are uncalibrated and performed worse than the constant 0.50 probability baseline on the reported holdout Brier-score comparison" in html
        assert "Brier 0.2556" in html
        assert "reference Brier 0.2500" in html
        # Universal misleading claim must be absent
        assert "p > 0.34" not in html

    def test_observed_quote_distinction_disclaimers(self, client):
        """Verify observed price is never presented as a forecast."""
        resp = client.get("/ui")
        assert resp.status_code == 200
        html = resp.text

        assert "HISTORICAL OBSERVED FACT" in html
        assert "FORWARD DIRECTIONAL FORECAST" in html
        assert "Target Price: Unsupported / Not Modeled" in html
        assert "Price Type: LAST_TRADED_PRICE" in html
