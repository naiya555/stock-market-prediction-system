# System Architecture

## 1. Overview

The Indian Stock Market Prediction System is designed around modularity, strict temporal data isolation, reproducible machine learning, and explainable multi-model inference.

The foundational design loop is:
```
PREDICT ➔ EXPLAIN ➔ VERIFY ➔ EVALUATE ➔ IMPROVE
```

---

## 2. High-Level System Architecture

```text
┌────────────────────────────────────────────────────────┐
│                      Frontend UI                       │
│    (Stock Selection, Forecast Dashboard, Audit Log)    │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP / REST
┌───────────────────────────▼────────────────────────────┐
│                    FastAPI API Gateway                 │
│         (Routing, Validation, Request Lifecycle)       │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                   Prediction Service                   │
│             (Orchestrator of Pipelines)                │
└──────┬────────────────────┬────────────────────┬───────┘
       │                    │                    │
┌──────▼───────┐    ┌───────▼────────┐    ┌──────▼───────┐
│ Market Data  │    │   News Data    │    │ External /   │
│   Service    │    │    Service     │    │ Macro Events │
└──────┬───────┘    └───────┬────────┘    └──────┬───────┘
       │                    │                    │
┌──────▼────────────────────▼────────────────────▼───────┐
│         Preprocessing & Temporal Validation            │
│  (Point-in-Time Alignment, Deduplication, Cleansing)   │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                   Feature Engineering                  │
│       (Returns, Volatility, Momentum, Sentiment)       │
└──────┬────────────────────┬────────────────────┬───────┘
       │                    │                    │
┌──────▼────────┐   ┌───────▼────────┐   ┌───────▼───────┐
│ Numerical ML  │   │ Financial NLP  │   │  Context LLM  │
│(XGBoost/Light)│   │   (FinBERT)    │   │  (Role A & B) │
└──────┬────────┘   └───────┬────────┘   └───────┬───────┘
       │                    │                    │
       │  ML Prediction     │ Sentiment Score    │  LLM Forecast
       └──────────────┬─────┴────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────┐
│              Combination / Ensemble Layer              │
│   (Independent Scores Preserved, Weighted Synthesis)   │
└─────────────────────┬──────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────┐
│       Output Payload: Prediction + Explanation         │
│ (Direction, Target ₹/%, Confidence, Factors, Risks)    │
└─────────────────────┬──────────────────────────────────┘
                      │ Immutable Write
┌─────────────────────▼──────────────────────────────────┐
│              Relational Database Storage               │
│        (SQLite initially, PostgreSQL migration)        │
└─────────────────────┬──────────────────────────────────┘
                      │ Future Actual Results
┌─────────────────────▼──────────────────────────────────┐
│            Verification & Evaluation Engine            │
│    (Out-of-Sample MAE/RMSE, Directional Accuracy)      │
└─────────────────────┬──────────────────────────────────┘
                      │ Controlled Gate
┌─────────────────────▼──────────────────────────────────┐
│            Controlled Retraining Pipeline              │
│       (Walk-Forward Validation, Model Registry)        │
└────────────────────────────────────────────────────────┘
```

---

## 3. Layer Responsibilities

### 3.1. Frontend
- **Role:** Web interface for interactive stock selection, inspection of predictions, transparent factor breakdown, and historical accuracy tracking.
- **Rules:** Pure presentation layer. Never executes forecasting logic or database mutations directly.

### 3.2. FastAPI Application Layer
- **Role:** Exposes RESTful endpoints (`/api/v1/predict`, `/api/v1/history`, `/api/v1/verify`, etc.).
- **Rules:** Handles request validation, authentication, rate limiting, and structured error responses.

### 3.3. Prediction Service Orchestrator
- **Role:** Central workflow coordinator. Dispatches data gathering, enforces point-in-time cutoffs, routes features to independent models, and invokes the combination layer.
- **Rules:** Enforces strict execution order and ensures no step proceeds if data timestamps are violated.

### 3.4. Data Services
- **Market Data Service:** Fetches historical and current OHLCV, volume, market breadth, and sector/NIFTY benchmarks.
- **News Data Service:** Collects corporate filings, financial disclosures, and verified Indian market news.
- **External Events Service:** Tracks macroeconomic announcements, RBI policy actions, budget statements, and regulatory circulars.
- **Rules:** Every record must be stamped with `data_available_at`.

### 3.5. Preprocessing & Temporal Alignment
- **Role:** Normalizes timestamps, removes duplicates, cleans missing values forward-safely (no forward-looking interpolations), and verifies point-in-time constraints.
- **Zero-Leakage Invariant:** Data timestamped after the forecast timestamp $T_{pred}$ is strictly excluded.

### 3.6. Feature Engineering
- **Role:** Computes quantitative indicators:
  - Technical: Moving averages, RSI, MACD, ATR, Bollinger Bands.
  - Statistical: Log returns, rolling realized volatility, momentum, volume z-scores.
  - Sector/Index: Relative strength against NIFTY 50 and sectoral indices.
  - NLP/Event: Structured sentiment scores and impact flags.

### 3.7. Numerical Machine Learning (XGBoost / LightGBM)
- **Role:** Generates quantitative direction probability and expected magnitude from numeric feature matrices.
- **Rules:** Evaluated using walk-forward validation and out-of-sample testing. Random cross-validation splits are prohibited to prevent temporal leakage.

