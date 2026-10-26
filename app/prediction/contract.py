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
    include_live_quote: bool = True

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
class QuoteContext:
    """Current market quote context associated with prediction inference.

    Provides observed market price diagnostics while strictly distinguishing observed
    market prices (last traded price) from forecast outputs (direction/probability).
    Explicitly discloses provider delays (~15 min on free Yahoo Finance feeds)
    and enforces zero-fabrication safety under missing or stale conditions.
    """

    symbol: str
    last_price: Optional[float]
    price_timestamp: Optional[str]
    retrieved_at: Optional[str]
    source: str
    session_state: str
    freshness_status: str
    is_delayed: bool = True
    delay_minutes: int = 15
    price_type: str = "LAST_TRADED_PRICE"
    open_price: Optional[float] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    note: str = (
        "Last traded price reflects observed exchange/provider market data and is NOT a predicted "
        "opening or closing price. The directional model forecasts return direction (UP/DOWN), "
        "not explicit price targets. Quotes from Yahoo Finance are delayed by ~15 minutes."
    )
    error_message: Optional[str] = None

    @classmethod
    def from_live_quote(cls, quote: Any) -> "QuoteContext":
        """Construct QuoteContext from a verified LiveQuote contract."""
        session_val = (
            quote.session_state.value
            if hasattr(quote.session_state, "value")
            else str(quote.session_state)
        )
        fresh_val = (
            quote.freshness_status.value
            if hasattr(quote.freshness_status, "value")
            else str(quote.freshness_status)
        )
        ts_iso = (
            quote.timestamp.isoformat()
            if hasattr(quote.timestamp, "isoformat")
            else str(quote.timestamp)
        )
        retrieved_iso = (
            quote.retrieved_at.isoformat()
            if hasattr(quote.retrieved_at, "isoformat")
            else str(quote.retrieved_at)
        )
        return cls(
            symbol=quote.symbol,
            last_price=float(quote.price),
            price_timestamp=ts_iso,
            retrieved_at=retrieved_iso,
            source=quote.source,
            session_state=session_val,
            freshness_status=fresh_val,
            is_delayed=getattr(quote, "is_delayed", True),
            delay_minutes=getattr(quote, "delay_minutes", 15),
            price_type="LAST_TRADED_PRICE",
            open_price=getattr(quote, "open_price", None),
            previous_close=getattr(quote, "previous_close", None),
            change=getattr(quote, "change", None),
            change_percent=getattr(quote, "change_percent", None),
            error_message=None,
        )

    @classmethod
    def unavailable(
        cls,
        symbol: str,
        reason: str,
        is_historical: bool = False,
    ) -> "QuoteContext":
        """Construct safe zero-fabrication quote context when quotes cannot be provided."""
        status = "NOT_APPLICABLE" if is_historical else "UNAVAILABLE"
        note = (
            "Point-in-time historical inference: live quotes excluded to prevent look-ahead bias."
            if is_historical
            else "Live market quote currently unavailable. Price was not fabricated."
        )
        return cls(
            symbol=symbol,
            last_price=None,
            price_timestamp=None,
            retrieved_at=None,
            source="none",
            session_state="UNKNOWN",
            freshness_status=status,
            is_delayed=False,
            delay_minutes=0,
            price_type="NONE",
            note=note,
            error_message=reason,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize quote context to dictionary."""
        return asdict(self)


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

    Captures predicted direction, probability (explicitly uncalibrated),
    model provenance, data quality, expected movement status, and capability boundaries.

    Attributes:
        symbol: Ticker symbol.
        prediction_timestamp: ISO string of when inference was executed.
        latest_input_timestamp: ISO timestamp of the market bar used to construct features.
        status: High-level operational status (SUCCESS, MODEL_UNAVAILABLE, etc.).
        predicted_direction: 'UP' or 'DOWN' (None if prediction failed).
        predicted_label: 1 for UP, 0 for DOWN (None if prediction failed).
        probability_up: Estimated probability of next session closing higher (uncalibrated tree output).
        probability_down: Estimated probability of next session closing lower or equal.
        model_name: Selected model identifier ('xgboost' or 'lightgbm').
        model_version: Version identifier of the model.
        model_metadata: Hyperparameters and configuration dictionary of the model.
        data_quality: Audit record of input data health and warm-up sufficiency.
        is_probability_calibrated: Boolean indicating whether probability calibration was applied (False for raw tree probabilities).
        probability_calibration: Explicit descriptor of calibration status ("uncalibrated").
        expected_movement: Expected return magnitude or price move (None if unsupported).
        expected_movement_status: Status of expected movement calculation ("UNSUPPORTED" for binary direction classifiers).
        error_message: Detailed diagnostic error message if status is not SUCCESS.
        quote_context: Optional observed market quote context distinguishing market price from predictions.
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
    is_probability_calibrated: bool = False
    probability_calibration: str = "uncalibrated"
    expected_movement: Optional[float] = None
    expected_movement_status: str = "UNSUPPORTED"
    error_message: Optional[str] = None
    quote_context: Optional[QuoteContext] = None
    disclaimer: str = (
        "The directional forecast predicts the binary sign of next-session close-to-close return "
        "(UP if Close_{t+1} > Close_t else DOWN). It does NOT predict target prices, percentage return "
        "magnitudes, trade duration, or stop-loss bounds, and does NOT constitute financial advice."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize prediction result to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["quote_context"] = self.quote_context.to_dict() if self.quote_context else None
        return data

    def format_summary(self) -> str:
        """Render a clean, human-readable text summary of the structured prediction output."""
        lines = [
            f"Prediction Summary for {self.symbol}:",
            f"  Status:                 {self.status.value}",
            f"  Prediction Timestamp:   {self.prediction_timestamp}",
            f"  Latest Input Bar:       {self.latest_input_timestamp or 'N/A'}",
            f"  Model:                  {self.model_name} ({self.model_version})",
        ]
        if self.quote_context:
            if self.quote_context.last_price is not None:
                lines.append(
                    f"  Last Quoted Price:     ₹ {self.quote_context.last_price:,.2f} "
                    f"({self.quote_context.freshness_status}, session={self.quote_context.session_state}, "
                    f"delayed={self.quote_context.is_delayed}) [OBSERVED, not predicted]"
                )
            else:
                lines.append(
                    f"  Quote Context:          {self.quote_context.freshness_status} "
                    f"({self.quote_context.error_message or self.quote_context.note})"
                )
        if self.status == PredictionStatus.SUCCESS:
            p_up_str = f"{self.probability_up * 100:.2f}%" if self.probability_up is not None else "N/A"
            p_dn_str = f"{self.probability_down * 100:.2f}%" if self.probability_down is not None else "N/A"
            lines.extend([
                f"  Predicted Direction:    {self.predicted_direction} (label={self.predicted_label})",
                f"  Probabilities:          P(UP)={p_up_str}, P(DOWN)={p_dn_str} ({self.probability_calibration})",
                f"  Calibrated:             {self.is_probability_calibrated}",
                f"  Expected Movement:      {self.expected_movement if self.expected_movement is not None else 'null'} (status={self.expected_movement_status})",
                f"  Data Quality:           {self.data_quality.cleaned_bars} bars, warmup={'complete' if self.data_quality.warmup_complete else 'incomplete'}, missing_features={self.data_quality.missing_feature_count}",
            ])
        else:
            lines.append(f"  Error Message:          {self.error_message}")
            lines.append(f"  Data Quality:           {self.data_quality.cleaned_bars} bars, warmup={'complete' if self.data_quality.warmup_complete else 'incomplete'}")
        lines.append(f"  Disclaimer:             {self.disclaimer}")
        return "\n".join(lines)
