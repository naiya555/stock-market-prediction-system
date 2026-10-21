"""Comprehensive Unit and Integration Tests for Evidence-Grounded LLM Context (Day 55).

Tests cover:
- Point-in-time filtering and cutoff enforcement.
- Source provenance preservation (headlines, orgs, URLs, IDs, timestamps).
- Empty context handling (NO_CONTEXT status without hallucination).
- Disabled LLM configuration handling (DISABLED status).
- Model unavailable and timeout behavior (UNAVAILABLE, TIMEOUT).
- Malformed and adversarial LLM output handling (FAILED).
- Numerical prediction immutability under adversarial LLM payloads.
- Quantitative-only fallback in ensemble prediction.
- Supporting evidence citation validation against provided records.
- Public API schema compatibility on /api/predict endpoint.
"""

from datetime import datetime, timedelta, timezone
import json
from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient

from app.api.app import app
from app.events.schemas import EventCategory, MacroEvent, StructuredEventValue
from app.llm.client import (
    LLMClientError,
    LLMModelUnavailableError,
    MockLLMClient,
)
from app.llm.prompts import build_prediction_explanation_prompt
from app.llm.schemas import (
    LLMDirection,
    LLMExplanationResult,
    LLMExplanationStatus,
    LLMReasoningResult,
)
from app.llm.service import LLMService, _validate_supporting_evidence
from app.news.schemas import NewsArticle
from app.prediction.contract import (
    PredictionDataQuality,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
)
from app.prediction.ensemble import (
    EnsembleAgreement,
    EnsemblePredictionResult,
    EnsembleService,
    EnsembleWeights,
)


# ==============================================================================
# Fixtures and Helpers
# ==============================================================================

