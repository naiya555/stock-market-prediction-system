"""Interactive Market Analysis Chat Assistant Route.

Provides real-time conversational assistance grounded in verified platform facts,
prediction evidence, macroeconomic indicators, and market terminology.
Uses local Ollama Gemma 3 12B with deterministic fallback when offline.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_event_providers, get_prediction_service
from app.api.schemas import ChatMessage, ChatRequest, ChatResponse
from app.llm.client import OllamaLLMClient
from app.prediction.router import model_router
from app.prediction.service import PredictionService

logger = logging.getLogger(__name__)

router = APIRouter()

# Terminology knowledge base for educational queries
FINANCIAL_TERMS = {
    "repo rate": "The Repo Rate (Repurchasing Option rate) is the benchmark interest rate at which the Reserve Bank of India (RBI) lends short-term money to commercial banks against government securities. An increase in repo rate generally increases borrowing costs across the economy to curb inflation, which typically dampens stock market valuations.",
    "inflation": "Inflation measures the rate at which the general level of prices for goods and services rises, eroding purchasing power. In India, headline inflation is tracked via the Consumer Price Index (CPI), and the RBI targets a 4% (+/- 2%) band.",
    "gdp": "Gross Domestic Product (GDP) represents the total monetary or market value of all finished goods and services produced within a country during a specific period, serving as a comprehensive scorecard of economic health.",
    "sebi": "The Securities and Exchange Board of India (SEBI) is the statutory regulatory body governing India's securities and commodities markets, ensuring market transparency, investor protection, and orderly trading.",
    "trai": "The Telecom Regulatory Authority of India (TRAI) regulates telecommunications services and tariffs, conducts spectrum pricing reviews, and ensures fair competition in the telecom sector (crucial for stocks like BHARTIARTL).",
    "rsi": "Relative Strength Index (RSI) is a momentum oscillator measuring the speed and magnitude of recent price changes (0 to 100) to evaluate overbought (>70) or oversold (<30) conditions.",
    "macd": "Moving Average Convergence Divergence (MACD) is a trend-following momentum indicator showing the relationship between two exponential moving averages (typically 12-day and 26-day EMA).",
    "atr": "Average True Range (ATR) measures market volatility by decomposing the entire range of an asset price for a given period (typically 14 sessions). Our system uses 1-session ATR-14 to anchor volatility-based price range bands.",
    "brier score": "Brier score measures the accuracy of probabilistic predictions (mean squared difference between predicted probability and actual binary outcome). Scores range from 0.0 (perfect) to 1.0; a score under 0.25 beats random guessing.",
}


def _match_terminology(message: str) -> Optional[str]:
    """Check if the user prompt asks for a recognized financial definition."""
    lowered = message.lower()
    for term, definition in FINANCIAL_TERMS.items():
        if term in lowered and any(q in lowered for q in ("what is", "define", "explain", "meaning", "tell me about")):
            return f"**{term.upper()}**: {definition}"
    return None


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with Market Prediction Assistant",
    description="Conversational assistant answering market questions, explaining predictions, and detailing instrument capabilities using local LLM reasoning or grounded facts.",
)
def chat_assistant(
    payload: ChatRequest,
    prediction_service: PredictionService = Depends(get_prediction_service),
    event_providers: List[Any] = Depends(get_event_providers),
) -> ChatResponse:
    """Process user message, augment with authoritative context, and generate grounded response."""
    user_msg = payload.message.strip()
    if not user_msg:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Chat message cannot be empty or whitespace.",
        )

    sources: List[str] = []
    limitations: List[str] = [
        "Educational and decision-support research only; not financial or investment advice.",
        "Directional forecasts reflect probabilistic next-session sign, not guaranteed outcomes.",
    ]
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Check instrument capability inquiry
    target_symbol = (payload.symbol or "").strip()
    lowered_msg = user_msg.lower()

    # Detect symbol mentions in the message if not explicitly provided
    if not target_symbol:
        for sym_cand in ("BHARTIARTL", "TCS", "RELIANCE", "NIFTY 50", "NIFTY_TELECOMMUNICATIONS"):
            if sym_cand.lower() in lowered_msg:
                target_symbol = sym_cand
                break

    instrument_context_str = ""
    if target_symbol:
        canon, cap_status, reason, prereq = model_router.inspect_instrument(target_symbol)
        instrument_context_str = (
            f"Target Instrument: {canon}\n"
            f"Capability Status: {cap_status.value}\n"
            f"Reason: {reason}\n"
            f"Actionable Prerequisite: {prereq or 'None (Ready for inference)'}\n"
        )
        sources.append(f"Platform Instrument Registry ({canon})")

    # 2. Check prediction context
    pred_context_str = ""
    if payload.prediction_context and isinstance(payload.prediction_context, dict):
        pc = payload.prediction_context
        pred_context_str = (
            f"Active Forecast for {pc.get('symbol', 'Unknown')}:\n"
            f"- Direction: {pc.get('predicted_direction', 'N/A')}\n"
            f"- Estimated P(UP): {pc.get('probability_up', 'N/A')}, P(DOWN): {pc.get('probability_down', 'N/A')}\n"
            f"- Model: {pc.get('model_name', 'N/A')} ({pc.get('model_version', 'N/A')})\n"
            f"- Input Timestamp: {pc.get('latest_input_timestamp', 'N/A')}\n"
            f"- Agreement Status: {pc.get('ensemble', {}).get('agreement_status', 'N/A') if isinstance(pc.get('ensemble'), dict) else 'N/A'}\n"
        )
        sources.append("Active Prediction Output")

    # 3. Check quick rule-based responses for common inquiries
    term_def = _match_terminology(user_msg)
    if term_def:
        sources.append("Market Terminology Knowledge Base")
        return ChatResponse(
            reply=term_def,
            model="knowledge_base_rule",
            sources=sources,
            limitations=limitations,
            timestamp=now_iso,
        )

    # 4. Check if user is asking why a symbol is blocked
    if any(q in lowered_msg for q in ("why is", "why blocked", "how to enable", "prerequisite", "support")):
        if target_symbol and canon != "BHARTIARTL":
            reply_text = (
                f"### {canon} Capability Status: `{cap_status.value}`\n\n"
                f"**Why it's blocked:** {reason}\n\n"
                f"**Prerequisite to enable:** {prereq}\n\n"
                f"*Note: The prediction system strictly prevents cross-applying BHARTIARTL equity models to other equities or market indices to prevent misleading signals.*"
            )
            return ChatResponse(
                reply=reply_text,
                model="model_router_authoritative",
                sources=sources,
                limitations=limitations,
                timestamp=now_iso,
            )

    # 5. Attempt generation with local Ollama Gemma 3 12B client
    ollama_client = OllamaLLMClient()
    if ollama_client.is_available():
        system_prompt = (
            "You are the professional, friendly Market Analysis Assistant for the Indian Stock Market Prediction System. "
            "You help users understand stock forecasts, market terminology, regulatory announcements, and system capabilities.\n\n"
            "STRICT RULES:\n"
            "1. Ground all responses in the provided platform facts and context.\n"
            "2. Never fabricate live stock prices, upcoming earnings numbers, or future market moves.\n"
            "3. Clearly state if information or model support is unavailable.\n"
            "4. Keep explanations concise, clear, and easy to understand for beginners.\n"
            "5. Never give direct investment or trading advice."
        )

        user_content_parts = [
            f"User Question: {user_msg}\n"
        ]
        if instrument_context_str:
            user_content_parts.append(f"\n--- Authoritative Instrument Context ---\n{instrument_context_str}")
        if pred_context_str:
            user_content_parts.append(f"\n--- Active Prediction Context ---\n{pred_context_str}")

        full_prompt = "\n".join(user_content_parts)

        try:
            raw_reply = ollama_client.generate(
                prompt=full_prompt,
                system=system_prompt,
                format_json=False,
            )
            sources.append(f"Local Ollama ({ollama_client.model_name})")
            return ChatResponse(
                reply=raw_reply.strip(),
                model=ollama_client.model_name,
                sources=sources,
                limitations=limitations,
                timestamp=now_iso,
            )
        except Exception as exc:
            logger.warning("Local Ollama inference failed: %s. Falling back to grounded rule engine.", exc)

    # 6. Fallback when Ollama is offline or generation encounters error
    fallback_parts = []
    if pred_context_str:
        fallback_parts.append(
            f"**Current Forecast Summary for {target_symbol or 'BHARTIARTL'}:**\n"
            f"The model predicts next-session direction as **{payload.prediction_context.get('predicted_direction', 'N/A')}** "
            f"with probability {round(payload.prediction_context.get('probability_up', 0.5) * 100, 1)}% UP.\n"
        )
    elif instrument_context_str:
        fallback_parts.append(
            f"**{canon} Status:** {cap_status.value}\n"
            f"- {reason}\n"
        )
    else:
        fallback_parts.append(
            "I am ready to assist with stock forecasting, model explanations, instrument capabilities, and market concepts. "
            "Select an instrument like **BHARTIARTL** to run a prediction, or ask questions about market terminology (e.g. repo rate, RSI, MACD)."
        )

    sources.append("Platform Rule Engine (Ollama Offline)")
    limitations.append("Local LLM runtime (Gemma 3 12B) is offline; response generated using deterministic platform rules.")

    return ChatResponse(
        reply="\n\n".join(fallback_parts),
        model="grounded_rule_fallback",
        sources=sources,
        limitations=limitations,
        timestamp=now_iso,
    )
