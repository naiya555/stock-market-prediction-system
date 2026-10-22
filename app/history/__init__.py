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

from app.history.calibration import (
    ConfidenceInterval,
    PairedComparisonResult,
    ReliabilityBin,
    ReliabilityDiagramResult,
    compute_log_loss,
    compute_mcnemar_paired_test,
    compute_reliability_diagram,
    compute_wilson_score_interval,
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
    "ReliabilityBin",
    "ReliabilityDiagramResult",
    "ConfidenceInterval",
    "PairedComparisonResult",
    "compute_log_loss",
    "compute_reliability_diagram",
    "compute_wilson_score_interval",
    "compute_mcnemar_paired_test",
]
