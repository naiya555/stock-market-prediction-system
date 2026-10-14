"""Tests for Day 21 Model Error Analysis and Feature Usefulness Audit."""

import numpy as np
import pandas as pd
import pytest

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
from app.training.lightgbm_classifier import LightGBMConfig, LightGBMDirectionClassifier
from app.training.walk_forward import (
    WalkForwardFoldEvaluation,
    WalkForwardFoldSplit,
    WalkForwardReport,
    WalkForwardStrategySummary,
)
from app.training.xgboost_classifier import (
    ClassificationMetrics,
    XGBoostConfig,
    XGBoostDirectionClassifier,
    compute_classification_metrics,
)


def test_down_metrics_computation():
    """Verify compute_classification_metrics calculates symmetrical DOWN metrics."""
    # y_true = [0, 0, 1, 1], y_pred = [0, 1, 0, 1]
    # DOWN (class 0): true=2, pred=1, true down pred down (TN) = 1, true up pred down (FN) = 1
    # Precision DOWN = TN / (TN + FN) = 1 / 2 = 0.5
    # Recall DOWN = TN / (TN + FP) = 1 / 2 = 0.5
    # F1 DOWN = 0.5
    y_true = [0, 0, 1, 1]
    y_pred = [0, 1, 0, 1]
    m = compute_classification_metrics(y_true, y_pred)

    assert m.accuracy == 0.5
    assert m.precision == 0.5
    assert m.recall == 0.5
    assert m.f1 == 0.5
    assert m.precision_down == 0.5
    assert m.recall_down == 0.5
    assert m.f1_down == 0.5


def test_down_metrics_edge_case_all_up():
    """Verify DOWN metrics are 0.0 when model predicts all UP (zero DOWN predictions)."""
    y_true = [0, 1, 1, 1]
    y_pred = [1, 1, 1, 1]
    m = compute_classification_metrics(y_true, y_pred)

    assert m.accuracy == 0.75
    assert m.recall == 1.0
    assert m.precision_down == 0.0
    assert m.recall_down == 0.0
    assert m.f1_down == 0.0


def test_xgboost_feature_importances_property():
    """Verify XGBoostDirectionClassifier exposes feature_importances_ properly."""
    clf = XGBoostDirectionClassifier(XGBoostConfig(n_estimators=5, max_depth=2))
    with pytest.raises(ValueError, match="Cannot extract feature importances from unfitted model"):
        _ = clf.feature_importances_

    # Fit on synthetic data
    np.random.seed(42)
    X = pd.DataFrame(
        {
            "feat_informative": np.random.randn(50),
            "feat_noise": np.random.randn(50),
        }
    )
    y = (X["feat_informative"] > 0).astype(int)
    clf.fit(X, y)

    importances = clf.feature_importances_
    assert isinstance(importances, dict)
    assert "feat_informative" in importances
    assert "feat_noise" in importances
    assert all(isinstance(v, float) for v in importances.values())


def test_analyze_walk_forward_errors():
    """Verify walk-forward error analysis decomposes metrics and distribution shifts."""
    # Create mock fold split
    split1 = WalkForwardFoldSplit(
        fold=1,
        X_train=pd.DataFrame({"f1": [1, 2, 3, 4]}),
        y_train=pd.Series([1, 1, 1, 0]),
        X_val=pd.DataFrame({"f1": [5, 6]}),
        y_val=pd.Series([0, 1]),
        train_indices=[0, 1, 2, 3],
        val_indices=[5, 6],
        embargo_indices=[4],
        train_start_date="2020-01-01",
        train_end_date="2020-01-04",
        train_outcome_cutoff="2020-01-05",
        val_start_date="2020-01-06",
        val_end_date="2020-01-07",
        train_rows=4,
        val_rows=2,
        embargo_rows=1,
        train_up_count=3,
        train_down_count=1,
        train_up_ratio=0.75,
        val_up_count=1,
        val_down_count=1,
        val_up_ratio=0.50,
    )

    maj_metrics = compute_classification_metrics([0, 1], [1, 1])
    xgb_metrics = compute_classification_metrics([0, 1], [0, 1])

    ev_maj = WalkForwardFoldEvaluation(
        fold=1,
        strategy_name="Baseline A (Majority Class)",
        metrics=maj_metrics,
        pred_up_count=2,
        pred_down_count=0,
    )
    ev_xgb = WalkForwardFoldEvaluation(
        fold=1,
        strategy_name="Model C (Day 17 XGBoost)",
        metrics=xgb_metrics,
        pred_up_count=1,
        pred_down_count=1,
    )

    report = WalkForwardReport(
        symbol="TEST.NS",
        total_dataset_rows=10,
        retained_rows=7,
        n_splits=1,
        embargo_sessions=1,
        folds=[split1],
        fold_evaluations=[ev_maj, ev_xgb],
        strategy_summaries={},
        best_strategy_by_mean_accuracy="Model C (Day 17 XGBoost)",
        best_strategy_by_mean_f1="Model C (Day 17 XGBoost)",
    )

    analyses = analyze_walk_forward_errors(report)
    assert len(analyses) == 2

    maj_analysis = next(a for a in analyses if "Majority Class" in a.strategy_name)
    assert maj_analysis.fold == 1
    assert maj_analysis.distribution_shift_up == -0.25  # 0.50 - 0.75
    assert maj_analysis.is_systematic_direction is True
    assert maj_analysis.systematic_direction == "ALL_UP"
    assert maj_analysis.diff_vs_majority == 0.0

    xgb_analysis = next(a for a in analyses if "Model C" in a.strategy_name)
    assert xgb_analysis.fold == 1
    assert xgb_analysis.accuracy == 1.00
    assert xgb_analysis.majority_accuracy == 0.50
    assert xgb_analysis.diff_vs_majority == 0.50
    assert xgb_analysis.is_systematic_direction is False
    assert xgb_analysis.systematic_direction is None
    assert xgb_analysis.precision_down == 1.00


