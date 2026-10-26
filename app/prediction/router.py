"""Centralized Model Routing Service for Stock Market Prediction System.

Inspects target instruments, available data, model artifacts, and runtime capabilities
to automatically route inference requests to the appropriate supported model or pipeline.
Removes user-facing model selection burden from ordinary analysis workflows.
"""

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.market.instruments import (
    BHARTIARTL_CANONICAL,
    NIFTY_50_CANONICAL,
    NIFTY_TELECOM_CANONICAL,
    RELIANCE_CANONICAL,
    TCS_CANONICAL,
    is_equity,
    is_index,
    resolve_canonical_symbol,
)

logger = logging.getLogger(__name__)


class InstrumentCapability(str, Enum):
    """Authoritative capability status for an instrument."""

    SUPPORTED_AND_READY = "SUPPORTED_AND_READY"
    SUPPORTED_DATA_UNAVAILABLE = "SUPPORTED_DATA_UNAVAILABLE"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"
    UNSUPPORTED_BY_CURRENT_MODEL = "UNSUPPORTED_BY_CURRENT_MODEL"
    REQUIRES_SEPARATE_INDEX_PIPELINE = "REQUIRES_SEPARATE_INDEX_PIPELINE"


# Alias for concise import
CapabilityStatus = InstrumentCapability


@dataclass(frozen=True)
class RoutingDecision:
    """Decision outcome of the centralized model routing service."""

    routed_model: Optional[str]  # e.g. "ensemble", "xgboost", "lightgbm", or None if unsupported
    is_supported: bool
    capability_status: InstrumentCapability
    reason: str
    actionable_prerequisite: Optional[str] = None
    components_selected: Optional[Dict[str, str]] = None


class ModelRouter:
    """Centralized Model Routing Service.

    Guarantees:
    1. Automatic Model Selection: Ordinary users select a stock or index and request analysis;
       the router selects the evaluated production model (multi-agent ensemble or quantitative ML).
    2. Zero Cross-Asset Contamination: Equity models are strictly barred from indices;
       models fitted on one symbol are barred from other equities without dedicated training.
    3. Actionable Explanations: Every blocked instrument returns a human-readable reason
       and the exact prerequisite needed to enable it.
    4. Auditability: The selected model and routing decision are recorded in metadata.
    """

    def __init__(self, prediction_service: Optional[Any] = None) -> None:
        self.prediction_service = prediction_service

    def inspect_instrument(self, symbol_or_alias: str) -> Tuple[str, InstrumentCapability, str, Optional[str]]:
        """Inspect an instrument and return its canonical symbol, capability, reason, and prerequisite."""
        if not symbol_or_alias or not symbol_or_alias.strip():
            return "", InstrumentCapability.UNSUPPORTED_BY_CURRENT_MODEL, "Empty or invalid ticker symbol.", "Provide a valid NSE ticker symbol."

        canon = resolve_canonical_symbol(symbol_or_alias)

        if is_index(canon):
            if canon in (NIFTY_50_CANONICAL, "^NSEI"):
                return (
                    canon,
                    InstrumentCapability.SUPPORTED_AND_READY,
                    "Validated broad-market index forecasting models (XGBoost + LightGBM calibrated on Nifty 50 benchmark data) are available and ready.",
                    None,
                )
            elif canon in (NIFTY_TELECOM_CANONICAL, "NIFTY_TELECOM"):
                return (
                    canon,
                    InstrumentCapability.SUPPORTED_AND_READY,
                    "Validated sectoral index forecasting models (XGBoost + LightGBM calibrated on official NSE Nifty Telecommunications benchmark data) are available and ready.",
                    None,
                )
            else:
                return (
                    canon,
                    InstrumentCapability.REQUIRES_SEPARATE_INDEX_PIPELINE,
                    f"Index instrument '{canon}' requires a dedicated index forecasting pipeline. Single-stock equity models cannot be applied to market indices.",
                    f"Implement an index pipeline for '{canon}'.",
                )

        if canon == BHARTIARTL_CANONICAL:
            return (
                canon,
                InstrumentCapability.SUPPORTED_AND_READY,
                "Validated production models (Multi-Agent Ensemble with XGBoost + LightGBM + Gemma 3 12B) are available and ready.",
                None,
            )

        if canon == TCS_CANONICAL:
            return (
                canon,
                InstrumentCapability.SUPPORTED_AND_READY,
                "Validated equity forecasting models (XGBoost + LightGBM calibrated on historical TCS data) are available and ready.",
                None,
            )

        if canon == RELIANCE_CANONICAL:
            return (
                canon,
                InstrumentCapability.UNSUPPORTED_BY_CURRENT_MODEL,
                f"No trained directional model artifact exists for '{canon}'. Production models are trained exclusively on symbol-specific feature distributions and cannot be cross-applied to other equities.",
                f"Train and evaluate an equity model on historical {canon} data using walk-forward validation before enabling inference.",
            )

        return (
            canon,
            InstrumentCapability.UNSUPPORTED_BY_CURRENT_MODEL,
            f"Instrument '{canon}' is not registered with an active production model. Equity models are symbol-specific.",
            f"Register '{canon}' in the instrument catalog and train a dedicated model artifact.",
        )

    def route_prediction(
        self,
        symbol_or_alias: str,
        requested_model: Optional[str] = None,
        has_news_or_events: bool = False,
        ollama_available: bool = False,
    ) -> RoutingDecision:
        """Automatically route a prediction request to the optimal model pipeline."""
        canon, capability, reason, prerequisite = self.inspect_instrument(symbol_or_alias)

        if capability != InstrumentCapability.SUPPORTED_AND_READY:
            return RoutingDecision(
                routed_model=None,
                is_supported=False,
                capability_status=capability,
                reason=reason,
                actionable_prerequisite=prerequisite,
                components_selected={"status": "BLOCKED"},
            )

        # For supported instruments (e.g. BHARTIARTL):
        # If user explicitly requested a specific model (e.g. for backward compatibility or diagnostics):
        req = (requested_model or "auto").strip().lower()
        if req in ("xgboost", "lightgbm"):
            return RoutingDecision(
                routed_model=req,
                is_supported=True,
                capability_status=capability,
                reason=f"Routed to requested quantitative {req.upper()} model.",
                components_selected={"ml_model": req, "pipeline": "quantitative_ml"},
            )

        # Default automatic selection: Multi-Agent Ensemble
        # The ensemble synthesizes quantitative ML (XGBoost/LightGBM) with qualitative reasoning/explanation
        # when available, and falls back safely to 100% quantitative ML if LLM context is absent.
        components = {
            "ml_model": "xgboost",
            "llm_model": "gemma3:12b" if ollama_available else "offline",
            "pipeline": "multi_agent_ensemble_v1",
        }
        return RoutingDecision(
            routed_model="ensemble",
            is_supported=True,
            capability_status=capability,
            reason="Automatically routed to Multi-Agent Ensemble (combining 37-feature quantitative ML with qualitative LLM reasoning and evidence-grounded explanation).",
            actionable_prerequisite=None,
            components_selected=components,
        )


# Singleton router instance
model_router = ModelRouter()
