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

### 4.4. Market Data Layer & Cleaning Pipeline (`app/market/`)
- **Market Data Pipeline Flow:**
  ```text
  Historical Collector (YFinanceProvider)
          ↓
  Raw Market Data (MarketOHLCV)
          ↓
  Cleaning Layer (clean_market_data in app/market/cleaner.py)
          ↓
  Validated/Clean Market Data (MarketOHLCV)
          ↓
  Feature Layer (Day 6 Returns + Volatility)
  ```
- **Provider Interface & Collector (`app/market/providers/`):** `BaseMarketDataProvider` contract implemented by `YFinanceProvider` for Indian cash equities (`.NS` / `.BO`). Encapsulates all third-party DataFrame manipulations and returns canonical `MarketOHLCV` records using raw unadjusted prices (`auto_adjust=False`).
- **Data Cleaning Layer (`app/market/cleaner.py`):**
  - **Missing Values:** Quarantines records with missing/null/NaN prices or volume; zero blind interpolation or forward-fill.
  - **Duplicate Handling:** Collapses identical duplicates into 1 bar; quarantines conflicting duplicates without fabricating arbitrary consensus prices.
  - **Physical Validation:** Filters/quarantines invalid geometry (`High < max(Open, Close)`, `Low > min(Open, Close)`, non-positive prices, negative volume).
  - **Timezone Normalization:** Enforces standard `Asia/Kolkata` timezone while preserving the exact trading-session calendar date.
  - **Chronological Sorting:** Ensures records are strictly ordered by `(symbol, timestamp)` ascending.
  - **Auditable Summary:** Yields `CleaningResult` pairing cleaned records with `CleaningSummary` audit metrics.

### 4.5. Returns & Volatility Feature Engine (`app/market/returns.py`)
- **Feature Pipeline Flow:**
  ```text
  Clean Market Data
        ↓
  Return Calculations
        ↓
  Rolling Returns
        ↓
  Volatility Metrics
        ↓
  Future ML Feature Engine
  ```
- **Daily Returns:** Simple percentage return $R_t = (P_t / P_{t-1}) - 1$. First observation ($t=0$) is strictly `None` (unavailable). Safe division-by-zero protection marks return as `None` if $P_{t-1} \le 0$.
- **Rolling Returns:** Multi-session cumulative simple returns $R_{t, w} = (P_t / P_{t-w}) - 1$ over configurable windows (default 3 and 5 sessions). Points with $t < w$ remain `None`. Zero future observations are included.
- **Sample Standard Deviation:** Standard deviation computed with Bessel correction ($ddof=1$) on valid daily returns using Python standard library mathematics.
- **Rolling Realized Volatility:** Sample standard deviation of daily returns across rolling session windows (default 5 sessions). Raw daily standard deviation is the primary feature; annualized volatility is computed with explicit factor $\sqrt{252}$ for Indian equity markets.
- **Canonical Feature Container:** `ReturnFeatures` immutable dataclass with `.to_dict()` serialization and type-safe property accessors.
- **Future Indicators Boundary (Out of Scope for Day 6 & 7):** Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR) and candlestick patterns belong strictly to subsequent roadmap phases and are NOT part of the Day 7 baseline.

### 4.6. End-to-End Market Data Pipeline & Visualization (`app/market/pipeline.py` & `app/market/visualizer.py`)
- **End-to-End Pipeline Architecture Flow:**
  ```text
  Historical Collector (YFinanceProvider)
          ↓
  Data Cleaning Layer (clean_market_data)
          ↓
  Feature Layer (compute_market_returns)
          ↓
  Pipeline Orchestrator (run_market_data_pipeline)
          ↓
  Market Visualizer (generate_market_charts)
          ↓
  Processed Charts (data/processed/charts/)
  ```
- **Pipeline Orchestrator (`app/market/pipeline.py`):** Unifies collection, cleaning, and feature engineering into deterministic callable pipelines (`run_market_data_pipeline` for network workflows, `process_market_data` for offline records). Yields immutable `MarketDataPipelineResult` maintaining raw, cleaned, and feature structures with audit summaries.
- **Headless Visualization Layer (`app/market/visualizer.py`):** Utilizes Matplotlib with the non-interactive `Agg` backend to render publication-quality financial charts without display server dependencies:
  - `plot_closing_prices`: Time-series line chart with INR currency formatting and trading session dates.
  - `plot_daily_returns`: Session return bar chart with green/red positive/negative color coding and zero baseline.
  - `generate_market_charts`: Batch chart generator outputting to `data/processed/charts/` (git-ignored).

