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

__all__ = [
    "FEATURE_COLUMNS",
    "FORBIDDEN_FEATURE_PATTERNS",
    "METADATA_COLUMNS",
    "TARGET_COLUMNS",
    "FeatureMatrixDataset",
    "assemble_feature_matrix",
    "validate_feature_matrix_isolation",
]
