"""Training Package.

Provides technical feature matrix assembly, temporal dataset splits,
walk-forward validation, and machine-learning model training infrastructure.
"""

from app.training.baselines import (
    BaselineComparisonReport,
    BaselineComparisonRow,
    MajorityClassClassifier,
    RandomClassifier,
    evaluate_baseline_comparison,
)
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURE_PATTERNS,
    METADATA_COLUMNS,
    TARGET_COLUMNS,
    FeatureMatrixDataset,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)
from app.training.lightgbm_classifier import (
    LightGBMConfig,
    LightGBMDirectionClassifier,
)
from app.training.error_analysis import (
    FeatureQualityMetric,
    FeatureUsefulnessAudit,
    FoldErrorAnalysis,
    HighCorrelationPair,
    analyze_walk_forward_errors,
    audit_feature_usefulness,
    render_collinearity_table,
    render_feature_importance_comparison_table,
    render_fold_error_table,
)
from app.training.walk_forward import (
    WalkForwardFoldEvaluation,
    WalkForwardFoldSplit,
    WalkForwardReport,
    WalkForwardStrategySummary,
    evaluate_walk_forward,
    generate_walk_forward_splits,
)
from app.training.xgboost_classifier import (
    ChronologicalSplitResult,
    ClassificationMetrics,
    DirectionTrainingResult,
    XGBoostConfig,
    XGBoostDirectionClassifier,
    compute_classification_metrics,
    run_training_pipeline,
    split_chronological_holdout,
    train_baseline_classifier,
)

__all__ = [
    "FEATURE_COLUMNS",
    "FORBIDDEN_FEATURE_PATTERNS",
    "METADATA_COLUMNS",
    "TARGET_COLUMNS",
    "FeatureMatrixDataset",
    "assemble_feature_matrix",
    "validate_feature_matrix_isolation",
    "ChronologicalSplitResult",
    "ClassificationMetrics",
    "DirectionTrainingResult",
    "XGBoostConfig",
    "XGBoostDirectionClassifier",
    "compute_classification_metrics",
    "run_training_pipeline",
    "split_chronological_holdout",
    "train_baseline_classifier",
    "MajorityClassClassifier",
    "RandomClassifier",
    "BaselineComparisonRow",
    "BaselineComparisonReport",
    "evaluate_baseline_comparison",
    "LightGBMConfig",
    "LightGBMDirectionClassifier",
    "WalkForwardFoldSplit",
    "WalkForwardFoldEvaluation",
    "WalkForwardStrategySummary",
    "WalkForwardReport",
    "generate_walk_forward_splits",
    "evaluate_walk_forward",
    "FoldErrorAnalysis",
    "FeatureQualityMetric",
    "HighCorrelationPair",
    "FeatureUsefulnessAudit",
    "analyze_walk_forward_errors",
    "audit_feature_usefulness",
    "render_fold_error_table",
    "render_feature_importance_comparison_table",
    "render_collinearity_table",
]