### 4.7. Technical Indicators & Momentum Engine (`app/market/indicators.py`)
- **Technical Feature Flow:**
  ```text
  Clean Market Records (MarketOHLCV)
             ↓
  Extract Chronological Series (Close Prices)
             ↓
  Compute Moving Averages (SMA & EMA: 5-day, 10-day, configurable)
             ↓
  Compute Momentum Oscillators (RSI: 14-period, configurable Wilder's smoothing)
             ↓
  Compute Trend / Convergence-Divergence (MACD: 12-fast, 26-slow, 9-signal EMA)
             ↓
  MovingAverageFeatures Dataclass (.to_dict() tabular export)
  ```
- **Price Basis:** Indicators are strictly computed using raw, unadjusted closing prices (`close`).
- **Mathematical Formulations:**
  - **Simple Moving Average (SMA):** $SMA_{t, W} = \frac{1}{W} \sum_{i=0}^{W-1} P_{t-i}$. Sessions where $t < W - 1$ return `None`.
  - **Exponential Moving Average (EMA):** $EMA_t = \alpha P_t + (1 - \alpha) EMA_{t-1}$ where $\alpha = \frac{2}{W + 1}$. Early un-warmed sessions ($t < W - 1$) return `None`.
  - **Relative Strength Index (RSI):** $RSI_t = 100 \times \frac{AvgGain_t}{AvgGain_t + AvgLoss_t}$ with Wilder's exponential smoothing ($\alpha = 1 / W$). Flat series return `50.0`, pure gains return `100.0`, pure losses return `0.0`. Sessions where $t < W$ return `None`.
  - **Moving Average Convergence Divergence (MACD):**
    - Fast EMA: $EMA_{fast, t} = EMA(prices, window=fast\_period)$ (default 12).
    - Slow EMA: $EMA_{slow, t} = EMA(prices, window=slow\_period)$ (default 26).
    - MACD Line: $MACD_t = EMA_{fast, t} - EMA_{slow, t}$. Un-warmed when $t < slow - 1$ (returns `None`).
    - Signal Line: $Signal_t = EMA(MACD, window=signal\_period)$ (default 9). Un-warmed when $t < slow + signal - 2$ (returns `None`).
    - MACD Histogram: $Histogram_t = MACD_t - Signal_t$. Returns `None` whenever Signal line is `None`. Strictly satisfies $Histogram = MACD - Signal$.
- **Zero Future-Data Leakage:** Point-in-time calculation strictly bounds inputs to observations up to and including the evaluated session timestamp.
- **Pipeline Integration:** Orchestrated within `MarketDataPipelineResult` alongside return and volatility features with configurable `lookback_days` supporting 6-12 month ranges, and configurable `macd_fast`, `macd_slow`, `macd_signal` parameters.
- **Non-Predictive Baseline:** Indicators provide descriptive trend, momentum, and divergence features; they are never treated as standalone guaranteed price-direction predictors.

- **Strict Development Schedule Boundaries:**
  - **Day 4 (Complete):** Concrete historical market data collector adapter and empirical verification.
  - **Day 5 (Complete):** Data cleaning layer (missing values, duplicates, physical anomalies, date normalization, chronological sorting).
  - **Day 6 (Complete):** Returns and rolling realized volatility feature calculations.
  - **Day 7 (Complete):** First market charting and full data pipeline completion.
  - **Day 8 (Complete):** Moving average technical indicators (SMA & EMA, configurable windows, point-in-time guarantees).
  - **Day 9 (Complete):** Expanded historical data acquisition (6-12 months lookback) and Relative Strength Index (RSI).
  - **Day 10 (Complete):** MACD technical indicator (fast/slow/signal EMAs, MACD line, signal line, histogram identity, point-in-time integrity).
  - **Day 11 (Planned):** Next scheduled milestone phase.






