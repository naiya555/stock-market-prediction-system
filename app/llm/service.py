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
    LLMModelUnavailableError,
    LLMResponseError,
    OllamaLLMClient,
)
from app.llm.prompts import (
    build_context_extraction_prompt,
    build_prediction_explanation_prompt,
    build_qualitative_reasoning_prompt,
)
from app.llm.schemas import (
    LLMContextExtraction,
    LLMDirection,
    LLMExplanationResult,
    LLMExplanationStatus,
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


MAX_LLM_COMPLETION_CHARS = 100_000


def _extract_json_object(raw_text: str, max_chars: int = MAX_LLM_COMPLETION_CHARS) -> Dict[str, Any]:
    """Extract and parse a JSON object from raw model output.

    Handles leading/trailing whitespace, markdown code blocks (```json ... ```),
    and rejects payloads that are not dictionaries or exceed length bounds.
    """
    if not raw_text or not raw_text.strip():
        raise LLMParseError("LLM response is empty")

    if len(raw_text) > max_chars:
        raise LLMParseError(f"LLM response exceeds maximum allowed length ({len(raw_text)} > {max_chars})")

    cleaned = raw_text.strip()

    # Deterministic line-based markdown code block removal (linear time, zero regex backtracking)
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        first_line = lines[0].strip()
        if first_line.startswith("```"):
            if len(lines) >= 2 and lines[-1].strip().startswith("```"):
                cleaned = "\n".join(lines[1:-1]).strip()
            else:
                cleaned = "\n".join(lines[1:]).strip()

    # Locate the outer JSON object braces
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace : last_brace + 1]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        snippet = raw_text[:200].replace("\r", "\\r").replace("\n", "\\n")
        raise LLMParseError(f"Model output could not be parsed as valid JSON: {e}. Output snippet: {snippet}") from e

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

    def explain_prediction(
        self,
        symbol: str,
        articles: Sequence[Union[NewsArticle, Dict[str, Any]]],
        events: Optional[Sequence[Union[MacroEvent, Dict[str, Any]]]] = None,
        cutoff_time: Optional[datetime] = None,
        quantitative_direction: Optional[str] = None,
        quantitative_probability: Optional[float] = None,
        quantitative_probability_down: Optional[float] = None,
        max_articles: int = 10,
        max_events: int = 10,
    ) -> LLMExplanationResult:
        """Generate an evidence-grounded qualitative explanation for a prediction (Day 55).

        Synthesizes point-in-time verified news articles and regulatory events into
        a validated LLMExplanationResult without mutating numerical predictions.

        Args:
            symbol: Target stock ticker.
            articles: Ingested financial news articles.
            events: Ingested macroeconomic and regulatory events.
            cutoff_time: Optional point-in-time reference timestamp.
            quantitative_direction: Optional directional forecast from quantitative ML.
            quantitative_probability: Optional upward probability P(UP) from quantitative ML.
            quantitative_probability_down: Optional downward probability P(DOWN) from quantitative ML.
            max_articles: Maximum number of articles to pass into prompt (default 10).
            max_events: Maximum number of events to pass into prompt (default 10).

        Returns:
            Validated LLMExplanationResult.
        """
        clean_sym = symbol.strip().upper() if symbol else "UNKNOWN"
        if clean_sym.endswith(".NS") or clean_sym.endswith(".BO"):
            clean_sym = clean_sym.rsplit(".", 1)[0]

        # 1. Check if LLM client is disabled
        if not getattr(self._client, "is_enabled", True):
            return LLMExplanationResult.disabled(symbol=clean_sym, model=self._client.model_name)

        # 2. Point-in-time filtering & bounding
        filtered_articles: List[Union[NewsArticle, Dict[str, Any]]] = []
        for art in articles or []:
            if cutoff_time is not None:
                pub = getattr(art, "published_at", None)
                if pub is None and isinstance(art, dict):
                    pub_val = art.get("published_at")
                    if isinstance(pub_val, datetime):
                        pub = pub_val
                    elif isinstance(pub_val, str):
                        try:
                            pub = datetime.fromisoformat(pub_val.replace("Z", "+00:00"))
                        except ValueError:
                            pub = None
                if pub is not None:
                    # Align timezones
                    if pub.tzinfo is None and cutoff_time.tzinfo is not None:
                        pub = pub.replace(tzinfo=timezone.utc)
                    elif pub.tzinfo is not None and cutoff_time.tzinfo is None:
                        cutoff_time = cutoff_time.replace(tzinfo=timezone.utc)
                    if pub > cutoff_time:
                        continue
            filtered_articles.append(art)

        filtered_events: List[Union[MacroEvent, Dict[str, Any]]] = []
        for ev in events or []:
            if cutoff_time is not None:
                pub = getattr(ev, "published_at", None)
                if pub is None and isinstance(ev, dict):
                    pub_val = ev.get("published_at")
                    if isinstance(pub_val, datetime):
                        pub = pub_val
                    elif isinstance(pub_val, str):
                        try:
                            pub = datetime.fromisoformat(pub_val.replace("Z", "+00:00"))
                        except ValueError:
                            pub = None
                if pub is not None:
                    if pub.tzinfo is None and cutoff_time.tzinfo is not None:
                        pub = pub.replace(tzinfo=timezone.utc)
                    elif pub.tzinfo is not None and cutoff_time.tzinfo is None:
                        cutoff_time = cutoff_time.replace(tzinfo=timezone.utc)
                    if pub > cutoff_time:
                        continue
            filtered_events.append(ev)

        # 3. Empty context check
        if not filtered_articles and not filtered_events:
            return LLMExplanationResult.no_context(symbol=clean_sym, model=self._client.model_name)

        # 4. Check model availability
        if hasattr(self._client, "check_model_availability"):
            try:
                self._client.check_model_availability()
            except LLMModelUnavailableError as e:
                return LLMExplanationResult.unavailable(
                    symbol=clean_sym,
                    model=self._client.model_name,
                    reason=f"Target model unavailable: {e}",
                )
            except LLMClientError as e:
                return LLMExplanationResult.unavailable(
                    symbol=clean_sym,
                    model=self._client.model_name,
                    reason=f"Ollama connection check failed: {e}",
                )

        # 5. Build prompt with provenance
        system_instruction, user_prompt, known_provenance = build_prediction_explanation_prompt(
            symbol=clean_sym,
            articles=filtered_articles[:max_articles],
            events=filtered_events[:max_events],
            quantitative_direction=quantitative_direction,
            quantitative_probability=quantitative_probability,
            quantitative_probability_down=quantitative_probability_down,
        )

        # 6. Execute model inference
        try:
            logger.info("Calling LLM explanation prompt for '%s'", clean_sym)
            raw_response = self._client.generate(
                prompt=user_prompt,
                system=system_instruction,
                format_json=True,
            )
        except LLMModelUnavailableError as e:
            return LLMExplanationResult.unavailable(
                symbol=clean_sym,
                model=self._client.model_name,
                reason=f"Model unavailable: {e}",
            )
        except LLMClientError as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "timed out" in err_str:
                return LLMExplanationResult.timeout(symbol=clean_sym, model=self._client.model_name)
            if "disabled" in err_str:
                return LLMExplanationResult.disabled(symbol=clean_sym, model=self._client.model_name)
            return LLMExplanationResult.unavailable(
                symbol=clean_sym,
                model=self._client.model_name,
                reason=f"Ollama client error: {e}",
            )
        except Exception as e:
            return LLMExplanationResult.failed(
                symbol=clean_sym,
                model=self._client.model_name,
                error_message=f"Generation failed: {e}",
            )

        # 7. Extract JSON and parse schema
        try:
            parsed_data = _extract_json_object(raw_response)
        except Exception as e:
            return LLMExplanationResult.failed(
                symbol=clean_sym,
                model=self._client.model_name,
                error_message=f"Model response was not valid JSON: {e}",
            )

        # 8. Validate supporting evidence against provenance
        verified_evidence, unverified_notes = _validate_supporting_evidence(
            parsed_data.get("supporting_evidence", ()),
            known_provenance,
        )

        limitations_input = parsed_data.get("limitations", ())
        if isinstance(limitations_input, (list, tuple)):
            limitations_list = [str(x).strip() for x in limitations_input if str(x).strip()]
        elif isinstance(limitations_input, str) and limitations_input.strip():
            limitations_list = [limitations_input.strip()]
        else:
            limitations_list = []
        limitations_list.extend(unverified_notes)

        # Truncation note if input exceeded max bounds
        if len(filtered_articles) > max_articles or len(filtered_events) > max_events:
            limitations_list.append(
                f"Input context was bounded to the {max_articles} most recent articles and {max_events} events."
            )

        summary = str(parsed_data.get("summary", "")).strip() or "Market context analyzed."
        direction = parsed_data.get("direction")
        confidence = str(parsed_data.get("confidence", "LOW")).strip().upper()

        return LLMExplanationResult(
            status=LLMExplanationStatus.SUCCESS,
            summary=summary,
            supporting_evidence=verified_evidence,
            limitations=tuple(limitations_list),
            model=self._client.model_name,
            generated_at=datetime.now(timezone.utc).isoformat(),
            symbol=clean_sym,
            direction=str(direction).strip().upper() if direction else None,
            confidence=confidence if confidence in ("LOW", "MEDIUM", "HIGH") else "LOW",
            raw_response=raw_response,
        )


