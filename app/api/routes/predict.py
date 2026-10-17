"""Directional Prediction API Route.

Executes point-in-time quantitative time-series forecasting (XGBoost/LightGBM)
and multi-agent ensemble synthesis (ML + Gemma 3 12B LLM) through canonical service contracts.
"""

from datetime import datetime, timezone
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_ensemble_service,
    get_prediction_repository,
    get_prediction_service,
)
from app.api.schemas import (
    DataQualityResponse,
    EnsembleDetailsResponse,
    PredictionResponse,
    PredictRequest,
    TargetRangeResponse,
)
from app.database.repository import PredictionRepository
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest as DomainPredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.ensemble import (
    EnsemblePredictionResult,
    EnsembleService,
    EnsembleWeights,
)
from app.prediction.service import PredictionService

logger = logging.getLogger(__name__)

router = APIRouter()


def _map_data_quality(dq: Optional[PredictionDataQuality]) -> Optional[DataQualityResponse]:
    """Map domain PredictionDataQuality to API DataQualityResponse schema."""
    if not dq:
        return None
    return DataQualityResponse(
        total_bars_fetched=dq.total_bars_fetched,
        cleaned_bars=dq.cleaned_bars,
        warmup_bars_required=dq.warmup_bars_required,
        warmup_complete=dq.warmup_complete,
        latest_bar_timestamp=dq.latest_bar_timestamp,
        missing_feature_count=dq.missing_feature_count,
        is_stale=dq.is_stale,
        stale_days=dq.stale_days,
    )


def _map_ensemble_details(res: EnsemblePredictionResult) -> EnsembleDetailsResponse:
    """Map EnsemblePredictionResult to API EnsembleDetailsResponse schema."""
    tr = None
    if res.target_range:
        tr = TargetRangeResponse(
            lower_bound=res.target_range.lower_bound,
            upper_bound=res.target_range.upper_bound,
            reference_price=res.target_range.reference_price,
            method=res.target_range.method,
        )

    llm_summary = None
    llm_conf = None
    llm_dir = None
    if res.llm_reasoning:
        llm_summary = res.llm_reasoning.reasoning_summary
        llm_conf = res.llm_reasoning.confidence_assessment
        llm_dir = (
            res.llm_reasoning.direction.value
            if hasattr(res.llm_reasoning.direction, "value")
            else str(res.llm_reasoning.direction)
        )

    return EnsembleDetailsResponse(
        agreement_status=res.agreement_status.value,
        combined_probability_up=res.combined_probability_up,
        combined_probability_down=res.combined_probability_down,
        weights_used=res.weights_used,
        integrated_positive_factors=list(res.integrated_positive_factors),
        integrated_negative_factors=list(res.integrated_negative_factors),
        downside_risks=list(res.downside_risks),
        source_references=list(res.source_references),
        target_range=tr,
        llm_direction=llm_dir,
        llm_reasoning_summary=llm_summary,
        llm_confidence=llm_conf,
    )


def _sanitize_public_error_message(msg: Optional[str], model_name: str) -> Optional[str]:
    """Sanitize internal diagnostics to prevent filesystem path and exception leakage."""
    if not msg:
        return None
    logger.warning("Internal prediction diagnostic for '%s': %s", model_name, msg)
    lower = msg.lower()
    if "artifact not found" in lower or "not found at" in lower:
        return f"Model artifact unavailable for '{model_name}'. Model must be trained and persisted prior to inference."
    if "failed to deserialize" in lower or "failed to load" in lower:
        return f"Model artifact could not be deserialized for '{model_name}'."
    if "unsupported model" in lower:
        return f"Unsupported model architecture '{model_name}'."
    if "feature matrix assembly failed" in lower:
        return f"Feature matrix assembly failed for '{model_name}'."
    if any(sep in msg for sep in ("\\", "/", "Traceback", "line ")):
        return f"Prediction computation failed for '{model_name}'. Check server logs."
    return msg


