"""Multi-Agent Ensemble and Synthesis Layer (Phase 12 / Day 32).

Synthesizes quantitative time-series ML forecasts (XGBoost / LightGBM) with qualitative
LLM reasoning (Gemma 3 12B) and financial sentiment features into an integrated,
explainable directional recommendation.

Core Invariants:
1. Independent Output Preservation (ADR 05): Both standalone ML prediction and LLM reasoning
   are preserved in full within the output payload.
2. Anti-Fabrication: Does not claim qualitative LLM reasoning is calibrated statistical probability.
   Blends quantitative probability with qualitative polarity using transparent, audited weights.
3. Agreement & Divergence Analysis: Identifies signal consensus vs. contradiction.
4. Database & Verification Parity: Adapts seamlessly to canonical PredictionResult for
   immutable persistence, outcome verification, and side-by-side performance evaluation.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union

from app.core.logging_config import sanitize_log_field
from app.core.schemas import ValidationError

if TYPE_CHECKING:
    from app.database.repository import PredictionRepository
    from app.prediction.service import PredictionService

from app.llm.client import MockLLMClient
from app.llm.schemas import (
    NON_PREDICTIVE_QUALITATIVE_DISCLAIMER,
    LLMDirection,
    LLMExplanationResult,
    LLMExplanationStatus,
    LLMReasoningResult,
)
from app.llm.service import LLMService
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
    QuoteContext,
)

logger = logging.getLogger(__name__)

ENSEMBLE_DISCLAIMER = (
    "The ensemble prediction synthesizes quantitative time-series classification with "
    "qualitative point-in-time contextual reasoning. Directional forecasts represent the binary "
    "sign of expected next-session return (UP if Close_{t+1} > Close_t else DOWN). "
    "Combined probabilities are uncalibrated weighted blends. Neither component guarantees returns "
    "or constitutes financial advice."
)


class EnsembleAgreement(str, Enum):
    """Categorical alignment status between quantitative ML and qualitative LLM."""

    STRONG_AGREEMENT = "STRONG_AGREEMENT"  # Both agree with high confidence / probability
    AGREEMENT = "AGREEMENT"                # Both predict identical direction
    DIVERGENCE = "DIVERGENCE"              # Opposite directional predictions (conflicting signals)
    PARTIAL = "PARTIAL"                    # One model directional, the other neutral / insufficient evidence
    ML_ONLY = "ML_ONLY"                    # Qualitative LLM unprovided or unavailable
    LLM_ONLY = "LLM_ONLY"                  # Quantitative ML failed or unavailable


@dataclass(frozen=True)
class EnsembleWeights:
    """Configurable weights for combining quantitative ML and qualitative LLM signals.

    Attributes:
        ml_weight: Weight assigned to numerical ML probability (default 0.70).
        llm_weight: Weight assigned to qualitative LLM polarity score (default 0.30).
    """

    ml_weight: float = 0.70
    llm_weight: float = 0.30

    def __post_init__(self) -> None:
        if self.ml_weight < 0.0 or self.llm_weight < 0.0:
            raise ValidationError("Weights must be non-negative.")
        total = self.ml_weight + self.llm_weight
        if total <= 0.0:
            raise ValidationError("Sum of weights must be greater than zero.")
        # Normalize weights to sum exactly to 1.0
        object.__setattr__(self, "ml_weight", round(self.ml_weight / total, 6))
        object.__setattr__(self, "llm_weight", round(self.llm_weight / total, 6))


@dataclass(frozen=True)
class TargetRange:
    """Volatility-anchored expected price range for next session.

    Attributes:
        lower_bound: Estimated lower price boundary in INR.
        upper_bound: Estimated upper price boundary in INR.
        reference_price: Current reference session closing price.
        method: Calculation methodology ('atr_14', 'volatility', or 'unsupported').
    """

    lower_bound: float
    upper_bound: float
    reference_price: float
    method: str = "atr_14"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EnsemblePredictionResult:
    """Canonical representation of synthesized multi-agent prediction output.

    Preserves individual standalone outputs, combined directional probabilities,
    agreement diagnostics, integrated factor rankings, and target ranges.
    """

    symbol: str
    prediction_timestamp: str
    latest_input_timestamp: Optional[str]
    status: PredictionStatus
    combined_direction: Optional[str]
    combined_label: Optional[int]
    combined_probability_up: Optional[float]
    combined_probability_down: Optional[float]
    agreement_status: EnsembleAgreement
    weights_used: Dict[str, float]
    ml_prediction: Optional[PredictionResult]
    llm_reasoning: Optional[LLMReasoningResult]
    sentiment_summary: Optional[Dict[str, Any]] = None
    integrated_positive_factors: Tuple[str, ...] = field(default_factory=tuple)
    integrated_negative_factors: Tuple[str, ...] = field(default_factory=tuple)
    downside_risks: Tuple[str, ...] = field(default_factory=tuple)
    source_references: Tuple[str, ...] = field(default_factory=tuple)
    target_range: Optional[TargetRange] = None
    model_name: str = "ensemble"
    model_version: str = "ensemble_v1"
    disclaimer: str = ENSEMBLE_DISCLAIMER
    error_message: Optional[str] = None
    quote_context: Optional[QuoteContext] = None
    explanation: Optional[LLMExplanationResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert ensemble result to serializable dictionary."""
        return {
            "symbol": self.symbol,
            "prediction_timestamp": self.prediction_timestamp,
            "latest_input_timestamp": self.latest_input_timestamp,
            "status": self.status.value,
            "combined_direction": self.combined_direction,
            "combined_label": self.combined_label,
            "combined_probability_up": self.combined_probability_up,
            "combined_probability_down": self.combined_probability_down,
            "agreement_status": self.agreement_status.value,
            "weights_used": dict(self.weights_used),
            "ml_prediction": self.ml_prediction.to_dict() if self.ml_prediction else None,
            "llm_reasoning": self.llm_reasoning.to_dict() if self.llm_reasoning else None,
            "sentiment_summary": self.sentiment_summary,
            "integrated_positive_factors": list(self.integrated_positive_factors),
            "integrated_negative_factors": list(self.integrated_negative_factors),
            "downside_risks": list(self.downside_risks),
            "source_references": list(self.source_references),
            "target_range": self.target_range.to_dict() if self.target_range else None,
            "quote_context": self.quote_context.to_dict() if self.quote_context else None,
            "explanation": self.explanation.to_dict() if self.explanation else None,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "disclaimer": self.disclaimer,
            "error_message": self.error_message,
        }

    def to_prediction_result(self) -> PredictionResult:
        """Adapt ensemble result to canonical PredictionResult for SQLite persistence and verification."""
        # Derive data quality from underlying ML prediction if available
        if self.ml_prediction and self.ml_prediction.data_quality:
            quality = self.ml_prediction.data_quality
        else:
            quality = PredictionDataQuality(
                total_bars_fetched=0,
                cleaned_bars=0,
                warmup_bars_required=34,
                warmup_complete=False,
                latest_bar_timestamp=self.latest_input_timestamp,
                missing_feature_count=0,
                missing_features=[],
                is_stale=False,
                stale_days=None,
            )

        metadata = {
            "weights_used": self.weights_used,
            "agreement_status": self.agreement_status.value,
            "ml_model_name": self.ml_prediction.model_name if self.ml_prediction else None,
            "ml_model_version": self.ml_prediction.model_version if self.ml_prediction else None,
            "llm_model_version": self.llm_reasoning.model_version if self.llm_reasoning else None,
            "has_llm_reasoning": self.llm_reasoning is not None,
            "has_sentiment": self.sentiment_summary is not None,
            "integrated_factors_count": len(self.integrated_positive_factors) + len(self.integrated_negative_factors),
            "explanation_status": self.explanation.status.value if self.explanation else None,
        }

        # Expected movement can be derived from target range if calculated
        expected_move: Optional[float] = None
        expected_status: str = "UNSUPPORTED"
        if self.target_range and self.target_range.reference_price > 0:
            if self.combined_direction == "UP":
                expected_move = round(self.target_range.upper_bound - self.target_range.reference_price, 2)
                expected_status = f"RANGE_HIGH_{self.target_range.method.upper()}"
            elif self.combined_direction == "DOWN":
                expected_move = round(self.target_range.lower_bound - self.target_range.reference_price, 2)
                expected_status = f"RANGE_LOW_{self.target_range.method.upper()}"

        return PredictionResult(
            symbol=self.symbol,
            prediction_timestamp=self.prediction_timestamp,
            latest_input_timestamp=self.latest_input_timestamp,
            status=self.status,
            predicted_direction=self.combined_direction,
            predicted_label=self.combined_label,
            probability_up=self.combined_probability_up,
            probability_down=self.combined_probability_down,
            model_name=self.model_name,
            model_version=self.model_version,
            model_metadata=metadata,
            data_quality=quality,
            is_probability_calibrated=False,
            probability_calibration="uncalibrated_weighted_ensemble",
            expected_movement=expected_move,
            expected_movement_status=expected_status,
            error_message=self.error_message,
            quote_context=self.quote_context or (self.ml_prediction.quote_context if self.ml_prediction else None),
            disclaimer=self.disclaimer,
        )

    def format_summary(self) -> str:
        """Render a readable text audit summary of the ensemble forecast."""
        lines = [
            f"=== Multi-Agent Ensemble Prediction for {self.symbol} ===",
            f"  Status:               {self.status.value}",
            f"  Timestamp:            {self.prediction_timestamp}",
            f"  Latest Input Bar:     {self.latest_input_timestamp or 'N/A'}",
            f"  Agreement Status:     {self.agreement_status.value}",
            f"  Weights:              ML={self.weights_used.get('ml', 0):.0%}, LLM={self.weights_used.get('llm', 0):.0%}",
        ]
        if self.quote_context:
            if self.quote_context.last_price is not None:
                lines.append(
                    f"  Last Quoted Price:    ₹ {self.quote_context.last_price:,.2f} "
                    f"({self.quote_context.freshness_status}, session={self.quote_context.session_state}, "
                    f"delayed={self.quote_context.is_delayed}) [OBSERVED, not predicted]"
                )
            else:
                lines.append(
                    f"  Quote Context:         {self.quote_context.freshness_status} "
                    f"({self.quote_context.error_message or self.quote_context.note})"
                )
        if self.status == PredictionStatus.SUCCESS:
            p_up = f"{self.combined_probability_up * 100:.2f}%" if self.combined_probability_up is not None else "N/A"
            p_dn = f"{self.combined_probability_down * 100:.2f}%" if self.combined_probability_down is not None else "N/A"
            lines.extend([
                f"  Combined Direction:   {self.combined_direction} (label={self.combined_label})",
                f"  Combined Probs:       P(UP)={p_up}, P(DOWN)={p_dn}",
            ])
            if self.target_range:
                lines.append(
                    f"  Target Range (1d):    [{self.target_range.lower_bound:.2f} - {self.target_range.upper_bound:.2f}] "
                    f"(Ref: {self.target_range.reference_price:.2f}, {self.target_range.method})"
                )

        if self.ml_prediction:
            ml_dir = self.ml_prediction.predicted_direction or "FAILED"
            ml_prob = f"{self.ml_prediction.probability_up * 100:.1f}%" if self.ml_prediction.probability_up is not None else "N/A"
            lines.append(f"  Quantitative ML:      {self.ml_prediction.model_name} -> {ml_dir} (P(UP)={ml_prob})")

        if self.llm_reasoning:
            lines.append(
                f"  Qualitative LLM:      {self.llm_reasoning.model_version} -> {self.llm_reasoning.direction.value} "
                f"(Confidence: {self.llm_reasoning.confidence_assessment})"
            )
            if self.llm_reasoning.reasoning_summary:
                lines.append(f"    Summary: {self.llm_reasoning.reasoning_summary}")

        if self.downside_risks:
            lines.append(f"  Downside Risks ({len(self.downside_risks)}):")
            for r in self.downside_risks[:3]:
                lines.append(f"    - {r}")

        if self.error_message:
            lines.append(f"  Error Message:        {self.error_message}")

        return "\n".join(lines)


