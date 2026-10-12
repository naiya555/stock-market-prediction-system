"""Prediction Package.

Provides target definition, machine-learning inference, LLM forecasting,
and multi-agent ensemble synthesis services.
"""

from app.prediction.target import (
    DirectionTarget,
    TargetObservation,
    calculate_forward_return,
    classify_forward_direction,
    compute_target_series,
    generate_direction_targets,
)

__all__ = [
    "DirectionTarget",
    "TargetObservation",
    "calculate_forward_return",
    "classify_forward_direction",
    "compute_target_series",
    "generate_direction_targets",
]
