"""Unit and Integration Tests for Phase 15 Model Comparison Service and API.

Validates:
1. ModelComparator metric computation across multiple architectures.
2. Extraction of constituent ML and LLM signals from ensemble raw_result.
3. Brier score probability calibration calculation.
4. Pairwise matched session alignment, divergence, and superiority win/loss.
5. Zero-division and insufficient sample safety.
6. Comparative text audit summary formatting with required disclaimers.
7. FastAPI GET /api/history/compare endpoint serialization and filtering.
"""

from datetime import datetime, timezone
import json
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.dependencies import get_prediction_repository
from app.history.comparison import (
    ComparativeEvaluationReport,
    ModelComparator,
    ModelPerformanceRow,
    PairwiseComparison,
)


def _build_test_record(
    symbol: str,
    target_date: str,
    model_name: str,
    pred_dir: str,
    prob_up: float,
    act_dir: str,
    act_label: int,
    raw_result: dict = None,
) -> dict:
    """Helper to build a joined prediction/actual record dict."""
    return {
        "prediction_id": f"pred_{model_name}_{target_date}",
        "symbol": symbol,
        "model_name": model_name,
        "model_version": f"{model_name}_v1",
        "prediction_timestamp": f"{target_date}T09:00:00Z",
        "latest_input_timestamp": f"{target_date}T00:00:00Z",
        "status": "SUCCESS",
        "predicted_direction": pred_dir,
        "predicted_label": 1 if pred_dir == "UP" else 0,
        "probability_up": prob_up,
        "probability_down": round(1.0 - prob_up, 2),
        "target_date": target_date,
        "actual_direction": act_dir,
        "actual_label": act_label,
        "actual_return": 0.015 if act_dir == "UP" else -0.015,
        "raw_result": raw_result,
        "raw_result_json": json.dumps(raw_result) if raw_result else None,
    }


def test_model_comparator_basic_metrics():
    """Verify ModelComparator computes accuracy, F1, and Brier score correctly."""
    # 4 verified sessions for XGBoost:
    # 1. UP, act UP (prob=0.8) -> Brier = (0.8 - 1)^2 = 0.04
    # 2. UP, act DOWN (prob=0.7) -> Brier = (0.7 - 0)^2 = 0.49
    # 3. DOWN, act DOWN (prob=0.2) -> Brier = (0.2 - 0)^2 = 0.04
    # 4. DOWN, act UP (prob=0.3) -> Brier = (0.3 - 1)^2 = 0.49
    # Mean Brier = (0.04 + 0.49 + 0.04 + 0.49) / 4 = 1.06 / 4 = 0.2650
    # Correct = 2, Total = 4, Accuracy = 0.5000
    records = [
        _build_test_record("RELIANCE", "2026-10-01", "xgboost", "UP", 0.8, "UP", 1),
        _build_test_record("RELIANCE", "2026-10-02", "xgboost", "UP", 0.7, "DOWN", 0),
        _build_test_record("RELIANCE", "2026-10-03", "xgboost", "DOWN", 0.2, "DOWN", 0),
        _build_test_record("RELIANCE", "2026-10-04", "xgboost", "DOWN", 0.3, "UP", 1),
    ]

    report = ModelComparator.compare_records(records, symbol="RELIANCE")
    assert report.total_records_analyzed == 4
    assert len(report.models) == 1

    xgb = report.models[0]
    assert xgb.model_name == "xgboost"
    assert xgb.total_predictions == 4
    assert xgb.verified_sessions == 4
    assert xgb.correct_predictions == 2
    assert xgb.directional_accuracy == 0.5
    assert xgb.brier_score == 0.2650


def test_model_comparator_pairwise_alignment():
    """Verify pairwise agreement, divergence, and superiority win/loss calculation."""
    # Session 1: Both predict UP, Act UP (Agree, Both Correct)
    # Session 2: A predicts UP, B predicts DOWN, Act UP (Diverge, A Wins)
    # Session 3: A predicts DOWN, B predicts UP, Act UP (Diverge, B Wins)
    # Session 4: Both predict DOWN, Act UP (Agree, Both Incorrect)
    records = [
        _build_test_record("TCS", "2026-10-01", "xgboost", "UP", 0.6, "UP", 1),
        _build_test_record("TCS", "2026-10-01", "lightgbm", "UP", 0.65, "UP", 1),

        _build_test_record("TCS", "2026-10-02", "xgboost", "UP", 0.7, "UP", 1),
        _build_test_record("TCS", "2026-10-02", "lightgbm", "DOWN", 0.3, "UP", 1),

        _build_test_record("TCS", "2026-10-03", "xgboost", "DOWN", 0.4, "UP", 1),
        _build_test_record("TCS", "2026-10-03", "lightgbm", "UP", 0.8, "UP", 1),

        _build_test_record("TCS", "2026-10-04", "xgboost", "DOWN", 0.2, "UP", 1),
        _build_test_record("TCS", "2026-10-04", "lightgbm", "DOWN", 0.25, "UP", 1),
    ]

    report = ModelComparator.compare_records(records, symbol="TCS")
    assert len(report.models) == 2
    assert len(report.pairwise_comparisons) == 1

    pw = report.pairwise_comparisons[0]
    assert pw.matched_sessions == 4
    assert pw.agreement_count == 2
    assert pw.agreement_rate == 0.5
    assert pw.agreement_accuracy == 0.5  # 1 out of 2 agreed sessions was correct
    assert pw.divergence_count == 2
    assert pw.divergence_rate == 0.5

    # In divergence: session 2 (xgb wins), session 3 (lgb wins)
    assert pw.both_correct_count == 1
    assert pw.both_incorrect_count == 1
    assert pw.model_a_superior_count == 1
    assert pw.model_b_superior_count == 1
    assert pw.accuracy_delta == 0.0


