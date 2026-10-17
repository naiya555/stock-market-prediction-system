"""Pydantic Request and Response Schemas for Phase 13 FastAPI REST API.

Defines typed, validated data contracts for health checks, prediction requests,
historical prediction queries, feedback handling, and macroeconomic/regulatory events.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Error Schemas
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Detailed error description."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Any] = Field(None, description="Optional diagnostic details")


class ErrorResponse(BaseModel):
    """Canonical error response wrapper."""

    error: ErrorDetail


# ---------------------------------------------------------------------------
# Health Check Schemas
# ---------------------------------------------------------------------------


class DependencyStatus(BaseModel):
    """Status diagnostic for an individual system dependency."""

    status: str = Field(..., description="Dependency status: 'ok', 'degraded', or 'unreachable'")
    details: Optional[str] = Field(None, description="Optional diagnostic context without sensitive data")


class HealthResponse(BaseModel):
    """Comprehensive readiness and health response payload."""

    status: str = Field(..., description="High-level application status: 'healthy' or 'degraded'")
    app_name: str = Field(..., description="Application name")
    environment: str = Field(..., description="Active runtime environment")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of health evaluation")
    dependencies: Dict[str, DependencyStatus] = Field(
        default_factory=dict,
        description="Individual dependency health states",
    )


# ---------------------------------------------------------------------------
# Prediction Schemas
# ---------------------------------------------------------------------------


class PredictRequest(BaseModel):
    """Directional stock movement inference request specification."""

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="NSE/BSE stock ticker symbol (e.g. 'RELIANCE' or 'TCS.NS')",
        examples=["RELIANCE"],
    )
    model_name: str = Field(
        default="xgboost",
        pattern=r"^(xgboost|lightgbm|ensemble)$",
        description="Model architecture: 'xgboost', 'lightgbm', or 'ensemble'",
    )
    as_of_date: Optional[datetime] = Field(
        default=None,
        description="Point-in-time reference cutoff datetime. Defaults to current UTC time.",
    )
    lookback_days: int = Field(
        default=5 * 365,
        ge=35,
        le=3650,
        description="Historical calendar days requested for technical indicator warmup (min 35)",
    )
    max_stale_days: int = Field(
        default=7,
        ge=1,
        le=90,
        description="Maximum allowable calendar days between latest bar and as_of_date",
    )
    allow_stale_data: bool = Field(
        default=True,
        description="Whether to proceed with inference if market data exceeds staleness threshold",
    )
    persist: bool = Field(
        default=True,
        description="Whether to record the prediction immutably in SQLite database",
    )
    ml_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Custom quantitative ML weight for ensemble synthesis (default 0.70)",
    )
    llm_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Custom qualitative LLM weight for ensemble synthesis (default 0.30)",
    )

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean:
            raise ValueError("symbol cannot be empty or whitespace.")
        return clean


class DataQualityResponse(BaseModel):
    """Input data health diagnostics for the prediction observation."""

    total_bars_fetched: int
    cleaned_bars: int
    warmup_bars_required: int
    warmup_complete: bool
    latest_bar_timestamp: Optional[str] = None
    missing_feature_count: int
    is_stale: bool
    stale_days: Optional[int] = None


class TargetRangeResponse(BaseModel):
    """Estimated next-session price bounds based on market volatility."""

    lower_bound: float
    upper_bound: float
    reference_price: float
    method: str


class EnsembleDetailsResponse(BaseModel):
    """Detailed multi-agent ensemble synthesis breakdown."""

    agreement_status: str
    combined_probability_up: float
    combined_probability_down: float
    weights_used: Dict[str, float]
    integrated_positive_factors: List[str]
    integrated_negative_factors: List[str]
    downside_risks: List[str]
    source_references: List[str]
    target_range: Optional[TargetRangeResponse] = None
    llm_reasoning_summary: Optional[str] = None
    llm_confidence: Optional[str] = None


class PredictionResponse(BaseModel):
    """Structured directional prediction inference response."""

    prediction_id: Optional[str] = Field(
        None,
        description="Unique UUID identifier if persisted to database",
    )
    symbol: str
    prediction_timestamp: str
    latest_input_timestamp: Optional[str] = None
    status: str
    predicted_direction: Optional[str] = None
    predicted_label: Optional[int] = None
    probability_up: Optional[float] = None
    probability_down: Optional[float] = None
    model_name: str
    model_version: str
    is_probability_calibrated: bool = False
    probability_calibration: str = "uncalibrated"
    data_quality: Optional[DataQualityResponse] = None
    ensemble: Optional[EnsembleDetailsResponse] = None
    error_message: Optional[str] = None
    disclaimer: str


# ---------------------------------------------------------------------------
# History Schemas
# ---------------------------------------------------------------------------


class ActualOutcomeResponse(BaseModel):
    """Verified market outcome linked to a prediction."""

    target_date: str
    actual_direction: str
    actual_label: int
    actual_return: float
    actual_close: float
    reference_close: Optional[float] = None
    source: str
    recorded_at: str


class HistoryItemResponse(BaseModel):
    """Historical prediction record with optional verified outcome."""

    prediction_id: str
    symbol: str
    model_name: str
    model_version: str
    prediction_timestamp: str
    latest_input_timestamp: Optional[str] = None
    status: str
    predicted_direction: Optional[str] = None
    predicted_label: Optional[int] = None
    probability_up: Optional[float] = None
    probability_down: Optional[float] = None
    is_probability_calibrated: bool = False
    probability_calibration: str = "uncalibrated"
    created_at: str
    actual: Optional[ActualOutcomeResponse] = None


class HistoryResponse(BaseModel):
    """Paginated collection of historical predictions."""

    items: List[HistoryItemResponse]
    total: int = Field(..., description="Total count matching filters")
    limit: int = Field(..., description="Pagination limit applied")
    offset: int = Field(..., description="Pagination offset applied")


# ---------------------------------------------------------------------------
# Feedback Schemas
# ---------------------------------------------------------------------------


class FeedbackRequest(BaseModel):
    """Feedback payload for a past prediction."""

    prediction_id: str = Field(..., min_length=1, description="Associated prediction UUID")
    feedback_type: str = Field(
        ...,
        min_length=1,
        description="Feedback category (e.g. 'accuracy_comment', 'flag', 'general')",
    )
    comments: Optional[str] = Field(None, max_length=2000, description="Optional user comments")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Optional 1-5 rating")


class FeedbackResponse(BaseModel):
    """Response acknowledging feedback submission status."""

    status: str
    message: str
    route: str


# ---------------------------------------------------------------------------
# Event Schemas
# ---------------------------------------------------------------------------


class EventItemResponse(BaseModel):
    """Canonical macroeconomic or regulatory announcement item."""

    event_id: str
    title: str
    category: str
    event_type: str
    source_org: str
    published_at: Optional[str] = None
    announced_at: Optional[str] = None
    effective_at: Optional[str] = None
    ingested_at: str
    url: Optional[str] = None
    affected_sectors: List[str]
    affected_symbols: List[str]
    summary: Optional[str] = None
    provider: str
    is_verified: bool


class EventsResponse(BaseModel):
    """Response containing ingested macroeconomic and regulatory events."""

    events: List[EventItemResponse]
    count: int
    providers_queried: List[str]
