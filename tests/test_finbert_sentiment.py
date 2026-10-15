"""Unit and regression tests for Day 28: FinBERT Financial Sentiment Scoring Foundation."""

from datetime import datetime, timedelta, timezone
import math
import pytest
from zoneinfo import ZoneInfo

from app.core.schemas import ValidationError
from app.news.cleaner import filter_news_point_in_time
from app.news.schemas import NewsArticle
from app.news.sentiment import (
    ArticleSentimentResult,
    BaseSentimentBackend,
    FinBERTBackend,
    FinBERTSentimentScorer,
    MockSentimentBackend,
    prepare_article_text,
)

IST = ZoneInfo("Asia/Kolkata")


def _make_article(
    headline: str = "Airtel reports 20% profit growth in Q2",
    summary: Optional[str] = "Operating performance improved across mobile services.",
    article_id: str = "art_12345678",
    pub_offset_hours: int = 0,
) -> NewsArticle:
    """Helper to create a valid NewsArticle fixture."""
    base_time = datetime(2026, 10, 15, 10, 0, tzinfo=IST)
    pub_time = base_time + timedelta(hours=pub_offset_hours)
    return NewsArticle(
        headline=headline,
        source="Economic Times",
        published_at=pub_time,
        ingested_at=pub_time + timedelta(minutes=5),
        symbols=("BHARTIARTL",),
        url="https://economictimes.indiatimes.com/news/123",
        summary=summary,
        provider="rss_news_provider",
        article_id=article_id,
    )


class TestArticleSentimentResultSchema:
    """Tests for ArticleSentimentResult contract validation and probability invariants."""

    def test_positive_sentiment_result_construction(self) -> None:
        now = datetime.now(timezone.utc).astimezone(IST)
        probs = {"positive": 0.85, "neutral": 0.10, "negative": 0.05}
        res = ArticleSentimentResult(
            article_id="art_1",
            headline="Bharti Airtel surges on strong subscriber additions",
            sentiment_label="positive",
            sentiment_score=0.85,
            probabilities=probs,
            model_name="ProsusAI/finbert",
            model_version="main",
            scored_at=now,
            status="SUCCESS",
        )
        assert res.article_id == "art_1"
        assert res.sentiment_label == "positive"
        assert res.sentiment_score == 0.85
        assert res.probabilities == probs
        assert res.model_name == "ProsusAI/finbert"
        assert res.status == "SUCCESS"
        assert res.error_message is None

        d = res.to_dict()
        assert d["sentiment_label"] == "positive"
        assert d["sentiment_score"] == 0.85
        assert d["probabilities"]["positive"] == 0.85
        assert "scored_at" in d

    def test_neutral_and_negative_sentiment_results(self) -> None:
        now = datetime.now(timezone.utc).astimezone(IST)

        # Neutral result
        neutral_probs = {"positive": 0.15, "neutral": 0.70, "negative": 0.15}
        n_res = ArticleSentimentResult(
            article_id="art_neutral",
            headline="Board meeting scheduled for November 4",
            sentiment_label="neutral",
            sentiment_score=0.70,
            probabilities=neutral_probs,
            model_name="ProsusAI/finbert",
            model_version="main",
            scored_at=now,
        )
        assert n_res.sentiment_label == "neutral"

        # Negative result
        neg_probs = {"positive": 0.05, "neutral": 0.15, "negative": 0.80}
        neg_res = ArticleSentimentResult(
            article_id="art_neg",
            headline="Net profit slumps 30% due to exceptional tax provision",
            sentiment_label="negative",
            sentiment_score=0.80,
            probabilities=neg_probs,
            model_name="ProsusAI/finbert",
            model_version="main",
            scored_at=now,
        )
        assert neg_res.sentiment_label == "negative"

    def test_validation_probabilities_must_sum_to_one(self) -> None:
        now = datetime.now(timezone.utc).astimezone(IST)
        # Sum is 1.15 (invalid)
        bad_probs = {"positive": 0.85, "neutral": 0.20, "negative": 0.10}
        with pytest.raises(ValidationError, match="Class probabilities must sum to 1.0"):
            ArticleSentimentResult(
                article_id="art_1",
                headline="Surge",
                sentiment_label="positive",
                sentiment_score=0.85,
                probabilities=bad_probs,
                model_name="finbert",
                model_version=None,
                scored_at=now,
            )

    def test_validation_non_finite_or_out_of_range_probabilities(self) -> None:
        now = datetime.now(timezone.utc).astimezone(IST)

        # NaN probability
        nan_probs = {"positive": float("nan"), "neutral": 0.5, "negative": 0.5}
        with pytest.raises(ValidationError, match="must be a finite float"):
            ArticleSentimentResult(
                article_id="art_1",
                headline="Headline",
                sentiment_label="positive",
                sentiment_score=0.5,
                probabilities=nan_probs,
                model_name="finbert",
                model_version=None,
                scored_at=now,
            )

        # Probability > 1.0
        out_probs = {"positive": 1.5, "neutral": -0.3, "negative": -0.2}
        with pytest.raises(ValidationError, match="must be in \\[0, 1\\]"):
            ArticleSentimentResult(
                article_id="art_1",
                headline="Headline",
                sentiment_label="positive",
                sentiment_score=1.0,
                probabilities=out_probs,
                model_name="finbert",
                model_version=None,
                scored_at=now,
            )

    def test_validation_winning_confidence_must_match_label_probability(self) -> None:
        now = datetime.now(timezone.utc).astimezone(IST)
        probs = {"positive": 0.80, "neutral": 0.10, "negative": 0.10}
        # sentiment_score claims 0.90 while positive probability is 0.80
        with pytest.raises(ValidationError, match="must match winning class probability"):
            ArticleSentimentResult(
                article_id="art_1",
                headline="Surge",
                sentiment_label="positive",
                sentiment_score=0.90,
                probabilities=probs,
                model_name="finbert",
                model_version=None,
                scored_at=now,
            )

    def test_validation_invalid_sentiment_class_rejected(self) -> None:
        now = datetime.now(timezone.utc).astimezone(IST)
        probs = {"positive": 0.8, "neutral": 0.1, "negative": 0.1}
        with pytest.raises(ValidationError, match="sentiment_label must be one of"):
            ArticleSentimentResult(
                article_id="art_1",
                headline="Surge",
                sentiment_label="bullish",  # Invalid (must be positive/neutral/negative)
                sentiment_score=0.8,
                probabilities=probs,
                model_name="finbert",
                model_version=None,
                scored_at=now,
            )

    def test_validation_empty_article_id_rejected(self) -> None:
        now = datetime.now(timezone.utc).astimezone(IST)
        with pytest.raises(ValidationError, match="article_id cannot be empty"):
            ArticleSentimentResult(
                article_id="",
                headline="Surge",
                sentiment_label="positive",
                sentiment_score=0.8,
                probabilities={"positive": 0.8, "neutral": 0.1, "negative": 0.1},
                model_name="finbert",
                model_version=None,
                scored_at=now,
            )


