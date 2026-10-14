"""Prediction Package.

Provides target definition, machine-learning inference, LLM forecasting,
and multi-agent ensemble synthesis services.
"""

from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.target import (
    DirectionTarget,
    TargetObservation,
    calculate_forward_return,
    classify_forward_direction,
    compute_target_series,
    generate_direction_targets,
)


def __getattr__(name: str):
    if name in ("PredictionService", "train_and_persist_baseline_model", "MIN_WARMUP_BARS"):
        from app.prediction.service import (
            MIN_WARMUP_BARS,
            PredictionService,
            train_and_persist_baseline_model,
        )

        globals()["PredictionService"] = PredictionService
        globals()["train_and_persist_baseline_model"] = train_and_persist_baseline_model
        globals()["MIN_WARMUP_BARS"] = MIN_WARMUP_BARS
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "DirectionTarget",
    "TargetObservation",
    "calculate_forward_return",
    "classify_forward_direction",
    "compute_target_series",
    "generate_direction_targets",
    "PredictionStatus",
    "PredictionRequest",
    "PredictionDataQuality",
    "PredictionResult",
    "PredictionService",
    "train_and_persist_baseline_model",
    "MIN_WARMUP_BARS",
]
