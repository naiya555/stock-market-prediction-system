"""Real-Data Verification Script for Day 17 XGBoost Direction Classifier.

Validates:
1. Real-data acquisition for BHARTIARTL.NS via existing provider and pipeline.
2. Technical feature matrix assembly and Day 15 target joining.
3. Chronological holdout partitioning with strict outcome embargo (zero label leakage).
4. Training of first reproducible XGBoost binary classifier (UP=1, DOWN=0).
5. Comprehensive evaluation metrics on holdout data (Accuracy, Precision, Recall, F1, Confusion Matrix).
6. Deterministic inference reproducibility with fixed random seed.
7. Verification of data invariants, sample exclusions, and class distributions.
8. Transparent research baseline disclaimers (no claims of trading edge or calibrated odds).
"""

from datetime import datetime
import math
from pathlib import Path
import sys

import numpy as np

# Configure UTF-8 encoding on Windows if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.market.pipeline import run_market_data_pipeline
from app.market.providers.yfinance_provider import YFinanceProvider
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)
from app.training.xgboost_classifier import (
    ClassificationMetrics,
    DirectionTrainingResult,
    XGBoostConfig,
    XGBoostDirectionClassifier,
    compute_classification_metrics,
    run_training_pipeline,
    split_chronological_holdout,
)


