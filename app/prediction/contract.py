"""Prediction Engine Service Contract.

Defines typed request and result containers, data quality metadata,
and status enumerations for directional stock market prediction inference.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class PredictionStatus(str, Enum):
    """Operational status of a prediction request."""

    SUCCESS = "SUCCESS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    STALE_DATA = "STALE_DATA"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    FEATURE_ERROR = "FEATURE_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PredictionRequest:
    """Request specification for directional stock movement inference.

    Attributes:
        symbol: Ticker symbol (e.g. 'BHARTIARTL' or 'BHARTIARTL.NS').
        model_name: Selected model architecture ('xgboost' or 'lightgbm', default 'xgboost').
        model_artifact_path: Optional explicit filesystem path to serialized model file.
        as_of_date: Optional historical cutoff timestamp for point-in-time inference.
        lookback_days: Days of historical data requested for feature warmup (default 5*365).
        max_stale_days: Maximum allowable calendar days between latest bar and as_of_date (default 7).
        allow_stale_data: Whether to proceed with prediction if data exceeds max_stale_days (default True).
    """

    symbol: str
    model_name: str = "xgboost"
    model_artifact_path: Optional[Union[str, Path]] = None
    as_of_date: Optional[datetime] = None
    lookback_days: int = 5 * 365
    max_stale_days: int = 7
    allow_stale_data: bool = True

    def __post_init__(self) -> None:
        """Validate request parameters."""
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol must be a non-empty string.")
        if self.model_name not in ("xgboost", "lightgbm"):
            raise ValueError(
                f"Unsupported model_name '{self.model_name}'. Must be 'xgboost' or 'lightgbm'."
            )
        if self.lookback_days < 35:
            raise ValueError(
                f"lookback_days ({self.lookback_days}) is insufficient for feature warmup (min 35 days)."
            )


@dataclass(frozen=True)
class PredictionDataQuality:
    """Data health diagnostics for the inference input observation.

    Attributes:
        total_bars_fetched: Raw bars retrieved from provider.
        cleaned_bars: Validated bars retained after pipeline cleaning.
        warmup_bars_required: Minimum observations needed for technical indicators (34).
        warmup_complete: Whether cleaned bar count satisfies warmup threshold.
        latest_bar_timestamp: ISO timestamp of the latest available bar.
        missing_feature_count: Count of required features evaluating to NaN in latest bar.
        missing_features: Names of any features missing in the latest bar.
        is_stale: Whether data age exceeds the configured staleness threshold.
        stale_days: Calendar days elapsed between latest bar and reference time.
    """

    total_bars_fetched: int
    cleaned_bars: int
    warmup_bars_required: int
    warmup_complete: bool
    latest_bar_timestamp: Optional[str]
    missing_feature_count: int
    missing_features: List[str]
    is_stale: bool
    stale_days: Optional[int]


@dataclass(frozen=True)
class PredictionResult:
    """Structured response container for directional prediction inference.

    Captures predicted direction, probability, model provenance, data quality,
    and explicit capability boundaries.

    Attributes:
        symbol: Ticker symbol.
        prediction_timestamp: ISO string of when inference was executed.
        latest_input_timestamp: ISO timestamp of the market bar used to construct features.
        status: High-level operational status (SUCCESS, MODEL_UNAVAILABLE, etc.).
        predicted_direction: 'UP' or 'DOWN' (None if prediction failed).
        predicted_label: 1 for UP, 0 for DOWN (None if prediction failed).
        probability_up: Estimated probability of next session closing higher.
        probability_down: Estimated probability of next session closing lower or equal.
        model_name: Selected model identifier ('xgboost' or 'lightgbm').
        model_version: Version identifier of the model.
        model_metadata: Hyperparameters and configuration dictionary of the model.
        data_quality: Audit record of input data health and warm-up sufficiency.
        error_message: Detailed diagnostic error message if status is not SUCCESS.
        disclaimer: Explicit disclosure of model capabilities and boundaries.
    """

    symbol: str
    prediction_timestamp: str
    latest_input_timestamp: Optional[str]
    status: PredictionStatus
    predicted_direction: Optional[str]
    predicted_label: Optional[int]
    probability_up: Optional[float]
    probability_down: Optional[float]
    model_name: str
    model_version: str
    model_metadata: Dict[str, Any]
    data_quality: PredictionDataQuality
    error_message: Optional[str] = None
    disclaimer: str = (
        "The directional forecast predicts the binary sign of next-session close-to-close return "
        "(UP if Close_{t+1} > Close_t else DOWN). It does NOT predict target prices, percentage return "
        "magnitudes, trade duration, or stop-loss bounds, and does NOT constitute financial advice."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize prediction result to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data
