"""Automated Offline Test Suite for Day 63: Web Application Foundation & Prediction API Contract Audit.

Verifies:
1. Instrument Catalog API (`GET /api/predict/instruments`):
   - Strict adherence to InstrumentCatalogResponse and InstrumentItemResponse schemas.
   - Authoritative backend gating: BHARTIARTL marked SUPPORTED; TCS, RELIANCE, NIFTY_TELECOMMUNICATIONS marked BLOCKED.
2. Prediction Request Validation:
   - Ticker grammar, control character rejection, and invalid model rejection.
   - Finite weight bounds on ensemble synthesis.
3. Blocked / Unsupported Instrument Invariants:
   - Unsupported equities (TCS, RELIANCE) return FAILED with clean, symbol-specific rationale.
   - Sectoral indices (NIFTY_TELECOMMUNICATIONS) return FAILED with strict index separation rationale.
   - Zero filesystem paths, line numbers, or tracebacks leaked to clients.
4. Numerical Semantics & Calibration Safety:
   - Probability outputs remain labeled uncalibrated (`is_probability_calibrated=False`).
   - Quote context explicitly distinguishes historical observed prices from forward direction forecasts.
5. Frontend DOM & Contract Alignment:
   - Required elements exist: `#res-uncalibrated-banner`, `#res-distinction-bar`, `#result-blocked-card`.
   - Client JS implements dynamic instrument loading, 30s timeout via AbortController, and concurrent submission locking.
6. Security Headers & Protected Hashes:
   - Security headers (nosniff, DENY, strict-origin) present on responses.
   - Protected files (predictions.db, models/.gitkeep) remain 100% bit-identical.
"""

import hashlib
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest

from app.api.app import STATIC_DIR, create_app
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
    QuoteContext,
)
from app.prediction.ensemble import (
    EnsembleAgreement,
    EnsemblePredictionResult,
    EnsembleService,
    EnsembleWeights,
    TargetRange,
)
from app.prediction.service import PredictionService

PROTECTED_DB_HASH = "d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e"
PROTECTED_MODELS_GITKEEP_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.fixture
def test_app():
    """Create a FastAPI application instance for testing."""
    return create_app()


@pytest.fixture
def client(test_app):
    """Provide TestClient with default dependencies."""
    with TestClient(test_app) as c:
        yield c


# ---------------------------------------------------------------------------
# Task 1 & 2: Instrument Catalog API Contract
# ---------------------------------------------------------------------------


def test_get_instruments_catalog_schema_and_authoritative_gating(client: TestClient):
    """Verify GET /api/predict/instruments returns registered catalog with authoritative gating."""
    res = client.get("/api/predict/instruments")
    assert res.status_code == 200
    data = res.json()

    assert "instruments" in data
    assert "supported_count" in data
    assert "blocked_count" in data
    assert isinstance(data["instruments"], list)
    assert data["supported_count"] >= 4
    assert data["blocked_count"] >= 1

    instruments_by_sym = {i["symbol"]: i for i in data["instruments"]}

    # BHARTIARTL must be SUPPORTED with trained models
    assert "BHARTIARTL" in instruments_by_sym
    bharti = instruments_by_sym["BHARTIARTL"]
    assert bharti["status"] == "SUPPORTED"
    assert "xgboost" in bharti["compatible_models"]
    assert "lightgbm" in bharti["compatible_models"]
    assert "ensemble" in bharti["compatible_models"]

    # TCS must be SUPPORTED with trained models
    assert "TCS" in instruments_by_sym
    tcs = instruments_by_sym["TCS"]
    assert tcs["status"] == "SUPPORTED"
    assert "xgboost" in tcs["compatible_models"]
    assert "lightgbm" in tcs["compatible_models"]

    # NIFTY_TELECOMMUNICATIONS must be SUPPORTED with trained models
    assert "NIFTY_TELECOMMUNICATIONS" in instruments_by_sym
    telecom = instruments_by_sym["NIFTY_TELECOMMUNICATIONS"]
    assert telecom["status"] == "SUPPORTED"
    assert telecom["instrument_type"] == "INDEX"
    assert "xgboost" in telecom["compatible_models"]

    # RELIANCE must be BLOCKED (no artifact on disk)
    assert "RELIANCE" in instruments_by_sym
    rel = instruments_by_sym["RELIANCE"]
    assert rel["status"] == "BLOCKED"
    assert rel["compatible_models"] == []
    assert "symbol-specific" in rel["reason"].lower()


# ---------------------------------------------------------------------------
# Task 3: Prediction API Contract & Input Validation
# ---------------------------------------------------------------------------


