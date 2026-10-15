"""Real-Data Verification Script for Day 25 Prediction Outcome Verification & Evaluation.

Demonstrates:
1. SQLite schema with actuals immutability triggers (trg_prevent_actual_update, trg_prevent_actual_delete).
2. Fetching real market data for BHARTIARTL.NS via YFinanceProvider.
3. Historical prediction outcome verification:
   - Verification of completed market sessions (t+1 session closed).
   - Canonical return and direction computation matching documented Day 15 target definition.
   - Provenance tracking and idempotent persistence into SQLite actuals table.
4. Pending outcome detection:
   - Identification of predictions whose t+1 session has not completed yet.
   - Pending predictions remain unverified without data leakage.
5. Evaluation metrics calculation:
   - Evaluation across repository predictions.
   - Strict denominator correctness: accuracy computed solely from verified predictions.
   - Symmetrical class metrics and confusion matrix.
6. Immutability & rejection of conflicting outcomes:
   - SQLite triggers reject UPDATE/DELETE.
   - Repository rejects conflicting outcome insertion.
7. Clean artifact cleanup in try...finally block.
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
from app.history.contract import ActualOutcome, VerificationStatus
from app.history.evaluator import PredictionEvaluator
from app.history.verifier import OutcomeVerifier
from app.market.providers.yfinance_provider import YFinanceProvider
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.service import (
    PredictionService,
    train_and_persist_baseline_model,
)


def verify_day25() -> int:
    print("================================================================================")
    print("DAY 25: OUTCOME VERIFICATION & EVALUATION FOUNDATION REAL-DATA VERIFICATION")
    print("================================================================================")

    symbol = "BHARTIARTL"
    models_dir = project_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    xgb_artifact = models_dir / "xgboost_direction.json"

    test_db_path = project_root / "data" / "verify_day25_temp.db"
    provider = YFinanceProvider()

    try:
        # Step 1: Initialize Database & Verify Schema
        print("\n[Step 1] Initializing SQLite database schema and checking triggers...")
        repo = PredictionRepository(db_path=test_db_path)
        cursor = repo.connection.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'trigger');")
        schema_objects = {row[0]: row[1] for row in cursor.fetchall()}

        print(f"  Initialized test database at: {test_db_path}")
        print(f"  Detected tables: {[k for k, v in schema_objects.items() if v == 'table']}")
        print(f"  Detected triggers: {[k for k, v in schema_objects.items() if v == 'trigger']}")

        assert "actuals" in schema_objects, "actuals table missing"
        assert "trg_prevent_actual_update" in schema_objects, "actuals update trigger missing"
        assert "trg_prevent_actual_delete" in schema_objects, "actuals delete trigger missing"
        print("  -> Schema verification PASSED.")

        # Step 2: Fetch real market data for BHARTIARTL.NS
        print(f"\n[Step 2] Fetching real daily market bars for {symbol}.NS...")
        from datetime import timedelta
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=90)
        bars = provider.fetch_historical_ohlcv(symbol=symbol, start_date=start_date, end_date=end_date)
        print(f"  Fetched {len(bars)} real daily bars from {bars[0].timestamp.isoformat()[:10]} to {bars[-1].timestamp.isoformat()[:10]}")
        assert len(bars) >= 10, "Insufficient bars fetched from provider."

        # Step 3: Ensure baseline model exists
        print("\n[Step 3] Ensuring baseline XGBoost model artifact is ready...")
        if not xgb_artifact.exists():
            print(f"  Training baseline model for {symbol}...")
            train_and_persist_baseline_model(symbol=symbol, model_name="xgboost", provider=provider, output_path=xgb_artifact)
        print(f"  -> Model ready at {xgb_artifact.name}")

        service = PredictionService(
            provider=provider,
            model_registry={"xgboost": xgb_artifact},
            repository=repo,
        )
        verifier = OutcomeVerifier(repository=repo)
        evaluator = PredictionEvaluator(repository=repo)

        # Step 4: Real-Data Completed Outcome Verification
        # We simulate a historical prediction made at bar index -5 (5 trading sessions ago)
        hist_bar = bars[-5]
        next_bar = bars[-4]
        hist_ref_close = hist_bar.close
        hist_actual_close = next_bar.close
        hist_ret = (hist_actual_close / hist_ref_close) - 1.0
        expected_actual_dir = "UP" if hist_ret > 0 else "DOWN"

        hist_ts = hist_bar.timestamp.isoformat()
        print(f"\n[Step 4] Creating historical prediction for session {hist_ts[:10]} (Close: {hist_ref_close:.2f})...")
        hist_pred = PredictionResult(
            symbol=symbol,
            prediction_timestamp=datetime.now(timezone.utc).isoformat(),
            latest_input_timestamp=hist_ts,
            status=PredictionStatus.SUCCESS,
            predicted_direction="UP",
            predicted_label=1,
            probability_up=0.58,
            probability_down=0.42,
            model_name="xgboost",
            model_version="1.0.0",
            model_metadata={"seed": 42},
            data_quality=PredictionDataQuality(
                total_bars_fetched=100,
                cleaned_bars=100,
                warmup_bars_required=34,
                warmup_complete=True,
                latest_bar_timestamp=hist_ts,
                missing_feature_count=0,
                missing_features=[],
                is_stale=False,
                stale_days=0,
            ),
            is_probability_calibrated=False,
            probability_calibration="uncalibrated",
            expected_movement=None,
            expected_movement_status="UNSUPPORTED",
            error_message=None,
            disclaimer="Directional forecast only.",
        )
        hist_pred_id = "real-hist-pred-001"
        repo.save_prediction(hist_pred, prediction_id=hist_pred_id)
        print(f"  Saved historical prediction {hist_pred_id}")

        print("  Verifying historical prediction outcome against real market bars...")
        v_rec = verifier.verify_prediction(hist_pred_id, market_bars=bars)
        print(f"  Verification Status: {v_rec.status.value}")
        print(f"  Reference Session ({hist_ts[:10]}): Close = {v_rec.reference_close:.2f}")
        print(f"  Target Session ({v_rec.target_date[:10]}): Close = {v_rec.actual_close:.2f}")
        print(f"  Realized Return: {v_rec.actual_return:+.4%}")
        print(f"  Actual Direction: {v_rec.actual_direction}")
        print(f"  Predicted Direction: {hist_pred.predicted_direction}")
        print(f"  Outcome Correct: {v_rec.is_correct}")

        assert v_rec.status == VerificationStatus.VERIFIED
        assert v_rec.actual_direction == expected_actual_dir
        assert repo.get_actual(hist_pred_id) is not None
        print("  -> Historical outcome verification PASSED.")

        # Test idempotency: re-running verification
        print("  Checking idempotency of repeated verification...")
        v_rec_repeat = verifier.verify_prediction(hist_pred_id, market_bars=bars)
        assert v_rec_repeat.status == VerificationStatus.ALREADY_VERIFIED
        print(f"  Repeated verification status: {v_rec_repeat.status.value} (Idempotent: PASSED)")

        # Step 5: Real-Data Pending Session Verification
        # Generate prediction for the latest available bar in the market data
        latest_bar = bars[-1]
        latest_ts = latest_bar.timestamp.isoformat()
        print(f"\n[Step 5] Creating prediction for latest market session {latest_ts[:10]} (Close: {latest_bar.close:.2f})...")
        latest_pred = PredictionResult(
            symbol=symbol,
            prediction_timestamp=datetime.now(timezone.utc).isoformat(),
            latest_input_timestamp=latest_ts,
            status=PredictionStatus.SUCCESS,
            predicted_direction="DOWN",
            predicted_label=0,
            probability_up=0.45,
            probability_down=0.55,
            model_name="xgboost",
            model_version="1.0.0",
            model_metadata={"seed": 42},
            data_quality=PredictionDataQuality(
                total_bars_fetched=100,
                cleaned_bars=100,
                warmup_bars_required=34,
                warmup_complete=True,
                latest_bar_timestamp=latest_ts,
                missing_feature_count=0,
                missing_features=[],
                is_stale=False,
                stale_days=0,
            ),
            is_probability_calibrated=False,
            probability_calibration="uncalibrated",
            expected_movement=None,
            expected_movement_status="UNSUPPORTED",
            error_message=None,
            disclaimer="Directional forecast only.",
        )
        latest_pred_id = "real-latest-pred-002"
        repo.save_prediction(latest_pred, prediction_id=latest_pred_id)
        print(f"  Saved latest prediction {latest_pred_id}")

        print("  Verifying latest prediction against current market data...")
        v_pending = verifier.verify_prediction(latest_pred_id, market_bars=bars)
        print(f"  Verification Status: {v_pending.status.value}")
        print(f"  Detail Message: {v_pending.message}")
        assert v_pending.status == VerificationStatus.PENDING
        assert repo.get_actual(latest_pred_id) is None
        print("  -> Pending outcome detection PASSED.")

        # Step 6: Prediction Evaluation Metrics
        print("\n[Step 6] Running prediction evaluation on repository...")
        metrics = evaluator.evaluate()
        print(metrics.format_summary())

        assert metrics.total_predictions == 2
        assert metrics.eligible_predictions == 2
        assert metrics.pending_predictions == 1
        assert metrics.verified_predictions == 1
        assert metrics.directional_accuracy is not None
        # Verify denominator is strictly verified_predictions (1) and not total (2)
        assert metrics.verified_predictions == metrics.correct_predictions + metrics.incorrect_predictions
        print("  -> Evaluation metrics and denominator isolation PASSED.")

        # Step 7: Immutability and Conflict Rejection Check
        print("\n[Step 7] Checking SQLite engine immutability and conflict prevention...")
        try:
            repo.connection.execute("UPDATE actuals SET actual_close = 9999.0 WHERE prediction_id = ?", (hist_pred_id,))
            print("  ERROR: UPDATE trigger failed to block modification!")
            return 1
        except sqlite3.IntegrityError as e:
            print(f"  UPDATE trigger blocked modification as expected: {e}")

        try:
            repo.connection.execute("DELETE FROM actuals WHERE prediction_id = ?", (hist_pred_id,))
            print("  ERROR: DELETE trigger failed to block deletion!")
            return 1
        except sqlite3.IntegrityError as e:
            print(f"  DELETE trigger blocked deletion as expected: {e}")

        try:
            conflicting_outcome = ActualOutcome(
                prediction_id=hist_pred_id,
                symbol=symbol,
                target_date=v_rec.target_date,
                actual_direction="DOWN" if v_rec.actual_direction == "UP" else "UP",
                actual_label=0 if v_rec.actual_label == 1 else 1,
                actual_return=-9.99,
                actual_close=1.0,
            )
            repo.save_actual(conflicting_outcome)
            print("  ERROR: Repository failed to reject conflicting actual outcome!")
            return 1
        except ValueError as e:
            print(f"  Repository rejected conflicting outcome as expected: {e}")

        print("  -> Immutability and conflict rejection PASSED.")

        print("\n================================================================================")
        print("ALL DAY 25 REAL-DATA VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("================================================================================")
        return 0

    except Exception as exc:
        print(f"\nVerification FAILED with exception: {exc}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Step 8: Strict Cleanup
        print("\n[Cleanup] Cleaning up temporary SQLite database...")
        try:
            if 'repo' in locals() and repo.connection:
                repo.connection.close()
        except Exception:
            pass
        if test_db_path.exists():
            try:
                test_db_path.unlink()
                print(f"  Removed temporary database: {test_db_path}")
            except Exception as e:
                print(f"  Warning: could not remove {test_db_path}: {e}")


if __name__ == "__main__":
    sys.exit(verify_day25())
