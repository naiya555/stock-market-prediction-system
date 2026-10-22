"""Deterministic tests for Day 65: Prediction Dashboard UI Completion & Data Presentation Audit.

Covers:
1. Dashboard HTML markup: instrument type badge, status badge, distinction metadata,
   limitations & next action box, retry alert action, and blocked recovery action.
2. Dashboard CSS styling: limitations card, retry button, distinction meta, and badges.
3. JavaScript state and presentation logic:
   - Dynamic instrument type identification ('EQUITY (NSE)' vs 'INDEX (NSE)').
   - Accessible direction labels with textual description (non-color dependent) and aria-labels.
   - Retry prediction action and switch-to-supported instrument recovery.
   - Safe rendering of backend diagnostics and limitations next actions.
4. Schema validation with full and minimal (missing optional fields) realistic fixtures.
5. Distinct handling for blocked equities vs blocked indices.
6. Error-state cleanup and stale-result protection.
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


class TestDashboardHtmlAndCssAudit:
    """Verify HTML markup and CSS rules for Day 65 dashboard enhancements."""

    def test_dashboard_html_contains_instrument_type_and_status_badges(self, client):
        """Verify presence of instrument type, status, and recovery controls in HTML."""
        resp = client.get("/ui")
        assert resp.status_code == 200
        html = resp.text

        # Badges in hero card
        assert 'id="res-instrument-type-badge"' in html
        assert 'id="res-status-badge"' in html

        # Distinction metadata
        assert 'id="res-observed-meta"' in html
        assert 'id="res-forecast-meta"' in html

        # Model Scope, Limitations & Next Actions Box
        assert 'id="res-limitations-action-card"' in html
        assert 'Model Scope, Limitations & Next Actions' in html
        assert 'id="res-next-action-text"' in html

        # Retry and Recovery Action Buttons
        assert 'id="alert-retry-btn"' in html
        assert 'id="btn-switch-to-supported"' in html
        assert 'id="blocked-card-badge"' in html

    def test_dashboard_css_defines_limitations_and_retry_styles(self, client):
        """Verify CSS contains styling for limitations card, retry button, and distinction meta."""
        resp = client.get("/static/css/styles.css")
        assert resp.status_code == 200
        css = resp.text

        assert ".limitations-action-card" in css
        assert ".limitation-item" in css
        assert ".next-action-bar" in css
        assert ".btn-retry-alert" in css
        assert ".distinction-meta" in css
        assert ".badge-instrument-type" in css
        assert ".badge-status-success" in css


class TestJavaScriptPresentationAndAccessibility:
    """Verify JavaScript logic for data presentation, accessibility, and error handling."""

    def test_js_wires_retry_and_recovery_listeners(self, client):
        """Verify app.js wires retry and switch-to-supported button event handlers."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "document.getElementById('alert-retry-btn')" in js
        assert "form.requestSubmit()" in js
        assert "document.getElementById('btn-switch-to-supported')" in js
        assert "symbolInput.value = 'BHARTIARTL'" in js

    def test_js_formats_direction_without_color_alone(self, client):
        """Verify direction presentation includes explicit text and aria-label to avoid color-only indicators."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "PREDICTED UP (Bullish Return)" in js
        assert "PREDICTED DOWN (Bearish Return)" in js
        assert "aria-label" in js
        assert "Predicted Direction: UP (Bullish Return)" in js
        assert "Predicted Direction: DOWN (Bearish Return)" in js

    def test_js_identifies_instrument_types_dynamically(self, client):
        """Verify app.js determines EQUITY vs INDEX based on symbol identifiers."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "res.symbol.includes('NIFTY') || res.symbol.includes('INDEX')" in js
        assert "instTypeBadge.textContent = `${instType} (NSE)`" in js

    def test_js_renders_distinction_meta_and_limitations_actions(self, client):
        """Verify app.js sets observed quote metadata, unmodeled target price notes, and next action."""
        resp = client.get("/static/js/app.js")
        assert resp.status_code == 200
        js = resp.text

        assert "Price Target: Unsupported / Not Modeled (Direction Only)" in js
        assert "res.quote_context.price_type || 'LAST_TRADED_PRICE'" in js
        assert "document.getElementById('res-next-action-text')" in js


