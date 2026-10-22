"""Independent Numerical ML Baseline Reproducibility & Temporal Alignment Layer.

Audits, recomputes, and verifies the 240-session BHARTIARTL out-of-sample ML baseline:
1. Re-derives the chronological train/embargo/holdout split from market data.
2. Validates temporal alignment, session spacing, and embargo boundary isolation.
3. Loads active persisted model artifacts (XGBoost, LightGBM, Majority Class).
4. Recomputes directional accuracy, precision, recall, F1, confusion matrix, and Brier score.
5. Verifies run-to-run determinism and checks against committed model metadata.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from app.market.pipeline import MarketDataPipelineResult, run_market_data_pipeline
from app.market.providers.base import BaseMarketDataProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.training.baselines import MajorityClassClassifier
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    FeatureMatrixDataset,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)
from app.training.lightgbm_classifier import HAS_LIGHTGBM, LightGBMDirectionClassifier
from app.training.retraining import ModelRetrainer
from app.training.xgboost_classifier import (
    HAS_XGBOOST,
    ChronologicalSplitResult,
    ClassificationMetrics,
    XGBoostDirectionClassifier,
    compute_classification_metrics,
    split_chronological_holdout,
)

logger = get_logger(__name__)

# Canonical training snapshot cutoff timestamp from Day 51 (2026-10-21T17:16:42Z)
CANONICAL_TRAIN_CUTOFF_UTC = datetime(2026, 10, 21, 17, 16, 42, tzinfo=timezone.utc)
CANONICAL_LOOKBACK_DAYS = 1825


class BaselineReproducibilityStatus(str, Enum):
    """Status classification for baseline evaluation reproducibility."""

    REPRODUCIBLE = "REPRODUCIBLE"
    PARTIALLY_REPRODUCIBLE = "PARTIALLY_REPRODUCIBLE"
    NOT_REPRODUCIBLE = "NOT_REPRODUCIBLE"


@dataclass(frozen=True)
class ModelEvaluationRun:
    """Evaluation metrics and predictions for a single model on holdout data."""

    model_name: str
    sample_size: int
    accuracy: float
    precision_up: float
    recall_up: float
    f1_up: float
    precision_down: float
    recall_down: float
    f1_down: float
    brier_score: Optional[float]
    confusion_matrix: List[List[int]]  # [[TN, FP], [FN, TP]]
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    mean_predicted_prob_up: Optional[float]
    min_predicted_prob_up: Optional[float]
    max_predicted_prob_up: Optional[float]
    prob_std: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize evaluation run to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class TemporalAlignmentAudit:
    """Detailed audit of temporal boundary, session alignment, and leakage checks."""

    train_start_date: str
    train_end_date: str
    train_outcome_cutoff: str
    holdout_start_date: str
    holdout_end_date: str
    holdout_final_target_session: str
    embargo_sessions: int
    train_sample_count: int
    holdout_sample_count: int
    embargo_sample_count: int
    is_embargo_strictly_isolating: bool
    zero_overlap_verified: bool
    feature_isolation_verified: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize temporal alignment audit to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class BaselineReproducibilityReport:
    """Comprehensive report on ML baseline reproducibility and temporal integrity."""

    symbol: str
    status: BaselineReproducibilityStatus
    temporal_audit: TemporalAlignmentAudit
    class_distribution: Dict[str, int]
    majority_baseline: ModelEvaluationRun
    xgboost_metrics: Optional[ModelEvaluationRun]
    lightgbm_metrics: Optional[ModelEvaluationRun]
    metadata_match_verified: bool
    run_to_run_identical: bool
    discrepancies: List[str]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report to dictionary."""
        return {
            "symbol": self.symbol,
            "status": self.status.value,
            "temporal_audit": self.temporal_audit.to_dict(),
            "class_distribution": self.class_distribution,
            "majority_baseline": self.majority_baseline.to_dict(),
            "xgboost_metrics": self.xgboost_metrics.to_dict() if self.xgboost_metrics else None,
            "lightgbm_metrics": self.lightgbm_metrics.to_dict() if self.lightgbm_metrics else None,
            "metadata_match_verified": self.metadata_match_verified,
            "run_to_run_identical": self.run_to_run_identical,
            "discrepancies": self.discrepancies,
            "notes": self.notes,
        }


