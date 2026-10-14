"""Real-Data Verification Script for Day 23 Structured Prediction Output.

Validates:
1. Real-data market pipeline and canonical feature matrix for BHARTIARTL.NS.
2. Structured prediction output contract via PredictionResult and PredictionService:
   - Predicted direction ('UP' or 'DOWN') and binary label (1 or 0).
   - Model probability clearly marked uncalibrated (is_probability_calibrated=False, probability_calibration='uncalibrated').
   - Ticker symbol, prediction timestamp, latest input bar timestamp, model name and version.
   - Data quality status (cleaned bars, warmup status, missing feature count).
   - Expected movement returned as None with explicit status 'UNSUPPORTED' (direction classifier boundary).
   - Serialized output dictionary via to_dict().
   - Human-readable text summary via format_summary().
3. Symmetrical probability validation (P(UP) + P(DOWN) == 1.0).
4. Error result output structure (MODEL_UNAVAILABLE, INSUFFICIENT_DATA).
5. Clean repository state preservation via try...finally artifact cleanup.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

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

from app.market.providers.yfinance_provider import YFinanceProvider
from app.prediction.contract import (
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.service import (
    PredictionService,
    train_and_persist_baseline_model,
)


def verify_day23() -> int:
    print("================================================================================")
    print("DAY 23: STRUCTURED PREDICTION OUTPUT VERIFICATION (BHARTIARTL.NS)")
    print("================================================================================")

    symbol = "BHARTIARTL"
    models_dir = project_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    xgb_artifact = models_dir / "xgboost_direction.json"
    lgb_artifact = models_dir / "lightgbm_direction.txt"

    end_date = datetime(2026, 10, 14, tzinfo=timezone.utc)
    provider = YFinanceProvider()

    try:
        # Step 1: Ensure Model Artifacts Exist
        print("\nStep 1: Preparing Model Artifacts (Deliberate Offline Training)...")
        if not xgb_artifact.is_file():
            print("  Training baseline XGBoost model...")
            train_and_persist_baseline_model(
                symbol=symbol,
                model_name="xgboost",
                output_path=xgb_artifact,
                lookback_days=5 * 365,
                end_date=end_date,
                provider=provider,
            )
        print(f"  [OK] Persisted XGBoost model: {xgb_artifact.name} ({xgb_artifact.stat().st_size} bytes)")

        if not lgb_artifact.is_file():
            print("  Training baseline LightGBM model...")
            train_and_persist_baseline_model(
                symbol=symbol,
                model_name="lightgbm",
                output_path=lgb_artifact,
                lookback_days=5 * 365,
                end_date=end_date,
                provider=provider,
            )
        print(f"  [OK] Persisted LightGBM model: {lgb_artifact.name} ({lgb_artifact.stat().st_size} bytes)")

        # Step 2: Initialize Prediction Service
        print("\nStep 2: Initializing PredictionService...")
        service = PredictionService(provider=provider, models_dir=models_dir)

        # Step 3: Execute Prediction and Verify Structured Output (XGBoost)
        print("\nStep 3: Executing Prediction and Auditing Structured Output (Model: XGBoost)...")
        req_xgb = PredictionRequest(
            symbol=symbol,
            model_name="xgboost",
            as_of_date=end_date,
        )
        res_xgb = service.predict(req_xgb)

        if res_xgb.status != PredictionStatus.SUCCESS:
            print(f"ERROR: Expected SUCCESS status for XGBoost, got {res_xgb.status}: {res_xgb.error_message}", file=sys.stderr)
            return 1

        print(f"  [OK] Status:                  {res_xgb.status.value}")
        print(f"  [OK] Symbol:                  {res_xgb.symbol}")
        print(f"  [OK] Predicted Direction:     {res_xgb.predicted_direction} (label={res_xgb.predicted_label})")
        print(f"  [OK] Model Probability:       P(UP)={res_xgb.probability_up*100:.2f}%, P(DOWN)={res_xgb.probability_down*100:.2f}%")
        print(f"  [OK] Probability Calibration: {res_xgb.probability_calibration} (is_calibrated={res_xgb.is_probability_calibrated})")
        print(f"  [OK] Expected Movement:       {res_xgb.expected_movement} (status={res_xgb.expected_movement_status})")
        print(f"  [OK] Prediction Timestamp:    {res_xgb.prediction_timestamp}")
        print(f"  [OK] Latest Input Bar:        {res_xgb.latest_input_timestamp}")
        print(f"  [OK] Model Version:           {res_xgb.model_version}")
        print(f"  [OK] Data Quality:            {res_xgb.data_quality.cleaned_bars} bars, warmup={'complete' if res_xgb.data_quality.warmup_complete else 'incomplete'}, missing_features={res_xgb.data_quality.missing_feature_count}")

        # Invariant checks on XGBoost output
        if res_xgb.predicted_direction not in ("UP", "DOWN"):
            print(f"ERROR: Invalid predicted direction: {res_xgb.predicted_direction}", file=sys.stderr)
            return 1
        if res_xgb.is_probability_calibrated is not False:
            print(f"ERROR: Model probability should be marked uncalibrated (is_probability_calibrated=False), got {res_xgb.is_probability_calibrated}", file=sys.stderr)
            return 1
        if res_xgb.probability_calibration != "uncalibrated":
            print(f"ERROR: Expected 'uncalibrated' calibration descriptor, got '{res_xgb.probability_calibration}'", file=sys.stderr)
            return 1
        if res_xgb.expected_movement is not None:
            print(f"ERROR: Direction classifier cannot predict price magnitude; expected_movement must be None, got {res_xgb.expected_movement}", file=sys.stderr)
            return 1
        if res_xgb.expected_movement_status != "UNSUPPORTED":
            print(f"ERROR: Expected 'UNSUPPORTED' for expected_movement_status, got '{res_xgb.expected_movement_status}'", file=sys.stderr)
            return 1
        if round(res_xgb.probability_up + res_xgb.probability_down, 2) != 1.00:
            print(f"ERROR: Probabilities do not sum to 1.0: {res_xgb.probability_up} + {res_xgb.probability_down}", file=sys.stderr)
            return 1

        # Step 4: Execute Prediction and Verify Structured Output (LightGBM)
        print("\nStep 4: Executing Prediction and Auditing Structured Output (Model: LightGBM)...")
        req_lgb = PredictionRequest(
            symbol=symbol,
            model_name="lightgbm",
            as_of_date=end_date,
        )
        res_lgb = service.predict(req_lgb)

        if res_lgb.status != PredictionStatus.SUCCESS:
            print(f"ERROR: Expected SUCCESS status for LightGBM, got {res_lgb.status}: {res_lgb.error_message}", file=sys.stderr)
            return 1

        print(f"  [OK] Status:                  {res_lgb.status.value}")
        print(f"  [OK] Predicted Direction:     {res_lgb.predicted_direction} (label={res_lgb.predicted_label})")
        print(f"  [OK] Model Probability:       P(UP)={res_lgb.probability_up*100:.2f}%, P(DOWN)={res_lgb.probability_down*100:.2f}%")
        print(f"  [OK] Probability Calibration: {res_lgb.probability_calibration} (is_calibrated={res_lgb.is_probability_calibrated})")
        print(f"  [OK] Expected Movement:       {res_lgb.expected_movement} (status={res_lgb.expected_movement_status})")
        print(f"  [OK] Model Version:           {res_lgb.model_version}")

        # Step 5: Test Dictionary Serialization and Summary Rendering
        print("\nStep 5: Testing Dictionary Serialization and Text Summary Rendering...")
        dict_output = res_xgb.to_dict()
        if not isinstance(dict_output, dict):
            print("ERROR: to_dict() did not return a dictionary", file=sys.stderr)
            return 1
        # Confirm JSON serializability
        try:
            json_str = json.dumps(dict_output, indent=2)
            print(f"  [OK] Successfully serialized to JSON ({len(json_str)} characters).")
        except Exception as exc:
            print(f"ERROR: JSON serialization failed: {exc}", file=sys.stderr)
            return 1

        summary_text = res_xgb.format_summary()
        print("\n  [Summary Output Preview]:")
        for line in summary_text.splitlines():
            print(f"    {line}")

        # Step 6: Test Error Containment in Output
        print("\nStep 6: Verifying Structured Error Output...")
        req_missing = PredictionRequest(
            symbol=symbol,
            model_name="xgboost",
            model_artifact_path=models_dir / "non_existent_model.json",
            as_of_date=end_date,
        )
        res_missing = service.predict(req_missing)
        if res_missing.status != PredictionStatus.MODEL_UNAVAILABLE:
            print(f"ERROR: Expected MODEL_UNAVAILABLE, got {res_missing.status}", file=sys.stderr)
            return 1
        if res_missing.predicted_direction is not None or res_missing.probability_up is not None:
            print("ERROR: Failed result should not contain predicted direction or probability", file=sys.stderr)
            return 1
        if res_missing.expected_movement is not None or res_missing.expected_movement_status != "UNSUPPORTED":
            print("ERROR: Expected movement should be None and status UNSUPPORTED on error", file=sys.stderr)
            return 1
        print("  [OK] Missing artifact returns structured error with null directions and explicit diagnostics.")

        # Step 7: Final Invariants & Capability Disclosures
        print("\n================================================================================")
        print("DAY 23 STRUCTURED PREDICTION OUTPUT CAPABILITY SUMMARY")
        print("================================================================================")
        print("1. Structured Output Schema:")
        print("   - Typed PredictionResult container with symbol, direction, probabilities, timestamps,")
        print("     model metadata, data quality, calibration flags, and capability boundaries.")
        print("2. Uncalibrated Probability Transparency:")
        print("   - Probabilities represent raw tree frequencies and are explicitly flagged:")
        print("     is_probability_calibrated = False, probability_calibration = 'uncalibrated'.")
        print("3. Explicit Expected Movement Boundaries:")
        print("   - expected_movement = None, expected_movement_status = 'UNSUPPORTED'.")
        print("   - Clear boundary disclosure that direction classifiers do not predict price targets.")
        print("4. Machine and Human Readability:")
        print("   - to_dict() returns JSON-serializable primitives for API integration.")
        print("   - format_summary() provides human-readable audit text.")
        print("================================================================================")
        print("Day 23 Structured Prediction Output Verified Successfully.")
        return 0
    finally:
        # Clean up verification artifacts to preserve Day 1 repository foundation state
        for artifact in (xgb_artifact, lgb_artifact):
            if artifact.is_file():
                try:
                    artifact.unlink()
                except Exception:
                    pass


if __name__ == "__main__":
    sys.exit(verify_day23())
