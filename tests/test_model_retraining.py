"""Unit and integration tests for Controlled Model Retraining & Version Tracking (ADR 10)."""

from pathlib import Path
import shutil
import tempfile
from typing import Generator
import pytest
import numpy as np
import pandas as pd

from app.database.repository import PredictionRepository
from app.training.xgboost_classifier import XGBoostConfig, ClassificationMetrics
from app.training.retraining import (
    ModelReleaseStatus,
    ModelRetrainer,
    RetrainingResult,
    ValidationGateResult,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for models and database testing."""
    td = Path(tempfile.mkdtemp(prefix="test_retraining_"))
    yield td
    shutil.rmtree(td, ignore_errors=True)


@pytest.fixture
def test_repo(temp_dir: Path) -> PredictionRepository:
    """Create a temporary repository."""
    db_path = temp_dir / "test_predictions.db"
    return PredictionRepository(str(db_path))


@pytest.fixture
def synthetic_datasets():
    """Create synthetic training and validation feature matrices."""
    np.random.seed(42)
    # 80 training samples, 25 validation samples
    n_train = 80
    n_val = 25
    n_features = 5
    feature_cols = [f"feat_{i}" for i in range(n_features)]

    X_train = pd.DataFrame(np.random.randn(n_train, n_features), columns=feature_cols)
    # Informative target so model learns and achieves > 55% accuracy
    y_train = pd.Series((X_train["feat_0"] + 0.5 * X_train["feat_1"] > 0).astype(int))

    X_val = pd.DataFrame(np.random.randn(n_val, n_features), columns=feature_cols)
    y_val = pd.Series((X_val["feat_0"] + 0.5 * X_val["feat_1"] > 0).astype(int))

    return X_train, y_train, X_val, y_val


def test_brier_score_computation():
    """Verify Brier score calculation edge cases."""
    # Perfect predictions: y=1 prob=1.0, y=0 prob=0.0 -> score = 0.0
    score_perf = ModelRetrainer.compute_brier_score([1, 0], [1.0, 0.0])
    assert score_perf == 0.0

    # Inverted predictions: y=1 prob=0.0, y=0 prob=1.0 -> score = 1.0
    score_inv = ModelRetrainer.compute_brier_score([1, 0], [0.0, 1.0])
    assert score_inv == 1.0

    # Empty inputs
    assert ModelRetrainer.compute_brier_score([], []) is None
    # Mismatched length
    assert ModelRetrainer.compute_brier_score([1], [0.5, 0.5]) is None


def test_retraining_success_and_atomic_promotion(temp_dir: Path, test_repo: PredictionRepository, synthetic_datasets):
    """Candidate meeting all gates is promoted, copied to active path, and tracked in database."""
    X_train, y_train, X_val, y_val = synthetic_datasets
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    result = retrainer.retrain_and_gate(
        symbol="RELIANCE.BSE",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-01-01",
        evaluation_cutoff_date="2025-02-01",
        candidate_version="xgb_v1_test",
    )

    assert result.status == ModelReleaseStatus.PROMOTED
    assert result.is_promoted is True
    assert result.rejection_reason is None
    assert all(gate.passed for gate in result.gate_results)

    # Candidate file should exist in candidates dir
    candidate_path = Path(result.candidate_artifact_path)
    assert candidate_path.is_file()

    # Active production file should exist
    active_path = models_dir / "xgboost_direction.json"
    assert active_path.is_file()
    assert result.active_artifact_path == str(active_path)

    # Repository verification
    active_release = test_repo.get_active_model_release("xgboost")
    assert active_release is not None
    assert active_release["release_id"] == result.release_id
    assert active_release["model_version"] == "xgb_v1_test"
    assert active_release["is_active"] == 1
    assert active_release["status"] == "PROMOTED"
    assert active_release["training_sample_count"] == 80
    assert active_release["evaluation_sample_count"] == 25


def test_retraining_rejection_on_insufficient_samples(temp_dir: Path, test_repo: PredictionRepository):
    """Candidate fails Gate 1 when samples are below minimum threshold."""
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    # Too few samples (< 50 train, < 15 eval)
    X_train = pd.DataFrame({"feat_0": [0.1, -0.2, 0.3], "feat_1": [0.5, 0.2, -0.1]})
    y_train = pd.Series([1, 0, 1])
    X_val = pd.DataFrame({"feat_0": [0.2, -0.1], "feat_1": [0.3, -0.4]})
    y_val = pd.Series([1, 0])

    result = retrainer.retrain_and_gate(
        symbol="TCS.BSE",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-01-01",
        evaluation_cutoff_date="2025-02-01",
        candidate_version="xgb_insufficient_samples",
    )

    assert result.status == ModelReleaseStatus.REJECTED
    assert result.is_promoted is False
    assert result.active_artifact_path is None
    assert "Sample sufficiency" in (result.rejection_reason or "")

    # Active production file should NOT exist
    active_path = models_dir / "xgboost_direction.json"
    assert not active_path.is_file()

    # Repository record should reflect rejection
    stored = test_repo.get_model_release(result.release_id)
    assert stored is not None
    assert stored["status"] == "REJECTED"
    assert stored["is_active"] == 0
    assert stored["rejection_reason"] is not None


def test_retraining_rejection_on_degenerate_class_distribution(temp_dir: Path, test_repo: PredictionRepository):
    """Candidate fails Gate 2 when training or validation data lacks binary diversity."""
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    n_train = 60
    n_val = 20
    X_train = pd.DataFrame(np.random.randn(n_train, 3), columns=["f0", "f1", "f2"])
    # All 1s in training set (degenerate)
    y_train = pd.Series([1] * n_train)
    X_val = pd.DataFrame(np.random.randn(n_val, 3), columns=["f0", "f1", "f2"])
    y_val = pd.Series([1] * (n_val // 2) + [0] * (n_val // 2))

    result = retrainer.retrain_and_gate(
        symbol="INFY.BSE",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-01-01",
        evaluation_cutoff_date="2025-02-01",
    )

    assert result.status == ModelReleaseStatus.REJECTED
    assert result.is_promoted is False
    assert "Degenerate partition" in (result.rejection_reason or "")


def test_active_model_preserved_when_candidate_degrades_performance(temp_dir: Path, test_repo: PredictionRepository, synthetic_datasets):
    """When a candidate performs worse than the existing active model, active model is preserved."""
    X_train, y_train, X_val, y_val = synthetic_datasets
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    # 1. Promote first model (v1)
    res_v1 = retrainer.retrain_and_gate(
        symbol="RELIANCE.BSE",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-01-01",
        evaluation_cutoff_date="2025-02-01",
        candidate_version="xgb_v1_good",
    )
    assert res_v1.is_promoted is True
    active_path = models_dir / "xgboost_direction.json"
    with open(active_path, "rb") as f:
        v1_bytes = f.read()

    # 2. Train a degraded candidate v2 using pure random noise labels
    np.random.seed(999)
    y_train_noise = pd.Series(np.random.binomial(1, 0.5, size=len(X_train)))
    res_v2 = retrainer.retrain_and_gate(
        symbol="RELIANCE.BSE",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train_noise,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-02-01",
        evaluation_cutoff_date="2025-03-01",
        candidate_version="xgb_v2_degraded",
    )

    assert res_v2.is_promoted is False
    assert res_v2.status == ModelReleaseStatus.REJECTED

    # Active model file must be completely untouched and identical to v1
    with open(active_path, "rb") as f:
        current_bytes = f.read()
    assert current_bytes == v1_bytes

    # Repository still reports v1 as the active release
    active_release = test_repo.get_active_model_release("xgboost")
    assert active_release is not None
    assert active_release["model_version"] == "xgb_v1_good"
    assert active_release["is_active"] == 1


def test_empty_dataset_handling(temp_dir: Path, test_repo: PredictionRepository):
    """Empty datasets are cleanly caught and rejected without unhandled crash."""
    retrainer = ModelRetrainer(repository=test_repo, models_dir=temp_dir / "models")
    res = retrainer.retrain_and_gate(
        symbol="NIFTY50",
        model_name="xgboost",
        X_train=pd.DataFrame(),
        y_train=pd.Series(dtype=int),
        X_val=pd.DataFrame(),
        y_val=pd.Series(dtype=int),
        training_cutoff_date="2025-01-01",
        evaluation_cutoff_date="2025-02-01",
    )
    assert res.status == ModelReleaseStatus.REJECTED
    assert res.is_promoted is False
    assert "Sample sufficiency failed" in (res.rejection_reason or "")


def test_repository_model_release_lifecycle(test_repo: PredictionRepository):
    """Test repository listing, retrieval, and active release queries."""
    # Insert release 1 (promoted)
    test_repo.save_model_release(
        release_id="rel_1",
        model_name="xgboost",
        model_version="v1.0",
        symbol="RELIANCE.BSE",
        status="PROMOTED",
        training_sample_count=100,
        evaluation_sample_count=30,
        training_cutoff_date="2025-01-01",
        evaluation_cutoff_date="2025-02-01",
        metrics={"accuracy": 0.58},
        gates=[{"gate": "sample", "passed": True}],
        artifact_path="models/xgboost_direction.json",
        is_active=True,
    )

    active = test_repo.get_active_model_release("xgboost")
    assert active is not None
    assert active["release_id"] == "rel_1"
    assert active["is_active"] == 1

    # Insert release 2 (promoted, should deactivate release 1)
    test_repo.save_model_release(
        release_id="rel_2",
        model_name="xgboost",
        model_version="v2.0",
        symbol="RELIANCE.BSE",
        status="PROMOTED",
        training_sample_count=120,
        evaluation_sample_count=35,
        training_cutoff_date="2025-02-01",
        evaluation_cutoff_date="2025-03-01",
        metrics={"accuracy": 0.62},
        gates=[{"gate": "sample", "passed": True}],
        artifact_path="models/xgboost_direction.json",
        is_active=True,
    )

    active_new = test_repo.get_active_model_release("xgboost")
    assert active_new is not None
    assert active_new["release_id"] == "rel_2"
    assert active_new["model_version"] == "v2.0"

    # Previous release 1 must be deactivated
    old_rel = test_repo.get_model_release("rel_1")
    assert old_rel is not None
    assert old_rel["is_active"] == 0

    # List all releases
    all_releases = test_repo.list_model_releases(model_name="xgboost")
    assert len(all_releases) == 2
    assert all_releases[0]["release_id"] == "rel_2"
    assert all_releases[1]["release_id"] == "rel_1"
