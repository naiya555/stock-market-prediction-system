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
        if term in lowered:
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
    lowered_msg = user_msg.lower()

    # 1. Determine target symbol
    target_symbol = (payload.symbol or payload.instrument or "").strip().upper()
    if not target_symbol:
        for sym_cand in ("BHARTIARTL", "TCS", "RELIANCE", "NIFTY 50", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS", "NIFTY TELECOM"):
            if sym_cand.lower() in lowered_msg:
                target_symbol = sym_cand
                break

    canon = None
    cap_status = None
    reason = None
    prereq = None
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
    pc = payload.prediction_context if isinstance(payload.prediction_context, dict) else {}
    if pc:
        p_up = pc.get("probability_up")
        p_up_str = f"{round(p_up * 100, 1)}%" if isinstance(p_up, (int, float)) else "Uncalibrated"
        p_down = pc.get("probability_down")
        p_down_str = f"{round(p_down * 100, 1)}%" if isinstance(p_down, (int, float)) else "Uncalibrated"

        pred_context_str = (
            f"Active Forecast for {pc.get('symbol', target_symbol or 'Unknown')}:\n"
            f"- Direction: {pc.get('predicted_direction', 'N/A')}\n"
            f"- Estimated P(UP): {p_up_str}, P(DOWN): {p_down_str}\n"
            f"- Model: {pc.get('model_name', 'N/A')}\n"
            f"- Reason / Signals: {pc.get('reason') or pc.get('why_prediction') or 'Technical momentum and trend analysis'}\n"
        )
        sources.append("Active Prediction Output")

    # Category 1: Why a prediction is UP or DOWN
    if any(q in lowered_msg for q in ("why up", "why down", "why is the prediction", "why prediction", "why does the model predict", "explain signal", "explain forecast", "why signal")):
        active_sym = target_symbol or pc.get("symbol") or "BHARTIARTL"
        dir_val = pc.get("predicted_direction", "N/A")
        reasons = pc.get("reason") or pc.get("why_prediction")
        p_up = pc.get("probability_up")
        prob_note = f" with estimated P(UP) = {p_up * 100:.1f}%" if isinstance(p_up, (int, float)) else ""

        if not reasons:
            reasons = f"The forecast is synthesized from momentum indicators (RSI, MACD), rolling returns, and moving average crossovers for {active_sym}."

        reply = (
            f"### Directional Forecast Rationale for {active_sym}\n\n"
            f"- **Predicted Direction:** **{dir_val}**{prob_note}\n"
            f"- **Forecast Horizon:** Next Trading Session (Close-to-Close)\n\n"
            f"**Underlying Factors:**\n"
            f"{reasons}\n\n"
            f"> *Note: The model predicts the return direction (sign of Close_{{t+1}} - Close_t) rather than an explicit price target.*"
        )
        sources.append("Quantitative Feature Engine & Model Inference")
        return ChatResponse(
            reply=reply,
            model="grounded_rule_engine",
            sources=sources,
            limitations=limitations,
            timestamp=now_iso,
        )

    # Category 2: Latest price and market session
    if any(q in lowered_msg for q in ("latest price", "which price", "market session", "current session", "what price", "what session", "trading session")):
        active_sym = target_symbol or pc.get("symbol") or "BHARTIARTL"
        from app.market.session import get_market_session, IST
        session_info = get_market_session(datetime.now(IST))
        session_state_name = session_info.state.value

        reply = (
            f"### Market Session & Price Status for {active_sym}\n\n"
            f"- **Current NSE Session State:** `{session_state_name}`\n"
            f"- **Data Provider:** `yfinance` (free tier)\n"
            f"- **Delay Policy:** Quotes are delayed by approximately **15 minutes** as required by exchange dissemination rules.\n"
            f"- **Price Distinction:** The dashboard displays the **Last Traded Price (LTP)** or confirmed previous session close. "
            f"Before market open (09:15 IST), the next opening price is unavailable/not yet observed. "
            f"After market close (15:30 IST), the confirmed closing price is recorded.\n\n"
            f"> *Crucial rule: Observed prices are factual historical records and are never generated or modified by prediction models.*"
        )
        sources.append("NSE Market Session Calendar & Quote Pipeline")
        return ChatResponse(
            reply=reply,
            model="grounded_rule_engine",
            sources=sources,
            limitations=limitations,
            timestamp=now_iso,
        )

    # Category 3: Financial Terminology (Repo Rate, Inflation, etc.)
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

    # Category 4: Instrument Availability & Training/Data Prerequisites
    if any(q in lowered_msg for q in ("why is", "why blocked", "how to enable", "prerequisite", "support", "available", "unavailable", "capability")):
        if target_symbol:
            if cap_status and cap_status.value == "SUPPORTED_AND_READY":
                reply_text = (
                    f"### {canon} Status: `SUPPORTED & READY`\n\n"
                    f"**Forecasting Status:** `{canon}` is fully enabled for directional predictions.\n\n"
                    f"- **Data Pipeline:** Verified OHLCV data pipeline active.\n"
                    f"- **Trained Model:** Walk-forward validated machine learning model persisted and verified on held-out test data beating majority baselines.\n"
                    f"- **Inference:** You can select `{canon}` and run predictions immediately on the Predictions tab."
                )
            else:
                reply_text = (
                    f"### {canon} Status: `{cap_status.value if cap_status else 'BLOCKED'}`\n\n"
                    f"**Why it's blocked:** {reason}\n\n"
                    f"**Prerequisites to enable:** {prereq or 'Train dedicated model before enabling.'}\n\n"
                    f"*Note: The system enforces strict capability gates to prevent cross-applying models fitted for one instrument to another.*"
                )
            sources.append("Platform Instrument Registry & Model Router")
            return ChatResponse(
                reply=reply_text,
                model="model_router_authoritative",
                sources=sources,
                limitations=limitations,
                timestamp=now_iso,
            )

    # Category 5: Relevant Market Events
    if any(q in lowered_msg for q in ("market event", "events", "news", "announcement", "circular", "policy", "rbi", "sebi")):
        active_sym = target_symbol or pc.get("symbol") or "BHARTIARTL"
        event_items = []
        if event_providers:
            for ep in event_providers[:2]:
                try:
                    evs = ep.fetch_events(limit=3)
                    for ev in evs:
                        event_items.append(
                            f"- **{ev.headline}** ({getattr(ev, 'source', 'Official')}, {ev.timestamp.strftime('%d %b %Y')})\n"
                            f"  *Category: {getattr(ev, 'category', 'Regulatory')}*"
                        )
                except Exception as exc:
                    logger.warning("Event retrieval in chat failed: %s", exc)

        if event_items:
            events_text = "\n".join(event_items[:5])
        else:
            events_text = "- No recent macro circulars retrieved in current cache."

        reply = (
            f"### Verified Market Events Relevant to {active_sym}\n\n"
            f"Here are recent macroeconomic and regulatory developments tracked from official sources:\n\n"
            f"{events_text}\n\n"
            f"> *All events are retrieved from official regulatory feeds (RBI, SEBI) with confirmed publication timestamps.*"
        )
        sources.append("Official Regulatory Event Providers (RBI / SEBI)")
        return ChatResponse(
            reply=reply,
            model="grounded_rule_engine",
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

        user_content_parts = [f"User Question: {user_msg}\n"]
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

    # 6. General fallback when Ollama is offline
    fallback_parts = []
    if pred_context_str:
        p_up = pc.get("probability_up")
        prob_str = f"with estimated probability {round(p_up * 100, 1)}% UP" if isinstance(p_up, (int, float)) else "with uncalibrated probability"
        fallback_parts.append(
            f"**Current Forecast Summary for {target_symbol or 'BHARTIARTL'}:**\n"
            f"The model predicts next-session direction as **{pc.get('predicted_direction', 'N/A')}** {prob_str}.\n"
        )
    elif instrument_context_str:
        fallback_parts.append(
            f"**{canon} Status:** {cap_status.value if cap_status else 'BLOCKED'}\n"
            f"- {reason}\n"
        )
    else:
        fallback_parts.append(
            "I am ready to assist with stock forecasting, model explanations, instrument capabilities, and market concepts.\n\n"
            "You can ask me:\n"
            "- Why a prediction is UP or DOWN\n"
            "- Which latest price and session the dashboard is showing\n"
            "- What Repo Rate and other market terms mean\n"
            "- Why an instrument like RELIANCE is unavailable\n"
            "- What verified market events are relevant to an instrument"
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
