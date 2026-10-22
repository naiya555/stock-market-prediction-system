"""Pydantic Request and Response Schemas for Phase 13 FastAPI REST API.

Defines typed, validated data contracts for health checks, prediction requests,
historical prediction queries, feedback handling, and macroeconomic/regulatory events.
"""

from datetime import datetime
import re
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
# Instrument Catalog Schemas
# ---------------------------------------------------------------------------


class InstrumentItemResponse(BaseModel):
    """Canonical instrument status and model compatibility definition."""

    symbol: str = Field(..., description="Canonical ticker symbol (e.g. 'BHARTIARTL')")
    name: str = Field(..., description="Official human-readable instrument name")
    instrument_type: str = Field(..., description="'EQUITY' or 'INDEX'")
    exchange: str = Field(default="NSE", description="Exchange code")
    status: str = Field(..., description="'SUPPORTED' or 'BLOCKED'")
    compatible_models: List[str] = Field(default_factory=list, description="List of compatible model names")
    reason: str = Field(..., description="Availability status rationale or blocking constraint")


class InstrumentCatalogResponse(BaseModel):
    """Collection of registered instruments and their model availability status."""

    instruments: List[InstrumentItemResponse]
    supported_count: int
    blocked_count: int


# ---------------------------------------------------------------------------
# Prediction Schemas
# ---------------------------------------------------------------------------


class PredictRequest(BaseModel):
    """Directional stock movement inference request specification."""

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="NSE/BSE stock or index ticker symbol (e.g. 'BHARTIARTL' or 'NIFTY_TELECOMMUNICATIONS')",
        examples=["BHARTIARTL"],
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
    include_live_quote: bool = Field(
        default=True,
        description="Whether to query current verified quote data for price context during live inference",
    )

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("symbol cannot be empty or whitespace.")
        clean = v.strip().upper()
        # Reject control characters (CR, LF, tabs, non-printables)
        if any(ord(c) < 32 or ord(c) == 127 for c in v):
            raise ValueError("symbol contains invalid control characters or line breaks.")
        # Validate against supported ticker grammar (letters, digits, dot, hyphen, underscore, caret)
        if not re.match(r"^[A-Z0-9_\-\.\^]{1,30}$", clean):
            raise ValueError(f"symbol '{clean}' does not match supported ticker format.")
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


class QuoteContextResponse(BaseModel):
    """Observed market quote context distinguishing observed prices from forecasts."""

    symbol: str
    last_price: Optional[float] = None
    price_timestamp: Optional[str] = None
    retrieved_at: Optional[str] = None
    source: str = "none"
    session_state: str = "UNKNOWN"
    freshness_status: str = "UNAVAILABLE"
    is_delayed: bool = True
    delay_minutes: int = 15
    price_type: str = "LAST_TRADED_PRICE"
    note: str = (
        "Last traded price reflects observed exchange/provider market data and is NOT a predicted "
        "opening or closing price. The directional model forecasts return direction (UP/DOWN), "
        "not explicit price targets. Quotes from Yahoo Finance are delayed by ~15 minutes."
    )
    error_message: Optional[str] = None


class LLMExplanationResponse(BaseModel):
    """Evidence-grounded qualitative context explanation (Day 55)."""

    status: str
    summary: str
    supporting_evidence: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    model: str
    generated_at: str
    direction: Optional[str] = None
    confidence: Optional[str] = None
    disclaimer: Optional[str] = None


class EnsembleDetailsResponse(BaseModel):
    """Detailed multi-agent ensemble synthesis breakdown."""

    agreement_status: str
    combined_probability_up: Optional[float] = None
    combined_probability_down: Optional[float] = None
    weights_used: Dict[str, float]
    requested_weights: Optional[Dict[str, float]] = None
    fallback_reason: Optional[str] = None
    integrated_positive_factors: List[str]
    integrated_negative_factors: List[str]
    downside_risks: List[str]
    source_references: List[str]
    target_range: Optional[TargetRangeResponse] = None
    llm_direction: Optional[str] = None
    llm_reasoning_summary: Optional[str] = None
    llm_confidence: Optional[str] = None
    explanation: Optional[LLMExplanationResponse] = None


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
    explanation: Optional[LLMExplanationResponse] = None
    quote_context: Optional[QuoteContextResponse] = None
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

    @field_validator("prediction_id", "feedback_type")
    @classmethod
    def validate_identifiers(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Field cannot be empty or whitespace.")
        if any(ord(c) < 32 or ord(c) == 127 for c in v):
            raise ValueError("Field contains invalid control characters or line breaks.")
        if not re.match(r"^[A-Za-z0-9_\-]{1,64}$", clean):
            raise ValueError("Field contains invalid characters; only alphanumeric, dash, and underscore allowed.")
        return clean


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


# ---------------------------------------------------------------------------
# Model Comparison & Evaluation Schemas (Phase 15)
# ---------------------------------------------------------------------------


class ModelPerformanceResponse(BaseModel):
    """Aggregated performance metrics for a specific model architecture."""

    model_name: str
    total_predictions: int
    verified_sessions: int
    pending_sessions: int
    correct_predictions: int
    incorrect_predictions: int
    directional_accuracy: Optional[float] = None
    precision_up: Optional[float] = None
    recall_up: Optional[float] = None
    f1_up: Optional[float] = None
    precision_down: Optional[float] = None
    recall_down: Optional[float] = None
    f1_down: Optional[float] = None
    brier_score: Optional[float] = None


class PairwiseComparisonResponse(BaseModel):
    """Side-by-side performance comparison on identical trading sessions."""

    model_a: str
    model_b: str
    matched_sessions: int
    agreement_count: int
    agreement_rate: Optional[float] = None
    agreement_accuracy: Optional[float] = None
    divergence_count: int
    divergence_rate: Optional[float] = None
    divergence_accuracy_a: Optional[float] = None
    divergence_accuracy_b: Optional[float] = None
    model_a_superior_count: int
    model_b_superior_count: int
    both_correct_count: int
    both_incorrect_count: int
    accuracy_delta: Optional[float] = None


class ModelComparisonResponse(BaseModel):
    """Response containing comparative metrics across Python ML, LLM, and Ensemble."""

    symbol: Optional[str] = None
    total_records_analyzed: int
    models: List[ModelPerformanceResponse]
    pairwise_comparisons: List[PairwiseComparisonResponse]
    ensemble_lift_over_ml: Optional[float] = None
    ensemble_lift_over_llm: Optional[float] = None
    disclaimer: str