def test_ensemble_constituent_extraction():
    """Verify that ensemble raw_result extracts constituent ML and LLM signals."""
    raw_res = {
        "combined_direction": "UP",
        "combined_probability_up": 0.65,
        "ml_prediction": {
            "model_name": "xgboost",
            "model_version": "v1",
            "predicted_direction": "UP",
            "predicted_label": 1,
            "probability_up": 0.70,
        },
        "llm_reasoning": {
            "model_version": "gemma3:12b",
            "direction": "DOWN",
            "confidence_assessment": "HIGH",
        },
    }

    # Ensemble record where actual direction is UP
    rec = _build_test_record(
        symbol="INFY",
        target_date="2026-10-10",
        model_name="ensemble",
        pred_dir="UP",
        prob_up=0.65,
        act_dir="UP",
        act_label=1,
        raw_result=raw_res,
    )

    report = ModelComparator.compare_records([rec], symbol="INFY")

    # Should have decomposed into: ensemble, xgboost, and llm
    model_names = [m.model_name for m in report.models]
    assert "ensemble" in model_names
    assert "xgboost" in model_names
    assert "llm" in model_names

    # Check pairwise comparison between ensemble and constituent models
    ens_row = next(m for m in report.models if m.model_name == "ensemble")
    xgb_row = next(m for m in report.models if m.model_name == "xgboost")
    llm_row = next(m for m in report.models if m.model_name == "llm")

    assert ens_row.directional_accuracy == 1.0  # Ensemble was UP (correct)
    assert xgb_row.directional_accuracy == 1.0  # XGB was UP (correct)
    assert llm_row.directional_accuracy == 0.0  # LLM was DOWN (incorrect)


def test_model_comparator_zero_division_safety():
    """Verify graceful handling when no predictions are verified or records are empty."""
    report = ModelComparator.compare_records([])
    assert report.total_records_analyzed == 0
    assert len(report.models) == 0
    assert len(report.pairwise_comparisons) == 0
    assert report.ensemble_lift_over_ml is None

    # Unverified pending prediction
    unverified = {
        "prediction_id": "pred_pending",
        "symbol": "HDFCBANK",
        "model_name": "xgboost",
        "model_version": "v1",
        "prediction_timestamp": "2026-10-18T09:00:00Z",
        "latest_input_timestamp": "2026-10-17T00:00:00Z",
        "status": "SUCCESS",
        "predicted_direction": "UP",
        "predicted_label": 1,
        "probability_up": 0.60,
        "target_date": "2026-10-18",
        "actual_direction": None,
        "actual_label": None,
    }
    report2 = ModelComparator.compare_records([unverified])
    assert len(report2.models) == 1
    m = report2.models[0]
    assert m.total_predictions == 1
    assert m.verified_sessions == 0
    assert m.pending_sessions == 1
    assert m.directional_accuracy is None
    assert m.brier_score is None


def test_comparative_report_formatting():
    """Verify format_summary returns a clean markdown audit table with disclaimers."""
    records = [
        _build_test_record("SBIN", "2026-10-01", "xgboost", "UP", 0.6, "UP", 1),
        _build_test_record("SBIN", "2026-10-01", "ensemble", "UP", 0.7, "UP", 1),
    ]
    report = ModelComparator.compare_records(records, symbol="SBIN")
    summary = report.format_summary()

    assert "PHASE 15 COMPARATIVE MODEL EVALUATION REPORT" in summary
    assert "SBIN" in summary
    assert "xgboost" in summary
    assert "ensemble" in summary
    assert "Disclaimer:" in summary
    assert "Brier Score" in summary


def test_api_history_compare_route():
    """Verify FastAPI GET /api/history/compare endpoint returns structured comparison response."""
    app = create_app()
    mock_repo = MagicMock()

    records = [
        _build_test_record("RELIANCE", "2026-10-01", "xgboost", "UP", 0.65, "UP", 1),
        _build_test_record("RELIANCE", "2026-10-01", "ensemble", "UP", 0.70, "UP", 1),
        _build_test_record("RELIANCE", "2026-10-02", "xgboost", "DOWN", 0.35, "DOWN", 0),
        _build_test_record("RELIANCE", "2026-10-02", "ensemble", "DOWN", 0.40, "DOWN", 0),
    ]
    mock_repo.list_predictions_with_actuals.return_value = records

    app.dependency_overrides[get_prediction_repository] = lambda: mock_repo

    with TestClient(app) as client:
        res = client.get("/api/history/compare?symbol=RELIANCE")
        assert res.status_code == 200
        data = res.json()

        assert "models" in data
        assert "pairwise_comparisons" in data
        assert data["symbol"] == "RELIANCE"
        assert len(data["models"]) == 2

        # Check models present
        m_names = [m["model_name"] for m in data["models"]]
        assert "xgboost" in m_names
        assert "ensemble" in m_names

        # Check pairwise
        assert len(data["pairwise_comparisons"]) == 1
        pw = data["pairwise_comparisons"][0]
        assert pw["matched_sessions"] == 2
        assert pw["agreement_rate"] == 1.0

        # Check disclaimer
        assert "Model comparison metrics" in data["disclaimer"]
