"""History Package for Stock Market Prediction System.

Provides prediction outcome verification, realized market outcome persistence,
and post-hoc directional accuracy and error evaluation.
"""

from app.history.comparison import (
    ComparativeEvaluationReport,
    ModelComparator,
    ModelPerformanceRow,
    PairwiseComparison,
)
from app.history.contract import (
    ActualOutcome,
    EvaluationMetrics,
    VerificationRecord,
    VerificationStatus,
)
from app.history.evaluator import PredictionEvaluator
from app.history.verifier import OutcomeVerifier, parse_session_date

from app.history.reproducibility import (
    BaselineReproducibilityReport,
    BaselineReproducibilityStatus,
    ModelEvaluationRun,
    TemporalAlignmentAudit,
    audit_baseline_reproducibility,
)

__all__ = [
    "ActualOutcome",
    "EvaluationMetrics",
    "VerificationRecord",
    "VerificationStatus",
    "OutcomeVerifier",
    "PredictionEvaluator",
    "parse_session_date",
    "ModelComparator",
    "ComparativeEvaluationReport",
    "ModelPerformanceRow",
    "PairwiseComparison",
    "BaselineReproducibilityReport",
    "BaselineReproducibilityStatus",
    "ModelEvaluationRun",
    "TemporalAlignmentAudit",
    "audit_baseline_reproducibility",
]
