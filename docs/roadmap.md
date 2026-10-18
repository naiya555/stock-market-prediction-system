# Long-Term Project Roadmap

This roadmap outlines the planned multi-phase evolution of the Indian Stock Market Prediction System. Development proceeds incrementally across sequential phases. Future phases must not be implemented prematurely.

---

## Roadmap Overview

| Phase | Title | Description | Target Scope |
|:---:|---|---|:---:|
| **1** | **Project Foundation** | Project skeleton, architecture, environment, and validation. | Complete (Day 1-2) |
| **2** | **Historical Market Data** | Reliable historical OHLCV data pipeline for Indian equities. | Complete (Day 3-4) |
| **3** | **Technical Feature Engine** | Mathematical computation of indicators, returns, and volatility. | Complete (Day 5-14) |
| **4** | **First ML Model** | Baseline XGBoost model setup with walk-forward temporal validation. | Complete (Day 15-21) |
| **5** | **Prediction Engine** | Point-in-time quantitative forecasting service. | Complete (Day 22-23) |
| **6** | **Prediction History & Database** | Relational schema and immutable storage for predictions. | Complete (Day 24) |
| **7** | **Verification & Accuracy** | Outcome recording, MAE/RMSE calculation, and accuracy tracking. | Complete (Day 25) |
| **8** | **NIFTY & Sector Context** | Broader market indicators, benchmark relative strength, and sector mapping. | Complete (Day 26) |
| **9** | **News & Financial Sentiment** | Financial news ingestion and FinBERT sentiment extraction pipeline. | Complete (Day 27-28) |
| **10** | **Regulatory & Global Events** | Macroeconomic, RBI, governmental, event parser & session impact. | **Complete (Day 29-30)** |
| **11** | **LLM Integration** | Dual-role LLM setup: contextual entity extraction and independent forecasting. | **Current Phase (Next Objective)** |
| **12** | **ML + LLM Combination** | Ensemble layer combining numerical ML and LLM predictions transparently. | Future |
| **13** | **Web Application** | Interactive FastAPI endpoints and user-facing presentation dashboard. | Complete (Day 33-34) |
| **14** | **Live Data Pipeline** | Point-in-time current price, breadth, session intake, and prediction quote integration. | **Complete (Day 35-36)** |
| **15** | **Model Comparison & Improvement**| Comparative metrics (ML vs. LLM vs. Ensemble) and controlled retraining. | **Current Phase (Next Objective)** |
| **16** | **Final Testing & Evaluation** | Comprehensive end-to-end audit, load testing, and production hardening. | Future |

---

## Detailed Phase Descriptions

### Phase 1: Project Foundation
- Establish workspace structure, virtual environment, and dependency baselines.
- Document system architecture, decision records, and data source protocols.
- Configure version control guidelines and basic foundation test suites.

### Phase 2: Historical Market Data
- Implement data ingestion adapters for Indian equities (NSE/BSE).
- Standardize data formats (date, open, high, low, close, volume, adjust factor).
- Enforce point-in-time timestamping and caching policies.

### Phase 3: Technical Feature Engine
- Implement time-series features: Simple and Exponential Moving Averages (SMA/EMA).
- Momentum and volatility indicators: RSI, MACD, ATR, Bollinger Bands, ROC.
- Candlestick geometric features: body, range, wicks, normalizing ratios, close location, return %, and direction.
- Trend Engine and market structure analysis: confirmed swing highs/lows with $t + k$ confirmation timing, structure transitions (HH, HL, LH, LL), and UPTREND/DOWNTREND/SIDEWAYS classification.
- Continuous returns, volume z-scores, and rolling drawdown measures.

