"""Automated Offline Test Suite for Phase 13 FastAPI REST API.

Tests API route contracts, input validation, dependency injection overrides,
offline mock services, SQLite repository persistence, and error handling.
Does NOT require network access or live Ollama inference.
"""

from datetime import datetime, timezone
import sqlite3
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest

from app.api.app import create_app
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
from app.events.providers.base import BaseEventProvider, EventProviderError
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
    EnsembleWeights,
    TargetRange,
)
from app.prediction.service import PredictionService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def in_memory_db() -> sqlite3.Connection:
    """Create a pristine, schema-initialized in-memory SQLite connection."""
    conn = create_connection(":memory:")
    initialize_database(conn)
    return conn


@pytest.fixture
def test_repo(in_memory_db: sqlite3.Connection) -> PredictionRepository:
    """Provide a PredictionRepository bound to an in-memory database."""
    return PredictionRepository(conn=in_memory_db)


@pytest.fixture
def mock_prediction_service() -> MagicMock:
    """Mock PredictionService for offline unit testing."""
    service = MagicMock(spec=PredictionService)
    return service


@pytest.fixture
def mock_ensemble_service() -> MagicMock:
    """Mock EnsembleService for offline unit testing."""
    service = MagicMock(spec=EnsembleService)
    return service


@pytest.fixture
def dummy_prediction_result() -> PredictionResult:
    """Create a realistic sample PredictionResult."""
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
    return PredictionResult(
        symbol="RELIANCE",
        prediction_timestamp="2026-10-17T09:00:00Z",
        latest_input_timestamp="2026-10-16T15:30:00+05:30",
        status=PredictionStatus.SUCCESS,
        predicted_direction="UP",
        predicted_label=1,
        probability_up=0.68,
        probability_down=0.32,
        model_name="xgboost",
        model_version="xgb_v1_day17",
        model_metadata={"n_estimators": 100},
        data_quality=dq,
        is_probability_calibrated=False,
        probability_calibration="uncalibrated",
        expected_movement=None,
        expected_movement_status="UNSUPPORTED",
        error_message=None,
        disclaimer="Standard research disclaimer.",
    )


