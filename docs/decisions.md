# Architectural Decision Records (ADRs)

This document formalizes the architectural decisions made on Day 1. All future implementation work must conform to these decisions.

---

## ADR 01: Python as Primary Backend Language
- **Status:** Accepted
- **Context:** The system demands numerical computing, machine learning, financial NLP, and API orchestration.
- **Decision:** Python 3.11+ is chosen as the foundational backend language.
- **Consequences:** Provides direct access to scientific computing (NumPy, SciPy), ML frameworks (scikit-learn, XGBoost, LightGBM), NLP models (Hugging Face / FinBERT), and modern async web frameworks.

---

## ADR 02: FastAPI as the Planned Backend API Framework
- **Status:** Accepted
- **Context:** An API is required to expose prediction services, trigger validations, and serve the future frontend.
- **Decision:** FastAPI will serve as the backend REST API framework.
- **Consequences:** Offers native asynchronous capabilities, automatic OpenAPI documentation, and strict type validation via Pydantic.

---

## ADR 03: Relational Database Storage Replacing Excel
- **Status:** Accepted
- **Context:** Historical tracking was previously managed via spreadsheets. Spreadsheets lack transaction isolation, relational integrity, auditability, and automated verification hooks.
- **Decision:** Spreadsheets/Excel will NOT be part of the software architecture. The system will use SQLite for local development and migrate to PostgreSQL for multi-user production.
- **Consequences:** Guarantees relational integrity, indexed point-in-time queries, and ACID guarantees for immutable prediction logging.

---

## ADR 04: Modular Package Architecture
- **Status:** Accepted
- **Context:** Complex machine learning systems risk becoming monolithic "god scripts" with tangled responsibilities.
- **Decision:** The codebase will be partitioned into distinct domain packages (`app/market/`, `app/news/`, `app/nlp/`, `app/prediction/`, `app/training/`, `app/history/`, `app/database/`, `app/api/`).
- **Consequences:** Minimizes circular dependencies, allows isolated testing of data loaders versus modeling code, and simplifies future refactoring.

---

## ADR 05: Independence of Python ML and LLM Predictions
- **Status:** Accepted
- **Context:** Combining numerical ML and qualitative LLM outputs into a single black-box obfuscates error attribution.
- **Decision:** Numerical ML models (XGBoost/LightGBM) and Contextual LLMs will operate independently and generate standalone prediction outputs before any ensemble combination occurs.
- **Consequences:** Both models can be measured, benchmarked, and evaluated side-by-side. If one underperforms, the source of error is immediately identifiable.

---

## ADR 06: Preservation of Historical Truth in Prediction Records
- **Status:** Accepted
- **Context:** In financial forecasting, hindsight bias occurs if original predictions are retrospectively altered to match outcomes.
- **Decision:** Once a prediction record is generated and stored, its prediction attributes (`timestamp`, `ticker`, `direction`, `target_range`, `confidence`, `factors`, `model_version`) are permanently immutable. Actual market results are stored as distinct verification records linked via foreign keys.
- **Consequences:** Creates an auditable track record of real out-of-sample performance.

---

## ADR 07: Strict Prevention of Temporal Data Leakage
- **Status:** Accepted
- **Context:** Data leakage (using information timestamped after $T_{pred}$) creates deceptively high historical backtest scores that fail in live markets.
- **Decision:** All data ingestion and feature generation pipelines must preserve point-in-time timestamps (`data_available_at`). No data stamped after $T_{pred}$ may be used in any feature matrix for that timestamp.
- **Consequences:** Eliminates look-ahead bias and ensures backtest metrics match live market execution reality.

---

## ADR 08: Explicit Model and Feature Versioning
- **Status:** Accepted
- **Context:** Models and feature definitions evolve over time. Evaluating past predictions requires knowing the exact model and feature pipeline that produced them.
- **Decision:** Every prediction record must persist `model_version`, `feature_version`, and `prompt_version` (where applicable).
- **Consequences:** Ensures complete reproducibility and enables retrospective auditing across model updates.

---

## ADR 09: Out-of-Sample Walk-Forward Evaluation
- **Status:** Accepted
- **Context:** Random train/test splits violate the temporal sequence of financial time series and introduce leakage.
- **Decision:** Cross-validation must strictly use walk-forward (expanding/rolling window) out-of-sample temporal splits. Training accuracy is rejected as a primary success metric.
- **Consequences:** Yields realistic evaluation of model generalization under non-stationary market regimes.

---

## ADR 10: Controlled, Gated Model Retraining
- **Status:** Accepted
- **Context:** Unsupervised or continuous automated retraining risks feedback loops, catastrophic forgetting, and instability.
- **Decision:** Model retraining will only occur through controlled, versioned releases following formal validation gates. Predictions do not automatically become training data.
- **Consequences:** Protects production integrity and prevents model drift caused by noisy, short-term anomalies.

---

## ADR 11: Prohibition of Fake or Mock Market Logic in Core Pipelines
- **Status:** Accepted
- **Context:** Mock data generators masquerading as production logic create false confidence and mask integration deficiencies.
- **Decision:** No synthetic or mock market data generators will be implemented in the core application logic. Real data adapters will be integrated in Phase 2 with proper error handling and fallback states.
- **Consequences:** Ensures the codebase reflects true production capabilities at every stage.

---

## ADR 12: Provider Agnosticism & Pluggable Interfaces
- **Status:** Accepted
- **Context:** Financial data vendors, news APIs, and LLM providers may change, deprecate endpoints, or alter rate limits.
- **Decision:** Data providers, news crawlers, and LLM inference clients will implement clean abstract interfaces to allow seamless substitution without altering core prediction logic.
- **Consequences:** Protects the system from vendor lock-in and vendor-specific service outages.

---

## ADR 13: Project Directory Layout & Minimal Day 1 Footprint
- **Status:** Accepted
- **Context:** Day 1 requires an organized directory structure without cluttering subdirectories with premature placeholder files.
- **Decision:** The structure places `app/`, `data/`, `models/`, `docs/`, and `tests/` at the root of `d:\Share_market_predictor`. Placeholder files are strictly omitted; `.gitkeep` is used only to preserve required data and model directory paths in Git.
- **Consequences:** Keeps the project minimal and fully aligned with Ponytail/YAGNI principles.