### Phase 4: First ML Model
- Define next-session binary directional prediction target ($Close_{t+1} / Close_t - 1$, UP if $>0$ else DOWN, zero return grouped into DOWN, missing final session target) (Day 15 complete).
- Feature matrix assembly and tabular dataset generation (canonical 37 numeric features, strict X/y isolation guard, explicit timestamp joins, natural warmup missing-value preservation, labeled subset extraction) (Day 16 complete).
- Establish baseline numerical forecasting model using XGBoost (binary direction classification, chronological holdout split with label outcome embargo, native XGBoost Core API, deterministic evaluation) (Day 17 complete).
- Baseline comparison & evaluation protocol (Majority-Class Classifier, Fixed-Seed Random Uniform/Stratified baselines, comparative evaluation report, bias identification) (Day 18 complete).
- Implement walk-forward validation splits (strictly avoiding random cross-validation to prevent temporal leakage; expanding-window folds with outcome embargo gap, macro/pooled aggregation, single-class guardrails, and comparative benchmarking of Majority, Uniform/Stratified Random, XGBoost, and LightGBM) (Day 20 complete).
- Model error analysis & feature usefulness audit (symmetrical class metrics for UP and DOWN, confusion matrix breakdown, directional prediction bias detection, distribution shift analysis, 37-feature matrix quality audit, collinearity group clustering with 59 pairs >= 0.90, exploratory XGBoost and LightGBM tree feature importance, and zero-leakage training isolation) (Day 21 complete).


### Phase 5: Prediction Engine
- Build the core prediction service orchestrating feature assembly and model inference (`PredictionService` in `app/prediction/service.py`, typed `PredictionRequest` and `PredictionResult` contracts, zero silent retraining, strict inference isolation) (Day 22 complete).
- Structured prediction output & transparency layer: generate validated directional forecast (`UP` / `DOWN`), class probabilities explicitly marked uncalibrated (`is_probability_calibrated=False`), input data quality auditing, explicit expected movement boundaries (`expected_movement=None`, `expected_movement_status="UNSUPPORTED"` for direction classifiers), full JSON serialization via `.to_dict()`, and text audit formatting via `.format_summary()` without fabricating target prices or uncalibrated confidence scores (Day 23 complete).

### Phase 6: Prediction History & Database
- Design SQLite database schema (predictions, stocks, actuals, model_versions) with WAL mode, foreign key constraints, and performance indexes (Day 24 complete).
- Implement immutable prediction persistence: predictions cannot be edited after creation via SQLite engine triggers (`trg_prevent_prediction_update`, `trg_prevent_prediction_delete`) and strongly-typed `PredictionRepository` (Day 24 complete).

### Phase 7: Verification & Accuracy (Current)
- Outcome verification engine (`OutcomeVerifier` in `app/history/verifier.py`): match persisted predictions with realized market sessions ($t+1$), respect trading calendar/holidays/pending sessions, compute canonical target direction/returns ($Close_{t+1}/Close_t - 1$, $R > 0 \implies UP$, $R \le 0 \implies DOWN$), data provenance tracking, and idempotent persistence into SQLite `actuals` table (Day 25 complete).
- Actuals immutability & relational integrity: prevent duplicate or conflicting outcome records, SQLite engine triggers (`trg_prevent_actual_update`, `trg_prevent_actual_delete`) enforce write-once immutability, and atomic foreign-key linking to `predictions` (Day 25 complete).
- Prediction evaluation service (`PredictionEvaluator` in `app/history/evaluator.py`): isolate evaluation denominator strictly to verified predictions ($N_{verified}$), exclude pending and ineligible predictions from error metrics, report symmetrical class metrics (UP/DOWN precision, recall, F1) and confusion matrix breakdown, zero division safety for insufficient samples, without fabricating target prices or calibrated probabilities (Day 25 complete).
- Compute continuous prediction error metrics (MAE, RMSE, direction magnitude correlation) when magnitude models are introduced in later phases.

### Phase 8: NIFTY & Sector Context (Complete - Day 26)
- Ingest NIFTY 50 (`^NSEI`), NIFTY Bank (`^NSEBANK`), NIFTY IT (`^CNXIT`), and relevant sector indices via provider index symbol mapping.
- Calculate point-in-time relative performance: daily relative return / alpha ($R_{stock} - R_{bench}$), relative strength ratio ($Close_{stock} / Close_{bench}$), and 5d/20d relative strength momentum.
- Compute 20-session rolling beta ($\beta_{20} = Cov(R_s, R_b) / Var(R_b)$) and 20-session rolling correlation ($\rho_{20} = Cov(R_s, R_b) / (\sigma_s \sigma_b)$) with zero-variance safeguards.
- Cross-sectional market breadth calculation: advances, declines, unchanged counts, advance-decline ratio, breadth thrust, net advances, and 20-day SMA breadth participation percentage across equity universes.
- Strict session alignment preventing look-ahead bias and handling calendar discrepancies.