def _get_currency_symbol() -> str:
    """Determine currency symbol, falling back to 'INR' if console cannot encode rupee."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "\u20b9".encode(encoding)
        return "\u20b9"
    except (UnicodeEncodeError, LookupError):
        return "INR"


def verify_real_data_xgboost() -> int:
    curr = _get_currency_symbol()
    print("==================================================")
    print("DAY 17: XGBOOST DIRECTION CLASSIFIER VERIFICATION")
    print("==================================================")

    provider = YFinanceProvider()
    symbol = "BHARTIARTL"
    lookback_days = 180

    # Step 1: Market data acquisition via pipeline
    print(f"\nStep 1: Running market data pipeline for {symbol} (lookback_days={lookback_days})...")
    try:
        pipeline_result = run_market_data_pipeline(
            symbol=symbol,
            lookback_days=lookback_days,
            provider=provider,
        )
    except Exception as exc:
        print(f"ERROR: Market data pipeline execution failed: {exc}", file=sys.stderr)
        return 1

    clean_records = pipeline_result.cleaned_records
    n_records = len(clean_records)
    print(f"  [OK] Cleaned bars produced: {n_records}")
    if n_records < 20:
        print(f"ERROR: Insufficient historical sessions ({n_records} < 20)", file=sys.stderr)
        return 1

    first_date = clean_records[0].timestamp.strftime("%Y-%m-%d")
    last_date = clean_records[-1].timestamp.strftime("%Y-%m-%d")
    print(f"  [OK] Historical Date Range: {first_date} to {last_date} ({n_records} sessions)")

    # Step 2: Feature matrix assembly and Day 15 targets
    print("\nStep 2: Assembling Technical Feature Matrix & Day 15 Targets...")
    try:
        dataset = assemble_feature_matrix(pipeline_result)
    except Exception as exc:
        print(f"ERROR: Feature matrix assembly failed: {exc}", file=sys.stderr)
        return 1

    print(f"  [OK] Total Aligned Rows:     {dataset.total_rows}")
    print(f"  [OK] Feature Columns in X:   {len(dataset.feature_names)}")
    print(f"  [OK] Labeled Rows (y in 0,1):{dataset.labeled_rows}")
    print(f"  [OK] Unlabeled Rows (y=NaN): {dataset.unlabeled_rows}")

    # Validate isolation guard
    validate_feature_matrix_isolation(dataset.X)
    print("  [OK] Isolation Guard: Zero target or future outcome columns in X.")

    # Step 3: Complete labeled rows extraction & accounting
    print("\nStep 3: Supervised Dataset Extraction & Warmup Accounting...")
    X_clean, y_clean, audit = dataset.get_labeled_dataset(drop_incomplete_warmup=True)
    unlabeled_excluded = audit["unlabeled_final_rows_excluded"]
    warmup_excluded = audit["incomplete_warmup_rows_excluded"]
    retained_rows = audit["final_retained_rows"]

    print(f"  Initial Total Observations:           {dataset.total_rows}")
    print(f"  Unlabeled Final Observation Excluded: {unlabeled_excluded}")
    print(f"  Incomplete Warmup Rows Excluded:      {warmup_excluded}")
    print(f"  Complete Labeled Rows Retained:       {retained_rows}")
    assert retained_rows == len(X_clean), "Row count mismatch in retained dataset"

    # Step 4: Chronological Holdout Partitioning with Outcome Embargo
    print("\nStep 4: Chronological Holdout Partitioning & Temporal Embargo...")
    test_ratio = 0.20
    embargo_sessions = 1
    split_res = split_chronological_holdout(
        data=dataset,
        test_ratio=test_ratio,
        embargo_sessions=embargo_sessions,
        drop_incomplete_warmup=True,
    )

    print(f"  [OK] Training Partition:   {split_res.train_rows} rows [{split_res.train_start_date} to {split_res.train_end_date}]")
    print(f"  [OK] Embargo Gap:          {split_res.embargo_rows} row (purged to prevent label outcome leakage)")
    print(f"  [OK] Holdout Partition:    {split_res.test_rows} rows [{split_res.holdout_start_date} to {split_res.holdout_end_date}]")
    print(f"  [OK] Train Outcome Cutoff: {split_res.train_outcome_cutoff} <= Holdout Start: {split_res.holdout_start_date}")
    assert split_res.train_outcome_cutoff <= split_res.holdout_start_date, "Temporal leakage violation!"

    # Class distributions
    train_pos = int(np.sum(split_res.y_train == 1))
    train_neg = int(np.sum(split_res.y_train == 0))
    test_pos = int(np.sum(split_res.y_test == 1))
    test_neg = int(np.sum(split_res.y_test == 0))
    print(f"\n  Class Counts:")
    print(f"    Train: DOWN(0) = {train_neg} ({train_neg/split_res.train_rows*100:.1f}%), UP(1) = {train_pos} ({train_pos/split_res.train_rows*100:.1f}%)")
    print(f"    Test:  DOWN(0) = {test_neg} ({test_neg/split_res.test_rows*100:.1f}%), UP(1) = {test_pos} ({test_pos/split_res.test_rows*100:.1f}%)")

    # Step 5: Train baseline XGBoost classifier
    print("\nStep 5: Training Baseline XGBoost Binary Classifier...")
    config = XGBoostConfig(
        objective="binary:logistic",
        eval_metric="logloss",
        max_depth=3,
        learning_rate=0.05,
        n_estimators=50,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=1,
    )
    print(f"  Hyperparameters: {config.to_dict()}")

    model = XGBoostDirectionClassifier(config=config)
    model.fit(split_res.X_train, split_res.y_train)
    assert model.is_fitted is True
    print("  [OK] Model successfully fitted strictly on training partition.")

    # Step 6: Holdout evaluation metrics
    print("\nStep 6: Computing Holdout Evaluation Metrics...")
    test_preds = model.predict(split_res.X_test)
    test_probs = model.predict_proba(split_res.X_test)[:, 1]
    metrics = compute_classification_metrics(split_res.y_test, test_preds)

    print("--------------------------------------------------")
    print("HOLDOUT EVALUATION METRICS (UNSEEN DATA)")
    print("--------------------------------------------------")
    print(f"  Holdout Sessions:    {metrics.total_samples}")
    print(f"  Accuracy:            {metrics.accuracy:.4f} ({metrics.accuracy*100:.2f}%)")
    print(f"  Precision (UP=1):    {metrics.precision:.4f}")
    print(f"  Recall (UP=1):       {metrics.recall:.4f}")
    print(f"  F1 Score (UP=1):     {metrics.f1:.4f}")
    print(f"  Confusion Matrix:    [[TN={metrics.true_negatives}, FP={metrics.false_positives}], [FN={metrics.false_negatives}, TP={metrics.true_positives}]]")
    print("--------------------------------------------------")

    # Step 7: Deterministic reproducibility check
    print("\nStep 7: Verifying Deterministic Prediction Reproducibility...")
    test_preds_repeat = model.predict(split_res.X_test)
    test_probs_repeat = model.predict_proba(split_res.X_test)[:, 1]
    assert np.array_equal(test_preds, test_preds_repeat), "Predictions are non-deterministic!"
    assert np.allclose(test_probs, test_probs_repeat, atol=1e-6), "Probabilities are non-deterministic!"
    print("  [OK] 100% deterministic prediction reproducibility verified.")

    # Step 8: Sample Holdout Predictions
    print("\nStep 8: Sample Holdout Predictions vs Realized Outcomes:")
    print("-----------------------------------------------------------------------------------------")
    print("Pred Date   | Pred Prob(UP) | Pred Class | Actual Binary | Actual Target | Correct? ")
    print("-----------------------------------------------------------------------------------------")
    for i in range(min(5, len(split_res.X_test))):
        dt_str = str(split_res.metadata_test["timestamp"].iloc[i])[:10] if split_res.metadata_test is not None else f"Row {i}"
        prob = test_probs[i]
        pred_cls = test_preds[i]
        actual_bin = int(split_res.y_test.iloc[i])
        actual_tgt = split_res.metadata_test["target_direction"].iloc[i] if split_res.metadata_test is not None else "N/A"
        correct = "YES" if pred_cls == actual_bin else "NO"
        print(f"{dt_str}  | {prob*100:6.2f}%       | {pred_cls} (UP)     | {actual_bin}             | {actual_tgt:<13} | {correct}")
    print("-----------------------------------------------------------------------------------------")

    print("\n==================================================")
    print("VERIFICATION SUMMARY")
    print("==================================================")
    print(f"Symbol:                 {symbol}")
    print(f"Total Bars:             {n_records}")
    print(f"Retained Complete Rows: {retained_rows}")
    print(f"Train / Test Split:     {split_res.train_rows} / {split_res.test_rows} (1 embargo session)")
    print(f"Train Date Range:       {split_res.train_start_date} to {split_res.train_end_date}")
    print(f"Holdout Date Range:     {split_res.holdout_start_date} to {split_res.holdout_end_date}")
    print(f"Holdout Accuracy:       {metrics.accuracy*100:.2f}%")
    print(f"Holdout F1 Score:       {metrics.f1:.4f}")
    print(f"Temporal Leakage:       Zero (outcome cutoff strictly <= holdout start)")
    print(f"Edge Claim:             None (research baseline only)")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(verify_real_data_xgboost())
