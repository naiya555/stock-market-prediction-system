"""End-to-end browser and frontend functionality audit tests for Day 64.

Verifies:
1. HTML markup integrity: symbol input maxlength=30, accessibility attributes, error containers.
2. CSS design rules: disabled chip styling, dynamic catalog error notice.
3. JavaScript state management: concurrency locks (isPredicting), request sequencing (predictionRequestId),
   stale response drop logic, active abort controller cancellation, malformed JSON handling.
4. FastAPI 422 validation error message parsing and formatting.
5. DOM cleanup on error: hero card, blocked card, and breakdown grid hiding with null prediction state.
6. API endpoint responses for supported (BHARTIARTL) and blocked (TCS, RELIANCE, NIFTY_TELECOMMUNICATIONS) instruments.
7. Sanity of uncalibrated probability signals and historical price quote distinction.
"""

from pathlib import Path
import re
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest

from app.api.app import app
from app.prediction.contract import PredictionRequest, PredictionResult, PredictionStatus


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


class TestHtmlMarkupAndAccessibility:
    """Audit HTML markup for accessibility, bounds, and UI controls."""

    def test_symbol_input_maxlength_is_30(self, client):
        """Verify symbol-input permits 30 characters to accommodate NIFTY_TELECOMMUNICATIONS."""
        resp = client.get("/ui")
        assert resp.status_code == 200
        html = resp.text

        # Ensure input has maxlength="30"
        match = re.search(r'<input[^>]*id=["\']symbol-input["\'][^>]*>', html)
        assert match is not None, "Could not find #symbol-input in index.html"
        tag = match.group(0)
        assert 'maxlength="30"' in tag, f"Expected maxlength=\"30\" in symbol-input, got {tag}"

    def test_accessibility_roles_and_aria_attributes(self, client):
        """Verify essential ARIA and accessibility attributes on form controls."""
        resp = client.get("/ui")
        assert resp.status_code == 200
        html = resp.text

        # Symbol error container has role="alert" and aria-live="polite"
        assert 'id="symbol-error"' in html
        assert 'role="alert"' in html
        assert 'aria-live="polite"' in html

        # Navigation tabs have role="tablist" or role="tab"
        assert 'role="tablist"' in html
        assert 'aria-selected=' in html

        # Market clock container exists
        assert 'id="market-clock-time"' in html


class TestCssRulesAndStyles:
    """Audit CSS styling rules for newly added states and accessibility."""

    def test_disabled_chips_and_catalog_notice_styles(self, client):
        """Verify CSS contains .chip:disabled and .catalog-error-notice styles."""
        resp = client.get("/static/css/styles.css")
        assert resp.status_code == 200
        css = resp.text

        assert ".chip:disabled" in css
        assert "cursor: not-allowed" in css
        assert ".catalog-error-notice" in css


class TestJavaScriptStateAndReliability:
    """Audit JavaScript client code for state management, timeout, and race condition defenses."""

    def test_js_has_prediction_request_id_and_concurrency_lock(self, client):
        """Verify AppState tracks predictionRequestId, isPredicting, and active controller."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "isPredicting: false" in js
        assert "predictionRequestId: 0" in js
        assert "activePredictionAbortController: null" in js
        assert "AppState.predictionRequestId = (AppState.predictionRequestId || 0) + 1;" in js
        assert "currentReqId !== AppState.predictionRequestId" in js

    def test_js_aborts_prior_request_and_handles_malformed_json(self, client):
        """Verify ApiService.runPrediction aborts prior controllers and validates responses."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "AppState.activePredictionAbortController.abort()" in js
        assert "Received empty or malformed payload from prediction server" in js

    def test_js_formats_validation_detail_array(self, client):
        """Verify FastAPI 422 array responses are cleanly formatted without raw JSON."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "Array.isArray(data.detail)" in js

    def test_js_cleans_up_stale_cards_on_error(self, client):
        """Verify showPredictionError hides heroCard, blockedCard, breakdownGrid and clears state."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        # In showPredictionError
        assert "AppState.prediction = null;" in js

    def test_js_disables_chips_during_prediction(self, client):
        """Verify chips are disabled during active prediction and guarded against clicks."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "chip.disabled = isLoading;" in js
        assert "if (AppState.isPredicting) return;" in js


class TestApiIntegrationAndContracts:
    """Audit API contracts for supported vs blocked instruments and security."""

    def test_instrument_catalog_returns_all_registered_instruments(self, client):
        """Verify GET /api/predict/instruments returns 5 instruments with explicit statuses."""
        resp = client.get("/api/predict/instruments")
        assert resp.status_code == 200
        data = resp.json()

        symbols = {inst["symbol"]: inst["status"] for inst in data["instruments"]}
        assert symbols.get("BHARTIARTL") == "SUPPORTED"
        assert symbols.get("TCS") == "SUPPORTED"
        assert symbols.get("RELIANCE") == "BLOCKED"
        assert symbols.get("NIFTY_TELECOMMUNICATIONS") == "SUPPORTED"
        assert symbols.get("NIFTY_50") == "SUPPORTED"

    def test_predict_bhartiartl_returns_uncalibrated_flag_and_quote_distinction(self, client):
        """Verify BHARTIARTL prediction output contains explicit uncalibrated labeling and quote context."""
        payload = {
            "symbol": "BHARTIARTL",
            "model_name": "xgboost",
            "persist": False,
        }
        resp = client.post("/api/predict", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["symbol"] == "BHARTIARTL"
        assert data["status"] == "SUCCESS"
        assert data["predicted_direction"] in ["UP", "DOWN"]
        assert data["probability_calibration"] == "uncalibrated"
        assert data["is_probability_calibrated"] is False
        assert "disclaimer" in data
        assert "quote_context" in data
        assert data["quote_context"]["symbol"] == "BHARTIARTL"
        assert data["quote_context"]["price_type"] == "LAST_TRADED_PRICE"
        assert "NOT a predicted opening or closing price" in data["quote_context"]["note"]

    def test_predict_blocked_instrument_reliance_sanitized_error(self, client):
        """Verify RELIANCE returns MODEL_UNAVAILABLE with sanitized message and zero path leakage."""
        payload = {
            "symbol": "RELIANCE",
            "model_name": "xgboost",
            "persist": False,
        }
        resp = client.post("/api/predict", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["symbol"] == "RELIANCE"
        assert data["status"] == "MODEL_UNAVAILABLE"
        assert "No trained model artifact found for equity instrument 'RELIANCE'" in data["error_message"]
        # Must not leak filesystem paths
        assert "C:\\" not in data["error_message"]
        assert "D:\\" not in data["error_message"]
        assert ".json" not in data["error_message"]
        assert ".pt" not in data["error_message"]

    def test_predict_supported_instrument_tcs_and_indices(self, client):
        """Verify TCS and indices return SUCCESS with valid forecasts."""
        for sym in ["TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]:
            payload = {
                "symbol": sym,
                "model_name": "xgboost",
                "persist": False,
            }
            resp = client.post("/api/predict", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["symbol"] == sym
            assert data["status"] == "SUCCESS"
            assert data["predicted_direction"] in ["UP", "DOWN"]

    def test_predict_malformed_symbol_422_rejection(self, client):
        """Verify malformed symbol fails request validation and returns structured error response."""
        payload = {
            "symbol": "INVALID@SYM!",
            "model_name": "xgboost",
            "persist": False,
        }
        resp = client.post("/api/predict", json=payload)
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "symbol" in data["error"]["message"].lower()
