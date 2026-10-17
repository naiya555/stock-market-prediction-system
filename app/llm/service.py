"""LLM Service Orchestrator for Context Extraction and Qualitative Reasoning.

Orchestrates communication with the LLM backend (Ollama / Gemma 3 12B), enforces
anti-fabrication guarantees, parses and validates JSON outputs against canonical schemas,
and strictly separates qualitative text reasoning from quantitative ML authority.
"""

from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from app.core.logging_config import get_logger
from app.core.schemas import ValidationError
from app.events.schemas import MacroEvent
from app.llm.client import (
    BaseLLMClient,
    LLMClientError,
    LLMError,
    LLMResponseError,
    OllamaLLMClient,
)
from app.llm.prompts import (
    build_context_extraction_prompt,
    build_qualitative_reasoning_prompt,
)
from app.llm.schemas import (
    LLMContextExtraction,
    LLMDirection,
    LLMReasoningResult,
)
from app.news.schemas import NewsArticle

logger = get_logger(__name__)


class LLMServiceError(LLMError):
    """Base exception for LLM service orchestration failures."""
    pass


class LLMParseError(LLMServiceError):
    """Raised when LLM output cannot be parsed into the required structured format."""
    pass


class LLMValidationError(LLMServiceError):
    """Raised when parsed structured data violates schema validation rules."""
    pass


def _extract_json_object(raw_text: str) -> Dict[str, Any]:
    """Extract and parse a JSON object from raw model output.

    Handles leading/trailing whitespace, markdown code blocks (```json ... ```),
    and rejects payloads that are not dictionaries.
    """
    if not raw_text or not raw_text.strip():
        raise LLMParseError("LLM response is empty")

    cleaned = raw_text.strip()

    # Strip markdown code blocks if the model wrapped the JSON
    if cleaned.startswith("```"):
        # Match ```json ... ``` or ``` ... ```
        pattern = r"^```(?:json)?\s*\n?(.*?)\n?```$"
        match = re.search(pattern, cleaned, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
        else:
            # Fallback: strip leading ```... and trailing ```
            lines = cleaned.splitlines()
            if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
                cleaned = "\n".join(lines[1:-1]).strip()

    # Attempt to locate the outer JSON object if extra text surrounds it
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace : last_brace + 1]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise LLMParseError(f"Model output could not be parsed as valid JSON: {e}. Output was: {raw_text[:200]}") from e

    if not isinstance(data, dict):
        raise LLMParseError(f"Expected JSON object (dict), but received {type(data).__name__}")

    return data