@pytest.fixture
def dummy_ensemble_result(dummy_prediction_result: PredictionResult) -> EnsemblePredictionResult:
    """Create a realistic sample EnsemblePredictionResult."""
    llm_res = LLMReasoningResult(
        symbol="RELIANCE",
        direction=LLMDirection.UP,
        reasoning_summary="Solid refining margins and positive regulatory tailwinds.",
        positive_factors=["Strong quarterly performance", "Regulatory clarity"],
        negative_factors=["Crude volatility"],
        downside_risks=["Geopolitical supply disruption"],
        source_references=["RBI policy circular Oct 2026"],
        confidence_assessment="HIGH",
        model_version="gemma3:12b",
    )
    return EnsemblePredictionResult(
        symbol="RELIANCE",
        prediction_timestamp="2026-10-17T09:00:00Z",
        latest_input_timestamp="2026-10-16T15:30:00+05:30",
        status=PredictionStatus.SUCCESS,
        combined_direction="UP",
        combined_label=1,
        combined_probability_up=0.74,
        combined_probability_down=0.26,
        agreement_status=EnsembleAgreement.STRONG_AGREEMENT,
        weights_used={"ml": 0.70, "llm": 0.30},
        ml_prediction=dummy_prediction_result,
        llm_reasoning=llm_res,
        sentiment_summary=None,
        integrated_positive_factors=("Strong quarterly performance", "Positive momentum"),
        integrated_negative_factors=("Crude volatility",),
        downside_risks=("Geopolitical supply disruption",),
        source_references=("RBI policy circular Oct 2026",),
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


class StubEventProvider(BaseEventProvider):
    """Stub event provider for deterministic API testing."""

    def __init__(self, name: str, events: List[MacroEvent], fail: bool = False):
        self._name = name
        self._events = events
        self._fail = fail

    @property
    def name(self) -> str:
        return self._name

    def fetch_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[MacroEvent]:
        if self._fail:
            raise EventProviderError(f"Simulated failure in provider '{self._name}'")
        return self._events[:limit]


@pytest.fixture
def client(
    in_memory_db: sqlite3.Connection,
    test_repo: PredictionRepository,
    mock_prediction_service: MagicMock,
    mock_ensemble_service: MagicMock,
) -> TestClient:
    """Create a FastAPI TestClient with mocked/in-memory dependencies."""
    app = create_app()

    # Wire overrides
    app.dependency_overrides[get_db_connection] = lambda: in_memory_db
    app.dependency_overrides[get_prediction_repository] = lambda: test_repo
    app.dependency_overrides[get_prediction_service] = lambda: mock_prediction_service
    app.dependency_overrides[get_ensemble_service] = lambda: mock_ensemble_service
    app.dependency_overrides[get_event_providers] = lambda: []

    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_root_endpoint(client: TestClient):
    """Verify root endpoint returns system metadata and docs links."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert "name" in data
    assert data["status"] == "running"
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/health"


def test_health_endpoint_healthy(client: TestClient):
    """Verify health endpoint reports healthy with operating dependencies."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "database" in data["dependencies"]
    assert data["dependencies"]["database"]["status"] == "ok"
    assert data["dependencies"]["llm"]["status"] == "configured"
    # Ensure no secrets or credentials leaked
    assert "password" not in res.text.lower()
    assert "secret" not in res.text.lower()


def test_health_endpoint_db_failure():
    """Verify health endpoint reports 503 degraded when database connectivity fails."""
    app = create_app()
    broken_conn = MagicMock()
    broken_conn.execute.side_effect = sqlite3.OperationalError("Database disk image is malformed")

    broken_repo = MagicMock()
    broken_repo.connection = broken_conn

    app.dependency_overrides[get_prediction_repository] = lambda: broken_repo

    with TestClient(app) as test_client:
        res = test_client.get("/api/health")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["database"]["status"] == "unreachable"


def test_predict_validation_invalid_symbol(client: TestClient):
    """Verify empty or whitespace symbol triggers 422 Unprocessable Entity."""
    res = client.post("/api/predict", json={"symbol": "  ", "model_name": "xgboost"})
    assert res.status_code == 422
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_predict_validation_invalid_model(client: TestClient):
    """Verify unsupported model name triggers 422 validation error."""
    res = client.post("/api/predict", json={"symbol": "TCS", "model_name": "catboost_v9"})
    assert res.status_code == 422


def test_predict_validation_insufficient_lookback(client: TestClient):
    """Verify lookback_days < 35 triggers 422 validation error."""
    res = client.post("/api/predict", json={"symbol": "TCS", "lookback_days": 10})
    assert res.status_code == 422


def test_predict_standalone_ml_success(
    client: TestClient,
    mock_prediction_service: MagicMock,
    dummy_prediction_result: PredictionResult,
    test_repo: PredictionRepository,
):
    """Verify standalone ML prediction executes and returns structured response."""
    mock_prediction_service.predict.return_value = dummy_prediction_result

    payload = {
        "symbol": "RELIANCE",
        "model_name": "xgboost",
        "persist": True,
    }
    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["symbol"] == "RELIANCE"
    assert data["status"] == "SUCCESS"
    assert data["predicted_direction"] == "UP"
    assert data["probability_up"] == 0.68
    assert data["model_name"] == "xgboost"
    assert data["prediction_id"] is not None
    assert data["data_quality"]["cleaned_bars"] == 245
    assert data["ensemble"] is None

    # Verify persisted in database
    persisted = test_repo.get_prediction(data["prediction_id"])
    assert persisted is not None
    assert persisted["symbol"] == "RELIANCE"


def test_predict_standalone_ml_failure_status(
    client: TestClient,
    mock_prediction_service: MagicMock,
):
    """Verify failed prediction status returns diagnostic without fabricating fake direction."""
    failed_result = PredictionResult(
        symbol="INSUFFICIENT_BARS",
        prediction_timestamp="2026-10-17T09:00:00Z",
        latest_input_timestamp=None,
        status=PredictionStatus.INSUFFICIENT_DATA,
        predicted_direction=None,
        predicted_label=None,
        probability_up=None,
        probability_down=None,
        model_name="xgboost",
        model_version="xgb_v1",
        model_metadata={},
        data_quality=None,
        is_probability_calibrated=False,
        probability_calibration="uncalibrated",
        expected_movement=None,
        expected_movement_status="UNSUPPORTED",
        error_message="Only 10 bars available; minimum 34 required.",
        disclaimer="Standard research disclaimer.",
    )
    mock_prediction_service.predict.return_value = failed_result

    res = client.post("/api/predict", json={"symbol": "INSUFFICIENT_BARS"})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "INSUFFICIENT_DATA"
    assert data["predicted_direction"] is None
    assert data["probability_up"] is None
    assert "Only 10 bars available" in data["error_message"]


def test_predict_standalone_ml_service_exception(
    client: TestClient,
    mock_prediction_service: MagicMock,
):
    """Verify unexpected service exception returns sanitized 500 without leaking stack trace."""
    mock_prediction_service.predict.side_effect = RuntimeError("Internal CUDA memory fault")

    res = client.post("/api/predict", json={"symbol": "RELIANCE"})
    assert res.status_code == 500
    data = res.json()
    assert "error" in data
    # Ensure internal exception details are not disclosed in public response
    assert "CUDA memory fault" not in data["error"]["message"]
    assert "unexpected error" in data["error"]["message"].lower()


def test_predict_error_sanitization_no_path_disclosure(
    client: TestClient,
    mock_prediction_service: MagicMock,
):
    """Verify internal filesystem paths and loader details in error_message are sanitized.

    Remediates CodeRabbit Deep Scan finding 3b923d5b-eb3d-4516-8cc7-41a22c917f99.
    """
    sensitive_path = "D:\\Share_market_predictor\\models\\checkpoints\\xgboost_v1.bin"
    path_result = PredictionResult(
        symbol="RELIANCE",
        prediction_timestamp="2026-10-17T10:00:00+00:00",
        latest_input_timestamp=None,
        status=PredictionStatus.MODEL_UNAVAILABLE,
        predicted_direction=None,
        predicted_label=None,
        probability_up=None,
        probability_down=None,
        model_name="xgboost",
        model_version="xgb_v1",
        model_metadata={},
        data_quality=None,
        error_message=f"Model artifact not found at {sensitive_path}. Traceback: File /app/loader.py line 42",
        disclaimer="Standard research disclaimer.",
    )
    mock_prediction_service.predict.return_value = path_result

    res = client.post("/api/predict", json={"symbol": "RELIANCE"})
    assert res.status_code == 200
    data = res.json()

    # Sensitive internal path and traceback must NOT be disclosed
    assert sensitive_path not in data["error_message"]
    assert "/app/loader.py" not in data["error_message"]
    assert "Model artifact unavailable for 'xgboost'" in data["error_message"]


def test_predict_ensemble_service_exception_sanitized(
    client: TestClient,
    mock_ensemble_service: MagicMock,
):
    """Verify unexpected ensemble exception returns sanitized message without path disclosure."""
    mock_ensemble_service.predict_ensemble.side_effect = FileNotFoundError(
        "Missing config at /etc/secrets/config.json"
    )

    payload = {"symbol": "RELIANCE", "model_name": "ensemble"}
    res = client.post("/api/predict", json=payload)
    assert res.status_code == 500
    data = res.json()
    assert "/etc/secrets/config.json" not in data["error"]["message"]
    assert "unexpected error" in data["error"]["message"].lower()


def test_predict_ensemble_success(
    client: TestClient,
    mock_ensemble_service: MagicMock,
    dummy_ensemble_result: EnsemblePredictionResult,
):
    """Verify multi-agent ensemble prediction returns synthesized breakdown."""
    mock_ensemble_service.predict_ensemble.return_value = dummy_ensemble_result

    payload = {
        "symbol": "RELIANCE",
        "model_name": "ensemble",
        "persist": True,
    }
    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["symbol"] == "RELIANCE"
    assert data["model_name"] == "ensemble"
    assert data["status"] == "SUCCESS"
    assert data["predicted_direction"] == "UP"
    assert data["probability_up"] == 0.74
    assert data["ensemble"] is not None
    assert data["ensemble"]["agreement_status"] == "STRONG_AGREEMENT"
    assert data["ensemble"]["target_range"]["lower_bound"] == 2450.0
    assert data["ensemble"]["target_range"]["upper_bound"] == 2550.0
    assert "Strong quarterly performance" in data["ensemble"]["integrated_positive_factors"]


def test_predict_ensemble_custom_weights(
    client: TestClient,
    mock_ensemble_service: MagicMock,
    dummy_ensemble_result: EnsemblePredictionResult,
):
    """Verify custom ml_weight and llm_weight are passed to EnsembleService."""
    mock_ensemble_service.predict_ensemble.return_value = dummy_ensemble_result

    payload = {
        "symbol": "RELIANCE",
        "model_name": "ensemble",
        "ml_weight": 0.85,
        "llm_weight": 0.15,
    }
    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200

    mock_ensemble_service.predict_ensemble.assert_called_once()
    call_kwargs = mock_ensemble_service.predict_ensemble.call_args.kwargs
    assert call_kwargs["weights"] is not None
    assert abs(call_kwargs["weights"].ml_weight - 0.85) < 1e-4
    assert abs(call_kwargs["weights"].llm_weight - 0.15) < 1e-4


def test_predict_no_persist_option(
    client: TestClient,
    mock_prediction_service: MagicMock,
    dummy_prediction_result: PredictionResult,
    test_repo: PredictionRepository,
):
    """Verify persist=False skips database persistence."""
    mock_prediction_service.predict.return_value = dummy_prediction_result

    payload = {
        "symbol": "RELIANCE",
        "persist": False,
    }
    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["prediction_id"] is None
    assert test_repo.count_predictions() == 0


def test_history_empty(client: TestClient):
    """Verify empty history returns 200 with empty items list."""
    res = client.get("/api/history")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_history_populated_and_filtering(
    client: TestClient,
    test_repo: PredictionRepository,
    dummy_prediction_result: PredictionResult,
):
    """Verify history queries, filtering by symbol/model, and pagination bounds."""
    # Insert 3 records into in-memory database
    test_repo.save_prediction(dummy_prediction_result)  # RELIANCE, xgboost

    pred2 = PredictionResult(
        symbol="RELIANCE",
        prediction_timestamp="2026-10-17T10:00:00Z",
        latest_input_timestamp="2026-10-16T15:30:00+05:30",
        status=PredictionStatus.SUCCESS,
        predicted_direction="DOWN",
        predicted_label=0,
        probability_up=0.42,
        probability_down=0.58,
        model_name="lightgbm",
        model_version="lgb_v1",
        model_metadata={},
        data_quality=None,
        is_probability_calibrated=False,
        probability_calibration="uncalibrated",
        expected_movement=None,
        expected_movement_status="UNSUPPORTED",
        error_message=None,
        disclaimer="Standard disclaimer.",
    )
    test_repo.save_prediction(pred2)  # RELIANCE, lightgbm

    pred3 = PredictionResult(
        symbol="TCS",
        prediction_timestamp="2026-10-17T11:00:00Z",
        latest_input_timestamp="2026-10-16T15:30:00+05:30",
        status=PredictionStatus.SUCCESS,
        predicted_direction="UP",
        predicted_label=1,
        probability_up=0.61,
        probability_down=0.39,
        model_name="xgboost",
        model_version="xgb_v1",
        model_metadata={},
        data_quality=None,
        is_probability_calibrated=False,
        probability_calibration="uncalibrated",
        expected_movement=None,
        expected_movement_status="UNSUPPORTED",
        error_message=None,
        disclaimer="Standard disclaimer.",
    )
    test_repo.save_prediction(pred3)  # TCS, xgboost

    # 1. Total count
    res_all = client.get("/api/history")
    assert res_all.status_code == 200
    assert res_all.json()["total"] == 3
    assert len(res_all.json()["items"]) == 3

    # 2. Filter by symbol
    res_rel = client.get("/api/history?symbol=RELIANCE")
    assert res_rel.status_code == 200
    data_rel = res_rel.json()
    assert data_rel["total"] == 2
    assert all(it["symbol"] == "RELIANCE" for it in data_rel["items"])

    # 3. Filter by model
    res_lgb = client.get("/api/history?model_name=lightgbm")
    assert res_lgb.status_code == 200
    data_lgb = res_lgb.json()
    assert data_lgb["total"] == 1
    assert data_lgb["items"][0]["model_name"] == "lightgbm"

    # 4. Pagination limit and offset
    res_page = client.get("/api/history?limit=1&offset=1")
    assert res_page.status_code == 200
    data_page = res_page.json()
    assert len(data_page["items"]) == 1
    assert data_page["total"] == 3
    assert data_page["limit"] == 1
    assert data_page["offset"] == 1


def test_history_with_verified_outcome(
    client: TestClient,
    test_repo: PredictionRepository,
    dummy_prediction_result: PredictionResult,
):
    """Verify history endpoint attaches verified actual outcome when present."""
    pid = test_repo.save_prediction(dummy_prediction_result)

    # Save actual outcome for this prediction
    actual_data = {
        "prediction_id": pid,
        "symbol": "RELIANCE",
        "target_date": "2026-10-19",
        "actual_direction": "UP",
        "actual_label": 1,
        "actual_return": 0.015,
        "actual_close": 2537.5,
        "reference_close": 2500.0,
        "source": "yfinance",
    }
    test_repo.save_actual(actual_data)

    res = client.get(f"/api/history?symbol=RELIANCE")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["prediction_id"] == pid
    assert item["actual"] is not None
    assert item["actual"]["actual_direction"] == "UP"
    assert item["actual"]["actual_close"] == 2537.5
    assert item["actual"]["actual_return"] == 0.015


def test_feedback_deferred(client: TestClient):
    """Verify feedback submission returns explicit 501 Not Implemented with ADR 10 disclaimer."""
    payload = {
        "prediction_id": "pred_test_123",
        "feedback_type": "accuracy_critique",
        "comments": "Model predicted UP but unexpected policy rate hike caused drop.",
        "rating": 4,
    }
    res = client.post("/api/feedback", json=payload)
    assert res.status_code == 501
    data = res.json()
    assert data["status"] == "deferred"
    assert "ADR 10" in data["message"]
    assert data["route"] == "/api/feedback"


def test_feedback_invalid_payload(client: TestClient):
    """Verify feedback schema validation rejects rating out of range [1, 5]."""
    payload = {
        "prediction_id": "pred_test_123",
        "feedback_type": "rating",
        "rating": 10,  # Invalid: max is 5
    }
    res = client.post("/api/feedback", json=payload)
    assert res.status_code == 422


def test_events_empty(client: TestClient):
    """Verify events endpoint handles empty event sets gracefully."""
    res = client.get("/api/events")
    assert res.status_code == 200
    data = res.json()
    assert data["events"] == []
    assert data["count"] == 0


def test_events_populated_and_filtered():
    """Verify events endpoint aggregates across providers and filters by category and source."""
    now = datetime.now(timezone.utc)
    ev_rbi = MacroEvent(
        title="RBI Repo Rate maintained at 6.50%",
        category=EventCategory.MONETARY_POLICY,
        event_type="rate_decision",
        source_org="Reserve Bank of India",
        ingested_at=now,
        published_at=now,
        affected_sectors=("BANKING", "FINANCIAL_SERVICES"),
        provider="rbi_provider",
    )
    ev_sebi = MacroEvent(
        title="SEBI Circular on Algorithm Trading Disclosures",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        ingested_at=now,
        published_at=now,
        affected_sectors=("CAPITAL_MARKETS",),
        provider="sebi_provider",
    )

    rbi_provider = StubEventProvider("rbi_provider", [ev_rbi])
    sebi_provider = StubEventProvider("sebi_provider", [ev_sebi])

    app = create_app()
    app.dependency_overrides[get_event_providers] = lambda: [rbi_provider, sebi_provider]

    with TestClient(app) as test_client:
        # 1. Fetch all
        res_all = test_client.get("/api/events")
        assert res_all.status_code == 200
        data_all = res_all.json()
        assert data_all["count"] == 2
        assert len(data_all["events"]) == 2

        # 2. Filter by category
        res_cat = test_client.get("/api/events?category=monetary_policy")
        assert res_cat.status_code == 200
        data_cat = res_cat.json()
        assert data_cat["count"] == 1
        assert data_cat["events"][0]["category"] == "monetary_policy"

        # 3. Filter by source
        res_src = test_client.get("/api/events?source=sebi")
        assert res_src.status_code == 200
        data_src = res_src.json()
        assert data_src["count"] == 1
        assert data_src["events"][0]["source_org"] == "SEBI"


def test_events_provider_error_resilience():
    """Verify that a failing provider does not crash the endpoint for surviving providers."""
    now = datetime.now(timezone.utc)
    ev_surviving = MacroEvent(
        title="SEBI Circular on Margin Trading",
        category=EventCategory.REGULATORY,
        event_type="circular",
        source_org="SEBI",
        ingested_at=now,
        published_at=now,
        provider="sebi_provider",
    )

    broken_provider = StubEventProvider("broken_rbi", [], fail=True)
    healthy_provider = StubEventProvider("sebi_provider", [ev_surviving], fail=False)

    app = create_app()
    app.dependency_overrides[get_event_providers] = lambda: [broken_provider, healthy_provider]

    with TestClient(app) as test_client:
        res = test_client.get("/api/events")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 1
        assert data["events"][0]["title"] == "SEBI Circular on Margin Trading"
