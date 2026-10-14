"""Real-Data Verification Script for Day 24 SQLite Prediction Database & Immutable Persistence.

Validates:
1. SQLite schema initialization: stocks, model_versions, predictions, and actuals tables.
2. Real-data market pipeline and model inference for BHARTIARTL.NS.
3. Prediction persistence into SQLite via PredictionRepository:
   - Preserves Day 23 uncalibrated probability semantics (is_probability_calibrated=False, probability_calibration='uncalibrated').
   - Preserves Day 23 unsupported expected movement semantics (expected_movement=None, expected_movement_status='UNSUPPORTED').
   - Full lossless payload serialization in raw_result_json.
   - Automatic registration of stock in stocks and model in model_versions.
4. Native SQLite engine immutability enforcement:
   - Rejection of UPDATE operations via trigger.
   - Rejection of DELETE operations via trigger.
   - Rejection of duplicate prediction_id insertion.
5. Strict artifact cleanup in try...finally block.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
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

from app.database.connection import create_connection
from app.database.repository import PredictionRepository
from app.database.schema import initialize_database
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


def verify_day24() -> int:
    print("================================================================================")
    print("DAY 24: SQLITE PREDICTION DATABASE & IMMUTABLE PERSISTENCE VERIFICATION")
    print("================================================================================")

    symbol = "BHARTIARTL"
    models_dir = project_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    xgb_artifact = models_dir / "xgboost_direction.json"

    # Temporary database for verification run
    test_db_path = project_root / "data" / "verify_day24_temp.db"
    provider = YFinanceProvider()

    try:
        # Step 1: Initialize Database & Verify Schema
        print("\n[Step 1] Initializing SQLite database schema...")
        repo = PredictionRepository(db_path=test_db_path)
        cursor = repo.connection.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'trigger');")
        schema_objects = {row[0]: row[1] for row in cursor.fetchall()}

        print(f"  Initialized database at: {test_db_path}")
        print(f"  Detected tables: {[k for k, v in schema_objects.items() if v == 'table']}")
        print(f"  Detected triggers: {[k for k, v in schema_objects.items() if v == 'trigger']}")

        assert "stocks" in schema_objects, "stocks table missing"
        assert "model_versions" in schema_objects, "model_versions table missing"
        assert "predictions" in schema_objects, "predictions table missing"
        assert "actuals" in schema_objects, "actuals table missing"
        assert "trg_prevent_prediction_update" in schema_objects, "update trigger missing"
        assert "trg_prevent_prediction_delete" in schema_objects, "delete trigger missing"
        print("  -> Schema verification PASSED.")

        # Step 2: Ensure Baseline Model Exists
        print("\n[Step 2] Verifying baseline XGBoost model artifact...")
        if not xgb_artifact.exists():
            print(f"  Training baseline XGBoost model for {symbol}...")
            train_and_persist_baseline_model(
                symbol=symbol,
                model_name="xgboost",
                provider=provider,
                output_path=xgb_artifact,
            )
        assert xgb_artifact.exists(), "Failed to prepare XGBoost model artifact."
        print(f"  -> Baseline model ready at {xgb_artifact.name}")

        # Step 3: Execute Prediction Inference with Service
        print("\n[Step 3] Running real prediction inference for BHARTIARTL.NS...")
        service = PredictionService(
            provider=provider,
            models_dir=models_dir,
            repository=repo,
        )
        request = PredictionRequest(
            symbol=symbol,
            model_name="xgboost",
            model_artifact_path=xgb_artifact,
            lookback_days=5 * 365,
        )
        # Execute prediction and persist atomically
        pred_result = service.predict(request, persist=True)

        print(f"  Prediction Status: {pred_result.status.value}")
        print(f"  Direction:         {pred_result.predicted_direction} (label={pred_result.predicted_label})")
        print(f"  P(UP):             {pred_result.probability_up * 100:.2f}%")
        print(f"  P(DOWN):           {pred_result.probability_down * 100:.2f}%")
        print(f"  Calibrated:        {pred_result.is_probability_calibrated} ({pred_result.probability_calibration})")
        print(f"  Expected Movement: {pred_result.expected_movement} ({pred_result.expected_movement_status})")
        assert pred_result.status == PredictionStatus.SUCCESS, f"Inference failed: {pred_result.error_message}"
        print("  -> Prediction inference PASSED.")

        # Step 4: Verify Persistence and Semantics in SQLite
        print("\n[Step 4] Auditing persisted prediction records in SQLite...")
        persisted_records = repo.list_predictions(symbol=symbol)
        assert len(persisted_records) >= 1, "No persisted predictions found in database"
        latest_rec = persisted_records[0]

        print(f"  Found {len(persisted_records)} persisted prediction(s) for {symbol}")
        print(f"  Prediction ID:             {latest_rec['prediction_id']}")
        print(f"  Stored Symbol:             {latest_rec['symbol']}")
        print(f"  Stored Model:              {latest_rec['model_name']} ({latest_rec['model_version']})")
        print(f"  Stored Direction:          {latest_rec['predicted_direction']}")
        print(f"  Stored P(UP) / P(DOWN):    {latest_rec['probability_up']} / {latest_rec['probability_down']}")
        print(f"  is_probability_calibrated: {latest_rec['is_probability_calibrated']} (expected: 0)")
        print(f"  probability_calibration:   {latest_rec['probability_calibration']} (expected: 'uncalibrated')")
        print(f"  expected_movement:         {latest_rec['expected_movement']} (expected: None)")
        print(f"  expected_movement_status:  {latest_rec['expected_movement_status']} (expected: 'UNSUPPORTED')")

        assert latest_rec["is_probability_calibrated"] == 0
        assert latest_rec["probability_calibration"] == "uncalibrated"
        assert latest_rec["expected_movement"] is None
        assert latest_rec["expected_movement_status"] == "UNSUPPORTED"
        assert latest_rec["raw_result"] is not None
        assert latest_rec["raw_result"]["symbol"] == symbol

        # Verify parent tables populated
        stocks = repo.get_stocks()
        assert any(s["symbol"] == symbol for s in stocks), f"{symbol} missing from stocks table"
        models = repo.get_model_versions(model_name="xgboost")
        assert len(models) >= 1, "xgboost missing from model_versions table"
        print("  -> Persistence and relational constraints PASSED.")

        # Step 5: Verify Immutability Enforcement (Triggers)
        print("\n[Step 5] Testing SQLite trigger immutability enforcement...")
        pid = latest_rec["prediction_id"]

        # Attempt UPDATE
        update_blocked = False
        try:
            repo.connection.execute("UPDATE predictions SET predicted_direction = 'FLIPPED' WHERE prediction_id = ?;", (pid,))
        except sqlite3.DatabaseError as exc:
            update_blocked = True
            print(f"  UPDATE successfully rejected by SQLite trigger: {exc}")
        assert update_blocked, "CRITICAL: UPDATE operation was not blocked by SQLite trigger!"

        # Attempt DELETE
        delete_blocked = False
        try:
            repo.connection.execute("DELETE FROM predictions WHERE prediction_id = ?;", (pid,))
        except sqlite3.DatabaseError as exc:
            delete_blocked = True
            print(f"  DELETE successfully rejected by SQLite trigger: {exc}")
        assert delete_blocked, "CRITICAL: DELETE operation was not blocked by SQLite trigger!"

        # Attempt duplicate insert
        dup_blocked = False
        try:
            repo.save_prediction(pred_result, prediction_id=pid)
        except sqlite3.IntegrityError as exc:
            dup_blocked = True
            print(f"  Duplicate prediction_id successfully rejected: {exc}")
        assert dup_blocked, "CRITICAL: Duplicate prediction_id was not rejected!"

        print("  -> Immutability enforcement PASSED.")
        repo.close()

        print("\n================================================================================")
        print("DAY 24 VERIFICATION COMPLETED SUCCESSFULLY (100% INVARIANTS SATISFIED)")
        print("================================================================================")
        return 0

    finally:
        # Cleanup transient files to ensure working tree cleanliness
        print("\n[Cleanup] Cleaning up transient verification artifacts...")
        if "repo" in locals() and repo is not None:
            try:
                repo.close()
            except Exception:
                pass
        for transient in (
            xgb_artifact,
            test_db_path,
            Path(str(test_db_path) + "-wal"),
            Path(str(test_db_path) + "-shm"),
        ):
            if transient.exists():
                try:
                    transient.unlink()
                    print(f"  Cleaned up {transient.name}")
                except Exception as exc:
                    print(f"  Warning: Failed to remove {transient.name}: {exc}")


if __name__ == "__main__":
    sys.exit(verify_day24())
