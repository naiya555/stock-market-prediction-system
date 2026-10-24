"""Prediction History and Audit API Route.

Exposes immutable historical prediction records and verified market outcomes from the SQLite persistence layer.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_prediction_repository
from app.api.schemas import (
    ActualOutcomeResponse,
    HistoryItemResponse,
    HistoryResponse,
    ModelComparisonResponse,
    ModelPerformanceResponse,
    PairwiseComparisonResponse,
)
from app.database.repository import PredictionRepository
from app.history.comparison import ModelComparator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=HistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query Immutable Prediction History & Verified Outcomes",
    description=(
        "Retrieves historical directional stock market predictions with bounded pagination, "
        "optional symbol and model filtering, and linked verified actual outcomes."
    ),
)
def get_history(
    symbol: Optional[str] = Query(
        None,
        min_length=1,
        max_length=50,
        description="Filter by stock ticker symbol (e.g. 'BHARTIARTL', 'BHARTIARTL.NS')",
    ),
    model_name: Optional[str] = Query(
        None,
        description="Filter by model architecture ('xgboost', 'lightgbm', 'ensemble')",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum number of historical records to return (1-500)",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Pagination offset index (non-negative)",
    ),
    repository: PredictionRepository = Depends(get_prediction_repository),
) -> HistoryResponse:
    """Query persisted predictions and map each record to HistoryItemResponse."""
    clean_sym = None
    if symbol and symbol.strip():
        from app.market.instruments import resolve_canonical_symbol
        clean_sym = resolve_canonical_symbol(symbol.strip())
    clean_model = model_name.strip().lower() if model_name else None

    # Retrieve raw records and total matching count from repository
    records = repository.list_predictions(
        symbol=clean_sym,
        model_name=clean_model,
        limit=limit,
        offset=offset,
    )
    total_count = repository.count_predictions(
        symbol=clean_sym,
        model_name=clean_model,
    )

    items: List[HistoryItemResponse] = []
    for rec in records:
        pid = rec["prediction_id"]

        # Check for linked verified actual outcome
        actual_model = None
        try:
            actual_rec = repository.get_actual(pid)
            if actual_rec:
                actual_model = ActualOutcomeResponse(
                    target_date=actual_rec["target_date"],
                    actual_direction=actual_rec["actual_direction"],
                    actual_label=actual_rec["actual_label"],
                    actual_return=float(actual_rec["actual_return"]),
                    actual_close=float(actual_rec["actual_close"]),
                    reference_close=float(actual_rec["reference_close"]) if actual_rec.get("reference_close") is not None else None,
                    source=actual_rec.get("source", "yfinance"),
                    recorded_at=actual_rec["recorded_at"],
                )
        except Exception as exc:
            logger.warning("Could not fetch actual outcome for prediction %s: %s", pid, exc)

        # Build Why This Prediction evidence object
        raw_res = rec.get("raw_result") or {}
        pos_factors = raw_res.get("integrated_positive_factors") or []
        neg_factors = raw_res.get("integrated_negative_factors") or []
        downside_risks = raw_res.get("downside_risks") or []
        quote_ctx = raw_res.get("quote_context") or {}
        model_meta = raw_res.get("model_metadata") or {}

        why_pred = {
            "forecast_direction": rec.get("predicted_direction"),
            "forecast_horizon": "Next trading session (1-day forward close-to-close return)",
            "input_timestamp": rec.get("latest_input_timestamp"),
            "data_freshness": "Point-in-time exchange close",
            "probability_up": rec.get("probability_up"),
            "probability_down": rec.get("probability_down"),
            "model_provenance": f"{rec['model_name']} ({rec['model_version']})",
            "weights_used": model_meta.get("weights_used"),
            "fallback_reason": model_meta.get("fallback_reason"),
            "positive_factors": pos_factors,
            "negative_factors": neg_factors,
            "downside_risks": downside_risks,
            "observed_price": quote_ctx.get("last_price"),
            "price_timestamp": quote_ctx.get("price_timestamp"),
            "explanation_summary": raw_res.get("explanation", {}).get("summary") if isinstance(raw_res.get("explanation"), dict) else None,
            "verified_outcome": {
                "actual_direction": actual_model.actual_direction if actual_model else None,
                "actual_return_pct": round(actual_model.actual_return * 100, 2) if actual_model else None,
                "actual_close": actual_model.actual_close if actual_model else None,
                "is_correct": (actual_model.actual_direction == rec.get("predicted_direction")) if actual_model else None,
            } if actual_model else None,
            "limitations": [
                "Binary directional sign only; opening/closing exact targets unsupported",
                "Uncalibrated weighted tree/heuristic probability blend",
                "Equity model calibrated specifically for BHARTIARTL feature matrix",
            ],
        }

        items.append(
            HistoryItemResponse(
                prediction_id=pid,
                symbol=rec["symbol"],
                model_name=rec["model_name"],
                model_version=rec["model_version"],
                prediction_timestamp=rec["prediction_timestamp"],
                latest_input_timestamp=rec.get("latest_input_timestamp"),
                status=rec["status"],
                predicted_direction=rec.get("predicted_direction"),
                predicted_label=rec.get("predicted_label"),
                probability_up=rec.get("probability_up"),
                probability_down=rec.get("probability_down"),
                is_probability_calibrated=bool(rec.get("is_probability_calibrated", 0)),
                probability_calibration=rec.get("probability_calibration", "uncalibrated"),
                created_at=rec.get("created_at", rec["prediction_timestamp"]),
                actual=actual_model,
                raw_result=raw_res if raw_res else None,
                why_prediction=why_pred,
            )
        )

    return HistoryResponse(
        items=items,
        total=total_count,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/compare",
    response_model=ModelComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Python ML vs. LLM vs. Combined Performance",
    description=(
        "Computes comparative evaluation metrics (accuracy, precision, recall, F1, Brier score, "
        "pairwise alignment, and ensemble lift) across model architectures on verified historical outcomes."
    ),
)
def compare_models(
    symbol: Optional[str] = Query(
        None,
        min_length=1,
        max_length=20,
        description="Optional stock ticker symbol filter (e.g. 'RELIANCE')",
    ),
    min_verified: int = Query(
        1,
        ge=1,
        description="Minimum verified sessions required to include pairwise comparison (default 1)",
    ),
    repository: PredictionRepository = Depends(get_prediction_repository),
) -> ModelComparisonResponse:
    """Compare model performance metrics across verified sessions."""
    comparator = ModelComparator(repository=repository)
    report = comparator.compare_from_repository(symbol=symbol, min_verified=min_verified)

    models_resp = [
        ModelPerformanceResponse(
            model_name=m.model_name,
            total_predictions=m.total_predictions,
            verified_sessions=m.verified_sessions,
            pending_sessions=m.pending_sessions,
            correct_predictions=m.correct_predictions,
            incorrect_predictions=m.incorrect_predictions,
            directional_accuracy=m.directional_accuracy,
            precision_up=m.precision_up,
            recall_up=m.recall_up,
            f1_up=m.f1_up,
            precision_down=m.precision_down,
            recall_down=m.recall_down,
            f1_down=m.f1_down,
            brier_score=m.brier_score,
        )
        for m in report.models
    ]

    pw_resp = [
        PairwiseComparisonResponse(
            model_a=p.model_a,
            model_b=p.model_b,
            matched_sessions=p.matched_sessions,
            agreement_count=p.agreement_count,
            agreement_rate=p.agreement_rate,
            agreement_accuracy=p.agreement_accuracy,
            divergence_count=p.divergence_count,
            divergence_rate=p.divergence_rate,
            divergence_accuracy_a=p.divergence_accuracy_a,
            divergence_accuracy_b=p.divergence_accuracy_b,
            model_a_superior_count=p.model_a_superior_count,
            model_b_superior_count=p.model_b_superior_count,
            both_correct_count=p.both_correct_count,
            both_incorrect_count=p.both_incorrect_count,
            accuracy_delta=p.accuracy_delta,
        )
        for p in report.pairwise_comparisons
    ]

    return ModelComparisonResponse(
        symbol=report.symbol,
        total_records_analyzed=report.total_records_analyzed,
        models=models_resp,
        pairwise_comparisons=pw_resp,
        ensemble_lift_over_ml=report.ensemble_lift_over_ml,
        ensemble_lift_over_llm=report.ensemble_lift_over_llm,
        disclaimer=report.disclaimer,
    )
