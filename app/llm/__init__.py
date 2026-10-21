"""LLM Integration Layer for Context Extraction and Qualitative Reasoning (Gemma 3 12B).

Provides isolated, anti-fabrication qualitative analysis using local Ollama runtime.
Strictly decoupled from authoritative quantitative ML models (XGBoost/LightGBM).
"""

from app.llm.client import (
    BaseLLMClient,
    LLMClientError,
    LLMError,
    LLMModelUnavailableError,
    LLMResponseError,
    MockLLMClient,
    OllamaLLMClient,
)
from app.llm.prompts import (
    build_context_extraction_prompt,
    build_prediction_explanation_prompt,
    build_qualitative_reasoning_prompt,
)
from app.llm.schemas import (
    NON_PREDICTIVE_QUALITATIVE_DISCLAIMER,
    LLMContextExtraction,
    LLMDirection,
    LLMExplanationResult,
    LLMExplanationStatus,
    LLMReasoningResult,
)
from app.llm.service import (
    LLMParseError,
    LLMService,
    LLMServiceError,
    LLMValidationError,
)

__all__ = [
    # Schemas
    "LLMDirection",
    "LLMContextExtraction",
    "LLMReasoningResult",
    "LLMExplanationStatus",
    "LLMExplanationResult",
    "NON_PREDICTIVE_QUALITATIVE_DISCLAIMER",
    # Clients
    "BaseLLMClient",
    "OllamaLLMClient",
    "MockLLMClient",
    # Exceptions
    "LLMError",
    "LLMClientError",
    "LLMModelUnavailableError",
    "LLMResponseError",
    "LLMServiceError",
    "LLMParseError",
    "LLMValidationError",
    # Prompts
    "build_context_extraction_prompt",
    "build_prediction_explanation_prompt",
    "build_qualitative_reasoning_prompt",
    # Service
    "LLMService",
]
