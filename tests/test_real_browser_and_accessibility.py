"""Deterministic regression and behavioral tests for Day 67.

Real Browser Interaction & Accessibility Audit.

Verifies:
1. Browser runtime discovery (Chrome or Edge presence on host).
2. Bug fix verification: fillEl, probUpEl, and probDownEl variable declarations in app.js.
3. Accessibility: Explicit <label for="..."> associations for all form inputs.
4. Accessibility: Non-color cues for direction (arrows and textual returns).
5. Accessibility: ARIA roles, landmarks, and live regions.
6. Responsive CSS: Media queries and max-width bounds preventing horizontal overflow.
7. Diagnostic recovery: One-click switch-to-supported button contract in HTML and JS.
8. Concurrency guard: Button disable and AppState.isPredicting state invariants.
9. Fast API TestClient contract: UI serving, static assets, catalog, and prediction endpoint.
"""

from pathlib import Path
import re

from fastapi.testclient import TestClient
import pytest

from app.api.app import app
from scripts.verify_real_browser import find_browser_executable


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


class TestBrowserAndAccessibilityAudit:
    """Test suite for Day 67 real browser interaction & accessibility audit."""

    def test_browser_runtime_discovery(self):
        """Verify that a supported browser runtime (Chrome or Edge) is discovered locally."""
        exe = find_browser_executable()
        assert Path(exe).is_file(), f"Discovered executable '{exe}' is not a valid file."
        assert any(b in exe.lower() for b in ("chrome.exe", "msedge.exe")), f"Unexpected browser '{exe}'."

    def test_variable_declaration_bugfix_in_app_js(self):
        """Verify the bug fix: fillEl, probUpEl, and probDownEl are explicitly declared."""
        app_js_path = Path("app/api/static/js/app.js")
        assert app_js_path.is_file()
        content = app_js_path.read_text(encoding="utf-8")

        # Must explicitly declare fillEl, probUpEl, probDownEl
        assert "const fillEl = document.getElementById('res-probability-fill');" in content
        assert "const probUpEl = document.getElementById('res-prob-up');" in content
        assert "const probDownEl = document.getElementById('res-prob-down');" in content

    def test_accessible_form_labels_association(self):
        """Verify every form input in the prediction form has an explicit associated label."""
        html_path = Path("app/api/static/index.html")
        assert html_path.is_file()
        content = html_path.read_text(encoding="utf-8")

        # Verify symbol-input label
        assert '<label for="symbol-input"' in content
        assert 'id="symbol-input"' in content

        # Verify model-select label
        assert '<label for="model-select"' in content
        assert 'id="model-select"' in content

    def test_non_color_direction_cues(self):
        """Verify prediction directions use icons and descriptive text, never color alone."""
        app_js_path = Path("app/api/static/js/app.js")
        content = app_js_path.read_text(encoding="utf-8")

        # Verify directional arrow icons
        assert "dirIcon.textContent = '↗';" in content
        assert "dirIcon.textContent = '↘';" in content
        assert "dirIcon.textContent = '⏸';" in content

        # Verify unambiguous return text
        assert "PREDICTED UP (Bullish Return)" in content
        assert "PREDICTED DOWN (Bearish Return)" in content
        assert "dirBadge.setAttribute('aria-label'" in content

    def test_aria_landmarks_and_live_regions(self):
        """Verify semantic regions, alerts, and live regions exist for assistive tech."""
        html_path = Path("app/api/static/index.html")
        content = html_path.read_text(encoding="utf-8")

        # Live regions and alert roles
        assert 'role="alert"' in content
        assert 'aria-live="polite"' in content
        assert 'aria-describedby="symbol-error"' in content
        assert 'id="symbol-error"' in content

    def test_responsive_css_media_queries(self):
        """Verify CSS contains responsive layout media queries preventing horizontal overflow."""
        css_path = Path("app/api/static/css/styles.css")
        assert css_path.is_file()
        content = css_path.read_text(encoding="utf-8")

        # Check for responsive breakpoints and mobile adaptations
        assert "@media (max-width: 768px)" in content
        assert "box-sizing: border-box" in content
        assert "flex-direction: column" in content

    def test_switch_to_supported_recovery_action(self):
        """Verify the one-click recovery button contract in HTML and JavaScript."""
        html_path = Path("app/api/static/index.html")
        html_content = html_path.read_text(encoding="utf-8")
        assert 'id="btn-switch-to-supported"' in html_content

        app_js_path = Path("app/api/static/js/app.js")
        js_content = app_js_path.read_text(encoding="utf-8")
        assert "document.getElementById('btn-switch-to-supported')" in js_content
        assert "symbolInput.value = 'BHARTIARTL';" in js_content

    def test_concurrency_double_submission_guard(self):
        """Verify prediction submission disables button and activates loading state."""
        app_js_path = Path("app/api/static/js/app.js")
        content = app_js_path.read_text(encoding="utf-8")

        # Concurrency lock
        assert "if (AppState.isPredicting) return;" in content
        assert "AppState.isPredicting = true;" in content
        assert "setPredictionLoading(true);" in content
        assert "btn.disabled = isLoading;" in content

    def test_ui_and_static_asset_serving(self, client):
        """Verify FastAPI correctly serves UI dashboard and static CSS/JS assets."""
        resp_ui = client.get("/ui")
        assert resp_ui.status_code == 200
        assert "text/html" in resp_ui.headers["content-type"]
        assert "Indian Stock Market Prediction System" in resp_ui.text

        resp_css = client.get("/static/css/styles.css")
        assert resp_css.status_code == 200

        resp_js = client.get("/static/js/app.js")
        assert resp_js.status_code == 200
        assert "renderPredictionResult" in resp_js.text

    def test_catalog_endpoint_integrity(self, client):
        """Verify catalog endpoint provides authoritative instrument statuses."""
        resp = client.get("/api/predict/instruments")
        assert resp.status_code == 200
        data = resp.json()
        assert "instruments" in data
        instruments = {i["symbol"]: i for i in data["instruments"]}

        assert instruments["BHARTIARTL"]["status"] == "SUPPORTED"
        assert instruments["TCS"]["status"] == "BLOCKED"
        assert instruments["RELIANCE"]["status"] == "BLOCKED"
        assert instruments["NIFTY_50"]["status"] == "BLOCKED"
        assert instruments["NIFTY_TELECOMMUNICATIONS"]["status"] == "BLOCKED"