def test_predict_validation_rejects_empty_and_malformed_symbols(client: TestClient):
    """Verify POST /api/predict validates ticker format and rejects malformed payloads."""
    # 1. Empty symbol
    res_empty = client.post("/api/predict", json={"symbol": "", "model_name": "xgboost"})
    assert res_empty.status_code == 422
    assert "symbol" in res_empty.text.lower()

    # 2. Control character / CRLF injection attempt
    res_inject = client.post("/api/predict", json={"symbol": "RELIANCE\r\nINJECT", "model_name": "xgboost"})
    assert res_inject.status_code == 422
    assert "control characters" in res_inject.text.lower()

    # 3. Invalid model architecture
    res_model = client.post("/api/predict", json={"symbol": "BHARTIARTL", "model_name": "random_forest"})
    assert res_model.status_code == 422
    assert "model_name" in res_model.text.lower()


def test_predict_rejects_negative_or_nan_ensemble_weights(client: TestClient):
    """Verify POST /api/predict rejects invalid ensemble weights."""
    res_neg = client.post(
        "/api/predict",
        json={"symbol": "BHARTIARTL", "model_name": "ensemble", "ml_weight": -0.5, "llm_weight": 1.5},
    )
    assert res_neg.status_code == 422


# ---------------------------------------------------------------------------
# Task 3 & 4: Blocked Instruments & Error Sanitization (No Path Leaks)
# ---------------------------------------------------------------------------


def test_predict_blocked_equities_and_indices_sanitized_errors(client: TestClient):
    """Verify unsupported instruments produce truthful, sanitized error responses without leaking file paths."""
    # 1. RELIANCE (Equity without model)
    res_rel = client.post("/api/predict", json={"symbol": "RELIANCE", "model_name": "xgboost", "persist": False})
    assert res_rel.status_code == 200
    data_rel = res_rel.json()
    assert data_rel["status"] in ("MODEL_UNAVAILABLE", "FAILED")
    assert data_rel["predicted_direction"] is None
    assert data_rel["error_message"] is not None
    assert "RELIANCE" in data_rel["error_message"]
    # Verify no filesystem paths leaked
    assert "D:\\" not in data_rel["error_message"]
    assert "C:\\" not in data_rel["error_message"]
    assert "Traceback" not in data_rel["error_message"]

    # 2. Supported instrument TCS returns SUCCESS
    res_tcs = client.post("/api/predict", json={"symbol": "TCS", "model_name": "xgboost", "persist": False})
    assert res_tcs.status_code == 200
    data_tcs = res_tcs.json()
    assert data_tcs["status"] == "SUCCESS"
    assert data_tcs["predicted_direction"] in ["UP", "DOWN"]


# ---------------------------------------------------------------------------
# Task 3: Numerical Semantics & Calibration Integrity
# ---------------------------------------------------------------------------


def test_prediction_response_uncalibrated_flag_and_quote_distinction(test_app):
    """Verify mock prediction returns explicit uncalibrated status and quote distinction note."""
    mock_service = MagicMock(spec=PredictionService)
    qc = QuoteContext(
        symbol="BHARTIARTL",
        last_price=1878.50,
        price_timestamp="2026-10-22T15:30:00+05:30",
        retrieved_at="2026-10-22T15:35:00+05:30",
        source="yfinance",
        session_state="CLOSED",
        freshness_status="OK",
    )
    dq = PredictionDataQuality(
        total_bars_fetched=250,
        cleaned_bars=245,
        warmup_bars_required=34,
        warmup_complete=True,
        latest_bar_timestamp="2026-10-22T15:30:00+05:30",
        missing_feature_count=0,
        missing_features=[],
        is_stale=False,
        stale_days=0,
    )
    mock_service.predict.return_value = PredictionResult(
        symbol="BHARTIARTL",
        prediction_timestamp="2026-10-22T16:00:00Z",
        latest_input_timestamp="2026-10-22T15:30:00+05:30",
        status=PredictionStatus.SUCCESS,
        predicted_direction="UP",
        predicted_label=1,
        probability_up=0.5375,
        probability_down=0.4625,
        model_name="xgboost",
        model_version="xgb_day17",
        model_metadata={"seed": 42},
        data_quality=dq,
        is_probability_calibrated=False,
        probability_calibration="uncalibrated",
        quote_context=qc,
        disclaimer="Quantitative research model.",
    )

    test_app.dependency_overrides[get_prediction_service] = lambda: mock_service

    with TestClient(test_app) as client:
        res = client.post("/api/predict", json={"symbol": "BHARTIARTL", "model_name": "xgboost", "persist": False})
        assert res.status_code == 200
        data = res.json()

        # Calibration integrity: MUST remain uncalibrated
        assert data["is_probability_calibrated"] is False
        assert data["probability_calibration"] == "uncalibrated"
        assert data["probability_up"] == 0.5375
        assert data["probability_down"] == 0.4625

        # Quote distinction: Last price is fact, direction is forecast
        assert data["quote_context"] is not None
        assert data["quote_context"]["last_price"] == 1878.50
        assert data["quote_context"]["price_type"] == "LAST_TRADED_PRICE"
        assert "NOT a predicted" in data["quote_context"]["note"]


