"""Prediction Engine Service Layer.

Provides the core PredictionService orchestrating market data ingestion,
canonical feature matrix assembly, data quality validation, and trained
model inference without automatic on-the-fly retraining.
"""

from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from app.core.logging_config import sanitize_log_field
from app.core.schemas import MarketOHLCV
from app.market.pipeline import (
    MarketDataPipelineResult,
    run_market_data_pipeline,
)
from app.market.instruments import INSTRUMENT_REGISTRY, is_equity, is_index, resolve_canonical_symbol
from app.market.providers.base import BaseMarketDataProvider
from app.market.providers.nifty_indices_provider import NiftyIndicesProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
    QuoteContext,
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
        repository: Optional[Any] = None,
    ) -> None:
        """Initialize prediction service with data provider, model storage, and optional repository.

        Args:
            provider: Market data provider instance (defaults to YFinanceProvider).
            models_dir: Filesystem directory containing persisted model artifacts.
            model_registry: Optional in-memory mapping of model_name -> fitted classifier.
            repository: Optional PredictionRepository for persisting prediction results.
        """
        self.provider = provider or YFinanceProvider()
        self.models_dir = Path(models_dir) if models_dir else Path("models")
        self.model_registry: Dict[str, Any] = dict(model_registry) if model_registry else {}
        self.repository = repository

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

    def get_instrument_catalog(self) -> List[Dict[str, Any]]:
        """Return canonical instrument catalog with authoritative model availability status.

        Enforces architectural separation:
        - BHARTIARTL has validated production models (XGBoost/LightGBM/Ensemble).
        - Other equities (TCS, RELIANCE) are blocked due to symbol specificity.
        - Sectoral/benchmark indices (NIFTY_TELECOMMUNICATIONS, NIFTY_50) are blocked
          because equity models cannot be cross-applied to indices.
        """
        catalog = []
        from app.prediction.router import model_router

        for symbol, inst in INSTRUMENT_REGISTRY.items():
            canon, cap_status, reason, prereq = model_router.inspect_instrument(symbol)
            if is_index(symbol):
                catalog.append({
                    "symbol": symbol,
                    "name": inst.name,
                    "instrument_type": inst.instrument_type.value,
                    "exchange": inst.exchange,
                    "status": "BLOCKED",
                    "capability_status": cap_status.value,
                    "actionable_prerequisite": prereq,
                    "compatible_models": [],
                    "reason": reason,
                })
            elif symbol == "BHARTIARTL":
                xgb_path = self._get_default_artifact_path("xgboost")
                lgb_path = self._get_default_artifact_path("lightgbm")
                compat = []
                if xgb_path.is_file():
                    compat.append("xgboost")
                if lgb_path.is_file():
                    compat.append("lightgbm")
                if compat:
                    compat.append("ensemble")
                catalog.append({
                    "symbol": symbol,
                    "name": inst.name,
                    "instrument_type": inst.instrument_type.value,
                    "exchange": inst.exchange,
                    "status": "SUPPORTED" if compat else "BLOCKED",
                    "capability_status": cap_status.value if compat else "TEMPORARILY_UNAVAILABLE",
                    "actionable_prerequisite": prereq,
                    "compatible_models": compat,
                    "reason": reason if compat else "Model artifacts not found on disk.",
                })
            else:
                catalog.append({
                    "symbol": symbol,
                    "name": inst.name,
                    "instrument_type": inst.instrument_type.value,
                    "exchange": inst.exchange,
                    "status": "BLOCKED",
                    "capability_status": cap_status.value,
                    "actionable_prerequisite": prereq,
                    "compatible_models": [],
                    "reason": reason,
                })
        return catalog

    def _resolve_model(
        self,
        model_name: str,
        explicit_artifact_path: Optional[Union[str, Path]] = None,
        preloaded_model: Optional[Any] = None,
        symbol: Optional[str] = None,
    ) -> Tuple[Optional[Any], Optional[str]]:
        """Resolve a fitted model from preloaded object, in-memory registry, or disk.

        Enforces strict instrument compatibility gates:
        - Prevents equity models from predicting sectoral or benchmark indices.
        - Prevents equity models fitted for one symbol (e.g. BHARTIARTL) from being
          cross-applied to other symbols (e.g. TCS, RELIANCE) without dedicated training.
        - Fails safely with clear diagnostics when models are missing or incompatible.

        Returns:
            Tuple of (model_instance, error_message).
        """
        canon_sym = resolve_canonical_symbol(symbol) if symbol else None

        # 1. Direct preloaded model argument
        if preloaded_model is not None:
            if not getattr(preloaded_model, "is_fitted", False):
                return None, "Supplied preloaded_model is not fitted."
            if canon_sym:
                model_symbol = getattr(preloaded_model, "symbol", None)
                if is_index(canon_sym):
                    if model_symbol and not is_index(model_symbol):
                        return None, (
                            f"Model was fitted for equity '{model_symbol}' and cannot be reused "
                            f"for sectoral index '{symbol}'."
                        )
                else:
                    if model_symbol and resolve_canonical_symbol(model_symbol) != canon_sym:
                        return None, (
                            f"Model was fitted for equity '{model_symbol}' and cannot be reused "
                            f"for equity '{symbol}'. Equity models are symbol-specific."
                        )
            return preloaded_model, None

        # 2. In-memory model registry
        if canon_sym and is_index(canon_sym):
            idx_keys = [
                f"{canon_sym}_{model_name}",
                f"{canon_sym.lower()}_{model_name}",
                f"{canon_sym}",
            ]
            found_key = next((k for k in idx_keys if k in self.model_registry), None)
            if found_key:
                reg_model = self.model_registry[found_key]
                if not getattr(reg_model, "is_fitted", False):
                    return None, f"Registry model for '{found_key}' is not fitted."
                return reg_model, None
        else:
            if canon_sym:
                sym_keys = [
                    f"{canon_sym}_{model_name}",
                    f"{canon_sym.lower()}_{model_name}",
                    f"{canon_sym}",
                ]
                found_key = next((k for k in sym_keys if k in self.model_registry), None)
                if found_key:
                    reg_model = self.model_registry[found_key]
                    if not getattr(reg_model, "is_fitted", False):
                        return None, f"Registry model for '{found_key}' is not fitted."
                    return reg_model, None

            if model_name in self.model_registry:
                reg_model = self.model_registry[model_name]
                if not getattr(reg_model, "is_fitted", False):
                    return None, f"Registry model for '{model_name}' is not fitted."
                reg_sym = getattr(reg_model, "symbol", None)
                if canon_sym and reg_sym:
                    if resolve_canonical_symbol(reg_sym) != canon_sym:
                        return None, (
                            f"Registry model for '{model_name}' was fitted for '{reg_sym}' and "
                            f"cannot be reused for '{symbol}'. Equity models are symbol-specific."
                        )
                return reg_model, None

        # 3. Persistent filesystem artifact
        if canon_sym and is_index(canon_sym) and not explicit_artifact_path:
            clean_sym = canon_sym.strip().lower()
            idx_artifact = self.models_dir / f"{clean_sym}_{model_name}_direction.json"
            if not idx_artifact.is_file():
                return None, (
                    f"Index-specific forecasting model for '{symbol}' not found at '{idx_artifact}'. "
                    f"BHARTIARTL equity models cannot be reused for sectoral index forecasting. "
                    f"Index-specific model training is documented as a planned follow-up."
                )
            artifact_path = idx_artifact
        elif canon_sym and not is_index(canon_sym) and not explicit_artifact_path:
            if canon_sym == "BHARTIARTL":
                artifact_path = self._get_default_artifact_path(model_name)
            else:
                ext = ".json" if model_name == "xgboost" else ".txt"
                sym_artifact = self.models_dir / f"{canon_sym.lower()}_{model_name}_direction{ext}"
                if not sym_artifact.is_file():
                    return None, (
                        f"No trained model artifact found for equity instrument '{canon_sym}'. "
                        f"Default models are trained specifically for 'BHARTIARTL' and cannot be cross-applied to '{canon_sym}'. "
                        f"Deliberate model training is required prior to inference."
                    )
                artifact_path = sym_artifact
        else:
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

        # Check metadata file if present to prevent cross-symbol artifact application
        if canon_sym:
            meta_path = artifact_path.parent / f"{model_name}_metadata.json"
            if not meta_path.is_file():
                meta_path = artifact_path.parent / "model_metadata.json"
            if meta_path.is_file():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta_data = json.load(f)
                    meta_symbol = meta_data.get("symbol")
                    if not meta_symbol and "models" in meta_data and model_name in meta_data["models"]:
                        meta_symbol = meta_data["models"][model_name].get("symbol")
                    if meta_symbol and resolve_canonical_symbol(meta_symbol) != canon_sym:
                        if is_index(canon_sym):
                            return None, (
                                f"Model artifact at '{artifact_path}' was trained for equity '{meta_symbol}' "
                                f"and cannot be reused for sectoral index '{canon_sym}'."
                            )
                        return None, (
                            f"Model artifact at '{artifact_path}' was trained for '{meta_symbol}' "
                            f"and cannot be reused for '{canon_sym}'. Equity models are symbol-specific."
                        )
                except Exception as meta_exc:
                    logger.debug("Could not verify metadata symbol for '%s': %s", artifact_path, meta_exc)

        try:
            if model_name == "xgboost":
                loaded_model = XGBoostDirectionClassifier.load_model(artifact_path)
            elif model_name == "lightgbm":
                loaded_model = LightGBMDirectionClassifier().load_model(artifact_path)
            else:
                return None, f"Unsupported model architecture '{model_name}'."
            loaded_model.symbol = canon_sym or getattr(loaded_model, "symbol", None) or "BHARTIARTL"
            return loaded_model, None
        except Exception as exc:
            logger.error("Failed to load model artifact '%s': %s", artifact_path, exc)
            return None, f"Failed to deserialize model artifact '{artifact_path}': {exc}"

    def _fetch_quote_context(
        self,
        symbol: str,
        request: PredictionRequest,
    ) -> Optional[QuoteContext]:
        """Acquire verified current price quote context for inference.

        Enforces strict point-in-time isolation: if request.as_of_date is set,
        live quotes are bypassed with a safe NOT_APPLICABLE status to prevent
        look-ahead bias. If live quotes fail or are unsupported, returns safe
        UNAVAILABLE status without fabricating prices.
        """
        if not getattr(request, "include_live_quote", True):
            return None

        clean_symbol = symbol.strip().upper()
        if request.as_of_date is not None:
            return QuoteContext.unavailable(
                symbol=clean_symbol,
                reason="Point-in-time historical inference: live quotes excluded to prevent look-ahead bias.",
                is_historical=True,
            )

        provider = self.provider
        if is_index(clean_symbol) and getattr(self.provider, "name", "") == "yfinance":
            provider = NiftyIndicesProvider()

        try:
            if hasattr(provider, "fetch_quote"):
                live_q = provider.fetch_quote(clean_symbol)
                return QuoteContext.from_live_quote(live_q)
            return QuoteContext.unavailable(
                symbol=clean_symbol,
                reason=f"Provider '{getattr(provider, 'name', type(provider).__name__)}' does not support live quotes.",
                is_historical=False,
            )
        except Exception as exc:
            logger.warning(
                "Live quote acquisition failed for '%s': %s. Safe zero-fabrication fallback applied.",
                sanitize_log_field(clean_symbol),
                exc,
            )
            return QuoteContext.unavailable(
                symbol=clean_symbol,
                reason=f"Live quote retrieval failed: {exc}",
                is_historical=False,
            )

    def predict(
        self,
        request: PredictionRequest,
        preloaded_model: Optional[Any] = None,
        persist: bool = False,
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

        # Index contract guard: Sectoral index forecasting requires an index-specific trained model.
        # Single-stock equity weights (e.g. BHARTIARTL) cannot be reused for index forecasting.
        if is_index(clean_symbol):
            idx_model, idx_model_err = self._resolve_model(
                model_name=request.model_name,
                explicit_artifact_path=request.model_artifact_path,
                preloaded_model=preloaded_model,
                symbol=clean_symbol,
            )
            if idx_model is None:
                quote_context = self._fetch_quote_context(clean_symbol, request)
                return self._build_error_result(
                    symbol=clean_symbol,
                    prediction_timestamp=pred_time_str,
                    status=PredictionStatus.MODEL_UNAVAILABLE,
                    error_message=idx_model_err or f"Model resolution failed for index '{clean_symbol}'.",
                    model_name=request.model_name,
                    quote_context=quote_context,
                )

        quote_context = self._fetch_quote_context(clean_symbol, request)

        ref_time = request.as_of_date or datetime.now(timezone.utc)
        start_date = ref_time - timedelta(days=request.lookback_days)

        # Step 2: Market Data Retrieval
        active_provider = self.provider
        if is_index(clean_symbol) and getattr(self.provider, "name", "") == "yfinance":
            active_provider = NiftyIndicesProvider()

        try:
            pipeline_result = run_market_data_pipeline(
                symbol=clean_symbol,
                start_date=start_date,
                end_date=ref_time,
                provider=active_provider,
            )
        except Exception as exc:
            logger.error("Market data pipeline failed for symbol '%s': %s", sanitize_log_field(clean_symbol), exc)
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.FAILED,
                error_message=f"Market data pipeline error: {exc}",
                model_name=request.model_name,
                quote_context=quote_context,
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
                quote_context=quote_context,
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
                quote_context=quote_context,
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
                quote_context=quote_context,
            )

        # Step 3: Feature Matrix Assembly & Isolation Guard
        try:
            dataset = assemble_feature_matrix(pipeline_result, only_latest=True)
        except Exception as exc:
            logger.error("Feature assembly failed for symbol '%s': %s", sanitize_log_field(clean_symbol), exc)
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.FEATURE_ERROR,
                error_message=f"Feature matrix assembly failed: {exc}",
                model_name=request.model_name,
                quote_context=quote_context,
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
                quote_context=quote_context,
            )

        # Step 4: Model Resolution (Strictly No Automatic Retraining)
        model, model_err = self._resolve_model(
            model_name=request.model_name,
            explicit_artifact_path=request.model_artifact_path,
            preloaded_model=preloaded_model,
            symbol=clean_symbol,
        )

        if model is None:
            return self._build_error_result(
                symbol=clean_symbol,
                prediction_timestamp=pred_time_str,
                status=PredictionStatus.MODEL_UNAVAILABLE,
                error_message=model_err or "Model resolution failed.",
                model_name=request.model_name,
                data_quality=quality,
                quote_context=quote_context,
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
                    quote_context=quote_context,
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
                quote_context=quote_context,
            )

        # Step 7: Build Successful PredictionResult
        cfg = getattr(model, "config", None)
        model_meta = cfg.to_dict() if hasattr(cfg, "to_dict") else {}
        model_version = f"{request.model_name}-direction-v1"

        result = PredictionResult(
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
            quote_context=quote_context,
        )

        if persist and self.repository is not None:
            self.repository.save_prediction(result)

        return result

    def _build_error_result(
        self,
        symbol: str,
        prediction_timestamp: str,
        status: PredictionStatus,
        error_message: str,
        model_name: str,
        data_quality: Optional[PredictionDataQuality] = None,
        quote_context: Optional[QuoteContext] = None,
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
            quote_context=quote_context,
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