class TestArticleTextPreparation:
    """Tests for text preparation and character truncation."""

    def test_prepare_headline_only(self) -> None:
        art = _make_article(
            headline="  Reliance announces multi-gigawatt solar plant  ",
            summary="Huge project.",
        )
        text = prepare_article_text(art, include_summary=False)
        assert text == "Reliance announces multi-gigawatt solar plant"

    def test_prepare_with_summary(self) -> None:
        art = _make_article(
            headline="TCS signs deal",
            summary="10-year digital transformation partnership.",
        )
        text = prepare_article_text(art, include_summary=True)
        assert text == "TCS signs deal. 10-year digital transformation partnership."

    def test_prepare_missing_summary_falls_back_to_headline(self) -> None:
        art = _make_article(headline="HDFC Bank update", summary=None)
        text = prepare_article_text(art, include_summary=True)
        assert text == "HDFC Bank update"

    def test_prepare_empty_headline_raises_validation_error(self) -> None:
        # Construct NewsArticle bypassing __post_init__ or using mock object with empty headline
        class FakeArticle:
            headline = "   "
            summary = "Summary text"
            article_id = "fake_1"

        with pytest.raises(ValidationError, match="has empty or blank headline"):
            prepare_article_text(FakeArticle())  # type: ignore

    def test_prepare_truncation_preserves_word_boundary(self) -> None:
        long_headline = "A " * 300  # 600 characters
        art = _make_article(headline=long_headline, summary=None)
        text = prepare_article_text(art, max_chars=100)
        assert len(text) <= 100
        assert not text.endswith(" ")


