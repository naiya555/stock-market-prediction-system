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


# ==============================================================================
# 8. Day 57 Review Findings Regression Tests
# ==============================================================================

class TestFindingAHTMLEscapingAndTruncationOrder:
    """Tests for Finding A: escape-then-truncate order, bound enforcement, and entity integrity."""

    def test_sanitize_and_bound_html_entities_and_length(self) -> None:
        """HTML special chars are properly escaped and final string strictly respects max_length."""
        from app.api.routes.predict import _sanitize_and_bound_text

        # Special chars
        raw = "<script>alert('xss') & \"quotes\"</script>"
        res = _sanitize_and_bound_text(raw, max_length=100)
        assert "<" not in res
        assert ">" not in res
        assert "&lt;script&gt;" in res
        assert "&amp;" in res
        assert "&quot;" in res

    def test_escaping_expansion_never_exceeds_max_length(self) -> None:
        """Expansion due to HTML escaping must strictly stay within max_length without entity cutting."""
        from app.api.routes.predict import _sanitize_and_bound_text

        # String of 50 '<' chars; escaped length is 50 * 4 = 200 chars
        raw = "<" * 50
        res = _sanitize_and_bound_text(raw, max_length=30)
        assert len(res) <= 30
        assert res.endswith(" [truncated]")
        # Must not end with a partial entity like '&l' or '&lt' before suffix
        prefix = res.replace(" [truncated]", "")
        assert not prefix.endswith("&")
        assert not prefix.endswith("&l")
        assert not prefix.endswith("&lt")

    def test_entity_boundary_not_sliced_in_half(self) -> None:
        """Truncation must never leave a dangling, cut-off HTML entity."""
        from app.api.routes.predict import _sanitize_and_bound_text

        # Exactly position an entity near the truncation budget
        # Budget for max_length=20 with suffix len 12 is 8
        # "Hello " (6 chars) + "&quot;" (6 chars)
        raw = 'Hello "world"'
        res = _sanitize_and_bound_text(raw, max_length=20)
        assert len(res) <= 20
        # Should drop the incomplete '&quot;' rather than producing 'Hello &qu [truncated]'
        assert "&qu [" not in res
        assert "&quo [" not in res
        assert "&quot; [" not in res or len(res) <= 20

    def test_control_characters_and_malformed_values_sanitized(self) -> None:
        """Null bytes, control codes, None, and non-strings handled safely."""
        from app.api.routes.predict import _sanitize_and_bound_text, _sanitize_and_bound_string_list

        assert _sanitize_and_bound_text(None) == ""
        assert _sanitize_and_bound_text(12345) == "12345"
        assert _sanitize_and_bound_text("Good\x00\x08Text\x1b") == "GoodText"
        assert _sanitize_and_bound_text("Line1\nLine2\tTab") == "Line1\nLine2\tTab"

        # List with non-string and malformed elements
        raw_list = ["valid", 999, None, {"text": "dict content"}, ""]
        clean_list = _sanitize_and_bound_string_list(raw_list, max_items=10, max_item_length=100)
        assert len(clean_list) == 3
        assert clean_list[0] == "valid"
        assert clean_list[1] == "999"
        assert clean_list[2] == "dict content"


