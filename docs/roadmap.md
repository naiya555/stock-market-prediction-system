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
| **11** | **LLM Integration** | Dual-role LLM setup: contextual entity extraction and independent forecasting. | Complete (Day 31-32) |
| **12** | **ML + LLM Combination** | Ensemble layer combining numerical ML and LLM predictions transparently. | Complete (Day 32) |
| **13** | **Web Application** | Interactive FastAPI endpoints and user-facing presentation dashboard. | Complete (Day 33-34) |
| **14** | **Live Data Pipeline** | Point-in-time current price, breadth, session intake, and prediction quote integration. | Complete (Day 35-36) |
| **15** | **Model Comparison & Improvement**| Comparative metrics (ML vs. LLM vs. Ensemble) and controlled retraining. | **In Progress (Day 37)** |
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

### Phase 15: Model Comparison & Improvement (Complete - Day 37-38)
- Comparative evaluation analytics and dashboard evaluating Python ML vs. LLM vs. Combined Ensemble performance side-by-side (`app/history/comparison.py`, `GET /api/history/compare`, Day 37 complete).
- Pairwise matched session alignment, divergence, win-loss superiority, Brier score probability calibration, and ensemble lift tracking.
- Interactive side-by-side model comparison dashboard in prediction history web UI.
- Controlled, gated model retraining workflows with version tracking and formal safety gates (ADR 10, Day 38 complete):
  - File system quarantine: Candidate models quarantined in `models/candidates/` and active models archived to `models/archive/`.
  - Five formal validation gates: Sample Sufficiency, Class Balance, Baseline Superiority, Minimum Out-of-Sample Performance (50%), and Active Model Non-Degradation (margin 2%).
  - Atomic promotion protocol copying candidate to active path (`models/{model}_direction.*`) and preserving active models 100% on any gate failure.
  - SQLite model release persistence in `model_releases` table tracking version history, cutoffs, metrics, and gate results.

### Phase 16: Final Testing & Evaluation (In Progress - Day 45)
- Comprehensive audit of retraining workflow and model release management (Day 39 complete).
- Implementation of Gate 0 (Chronological Integrity Gate) eliminating look-ahead bias and inverted cutoffs (ADR 07).
- Transactional promotion protocol with mandatory archiving, atomic staging (`os.replace`), and automatic rollback from archive on SQLite/filesystem failure.
- Multi-regime market stress testing across Bull, Bear, Choppy, and Shock Transition regimes (`tests/test_multi_regime_evaluation.py`).
- Security audit and deployment readiness hardening (Day 40 complete):
  - Dependency manifest audit (`pip check` verified clean across all 56 installed packages; scanner environment limitation noted).
  - Production CORS strict validation (wildcards `*` and insecure plain HTTP non-localhost origins rejected at startup).
  - Production OpenAPI/Swagger docs exposure lockdown (`docs_url=None`, `openapi_url=None` returning 404 in production).
  - Defensive OWASP response headers middleware (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`).
  - Production startup guard rejecting `APP_DEBUG=true` in production mode.
- CI/CD security scanning, deployment runbook & staging readiness (Day 41 complete):
  - Automated CI/CD dependency vulnerability scanning and multi-version test suite (`.github/workflows/ci.yml`).
  - Production operations and deployment runbook covering env defaults, Nginx TLS termination, WAL hot backup, model rollback, and triage (`docs/deployment-runbook.md`).
  - Request latency telemetry middleware emitting `X-Process-Time-Ms` and non-sensitive operational access logs.
  - Reproducible staging soak simulation framework (`scripts/staging_soak_test.py`).
- Live staging readiness & deployment runbook automated validation (Day 42 complete):
  - Verified local Ollama Gemma 3 12B service readiness and conducted infrastructure inventory.
  - Validated deployment runbook protocols with automated tests (`tests/test_deployment_runbook.py`).
  - Verified real TCP socket HTTP execution of `staging_soak_test.py` with zero database mutation.
  - Documented staging infrastructure blocker and concrete external provisioning prerequisites.
- Local staging environment & production-style validation (Day 43 complete):
  - Implemented reproducible isolated local staging launcher with strict loopback binding policy (`scripts/run_local_staging.py`).
  - Isolated ephemeral SQLite database and temporary read-only model artifact copies.
  - Validated 8-point production checklist (loopback isolation, startup, `/api/health`, defensive headers, OpenAPI 404 suppression, smoke tests, zero dev DB mutation, zero active model mutation).
  - Executed controlled local load test (50 requests, concurrency 4, 100% success, 19.14 req/s, p50 23.15ms).
  - Added automated test suite for local staging runner (`tests/test_local_staging.py`).
- Local staging performance reliability & failure-handling audit (Day 44 complete):
  - Isolated tail latency root cause (external RSS HTTP calls in `/api/events`) and implemented `OfflineStagingEventProvider` via `dependency_overrides`.
  - Upgraded percentile math to standard linear interpolation (`compute_percentile`), added `p90`, and added sample size sufficiency indicators.
  - Added strict HTTP 2xx success classification (`classify_http_outcome`) and accurate partial-run throughput denominators.
  - Implemented per-endpoint latency breakdown tracking (`EndpointStats`) across `/api/health`, `/`, `/api/history`, and `/api/events`.
  - Added automated test suite covering 8 failure-handling scenarios (unreachable port, timeout, 5xx, idle shutdown, request shutdown, tempdir cleanup, DB/models preservation, occupied port).
  - Formulated proposed 10-minute sustained-load test plan with explicit local acceptance criteria for user approval.
- Local staging sustained soak test, connection pooling & data integrity audit (Day 45 complete):
  - Upgraded runner with process-scoped Windows sleep prevention (`SetThreadExecutionState`), monotonic timing, and heartbeat suspension detection.
  - Implemented persistent HTTP Keep-Alive connection pooling with thread-confined `requests.Session()` (`HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(0))`), bounded timeouts `(2.0, 5.0)`, and explicit response/session cleanup in `finally` blocks.
  - Executed clean 600-second sustained soak test retry (`scripts/run_local_staging.py --duration 600`): confirmed 0.0s sleep gap and uninterrupted run (600.42s elapsed).
  - Captured complete telemetry: 156,895 completed requests (261.31 req/s), 156,895 HTTP 2xx (100.00%), 0 HTTP 4xx, 0 HTTP 5xx, 0 timeouts, 0 network errors.
  - Latency verified well within limits: p50 14.99 ms (< 50 ms), p90 24.99 ms, p95 29.02 ms (< 100 ms), p99 39.02 ms.
  - Verified 100% data immutability with identical SHA-256 hashes before and after for `data/predictions.db` and active `models/` (0 bytes mutated).
  - Verified graceful Uvicorn shutdown on loopback, immediate port 8899 release, and ephemeral directory cleanup.
  - Passed all 25 focused staging tests (+6 new deterministic tests) and 612 full regression tests with clean `pip check`.
  - Maintained Phase 16 as IN PROGRESS; local staging validation complete, awaiting dedicated cloud/cluster staging infrastructure for multi-hour production-equivalent soak testing.
- Remaining Phase 16 acceptance criteria:
  - Multi-hour soak testing on dedicated production-equivalent staging infrastructure during live exchange market hours once external host cluster is provisioned.
  - Final Phase 16 completion and milestone sign-off review.




