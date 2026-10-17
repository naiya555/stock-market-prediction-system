"""Automated Offline Test Suite for Frontend Web UI Integration (Phase 13 / Day 34).

Verifies:
1. Static asset delivery (index.html, styles.css, app.js) via FastAPI.
2. Content-negotiation on root route (serves HTML for browser, JSON for API clients).
3. Delivery of dedicated /ui route.
4. CORS headers on preflight and API requests.
5. DOM element integrity: ensures required interactive IDs and accessibility attributes exist.
6. API contract alignment: ensures frontend JavaScript consumes canonical API fields without fabrication.
"""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.api.app import STATIC_DIR, create_app


@pytest.fixture
def client() -> TestClient:
    """Provide a FastAPI TestClient configured with static assets."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_frontend_files_exist_on_disk():
    """Verify all required frontend source files exist in app/api/static."""
    assert STATIC_DIR.exists(), f"Static directory {STATIC_DIR} does not exist"
    index_file = STATIC_DIR / "index.html"
    css_file = STATIC_DIR / "css" / "styles.css"
    js_file = STATIC_DIR / "js" / "app.js"

    assert index_file.is_file(), "index.html not found"
    assert css_file.is_file(), "styles.css not found"
    assert js_file.is_file(), "app.js not found"

    assert index_file.stat().st_size > 500, "index.html appears truncated"
    assert css_file.stat().st_size > 500, "styles.css appears truncated"
    assert js_file.stat().st_size > 500, "app.js appears truncated"


def test_ui_route_serves_html(client: TestClient):
    """Verify GET /ui serves the HTML web dashboard with correct media type."""
    res = client.get("/ui")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    content = res.text

    # Verify essential title and semantic structure
    assert "Indian Stock Market Prediction System" in content
    assert "<nav" in content
    assert "<main" in content

    # Verify critical interactive element IDs for UI automation
    required_ids = [
        "symbol-input",
        "model-select",
        "prediction-form",
        "btn-run-prediction",
        "prediction-results-container",
        "tab-btn-predict",
        "tab-btn-history",
        "tab-btn-events",
        "tab-btn-health",
        "history-table",
        "events-cards-grid",
        "health-pill",
        "ml-weight-slider",
    ]
    for element_id in required_ids:
        assert f'id="{element_id}"' in content, f"Missing required DOM element id='{element_id}'"


def test_root_route_content_negotiation(client: TestClient):
    """Verify GET / serves HTML when browser sends text/html, but JSON when client requests JSON."""
    # 1. Browser-like request (Accept: text/html,...)
    browser_res = client.get("/", headers={"accept": "text/html,application/xhtml+xml"})
    assert browser_res.status_code == 200
    assert "text/html" in browser_res.headers.get("content-type", "")
    assert "<!DOCTYPE html>" in browser_res.text

    # 2. API client request (Accept: application/json)
    api_res = client.get("/", headers={"accept": "application/json"})
    assert api_res.status_code == 200
    assert "application/json" in api_res.headers.get("content-type", "")
    json_data = api_res.json()
    assert json_data["status"] == "running"
    assert json_data["ui"] == "/ui"


def test_static_css_served(client: TestClient):
    """Verify stylesheet is accessible under /static/css/styles.css with CSS MIME type."""
    res = client.get("/static/css/styles.css")
    assert res.status_code == 200
    assert "text/css" in res.headers.get("content-type", "")
    assert "--color-primary" in res.text
    assert "--color-up" in res.text
    assert "--color-down" in res.text


def test_static_js_served(client: TestClient):
    """Verify JavaScript client is accessible under /static/js/app.js with JS MIME type."""
    res = client.get("/static/js/app.js")
    assert res.status_code == 200
    assert "javascript" in res.headers.get("content-type", "")
    assert "ApiService" in res.text
    assert "renderPredictionResult" in res.text


def test_cors_headers_restricted(client: TestClient):
    """Verify CORS middleware allows trusted origins and rejects untrusted origins."""
    # 1. Allowed origin (e.g. localhost:3000)
    allowed_res = client.options(
        "/api/predict",
        headers={
            "origin": "http://localhost:3000",
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )
    assert allowed_res.status_code == 200
    assert allowed_res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    # Credentials must NOT be allowed with wildcard or unauthenticated public API
    assert allowed_res.headers.get("access-control-allow-credentials") is None

    # 2. Untrusted origin (e.g. evil.com)
    untrusted_res = client.options(
        "/api/predict",
        headers={
            "origin": "http://evil.com",
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )
    assert "access-control-allow-origin" not in untrusted_res.headers


def test_history_header_timezone_consistency():
    """Verify history table header specifies IST matching formatDateTimeIST output."""
    index_file = STATIC_DIR / "index.html"
    content = index_file.read_text(encoding="utf-8")
    assert '<th scope="col">Prediction Time (IST)</th>' in content
    assert '<th scope="col">Prediction Time (UTC)</th>' not in content


def test_safe_url_and_data_integrity_in_js():
    """Verify safe URL protocol validation and absence of invented data/defaults in JS."""
    js_file = STATIC_DIR / "js" / "app.js"
    content = js_file.read_text(encoding="utf-8")

    # 1. Safe URL validation protocol exists and is applied to event circular links
    assert "function isSafeHttpUrl(" in content
    assert "isSafeHttpUrl(ev.url)" in content

    # 2. No invented confidence or 50% fallbacks
    assert "|| 'MEDIUM'" not in content
    assert "probUp !== null ? res.probability_up : 0.5" not in content
    assert "res.ensemble.combined_direction || '--'" not in content


def test_frontend_template_no_hardcoded_demo_predictions():
    """Verify production HTML contains no hardcoded mock prices or fake forecast data."""
    index_file = STATIC_DIR / "index.html"
    content = index_file.read_text(encoding="utf-8")

    # Initial forecast values should be clean placeholders (e.g. '--')
    assert '<span class="bound-price" id="res-range-lower">₹--</span>' in content
    assert '<span class="bound-price" id="res-range-upper">₹--</span>' in content
    assert 'id="res-direction-text">--</span>' in content
    assert 'P(UP): 99.9%' not in content
    assert 'P(DOWN): 99.9%' not in content


def test_frontend_js_api_contract_parity():
    """Verify frontend JavaScript explicitly consumes the canonical API schema fields."""
    js_file = STATIC_DIR / "js" / "app.js"
    content = js_file.read_text(encoding="utf-8")

    # Required API endpoints
    assert "`${API_BASE}/health`" in content
    assert "`${API_BASE}/predict`" in content
    assert "`${API_BASE}/history" in content
    assert "`${API_BASE}/events" in content

    # Required Pydantic response fields mapping
    assert "res.predicted_direction" in content
    assert "res.probability_up" in content
    assert "res.probability_down" in content
    assert "res.data_quality" in content
    assert "res.ensemble" in content
    assert "res.ensemble.agreement_status" in content
    assert "res.ensemble.target_range" in content
    assert "res.ensemble.integrated_positive_factors" in content
    assert "res.ensemble.downside_risks" in content
    assert "res.ensemble.source_references" in content
    assert "res.ensemble.llm_direction" in content
    assert "res.ensemble.llm_confidence" in content