### Phase 9: News & Financial Sentiment (Complete - Day 27 & Day 28)
- Implement financial news retrieval and deduplication (`app/news/` - Day 27 complete):
  - Extensible provider contract `BaseNewsProvider` and concrete `RSSNewsProvider` adapter for Indian market news.
  - Canonical immutable schema `NewsArticle` capturing headline, publisher source, timezone-aware publication time, distinct ingestion time, symbol associations, URL, summary, and deterministic `article_id`.
  - News deduplication engine (`deduplicate_news` in `cleaner.py`): removes exact article ID duplicates, duplicate URLs, and syndicated headlines within configurable time windows while preserving the earliest publication.
  - Strict point-in-time session filtering (`filter_news_point_in_time`): prevents temporal look-ahead leakage by excluding any news published or ingested after the decision cutoff timestamp.
- FinBERT domain-specific sentiment scoring foundation (`app/news/sentiment.py` - Day 28 complete):
  - Model selection: `ProsusAI/finbert` (domain-adapted BERT fine-tuned on Financial PhraseBank, Apache 2.0 open-source license).
  - Lazy model initialization: weights and tokenizers loaded strictly on demand, zero import overhead.
  - Dynamic label mapping resolution from `model.config.id2label` (e.g. `{0: 'positive', 1: 'negative', 2: 'neutral'}`).
  - Pluggable backend architecture: `BaseSentimentBackend` interface with `FinBERTBackend` and offline deterministic `MockSentimentBackend` for CI/unit tests.
  - Strict error quarantining: inference failures recorded as `status="ERROR"` with `sentiment_label=None` and `probabilities=None` (zero fabricated false neutrals).
  - Text preparation with headline validation and configurable character truncation (`prepare_article_text`).
  - Canonical `ArticleSentimentResult` schema capturing article ID, headline, sentiment label, winning confidence score, class probability distribution, model provenance, and execution timestamp (`scored_at`).
  - Strict non-causal disclosure: sentiment classification is text tone representation, not a directional stock price prediction.

### Phase 10: Regulatory & Global Events (Complete - Day 29 & Day 30)
- Macroeconomic, regulatory, and external events ingestion foundation (`app/events/` - Day 29 complete):
  - Canonical immutable schema `MacroEvent` with four distinct timezone-aware timestamps (`published_at`, `announced_at`, `effective_at`, `ingested_at`), deterministic SHA-256 `event_id`, and `StructuredEventValue`.
  - Canonical `ExternalMarketObservation` schema representing continuous macro variables (Brent Crude, USD/INR, S&P 500) as distinct time-series observations.
  - Official primary-source adapters:
    - `RBIEventProvider` (`https://rbi.org.in/pressreleases_rss.xml`): ingests press releases, MPC decisions, and repo rate levels.
    - `SEBIEventProvider` (`https://www.sebi.gov.in/sebirss.xml`): ingests master circulars, regulatory guidelines, and enforcement orders.
    - `ExternalMarketProvider`: ingests continuous macro time-series measurements (`BZ=F`, `INR=X`, `^GSPC`).
  - Multi-tier event deduplication engine (`deduplicate_events` in `cleaner.py`): removes exact IDs, duplicate URLs, and matching source+title records within configurable time windows.
  - Strict point-in-time session filtering (`filter_events_point_in_time`): eliminates look-ahead leakage across market decision cutoffs while preserving future legal effective dates.
  - Non-causal representation: macro events and external market observations represent contextual information without asserting causal stock price direction rules.