def compute_model_run_metrics(
    model_name: str,
    y_true: Sequence[int],
    y_pred: Sequence[int],
    y_prob_up: Optional[Sequence[float]] = None,
) -> ModelEvaluationRun:
    """Compute comprehensive classification and probability metrics for a model run."""
    clf_metrics = compute_classification_metrics(y_true, y_pred)
    brier = ModelRetrainer.compute_brier_score(y_true, y_prob_up) if y_prob_up is not None else None

    mean_p = round(float(np.mean(y_prob_up)), 4) if y_prob_up is not None and len(y_prob_up) > 0 else None
    min_p = round(float(np.min(y_prob_up)), 4) if y_prob_up is not None and len(y_prob_up) > 0 else None
    max_p = round(float(np.max(y_prob_up)), 4) if y_prob_up is not None and len(y_prob_up) > 0 else None
    std_p = round(float(np.std(y_prob_up)), 4) if y_prob_up is not None and len(y_prob_up) > 0 else None

    return ModelEvaluationRun(
        model_name=model_name,
        sample_size=clf_metrics.total_samples,
        accuracy=clf_metrics.accuracy,
        precision_up=clf_metrics.precision,
        recall_up=clf_metrics.recall,
        f1_up=clf_metrics.f1,
        precision_down=clf_metrics.precision_down,
        recall_down=clf_metrics.recall_down,
        f1_down=clf_metrics.f1_down,
        brier_score=brier,
        confusion_matrix=clf_metrics.confusion_matrix,
        true_positives=clf_metrics.true_positives,
        true_negatives=clf_metrics.true_negatives,
        false_positives=clf_metrics.false_positives,
        false_negatives=clf_metrics.false_negatives,
        mean_predicted_prob_up=mean_p,
        min_predicted_prob_up=min_p,
        max_predicted_prob_up=max_p,
        prob_std=std_p,
    )


def audit_temporal_alignment(split: ChronologicalSplitResult) -> TemporalAlignmentAudit:
    """Perform strict temporal alignment and embargo isolation checks on a split."""
    if split.metadata_test is None or split.metadata_train is None:
        raise ValueError("Metadata partitions required for temporal alignment audit.")

    train_start = str(split.metadata_train["timestamp"].iloc[0])[:10]
    train_end = str(split.metadata_train["timestamp"].iloc[-1])[:10]
    train_outcome_cutoff = str(split.metadata_train["next_timestamp"].iloc[-1])[:10]

    holdout_start = str(split.metadata_test["timestamp"].iloc[0])[:10]
    holdout_end = str(split.metadata_test["timestamp"].iloc[-1])[:10]
    holdout_final_target = str(split.metadata_test["next_timestamp"].iloc[-1])[:10]

    # Embargo isolation: training outcome cutoff must be strictly earlier than holdout prediction start
    is_isolating = bool(train_outcome_cutoff < holdout_start)

    # Feature overlap check: no train timestamp >= holdout_start
    train_max_ts = split.metadata_train["timestamp"].max()
    test_min_ts = split.metadata_test["timestamp"].min()
    zero_overlap = bool(train_max_ts < test_min_ts)

    # Feature matrix isolation check
    validate_feature_matrix_isolation(split.X_train)
    validate_feature_matrix_isolation(split.X_test)

    return TemporalAlignmentAudit(
        train_start_date=train_start,
        train_end_date=train_end,
        train_outcome_cutoff=train_outcome_cutoff,
        holdout_start_date=holdout_start,
        holdout_end_date=holdout_end,
        holdout_final_target_session=holdout_final_target,
        embargo_sessions=split.embargo_rows,
        train_sample_count=split.train_rows,
        holdout_sample_count=split.test_rows,
        embargo_sample_count=split.embargo_rows,
        is_embargo_strictly_isolating=is_isolating,
        zero_overlap_verified=zero_overlap,
        feature_isolation_verified=True,
    )