def _validate_supporting_evidence(
    raw_evidence: Any,
    known_provenance: Dict[str, str],
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Validate supporting evidence items strictly against supplied source records.

    Enforces zero-fabrication guarantees:
    - Explicit tags (e.g. [News 99], [Event 10]) are checked against supplied tags.
    - Sources must match known publishers, organizations, URLs, or headline tokens.
    - Loose keyword wildcards (e.g. matching 'article' or 'report') are forbidden.
    - Rejected citations are omitted and reported in limitations.
    """
    if not raw_evidence:
        return (), ()

    if isinstance(raw_evidence, (list, tuple)):
        items = [str(x).strip() for x in raw_evidence if str(x).strip()]
    elif isinstance(raw_evidence, str) and raw_evidence.strip():
        items = [raw_evidence.strip()]
    else:
        return (), ()

    verified: List[str] = []
    unverified_notes: List[str] = []

    if not known_provenance:
        return (), ("Supporting evidence could not be matched against verified sources (empty provenance).",)

    tag_pattern = re.compile(r"\[(news|event)\s*(\d+)\]", re.IGNORECASE)

    for item in items:
        item_lower = item.lower()

        # Reject any citation referencing an invented/unknown tag ID (e.g. [News 99])
        explicit_tags = tag_pattern.findall(item_lower)
        invalid_tags = [
            f"[{t_type} {t_num}]"
            for t_type, t_num in explicit_tags
            if f"[{t_type.lower()} {t_num}]" not in known_provenance
        ]
        if invalid_tags:
            unverified_notes.append(
                f"Unverified citation omitted (tag {', '.join(invalid_tags)} not in context): '{item[:80]}'"
            )
            continue

        # Verify whether citation names a known source tag, publisher, org, or headline snippet
        is_grounded = any(
            token in item_lower
            for token in known_provenance.keys()
            if len(token) >= 3
        )
        if is_grounded:
            verified.append(item)
        else:
            unverified_notes.append(
                f"Unverified citation omitted (source not in supplied context): '{item[:80]}'"
            )

    return tuple(verified), tuple(unverified_notes)