# ==============================================================================
# Ensemble Service Implementation
# ==============================================================================

class EnsembleService:
    """Service layer synthesizing quantitative ML forecasts with qualitative LLM reasoning."""

    def __init__(
        self,
        prediction_service: Optional[Any] = None,
        llm_service: Optional[LLMService] = None,
        repository: Optional[Any] = None,
        default_weights: Optional[EnsembleWeights] = None,
    ) -> None:
        """Initialize ensemble service with sub-services and configuration."""
        if prediction_service is not None:
            self.prediction_service = prediction_service
        else:
            from app.prediction.service import PredictionService
            self.prediction_service = PredictionService()
        self.llm_service = llm_service or LLMService()
        self.repository = repository
        self.weights = default_weights or EnsembleWeights()

    @staticmethod
    def _map_llm_direction_to_polarity(direction: LLMDirection, confidence: str) -> float:
        """Map categorical LLM direction and qualitative confidence to a bounded polarity score in [-1.0, 1.0].

        Confidence scale:
        - HIGH: 1.0
        - MEDIUM: 0.75
        - LOW: 0.50
        """
        conf_clean = confidence.strip().upper()
        if conf_clean == "HIGH":
            multiplier = 1.0
        elif conf_clean == "MEDIUM":
            multiplier = 0.75
        else:
            multiplier = 0.50

        if direction == LLMDirection.UP:
            return 1.0 * multiplier
        elif direction == LLMDirection.DOWN:
            return -1.0 * multiplier
        elif direction in (LLMDirection.NEUTRAL, LLMDirection.INSUFFICIENT_EVIDENCE):
            return 0.0
        return 0.0

    @classmethod
    def _evaluate_agreement(
        cls,
        ml_result: PredictionResult,
        llm_result: Optional[LLMReasoningResult],
    ) -> EnsembleAgreement:
        """Determine categorical agreement/divergence between ML and LLM predictions."""
        if not llm_result:
            return EnsembleAgreement.ML_ONLY

        if ml_result.status != PredictionStatus.SUCCESS or not ml_result.predicted_direction:
            return EnsembleAgreement.LLM_ONLY

        ml_dir = ml_result.predicted_direction.upper()
        llm_dir = llm_result.direction

        # Handle neutral or insufficient evidence
        if llm_dir in (LLMDirection.NEUTRAL, LLMDirection.INSUFFICIENT_EVIDENCE):
            return EnsembleAgreement.PARTIAL

        # Direct comparison
        if ml_dir == "UP" and llm_dir == LLMDirection.UP:
            p_up = ml_result.probability_up or 0.5
            conf = llm_result.confidence_assessment.upper()
            if p_up >= 0.60 and conf in ("HIGH", "MEDIUM"):
                return EnsembleAgreement.STRONG_AGREEMENT
            return EnsembleAgreement.AGREEMENT

        if ml_dir == "DOWN" and llm_dir == LLMDirection.DOWN:
            p_dn = ml_result.probability_down or 0.5
            conf = llm_result.confidence_assessment.upper()
            if p_dn >= 0.60 and conf in ("HIGH", "MEDIUM"):
                return EnsembleAgreement.STRONG_AGREEMENT
            return EnsembleAgreement.AGREEMENT

        # Opposite directions
        return EnsembleAgreement.DIVERGENCE

    def synthesize(
        self,
        ml_result: PredictionResult,
        llm_result: Optional[LLMReasoningResult] = None,
        sentiment_summary: Optional[Dict[str, Any]] = None,
        current_price: Optional[float] = None,
        atr_value: Optional[float] = None,
        weights: Optional[EnsembleWeights] = None,
        quote_context: Optional[QuoteContext] = None,
        explanation: Optional[LLMExplanationResult] = None,
    ) -> EnsemblePredictionResult:
        """Synthesize pre-computed ML prediction and qualitative LLM reasoning.

        Pure deterministic operation: does not trigger network calls or model inference.

        Args:
            ml_result: Standalone quantitative PredictionResult.
            llm_result: Optional standalone qualitative LLMReasoningResult.
            sentiment_summary: Optional FinBERT sentiment context metadata.
            current_price: Optional closing price of latest input bar in INR.
            atr_value: Optional 14-period Average True Range value in INR.
            weights: Optional custom weights overriding default.
            quote_context: Optional verified current market quote context.
            explanation: Optional evidence-grounded LLMExplanationResult.

        Returns:
            Validated EnsemblePredictionResult.
        """
        active_weights = weights or self.weights
        now_iso = datetime.now(timezone.utc).isoformat()
        symbol = ml_result.symbol
        resolved_quote = quote_context or getattr(ml_result, "quote_context", None)

        # Anchor current_price to verified quote if not explicitly supplied
        if current_price is None and resolved_quote and resolved_quote.last_price is not None:
            current_price = resolved_quote.last_price

        # If quantitative ML prediction failed, ensemble cannot synthesize probabilities
        if ml_result.status != PredictionStatus.SUCCESS:
            return EnsemblePredictionResult(
                symbol=symbol,
                prediction_timestamp=now_iso,
                latest_input_timestamp=ml_result.latest_input_timestamp,
                status=ml_result.status,
                combined_direction=None,
                combined_label=None,
                combined_probability_up=None,
                combined_probability_down=None,
                agreement_status=EnsembleAgreement.LLM_ONLY if llm_result else EnsembleAgreement.ML_ONLY,
                weights_used={"ml": active_weights.ml_weight, "llm": active_weights.llm_weight},
                ml_prediction=ml_result,
                llm_reasoning=llm_result,
                sentiment_summary=sentiment_summary,
                quote_context=resolved_quote,
                explanation=explanation,
                error_message=f"ML prediction failed: {ml_result.error_message}",
            )

        # Baseline ML probabilities
        p_ml_up = float(ml_result.probability_up if ml_result.probability_up is not None else 0.5)

        # Calculate LLM directional component
        if llm_result:
            polarity = self._map_llm_direction_to_polarity(
                llm_result.direction,
                llm_result.confidence_assessment,
            )
            # Implied LLM probability: polarity 0.0 -> 0.50, +1.0 -> 1.0, -1.0 -> 0.0
            p_llm_up = 0.50 + (0.50 * polarity)
            w_ml = active_weights.ml_weight
            w_llm = active_weights.llm_weight
        else:
            # Fallback to ML only when LLM is omitted or unavailable
            polarity = 0.0
            p_llm_up = 0.50
            w_ml = 1.0
            w_llm = 0.0

        # Weighted combination
        p_comb_up = (w_ml * p_ml_up) + (w_llm * p_llm_up)
        p_comb_up = max(0.0001, min(0.9999, round(p_comb_up, 4)))
        p_comb_dn = round(1.0 - p_comb_up, 4)

        # Combined directional decision
        if p_comb_up > 0.50:
            combined_dir = "UP"
            combined_lbl = 1
        elif p_comb_up < 0.50:
            combined_dir = "DOWN"
            combined_lbl = 0
        else:
            # Tie breaker: default to quantitative ML prediction direction
            combined_dir = ml_result.predicted_direction or "UP"
            combined_lbl = 1 if combined_dir == "UP" else 0

        # Assess agreement
        agreement = self._evaluate_agreement(ml_result, llm_result)

        # Target range calculation
        target_range: Optional[TargetRange] = None
        if current_price is not None and current_price > 0:
            if atr_value is not None and atr_value > 0:
                lower = max(0.01, round(current_price - atr_value, 2))
                upper = round(current_price + atr_value, 2)
                target_range = TargetRange(
                    lower_bound=lower,
                    upper_bound=upper,
                    reference_price=current_price,
                    method="atr_14",
                )
            else:
                target_range = TargetRange(
                    lower_bound=current_price,
                    upper_bound=current_price,
                    reference_price=current_price,
                    method="unsupported",
                )

        # Integrated factor rankings
        pos_factors: List[str] = []
        neg_factors: List[str] = []
        downside: List[str] = []
        sources: List[str] = []

        if llm_result:
            pos_factors.extend(llm_result.positive_factors)
            neg_factors.extend(llm_result.negative_factors)
            downside.extend(llm_result.downside_risks)
            sources.extend(llm_result.source_references)

        # Include quantitative technical factors
        if ml_result.predicted_direction == "UP":
            pos_factors.append(f"Quantitative {ml_result.model_name} signal indicates positive momentum (P={p_ml_up:.1%})")
        else:
            neg_factors.append(f"Quantitative {ml_result.model_name} signal indicates downward trend (P={ml_result.probability_down or (1-p_ml_up):.1%})")

        return EnsemblePredictionResult(
            symbol=symbol,
            prediction_timestamp=now_iso,
            latest_input_timestamp=ml_result.latest_input_timestamp,
            status=PredictionStatus.SUCCESS,
            combined_direction=combined_dir,
            combined_label=combined_lbl,
            combined_probability_up=p_comb_up,
            combined_probability_down=p_comb_dn,
            agreement_status=agreement,
            weights_used={"ml": w_ml, "llm": w_llm},
            ml_prediction=ml_result,
            llm_reasoning=llm_result,
            sentiment_summary=sentiment_summary,
            integrated_positive_factors=tuple(dict.fromkeys(pos_factors)),
            integrated_negative_factors=tuple(dict.fromkeys(neg_factors)),
            downside_risks=tuple(dict.fromkeys(downside)),
            source_references=tuple(dict.fromkeys(sources)),
            target_range=target_range,
            quote_context=resolved_quote,
            explanation=explanation,
            model_name="ensemble",
            model_version="ensemble_v1",
        )

    def predict_ensemble(
        self,
        request: PredictionRequest,
        articles: Optional[Sequence[Any]] = None,
        events: Optional[Sequence[Any]] = None,
        preloaded_ml_model: Optional[Any] = None,
        current_price: Optional[float] = None,
        atr_value: Optional[float] = None,
        weights: Optional[EnsembleWeights] = None,
        persist: bool = True,
    ) -> EnsemblePredictionResult:
        """Execute full multi-agent ensemble prediction pipeline.

        1. Calls PredictionService for quantitative ML inference.
        2. Calls LLMService for qualitative LLM reasoning and explanation if context is supplied.
        3. Synthesizes outputs into EnsemblePredictionResult.
        4. Optionally persists to SQLite via PredictionRepository.

        Args:
            request: Directional prediction request specification.
            articles: Optional point-in-time filtered news articles.
            events: Optional point-in-time filtered macro/regulatory events.
            preloaded_ml_model: Optional pre-fitted ML model instance.
            current_price: Optional current stock price for target range.
            atr_value: Optional 14-day ATR for target range bounds.
            weights: Optional custom weighting configuration.
            persist: Whether to save the resulting prediction to the database.

        Returns:
            EnsemblePredictionResult.
        """
        # Step 1: Run Quantitative ML Inference
        clean_sym = sanitize_log_field(request.symbol)
        logger.info("Executing quantitative ML prediction for '%s' (%s)", clean_sym, request.model_name)
        ml_result = self.prediction_service.predict(
            request=request,
            preloaded_model=preloaded_ml_model,
        )

        # Step 2: Run Qualitative LLM Reasoning / Evidence-Grounded Explanation
        llm_result: Optional[LLMReasoningResult] = None
        explanation: Optional[LLMExplanationResult] = None

        if not articles and not events:
            explanation = LLMExplanationResult.no_context(
                symbol=request.symbol,
                model=getattr(self.llm_service.client, "model_name", "gemma3:12b") if hasattr(self.llm_service, "client") else "gemma3:12b",
            )
        else:
            try:
                logger.info("Executing qualitative LLM reasoning for '%s'", clean_sym)
                if hasattr(self.llm_service, "explain_prediction"):
                    explanation = self.llm_service.explain_prediction(
                        symbol=request.symbol,
                        articles=articles or [],
                        events=events or [],
                        cutoff_time=request.as_of_date,
                        quantitative_direction=ml_result.predicted_direction,
                        quantitative_probability=ml_result.probability_up,
                    )
                    if explanation.status == LLMExplanationStatus.SUCCESS:
                        llm_result = explanation.to_reasoning_result()
                else:
                    llm_result = self.llm_service.generate_qualitative_reasoning(
                        symbol=request.symbol,
                        articles=articles or [],
                        events=events or [],
                    )
                    if llm_result:
                        explanation = llm_result.to_explanation()
            except Exception as exc:
                logger.warning(
                    "Qualitative LLM reasoning failed for '%s': %s. Proceeding with ML-only fallback.",
                    clean_sym,
                    exc,
                )
                explanation = LLMExplanationResult.failed(
                    symbol=request.symbol,
                    model=getattr(self.llm_service.client, "model_name", "gemma3:12b") if hasattr(self.llm_service, "client") else "gemma3:12b",
                    error_message=str(exc),
                )
                llm_result = None

        # Step 3: Synthesize Results
        ensemble_result = self.synthesize(
            ml_result=ml_result,
            llm_result=llm_result,
            current_price=current_price,
            atr_value=atr_value,
            weights=weights,
            quote_context=ml_result.quote_context,
            explanation=explanation,
        )

        # Step 4: Optional Persistence
        if persist and self.repository:
            try:
                adapted_result = ensemble_result.to_prediction_result()
                pred_id = self.repository.save_prediction(adapted_result)
                logger.info("Persisted ensemble prediction for '%s' with id: %s", request.symbol, pred_id)
            except Exception as exc:
                logger.error("Failed to persist ensemble prediction for '%s': %s", request.symbol, exc)

        return ensemble_result