class TestFindingBExactModelTagMatching:
    """Tests for Finding B: exact model tag matching and residency checks."""

    def test_match_model_tag_rules(self) -> None:
        """Verify strict matching rules under Ollama contract."""
        from app.llm.client import _match_model_tag

        # Exact matches
        assert _match_model_tag("gemma3:12b", "gemma3:12b") is True
        assert _match_model_tag("GEMMA3:12B", "gemma3:12b") is True
        assert _match_model_tag("library/gemma3:12b", "gemma3:12b") is True

        # Canonical default tag ':latest'
        assert _match_model_tag("gemma3", "gemma3:latest") is True
        assert _match_model_tag("gemma3:latest", "gemma3") is True

        # Rejection of unsafe substring matching
        assert _match_model_tag("gemma3:12b-instruct", "gemma3:12b") is False
        assert _match_model_tag("gemma3:12b", "gemma3:12b-instruct") is False
        assert _match_model_tag("gemma3:8b", "gemma3:12b") is False
        assert _match_model_tag("gemma3", "gemma3-other") is False
        assert _match_model_tag("", "gemma3:12b") is False
        assert _match_model_tag("gemma3:12b", "") is False

    def test_check_model_residency_scenarios(self) -> None:
        """Verify check_model_residency handles all Ollama /api/ps responses deterministically."""
        from app.llm.client import OllamaLLMClient

        class DummyResponse:
            def __init__(self, status: int, data: bytes):
                self.status = status
                self._data = data

            def read(self) -> bytes:
                return self._data

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        # 1. Exact match resident -> True
        def opener_match(req, timeout):
            return DummyResponse(200, json.dumps({"models": [{"name": "gemma3:12b"}]}).encode())

        c1 = OllamaLLMClient(model_name="gemma3:12b", http_opener=opener_match)
        assert c1.check_model_residency() is True

        # 2. Similar prefix but different tag -> False (not resident)
        def opener_prefix(req, timeout):
            return DummyResponse(200, json.dumps({"models": [{"name": "gemma3:12b-instruct"}]}).encode())

        c2 = OllamaLLMClient(model_name="gemma3:12b", http_opener=opener_prefix)
        assert c2.check_model_residency() is False

        # 3. Empty resident model list -> False
        def opener_empty(req, timeout):
            return DummyResponse(200, json.dumps({"models": []}).encode())

        c3 = OllamaLLMClient(model_name="gemma3:12b", http_opener=opener_empty)
        assert c3.check_model_residency() is False

        # 4. Multiple resident models (one matching) -> True
        def opener_multi(req, timeout):
            return DummyResponse(
                200,
                json.dumps({"models": [{"name": "qwen:7b"}, {"name": "gemma3:12b"}]}).encode(),
            )

        c4 = OllamaLLMClient(model_name="gemma3:12b", http_opener=opener_multi)
        assert c4.check_model_residency() is True

        # 5. HTTP Error -> None (unknown)
        def opener_err(req, timeout):
            return DummyResponse(500, b"Internal server error")

        c5 = OllamaLLMClient(model_name="gemma3:12b", http_opener=opener_err)
        assert c5.check_model_residency() is None

        # 6. Malformed JSON -> None (unknown)
        def opener_bad_json(req, timeout):
            return DummyResponse(200, b"not json")

        c6 = OllamaLLMClient(model_name="gemma3:12b", http_opener=opener_bad_json)
        assert c6.check_model_residency() is None


class TestFindingCCitationWordBoundaryValidation:
    """Tests for Finding C: boundary-aware citation matching."""

    def test_n1_versus_n10_boundary_matching(self) -> None:
        """[N1] in context must NOT validate [N10] or [News 10]."""
        from app.llm.service import _validate_supporting_evidence

        provenance = {
            "[news 1]": "Reuters",
            "[n1]": "Reuters",
        }

        # Valid [News 1]
        v1, n1 = _validate_supporting_evidence(["According to [News 1], profit grew 15%."], provenance)
        assert len(v1) == 1
        assert len(n1) == 0

        # Valid [N1]
        v2, n2 = _validate_supporting_evidence(["According to [N1], profit grew 15%."], provenance)
        assert len(v2) == 1
        assert len(n2) == 0

        # Invalid [News 10]
        v3, n3 = _validate_supporting_evidence(["According to [News 10], margin expanded."], provenance)
        assert len(v3) == 0
        assert len(n3) == 1
        assert "tag [news 10] not in context" in n3[0].lower()

        # Invalid [N10]
        v4, n4 = _validate_supporting_evidence(["According to [N10], margin expanded."], provenance)
        assert len(v4) == 0
        assert len(n4) == 1
        assert "not in context" in n4[0]

    def test_explicit_source_ids_and_boundary(self) -> None:
        """Article IDs with digits and underscores require word boundaries."""
        from app.llm.service import _validate_supporting_evidence

        provenance = {
            "art_101": "Economic Times",
            "ev_regulatory_1": "TRAI",
        }

        # Valid exact ID
        v1, n1 = _validate_supporting_evidence(["Per art_101, tariff increased."], provenance)
        assert len(v1) == 1

        # Superstring of ID art_1010 must not be matched by art_101
        v2, n2 = _validate_supporting_evidence(["Per art_1010, tariff increased."], provenance)
        assert len(v2) == 0
        assert len(n2) == 1

        # Valid ID with underscores
        v3, n3 = _validate_supporting_evidence(["Confirmed in ev_regulatory_1 announcement."], provenance)
        assert len(v3) == 1

    def test_generic_publisher_names_cannot_ground_ungrounded_claims(self) -> None:
        """Generic words ('article', 'report') or bare publisher names alone cannot ground claims."""
        from app.llm.service import _validate_supporting_evidence

        provenance = {
            "[news 1]": "Reuters",
            "[n1]": "Reuters",
        }

        # Claim mentioning publisher name without valid tag/ID
        v, n = _validate_supporting_evidence(["Reuters reported that inflation softened."], provenance)
        assert len(v) == 0
        assert len(n) == 1

    def test_multiple_citations_and_punctuation(self) -> None:
        """Multiple citations in one sentence and adjacent punctuation handled correctly."""
        from app.llm.service import _validate_supporting_evidence

        provenance = {
            "[news 1]": "Reuters",
            "[event 1]": "RBI",
        }

        # Multiple valid tags with adjacent punctuation
        item = "Synthesis indicates recovery ([News 1]), in line with monetary policy ([Event 1])."
        v1, n1 = _validate_supporting_evidence([item], provenance)
        assert len(v1) == 1

        # One valid, one invalid tag in single sentence -> rejected
        mixed = "Based on [News 1] and [News 99], outlook improved."
        v2, n2 = _validate_supporting_evidence([mixed], provenance)
        assert len(v2) == 0
        assert len(n2) == 1
        assert "[News 99]" in n2[0]


