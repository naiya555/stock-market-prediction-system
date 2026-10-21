"""Directional Prediction API Route.

Executes point-in-time quantitative time-series forecasting (XGBoost/LightGBM)
and multi-agent ensemble synthesis (ML + Gemma 3 12B LLM) through canonical service contracts.
"""

from datetime import datetime, timedelta, timezone
import html
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_ensemble_service,
    get_event_providers,
    get_news_provider,
    get_prediction_repository,
    get_prediction_service,
)
from app.events.cleaner import deduplicate_events, filter_events_point_in_time
from app.events.providers.base import BaseEventProvider
from app.news.cleaner import deduplicate_news, filter_news_point_in_time
from app.news.providers.base import BaseNewsProvider
from app.api.schemas import (
    DataQualityResponse,
    EnsembleDetailsResponse,
    LLMExplanationResponse,
    PredictionResponse,
    PredictRequest,
    QuoteContextResponse,
    TargetRangeResponse,
)
from app.llm.schemas import LLMExplanationResult
from app.database.repository import PredictionRepository
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest as DomainPredictionRequest,
    PredictionResult,
    PredictionStatus,
    QuoteContext,
)
from app.prediction.ensemble import (
    EnsemblePredictionResult,
    EnsembleService,
    EnsembleWeights,
)
from app.prediction.service import PredictionService

logger = logging.getLogger(__name__)

router = APIRouter()


def _sanitize_public_quote_error(msg: Optional[str]) -> Optional[str]:
    """Sanitize internal diagnostics in quote error messages to prevent leakage."""
    if not msg:
        return None
    if any(sep in msg for sep in ("\\", "/", "Traceback", "line ", "Exception")):
        return "Quote retrieval failed. Check server logs."
    return msg


def _map_quote_context(qc: Optional[QuoteContext]) -> Optional[QuoteContextResponse]:
    """Map domain QuoteContext to API QuoteContextResponse schema."""
    if not qc:
        return None
    return QuoteContextResponse(
        symbol=qc.symbol,
        last_price=qc.last_price,
        price_timestamp=qc.price_timestamp,
        retrieved_at=qc.retrieved_at,
        source=qc.source,
        session_state=qc.session_state,
        freshness_status=qc.freshness_status,
        is_delayed=qc.is_delayed,
        delay_minutes=qc.delay_minutes,
        price_type=qc.price_type,
        note=qc.note,
        error_message=_sanitize_public_quote_error(qc.error_message),
    )


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


def _sanitize_and_bound_text(val: Any, max_length: int = 2000) -> str:
    """Sanitize untrusted model text, escape HTML entities, and enforce length bound."""
    if val is None:
        return ""
    if not isinstance(val, str):
        val = str(val)
    # Strip non-printable control characters except standard space/tab/newline
    cleaned = "".join(ch for ch in val if ch in ("\n", "\r", "\t") or ch.isprintable())
    # Escape HTML entities so model output cannot execute or inject markup
    escaped = html.escape(cleaned.strip())
    if len(escaped) > max_length:
        escaped = escaped[:max_length] + " [truncated]"
    return escaped


def _sanitize_and_bound_string_list(
    items: Any,
    max_items: int = 25,
    max_item_length: int = 500,
) -> List[str]:
    """Sanitize list of untrusted strings with element-level and collection bounds."""
    if not items:
        return []
    if isinstance(items, (list, tuple, set)):
        raw_list = list(items)[:max_items]
    else:
        raw_list = [items]

    sanitized: List[str] = []
    for elem in raw_list:
        clean_elem = _sanitize_and_bound_text(elem, max_length=max_item_length)
        if clean_elem:
            sanitized.append(clean_elem)
    return sanitized


def _map_llm_explanation(exp: Optional[LLMExplanationResult]) -> Optional[LLMExplanationResponse]:
    """Map domain LLMExplanationResult to API LLMExplanationResponse schema with bounds and HTML escaping."""
    if not exp:
        return None
    raw_status = exp.status.value if hasattr(exp.status, "value") else str(exp.status)
    status_str = _sanitize_and_bound_text(raw_status, max_length=50)

    summary_str = _sanitize_and_bound_text(exp.summary, max_length=2000)
    evidence_list = _sanitize_and_bound_string_list(exp.supporting_evidence, max_items=25, max_item_length=500)
    limitations_list = _sanitize_and_bound_string_list(exp.limitations, max_items=25, max_item_length=500)
    model_str = _sanitize_and_bound_text(exp.model, max_length=100)
    direction_str = _sanitize_and_bound_text(exp.direction, max_length=30) if exp.direction else None
    confidence_str = _sanitize_and_bound_text(exp.confidence, max_length=30) if exp.confidence else None
    disclaimer_str = _sanitize_and_bound_text(exp.disclaimer, max_length=500)

    return LLMExplanationResponse(
        status=status_str,
        summary=summary_str,
        supporting_evidence=evidence_list,
        limitations=limitations_list,
        model=model_str,
        generated_at=exp.generated_at,
        direction=direction_str,
        confidence=confidence_str,
        disclaimer=disclaimer_str,
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
        explanation=_map_llm_explanation(res.explanation),
    )