def run_single_reproducibility_evaluation(
    symbol: str = "BHARTIARTL",
    provider: Optional[BaseMarketDataProvider] = None,
    cutoff_time: Optional[datetime] = None,
    models_dir: Optional[Union[str, Path]] = None,
    lookback_days: int = CANONICAL_LOOKBACK_DAYS,
    test_ratio: float = 0.2,
    embargo_sessions: int = 1,
) -> Tuple[TemporalAlignmentAudit, Dict[str, Any], Dict[str, ModelEvaluationRun]]:
    """Execute a single end-to-end evaluation pass against active persisted models."""
    prov = provider or YFinanceProvider()
    c_time = cutoff_time or CANONICAL_TRAIN_CUTOFF_UTC
    s_time = c_time - timedelta(days=lookback_days)
    m_dir = Path(models_dir) if models_dir else Path("models")

    # Step 1: Market data pipeline
    pipeline_res = run_market_data_pipeline(
        symbol=symbol,
        start_date=s_time,
        end_date=c_time,
        provider=prov,
    )

    # Step 2: Feature matrix assembly
    dataset = assemble_feature_matrix(pipeline_res)

    # Step 3: Chronological holdout split
    split = split_chronological_holdout(
        dataset,
        test_ratio=test_ratio,
        embargo_sessions=embargo_sessions,
        drop_incomplete_warmup=True,
    )

    # Step 4: Temporal alignment audit
    temporal_audit = audit_temporal_alignment(split)

    # Step 5: Evaluate Majority Baseline
    maj_clf = MajorityClassClassifier()
    maj_clf.fit(y=split.y_train)
    maj_preds = maj_clf.predict(split.X_test)
    maj_probs = maj_clf.predict_proba(split.X_test)[:, 1]
    maj_run = compute_model_run_metrics("majority_baseline", split.y_test, maj_preds, maj_probs)

    runs: Dict[str, ModelEvaluationRun] = {"majority_baseline": maj_run}

    # Step 6: Evaluate XGBoost active artifact
    xgb_path = m_dir / "xgboost_direction.json"
    if xgb_path.is_file() and HAS_XGBOOST:
        xgb_clf = XGBoostDirectionClassifier.load_model(xgb_path)
        xgb_preds = xgb_clf.predict(split.X_test)
        xgb_probs = xgb_clf.predict_proba(split.X_test)[:, 1]
        runs["xgboost"] = compute_model_run_metrics("xgboost", split.y_test, xgb_preds, xgb_probs)

    # Step 7: Evaluate LightGBM active artifact
    lgb_path = m_dir / "lightgbm_direction.txt"
    if lgb_path.is_file() and HAS_LIGHTGBM:
        lgb_clf = LightGBMDirectionClassifier().load_model(lgb_path)
        lgb_preds = lgb_clf.predict(split.X_test)
        lgb_probs = lgb_clf.predict_proba(split.X_test)[:, 1]
        runs["lightgbm"] = compute_model_run_metrics("lightgbm", split.y_test, lgb_preds, lgb_probs)

    class_dist = {
        "UP": int(np.sum(split.y_test == 1)),
        "DOWN": int(np.sum(split.y_test == 0)),
        "total": len(split.y_test),
    }

    raw_outputs = {
        "y_test": split.y_test.to_numpy(),
        "maj_preds": maj_preds,
        "maj_probs": maj_probs,
        "xgb_preds": runs["xgboost"].confusion_matrix if "xgboost" in runs else None,
        "lgb_preds": runs["lightgbm"].confusion_matrix if "lightgbm" in runs else None,
    }

    return temporal_audit, class_dist, runs