class LLMService:
    """Service layer orchestrating Role A context extraction and Role B qualitative reasoning."""

    def __init__(self, client: Optional[BaseLLMClient] = None) -> None:
        """Initialize LLM service with the specified client backend."""
        self._client: BaseLLMClient = client or OllamaLLMClient()

    @property
    def client(self) -> BaseLLMClient:
        """Return the underlying LLM client."""
        return self._client

    def extract_context(
        self,
        articles: Sequence[Union[NewsArticle, Dict[str, Any]]],
        events: Optional[Sequence[Union[MacroEvent, Dict[str, Any]]]] = None,
    ) -> LLMContextExtraction:
        """Extract structured entities, factors, and sector exposures from qualitative sources.

        Args:
            articles: Point-in-time filtered news articles.
            events: Optional point-in-time filtered macroeconomic/regulatory events.

        Returns:
            Validated LLMContextExtraction instance.

        Raises:
            LLMClientError: On communication, connection, or timeout failure.
            LLMParseError: If output is malformed or unparseable.
            LLMValidationError: If structured output violates schema contract.
        """
        # Fast-path for empty context
        if not articles and not events:
            return LLMContextExtraction(
                entities=(),
                affected_sectors=(),
                macro_factors=(),
                regulatory_factors=(),
                sentiment_tone="NEUTRAL",
                source_references=(),
                uncertainty_notes="No source articles or events provided for point-in-time extraction.",
                model_version=self._client.model_name,
                extracted_at=datetime.now(timezone.utc),
            )

        system_instruction, user_prompt = build_context_extraction_prompt(articles, events)

        logger.debug(
            "Calling LLM for context extraction: %d articles, %d events",
            len(articles),
            len(events) if events else 0,
        )

        raw_response = self._client.generate(
            prompt=user_prompt,
            system=system_instruction,
            format_json=True,
        )

        parsed_data = _extract_json_object(raw_response)

        try:
            return LLMContextExtraction(
                entities=parsed_data.get("entities", ()),
                affected_sectors=parsed_data.get("affected_sectors", ()),
                macro_factors=parsed_data.get("macro_factors", ()),
                regulatory_factors=parsed_data.get("regulatory_factors", ()),
                sentiment_tone=str(parsed_data.get("sentiment_tone", "NEUTRAL")),
                source_references=parsed_data.get("source_references", ()),
                uncertainty_notes=parsed_data.get("uncertainty_notes"),
                model_version=self._client.model_name,
                extracted_at=datetime.now(timezone.utc),
                raw_response=raw_response,
            )
        except ValidationError as e:
            raise LLMValidationError(f"Context extraction schema validation failed: {e}") from e

    def generate_qualitative_reasoning(
        self,
        symbol: str,
        articles: Sequence[Union[NewsArticle, Dict[str, Any]]],
        events: Optional[Sequence[Union[MacroEvent, Dict[str, Any]]]] = None,
        context_summary: Optional[str] = None,
    ) -> LLMReasoningResult:
        """Perform qualitative directional reasoning and risk synthesis for an equity symbol.

        Args:
            symbol: Target stock symbol (e.g. 'RELIANCE').
            articles: Point-in-time filtered news articles.
            events: Optional point-in-time filtered macro/regulatory events.
            context_summary: Optional synthesized context notes from Role A.

        Returns:
            Validated LLMReasoningResult instance.

        Raises:
            LLMClientError: On communication, connection, or timeout failure.
            LLMParseError: If output is malformed or missing required fields.
            LLMValidationError: If structured output violates schema contract.
        """
        if not symbol or not symbol.strip():
            raise LLMValidationError("symbol cannot be empty")

        clean_sym = symbol.strip().upper()
        if clean_sym.endswith(".NS") or clean_sym.endswith(".BO"):
            clean_sym = clean_sym.rsplit(".", 1)[0]

        # Fast-path for completely empty qualitative context:
        # Honestly return INSUFFICIENT_EVIDENCE with LOW confidence (do NOT fabricate neutral fallback)
        if not articles and not events and not context_summary:
            return LLMReasoningResult(
                symbol=clean_sym,
                direction=LLMDirection.INSUFFICIENT_EVIDENCE,
                reasoning_summary="No qualitative news or event records provided for point-in-time analysis.",
                positive_factors=(),
                negative_factors=(),
                downside_risks=(),
                source_references=(),
                confidence_assessment="LOW",
                model_version=self._client.model_name,
                generated_at=datetime.now(timezone.utc),
            )

        system_instruction, user_prompt = build_qualitative_reasoning_prompt(
            symbol=clean_sym,
            articles=articles,
            events=events,
            context_summary=context_summary,
        )

        logger.debug(
            "Calling LLM for qualitative reasoning: symbol=%s, articles=%d, events=%d",
            clean_sym,
            len(articles),
            len(events) if events else 0,
        )

        raw_response = self._client.generate(
            prompt=user_prompt,
            system=system_instruction,
            format_json=True,
        )

        parsed_data = _extract_json_object(raw_response)

        # Validate presence of required keys
        if "direction" not in parsed_data:
            raise LLMParseError("LLM reasoning output missing required key 'direction'")
        if "reasoning_summary" not in parsed_data:
            raise LLMParseError("LLM reasoning output missing required key 'reasoning_summary'")

        raw_direction = str(parsed_data["direction"]).strip().upper()
        try:
            direction_enum = LLMDirection(raw_direction)
        except ValueError:
            raise LLMValidationError(
                f"Invalid qualitative direction '{raw_direction}'. "
                f"Must be one of: {[d.value for d in LLMDirection]}"
            )

        try:
            return LLMReasoningResult(
                symbol=clean_sym,
                direction=direction_enum,
                reasoning_summary=str(parsed_data["reasoning_summary"]),
                positive_factors=parsed_data.get("positive_factors", ()),
                negative_factors=parsed_data.get("negative_factors", ()),
                downside_risks=parsed_data.get("downside_risks", ()),
                source_references=parsed_data.get("source_references", ()),
                confidence_assessment=str(parsed_data.get("confidence_assessment", "LOW")),
                model_version=self._client.model_name,
                generated_at=datetime.now(timezone.utc),
                raw_response=raw_response,
            )
        except ValidationError as e:
            raise LLMValidationError(f"Qualitative reasoning schema validation failed: {e}") from e
