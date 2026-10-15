"""Outcome Verification and Evaluation Contracts for Phase 7.

Defines typed data structures for actual market outcomes, verification statuses,
per-prediction verification records, and aggregate evaluation metrics.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional


class VerificationStatus(str, Enum):
    """Operational status of a prediction outcome verification."""

    VERIFIED = "VERIFIED"
    ALREADY_VERIFIED = "ALREADY_VERIFIED"
    PENDING = "PENDING"
    INELIGIBLE = "INELIGIBLE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class ActualOutcome:
    """Canonical record of a realized future market outcome for a prediction.

    Attributes:
        prediction_id: Unique identifier of the associated prediction.
        symbol: Ticker symbol (e.g. 'BHARTIARTL').
        target_date: ISO date/timestamp string of the realized target trading session (t+1).
        actual_direction: Realized market movement ('UP' if return > 0 else 'DOWN').
        actual_label: 1 for UP, 0 for DOWN.
        actual_return: Forward close-to-close return ((Close_{t+1} / Close_t) - 1.0).
        actual_close: Realized closing price at target session t+1.
        reference_close: Reference closing price at session t when prediction was generated.
        source: Provenance data source (e.g. 'yfinance', 'nse_bhavcopy', 'mock').
        recorded_at: ISO timestamp when this outcome was verified and persisted.
    """

    prediction_id: str
    symbol: str
    target_date: str
    actual_direction: str
    actual_label: int
    actual_return: float
    actual_close: float
    reference_close: Optional[float] = None
    source: str = "yfinance"
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        """Validate actual outcome fields."""
        if not isinstance(self.prediction_id, str) or not self.prediction_id.strip():
            raise ValueError("prediction_id must be a non-empty string.")
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol must be a non-empty string.")
        if not isinstance(self.target_date, str) or not self.target_date.strip():
            raise ValueError("target_date must be a non-empty string.")
        if self.actual_direction not in ("UP", "DOWN"):
            raise ValueError(f"actual_direction must be 'UP' or 'DOWN', got {self.actual_direction!r}.")
        if self.actual_label not in (0, 1):
            raise ValueError(f"actual_label must be 0 or 1, got {self.actual_label!r}.")
        if not math.isfinite(self.actual_return):
            raise ValueError("actual_return must be a finite float.")
        if not (math.isfinite(self.actual_close) and self.actual_close > 0.0):
            raise ValueError("actual_close must be a positive finite float.")
        if self.reference_close is not None and not (math.isfinite(self.reference_close) and self.reference_close > 0.0):
            raise ValueError("reference_close must be a positive finite float if provided.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert actual outcome to a serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class VerificationRecord:
    """Detailed result of verifying an individual prediction against market data.

    Attributes:
        prediction_id: Unique prediction identifier.
        symbol: Ticker symbol.
        status: VerificationStatus enumeration.
        predicted_direction: Forecasted direction from original prediction ('UP' or 'DOWN').
        predicted_label: Forecasted label (1 or 0).
        actual_direction: Realized direction ('UP' or 'DOWN') if outcome available.
        actual_label: Realized label (1 or 0) if outcome available.
        target_date: Realized target session date string if available.
        actual_return: Realized percentage return if available.
        actual_close: Realized closing price if available.
        reference_close: Reference closing price if available.
        is_correct: Whether predicted direction matched actual direction (None if pending/ineligible).
        message: Informative diagnostic or status message.
    """

    prediction_id: str
    symbol: str
    status: VerificationStatus
    predicted_direction: Optional[str]
    predicted_label: Optional[int]
    actual_direction: Optional[str] = None
    actual_label: Optional[int] = None
    target_date: Optional[str] = None
    actual_return: Optional[float] = None
    actual_close: Optional[float] = None
    reference_close: Optional[float] = None
    is_correct: Optional[bool] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert verification record to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class EvaluationMetrics:
    """Aggregate evaluation statistics for verified stock direction predictions.

    Attributes:
        total_predictions: Count of all persisted predictions matching query.
        eligible_predictions: Count of successful predictions eligible for verification.
        ineligible_predictions: Count of unsuccessful predictions (e.g. MODEL_UNAVAILABLE).
        verified_predictions: Count of predictions with verified completed outcomes (the denominator).
        pending_predictions: Count of eligible predictions whose target session has not completed.
        unverifiable_predictions: Count of predictions missing reference market data.
        correct_predictions: Verified predictions where predicted_direction == actual_direction.
        incorrect_predictions: Verified predictions where predicted_direction != actual_direction.
        directional_accuracy: correct_predictions / verified_predictions (None if denominator is 0).
        up_predictions: Count of UP forecasts among verified predictions.
        down_predictions: Count of DOWN forecasts among verified predictions.
        actual_up_count: Count of actual UP outcomes among verified predictions.
        actual_down_count: Count of actual DOWN outcomes among verified predictions.
        true_positives: Predicted UP, Actual UP.
        false_positives: Predicted UP, Actual DOWN.
        true_negatives: Predicted DOWN, Actual DOWN.
        false_negatives: Predicted DOWN, Actual UP.
        precision_up: TP / (TP + FP) (None if denominator is 0).
        recall_up: TP / (TP + FN) (None if denominator is 0).
        f1_up: Harmonic mean of precision_up and recall_up.
        precision_down: TN / (TN + FN) (None if denominator is 0).
        recall_down: TN / (TN + FP) (None if denominator is 0).
        f1_down: Harmonic mean of precision_down and recall_down.
        by_model: Dictionary of metrics grouped by model architecture.
        by_symbol: Dictionary of metrics grouped by stock symbol.
        disclaimer: Explicit statement regarding sample size, model boundaries, and calibration.
    """

    total_predictions: int
    eligible_predictions: int
    ineligible_predictions: int
    verified_predictions: int
    pending_predictions: int
    unverifiable_predictions: int
    correct_predictions: int
    incorrect_predictions: int
    directional_accuracy: Optional[float]
    up_predictions: int
    down_predictions: int
    actual_up_count: int
    actual_down_count: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision_up: Optional[float]
    recall_up: Optional[float]
    f1_up: Optional[float]
    precision_down: Optional[float]
    recall_down: Optional[float]
    f1_down: Optional[float]
    by_model: Dict[str, Any]
    by_symbol: Dict[str, Any]
    disclaimer: str = (
        "Directional accuracy evaluates binary next-session close-to-close direction (UP vs DOWN) "
        "calculated strictly over completed, verified sessions. Direction classifiers do not predict "
        "target price levels or return magnitudes. Model probabilities are uncalibrated raw scores."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert evaluation metrics to dictionary."""
        return asdict(self)

    def format_summary(self) -> str:
        """Render a clean, human-readable text audit of the evaluation metrics."""
        acc_str = f"{self.directional_accuracy * 100:.2f}%" if self.directional_accuracy is not None else "N/A (no verified sessions)"
        prec_up_str = f"{self.precision_up * 100:.2f}%" if self.precision_up is not None else "N/A"
        rec_up_str = f"{self.recall_up * 100:.2f}%" if self.recall_up is not None else "N/A"
        f1_up_str = f"{self.f1_up:.4f}" if self.f1_up is not None else "N/A"
        prec_dn_str = f"{self.precision_down * 100:.2f}%" if self.precision_down is not None else "N/A"
        rec_dn_str = f"{self.recall_down * 100:.2f}%" if self.recall_down is not None else "N/A"
        f1_dn_str = f"{self.f1_down:.4f}" if self.f1_down is not None else "N/A"

        lines = [
            "================================================================================",
            "PREDICTION OUTCOME EVALUATION REPORT",
            "================================================================================",
            f"  Total Predictions:         {self.total_predictions}",
            f"  Eligible Predictions:      {self.eligible_predictions}",
            f"  Ineligible / Failed:       {self.ineligible_predictions}",
            f"  Verified Completed:        {self.verified_predictions} (Evaluation Denominator)",
            f"  Pending (Future Session):  {self.pending_predictions}",
            f"  Unverifiable Data:         {self.unverifiable_predictions}",
            "--------------------------------------------------------------------------------",
            f"  Correct Direction:         {self.correct_predictions}",
            f"  Incorrect Direction:       {self.incorrect_predictions}",
            f"  Directional Accuracy:      {acc_str}",
            "--------------------------------------------------------------------------------",
            "  Symmetrical Class Breakdown:",
            f"    UP   -> Predicted: {self.up_predictions}, Actual: {self.actual_up_count} | Precision: {prec_up_str}, Recall: {rec_up_str}, F1: {f1_up_str}",
            f"    DOWN -> Predicted: {self.down_predictions}, Actual: {self.actual_down_count} | Precision: {prec_dn_str}, Recall: {rec_dn_str}, F1: {f1_dn_str}",
            f"    Confusion Matrix:        TP={self.true_positives}, FP={self.false_positives}, TN={self.true_negatives}, FN={self.false_negatives}",
            "================================================================================",
            f"Disclaimer: {self.disclaimer}",
            "================================================================================",
        ]
        return "\n".join(lines)
