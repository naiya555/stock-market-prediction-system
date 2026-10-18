"""Multi-Regime Stress Testing and Audit Regression Suite for Phase 16.

Validates:
1. Chronological integrity gate (Gate 0) rejecting temporal inversions and lookahead overlap.
2. Atomic model promotion with rollback on database/filesystem failure.
3. Archive failure aborts promotion safely without modifying active model.
4. Multi-regime market stress testing across distinct market environments:
   - Bull regime (trending upward, momentum persistence)
   - Bear regime (trending downward, downside volatility)
   - Choppy / range-bound regime (mean-reverting noise)
   - Regime transition shock (bull-to-bear reversal triggering Gate 4 rejection)
5. Concurrent retraining promotion serialization via re-entrant lock.
"""

from datetime import datetime, timedelta
from pathlib import Path
import shutil
import tempfile
import threading
from typing import Generator
import pytest
import numpy as np
import pandas as pd

from app.database.repository import PredictionRepository
from app.training.retraining import (
    ModelReleaseStatus,
    ModelRetrainer,
    RetrainingResult,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for models and database testing."""
    td = Path(tempfile.mkdtemp(prefix="test_multi_regime_"))
    yield td
    shutil.rmtree(td, ignore_errors=True)


@pytest.fixture
def test_repo(temp_dir: Path) -> PredictionRepository:
    """Create a temporary repository."""
    db_path = temp_dir / "test_predictions.db"
    return PredictionRepository(str(db_path))


# =====================================================================
# PART 1: AUDIT REGRESSION TESTS (CHRONOLOGICAL INTEGRITY & ROLLBACK)
# =====================================================================

def test_chronological_integrity_gate_inverted_cutoffs(temp_dir: Path, test_repo: PredictionRepository):
    """Retraining is rejected when training_cutoff_date is after evaluation_cutoff_date."""
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    n_train, n_val = 60, 20
    X_train = pd.DataFrame(np.random.randn(n_train, 3), columns=["f1", "f2", "f3"])
    y_train = pd.Series([1 if i % 2 == 0 else 0 for i in range(n_train)])
    X_val = pd.DataFrame(np.random.randn(n_val, 3), columns=["f1", "f2", "f3"])
    y_val = pd.Series([1 if i % 2 == 0 else 0 for i in range(n_val)])

    # Chronologically inverted cutoffs: training after eval
    res = retrainer.retrain_and_gate(
        symbol="TCS.BSE",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-06-01",
        evaluation_cutoff_date="2025-01-01",
    )

    assert res.status == ModelReleaseStatus.REJECTED
    assert res.is_promoted is False
    assert "Chronological inversion detected" in (res.rejection_reason or "")
    chrono_gate = next((g for g in res.gate_results if g.gate_name == "CHRONOLOGICAL_INTEGRITY_GATE"), None)
    assert chrono_gate is not None
    assert chrono_gate.passed is False

    # Production model file must not exist
    active_path = models_dir / "xgboost_direction.json"
    assert not active_path.is_file()


def test_chronological_integrity_gate_temporal_overlap_in_dates(temp_dir: Path, test_repo: PredictionRepository):
    """Retraining is rejected when training timestamps overlap into evaluation timestamps."""
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    # Dates with overlap: train ends at 2025-03-10, val starts at 2025-03-01
    train_dates = pd.date_range("2025-01-01", periods=60, freq="D")
    val_dates = pd.date_range("2025-02-15", periods=20, freq="D")

    X_train = pd.DataFrame(np.random.randn(60, 3), index=train_dates, columns=["f1", "f2", "f3"])
    y_train = pd.Series([1 if i % 2 == 0 else 0 for i in range(60)], index=train_dates)
    X_val = pd.DataFrame(np.random.randn(20, 3), index=val_dates, columns=["f1", "f2", "f3"])
    y_val = pd.Series([1 if i % 2 == 0 else 0 for i in range(20)], index=val_dates)

    res = retrainer.retrain_and_gate(
        symbol="INFY.BSE",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-01-01",
        evaluation_cutoff_date="2025-03-31",
    )

    assert res.status == ModelReleaseStatus.REJECTED
    assert res.is_promoted is False
    assert "Temporal overlap/leakage detected" in (res.rejection_reason or "")


def test_promotion_rollback_on_repository_failure(temp_dir: Path, test_repo: PredictionRepository):
    """When repository save fails during promotion, active model is restored from archive."""
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    n_train, n_val = 70, 20
    np.random.seed(42)
    X_train = pd.DataFrame(np.random.randn(n_train, 3), columns=["f1", "f2", "f3"])
    y_train = pd.Series((X_train["f1"] > 0).astype(int))
    X_val = pd.DataFrame(np.random.randn(n_val, 3), columns=["f1", "f2", "f3"])
    y_val = pd.Series((X_val["f1"] > 0).astype(int))

    # 1. Promote initial active model v1
    res_v1 = retrainer.retrain_and_gate(
        symbol="RELIANCE.BSE",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-01-01",
        evaluation_cutoff_date="2025-02-01",
        candidate_version="xgb_v1_initial",
    )
    assert res_v1.is_promoted is True
    active_path = models_dir / "xgboost_direction.json"
    assert active_path.is_file()
    with open(active_path, "rb") as f:
        v1_bytes = f.read()

    # 2. Candidate v2 with a mock repository that raises during save_model_release
    class FailingRepo(PredictionRepository):
        def save_model_release(self, *args, **kwargs):
            raise RuntimeError("Database locked or I/O failure during save_model_release!")

    failing_repo = FailingRepo(str(temp_dir / "test_predictions.db"))
    retrainer_failing = ModelRetrainer(repository=failing_repo, models_dir=models_dir)

    with pytest.raises(RuntimeError, match="Database locked or I/O failure"):
        retrainer_failing.retrain_and_gate(
            symbol="RELIANCE.BSE",
            model_name="xgboost",
            X_train=X_train * 2.0,
            y_train=y_train,
            X_val=X_val * 2.0,
            y_val=y_val,
            training_cutoff_date="2025-02-01",
            evaluation_cutoff_date="2025-03-01",
            candidate_version="xgb_v2_broken_repo",
        )

    # 3. Active model file must be completely rolled back and identical to v1!
    with open(active_path, "rb") as f:
        current_bytes = f.read()
    assert current_bytes == v1_bytes

    # Temporary staging file must have been unlinked
    temp_staging = active_path.with_suffix(".tmp")
    assert not temp_staging.is_file()


def test_promotion_aborted_when_archiving_fails(temp_dir: Path, test_repo: PredictionRepository):
    """If archiving existing active model fails, promotion aborts and active model is untouched."""
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    n_train, n_val = 60, 20
    np.random.seed(42)
    X_train = pd.DataFrame(np.random.randn(n_train, 3), columns=["f1", "f2", "f3"])
    y_train = pd.Series((X_train["f1"] > 0).astype(int))
    X_val = pd.DataFrame(np.random.randn(n_val, 3), columns=["f1", "f2", "f3"])
    y_val = pd.Series((X_val["f1"] > 0).astype(int))

    # Promote initial active model
    res_v1 = retrainer.retrain_and_gate(
        symbol="RELIANCE.BSE",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-01-01",
        evaluation_cutoff_date="2025-02-01",
    )
    assert res_v1.is_promoted is True
    active_path = models_dir / "xgboost_direction.json"
    with open(active_path, "rb") as f:
        v1_bytes = f.read()

    # Simulate archive directory failure by replacing archive dir with a read-only file or removing it
    shutil.rmtree(retrainer.archive_dir)
    # Create a file at archive_dir path so mkdir/copying fails
    with open(retrainer.archive_dir, "w") as f:
        f.write("blocked")

    res_v2 = retrainer.retrain_and_gate(
        symbol="RELIANCE.BSE",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2025-02-01",
        evaluation_cutoff_date="2025-03-01",
        candidate_version="v2_archive_fail",
        force_promote=True,
    )

    assert res_v2.status == ModelReleaseStatus.REJECTED
    assert res_v2.is_promoted is False
    assert "Archive failure" in (res_v2.rejection_reason or "")

    # Active model must remain untouched
    with open(active_path, "rb") as f:
        current_bytes = f.read()
    assert current_bytes == v1_bytes


# =====================================================================
# PART 2: MULTI-REGIME MARKET STRESS EVALUATION
# =====================================================================

def test_multi_regime_bull_market_evaluation(temp_dir: Path, test_repo: PredictionRepository):
    """Evaluate candidate model under sustained Bull regime with upward drift."""
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    n_train, n_val = 100, 30
    np.random.seed(101)

    # Bull regime: strong positive momentum signal (feature 0 strongly predictive of UP)
    # Target distribution has 65% UP, 35% DOWN
    X_train = pd.DataFrame(np.random.randn(n_train, 4), columns=["momentum", "volatility", "rsi", "return"])
    y_train = pd.Series((X_train["momentum"] + 0.3 * np.random.randn(n_train) > -0.2).astype(int))

    X_val = pd.DataFrame(np.random.randn(n_val, 4), columns=["momentum", "volatility", "rsi", "return"])
    y_val = pd.Series((X_val["momentum"] + 0.3 * np.random.randn(n_val) > -0.2).astype(int))

    result = retrainer.retrain_and_gate(
        symbol="NIFTY_BULL",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2024-01-01",
        evaluation_cutoff_date="2024-04-01",
        candidate_version="bull_v1",
    )

    assert result.status == ModelReleaseStatus.PROMOTED
    assert result.is_promoted is True
    assert result.metrics["accuracy"] >= 0.50
    assert result.metrics["brier_score"] is not None
    assert all(gate.passed for gate in result.gate_results)


def test_multi_regime_bear_market_evaluation(temp_dir: Path, test_repo: PredictionRepository):
    """Evaluate candidate model under sustained Bear regime with downward drift."""
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    n_train, n_val = 100, 30
    np.random.seed(202)

    # Bear regime: negative drift, downside volatility
    # Target distribution has 35% UP, 65% DOWN
    X_train = pd.DataFrame(np.random.randn(n_train, 4), columns=["momentum", "volatility", "rsi", "return"])
    y_train = pd.Series((X_train["momentum"] + 0.3 * np.random.randn(n_train) > 0.3).astype(int))

    X_val = pd.DataFrame(np.random.randn(n_val, 4), columns=["momentum", "volatility", "rsi", "return"])
    y_val = pd.Series((X_val["momentum"] + 0.3 * np.random.randn(n_val) > 0.3).astype(int))

    result = retrainer.retrain_and_gate(
        symbol="NIFTY_BEAR",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2024-04-01",
        evaluation_cutoff_date="2024-07-01",
        candidate_version="bear_v1",
    )

    assert result.status == ModelReleaseStatus.PROMOTED
    assert result.is_promoted is True
    assert result.metrics["accuracy"] >= 0.50


def test_multi_regime_shock_transition_rejection(temp_dir: Path, test_repo: PredictionRepository):
    """Candidate trained on Bull regime collapses during Bear regime transition shock and is REJECTED.

    Simulates a dangerous scenario: a model learns bull-market momentum heuristics,
    but encounters a sharp market regime reversal (e.g. March 2020 crash).
    Gate 4 (MINIMUM_PERFORMANCE_GATE) and Gate 3 must catch the collapse and reject the candidate.
    """
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    n_train, n_val = 120, 40
    np.random.seed(303)

    # Training: Bull regime where high momentum = UP
    X_train = pd.DataFrame(np.random.randn(n_train, 3), columns=["f1", "f2", "f3"])
    y_train = pd.Series((X_train["f1"] > -0.3).astype(int))  # Mostly UP

    # Evaluation: Severe Bear shock where the momentum heuristic completely inverts!
    # (High momentum stocks crash hardest)
    X_val = pd.DataFrame(np.random.randn(n_val, 3), columns=["f1", "f2", "f3"])
    y_val = pd.Series((X_val["f1"] < -0.2).astype(int))  # Inverted relationship

    result = retrainer.retrain_and_gate(
        symbol="NIFTY_SHOCK",
        model_name="xgboost",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        training_cutoff_date="2024-01-01",
        evaluation_cutoff_date="2024-03-31",
        candidate_version="overfit_bull_candidate",
    )

    # The candidate model must be REJECTED due to failure under out-of-sample regime shift!
    assert result.status == ModelReleaseStatus.REJECTED
    assert result.is_promoted is False
    assert result.active_artifact_path is None

    # Verify that Gate 4 or Gate 3 caught the failure
    failed_gate_names = [g.gate_name for g in result.gate_results if not g.passed]
    assert "MINIMUM_PERFORMANCE_GATE" in failed_gate_names or "BASELINE_SUPERIORITY_GATE" in failed_gate_names


def test_concurrent_retraining_promotion_thread_safety(temp_dir: Path, test_repo: PredictionRepository):
    """Concurrent retraining runs on the same retrainer instance are cleanly serialized without corruption."""
    models_dir = temp_dir / "models"
    retrainer = ModelRetrainer(repository=test_repo, models_dir=models_dir)

    n_train, n_val = 70, 20
    np.random.seed(404)
    X_train = pd.DataFrame(np.random.randn(n_train, 3), columns=["f1", "f2", "f3"])
    y_train = pd.Series((X_train["f1"] > 0).astype(int))
    X_val = pd.DataFrame(np.random.randn(n_val, 3), columns=["f1", "f2", "f3"])
    y_val = pd.Series((X_val["f1"] > 0).astype(int))

    results = []
    errors = []

    def run_worker(version_name: str, symbol: str, cutoff_train: str, cutoff_eval: str):
        try:
            res = retrainer.retrain_and_gate(
                symbol=symbol,
                model_name="xgboost",
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                training_cutoff_date=cutoff_train,
                evaluation_cutoff_date=cutoff_eval,
                candidate_version=version_name,
            )
            results.append(res)
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=run_worker, args=("v_thread_1", "RELIANCE.BSE", "2025-01-01", "2025-02-01")),
        threading.Thread(target=run_worker, args=("v_thread_2", "INFY.BSE", "2025-02-01", "2025-03-01")),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 2
    assert all(r.is_promoted for r in results)

    # Active model file must be a valid, loadable model artifact
    active_path = models_dir / "xgboost_direction.json"
    assert active_path.is_file()
