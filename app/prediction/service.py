"""Prediction Engine Service Layer.

Provides the core PredictionService orchestrating market data ingestion,
canonical feature matrix assembly, data quality validation, and trained
model inference without automatic on-the-fly retraining.
"""

from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from app.core.schemas import MarketOHLCV
from app.market.pipeline import (
    MarketDataPipelineResult,
    run_market_data_pipeline,
)
from app.market.providers.base import BaseMarketDataProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)
from app.training.lightgbm_classifier import (
    LightGBMConfig,
    LightGBMDirectionClassifier,
)
from app.training.xgboost_classifier import (
    XGBoostConfig,
    XGBoostDirectionClassifier,
)

logger = logging.getLogger(__name__)

# Minimum required sessions for indicator warm-up (MACD slow EMA 26 + signal EMA 9 = 34 bars)
MIN_WARMUP_BARS = 34


class PredictionService:
    """Production prediction service for next-session directional stock forecasting.

    Orchestrates market data retrieval, feature generation, data quality auditing,
    and model inference. Enforces strict temporal isolation and prohibits silent
    automatic retraining during inference requests.
    """

    def __init__(
        self,
        provider: Optional[BaseMarketDataProvider] = None,
        models_dir: Optional[Union[str, Path]] = None,
        model_registry: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize prediction service with data provider and model storage.

        Args:
            provider: Market data provider instance (defaults to YFinanceProvider).
            models_dir: Filesystem directory containing persisted model artifacts.
            model_registry: Optional in-memory mapping of model_name -> fitted classifier.
        """
        self.provider = provider or YFinanceProvider()
        self.models_dir = Path(models_dir) if models_dir else Path("models")
        self.model_registry: Dict[str, Any] = dict(model_registry) if model_registry else {}

    def _get_default_artifact_path(self, model_name: str) -> Path:
        """Resolve the canonical default artifact filepath for a model architecture."""
        if model_name == "xgboost":
            return self.models_dir / "xgboost_direction.json"
        if model_name == "lightgbm":
            return self.models_dir / "lightgbm_direction.txt"
        return self.models_dir / f"{model_name}_direction.bin"

    def register_model(self, model_name: str, model: Any) -> None:
        """Register a pre-trained in-memory classifier instance."""
        if not getattr(model, "is_fitted", False):
            raise ValueError(f"Cannot register unfitted model for '{model_name}'.")
        self.model_registry[model_name] = model
        logger.info("Registered in-memory model for '%s'", model_name)

    def _resolve_model(
        self,
        model_name: str,
        explicit_artifact_path: Optional[Union[str, Path]] = None,
        preloaded_model: Optional[Any] = None,
    ) -> Tuple[Optional[Any], Optional[str]]:
        """Resolve a fitted model from preloaded object, in-memory registry, or disk.

        Returns:
            Tuple of (model_instance, error_message).
        """
        # 1. Direct preloaded model argument
        if preloaded_model is not None:
            if not getattr(preloaded_model, "is_fitted", False):
                return None, "Supplied preloaded_model is not fitted."
            return preloaded_model, None

        # 2. In-memory model registry
        if model_name in self.model_registry:
            reg_model = self.model_registry[model_name]
            if not getattr(reg_model, "is_fitted", False):
                return None, f"Registry model for '{model_name}' is not fitted."
            return reg_model, None

        # 3. Persistent filesystem artifact
        artifact_path = (
            Path(explicit_artifact_path)
            if explicit_artifact_path
            else self._get_default_artifact_path(model_name)
        )

        if not artifact_path.is_file():
            return None, (
                f"Model artifact not found at '{artifact_path}'. "
                f"Models must be trained and persisted deliberately using app.training "
                f"prior to inference. Automatic on-the-fly retraining during inference is prohibited."
            )

        try:
            if model_name == "xgboost":
                loaded_model = XGBoostDirectionClassifier.load_model(artifact_path)
            elif model_name == "lightgbm":
                loaded_model = LightGBMDirectionClassifier().load_model(artifact_path)
            else:
                return None, f"Unsupported model architecture '{model_name}'."
            return loaded_model, None
        except Exception as exc:
            logger.error("Failed to load model artifact '%s': %s", artifact_path, exc)
            return None, f"Failed to deserialize model artifact '{artifact_path}': {exc}"

    def predict(
        self,
        request: PredictionRequest,
        preloaded_model: Optional[Any] = None,
    ) -> PredictionResult:
        """Execute directional movement prediction for a stock symbol.

        Steps:
        1. Validates symbol and request parameters.
        2. Retrieves market data using point-in-time boundaries.
        3. Assembles canonical 37-feature matrix.
        4. Validates data quality, warmup sufficiency, and absence of NaN values.
        5. Resolves fitted model without automatic retraining.
        6. Computes class probabilities and returns structured PredictionResult.

        Args:
            request: PredictionRequest specification.
            preloaded_model: Optional fitted classifier instance overriding disk lookup.

        Returns:
            PredictionResult detailing direction, probability, data quality, and metadata.
        """
        pred_time_str = datetime.now(timezone.utc).isoformat()
        clean_symbol = request.symbol.strip().upper()

        # Step 1: Request Validation
        if not clean_symbol:
            return self._build_error_result(
                symbol=request.symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.INVALID_REQUEST,
                error_message="Symbol cannot be empty or whitespace.",
                model_name=request.model_name,
            )

        ref_time = request.as_of_date or datetime.now(timezone.utc)
        start_date = ref_time - timedelta(days=request.lookback_days)

        # Step 2: Market Data Retrieval
        try:
            pipeline_result = run_market_data_pipeline(
                symbol=clean_symbol,
                start_date=start_date,
                end_date=ref_time,
                provider=self.provider,
            )
        except Exception as exc:
            logger.error("Market data pipeline failed for symbol '%s': %s", clean_symbol, exc)
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.FAILED,
                error_message=f"Market data pipeline error: {exc}",
                model_name=request.model_name,
            )

        cleaned_records = pipeline_result.cleaned_records
        n_cleaned = len(cleaned_records)
        raw_count = (
            n_cleaned
            + pipeline_result.cleaning_summary.missing_records_count
            + pipeline_result.cleaning_summary.invalid_records_count
        )

        if n_cleaned == 0:
            quality = PredictionDataQuality(
                total_bars_fetched=raw_count,
                cleaned_bars=0,
                warmup_bars_required=MIN_WARMUP_BARS,
                warmup_complete=False,
                latest_bar_timestamp=None,
                missing_feature_count=len(FEATURE_COLUMNS),
                missing_features=list(FEATURE_COLUMNS),
                is_stale=True,
                stale_days=None,
            )
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.INSUFFICIENT_DATA,
                error_message=f"No market data found for symbol '{clean_symbol}' in range {start_date.date()} to {ref_time.date()}.",
                model_name=request.model_name,
                data_quality=quality,
            )

        latest_bar = cleaned_records[-1]
        latest_bar_date = latest_bar.timestamp.date()
        latest_bar_iso = latest_bar.timestamp.isoformat()

        # Check Warmup Sufficiency
        warmup_ok = n_cleaned >= MIN_WARMUP_BARS
        stale_days = abs((ref_time.date() - latest_bar_date).days)
        is_stale = stale_days > request.max_stale_days

        if not warmup_ok:
            quality = PredictionDataQuality(
                total_bars_fetched=raw_count,
                cleaned_bars=n_cleaned,
                warmup_bars_required=MIN_WARMUP_BARS,
                warmup_complete=False,
                latest_bar_timestamp=latest_bar_iso,
                missing_feature_count=len(FEATURE_COLUMNS),
                missing_features=list(FEATURE_COLUMNS),
                is_stale=is_stale,
                stale_days=stale_days,
            )
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.INSUFFICIENT_DATA,
                error_message=(
                    f"Insufficient historical bars for '{clean_symbol}': {n_cleaned} bars available, "
                    f"minimum {MIN_WARMUP_BARS} required for technical indicator warm-up."
                ),
                model_name=request.model_name,
                data_quality=quality,
            )

        if is_stale and not request.allow_stale_data:
            quality = PredictionDataQuality(
                total_bars_fetched=raw_count,
                cleaned_bars=n_cleaned,
                warmup_bars_required=MIN_WARMUP_BARS,
                warmup_complete=True,
                latest_bar_timestamp=latest_bar_iso,
                missing_feature_count=0,
                missing_features=[],
                is_stale=True,
                stale_days=stale_days,
            )
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.STALE_DATA,
                error_message=(
                    f"Latest market bar for '{clean_symbol}' ({latest_bar_date}) is {stale_days} "
                    f"calendar days old, exceeding max_stale_days={request.max_stale_days}."
                ),
                model_name=request.model_name,
                data_quality=quality,
            )

        # Step 3: Feature Matrix Assembly & Isolation Guard
        try:
            dataset = assemble_feature_matrix(pipeline_result)
        except Exception as exc:
            logger.error("Feature assembly failed for symbol '%s': %s", clean_symbol, exc)
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.FEATURE_ERROR,
                error_message=f"Feature matrix assembly failed: {exc}",
                model_name=request.model_name,
            )

        # Extract the latest feature row (t = N - 1)
        latest_idx = len(dataset.X) - 1
        X_latest = dataset.X.iloc[[latest_idx]].copy()

        # Enforce strict feature matrix isolation (rejects target/future columns)
        validate_feature_matrix_isolation(X_latest)

        # Enforce canonical column order
        X_latest = X_latest[FEATURE_COLUMNS]

        # Check for missing values in latest observation
        nan_cols = [c for c in FEATURE_COLUMNS if pd.isna(X_latest[c].iloc[0])]
        quality = PredictionDataQuality(
            total_bars_fetched=raw_count,
            cleaned_bars=n_cleaned,
            warmup_bars_required=MIN_WARMUP_BARS,
            warmup_complete=True,
            latest_bar_timestamp=latest_bar_iso,
            missing_feature_count=len(nan_cols),
            missing_features=nan_cols,
            is_stale=is_stale,
            stale_days=stale_days,
        )

        if nan_cols:
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.FEATURE_ERROR,
                error_message=(
                    f"Inference observation for '{clean_symbol}' at {latest_bar_date} contains "
                    f"{len(nan_cols)} NaN feature values: {nan_cols}. Cannot execute model."
                ),
                model_name=request.model_name,
                data_quality=quality,
            )

        # Step 4: Model Resolution (Strictly No Automatic Retraining)
        model, model_err = self._resolve_model(
            model_name=request.model_name,
            explicit_artifact_path=request.model_artifact_path,
            preloaded_model=preloaded_model,
        )

        if model is None:
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.MODEL_UNAVAILABLE,
                error_message=model_err or "Model resolution failed.",
                model_name=request.model_name,
                data_quality=quality,
            )

        # Step 5: Feature Schema Parity Check
        model_feats = getattr(model, "feature_names", [])
        if model_feats and list(model_feats) != FEATURE_COLUMNS:
            if set(model_feats) == set(FEATURE_COLUMNS):
                X_latest = X_latest[model_feats]
            else:
                return self._build_error_result(
                    symbol=clean_symbol,
                    prediction_timestamp=pred_time_str,
                    status=PredictionStatus.FEATURE_ERROR,
                    error_message=(
                        f"Model feature mismatch: model expects {len(model_feats)} features, "
                        f"feature matrix produced {len(FEATURE_COLUMNS)}."
                    ),
                    model_name=request.model_name,
                    data_quality=quality,
                )

        # Step 6: Model Inference Execution
        try:
            probs = model.predict_proba(X_latest)
            p_up = round(float(probs[0, 1]), 4)
            p_down = round(float(probs[0, 0]), 4)
            label = 1 if p_up > 0.5 else 0
            direction = "UP" if label == 1 else "DOWN"
        except Exception as exc:
            logger.error("Inference execution failed on model '%s': %s", request.model_name, exc)
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.FAILED,
                error_message=f"Model inference failed: {exc}",
                model_name=request.model_name,
                data_quality=quality,
            )

        # Step 7: Build Successful PredictionResult
        cfg = getattr(model, "config", None)
        model_meta = cfg.to_dict() if hasattr(cfg, "to_dict") else {}
        model_version = f"{request.model_name}-direction-v1"

        return PredictionResult(
            symbol=clean_symbol,
            prediction_timestamp=pred_time_str,
            latest_input_timestamp=latest_bar_iso,
            status=PredictionStatus.SUCCESS,
            predicted_direction=direction,
            predicted_label=label,
            probability_up=p_up,
            probability_down=p_down,
            is_probability_calibrated=False,
            probability_calibration="uncalibrated",
            expected_movement=None,
            expected_movement_status="UNSUPPORTED",
            model_name=request.model_name,
            model_version=model_version,
            model_metadata=model_meta,
            data_quality=quality,
            error_message=None,
        )

    def _build_error_result(
        self,
        symbol: str,
        prediction_timestamp: str,
        status: PredictionStatus,
        error_message: str,
        model_name: str,
        data_quality: Optional[PredictionDataQuality] = None,
    ) -> PredictionResult:
        """Construct standard error result container."""
        if data_quality is None:
            data_quality = PredictionDataQuality(
                total_bars_fetched=0,
                cleaned_bars=0,
                warmup_bars_required=MIN_WARMUP_BARS,
                warmup_complete=False,
                latest_bar_timestamp=None,
                missing_feature_count=len(FEATURE_COLUMNS),
                missing_features=list(FEATURE_COLUMNS),
                is_stale=False,
                stale_days=None,
            )
        return PredictionResult(
            symbol=symbol,
            prediction_timestamp=prediction_timestamp,
            latest_input_timestamp=data_quality.latest_bar_timestamp,
            status=status,
            predicted_direction=None,
            predicted_label=None,
            probability_up=None,
            probability_down=None,
            is_probability_calibrated=False,
            probability_calibration="uncalibrated",
            expected_movement=None,
            expected_movement_status="UNSUPPORTED",
            model_name=model_name,
            model_version=f"{model_name}-direction-v1",
            model_metadata={},
            data_quality=data_quality,
            error_message=error_message,
        )


def train_and_persist_baseline_model(
    symbol: str = "BHARTIARTL",
    model_name: str = "xgboost",
    output_path: Optional[Union[str, Path]] = None,
    lookback_days: int = 5 * 365,
    end_date: Optional[datetime] = None,
    provider: Optional[BaseMarketDataProvider] = None,
) -> Path:
    """Deliberately train and serialize a baseline direction classifier to disk.

    This function represents the explicit training lifecycle step. It is NOT
    invoked automatically during PredictionService.predict().

    Args:
        symbol: Ticker symbol to train on.
        model_name: 'xgboost' or 'lightgbm'.
        output_path: Destination path for serialized model (default: models/{model_name}_direction.*).
        lookback_days: Lookback window in days (default: 5 years).
        end_date: Cutoff date for training observations.
        provider: Market data provider instance.

    Returns:
        Path to persisted model file.

    Raises:
        ValueError: On unsupported model_name or insufficient labeled training data.
    """
    prov = provider or YFinanceProvider()
    cutoff = end_date or datetime.now(timezone.utc)
    start_date = cutoff - timedelta(days=lookback_days)

    pipeline_result = run_market_data_pipeline(
        symbol=symbol,
        start_date=start_date,
        end_date=cutoff,
        provider=prov,
    )

    dataset = assemble_feature_matrix(pipeline_result)
    X_train, y_train, _ = dataset.get_labeled_dataset(drop_incomplete_warmup=True)

    if len(X_train) < 50:
        raise ValueError(
            f"Insufficient labeled training samples for '{symbol}': {len(X_train)} rows available, min 50 required."
        )

    out_p = (
        Path(output_path)
        if output_path
        else Path("models") / (f"xgboost_direction.json" if model_name == "xgboost" else "lightgbm_direction.txt")
    )
    out_p.parent.mkdir(parents=True, exist_ok=True)

    if model_name == "xgboost":
        cfg = XGBoostConfig(n_estimators=50, max_depth=3, learning_rate=0.05, random_state=42)
        model = XGBoostDirectionClassifier(config=cfg)
        model.fit(X_train, y_train)
        model.save_model(out_p)
    elif model_name == "lightgbm":
        cfg_lgb = LightGBMConfig(n_estimators=50, max_depth=3, num_leaves=7, learning_rate=0.05, random_state=42)
        model_lgb = LightGBMDirectionClassifier(config=cfg_lgb)
        model_lgb.fit(X_train, y_train)
        model_lgb.save_model(out_p)
    else:
        raise ValueError(f"Unsupported model_name '{model_name}'. Must be 'xgboost' or 'lightgbm'.")

    logger.info("Successfully trained and persisted %s model to %s", model_name, out_p)
    return out_p
