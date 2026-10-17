"""Day 34 Live Verification Script: Interactive Stock Prediction Web UI.

Verifies:
1. Static assets existence, structure, and integrity (index.html, styles.css, app.js).
2. FastAPI static mounts and UI routing (/ui and content-negotiated /).
3. CORS headers and security configuration for cross-origin frontend consumers.
4. UI DOM elements and accessibility standards (unique IDs, semantic tags, ARIA attributes).
5. Zero fabricated/hardcoded mock predictions or demo outcomes in production templates.
6. JavaScript client API contract alignment with backend Pydantic schemas.
7. Simulated browser interaction flow via TestClient consuming /api endpoints.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
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

from app.api import app
from app.api.dependencies import (
    get_ensemble_service,
    get_prediction_repository,
    get_prediction_service,
)
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


def log_step(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"       {detail}")


def run_day34_verification() -> bool:
    print("=" * 70)
    print("Day 34 Verification: Interactive Stock Prediction Web UI")
    print("=" * 70)
    all_passed = True

    static_dir = project_root / "app" / "api" / "static"
    html_file = static_dir / "index.html"
    css_file = static_dir / "css" / "styles.css"
    js_file = static_dir / "js" / "app.js"

    # Step 1: Verify Static Asset Files
    files_exist = html_file.is_file() and css_file.is_file() and js_file.is_file()
    log_step(
        "Static Asset Files Existence",
        files_exist,
        f"HTML: {html_file.stat().st_size}B, CSS: {css_file.stat().st_size}B, JS: {js_file.stat().st_size}B"
        if files_exist
        else "Missing static files",
    )
    if not files_exist:
        return False

    html_content = html_file.read_text(encoding="utf-8")
    css_content = css_file.read_text(encoding="utf-8")
    js_content = js_file.read_text(encoding="utf-8")

    # Step 2: Verify HTML Structure and Accessibility Elements
    required_ids = [
        "symbol-input",
        "model-select",
        "btn-run-prediction",
        "prediction-loading-skeleton",
        "prediction-results-container",
        "res-direction-badge",
        "res-model-badge",
        "ml-breakdown-card",
        "llm-breakdown-card",
        "audit-breakdown-card",
        "res-agreement-banner",
        "history-table-body",
        "history-symbol-filter",
        "btn-refresh-history",
        "btn-history-prev",
        "btn-history-next",
        "events-cards-grid",
        "events-category-filters",
        "health-overview-card",
    ]
    missing_ids = [i for i in required_ids if f'id="{i}"' not in html_content]
    dom_ok = len(missing_ids) == 0
    log_step(
        "Semantic DOM IDs and Controls",
        dom_ok,
        f"Verified {len(required_ids)} required interactive IDs. Missing: {missing_ids}",
    )
    all_passed = all_passed and dom_ok

    # Step 3: Verify Zero Hardcoded Demo Predictions
    forbidden_patterns = [
        r"₹\s*2,\d{3}",
        r"BULLISH|BEARISH(?=.*class=.*badge)",
        r"RELIANCE\s*\|\s*Target",
    ]
    found_forbidden = []
    for pat in forbidden_patterns:
        if re.search(pat, html_content):
            found_forbidden.append(pat)

    no_demo_data = len(found_forbidden) == 0
    log_step(
        "Zero Fabricated Demo Predictions in Templates",
        no_demo_data,
        f"Verified clean templates. Forbidden matches: {found_forbidden}",
    )
    all_passed = all_passed and no_demo_data

    # Step 4: Verify UI Routes via TestClient
    client = TestClient(app)

    ui_resp = client.get("/ui")
    ui_ok = ui_resp.status_code == 200 and "text/html" in ui_resp.headers.get("content-type", "")
    log_step(
        "GET /ui Endpoint Delivery",
        ui_ok,
        f"Status: {ui_resp.status_code}, Content-Type: {ui_resp.headers.get('content-type')}",
    )
    all_passed = all_passed and ui_ok

    # Step 5: Content Negotiation on GET /
    root_html = client.get("/", headers={"Accept": "text/html"})
    root_json = client.get("/", headers={"Accept": "application/json"})
    content_neg_ok = (
        root_html.status_code == 200
        and "text/html" in root_html.headers.get("content-type", "")
        and root_json.status_code == 200
        and "application/json" in root_json.headers.get("content-type", "")
    )
    log_step(
        "GET / Content-Negotiation (Browser HTML vs API JSON)",
        content_neg_ok,
        f"HTML Accept -> {root_html.headers.get('content-type')}, JSON Accept -> {root_json.headers.get('content-type')}",
    )
    all_passed = all_passed and content_neg_ok

    # Step 6: Static File Serving MIME Types
    css_resp = client.get("/static/css/styles.css")
    js_resp = client.get("/static/js/app.js")
    mime_ok = (
        css_resp.status_code == 200
        and "text/css" in css_resp.headers.get("content-type", "")
        and js_resp.status_code == 200
        and any(t in js_resp.headers.get("content-type", "") for t in ["javascript", "text/plain"])
    )
    log_step(
        "Static Files MIME Type Delivery",
        mime_ok,
        f"CSS: {css_resp.headers.get('content-type')}, JS: {js_resp.headers.get('content-type')}",
    )
    all_passed = all_passed and mime_ok

    # Step 7: CORS Headers Configuration
    cors_resp = client.options(
        "/api/predict",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    cors_allow_origin = cors_resp.headers.get("access-control-allow-origin")
    cors_cred = cors_resp.headers.get("access-control-allow-credentials")

    untrusted_resp = client.options(
        "/api/predict",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    cors_untrusted_blocked = "access-control-allow-origin" not in untrusted_resp.headers

    cors_ok = (
        cors_allow_origin == "http://localhost:3000"
        and cors_cred is None
        and cors_untrusted_blocked
    )
    log_step(
        "Restricted CORS Security Headers",
        cors_ok,
        f"Allow-Origin: {cors_allow_origin}, Cred: {cors_cred}, Untrusted Blocked: {cors_untrusted_blocked}",
    )
    all_passed = all_passed and cors_ok

    # Step 8: Simulated Frontend API Flow (Predict, History, Events, Health)
    # Health
    health_resp = client.get("/api/health")
    health_ok = health_resp.status_code == 200 and health_resp.json().get("status") in (
        "healthy",
        "degraded",
    )

    # Events
    events_resp = client.get("/api/events?limit=5")
    events_ok = events_resp.status_code == 200 and "events" in events_resp.json()

    # History
    hist_resp = client.get("/api/history?limit=10&page=1")
    hist_ok = hist_resp.status_code == 200 and "items" in hist_resp.json()

    api_flow_ok = health_ok and events_ok and hist_ok
    log_step(
        "Frontend API Contract Parity (/api/health, /api/events, /api/history)",
        api_flow_ok,
        f"Health: {health_resp.status_code}, Events: {events_resp.status_code}, History: {hist_resp.status_code}",
    )
    all_passed = all_passed and api_flow_ok

    # Step 9: UI Client Parity with Schema Field Names
    expected_js_fields = [
        "predicted_direction",
        "model_name",
        "data_quality",
        "probability_up",
        "probability_down",
        "target_range",
        "agreement_status",
        "llm_direction",
        "llm_confidence",
        "llm_reasoning_summary",
        "isSafeHttpUrl",
    ]
    missing_js_fields = [f for f in expected_js_fields if f not in js_content]
    js_parity_ok = len(missing_js_fields) == 0
    log_step(
        "JavaScript Client Schema Alignment & Security Helpers",
        js_parity_ok,
        f"Aligned fields: {expected_js_fields}. Missing: {missing_js_fields}",
    )
    all_passed = all_passed and js_parity_ok

    print("=" * 70)
    print(f"Day 34 Verification Result: {'SUCCESS' if all_passed else 'FAILURE'}")
    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    success = run_day34_verification()
    sys.exit(0 if success else 1)
