"""Financial NLP Package.

Provides FinBERT sentiment scoring foundation and financial text processing.
"""

from app.news.sentiment import (
    DEFAULT_FINBERT_MODEL,
    VALID_SENTIMENT_CLASSES,
    ArticleSentimentResult,
    BaseSentimentBackend,
    FinBERTBackend,
    FinBERTSentimentScorer,
    MockSentimentBackend,
    prepare_article_text,
)

__all__ = [
    "ArticleSentimentResult",
    "BaseSentimentBackend",
    "MockSentimentBackend",
    "FinBERTBackend",
    "FinBERTSentimentScorer",
    "prepare_article_text",
    "DEFAULT_FINBERT_MODEL",
    "VALID_SENTIMENT_CLASSES",
]