class TestFindingDCustomEnsembleWeights:
    """Tests for Finding D: custom ensemble weights, validation, and immutability."""

    def test_custom_weights_applied_in_prediction(
        self,
        sample_news: List[NewsArticle],
        mock_ml_result: PredictionResult,
    ) -> None:
        """Custom ml_weight and llm_weight are respected during ensemble synthesis."""
        class MockLLMServiceForWeights:
            def __init__(self):
                self.client = MockLLMClient()

            def generate_qualitative_reasoning(self, symbol, articles, events):
                return LLMReasoningResult(
                    symbol=symbol,
                    direction=LLMDirection.UP,
                    reasoning_summary="Positive enterprise expansion",
                    confidence_assessment="HIGH",
                    positive_factors=("Strong contract",),
                    negative_factors=(),
                    downside_risks=(),
                    source_references=("[News 1]",),
                    model_version="mock-gemma3:12b",
                    generated_at=datetime.now(timezone.utc),
                )

            def explain_prediction(self, **kwargs):
                return LLMExplanationResult(
                    status=LLMExplanationStatus.SUCCESS,
                    summary="Explained",
                    supporting_evidence=("Citing [News 1]: contract",),
                    limitations=(),
                    model="mock-gemma3:12b",
                    generated_at=datetime.now(timezone.utc).isoformat(),
                    symbol=kwargs.get("symbol", "BHARTIARTL"),
                )

        service = EnsembleService(
            prediction_service=None,
            llm_service=MockLLMServiceForWeights(),
            repository=None,
        )

        req = PredictionRequest(symbol="BHARTIARTL", model_name="xgboost")
        custom_w = EnsembleWeights(ml_weight=0.85, llm_weight=0.15)

        # Base ML up is 0.642. LLM is UP with HIGH conf -> polarity +1.0 -> p_llm_up = 1.0
        # Expected combined: 0.85 * 0.642 + 0.15 * 1.0 = 0.5457 + 0.15 = 0.6957
        res = service.synthesize(
            ml_result=mock_ml_result,
            llm_result=MockLLMServiceForWeights().generate_qualitative_reasoning("BHARTIARTL", sample_news, []),
            weights=custom_w,
        )

        assert res.weights_used["ml"] == 0.85
        assert res.weights_used["llm"] == 0.15
        assert abs(res.combined_probability_up - 0.6957) < 0.001

    def test_zero_llm_weight_forces_ml_only_immutability(
        self,
        mock_ml_result: PredictionResult,
    ) -> None:
        """Zero llm_weight forces strict ML_ONLY immutability."""
        service = EnsembleService(prediction_service=None, llm_service=None, repository=None)
        zero_llm = EnsembleWeights(ml_weight=1.0, llm_weight=0.0)

        res = service.synthesize(
            ml_result=mock_ml_result,
            llm_result=None,
            weights=zero_llm,
        )
        assert res.weights_used == {"ml": 1.0, "llm": 0.0}
        assert res.combined_probability_up == mock_ml_result.probability_up
        assert res.agreement_status == EnsembleAgreement.ML_ONLY


class TestEnsemblePredictionResultConstructorContract:
    """Tests verifying EnsemblePredictionResult construction contracts and defaults."""

    def test_constructor_with_minimal_required_fields(
        self,
        mock_ml_result: PredictionResult,
    ) -> None:
        """Instantiating EnsemblePredictionResult with minimal fields succeeds without TypeError."""
        result = EnsemblePredictionResult(
            symbol="BHARTIARTL",
            prediction_timestamp="2026-10-22T01:00:00+00:00",
            status=PredictionStatus.SUCCESS,
            combined_direction="UP",
            combined_label=1,
            combined_probability_up=0.60,
            combined_probability_down=0.40,
            agreement_status=EnsembleAgreement.ML_ONLY,
            weights_used={"ml": 1.0, "llm": 0.0},
            ml_prediction=mock_ml_result,
        )

        assert result.symbol == "BHARTIARTL"
        assert result.latest_input_timestamp is None
        assert result.llm_reasoning is None
        assert result.sentiment_summary is None
        assert result.explanation is None
        assert result.target_range is None
        assert result.model_name == "ensemble"
        assert result.model_version == "ensemble_v1"
