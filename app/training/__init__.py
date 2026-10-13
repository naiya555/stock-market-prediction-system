"""Training Package.

Provides technical feature matrix assembly, temporal dataset splits,
walk-forward validation, and machine-learning model training infrastructure.
"""

from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURE_PATTERNS,
    METADATA_COLUMNS,
    TARGET_COLUMNS,
    FeatureMatrixDataset,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
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
]
