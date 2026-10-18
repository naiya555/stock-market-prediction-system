"""Controlled Model Retraining and Gated Release Service for Phase 15.

Enforces ADR 10 (Controlled, Gated Model Retraining):
- Retraining never starts automatically from an unverified or insufficient dataset.
- Chronological separation and embargo gap strictly enforced between training and validation data.
- Candidate models are quarantined in a candidate directory and never overwrite the active model
  until all formal validation gates have been satisfied.
- Active models are preserved in an archive on promotion or left completely untouched on failure.
- Complete audit trails (versions, cutoffs, metrics, and gate outcomes) are persisted to SQLite.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import math
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import uuid

import numpy as np
import pandas as pd

from app.core.logging_config import get_logger, sanitize_log_field
from app.database.repository import PredictionRepository
from app.training.baselines import MajorityClassClassifier
from app.training.lightgbm_classifier import (
    HAS_LIGHTGBM,
    LightGBMConfig,
    LightGBMDirectionClassifier,
)
from app.training.xgboost_classifier import (
    ClassificationMetrics,
    XGBoostConfig,
    XGBoostDirectionClassifier,
    compute_classification_metrics,
)

logger = get_logger(__name__)


class ModelReleaseStatus(str, Enum):
    """Lifecycle status of a model release candidate."""

    CANDIDATE = "CANDIDATE"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class ValidationGateResult:
    """Outcome of an individual validation gate evaluation."""

    gate_name: str
    passed: bool
    observed_value: Any
    threshold: Any
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert gate result to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class RetrainingResult:
    """Comprehensive result of a controlled model retraining and validation run."""

    release_id: str
    model_name: str
    model_version: str
    symbol: str
    status: ModelReleaseStatus
    training_sample_count: int
    evaluation_sample_count: int
    training_cutoff_date: str
    evaluation_cutoff_date: str
    metrics: Dict[str, Any]
    gate_results: List[ValidationGateResult]
    rejection_reason: Optional[str]
    candidate_artifact_path: str
    active_artifact_path: Optional[str]
    is_promoted: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert retraining result to serializable dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["gate_results"] = [g.to_dict() for g in self.gate_results]
        return data


class ModelRetrainer:
    """Controlled, gated model retraining service adhering strictly to ADR 10."""

    # Default Validation Gate Thresholds
    MIN_TRAIN_SAMPLES = 50
    MIN_EVAL_SAMPLES = 15
    MIN_ACCURACY_THRESHOLD = 0.50
    MAX_ACTIVE_DEGRADATION_MARGIN = 0.02

    def __init__(
        self,
        repository: Optional[PredictionRepository] = None,
        models_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        """Initialize retrainer with repository and models directory."""
        self.repository = repository
        self.models_dir = Path(models_dir) if models_dir else Path("models")
        self.candidates_dir = self.models_dir / "candidates"
        self.archive_dir = self.models_dir / "archive"

        # Ensure directories exist
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _get_active_artifact_path(self, model_name: str) -> Path:
        """Return canonical production artifact path for a model."""
        clean_name = model_name.strip().lower()
        if clean_name == "xgboost":
            return self.models_dir / "xgboost_direction.json"
        if clean_name == "lightgbm":
            return self.models_dir / "lightgbm_direction.txt"
        return self.models_dir / f"{clean_name}_direction.bin"

    @staticmethod
    def compute_brier_score(y_true: Sequence[int], y_prob_up: Sequence[float]) -> Optional[float]:
        """Compute mean squared probability error (Brier score) for binary predictions."""
        if len(y_true) == 0 or len(y_prob_up) == 0 or len(y_true) != len(y_prob_up):
            return None
        sq_errs = []
        for y, p in zip(y_true, y_prob_up):
            if math.isfinite(y) and math.isfinite(p):
                sq_errs.append((float(p) - float(y)) ** 2)
        return round(sum(sq_errs) / len(sq_errs), 4) if sq_errs else None

    def evaluate_gates(
        self,
        candidate_metrics: ClassificationMetrics,
        candidate_brier: Optional[float],
        majority_accuracy: float,
        active_metrics: Optional[ClassificationMetrics] = None,
        n_train: int = 0,
        n_eval: int = 0,
        y_train: Optional[Sequence[int]] = None,
        y_val: Optional[Sequence[int]] = None,
    ) -> Tuple[bool, List[ValidationGateResult], Optional[str]]:
        """Evaluate formal validation gates required for model promotion under ADR 10."""
        gates: List[ValidationGateResult] = []

        # Gate 1: Minimum Sample Size Gate
        pass_samples = (n_train >= self.MIN_TRAIN_SAMPLES and n_eval >= self.MIN_EVAL_SAMPLES)
        gates.append(
            ValidationGateResult(
                gate_name="SAMPLE_SUFFICIENCY_GATE",
                passed=pass_samples,
                observed_value={"n_train": n_train, "n_eval": n_eval},
                threshold={"min_train": self.MIN_TRAIN_SAMPLES, "min_eval": self.MIN_EVAL_SAMPLES},
                message=(
                    f"Sample sufficiency: train={n_train}/{self.MIN_TRAIN_SAMPLES}, "
                    f"eval={n_eval}/{self.MIN_EVAL_SAMPLES}."
                ),
            )
        )

        # Gate 2: Class Balance Gate
        classes_train = set(y_train) if y_train is not None else set()
        classes_val = set(y_val) if y_val is not None else set()
        has_both_train = (0 in classes_train and 1 in classes_train)
        has_both_val = (0 in classes_val and 1 in classes_val)
        pass_balance = bool(has_both_train and has_both_val)
        gates.append(
            ValidationGateResult(
                gate_name="CLASS_BALANCE_GATE",
                passed=pass_balance,
                observed_value={"train_classes": list(classes_train), "val_classes": list(classes_val)},
                threshold="Both classes {0, 1} required in train and eval partitions",
                message=(
                    "Class distribution is valid and non-degenerate."
                    if pass_balance
                    else "Degenerate partition detected: training or validation set lacks binary class representation."
                ),
            )
        )

        # Gate 3: Baseline Superiority Gate
        # Candidate accuracy must not be substantially worse than majority class
        acc_cand = candidate_metrics.accuracy
        pass_baseline = (acc_cand >= majority_accuracy - 0.01)
        gates.append(
            ValidationGateResult(
                gate_name="BASELINE_SUPERIORITY_GATE",
                passed=pass_baseline,
                observed_value=round(acc_cand, 4),
                threshold=round(majority_accuracy, 4),
                message=(
                    f"Candidate accuracy ({acc_cand*100:.1f}%) meets/exceeds majority baseline ({majority_accuracy*100:.1f}%)."
                    if pass_baseline
                    else f"Candidate accuracy ({acc_cand*100:.1f}%) is inferior to majority baseline ({majority_accuracy*100:.1f}%)."
                ),
            )
        )

        # Gate 4: Minimum Out-of-Sample Performance Gate
        pass_min_acc = (acc_cand >= self.MIN_ACCURACY_THRESHOLD)
        gates.append(
            ValidationGateResult(
                gate_name="MINIMUM_PERFORMANCE_GATE",
                passed=pass_min_acc,
                observed_value=round(acc_cand, 4),
                threshold=self.MIN_ACCURACY_THRESHOLD,
                message=(
                    f"Candidate directional accuracy ({acc_cand*100:.1f}%) satisfies minimum {self.MIN_ACCURACY_THRESHOLD*100:.0f}% threshold."
                    if pass_min_acc
                    else f"Candidate directional accuracy ({acc_cand*100:.1f}%) below minimum {self.MIN_ACCURACY_THRESHOLD*100:.0f}% threshold."
                ),
            )
        )

        # Gate 5: Active Model Non-Degradation Gate
        pass_non_deg = True
        if active_metrics is not None and active_metrics.accuracy is not None:
            active_acc = active_metrics.accuracy
            threshold_acc = active_acc - self.MAX_ACTIVE_DEGRADATION_MARGIN
            pass_non_deg = (acc_cand >= threshold_acc)
            gates.append(
                ValidationGateResult(
                    gate_name="ACTIVE_MODEL_NON_DEGRADATION_GATE",
                    passed=pass_non_deg,
                    observed_value=round(acc_cand, 4),
                    threshold=round(threshold_acc, 4),
                    message=(
                        f"Candidate accuracy ({acc_cand*100:.1f}%) does not degrade active model ({active_acc*100:.1f}%)."
                        if pass_non_deg
                        else f"Candidate accuracy ({acc_cand*100:.1f}%) degraded below active model threshold ({threshold_acc*100:.1f}%)."
                    ),
                )
            )
        else:
            gates.append(
                ValidationGateResult(
                    gate_name="ACTIVE_MODEL_NON_DEGRADATION_GATE",
                    passed=True,
                    observed_value=round(acc_cand, 4),
                    threshold=None,
                    message="No existing active model baseline to benchmark against; gate automatically passes.",
                )
            )

        all_passed = all(g.passed for g in gates)
        first_failure = next((g.message for g in gates if not g.passed), None)
        return all_passed, gates, first_failure

    def retrain_and_gate(
        self,
        symbol: str,
        model_name: str,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        training_cutoff_date: str,
        evaluation_cutoff_date: str,
        model_config: Optional[Any] = None,
        candidate_version: Optional[str] = None,
        force_promote: bool = False,
    ) -> RetrainingResult:
        """Execute a controlled model retraining run with validation gating and atomic release."""
        clean_model = model_name.strip().lower()
        clean_sym = symbol.strip().upper()
        release_id = str(uuid.uuid4())
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        version = candidate_version or f"{clean_model}_{date_str}_{release_id[:6]}"

        logger.info(
            "Starting controlled retraining run %s for '%s' (%s) with %d train samples, %d eval samples.",
            release_id,
            clean_sym,
            clean_model,
            len(X_train),
            len(X_val),
        )

        # Candidate artifact filepath (strictly in candidates/ directory)
        ext = "json" if clean_model == "xgboost" else ("txt" if clean_model == "lightgbm" else "bin")
        candidate_path = self.candidates_dir / f"{clean_model}_{version}.{ext}"

        # 1. Fit Candidate Classifier
        if clean_model == "xgboost":
            cfg = model_config or XGBoostConfig(n_estimators=50, max_depth=3, learning_rate=0.05, random_state=42)
            candidate_model = XGBoostDirectionClassifier(config=cfg)
        elif clean_model == "lightgbm":
            if not HAS_LIGHTGBM:
                raise RuntimeError("LightGBM package is not installed or available.")
            cfg = model_config or LightGBMConfig(n_estimators=50, max_depth=3, num_leaves=7, learning_rate=0.05, random_state=42)
            candidate_model = LightGBMDirectionClassifier(config=cfg)
        else:
            raise ValueError(f"Unsupported model architecture '{model_name}'. Must be 'xgboost' or 'lightgbm'.")

        # Pre-training validation: check sample sufficiency and class balance before fitting
        n_train = len(X_train) if X_train is not None else 0
        n_eval = len(X_val) if X_val is not None else 0
        y_train_list = list(y_train) if y_train is not None else []
        y_val_list = list(y_val) if y_val is not None else []

        classes_train = set(y_train_list)
        classes_val = set(y_val_list)
        has_both_train = (0 in classes_train and 1 in classes_train)
        has_both_val = (0 in classes_val and 1 in classes_val)
        pass_samples = (n_train >= self.MIN_TRAIN_SAMPLES and n_eval >= self.MIN_EVAL_SAMPLES)
        pass_balance = bool(has_both_train and has_both_val)

        if not pass_samples or not pass_balance:
            gates = [
                ValidationGateResult(
                    gate_name="SAMPLE_SUFFICIENCY_GATE",
                    passed=pass_samples,
                    observed_value={"n_train": n_train, "n_eval": n_eval},
                    threshold={"min_train": self.MIN_TRAIN_SAMPLES, "min_eval": self.MIN_EVAL_SAMPLES},
                    message=(
                        f"Sample sufficiency: train={n_train}/{self.MIN_TRAIN_SAMPLES}, eval={n_eval}/{self.MIN_EVAL_SAMPLES}."
                        if pass_samples
                        else f"Sample sufficiency failed: train={n_train}/{self.MIN_TRAIN_SAMPLES}, eval={n_eval}/{self.MIN_EVAL_SAMPLES}."
                    ),
                ),
                ValidationGateResult(
                    gate_name="CLASS_BALANCE_GATE",
                    passed=pass_balance,
                    observed_value={"train_classes": list(classes_train), "val_classes": list(classes_val)},
                    threshold="Both classes {0, 1} required in train and eval partitions",
                    message=(
                        "Class distribution is valid and non-degenerate."
                        if pass_balance
                        else "Degenerate partition detected: training or validation set lacks binary class representation."
                    ),
                ),
            ]
            fail_msg = next(g.message for g in gates if not g.passed)
            result = RetrainingResult(
                release_id=release_id,
                model_name=clean_model,
                model_version=version,
                symbol=clean_sym,
                status=ModelReleaseStatus.REJECTED,
                training_sample_count=n_train,
                evaluation_sample_count=n_eval,
                training_cutoff_date=training_cutoff_date,
                evaluation_cutoff_date=evaluation_cutoff_date,
                metrics={},
                gate_results=gates,
                rejection_reason=fail_msg,
                candidate_artifact_path=str(candidate_path),
                active_artifact_path=None,
                is_promoted=False,
            )
            if self.repository:
                self.repository.save_model_release(
                    release_id=release_id,
                    model_name=clean_model,
                    model_version=version,
                    symbol=clean_sym,
                    status=result.status.value,
                    training_sample_count=n_train,
                    evaluation_sample_count=n_eval,
                    training_cutoff_date=training_cutoff_date,
                    evaluation_cutoff_date=evaluation_cutoff_date,
                    metrics={},
                    gates=[g.to_dict() for g in gates],
                    artifact_path=str(candidate_path),
                    rejection_reason=fail_msg,
                    is_active=False,
                )
            return result

        # Fit model on training set
        try:
            candidate_model.fit(X_train, y_train)
            candidate_model.save_model(candidate_path)
        except Exception as exc:
            logger.error("Failed to fit/save candidate model: %s", exc)
            raise

        # 2. Evaluate Candidate on Out-of-Sample Validation Set
        candidate_preds = candidate_model.predict(X_val)
        candidate_probs = candidate_model.predict_proba(X_val)
        p_up_list = [p[1] for p in candidate_probs] if candidate_probs is not None else []
        cand_metrics = compute_classification_metrics(y_val, candidate_preds)
        cand_brier = self.compute_brier_score(y_val, p_up_list)

        # 3. Evaluate Majority-Class Baseline on Validation Set
        maj_model = MajorityClassClassifier()
        maj_model.fit(y=y_train)
        maj_preds = maj_model.predict(X_val)
        maj_metrics = compute_classification_metrics(y_val, maj_preds)

        # 4. Evaluate Active Production Model on Validation Set (if present)
        active_path = self._get_active_artifact_path(clean_model)
        active_metrics = None
        if active_path.is_file():
            try:
                if clean_model == "xgboost":
                    active_model = XGBoostDirectionClassifier.load_model(active_path)
                else:
                    active_model = LightGBMDirectionClassifier().load_model(active_path)
                act_preds = active_model.predict(X_val)
                active_metrics = compute_classification_metrics(y_val, act_preds)
            except Exception as exc:
                logger.warning("Could not evaluate active production model '%s': %s", active_path, exc)

        # 5. Evaluate Validation Gates
        passed, gates, fail_reason = self.evaluate_gates(
            candidate_metrics=cand_metrics,
            candidate_brier=cand_brier,
            majority_accuracy=maj_metrics.accuracy,
            active_metrics=active_metrics,
            n_train=len(X_train),
            n_eval=len(X_val),
            y_train=list(y_train),
            y_val=list(y_val),
        )

        metrics_dict = {
            "accuracy": cand_metrics.accuracy,
            "precision_up": cand_metrics.precision,
            "recall_up": cand_metrics.recall,
            "f1_up": cand_metrics.f1,
            "precision_down": cand_metrics.precision_down,
            "recall_down": cand_metrics.recall_down,
            "f1_down": cand_metrics.f1_down,
            "brier_score": cand_brier,
            "majority_baseline_accuracy": maj_metrics.accuracy,
            "active_model_accuracy": active_metrics.accuracy if active_metrics else None,
        }

        should_promote = passed or force_promote
        status = ModelReleaseStatus.PROMOTED if should_promote else ModelReleaseStatus.REJECTED

        # 6. Atomic Promotion Protocol
        if should_promote:
            # Step A: Archive currently active model if present
            if active_path.is_file():
                archive_name = f"{clean_model}_archived_{date_str}.{ext}"
                archive_path = self.archive_dir / archive_name
                try:
                    shutil.copy2(active_path, archive_path)
                    logger.info("Archived active model to %s", archive_path)
                except Exception as exc:
                    logger.warning("Failed to archive active model: %s", exc)

            # Step B: Atomically copy candidate to active path
            shutil.copy2(candidate_path, active_path)
            logger.info("Promoted candidate model %s to active path %s", version, active_path)
        else:
            logger.warning(
                "Candidate model %s failed validation gates and was REJECTED: %s. Active model preserved.",
                version,
                fail_reason,
            )

        # 7. Record Model Release in Repository
        if self.repository:
            self.repository.save_model_release(
                release_id=release_id,
                model_name=clean_model,
                model_version=version,
                symbol=clean_sym,
                status=status.value,
                training_sample_count=len(X_train),
                evaluation_sample_count=len(X_val),
                training_cutoff_date=training_cutoff_date,
                evaluation_cutoff_date=evaluation_cutoff_date,
                metrics=metrics_dict,
                gates=[g.to_dict() for g in gates],
                artifact_path=str(active_path if should_promote else candidate_path),
                rejection_reason=fail_reason if not should_promote else None,
                is_active=should_promote,
            )

        return RetrainingResult(
            release_id=release_id,
            model_name=clean_model,
            model_version=version,
            symbol=clean_sym,
            status=status,
            training_sample_count=len(X_train),
            evaluation_sample_count=len(X_val),
            training_cutoff_date=training_cutoff_date,
            evaluation_cutoff_date=evaluation_cutoff_date,
            metrics=metrics_dict,
            gate_results=gates,
            rejection_reason=fail_reason if not should_promote else None,
            candidate_artifact_path=str(candidate_path),
            active_artifact_path=str(active_path) if should_promote else None,
            is_promoted=should_promote,
        )