- Trading session alignment & empirical event impact analysis (`app/events/` - Day 30 complete):
  - Indian equity trading calendar abstractions (`BaseTradingCalendar`): `MarketDataTradingCalendar` anchored directly to realized price bars, and injectable `ExchangeTradingCalendar` supporting configurable weekends, holidays, and Muhurat sessions.
  - Session alignment engine (`EventSessionAligner` in `aligner.py`): deterministically categorizes events into `PRE_MARKET` (< 09:15 IST), `IN_SESSION` (09:15-15:30 IST), and `POST_MARKET` (> 15:30 IST), routing post-market and non-trading day announcements strictly to the next trading day to eliminate look-ahead leakage across session close.
  - Date-only precision guard: conservatively aligns date-only regulatory circulars (e.g. SEBI notices lacking time-of-day) to the next trading day.
  - Empirical event impact analyzer (`EventImpactAnalyzer` in `impact.py`): computes same-day returns, 1d/3d/5d forward returns, pre- and post-event realized volatilities (5-session rolling sample stdev), and benchmark excess returns (^NSEI).
  - Anti-leakage safeguards: uncompleted future sessions safely return `None` with status `INCOMPLETE_OUTCOME_WINDOW`; multi-event deduplication eliminates double-counting; mandatory non-causal disclosures enforced on all outputs.

### Phase 11: LLM Integration (Complete - Day 31)
- Contextual LLM integration foundation (`app/llm/` - Day 31 complete):
  - Local runtime integration with Ollama (`http://127.0.0.1:11434`) and Gemma 3 12B (`gemma3:12b`) using Python standard library HTTP (`urllib.request`), with zero third-party framework wrappers (no LangChain, no LlamaIndex).
  - Pluggable backend architecture: `BaseLLMClient` interface with concrete `OllamaLLMClient` and deterministic `MockLLMClient` for 100% offline automated testing.
  - Role A (Structured Context Extraction):
    - `LLMContextExtraction` schema capturing entities, affected sectors, macro/regulatory factors, qualitative sentiment tone, source references, and uncertainty notes.
    - Anti-prompt-injection boundary: wraps untrusted news/events in `<source_context>` tags with delimiter escaping and explicit system rules treating text as reference data only.
  - Role B (Independent Qualitative Reasoning & Risk Identification):
    - `LLMReasoningResult` schema capturing symbol, qualitative direction (`UP`, `DOWN`, `NEUTRAL`, `INSUFFICIENT_EVIDENCE`), reasoning summary, positive/negative factors, downside risks, source citations, qualitative confidence (LOW/MEDIUM/HIGH), and mandatory non-causal disclaimer.
    - Strict zero-fabrication guarantees: no invented prices, price targets, returns, or uncalibrated probabilities.
    - Safe fast-paths: empty context yields `INSUFFICIENT_EVIDENCE` with LOW confidence; client errors and malformed responses raise explicit typed exceptions (`LLMClientError`, `LLMParseError`, `LLMValidationError`) rather than fabricating fake neutral answers.
  - Strict quantitative model isolation: quantitative ML models (XGBoost/LightGBM), the 37-feature matrix, and prediction database records remain completely unaffected by qualitative LLM reasoning.

### Phase 12: ML + LLM Combination (Complete - Day 32)
- Multi-agent ensemble and synthesis layer (`app/prediction/ensemble.py` - Day 32 complete):
  - Canonical data contracts: `EnsemblePredictionResult`, `EnsembleAgreement`, `EnsembleWeights`, `TargetRange`.
  - Independent score preservation (ADR 05): Both standalone quantitative `PredictionResult` (XGBoost/LightGBM) and qualitative `LLMReasoningResult` (Gemma 3 12B) are retained in full without loss of attribution.
  - Transparent, audited weighted probability synthesis: blends quantitative $P_{ML}(UP)$ with qualitative polarity $S_{LLM}$ using configurable normalized weights (default 70% ML / 30% LLM).
  - Agreement & Divergence analysis: classifies model alignment into `STRONG_AGREEMENT`, `AGREEMENT`, `DIVERGENCE` (conflicting signals flag), `PARTIAL`, `ML_ONLY`, or `LLM_ONLY`.
  - Integrated factor rankings and downside risks combining quantitative indicators and qualitative news/regulatory drivers.
  - Volatility-anchored expected price range estimation (1-session ATR-14 bounds).
  - Canonical adapter: `.to_prediction_result()` seamlessly enables immutable SQLite persistence (`PredictionRepository`), outcome verification (`OutcomeVerifier`), and comparative performance metrics (`PredictionEvaluator`).
  - Graceful degradation: handles LLM service failures or offline states by falling back to 100% ML weight without crashing.

