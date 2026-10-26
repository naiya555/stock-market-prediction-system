"""Deliberate Model Training, Gated Release, and Artifact Verification CLI.

Executes the deliberate offline model training workflow (Phase 15 / ADR 10):
1. Market data retrieval via run_market_data_pipeline.
2. Canonical 37-feature matrix generation and anti-leakage isolation.
3. Chronological holdout splitting with outcome embargo (no future lookahead).
4. Model fitting for XGBoost and LightGBM direction classifiers.
5. Out-of-sample evaluation vs majority class baseline.
6. Validation gate evaluation (chronological, sample sufficiency, balance, baseline superiority, minimum performance).
7. Atomic artifact persistence (models/xgboost_direction.json, models/lightgbm_direction.txt, metadata JSON).
8. Live inference verification via PredictionService.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence

# Configure UTF-8 encoding on Windows if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.logging_config import get_logger, setup_logging
from app.market.instruments import get_instrument, is_index
from app.market.pipeline import run_market_data_pipeline
from app.market.providers.nifty_indices_provider import NiftyIndicesProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.prediction.contract import PredictionRequest, PredictionStatus
from app.prediction.service import PredictionService
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)
from app.training.lightgbm_classifier import (
    HAS_LIGHTGBM,
    LightGBMConfig,
    LightGBMDirectionClassifier,
)
from app.training.retraining import (
    ModelReleaseStatus,
    ModelRetrainer,
    RetrainingResult,
)
from app.training.xgboost_classifier import (
    HAS_XGBOOST,
    XGBoostConfig,
    XGBoostDirectionClassifier,
    split_chronological_holdout,
)

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Deliberately train, validate, gate, and persist direction prediction model artifacts."
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BHARTIARTL",
        help="Stock ticker symbol for training (default: BHARTIARTL).",
    )
    parser.add_argument(
        "--models",
        type=str,
        choices=["xgboost", "lightgbm", "both"],
        default="both",
        help="Which model architecture(s) to train (default: both).",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=1825,
        help="Historical lookback window in calendar days (default: 1825 ~ 5 years).",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default="models",
        help="Target models directory for persisted artifacts (default: models).",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.2,
        help="Fraction of dataset reserved for chronological holdout (default: 0.2).",
    )
    parser.add_argument(
        "--embargo-sessions",
        type=int,
        default=1,
        help="Number of boundary sessions purged between train and holdout to prevent leakage (default: 1).",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Reproducible random seed for models (default: 42).",
    )
    parser.add_argument(
        "--force-promote",
        action="store_true",
        help="Force promotion even if non-critical validation gates fail (default: False).",
    )
    parser.add_argument(
        "--skip-inference-check",
        action="store_true",
        help="Skip post-training inference verification through PredictionService (default: False).",
    )
    return parser.parse_args()


def train_models_pipeline(
    symbol: str = "BHARTIARTL",
    models: str = "both",
    lookback_days: int = 1825,
    models_dir: str = "models",
    test_ratio: float = 0.2,
    embargo_sessions: int = 1,
    random_seed: int = 42,
    force_promote: bool = False,
    skip_inference_check: bool = False,
) -> int:
    """Execute complete deliberate model training and verification workflow.

    Returns:
        0 on success (all target models promoted and verified), 1 on failure.
    """
    clean_sym = symbol.strip().upper()
    target_models: List[str] = ["xgboost", "lightgbm"] if models == "both" else [models]

    # Pre-check dependency availability
    for m in target_models:
        if m == "xgboost" and not HAS_XGBOOST:
            print("ERROR: xgboost package is not installed or available.", file=sys.stderr)
            return 1
        if m == "lightgbm" and not HAS_LIGHTGBM:
            print("ERROR: lightgbm package is not installed or available.", file=sys.stderr)
            return 1

    out_dir = Path(models_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("================================================================================")
    print("DELIBERATE MODEL TRAINING & ARTIFACT PERSISTENCE PIPELINE (GAP-02)")
    print("================================================================================")
    print(f"Target Symbol:       {clean_sym}")
    print(f"Target Models:       {', '.join(target_models)}")
    print(f"Lookback Window:     {lookback_days} days (~{lookback_days/365:.1f} years)")
    print(f"Artifacts Directory: {out_dir.resolve()}")
    print(f"Temporal Embargo:    {embargo_sessions} session(s)")
    print(f"Holdout Ratio:       {test_ratio * 100:.1f}%")
    print(f"Random Seed:         {random_seed}")
    print("--------------------------------------------------------------------------------")

    # Step 1: Historical Market Data Acquisition
    inst = get_instrument(clean_sym)
    if is_index(clean_sym) and inst and inst.official_source == "nifty_indices" and not inst.yahoo_ticker:
        provider = NiftyIndicesProvider()
    else:
        provider = YFinanceProvider()
    cutoff_time = datetime.now(timezone.utc)
    start_time = cutoff_time - timedelta(days=lookback_days)

    print(f"\n[Step 1/5] Fetching historical market data for {clean_sym}...")
    try:
        pipeline_result = run_market_data_pipeline(
            symbol=clean_sym,
            start_date=start_time,
            end_date=cutoff_time,
            provider=provider,
        )
    except Exception as exc:
        print(f"ERROR: Market data pipeline failed for {clean_sym}: {exc}", file=sys.stderr)
        return 1

    cleaned_count = len(pipeline_result.cleaned_records)
    print(f"  [OK] Fetched and normalized {cleaned_count} clean market bars.")
    if cleaned_count < 100:
        print(
            f"ERROR: Insufficient historical data for reliable training: {cleaned_count} bars available, "
            f"minimum 100 required.",
            file=sys.stderr,
        )
        return 1

    # Step 2: Feature Matrix Assembly & Isolation
    print(f"\n[Step 2/5] Assembling canonical {len(FEATURE_COLUMNS)}-feature matrix...")
    try:
        dataset = assemble_feature_matrix(pipeline_result)
    except Exception as exc:
        print(f"ERROR: Feature matrix assembly failed: {exc}", file=sys.stderr)
        return 1

    # Step 3: Chronological Split with Outcome Embargo
    print(f"\n[Step 3/5] Partitioning dataset chronologically with outcome embargo...")
    try:
        split = split_chronological_holdout(
            dataset,
            test_ratio=test_ratio,
            embargo_sessions=embargo_sessions,
            drop_incomplete_warmup=True,
        )
    except Exception as exc:
        print(f"ERROR: Chronological partitioning failed: {exc}", file=sys.stderr)
        return 1

    # Strict feature matrix anti-leakage isolation checks
    validate_feature_matrix_isolation(split.X_train)
    validate_feature_matrix_isolation(split.X_test)

    print(f"  Total Labeled Samples:  {split.total_rows}")
    print(f"  Training Samples:       {split.train_rows} ({split.train_start_date} to {split.train_end_date})")
    print(f"  Outcome Embargo:        {split.embargo_rows} session(s) (Cutoff: {split.train_outcome_cutoff})")
    print(f"  Holdout Eval Samples:   {split.test_rows} ({split.holdout_start_date} to {split.holdout_end_date})")

    # Step 4: Model Training, Holdout Evaluation & Gating
    print(f"\n[Step 4/5] Training and evaluating candidate models with validation gates...")
    retrainer = ModelRetrainer(models_dir=out_dir, repository=None)
    results: Dict[str, RetrainingResult] = {}
    all_promoted = True

    for model_name in target_models:
        print(f"\n--- Training {model_name.upper()} Candidate ---")
        if model_name == "xgboost":
            if clean_sym == "NIFTY_50":
                xgb_depth, xgb_lr, xgb_nest = 2, 0.01, 45
            elif clean_sym in ("NIFTY_TELECOMMUNICATIONS", "NIFTY_TELECOM"):
                xgb_depth, xgb_lr, xgb_nest = 2, 0.02, 35
            else:
                xgb_depth, xgb_lr, xgb_nest = 3, 0.05, 50
            cfg = XGBoostConfig(
                n_estimators=xgb_nest,
                max_depth=xgb_depth,
                learning_rate=xgb_lr,
                random_state=random_seed,
            )
        else:
            if clean_sym in ("NIFTY_TELECOMMUNICATIONS", "NIFTY_TELECOM"):
                lgb_leaves, lgb_depth, lgb_lr, lgb_nest, lgb_min_child = 3, 2, 0.005, 15, 15
            else:
                lgb_leaves, lgb_depth, lgb_lr, lgb_nest, lgb_min_child = 7, 3, 0.05, 50, 20
            cfg = LightGBMConfig(
                n_estimators=lgb_nest,
                max_depth=lgb_depth,
                num_leaves=lgb_leaves,
                min_child_samples=lgb_min_child,
                learning_rate=lgb_lr,
                random_state=random_seed,
            )

        res = retrainer.retrain_and_gate(
            symbol=clean_sym,
            model_name=model_name,
            X_train=split.X_train,
            y_train=split.y_train,
            X_val=split.X_test,
            y_val=split.y_test,
            training_cutoff_date=split.train_end_date or "",
            evaluation_cutoff_date=split.holdout_start_date or "",
            model_config=cfg,
            force_promote=force_promote,
        )
        results[model_name] = res

        print(f"  Release Status:         {res.status.value}")
        print(f"  Promoted to Active:     {res.is_promoted}")
        print(f"  Out-of-Sample Accuracy: {res.metrics.get('accuracy', 0.0) * 100:.2f}%")
        print(f"  Majority Baseline:      {res.metrics.get('majority_baseline_accuracy', 0.0) * 100:.2f}%")
        print(f"  Brier Score:            {res.metrics.get('brier_score', 0.0)}")
        print(f"  Precision (UP / DOWN):  {res.metrics.get('precision_up', 0.0):.4f} / {res.metrics.get('precision_down', 0.0):.4f}")
        print(f"  Recall    (UP / DOWN):  {res.metrics.get('recall_up', 0.0):.4f} / {res.metrics.get('recall_down', 0.0):.4f}")
        print(f"  F1 Score  (UP / DOWN):  {res.metrics.get('f1_up', 0.0):.4f} / {res.metrics.get('f1_down', 0.0):.4f}")
        print(f"  Confusion Matrix:       {res.metrics.get('confusion_matrix')}")

        print("  Validation Gates:")
        for gate in res.gate_results:
            mark = "[PASS]" if gate.passed else "[FAIL]"
            print(f"    {mark} {gate.gate_name}: {gate.message}")

        if not res.is_promoted:
            all_promoted = False
            print(f"  [REJECTED] Model rejected by gates: {res.rejection_reason}", file=sys.stderr)
        else:
            print(f"  [PROMOTED] Model persisted to {res.active_artifact_path}")

    # Write consolidated metadata file
    consolidated_metadata = {
        "symbol": clean_sym,
        "dataset_period": {
            "start_date": split.train_start_date,
            "train_end_date": split.train_end_date,
            "holdout_start_date": split.holdout_start_date,
            "holdout_end_date": split.holdout_end_date,
            "train_outcome_cutoff": split.train_outcome_cutoff,
        },
        "sample_counts": {
            "total_labeled": split.total_rows,
            "train": split.train_rows,
            "eval": split.test_rows,
            "embargo": split.embargo_rows,
        },
        "feature_version": "index_20_features" if len(dataset.feature_names) == 20 else "canonical_37_features",
        "feature_columns": dataset.feature_names,
        "target_definition": "next_session_direction (1=UP if next_close > current_close else 0=DOWN)",
        "models": {m: res.to_dict() for m, res in results.items()},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_name = f"{clean_sym.lower()}_model_metadata.json" if clean_sym != "BHARTIARTL" else "model_metadata.json"
    meta_json_path = out_dir / meta_name
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(consolidated_metadata, f, indent=2)
    print(f"\n  [OK] Consolidated metadata saved to {meta_json_path}")

    if not all_promoted:
        print("\nERROR: One or more models failed validation gates. Review metrics above.", file=sys.stderr)
        return 1

    # Step 5: Live Inference Verification
    if not skip_inference_check:
        print("\n[Step 5/5] Verifying live inference via PredictionService...")
        service = PredictionService(provider=provider, models_dir=out_dir)

        for model_name in target_models:
            print(f"  Testing PredictionService.predict(model_name='{model_name}')...")
            req = PredictionRequest(symbol=clean_sym, model_name=model_name)
            pred_res = service.predict(req)

            if pred_res.status != PredictionStatus.SUCCESS:
                print(
                    f"ERROR: Inference verification failed for {model_name}: "
                    f"status={pred_res.status}, error={pred_res.error_message}",
                    file=sys.stderr,
                )
                return 1

            if pred_res.predicted_direction not in ("UP", "DOWN"):
                print(f"ERROR: Invalid predicted direction: {pred_res.predicted_direction}", file=sys.stderr)
                return 1

            p_up = pred_res.probability_up
            p_down = pred_res.probability_down
            if p_up is None or p_down is None or not (math.isfinite(p_up) and math.isfinite(p_down)):
                print(f"ERROR: Invalid probabilities: p_up={p_up}, p_down={p_down}", file=sys.stderr)
                return 1

            prob_sum = round(p_up + p_down, 4)
            if prob_sum != 1.0:
                print(f"ERROR: Probabilities do not sum to 1.0: {prob_sum}", file=sys.stderr)
                return 1

            print(
                f"    [PASS] {model_name.upper()} Inference Verified -> Direction: {pred_res.predicted_direction}, "
                f"P(UP)={p_up:.4f}, P(DOWN)={p_down:.4f}, Status: {pred_res.status.value}"
            )

    print("\n================================================================================")
    print("ALL MODELS SUCCESSFULLY TRAINED, GATED, PERSISTED, AND VERIFIED.")
    print("================================================================================")
    return 0


if __name__ == "__main__":
    args = parse_args()
    exit_code = train_models_pipeline(
        symbol=args.symbol,
        models=args.models,
        lookback_days=args.lookback_days,
        models_dir=args.models_dir,
        test_ratio=args.test_ratio,
        embargo_sessions=args.embargo_sessions,
        random_seed=args.random_seed,
        force_promote=args.force_promote,
        skip_inference_check=args.skip_inference_check,
    )
    sys.exit(exit_code)