### 3.8. Financial NLP (FinBERT)
- **Role:** Domain-specific sentiment classifier.
- **Distinction:** FinBERT is treated as a sentiment feature extractor (Positive, Neutral, Negative with calibrated probabilities), NOT a general reasoning agent.

### 3.9. Contextual LLM (Dual-Role Architecture)
- **Role A — Context Analysis:** Parses unstructured announcements, RBI press releases, and geopolitical news into structured entities, sector impacts, and time horizons.
- **Role B — Direct Prediction:** Generates an independent qualitative forecast (direction, confidence, key factors, risk elements).
- **Independence Principle:** The LLM prediction is evaluated separately from the Python ML model. Neither model is treated as infallible.

### 3.10. Combination & Ensemble Layer
- **Role:** Synthesizes the independent outputs into a final actionable recommendation:
  - Preserves individual model predictions and individual confidence scores.
  - Produces combined directional probability, target range, and integrated factor rankings.

### 3.11. Explanation & Attribution Layer
- **Role:** Provides truthful, input-grounded explanations.
- **Rule:** Explanations cite actual model feature attributions (e.g., SHAP values) and verified context items. Hallucinating or post-hoc rationalizing reasons is forbidden.

### 3.12. Database Persistence
- **Role:** Replaces spreadsheets entirely.
- **Technology:** SQLite for development and early testing; PostgreSQL for multi-user production.
- **Immutability Invariant:** Once a prediction is recorded, its prediction attributes (`prediction_id`, `timestamp`, `direction`, `target`, `model_version`, `factors`) can never be modified. Actual market outcomes are appended as distinct relational records.

### 3.13. Verification & Evaluation Engine
- **Role:** As real market prices arrive, computes:
  - Directional correctness (Binary / Multiclass: UP / DOWN / SIDEWAYS).
  - Magnitude errors (MAE, RMSE, MAPE).
  - Classification metrics: Precision, Recall, F1-Score, Brier score / calibration.
- **Comparison:** ML accuracy, LLM accuracy, and ensemble accuracy are tracked side-by-side.

### 3.14. Controlled Retraining
- **Role:** Periodic, gatekeeper-managed model updates.
- **Rules:** Retraining is never automated or unmonitored. Predictions do not immediately feed back into training sets. Models undergo walk-forward backtesting before deployment to the model registry.

---

## 4. Core Primitives & Cross-Cutting Foundation (`app/core/`)

### 4.1. Centralized Configuration (`app/core/config.py`)
- **Single Source of Truth:** Centralized settings container (`Settings`) managing runtime mode, logging verbosity, timezones (`Asia/Kolkata`), and storage paths.
- **Environment Driven:** Reads overrides from environment variables and local `.env` files via `python-dotenv`.
- **Zero-Secret Invariant:** No API keys, passwords, or secrets are hardcoded. Safe defaults are provided only for non-secret values.

### 4.2. Centralized Structured Logging (`app/core/logging_config.py`)
- **Consistent Format:** Standardized log formatting (`timestamp | level | logger | message`) across all application tiers.
- **Universal Availability:** Utilized consistently across future collectors, prediction pipelines, API routes, and database operations.
- **Sanitization:** Loggers are configured strictly to output application state and events, never printing sensitive credentials.

### 4.3. Canonical Data Schema Contracts (`app/core/schemas.py`)
- **Adapter Invariant:** All future external data adapters (NSE scrapers, broker APIs, news feeds) must normalize external payloads into canonical internal dataclasses (`MarketOHLCV`, `MarketQuote`, `DataSourceMetadata`).
- **Temporal Integrity:** Every record preserves the explicit point-in-time `timestamp` and source origin `source`.
- **Physical Validation:** Domain rules (e.g., `high >= max(open, close)`, `low <= min(open, close)`, strictly positive prices) are enforced at contract instantiation, preventing malformed data from reaching downstream modeling layers.

### 4.4. Market Data Layer & Historical Collector (`app/market/`)
- **Ingestion Pipeline Data Flow:**
  ```text
  External Provider (Yahoo Finance / NSE)
          ↓
  Concrete Provider Adapter (YFinanceProvider)
          ↓
  Normalization (Raw Unadjusted OHLCV)
          ↓
  Canonical MarketOHLCV (app.core.schemas)
          ↓
  Validation (Domain Bounds & Positive Prices)
  ```
- **Provider Interface (`app/market/providers/base.py`):** Establishes the `BaseMarketDataProvider` abstract contract defining `name` and `fetch_historical_ohlcv(symbol, start_date, end_date, interval)`.
- **Concrete Provider Adapter (`app/market/providers/yfinance_provider.py`):** Implements `YFinanceProvider` for Indian cash equities (`.NS` / `.BO`). Encapsulates all third-party DataFrame manipulations and upstream HTTP session handling within the adapter boundary.
- **Price Convention:** Adopts raw unadjusted OHLCV prices (`auto_adjust=False`) to preserve authentic historical market trade levels and physical candle relationships (`High >= max(Open, Close)`, `Low <= min(Open, Close)`).
- **Strict Development Schedule Boundaries:**
  - **Day 4 (Current):** Implements the concrete historical market data collector adapter, input boundaries, and ingestion validation.
  - **Day 5 (Planned):** Implements data cleaning pipelines (missing values, duplicate bars, date/time sequence normalization).
  - **Day 6 (Planned):** Implements continuous returns and rolling realized volatility calculations.
  - **Day 7 (Planned):** Delivers initial market charting and end-to-end data pipeline completion.



