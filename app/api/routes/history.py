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
)
from app.database.repository import PredictionRepository

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
        max_length=20,
        description="Filter by stock ticker symbol (e.g. 'RELIANCE')",
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
    clean_sym = symbol.strip().upper() if symbol else None
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
            )
        )

    return HistoryResponse(
        items=items,
        total=total_count,
        limit=limit,
        offset=offset,
    )