### Phase 13: Web Application & API Layer (Complete - Day 34)
- FastAPI REST API Foundation (`app/api/` - Day 33 complete):
  - Application factory (`app/api/app.py`): central FastAPI instance with OpenAPI documentation (`/docs`, `/redoc`), structured error handlers, and non-disclosure sanitization.
  - Dependency injection layer (`app/api/dependencies.py`): loosely coupled database connections, `PredictionRepository`, `PredictionService`, `EnsembleService`, and event providers for clean test overrides.
  - Typed Pydantic request/response schemas (`app/api/schemas.py`): input bounds, parameter validations, and non-sensitive payload models.
  - Health endpoint (`GET /api/health`): verifies SQLite connectivity, model storage accessibility, and LLM configuration without running slow inference or disclosing internal secrets.
  - Prediction endpoint (`POST /api/predict`): accepts validated tickers and parameters, orchestrates standalone ML (XGBoost/LightGBM) or synthesized multi-agent ensemble (ML + Gemma 3 12B), and persists immutable records.
  - History endpoint (`GET /api/history`): retrieves persisted predictions with bounded pagination, ticker/model filtering, and linked verified actual outcomes.
  - Feedback endpoint (`POST /api/feedback`): validates feedback schema and explicitly defers persistence (HTTP 501) with ADR 10 disclosure against automated retraining loops.
  - Events endpoint (`GET /api/events`): exposes normalized, deduplicated macroeconomic and regulatory announcements across RBI and SEBI providers.
- Interactive Stock Prediction Web UI (`app/api/static/` - Day 34 complete):
  - Modern, responsive single-page web dashboard adhering strictly to Vanilla HTML5, CSS3, and JavaScript (zero bloated frontend framework dependencies).
  - Deep dark-theme aesthetic (`#070a13` canvas, glassmorphic cards, emerald `#10b981` bullish up, rose `#f43f5e` bearish down, responsive grid down to 320px mobile).
  - Four dedicated tab views:
    1. **Prediction Engine**: Stock search input with regex validation, popular ticker quick-chips (RELIANCE, TCS, INFY, etc.), model selector, collapsible advanced controls (ensemble weight slider, lookback days, staleness threshold, SQLite persistence toggle).
    2. **Prediction History**: Tabular view of immutable audit records, pagination controls, ticker/model filters, and real-time display of verified market outcomes ($Close_{t+1}$ vs $Close_t$, return %, directional accuracy).
    3. **Macro & Regulatory Events**: Live feed of normalized RBI monetary policy and SEBI regulatory circulars, categorized filter chips, and verified source citations.
    4. **System Readiness**: Real-time diagnostic cards for SQLite connectivity, model artifact registry, and LLM Ollama runtime via non-inferencing `/api/health`.
  - Financial display compliance: strictly separates quantitative ML metrics from qualitative LLM reasoning, prominently disclaims uncalibrated 70/30 heuristic weights, renders volatility target ranges ($Close \pm ATR$) and agreement badges only when provided by API responses, never substitutes 50% for missing probabilities, validates event link protocols strictly to HTTP(S), and never displays hardcoded demo prices or synthetic outcomes.
  - FastAPI integration: mounted static directory (`/static`), `/ui` HTML route, browser content-negotiation on `/`, and Starlette CORS middleware restricted to trusted local origin whitelists with credentials disabled to prevent credential leakage.

### Phase 14: Live Data Pipeline (Complete - Day 35-36)
- Connect near-real-time market data providers with strict timestamp preservation (`YFinanceProvider.fetch_quote()`).
- Handle Indian market session states (pre-open, regular hours, post-close, closed, holidays, weekends via `MarketSessionStateEngine`).
- Integrate verified quote context into inference (`QuoteContext`, `PredictionService._fetch_quote_context`) and ensemble target range anchoring (`EnsembleService.synthesize`).
- End-to-end pipeline validation, temporal isolation (zero look-ahead bias), quote observability, and sensitive error message sanitization (Day 36 complete).

### Phase 15: Model Comparison & Improvement
- Create comparative dashboards evaluating Python ML vs. LLM vs. Combined performance.
- Implement controlled, gated model retraining workflows with version tracking.

### Phase 16: Final Testing & Evaluation
- End-to-end integration testing and robustness verification under adverse market regimes.
- Security audit, documentation finalization, and deployment readiness review.