@pytest.fixture
def sample_cutoff() -> datetime:
    return datetime(2026, 10, 20, 15, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_news(sample_cutoff: datetime) -> List[NewsArticle]:
    t1 = sample_cutoff - timedelta(hours=2)
    t2 = sample_cutoff - timedelta(days=1)
    return [
        NewsArticle(
            headline="Bharti Airtel signs major enterprise telecom pact with global cloud provider",
            source="The Economic Times",
            published_at=t1,
            ingested_at=t1,
            symbols=("BHARTIARTL",),
            url="https://economictimes.indiatimes.com/airtel-enterprise-deal",
            summary="Multi-year agreement will deliver hybrid cloud connectivity across Indian data centers.",
            provider="moneycontrol",
            article_id="art-airtel-101",
        ),
        NewsArticle(
            headline="Telecom sector revenue expands 12% on higher blended tariffs",
            source="Reuters",
            published_at=t2,
            ingested_at=t2,
            symbols=("BHARTIARTL", "JIO"),
            url="https://reuters.com/india-telecom-revenue-growth",
            summary="Industry ARPU showed consistent quarterly expansion across both prepaid and postpaid cohorts.",
            provider="reuters",
            article_id="art-telecom-102",
        ),
    ]


@pytest.fixture
def sample_events(sample_cutoff: datetime) -> List[MacroEvent]:
    t1 = sample_cutoff - timedelta(days=2)
    return [
        MacroEvent(
            title="TRAI releases recommendations on satcom spectrum pricing and license terms",
            category=EventCategory.REGULATORY,
            event_type="consultation_paper",
            source_org="TRAI",
            ingested_at=t1,
            published_at=t1,
            effective_at=t1,
            url="https://trai.gov.in/releases/satcom-spectrum-terms",
            summary="Regulator proposed administrative allocation with annual revenue-linked fees.",
            affected_symbols=("BHARTIARTL",),
            structured_value=StructuredEventValue(
                metric_name="license_fee_pct",
                value=4.0,
                unit="pct",
            ),
            event_id="ev-trai-201",
        )
    ]


@pytest.fixture
def mock_ml_result() -> PredictionResult:
    return PredictionResult(
        symbol="BHARTIARTL",
        prediction_timestamp="2026-10-20T15:30:00+00:00",
        latest_input_timestamp="2026-10-20",
        status=PredictionStatus.SUCCESS,
        predicted_direction="UP",
        predicted_label=1,
        probability_up=0.6420,
        probability_down=0.3580,
        model_name="xgboost",
        model_version="xgboost_v1",
        model_metadata={"algorithm": "xgboost", "test": True},
        data_quality=PredictionDataQuality(
            total_bars_fetched=100,
            cleaned_bars=100,
            warmup_bars_required=34,
            warmup_complete=True,
            latest_bar_timestamp="2026-10-20",
            missing_feature_count=0,
            missing_features=[],
            is_stale=False,
            stale_days=0,
        ),
    )


# ==============================================================================
# 1. Point-in-Time Filtering and Provenance Preservation Tests
# ==============================================================================

class TestContextFilteringAndProvenance:
    """Test temporal point-in-time invariants and provenance preservation."""

    def test_future_news_and_events_are_strictly_excluded(
        self,
        sample_cutoff: datetime,
        sample_news: List[NewsArticle],
        sample_events: List[MacroEvent],
    ) -> None:
        """Articles published after cutoff timestamp must be filtered out."""
        future_time = sample_cutoff + timedelta(hours=3)
        future_article = NewsArticle(
            headline="Future announcement that should not leak",
            source="Leaked News",
            published_at=future_time,
            ingested_at=future_time,
            symbols=("BHARTIARTL",),
            url="https://leak.example.com",
            article_id="future-art",
        )
        future_event = MacroEvent(
            title="Future SEBI circular",
            category=EventCategory.REGULATORY,
            event_type="circular",
            source_org="SEBI",
            ingested_at=future_time,
            published_at=future_time,
            url="https://sebi.gov.in/future",
            event_id="future-ev",
        )

        all_news = list(sample_news) + [future_article]
        all_events = list(sample_events) + [future_event]

        # Use mock client to inspect assembled prompt
        mock_client = MockLLMClient(
            default_response=json.dumps({
                "summary": "Valid test explanation",
                "supporting_evidence": ["Citing [News 1] (The Economic Times): valid point"],
                "limitations": [],
                "direction": "UP",
                "confidence": "MEDIUM",
            })
        )
        service = LLMService(client=mock_client)

        result = service.explain_prediction(
            symbol="BHARTIARTL",
            articles=all_news,
            events=all_events,
            cutoff_time=sample_cutoff,
        )

        assert result.status == LLMExplanationStatus.SUCCESS
        # Inspect captured prompt in mock client
        prompt_text = mock_client.calls[0]["prompt"]
        assert "Future announcement" not in prompt_text
        assert "future-art" not in prompt_text
        assert "Future SEBI circular" not in prompt_text
        assert "future-ev" not in prompt_text
        # Legitimate point-in-time items must be present
        assert "Bharti Airtel signs major enterprise telecom pact" in prompt_text
        assert "TRAI releases recommendations" in prompt_text

    def test_provenance_fields_preserved_in_prompt(
        self,
        sample_news: List[NewsArticle],
        sample_events: List[MacroEvent],
    ) -> None:
        """Provenance (URLs, source org, article ID, publication time) must be preserved in prompt."""
        _, prompt, known_prov = build_prediction_explanation_prompt(
            symbol="BHARTIARTL",
            articles=sample_news,
            events=sample_events,
        )

        # News provenance
        assert "Source: The Economic Times" in prompt
        assert "URL: https://economictimes.indiatimes.com/airtel-enterprise-deal" in prompt
        assert "ID: art-airtel-101" in prompt
        assert "UTC" in prompt

        # Event provenance
        assert "Source: TRAI" in prompt
        assert "Category: regulatory" in prompt
        assert "URL: https://trai.gov.in/releases/satcom-spectrum-terms" in prompt
        assert "Metric: license_fee_pct=4.0 pct" in prompt

        # Provenance map must capture tags and source names
        assert "[news 1]" in known_provenance_clean(known_prov)
        assert "trai" in known_provenance_clean(known_prov)

    def test_probability_formatting_for_up_and_down_predictions(
        self,
        sample_news: List[NewsArticle],
    ) -> None:
        """P(UP) must strictly denote upward probability for both UP and DOWN predictions."""
        # 1. UP prediction: probability_up = 0.584
        _, prompt_up, _ = build_prediction_explanation_prompt(
            symbol="BHARTIARTL",
            articles=sample_news,
            quantitative_direction="UP",
            quantitative_probability=0.584,
            quantitative_probability_down=0.416,
        )
        assert "Authoritative Quantitative ML Baseline Forecast: UP [P(UP)=58.4%]." in prompt_up

        # 2. DOWN prediction: probability_up = 0.469, probability_down = 0.531
        _, prompt_down, _ = build_prediction_explanation_prompt(
            symbol="BHARTIARTL",
            articles=sample_news,
            quantitative_direction="DOWN",
            quantitative_probability=0.469,
            quantitative_probability_down=0.531,
        )
        assert "Authoritative Quantitative ML Baseline Forecast: DOWN [P(DOWN)=53.1%, P(UP)=46.9%]." in prompt_down
        # P(UP) must NOT be mislabeled as 53.1%
        assert "P(UP)=53.1%" not in prompt_down


def known_provenance_clean(prov_map: Dict[str, str]) -> List[str]:
    return [k.lower() for k in prov_map.keys()]


# ==============================================================================
# 2. Empty Context and Status Handling Tests
# ==============================================================================

class TestExplanationStatusContracts:
    """Test contracts for NO_CONTEXT, DISABLED, UNAVAILABLE, TIMEOUT, and FAILED."""

    def test_empty_context_returns_no_context_status(self) -> None:
        """When no articles or events are supplied, service returns NO_CONTEXT without hallucinating."""
        client = MockLLMClient()
        service = LLMService(client=client)

        result = service.explain_prediction(
            symbol="BHARTIARTL",
            articles=[],
            events=[],
        )

        assert result.status == LLMExplanationStatus.NO_CONTEXT
        assert result.direction == LLMDirection.INSUFFICIENT_EVIDENCE.value
        assert result.confidence == "LOW"
        assert len(result.supporting_evidence) == 0
        assert len(result.limitations) > 0
        assert len(client.calls) == 0  # Zero network or LLM calls made

    def test_disabled_llm_returns_disabled_status(
        self,
        sample_news: List[NewsArticle],
    ) -> None:
        """When OLLAMA_ENABLED=False or enabled=False, returns DISABLED without raising."""
        client = MockLLMClient(enabled=False)
        service = LLMService(client=client)

        result = service.explain_prediction(
            symbol="BHARTIARTL",
            articles=sample_news,
        )

        assert result.status == LLMExplanationStatus.DISABLED
        assert "disabled by configuration" in result.summary.lower()
        assert len(client.calls) == 0

    def test_model_unavailable_returns_unavailable_status(
        self,
        sample_news: List[NewsArticle],
    ) -> None:
        """When target model is not in Ollama tags, returns UNAVAILABLE."""
        client = MockLLMClient(simulated_error=LLMModelUnavailableError("Model 'gemma3:12b' not found"))
        service = LLMService(client=client)

        result = service.explain_prediction(
            symbol="BHARTIARTL",
            articles=sample_news,
        )

        assert result.status == LLMExplanationStatus.UNAVAILABLE
        assert "unavailable" in result.summary.lower()

    def test_timeout_returns_timeout_status(
        self,
        sample_news: List[NewsArticle],
    ) -> None:
        """When client times out, returns TIMEOUT status with clear limitation."""
        client = MockLLMClient(simulated_error=LLMClientError("Request timed out after 30.0 seconds"))
        service = LLMService(client=client)

        result = service.explain_prediction(
            symbol="BHARTIARTL",
            articles=sample_news,
        )

        assert result.status == LLMExplanationStatus.TIMEOUT
        assert "timed out" in result.summary.lower()
        assert any("timeout" in l.lower() for l in result.limitations)

    def test_malformed_json_returns_failed_status(
        self,
        sample_news: List[NewsArticle],
    ) -> None:
        """When LLM returns corrupted or non-JSON output, returns FAILED status."""
        client = MockLLMClient(default_response="This is plain text with no JSON object.")
        service = LLMService(client=client)

        result = service.explain_prediction(
            symbol="BHARTIARTL",
            articles=sample_news,
        )

        assert result.status == LLMExplanationStatus.FAILED
        assert any("json" in l.lower() for l in result.limitations)


# ==============================================================================
# 3. Supporting Evidence Verification Tests
# ==============================================================================

class TestSupportingEvidenceVerification:
    """Test validation of supporting evidence citations against provided context."""

    def test_unverified_invented_sources_are_flagged(self) -> None:
        """Citations that reference invented or unsupplied sources are moved to limitations."""
        known_prov = {
            "[news 1]": "The Economic Times",
            "the economic times": "[News 1]",
            "[event 1]": "TRAI",
            "trai": "[Event 1]",
        }

        raw_evidence = [
            "Citing [News 1] (The Economic Times): ARPU improved by 14%",
            "Citing Wall Street Journal: Major secret restructuring underway",  # Invented
            "Citing [Event 1] (TRAI): Satcom fee proposed at 4%",
        ]

        verified, unverified = _validate_supporting_evidence(raw_evidence, known_prov)

        assert len(verified) == 2
        assert "ARPU improved by 14%" in verified[0]
        assert "Satcom fee proposed at 4%" in verified[1]
        assert len(unverified) == 1
        assert "Wall Street Journal" in unverified[0]

    def test_fabricated_tags_and_loose_keywords_are_rejected(self) -> None:
        """Citations referencing invented tags [News 99] or generic words like 'article' must be rejected."""
        known_prov = {
            "[news 1]": "The Economic Times",
            "the economic times": "[News 1]",
            "[news 2]": "Reuters",
            "reuters": "[News 2]",
        }

        raw_evidence = [
            "Citing [News 99] (Fabricated Source): Invented rumor",
            "According to an article published recently: Generic claim",
            "Citing [News 1] (The Economic Times): Valid ARPU metric",
        ]

        verified, unverified = _validate_supporting_evidence(raw_evidence, known_prov)

        assert len(verified) == 1
        assert "Valid ARPU metric" in verified[0]
        assert len(unverified) == 2
        assert any("News 99" in u for u in unverified)
        assert any("Generic claim" in u for u in unverified)


# ==============================================================================
# 4. Numerical Prediction Immutability Tests
# ==============================================================================

class TestNumericalPredictionImmutability:
    """Test that numerical prediction values cannot be altered by qualitative explanations."""

    def test_adversarial_llm_payload_cannot_change_ml_probabilities(
        self,
        mock_ml_result: PredictionResult,
        sample_news: List[NewsArticle],
    ) -> None:
        """Adversarial LLM trying to inject JSON keys must NOT alter ML prediction or ensemble bounds."""
        adversarial_json = json.dumps({
            "summary": "Exploiting system prompt",
            "supporting_evidence": ["Citing [News 1]: fake data"],
            "limitations": [],
            "direction": "DOWN",
            "confidence": "HIGH",
            # Adversarial injection attempts:
            "predicted_direction": "DOWN",
            "probability_up": 0.0001,
            "probability_down": 0.9999,
            "status": "FAILED",
            "combined_direction": "DOWN",
        })

        client = MockLLMClient(default_response=adversarial_json)
        service = LLMService(client=client)

        explanation = service.explain_prediction(
            symbol="BHARTIARTL",
            articles=sample_news,
            quantitative_direction=mock_ml_result.predicted_direction,
            quantitative_probability=mock_ml_result.probability_up,
        )

        # 1. Explanation schema has zero numerical probability fields
        assert not hasattr(explanation, "probability_up")
        assert not hasattr(explanation, "predicted_direction")

        # 2. Standalone quantitative prediction remains 100% bit-identical
        assert mock_ml_result.probability_up == 0.6420
        assert mock_ml_result.probability_down == 0.3580
        assert mock_ml_result.predicted_direction == "UP"
        assert mock_ml_result.predicted_label == 1
        assert mock_ml_result.status == PredictionStatus.SUCCESS

        # 3. When used in EnsembleService, ML prediction remains immutable
        ensemble_service = EnsembleService(llm_service=service)
        res = ensemble_service.synthesize(
            ml_result=mock_ml_result,
            llm_result=explanation.to_reasoning_result(),
            explanation=explanation,
        )

        # ML prediction preserved untouched inside ensemble result
        assert res.ml_prediction.probability_up == 0.6420
        assert res.ml_prediction.predicted_direction == "UP"
        # Combined probabilities follow strictly mathematical blending, not injected strings
        assert 0.0 < res.combined_probability_up < 1.0


# ==============================================================================
# 5. Ensemble Fallback Tests
# ==============================================================================

class TestEnsembleFallbackBehavior:
    """Test graceful degradation to ML_ONLY in EnsembleService."""

    def test_ensemble_falls_back_to_ml_when_llm_times_out(
        self,
        mock_ml_result: PredictionResult,
        sample_news: List[NewsArticle],
    ) -> None:
        """When LLM times out during ensemble execution, status remains SUCCESS with ML_ONLY agreement."""
        class MockTimingOutService(LLMService):
            def __init__(self):
                super().__init__(client=MockLLMClient())

            def explain_prediction(self, *args, **kwargs):
                return LLMExplanationResult.timeout(symbol="BHARTIARTL")

        class MockPredService:
            def predict(self, *args, **kwargs):
                return mock_ml_result

        ensemble = EnsembleService(
            prediction_service=MockPredService(),
            llm_service=MockTimingOutService(),
        )

        req = PredictionRequest(symbol="BHARTIARTL", model_name="xgboost")
        res = ensemble.predict_ensemble(request=req, articles=sample_news, persist=False)

        assert res.status == PredictionStatus.SUCCESS
        assert res.agreement_status == EnsembleAgreement.ML_ONLY
        assert res.combined_direction == "UP"
        assert res.combined_probability_up == mock_ml_result.probability_up
        assert res.weights_used["ml"] == 1.0
        assert res.weights_used["llm"] == 0.0
        assert res.explanation is not None
        assert res.explanation.status == LLMExplanationStatus.TIMEOUT


# ==============================================================================
# 6. Evidence Classification Tests
# ==============================================================================

class TestEvidenceClassification:
    """Test classification of evidence into positive, negative, and neutral items."""

    def test_unclassified_neutral_evidence_not_converted_to_positive_factors(self) -> None:
        """Neutral or unclassified evidence must remain in source_references and not become positive_factors."""
        exp = LLMExplanationResult(
            status=LLMExplanationStatus.SUCCESS,
            summary="Operational update",
            supporting_evidence=(
                "Citing [News 1]: Company scheduled general meeting for next Tuesday",
                "Citing [News 2]: High quarterly growth and subscriber expansion observed",
                "Citing [Event 1]: Severe regulatory penalty and margin decline warned",
            ),
            limitations=("Macro uncertainty",),
            model="mock-gemma3:12b",
            generated_at="2026-10-22T01:00:00+00:00",
            symbol="BHARTIARTL",
            direction="UP",
            confidence="MEDIUM",
        )

        reasoning = exp.to_reasoning_result()

        # Positive factor must only contain the bullish item
        assert len(reasoning.positive_factors) == 1
        assert "growth and subscriber expansion" in reasoning.positive_factors[0]

        # Negative factor must only contain the bearish item
        assert len(reasoning.negative_factors) == 1
        assert "regulatory penalty" in reasoning.negative_factors[0]

        # Neutral item must NOT be in positive_factors
        assert not any("general meeting" in p for p in reasoning.positive_factors)
        # All items must be present in source_references
        assert len(reasoning.source_references) == 3

    def test_down_prediction_unclassified_evidence_never_bullish(self) -> None:
        """When direction is DOWN, neutral evidence must never be coerced into positive_factors."""
        exp = LLMExplanationResult(
            status=LLMExplanationStatus.SUCCESS,
            summary="Bearish context",
            supporting_evidence=(
                "Citing [News 1]: Routine quarterly filing submitted on Friday",
            ),
            limitations=("Capex strain",),
            model="mock-gemma3:12b",
            generated_at="2026-10-22T01:00:00+00:00",
            symbol="BHARTIARTL",
            direction="DOWN",
            confidence="HIGH",
        )

        reasoning = exp.to_reasoning_result()
        assert len(reasoning.positive_factors) == 0
        assert reasoning.direction == LLMDirection.DOWN


# ==============================================================================
# 7. Public API Compatibility & Sanitization Tests (Isolated)
# ==============================================================================

class TestPredictAPIPublicResponse:
    """Test that /api/predict correctly sanitizes, bounds, and returns explanation structures."""

    def test_api_sanitization_and_bounding_of_untrusted_llm_output(self) -> None:
        """Untrusted HTML and oversized text must be escaped and bounded by API mapping."""
        from app.api.routes.predict import _map_llm_explanation

        malicious_exp = LLMExplanationResult(
            status=LLMExplanationStatus.SUCCESS,
            summary="<script>alert('xss')</script> Safe text " + ("A" * 3000),
            supporting_evidence=("<img src=x onerror=alert(1)>", "Valid evidence"),
            limitations=("<b>Bold Warning</b>",),
            model="mock-model",
            generated_at="2026-10-22T01:00:00+00:00",
            symbol="BHARTIARTL",
            direction="UP",
            confidence="MEDIUM",
        )

        mapped = _map_llm_explanation(malicious_exp)
        assert mapped is not None
        assert "<script>" not in mapped.summary
        assert "&lt;script&gt;" in mapped.summary
        assert "[truncated]" in mapped.summary
        assert len(mapped.summary) <= 2050
        assert "<img" not in mapped.supporting_evidence[0]
        assert "&lt;img" in mapped.supporting_evidence[0]
        assert "<b>" not in mapped.limitations[0]
        assert "&lt;b&gt;" in mapped.limitations[0]

    def test_api_predict_ensemble_includes_explanation_isolated(
        self,
        mock_ml_result: PredictionResult,
    ) -> None:
        """API response must conform to PredictionResponse with explanation fields using isolated mock."""
        from app.api.dependencies import get_ensemble_service

        mock_exp = LLMExplanationResult(
            status=LLMExplanationStatus.SUCCESS,
            summary="Verified enterprise contract expansion supports telecom cash flow.",
            supporting_evidence=("Citing [News 1]: Enterprise contract signed",),
            limitations=("Execution timeline pending",),
            model="mock-gemma3:12b",
            generated_at="2026-10-22T01:00:00+00:00",
            symbol="BHARTIARTL",
            direction="UP",
            confidence="MEDIUM",
        )

        mock_ensemble_res = EnsemblePredictionResult(
            symbol="BHARTIARTL",
            prediction_timestamp="2026-10-22T01:00:00+00:00",
            latest_input_timestamp=mock_ml_result.latest_input_timestamp,
            status=PredictionStatus.SUCCESS,
            combined_direction="UP",
            combined_label=1,
            combined_probability_up=0.5840,
            combined_probability_down=0.4160,
            agreement_status=EnsembleAgreement.ML_ONLY,
            weights_used={"ml": 1.0, "llm": 0.0},
            ml_prediction=mock_ml_result,
            llm_reasoning=None,
            explanation=mock_exp,
        )

        class IsolatedMockEnsembleService:
            def predict_ensemble(self, *args, **kwargs):
                return mock_ensemble_res

        app.dependency_overrides[get_ensemble_service] = lambda: IsolatedMockEnsembleService()
        try:
            client = TestClient(app)
            response = client.post(
                "/api/predict",
                json={
                    "symbol": "BHARTIARTL",
                    "model_name": "ensemble",
                    "persist": False,
                    "allow_stale_data": True,
                },
            )
            assert response.status_code == 200
            data = response.json()

            assert "explanation" in data
            assert data["explanation"] is not None
            exp = data["explanation"]
            assert exp["status"] == "SUCCESS"
            assert exp["summary"] == "Verified enterprise contract expansion supports telecom cash flow."
            assert "supporting_evidence" in exp
            assert len(exp["supporting_evidence"]) == 1
            assert "limitations" in exp
            assert exp["model"] == "mock-gemma3:12b"
            assert data["probability_up"] == 0.5840
            assert data["predicted_direction"] == "UP"
        finally:
            app.dependency_overrides.pop(get_ensemble_service, None)