def test_audit_feature_usefulness_isolation_guard():
    """Verify audit_feature_usefulness rejects feature matrix containing target or outcome columns."""
    df_leak = pd.DataFrame(
        {
            "feature1": [1.0, 2.0, 3.0],
            "target_binary": [1, 0, 1],
        }
    )
    with pytest.raises(ValueError, match="Data leakage detected"):
        audit_feature_usefulness(df_leak)


def test_audit_feature_usefulness_constant_and_correlation():
    """Verify detection of constant features and high collinearity pairs."""
    np.random.seed(42)
    base = np.random.randn(60)
    # Collinear feature: almost perfectly correlated with base
    collinear = base * 2.0 + np.random.normal(0, 0.01, size=60)
    # Independent feature
    indep = np.random.randn(60)
    # Constant feature
    const_col = np.ones(60)

    X_train = pd.DataFrame(
        {
            "base_feat": base,
            "collinear_feat": collinear,
            "independent_feat": indep,
            "constant_feat": const_col,
        }
    )

    audit = audit_feature_usefulness(X_train, correlation_threshold=0.90)

    assert audit.n_samples == 60
    assert audit.n_features == 4
    assert "constant_feat" in audit.constant_features
    assert "constant_feat" in audit.feature_metrics
    assert audit.feature_metrics["constant_feat"].is_constant is True
    assert audit.feature_metrics["base_feat"].is_constant is False

    # Check high correlation detection
    pairs = audit.high_correlation_pairs
    assert len(pairs) >= 1
    collinear_pair = next(
        (p for p in pairs if {"base_feat", "collinear_feat"} == {p.feature_a, p.feature_b}),
        None,
    )
    assert collinear_pair is not None
    assert abs(collinear_pair.correlation) > 0.95


def test_audit_feature_usefulness_with_models():
    """Verify tree feature importance extraction within audit."""
    np.random.seed(42)
    X = pd.DataFrame(
        {
            "f1": np.random.randn(60),
            "f2": np.random.randn(60),
            "f3": np.random.randn(60),
        }
    )
    y = (X["f1"] > 0).astype(int)

    xgb = XGBoostDirectionClassifier(XGBoostConfig(n_estimators=5, max_depth=2))
    xgb.fit(X, y)

    lgb = LightGBMDirectionClassifier(LightGBMConfig(n_estimators=5, max_depth=2, num_leaves=4))
    lgb.fit(X, y)

    audit = audit_feature_usefulness(X, xgboost_model=xgb, lightgbm_model=lgb)
    assert audit.xgboost_importances is not None
    assert audit.lightgbm_importances is not None
    assert len(audit.top_xgboost_features) == 3
    assert len(audit.top_lightgbm_features) == 3


def test_markdown_rendering():
    """Verify markdown table formatters generate valid string tables."""
    # Mock audit
    fm = {
        "f1": FeatureQualityMetric("f1", 0, 0.0, False, 10, 0.5, 1.0, -1.0, 2.0),
        "f2": FeatureQualityMetric("f2", 0, 0.0, False, 10, 0.2, 0.8, -0.5, 1.5),
    }
    pairs = [HighCorrelationPair("f1", "f2", 0.95)]
    audit = FeatureUsefulnessAudit(
        n_samples=50,
        n_features=2,
        feature_metrics=fm,
        constant_features=[],
        missing_features=[],
        high_correlation_pairs=pairs,
        correlation_threshold=0.90,
        top_xgboost_features=[("f1", 10.0), ("f2", 5.0)],
        top_lightgbm_features=[("f1", 15.0), ("f2", 8.0)],
    )

    corr_table = render_collinearity_table(audit)
    assert "| Feature A | Feature B |" in corr_table
    assert "`f1`" in corr_table

    imp_table = render_feature_importance_comparison_table(audit)
    assert "| Rank | XGBoost Feature |" in imp_table
    assert "`f1`" in imp_table