class TestFinBERTSentimentScorer:
    """Tests for FinBERTSentimentScorer using MockSentimentBackend (100% offline)."""

    def test_score_single_article_positive(self) -> None:
        mock_backend = MockSentimentBackend()
        scorer = FinBERTSentimentScorer(backend=mock_backend)

        art = _make_article(headline="Tata Motors reports massive quarterly profit growth")
        res = scorer.score_article(art)

        assert res.status == "SUCCESS"
        assert res.sentiment_label == "positive"
        assert res.sentiment_score == 0.85
        assert res.probabilities["positive"] == 0.85
        assert res.probabilities["neutral"] == 0.10
        assert res.probabilities["negative"] == 0.05
        assert res.article_id == art.article_id
        assert res.model_name == "mock-finbert"
        assert res.error_message is None

    def test_score_single_article_negative(self) -> None:
        mock_backend = MockSentimentBackend()
        scorer = FinBERTSentimentScorer(backend=mock_backend)

        art = _make_article(headline="IT bellwether forecasts severe revenue slump and margin drop")
        res = scorer.score_article(art)

        assert res.status == "SUCCESS"
        assert res.sentiment_label == "negative"
        assert res.sentiment_score == 0.80

    def test_batch_scoring_preserves_order_and_ids(self) -> None:
        mock_backend = MockSentimentBackend()
        scorer = FinBERTSentimentScorer(backend=mock_backend)

        articles = [
            _make_article("Stock surge", article_id="art_1"),
            _make_article("Revenue slump", article_id="art_2"),
            _make_article("General corporate notice", article_id="art_3"),
        ]

        results = scorer.score_articles(articles)
        assert len(results) == 3
        assert results[0].article_id == "art_1"
        assert results[0].sentiment_label == "positive"

        assert results[1].article_id == "art_2"
        assert results[1].sentiment_label == "negative"

        assert results[2].article_id == "art_3"
        assert results[2].sentiment_label == "neutral"

    def test_empty_batch_returns_empty_list(self) -> None:
        scorer = FinBERTSentimentScorer(backend=MockSentimentBackend())
        assert scorer.score_articles([]) == []

    def test_inference_failure_produces_error_status_not_false_neutral(self) -> None:
        # Verify that inference exception produces status="ERROR" with error_message, NEVER silent fake neutral
        failing_backend = MockSentimentBackend(simulate_error=RuntimeError("CUDA out of memory"))
        scorer = FinBERTSentimentScorer(backend=failing_backend)

        art = _make_article("Any headline")
        res = scorer.score_article(art)

        assert res.status == "ERROR"
        assert res.sentiment_label is None
        assert res.sentiment_score is None
        assert res.probabilities is None
        assert "Inference error: CUDA out of memory" in (res.error_message or "")
        assert res.article_id == art.article_id

    def test_text_preparation_failure_produces_error_status(self) -> None:
        scorer = FinBERTSentimentScorer(backend=MockSentimentBackend())
        # Article with blank headline
        class BadArticle:
            headline = "   "
            summary = "Text"
            article_id = "bad_art_1"

        res = scorer.score_article(BadArticle())  # type: ignore
        assert res.status == "ERROR"
        assert res.sentiment_label is None
        assert "Text preparation failed" in (res.error_message or "")


class TestFinBERTBackendLazyLoading:
    """Tests for FinBERTBackend lazy-loading semantics and dependency handling."""

    def test_backend_properties_before_loading(self) -> None:
        backend = FinBERTBackend(model_identifier="ProsusAI/finbert", revision="v1")
        assert backend.model_name == "ProsusAI/finbert"
        assert backend.model_version == "v1"
        assert backend._is_loaded is False  # Weights not loaded on initialization


class TestPointInTimeSentimentIntegration:
    """Tests verifying point-in-time eligibility integration with sentiment scoring."""

    def test_sentiment_scoring_on_point_in_time_filtered_articles(self) -> None:
        cutoff = datetime(2026, 10, 15, 12, 0, tzinfo=IST)

        # 3 articles: 2 published before cutoff, 1 after cutoff
        a_past1 = _make_article("Morning growth", article_id="p1", pub_offset_hours=-3)
        a_past2 = _make_article("Midday update", article_id="p2", pub_offset_hours=-1)
        a_future = _make_article("Evening results", article_id="f1", pub_offset_hours=+4)

        # Filter point-in-time
        eligible = filter_news_point_in_time([a_past1, a_past2, a_future], as_of_time=cutoff)
        assert len(eligible) == 2
        assert a_future not in eligible

        # Score only eligible articles
        scorer = FinBERTSentimentScorer(backend=MockSentimentBackend())
        results = scorer.score_articles(eligible)

        assert len(results) == 2
        scored_ids = {r.article_id for r in results}
        assert scored_ids == {"p1", "p2"}
        assert "f1" not in scored_ids
