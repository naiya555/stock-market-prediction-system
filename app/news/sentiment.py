"""FinBERT Financial News Sentiment Scoring Foundation.

Provides domain-specific sentiment classification (positive, neutral, negative)
for financial news articles using FinBERT (ProsusAI/finbert).

CRITICAL NON-PREDICTIVE DISCLAIMER:
    Sentiment score is a natural language classification of textual tone in news.
    It is NOT a prediction of future stock price movements, directional returns,
    or financial performance. High classifier confidence in positive/negative sentiment
    must never be conflated with market prediction confidence or trading signals.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from app.core.logging_config import get_logger
from app.core.schemas import ValidationError
from app.news.schemas import NewsArticle

logger = get_logger(__name__)

IST = ZoneInfo("Asia/Kolkata")

# Default FinBERT model identifier on Hugging Face Hub
DEFAULT_FINBERT_MODEL = "ProsusAI/finbert"

# Allowed canonical sentiment classes
VALID_SENTIMENT_CLASSES = ("positive", "neutral", "negative")


@dataclass(frozen=True)
class ArticleSentimentResult:
    """Canonical point-in-time sentiment classification output for a single news article."""

    article_id: str
    headline: str
    sentiment_label: Optional[str]
    sentiment_score: Optional[float]
    probabilities: Optional[Dict[str, float]]
    model_name: str
    model_version: Optional[str]
    scored_at: datetime
    status: str = "SUCCESS"  # SUCCESS, ERROR, UNSCORED
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.article_id or not self.article_id.strip():
            raise ValidationError("article_id cannot be empty")
        object.__setattr__(self, "article_id", self.article_id.strip())

        if not isinstance(self.scored_at, datetime):
            raise ValidationError("scored_at must be a valid datetime instance")
        if self.scored_at.tzinfo is None:
            raise ValidationError("scored_at must be timezone-aware")

        if self.status == "SUCCESS":
            if not self.sentiment_label or self.sentiment_label.lower() not in VALID_SENTIMENT_CLASSES:
                raise ValidationError(
                    f"sentiment_label must be one of {VALID_SENTIMENT_CLASSES}, got '{self.sentiment_label}'"
                )
            object.__setattr__(self, "sentiment_label", self.sentiment_label.lower())

            if self.sentiment_score is None or not isinstance(self.sentiment_score, (int, float)):
                raise ValidationError("sentiment_score must be a numeric probability")
            if math.isnan(self.sentiment_score) or math.isinf(self.sentiment_score):
                raise ValidationError("sentiment_score must be a finite number")
            if not (0.0 <= self.sentiment_score <= 1.0):
                raise ValidationError(f"sentiment_score must be in range [0, 1], got {self.sentiment_score}")

            if not self.probabilities or not isinstance(self.probabilities, dict):
                raise ValidationError("probabilities must be a non-empty dictionary")

            missing_classes = set(VALID_SENTIMENT_CLASSES) - set(self.probabilities.keys())
            if missing_classes:
                raise ValidationError(f"probabilities missing required classes: {missing_classes}")

            prob_sum = 0.0
            norm_probs: Dict[str, float] = {}
            for cls_name in VALID_SENTIMENT_CLASSES:
                p_val = self.probabilities[cls_name]
                if not isinstance(p_val, (int, float)) or math.isnan(p_val) or math.isinf(p_val):
                    raise ValidationError(f"Probability for '{cls_name}' must be a finite float")
                if not (0.0 <= p_val <= 1.0):
                    raise ValidationError(f"Probability for '{cls_name}' must be in [0, 1], got {p_val}")
                prob_sum += float(p_val)
                norm_probs[cls_name] = float(p_val)

            # Validate probability normalization: sum must equal 1.0 within tolerance
            if abs(prob_sum - 1.0) > 1e-3:
                raise ValidationError(f"Class probabilities must sum to 1.0 (got {prob_sum:.4f})")

            object.__setattr__(self, "probabilities", norm_probs)

            # Winning confidence must match the assigned label's probability
            expected_score = norm_probs[self.sentiment_label]
            if abs(self.sentiment_score - expected_score) > 1e-4:
                raise ValidationError(
                    f"sentiment_score ({self.sentiment_score}) must match winning class probability ({expected_score})"
                )

    def to_dict(self) -> Dict[str, Any]:
        """Convert sentiment result to flat dictionary."""
        return {
            "article_id": self.article_id,
            "headline": self.headline,
            "sentiment_label": self.sentiment_label,
            "sentiment_score": round(self.sentiment_score, 4) if self.sentiment_score is not None else None,
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()} if self.probabilities else None,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "scored_at": self.scored_at.isoformat(),
            "status": self.status,
            "error_message": self.error_message,
        }


def prepare_article_text(
    article: NewsArticle,
    include_summary: bool = False,
    max_chars: int = 512,
) -> str:
    """Prepare textual input from a NewsArticle for FinBERT tokenization.

    Rules:
    - Headline is mandatory and forms the primary text.
    - If include_summary is True and summary exists, concatenates headline + summary.
    - Truncates to max_chars to remain well within BERT's 512 subword token limit.
    - Rejects empty or whitespace-only headlines.
    - Preserves the original NewsArticle completely unchanged.

    Args:
        article: Canonical NewsArticle instance.
        include_summary: Whether to append the article summary (default False).
        max_chars: Maximum character length cutoff (default 512).

    Returns:
        Prepared clean text string.

    Raises:
        ValidationError: If article has blank or whitespace-only headline.
    """
    if not article.headline or not article.headline.strip():
        raise ValidationError(f"Article {article.article_id} has empty or blank headline")

    headline = article.headline.strip()
    if include_summary and article.summary and article.summary.strip():
        text = f"{headline}. {article.summary.strip()}"
    else:
        text = headline

    if len(text) > max_chars:
        # Truncate at character boundary safely
        text = text[:max_chars].rsplit(" ", 1)[0].strip()

    return text


class BaseSentimentBackend(ABC):
    """Abstract interface for sentiment model inference execution."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        pass

    @property
    @abstractmethod
    def model_version(self) -> Optional[str]:
        """Return model revision or version string."""
        pass

    @abstractmethod
    def predict(self, text: str) -> Dict[str, float]:
        """Compute class probabilities for a single text input.

        Returns:
            Dictionary mapping 'positive', 'neutral', 'negative' to probabilities in [0, 1].
        """
        pass

    def predict_batch(self, texts: Sequence[str]) -> List[Dict[str, float]]:
        """Compute class probabilities across a batch of texts.

        Default implementation loops over predict; optimized backends may batch tensor operations.
        """
        return [self.predict(t) for t in texts]