def _sanitize_public_error_message(msg: Optional[str], model_name: str) -> Optional[str]:
    """Sanitize internal diagnostics to prevent filesystem path and exception leakage."""
    if not msg:
        return None
    logger.warning("Internal prediction diagnostic for '%s': %s", model_name, msg)
    lower = msg.lower()
    if "index-specific forecasting model" in lower or "cannot be reused for sectoral index" in lower:
        return f"Index-specific forecasting model unavailable for '{model_name}'. Equity models cannot be reused for sectoral indices."
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
    news_provider: BaseNewsProvider = Depends(get_news_provider),
    event_providers: List[BaseEventProvider] = Depends(get_event_providers),
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
            include_live_quote=payload.include_live_quote,
        )

        # Establish timezone-aware point-in-time information cutoff
        if payload.as_of_date is not None:
            if payload.as_of_date.tzinfo is None:
                cutoff_time = payload.as_of_date.replace(tzinfo=timezone.utc)
            else:
                cutoff_time = payload.as_of_date
        else:
            cutoff_time = datetime.now(timezone.utc)

        # 1a. Acquire and filter point-in-time news articles
        articles = []
        if news_provider is not None:
            try:
                raw_news = news_provider.fetch_news(
                    symbol=clean_symbol,
                    end_date=cutoff_time,
                    limit=20,
                )
                if raw_news:
                    cleaned_news = deduplicate_news(raw_news)
                    news_window = timedelta(days=min(payload.lookback_days, 14))
                    articles = filter_news_point_in_time(
                        cleaned_news.articles,
                        as_of_time=cutoff_time,
                        lookback_window=news_window,
                    )
            except Exception as exc:
                logger.warning(
                    "News acquisition failed for '%s': %s. Continuing ensemble without news context.",
                    clean_symbol,
                    exc,
                )
                articles = []

        # 1b. Acquire and filter point-in-time macro/regulatory events
        events = []
        if event_providers:
            base_symbol = clean_symbol.rsplit(".", 1)[0]
            raw_events = []
            for ep in event_providers:
                try:
                    evs = ep.fetch_events(end_date=cutoff_time, limit=20)
                    if evs:
                        raw_events.extend(evs)
                except Exception as exc:
                    logger.warning(
                        "Event provider '%s' failed: %s. Continuing with remaining providers.",
                        getattr(ep, "name", type(ep).__name__),
                        exc,
                    )
            if raw_events:
                try:
                    cleaned_evs = deduplicate_events(raw_events)
                    events_window = timedelta(days=min(payload.lookback_days, 30))
                    pit_events = filter_events_point_in_time(
                        cleaned_evs.events,
                        as_of_time=cutoff_time,
                        lookback_window=events_window,
                    )
                    # Filter for relevance: general market events or matching this symbol
                    events = [
                        ev for ev in pit_events
                        if not ev.affected_symbols or base_symbol in ev.affected_symbols
                    ]
                except Exception as exc:
                    logger.warning(
                        "Event cleaning or filtering failed: %s. Continuing ensemble without event context.",
                        exc,
                    )
                    events = []

        try:
            ensemble_res = ensemble_service.predict_ensemble(
                request=domain_req,
                articles=articles,
                events=events,
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
            try:
                canonical_result = ensemble_res.to_prediction_result()
                pred_id = repository.save_prediction(canonical_result)
            except Exception as exc:
                logger.error("Failed to persist ensemble prediction for %s: %s", clean_symbol, exc)

        dq_api = None
        if ensemble_res.ml_prediction and ensemble_res.ml_prediction.data_quality:
            dq_api = _map_data_quality(ensemble_res.ml_prediction.data_quality)

        ens_quote_ctx = ensemble_res.quote_context or (
            ensemble_res.ml_prediction.quote_context if ensemble_res.ml_prediction else None
        )

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
            explanation=_map_llm_explanation(ensemble_res.explanation),
            quote_context=_map_quote_context(ens_quote_ctx),
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
        include_live_quote=payload.include_live_quote,
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
        quote_context=_map_quote_context(ml_res.quote_context),
        error_message=_sanitize_public_error_message(ml_res.error_message, payload.model_name),
        disclaimer=ml_res.disclaimer,
    )