@router.post(
    "",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Next-Session Directional Stock Prediction",
    description=(
        "Executes point-in-time directional inference using either pure quantitative ML "
        "(XGBoost, LightGBM) or synthesized Multi-Agent Ensemble (ML + Gemma 3 12B). "
        "Preserves immutable audit trail and calibrated probability blending."
    ),
)
def predict(
    payload: PredictRequest,
    prediction_service: PredictionService = Depends(get_prediction_service),
    ensemble_service: EnsembleService = Depends(get_ensemble_service),
    repository: PredictionRepository = Depends(get_prediction_repository),
) -> PredictionResponse:
    """Validate request, run inference through existing services, and return structured response."""
    clean_symbol = payload.symbol.strip().upper()
    if not clean_symbol:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Stock symbol cannot be empty or whitespace.",
        )

    # 1. Handle Multi-Agent Ensemble Synthesis
    if payload.model_name == "ensemble":
        custom_weights = None
        if payload.ml_weight is not None and payload.llm_weight is not None:
            custom_weights = EnsembleWeights(
                ml_weight=payload.ml_weight,
                llm_weight=payload.llm_weight,
            )

        domain_req = DomainPredictionRequest(
            symbol=clean_symbol,
            model_name="xgboost",  # Base ML engine for ensemble
            as_of_date=payload.as_of_date,
            lookback_days=payload.lookback_days,
            max_stale_days=payload.max_stale_days,
            allow_stale_data=payload.allow_stale_data,
        )

        try:
            ensemble_res = ensemble_service.predict_ensemble(
                request=domain_req,
                weights=custom_weights,
                persist=payload.persist,
            )
        except Exception as exc:
            logger.error("Ensemble prediction service error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ensemble prediction service encountered an unexpected error.",
            )

        # Retrieve prediction ID if persisted
        pred_id = None
        if payload.persist and ensemble_res.status == PredictionStatus.SUCCESS:
            canonical_result = ensemble_res.to_prediction_result()
            pred_id = repository.save_prediction(canonical_result)

        dq_api = None
        if ensemble_res.ml_prediction and ensemble_res.ml_prediction.data_quality:
            dq_api = _map_data_quality(ensemble_res.ml_prediction.data_quality)

        return PredictionResponse(
            prediction_id=pred_id,
            symbol=ensemble_res.symbol,
            prediction_timestamp=ensemble_res.prediction_timestamp,
            latest_input_timestamp=ensemble_res.latest_input_timestamp,
            status=ensemble_res.status.value,
            predicted_direction=ensemble_res.combined_direction,
            predicted_label=ensemble_res.combined_label,
            probability_up=ensemble_res.combined_probability_up,
            probability_down=ensemble_res.combined_probability_down,
            model_name="ensemble",
            model_version=ensemble_res.model_version,
            is_probability_calibrated=False,
            probability_calibration="uncalibrated",
            data_quality=dq_api,
            ensemble=_map_ensemble_details(ensemble_res),
            error_message=_sanitize_public_error_message(ensemble_res.error_message, "ensemble"),
            disclaimer=ensemble_res.disclaimer,
        )

    # 2. Handle Standalone Quantitative ML Prediction (XGBoost / LightGBM)
    domain_req = DomainPredictionRequest(
        symbol=clean_symbol,
        model_name=payload.model_name,
        as_of_date=payload.as_of_date,
        lookback_days=payload.lookback_days,
        max_stale_days=payload.max_stale_days,
        allow_stale_data=payload.allow_stale_data,
    )

    try:
        ml_res = prediction_service.predict(domain_req)
    except Exception as exc:
        logger.error("Prediction service failure for %s: %s", clean_symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction service encountered an unexpected error.",
        )

    pred_id = None
    if payload.persist and ml_res.status == PredictionStatus.SUCCESS:
        try:
            pred_id = repository.save_prediction(ml_res)
        except Exception as exc:
            logger.error("Failed to persist prediction for %s: %s", clean_symbol, exc)

    return PredictionResponse(
        prediction_id=pred_id,
        symbol=ml_res.symbol,
        prediction_timestamp=ml_res.prediction_timestamp,
        latest_input_timestamp=ml_res.latest_input_timestamp,
        status=ml_res.status.value,
        predicted_direction=ml_res.predicted_direction,
        predicted_label=ml_res.predicted_label,
        probability_up=ml_res.probability_up,
        probability_down=ml_res.probability_down,
        model_name=ml_res.model_name,
        model_version=ml_res.model_version,
        is_probability_calibrated=ml_res.is_probability_calibrated,
        probability_calibration=ml_res.probability_calibration,
        data_quality=_map_data_quality(ml_res.data_quality),
        ensemble=None,
        error_message=_sanitize_public_error_message(ml_res.error_message, payload.model_name),
        disclaimer=ml_res.disclaimer,
    )