class MockSentimentBackend(BaseSentimentBackend):
    """Deterministic, offline test double for FinBERT inference.

    Allows injecting static probability distributions or simulating inference exceptions
    without downloading neural network weights or making network calls.
    """

    def __init__(
        self,
        default_probs: Optional[Dict[str, float]] = None,
        model_name: str = "mock-finbert",
        model_version: str = "1.0.0",
        simulate_error: Optional[Exception] = None,
    ) -> None:
        self._default_probs = default_probs or {"positive": 0.1, "neutral": 0.8, "negative": 0.1}
        self._model_name = model_name
        self._model_version = model_version
        self._simulate_error = simulate_error

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> Optional[str]:
        return self._model_version

    def predict(self, text: str) -> Dict[str, float]:
        if self._simulate_error:
            raise self._simulate_error

        # Simple deterministic heuristic for test cases if no static mapping provided:
        clean = text.lower()
        if "growth" in clean or "profit" in clean or "surge" in clean or "bull" in clean:
            return {"positive": 0.85, "neutral": 0.10, "negative": 0.05}
        if "drop" in clean or "loss" in clean or "slump" in clean or "bear" in clean:
            return {"positive": 0.05, "neutral": 0.15, "negative": 0.80}

        return dict(self._default_probs)

    def predict_batch(self, texts: Sequence[str]) -> List[Dict[str, float]]:
        return [self.predict(t) for t in texts]


