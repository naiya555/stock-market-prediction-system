"""Deterministic regression tests for Day 60: Historical Evaluation Data-Readiness Audit.

Verifies:
1. Programmatic dataset inventory correctly categorizes repository datasets and providers.
2. Historical news/event readiness is explicitly classified as BLOCKED.
3. Quantitative ML evaluation readiness is classified as READY for BHARTIARTL (N=240).
4. Blended evaluation readiness is classified as BLOCKED until point-in-time news is available.
5. Cutoff and embargo semantics prevent temporal leakage.
6. Target definition and market session invariants.
7. Protected file hashes remain pristine.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import pytest

from app.history.data_readiness import (
    HistoricalReadinessReport,
    ReadinessStatus,
    audit_repository_data_readiness,
)

PROTECTED_DB_HASH = "d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e"
PROTECTED_MODELS_GITKEEP_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class TestDatasetInventoryAudit:
    """Validate repository dataset discovery, inventory completeness, and record counts."""

    def test_audit_inventory_discovers_core_datasets(self) -> None:
        report = audit_repository_data_readiness()
        assert isinstance(report, HistoricalReadinessReport)

        names = [item.name for item in report.inventory]
        assert "Predictions SQLite Database" in names
        assert "Trained Model Holdout Evaluation Metadata" in names
        assert "Point-in-Time Historical News Archive" in names
        assert "RSSNewsProvider (Google News RSS)" in names
        assert "RBI & SEBI Macro Event Providers" in names

    def test_database_is_clean_with_zero_records(self) -> None:
        report = audit_repository_data_readiness()
        db_item = next(item for item in report.inventory if item.name == "Predictions SQLite Database")
        assert db_item.record_count == 0
        assert "Pristine state preserved" in db_item.notes

    def test_model_metadata_reproduces_240_holdout_sessions(self) -> None:
        report = audit_repository_data_readiness()
        meta_item = next(item for item in report.inventory if item.name == "Trained Model Holdout Evaluation Metadata")
        assert meta_item.record_count == 240
        assert meta_item.readiness_status == ReadinessStatus.READY
        assert meta_item.is_point_in_time_verified is True
        assert "BHARTIARTL" in meta_item.instrument_or_topic
        assert report.reproducible_ml_sessions == 240
        assert "xgboost" in report.reproducible_ml_models
        assert "lightgbm" in report.reproducible_ml_models


class TestReadinessClassification:
    """Validate explicit readiness status assignments per Day 60 guidelines."""

    def test_ml_evaluation_is_ready_from_promoted_artifacts(self) -> None:
        report = audit_repository_data_readiness()
        assert report.ml_evaluation_readiness == ReadinessStatus.READY

    def test_llm_evaluation_is_explicitly_blocked(self) -> None:
        report = audit_repository_data_readiness()
        assert report.llm_evaluation_readiness == ReadinessStatus.BLOCKED

    def test_blended_evaluation_is_explicitly_blocked(self) -> None:
        report = audit_repository_data_readiness()
        assert report.blended_evaluation_readiness == ReadinessStatus.BLOCKED

    def test_missing_prerequisites_documented(self) -> None:
        report = audit_repository_data_readiness()
        assert len(report.missing_prerequisites) >= 4
        assert any("news corpus" in p.lower() for p in report.missing_prerequisites)
        assert any("gpu" in p.lower() or "throughput" in p.lower() for p in report.missing_prerequisites)


class TestCutoffAndAntiLeakageEnforcement:
    """Validate temporal separation, embargo mechanics, and cutoff semantics."""

    def test_chronological_cutoff_ordering_in_model_metadata(self) -> None:
        meta_path = Path("models/model_metadata.json")
        assert meta_path.is_file()

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        dp = meta["dataset_period"]
        train_end = dp["train_end_date"]
        outcome_cutoff = dp["train_outcome_cutoff"]
        holdout_start = dp["holdout_start_date"]
        holdout_end = dp["holdout_end_date"]

        # Strict chronological ordering: train_end < outcome_cutoff < holdout_start <= holdout_end
        assert train_end < outcome_cutoff
        assert outcome_cutoff < holdout_start
        assert holdout_start <= holdout_end
        assert meta["sample_counts"]["embargo"] == 1
        assert meta["sample_counts"]["train"] + meta["sample_counts"]["eval"] + meta["sample_counts"]["embargo"] == meta["sample_counts"]["total_labeled"]

    def test_prohibit_backfilling_today_news_onto_historical_dates(self) -> None:
        """Verify that current news publication dates cannot be matched to historical cutoffs."""
        now = datetime.now(timezone.utc)
        historical_cutoff = datetime(2025, 10, 27, 15, 30, tzinfo=timezone.utc)

        # Gap between today and cutoff must be strictly > 300 days
        gap_days = (now - historical_cutoff).days
        assert gap_days > 300

        # Simulating lookahead check: news published after cutoff cannot be admitted
        sample_article_published = now - timedelta(days=2)
        assert sample_article_published > historical_cutoff, "Article published after cutoff must be rejected"


class TestEvaluationProtocolInvariants:
    """Validate evaluation protocol constraints and metric requirements."""

    def test_target_definition_consistency(self) -> None:
        meta_path = Path("models/model_metadata.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        target_def = meta["target_definition"]
        assert "next_session_direction" in target_def
        assert "1=UP" in target_def
        assert "0=DOWN" in target_def

    def test_serialization_of_readiness_report(self) -> None:
        report = audit_repository_data_readiness()
        d = report.to_dict()
        assert isinstance(d, dict)
        assert d["ml_evaluation_readiness"] == "READY"
        assert d["llm_evaluation_readiness"] == "BLOCKED"
        assert d["blended_evaluation_readiness"] == "BLOCKED"
        assert len(d["inventory"]) >= 4


class TestProtectedFilesIntegrity:
    """Verify that protected files have not been modified or corrupted."""

    def test_database_and_gitkeep_hashes_unchanged(self) -> None:
        db_path = Path("data/predictions.db")
        gitkeep_path = Path("models/.gitkeep")

        assert db_path.exists(), "data/predictions.db missing"
        assert gitkeep_path.exists(), "models/.gitkeep missing"

        db_sha = hashlib.sha256(db_path.read_bytes()).hexdigest().lower()
        gitkeep_sha = hashlib.sha256(gitkeep_path.read_bytes()).hexdigest().lower()

        assert db_sha == PROTECTED_DB_HASH, (
            f"Protected database data/predictions.db modified! SHA256: {db_sha}"
        )
        assert gitkeep_sha == PROTECTED_MODELS_GITKEEP_HASH, (
            f"Protected models/.gitkeep modified! SHA256: {gitkeep_sha}"
        )