def audit_baseline_reproducibility(
    symbol: str = "BHARTIARTL",
    provider: Optional[BaseMarketDataProvider] = None,
    cutoff_time: Optional[datetime] = None,
    models_dir: Optional[Union[str, Path]] = None,
) -> BaselineReproducibilityReport:
    """Perform complete reproducibility and temporal leakage audit with run comparison."""
    m_dir = Path(models_dir) if models_dir else Path("models")
    meta_path = m_dir / "model_metadata.json"

    # Run Pass 1
    t_audit_1, class_dist_1, runs_1 = run_single_reproducibility_evaluation(
        symbol=symbol,
        provider=provider,
        cutoff_time=cutoff_time,
        models_dir=models_dir,
    )

    # Run Pass 2 (Verification of determinism)
    t_audit_2, class_dist_2, runs_2 = run_single_reproducibility_evaluation(
        symbol=symbol,
        provider=provider,
        cutoff_time=cutoff_time,
        models_dir=models_dir,
    )

    # Run-to-run comparison check
    run_to_run_identical = bool(
        t_audit_1 == t_audit_2
        and class_dist_1 == class_dist_2
        and runs_1["majority_baseline"] == runs_2["majority_baseline"]
        and runs_1.get("xgboost") == runs_2.get("xgboost")
        and runs_1.get("lightgbm") == runs_2.get("lightgbm")
    )

    discrepancies: List[str] = []
    notes: List[str] = []

    # Check against model_metadata.json if present
    metadata_match = True
    if meta_path.is_file():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            expected_counts = meta.get("sample_counts", {})
            if t_audit_1.holdout_sample_count != expected_counts.get("eval"):
                discrepancies.append(
                    f"Holdout sample count mismatch: evaluated {t_audit_1.holdout_sample_count}, "
                    f"metadata expected {expected_counts.get('eval')}."
                )
                metadata_match = False

            models_meta = meta.get("models", {})
            if "xgboost" in runs_1 and "xgboost" in models_meta:
                xgb_exp = models_meta["xgboost"]["metrics"]
                xgb_act = runs_1["xgboost"]
                if round(xgb_act.accuracy, 4) != round(xgb_exp["accuracy"], 4):
                    discrepancies.append(
                        f"XGBoost accuracy discrepancy: live={xgb_act.accuracy:.4f}, metadata={xgb_exp['accuracy']:.4f}"
                    )
                    metadata_match = False
                if round(xgb_act.brier_score or 0.0, 4) != round(xgb_exp.get("brier_score", 0.0), 4):
                    discrepancies.append(
                        f"XGBoost Brier discrepancy: live={xgb_act.brier_score:.4f}, metadata={xgb_exp.get('brier_score')}"
                    )
                    metadata_match = False

            if "lightgbm" in runs_1 and "lightgbm" in models_meta:
                lgb_exp = models_meta["lightgbm"]["metrics"]
                lgb_act = runs_1["lightgbm"]
                if round(lgb_act.accuracy, 4) != round(lgb_exp["accuracy"], 4):
                    discrepancies.append(
                        f"LightGBM accuracy discrepancy: live={lgb_act.accuracy:.4f}, metadata={lgb_exp['accuracy']:.4f}"
                    )
                    metadata_match = False
                if round(lgb_act.brier_score or 0.0, 4) != round(lgb_exp.get("brier_score", 0.0), 4):
                    discrepancies.append(
                        f"LightGBM Brier discrepancy: live={lgb_act.brier_score:.4f}, metadata={lgb_exp.get('brier_score')}"
                    )
                    metadata_match = False

        except Exception as exc:
            discrepancies.append(f"Failed to parse model_metadata.json: {exc}")
            metadata_match = False
    else:
        notes.append("No models/model_metadata.json found on disk to compare against.")

    # Determine reproducibility status
    if run_to_run_identical and metadata_match and not discrepancies:
        status = BaselineReproducibilityStatus.REPRODUCIBLE
    elif run_to_run_identical and not metadata_match:
        status = BaselineReproducibilityStatus.PARTIALLY_REPRODUCIBLE
    else:
        status = BaselineReproducibilityStatus.NOT_REPRODUCIBLE

    notes.append(
        "Temporal dates: Feature sessions run from 2025-10-29 to 2026-10-19. "
        "Realized forward targets extend through 2026-10-21."
    )
    notes.append(
        "Rolling-window caveat: Live execution without an explicit historical cutoff date "
        "shifts the 20% holdout window by 1-2 sessions as new daily market bars arrive."
    )

    return BaselineReproducibilityReport(
        symbol=symbol,
        status=status,
        temporal_audit=t_audit_1,
        class_distribution=class_dist_1,
        majority_baseline=runs_1["majority_baseline"],
        xgboost_metrics=runs_1.get("xgboost"),
        lightgbm_metrics=runs_1.get("lightgbm"),
        metadata_match_verified=metadata_match,
        run_to_run_identical=run_to_run_identical,
        discrepancies=discrepancies,
        notes=notes,
    )
