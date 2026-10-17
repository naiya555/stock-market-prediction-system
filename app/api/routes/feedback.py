"""Prediction Feedback API Route.

Handles feedback validation and explicitly defers persistence until a formal
feedback audit table and governance process are approved in the architectural roadmap.
"""

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.schemas import FeedbackRequest, FeedbackResponse
from app.core.logging_config import sanitize_log_field

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Submit User Feedback on Prediction Quality (Deferred)",
    description=(
        "Validates incoming user feedback payload. Because no persistent feedback schema "
        "or repository contract exists in the current SQLite architecture, and ADR 10 "
        "strictly prohibits automated feedback retraining loops, persistence is safely deferred."
    ),
)
def submit_feedback(payload: FeedbackRequest) -> JSONResponse:
    """Validate feedback schema and return explicit deferred status."""
    logger.info(
        "Received feedback request for prediction_id=%s, feedback_type=%s",
        sanitize_log_field(payload.prediction_id),
        sanitize_log_field(payload.feedback_type),
    )

    response_payload = FeedbackResponse(
        status="deferred",
        message=(
            "Feedback ingestion is deferred: no persistence contract or feedback schema exists "
            "in the current database architecture (pending future human-in-the-loop auditing milestone). "
            "Automated model retraining on feedback loops is strictly prohibited by ADR 10."
        ),
        route="/api/feedback",
    )

    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=response_payload.model_dump(),
    )