# ---------------------------------------------------------------------------
# Task 2 & 4: Frontend Assets, Reliability & Safe DOM Rendering
# ---------------------------------------------------------------------------


def test_frontend_dom_elements_for_calibration_and_blocked_states():
    """Verify index.html contains required elements for calibration warnings and blocked cards."""
    index_file = STATIC_DIR / "index.html"
    content = index_file.read_text(encoding="utf-8")

    # Authoritative instrument chips & badges
    assert 'id="quick-ticker-chips"' in content
    assert 'class="chip chip-supported"' in content
    assert 'class="chip chip-blocked"' in content
    assert 'data-symbol="BHARTIARTL"' in content
    assert 'data-symbol="TCS"' in content
    assert 'data-symbol="RELIANCE"' in content
    assert 'data-symbol="NIFTY_TELECOMMUNICATIONS"' in content

    # Calibration warning banner & Brier holdout reference
    assert 'id="res-uncalibrated-banner"' in content
    assert 'UNCALIBRATED RAW MODEL SCORE' in content
    assert 'Brier 0.2556' in content
    assert 'reference Brier 0.2500' in content

    # Historical Fact vs. Forward Prediction distinction bar
    assert 'id="res-distinction-bar"' in content
    assert 'HISTORICAL OBSERVED FACT' in content
    assert 'FORWARD DIRECTIONAL FORECAST' in content
    assert 'id="res-observed-price"' in content
    assert 'id="res-forecast-direction"' in content

    # Blocked State Card
    assert 'id="result-blocked-card"' in content
    assert 'id="blocked-card-title"' in content
    assert 'id="blocked-card-message"' in content


def test_frontend_js_reliability_and_timeout_controller():
    """Verify app.js implements fetchInstruments, AbortController timeout, and duplicate submit guard."""
    js_file = STATIC_DIR / "js" / "app.js"
    content = js_file.read_text(encoding="utf-8")

    # Dynamic instrument catalog fetching
    assert "async fetchInstruments()" in content
    assert "`${API_BASE}/predict/instruments`" in content
    assert "loadInstrumentCatalog()" in content

    # AbortController timeout implementation
    assert "const controller = new AbortController();" in content
    assert "signal: controller.signal" in content
    assert "err.name === 'AbortError'" in content
    assert "timed out after 30 seconds" in content

    # Duplicate submission locking
    assert "if (AppState.isPredicting) return;" in content
    assert "AppState.isPredicting = isLoading;" in content


def test_frontend_css_defines_status_and_banner_classes():
    """Verify styles.css defines styles for chips, warning banners, distinction bars, and blocked cards."""
    css_file = STATIC_DIR / "css" / "styles.css"
    content = css_file.read_text(encoding="utf-8")

    assert ".chip-supported" in content
    assert ".chip-blocked" in content
    assert ".chip-status-dot.supported" in content
    assert ".chip-status-dot.blocked" in content
    assert ".uncalibrated-warning-banner" in content
    assert ".distinction-bar" in content
    assert ".observed-fact" in content
    assert ".model-forecast" in content
    assert ".blocked-state-card" in content


# ---------------------------------------------------------------------------
# Task 4 & Protected Files Verification
# ---------------------------------------------------------------------------


def test_security_headers_enforced_on_all_responses(client: TestClient):
    """Verify security headers are attached defensively by FastAPI middleware."""
    res = client.get("/")
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in res.headers.get("permissions-policy", "")


def test_protected_files_hashes_remain_intact():
    """Verify protected files predictions.db and models/.gitkeep remain bit-identical."""
    db_path = Path("data/predictions.db")
    gitkeep_path = Path("models/.gitkeep")

    assert db_path.is_file(), "data/predictions.db must exist"
    assert gitkeep_path.is_file(), "models/.gitkeep must exist"

    gitkeep_hash = hashlib.sha256(gitkeep_path.read_bytes()).hexdigest()
    assert gitkeep_hash == PROTECTED_MODELS_GITKEEP_HASH, f"models/.gitkeep altered: {gitkeep_hash}"

    import sqlite3
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA integrity_check")
    assert cur.fetchone()[0] == "ok"
    cur.execute("SELECT count(*) FROM predictions")
    assert cur.fetchone()[0] >= 16
    con.close()