class FinBERTBackend(BaseSentimentBackend):
    """Production FinBERT inference backend powered by Hugging Face Transformers.

    Features:
    - Lazy loading: PyTorch and Transformers are imported and initialized only on first call.
    - Dynamic label mapping: Inspects model.config.id2label dynamically rather than assuming order.
    - Deterministic evaluation: Enforces torch.inference_mode() and model.eval().
    - Configurable model identifier and local cache behavior.
    """

    def __init__(
        self,
        model_identifier: str = DEFAULT_FINBERT_MODEL,
        revision: Optional[str] = None,
        device: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ) -> None:
        self._model_identifier = model_identifier
        self._revision = revision
        self._device = device
        self._cache_dir = cache_dir

        self._tokenizer = None
        self._model = None
        self._label_map: Optional[Dict[int, str]] = None
        self._is_loaded = False

    @property
    def model_name(self) -> str:
        return self._model_identifier

    @property
    def model_version(self) -> Optional[str]:
        return self._revision or "main"

    def _load_model(self) -> None:
        """Lazily load PyTorch, Transformers tokenizer, and classification model."""
        if self._is_loaded:
            return

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            logger.error("FinBERT dependencies missing: %s", exc)
            raise RuntimeError(
                f"FinBERT inference requires 'transformers' and 'torch'. Install them via pip: {exc}"
            ) from exc

        logger.info(
            "Loading FinBERT model '%s' (revision=%s, cache_dir=%s)...",
            self._model_identifier,
            self._revision,
            self._cache_dir,
        )

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_identifier,
                revision=self._revision,
                cache_dir=self._cache_dir,
            )
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self._model_identifier,
                revision=self._revision,
                cache_dir=self._cache_dir,
            )
        except Exception as exc:
            logger.error("Failed to load FinBERT model '%s': %s", self._model_identifier, exc)
            raise RuntimeError(f"Failed to load FinBERT model '{self._model_identifier}': {exc}") from exc

        # Resolve compute device safely
        if self._device:
            target_device = self._device
        else:
            target_device = "cuda" if torch.cuda.is_available() else "cpu"

        self._model.to(target_device)
        self._model.eval()
        self._device = target_device

        # Dynamically inspect model config id2label mapping
        # ProsusAI/finbert standard id2label: {0: 'positive', 1: 'negative', 2: 'neutral'}
        raw_id2label = getattr(self._model.config, "id2label", None)
        if raw_id2label:
            self._label_map = {int(idx): str(lbl).lower() for idx, lbl in raw_id2label.items()}
        else:
            logger.warning("No id2label found in model config; falling back to default FinBERT index mapping")
            self._label_map = {0: "positive", 1: "negative", 2: "neutral"}

        self._is_loaded = True
        logger.info(
            "FinBERT model loaded successfully on device '%s' with label map %s",
            self._device,
            self._label_map,
        )

    def predict(self, text: str) -> Dict[str, float]:
        """Compute FinBERT class probabilities for text."""
        return self.predict_batch([text])[0]

    def predict_batch(self, texts: Sequence[str]) -> List[Dict[str, float]]:
        """Compute FinBERT class probabilities across multiple texts."""
        if not texts:
            return []

        self._load_model()
        import torch

        # Tokenize with truncation to model max length (typically 512)
        inputs = self._tokenizer(
            list(texts),
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt",
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()

        results: List[Dict[str, float]] = []
        for row in probs:
            prob_dict: Dict[str, float] = {}
            for idx, prob_val in enumerate(row):
                label_name = self._label_map.get(idx, f"class_{idx}")
                prob_dict[label_name] = float(prob_val)

            # Ensure all canonical classes exist
            for cls_name in VALID_SENTIMENT_CLASSES:
                if cls_name not in prob_dict:
                    prob_dict[cls_name] = 0.0

            results.append(prob_dict)

        return results


class FinBERTSentimentScorer:
    """High-level service coordinating article text preparation and sentiment scoring."""

    def __init__(
        self,
        backend: Optional[BaseSentimentBackend] = None,
        model_identifier: str = DEFAULT_FINBERT_MODEL,
        include_summary: bool = False,
    ) -> None:
        """Initialize FinBERT sentiment scoring service.

        Args:
            backend: Optional custom sentiment backend (default creates FinBERTBackend).
            model_identifier: Model name on Hugging Face (default 'ProsusAI/finbert').
            include_summary: Whether to include article summary in scoring text.
        """
        self._backend = backend or FinBERTBackend(model_identifier=model_identifier)
        self._include_summary = include_summary

    @property
    def model_name(self) -> str:
        return self._backend.model_name

    @property
    def model_version(self) -> Optional[str]:
        return self._backend.model_version

    def score_article(self, article: NewsArticle) -> ArticleSentimentResult:
        """Score sentiment for a single NewsArticle.

        Invariants:
        - Never guesses or fabricates a fake neutral sentiment on inference failure.
        - Preserves article_id, headline, and provenance tracking.
        - Records scoring timestamp distinctly from publication and ingestion times.
        """
        scored_at = datetime.now(timezone.utc).astimezone(IST)

        try:
            text = prepare_article_text(article, include_summary=self._include_summary)
        except ValidationError as exc:
            logger.warning("Article text preparation failed for %s: %s", article.article_id, exc)
            return ArticleSentimentResult(
                article_id=article.article_id,
                headline=article.headline,
                sentiment_label=None,
                sentiment_score=None,
                probabilities=None,
                model_name=self.model_name,
                model_version=self.model_version,
                scored_at=scored_at,
                status="ERROR",
                error_message=f"Text preparation failed: {exc}",
            )

        try:
            probs = self._backend.predict(text)
        except Exception as exc:
            logger.error("Inference failure for article %s: %s", article.article_id, exc)
            return ArticleSentimentResult(
                article_id=article.article_id,
                headline=article.headline,
                sentiment_label=None,
                sentiment_score=None,
                probabilities=None,
                model_name=self.model_name,
                model_version=self.model_version,
                scored_at=scored_at,
                status="ERROR",
                error_message=f"Inference error: {exc}",
            )

        # Identify winning class and confidence
        winning_label = max(probs, key=probs.get)
        confidence = probs[winning_label]

        return ArticleSentimentResult(
            article_id=article.article_id,
            headline=article.headline,
            sentiment_label=winning_label,
            sentiment_score=confidence,
            probabilities=probs,
            model_name=self.model_name,
            model_version=self.model_version,
            scored_at=scored_at,
            status="SUCCESS",
            error_message=None,
        )

    def score_articles(self, articles: Sequence[NewsArticle]) -> List[ArticleSentimentResult]:
        """Score sentiment across an ordered sequence of NewsArticle records.

        Preserves 1:1 input ordering.
        """
        if not articles:
            return []

        results: List[ArticleSentimentResult] = []
        for art in articles:
            results.append(self.score_article(art))
        return results