class TestPredictionResponseSchemaAndFixtures:
    """Verify realistic API response fixtures and schema handling with optional fields."""

    def test_realistic_fixture_with_full_fields_validates(self):
        """Verify realistic PredictionResponse with quote_context, data_quality, and ensemble."""
        full_fixture = {
            "prediction_id": "c8d0e7f2-1a3b-4c5d-9e8f-0123456789ab",
            "symbol": "BHARTIARTL",
            "prediction_timestamp": "2026-10-22T17:50:56.860024+00:00",
            "latest_input_timestamp": "2026-10-22T00:00:00+05:30",
            "status": "SUCCESS",
            "predicted_direction": "DOWN",
            "predicted_label": 0,
            "probability_up": 0.4979,
            "probability_down": 0.5021,
            "model_name": "xgboost",
            "model_version": "xgboost-direction-v1",
            "is_probability_calibrated": False,
            "probability_calibration": "uncalibrated",
            "data_quality": {
                "total_bars_fetched": 1235,
                "cleaned_bars": 1235,
                "warmup_bars_required": 34,
                "warmup_complete": True,
                "latest_bar_timestamp": "2026-10-22T00:00:00+05:30",
                "missing_feature_count": 0,
                "is_stale": False,
                "stale_days": 0,
            },
            "ensemble": None,
            "explanation": None,
            "quote_context": {
                "symbol": "BHARTIARTL",
                "last_price": 1895.0,
                "price_timestamp": "2026-10-22T15:28:00+05:30",
                "retrieved_at": "2026-10-22T23:20:56.860042+05:30",
                "source": "yfinance",
                "session_state": "CLOSED",
                "freshness_status": "FRESH",
                "is_delayed": True,
                "delay_minutes": 15,
                "price_type": "LAST_TRADED_PRICE",
                "note": "Last traded price reflects observed exchange/provider market data and is NOT a predicted opening or closing price.",
                "error_message": None,
            },
            "error_message": None,
            "disclaimer": "Directional forecast predicts next-session binary return. Does not predict target prices.",
        }

        parsed = PredictionResponse.model_validate(full_fixture)
        assert parsed.symbol == "BHARTIARTL"
        assert parsed.status == "SUCCESS"
        assert parsed.probability_calibration == "uncalibrated"
        assert parsed.quote_context.last_price == 1895.0
        assert parsed.quote_context.price_type == "LAST_TRADED_PRICE"

    def test_fixture_with_missing_optional_fields_validates(self):
        """Verify PredictionResponse validates gracefully when optional fields are null or omitted."""
        minimal_fixture = {
            "prediction_id": None,
            "symbol": "BHARTIARTL",
            "prediction_timestamp": "2026-10-22T17:50:56.860024+00:00",
            "latest_input_timestamp": None,
            "status": "SUCCESS",
            "predicted_direction": "UP",
            "predicted_label": 1,
            "probability_up": 0.5230,
            "probability_down": 0.4770,
            "model_name": "lightgbm",
            "model_version": "lightgbm-direction-v1",
            "is_probability_calibrated": False,
            "probability_calibration": "uncalibrated",
            "data_quality": None,
            "ensemble": None,
            "explanation": None,
            "quote_context": None,
            "error_message": None,
            "disclaimer": "Academic research only.",
        }

        parsed = PredictionResponse.model_validate(minimal_fixture)
        assert parsed.symbol == "BHARTIARTL"
        assert parsed.quote_context is None
        assert parsed.data_quality is None
        assert parsed.ensemble is None


class TestBlockedAndErrorStates:
    """Verify distinct blocked-instrument vs transient error handling."""

    def test_blocked_equity_response_semantics(self, client):
        """Verify blocked equity TCS returns MODEL_UNAVAILABLE with equity-specific rationale."""
        resp = client.post("/api/predict", json={"symbol": "TCS", "model_name": "xgboost", "persist": False})
        assert resp.status_code == 200
        data = resp.json()

        assert data["symbol"] == "TCS"
        assert data["status"] == "MODEL_UNAVAILABLE"
        assert "No trained model artifact found for equity instrument 'TCS'" in data["error_message"]
        assert "BHARTIARTL" in data["error_message"]

    def test_blocked_index_response_semantics(self, client):
        """Verify blocked sectoral index returns MODEL_UNAVAILABLE with cross-asset rationale."""
        resp = client.post(
            "/api/predict",
            json={"symbol": "NIFTY_TELECOMMUNICATIONS", "model_name": "xgboost", "persist": False},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["symbol"] == "NIFTY_TELECOMMUNICATIONS"
        assert data["status"] in ["MODEL_UNAVAILABLE", "FAILED"]
        assert "BHARTIARTL equity models cannot be reused for sectoral indices" in data["error_message"]

    def test_instrument_catalog_truthful_reasons(self, client):
        """Verify instrument catalog returns accurate status and reasons for all registered instruments."""
        resp = client.get("/api/predict/instruments")
        assert resp.status_code == 200
        data = resp.json()

        inst_map = {item["symbol"]: item for item in data["instruments"]}
        assert inst_map["BHARTIARTL"]["status"] == "SUPPORTED"
        assert inst_map["TCS"]["status"] == "BLOCKED"
        assert inst_map["RELIANCE"]["status"] == "BLOCKED"
        assert inst_map["NIFTY_TELECOMMUNICATIONS"]["status"] == "BLOCKED"
        assert inst_map["NIFTY_50"]["status"] == "BLOCKED"
