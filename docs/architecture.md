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
  Extract Chronological Series (Close Prices, High, Low)
             ↓
  Compute Moving Averages (SMA & EMA: 5-day, 10-day, configurable)
             ↓
  Compute Momentum Oscillators (RSI: 14-period, configurable Wilder's smoothing)
             ↓
  Compute Trend / Convergence-Divergence (MACD: 12-fast, 26-slow, 9-signal EMA)
             ↓
  Compute Volatility Bands (Bollinger Bands: 20-period SMA, 2.0 std dev, ddof=0, Band Width, %B)
             ↓
  Compute Trading Range Volatility (ATR: 14-period True Range, Wilder's smoothing recurrence)
             ↓
  Compute Relative Price Momentum (ROC: 10-period Rate of Change percentage)
             ↓
  MovingAverageFeatures Dataclass (.to_dict() tabular export)
  ```
- **Price Basis:** Indicators are strictly computed using raw, unadjusted market prices (`close`, `high`, `low`).
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
  - **Bollinger Bands:**
    - Middle Band: $Middle_t = SMA_{t, W}$ (default $W=20$). Un-warmed when $t < W - 1$ (returns `None`).
    - Upper Band: $Upper_t = Middle_t + multiplier \times \sigma_{t, W}$ (default $multiplier=2.0$).
    - Lower Band: $Lower_t = Middle_t - multiplier \times \sigma_{t, W}$.
    - Rolling Standard Deviation: Population standard deviation ($ddof=0$) by default: $\sigma_t = \sqrt{\frac{1}{W} \sum_{i=0}^{W-1} (P_{t-i} - Middle_t)^2}$, configurable to sample standard deviation ($ddof=1$).
    - Band Width: $BandWidth_t = \frac{Upper_t - Lower_t}{Middle_t}$ when $Middle_t > 0$ (evaluates safely to `0.0` for flat series, `None` if middle is non-positive).
    - Percent B (%B): $\%B_t = \frac{Close_t - Lower_t}{Upper_t - Lower_t}$ when $Upper_t > Lower_t$ (evaluates safely to `None` for flat series where denominator is zero).
  - **Average True Range (ATR):**
    - True Range ($TR_t$): For session $t=0$: $TR_0 = High_0 - Low_0$ when valid. For sessions $t > 0$: $TR_t = \max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|)$.
    - Initial Seed ($t = period - 1$, e.g., $t=13$ for $period=14$): Simple arithmetic mean of first 14 True Range values: $ATR_{13} = \frac{1}{14} \sum_{i=0}^{13} TR_i$.
    - Wilder Smoothing Recurrence ($t \ge period$): $ATR_t = \frac{(period - 1) \times ATR_{t-1} + TR_t}{period}$.
    - Un-warmed sessions ($t < period - 1$) return `None`.
    - Volatility character: strictly measures price movement range without directional bias; does not predict the direction of the next move.
  - **Rate of Change (ROC):**
    - Formula: $ROC_{t, n} = \left(\frac{Close_t}{Close_{t-n}} - 1\right) \times 100$ (default $n=10$ sessions).
    - Un-warmed sessions ($t < n$) return `None`.
    - Division safety: handles non-positive previous closes safely by returning `None`; flat series evaluate safely to `0.0`.
    - Momentum character: measures relative percentage change over historical lookback window; does not guarantee price direction.
- **Zero Future-Data Leakage:** Point-in-time calculation strictly bounds inputs to observations up to and including the evaluated session timestamp.
- **Pipeline Integration:** Orchestrated within `MarketDataPipelineResult` alongside return and volatility features with configurable `lookback_days` supporting 6-12 month ranges, configurable MACD (`macd_fast`, `macd_slow`, `macd_signal`), configurable Bollinger Bands (`bb_window`, `bb_multiplier`, `bb_ddof`), and configurable ATR/ROC (`atr_periods=(14,)`, `roc_periods=(10,)`).
- **Non-Predictive Baseline:** Indicators provide descriptive trend, momentum, volatility, and divergence features; they are never treated as standalone guaranteed price-direction predictors.

- **Strict Development Schedule Boundaries:**
  - **Day 4 (Complete):** Concrete historical market data collector adapter and empirical verification.
  - **Day 5 (Complete):** Data cleaning layer (missing values, duplicates, physical anomalies, date normalization, chronological sorting).
  - **Day 6 (Complete):** Returns and rolling realized volatility feature calculations.
  - **Day 7 (Complete):** First market charting and full data pipeline completion.
  - **Day 8 (Complete):** Moving average technical indicators (SMA & EMA, configurable windows, point-in-time guarantees).
  - **Day 9 (Complete):** Expanded historical data acquisition (6-12 months lookback) and Relative Strength Index (RSI).
### 4.8. Candlestick Feature Engine (`app/market/candlestick.py`)
- **Candlestick Geometric Feature Flow:**
  ```text
  Clean Market Records (MarketOHLCV)
             ↓
  Extract Contemporaneous Bar OHLC (Open, High, Low, Close)
             ↓
  Validate Physical Geometry (High >= Low, High >= max(Open, Close), Low <= min(Open, Close))
             ↓
  Compute Geometric Dimensions (Body, Abs Body, Range, Upper Wick, Lower Wick)
             ↓
  Compute Normalizing Ratios & Bounds (Body Ratio, Upper Wick Ratio, Lower Wick Ratio)
             ↓
  Compute Intra-Session Location & Momentum (Close Location within Range, Body Return %)
             ↓
  Classify Intra-Session Direction (Bullish if Close > Open, Bearish if Close < Open, Neutral)
             ↓
  CandlestickFeatures Dataclass (.to_dict() tabular export & Pipeline Integration)
  ```
- **Mathematical Formulations:**
  - **Signed Body:** $Close - Open$
  - **Absolute Body:** $|Close - Open|$
  - **Candle Range:** $High - Low$
  - **Upper Wick:** $High - \max(Open, Close)$
  - **Lower Wick:** $\min(Open, Close) - Low$
  - **Body-to-Range Ratio:** $\frac{|Close - Open|}{High - Low}$, when $Range > 0$ (evaluates safely to `None` when $Range = 0$)
  - **Upper-Wick-to-Range Ratio:** $\frac{UpperWick}{High - Low}$, when $Range > 0$ (evaluates safely to `None` when $Range = 0$)
  - **Lower-Wick-to-Range Ratio:** $\frac{LowerWick}{High - Low}$, when $Range > 0$ (evaluates safely to `None` when $Range = 0$)
  - **Close Location within Range:** $\frac{Close - Low}{High - Low}$, when $Range > 0$ (evaluates safely to `None` when $Range = 0$)
  - **Body Return Percentage:** $\left(\frac{Close}{Open} - 1\right) \times 100$, when $Open > 0$ (evaluates safely to `None` when $Open \le 0$)
  - **Candle Direction:** `bullish` if $Close > Open$, `bearish` if $Close < Open$, and `neutral` if $Close == Open$.
- **Invariants & Geometric Identities:**
  - **Geometric Partition Invariant:** $Body_{abs} + UpperWick + LowerWick = Range$.
  - **Ratio Partition Invariant:** $Ratio_{body} + Ratio_{upper} + Ratio_{lower} = 1.0$ (when $Range > 0$).
  - **Bounded Properties:** $0.0 \le Ratio \le 1.0$ and $0.0 \le CloseLocation \le 1.0$ across all valid non-zero candles.
  - **Zero-Range Policy:** Zero dimensions are preserved ($Body=0.0, Range=0.0, Upper=0.0, Lower=0.0$), ratios evaluate strictly to `None`, and direction evaluates to `neutral`.
  - **Physical Geometry Protection:** Invalid candles (violating $High \ge \max(Open, Close)$ or $Low \le \min(Open, Close)$) or non-finite prices are safely masked with `None`.
- **Pipeline Integration:** Orchestrated within `MarketDataPipelineResult.candlesticks` via `compute_candlestick_features` and integrated into `MovingAverageFeatures` and `.to_indicator_dicts()` for tabular datasets.
- **Strict Point-in-Time Guarantees:** Computed strictly from the contemporaneous candle's OHLC; zero future bars affect earlier candle features.
- **Non-Predictive Disclaimer:** Candlestick features quantify single-bar geometric price action and intra-session dynamics; they do not constitute guaranteed buy/sell signals or predictive forecasts.

- **Strict Development Schedule Boundaries:**
  - **Day 4 (Complete):** Concrete historical market data collector adapter and empirical verification.
  - **Day 5 (Complete):** Data cleaning layer (missing values, duplicates, physical anomalies, date normalization, chronological sorting).
  - **Day 6 (Complete):** Returns and rolling realized volatility feature calculations.
  - **Day 7 (Complete):** First market charting and full data pipeline completion.
  - **Day 8 (Complete):** Moving average technical indicators (SMA & EMA, configurable windows, point-in-time guarantees).
  - **Day 9 (Complete):** Expanded historical data acquisition (6-12 months lookback) and Relative Strength Index (RSI).
  - **Day 10 (Complete):** MACD technical indicator (fast/slow/signal EMAs, MACD line, signal line, histogram identity, point-in-time integrity).
  - **Day 11 (Complete):** Bollinger Bands technical indicator (middle, upper, lower bands, bandwidth, percent B, configurable window/multiplier/ddof, safe zero-denominator handling).
  - **Day 12 (Complete):** Volatility and momentum technical features: Average True Range (ATR-14 with Wilder's recurrence and first-session policy) and Rate of Change (ROC-10 with safe division and flat-price zero handling).
  - **Day 13 (Complete):** Candlestick feature engine (signed/abs body, range, upper/lower wicks, normalizing ratios, close location, return %, direction, zero-range safe division, physical geometry validation, pipeline integration).
  - **Day 14 (Complete):** Trend engine and market structure analysis layer (confirmed swing highs/lows with $t + k$ confirmation timing, market structure labeling HH/HL/LH/LL, UPTREND/DOWNTREND/SIDEWAYS classification, rolling point-in-time alignment, pipeline integration).
  - **Day 15 (Complete):** ML prediction target definition (next-session direction, close-to-close return formulation, zero-return baseline policy, non-calendar trading session alignment, missing final target invariant, zero temporal leakage).
  - **Day 16 (Complete):** Technical feature matrix assembly (canonical 37 numeric features, strict X/y isolation guard, explicit timestamp key joins, natural warmup missing-value preservation, transparent labeled subset extraction accounting).
  - **Day 17 (Planned):** First baseline ML model training (XGBoost/LightGBM) and walk-forward evaluation.

### 4.9. Trend Engine & Market Structure Analysis Layer (`app/market/trend.py`)
- **Trend Engine Structural Flow:**
  ```text
  Clean Chronological Bars (MarketOHLCV)
             ↓
  Deterministic Local Swing Detection (identify_swings with configurable flank window k)
             ↓
  Enforce Explicit Confirmation Timing (Pivots at t confirm strictly at t + k)
             ↓
  Point-in-Time Cutoff Filtering (Only pivots confirmed at or before evaluation index T are visible)
             ↓
  Market Structure Transition Labeling (HH, HL, LH, LL relative to preceding confirmed swing)
             ↓
  Rule-Based Structural Trend Classification (UPTREND, DOWNTREND, SIDEWAYS, INSUFFICIENT_DATA)
             ↓
  TrendAnalysisResult Dataclass (.to_dict() serialization, summary metrics, pipeline integration)
  ```
- **Swing Detection Rules:**
  - **Swing High:** A bar at index $t$ is an identified swing high if $High_t > High_{t-i}$ for all $1 \le i \le k$ (left flank) and $High_t \ge High_{t+j}$ for all $1 \le j \le k$ (right flank). The asymmetric strictness on the left flank prevents duplicate identical pivots during multi-bar price peaks.
  - **Swing Low:** A bar at index $t$ is an identified swing low if $Low_t < Low_{t-i}$ for all $1 \le i \le k$ (left flank) and $Low_t \le Low_{t+j}$ for all $1 \le j \le k$ (right flank).
  - **Configurable Comparison Window:** The flank window parameter $k$ (`swing_window`, default 2) is configurable.
- **Confirmation Timing & Look-Ahead Bias Safeguards:**
  - A swing pivot occurring at bar index $t$ is confirmed strictly when bar $t + k$ closes.
  - When evaluating market structure at bar $T$ (as-of index), only swing points with `confirmation_index <= T` are considered confirmed and accessible to classification.
  - Unconfirmed candidate pivots in the trailing $k$ bars ($t > T - k$) remain strictly invisible point-in-time.
- **Market Structure Classification Rules:**
  - **Higher High (HH):** $High_n > High_{n-1}$.
  - **Lower High (LH):** $High_n < High_{n-1}$.
  - **Higher Low (HL):** $Low_n > Low_{n-1}$.
  - **Lower Low (LL):** $Low_n < Low_{n-1}$.
  - **Evidence Requirements:** Minimum of `min_swings` (default 2) confirmed swing highs and 2 confirmed swing lows required.
  - **Classification Matrix:**
    - `UPTREND`: Latest confirmed swing high is `HH` AND latest confirmed swing low is `HL`.
    - `DOWNTREND`: Latest confirmed swing high is `LH` AND latest confirmed swing low is `LL`.
    - `SIDEWAYS`: Sufficient confirmed swings exist, but directional evidence is mixed, conflicting, or consolidating (e.g. `HH` + `LL`, `LH` + `HL`, `EH`, `EL`).
    - `None` (`INSUFFICIENT_DATA`): Evaluates safely to `None` with status `INSUFFICIENT_DATA` when fewer than `min_swings` confirmed pivots exist. Insufficient history is never mislabeled as `SIDEWAYS`.
- **Pipeline Integration:** Orchestrated within `MarketDataPipelineResult.trend` via `analyze_market_trend` and attached to summary dictionaries (`"trend_classification"`, `"trend"`).
- **Point-in-Time Rolling Series Alignment:** `compute_rolling_trends` generates a 1:1 aligned sequence of historical classifications across all bars with zero future leakage.
- **Non-Predictive Disclaimer:** Trend classification reflects historical structural price action geometry; it is strictly descriptive and does not constitute guaranteed directional continuation, price forecasting, or investment advice.

### 4.10. Machine Learning Prediction Target Definition (`app/prediction/target.py`)
- **Prediction Target Mathematical Flow:**
  ```text
  Clean Chronological Bars (MarketOHLCV) sorted by (symbol, timestamp)
             ↓
  Extract Reference Close (Close_t at session t)
             ↓
  Identify Next Available Trading Session Close (Close_{t+1} at session t+1)
             ↓
  Compute Forward Percentage Return: target_return[t] = (Close_{t+1} / Close_t) - 1.0
             ↓
  Apply Binary Classification Rule:
    - UP (binary 1) if target_return[t] > 0.0
    - DOWN (binary 0) if target_return[t] <= 0.0 (zero-return sessions grouped into DOWN)
             ↓
  Final Session Policy: Latest session (t = N - 1) has no realized future; target is strictly None
             ↓
  TargetObservation Dataclass (.to_dict() tabular export, feature-outcome isolation)
  ```
- **Mathematical Formulations:**
  - **Forward Target Return:** $target\_return[t] = \frac{Close_{t+1}}{Close_t} - 1.0$.
  - **Directional Target:** $\text{"UP"}$ if $target\_return[t] > 0.0$, else $\text{"DOWN"}$.
  - **Binary Target:** $1$ if $target\_return[t] > 0.0$, else $0$.
- **Zero-Return Baseline Policy:**
  - Sessions where $Close_{t+1} == Close_t$ produce an exact $0.0\%$ return. For this initial binary baseline, they are grouped deterministically into `"DOWN"` ($binary=0$). They are explicitly retained and not discarded.
- **Trading Session Spacing (Calendar Independence):**
  - Next session $t+1$ represents the next available trading day in the sequence. Weekends, market holidays, and special trading sessions do not require calendar day interpolation.
- **Temporal Leakage Safeguards & Missing Outcome Invariant:**
  - Input features at time $t$ utilize exclusively data available at or before session $t$.
  - Future closing prices ($Close_{t+1}$) and forward returns are strictly outcome labels, never included as input features.
  - For the final session in the dataset ($t = N - 1$), the target evaluates strictly to `None` with `has_target=False` (never forward-filled or fabricated).
- **Component Separation:** Target definitions are isolated in `app/prediction/target.py`, separate from technical feature calculators (`app/market/`) and model training (`app/training/`).

### 4.11. Technical Feature Matrix Assembly Layer (`app/training/feature_matrix.py`)
- **Dataset Assembly Workflow:**
  ```text
  Clean Market Records (MarketOHLCV)
             ↓
  Orchestrate Pipelines:
    - Technical Indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ROC, Candlesticks)
    - Point-in-Time Trend Regimes (compute_rolling_trends)
    - Day 15 Direction Targets (generate_direction_targets)
             ↓
  Explicit Timestamp Key Join on (symbol, timestamp)
             ↓
  Feature Matrix (X) & Target (y) Strict Isolation Guard:
    - Verifies zero forbidden columns in X (next_*, target_*, outcome_*, future_*)
             ↓
  Preserve Natural Warmup Missing Values (NaN) without blind zero-filling
             ↓
  FeatureMatrixDataset Container (.df, .X, .y, .metadata, .get_labeled_dataset())
  ```
- **Canonical 37 Numeric Features in Matrix $X$:**
  1. *OHLCV Raw Dynamics:* `open`, `high`, `low`, `close`, `volume`.
  2. *Returns & Volatility:* `daily_return`, `rolling_return_3d`, `rolling_return_5d`, `rolling_volatility_5d`, `annualized_volatility_5d`.
  3. *Moving Averages:* `sma_5`, `sma_10`, `ema_5`, `ema_10`.
  4. *Momentum Oscillators:* `rsi_14`, `macd`, `macd_signal`, `macd_histogram`.
  5. *Volatility Bands:* `bb_middle`, `bb_upper`, `bb_lower`, `bb_bandwidth`, `bb_percent_b`.
  6. *Range Volatility & Velocity:* `atr_14`, `roc_10`.
  7. *Candlestick Geometry & Direction:* `candle_body`, `candle_body_abs`, `candle_range`, `candle_upper_wick`, `candle_lower_wick`, `candle_body_ratio`, `candle_upper_wick_ratio`, `candle_lower_wick_ratio`, `candle_close_location`, `candle_body_return_pct`, `candle_direction_encoded` (+1.0 bullish, -1.0 bearish, 0.0 neutral).
  8. *Trend Structure:* `trend_regime_encoded` (+1.0 UPTREND, -1.0 DOWNTREND, 0.0 SIDEWAYS, NaN unconfirmed).
- **Strict Leakage Prevention & Guard:**
  - Automated `validate_feature_matrix_isolation(X)` ensures target direction, binary target, forward return, next-session close, and outcome timestamps cannot enter the feature space.
  - Final historical observation strictly has target `y = NaN` (unlabeled).
- **Preservation of Warmup Missing Values:**
  - Indicator warmups (e.g. 33 un-warmed sessions for MACD-26/Signal-9) naturally produce `np.nan`.
  - Zero-filling is strictly forbidden; imputation and scaling must be fitted on training folds only (Day 17) to prevent global leakage.
- **Labeled Dataset Extraction Accounting:**
  - `FeatureMatrixDataset.get_labeled_dataset()` transparently reports initial rows, unlabeled final row exclusions, optional warmup exclusions, and retained training rows.

### 4.12. Baseline XGBoost Direction Classifier Layer (`app/training/xgboost_classifier.py`)
- **Training Workflow Flow:**
  ```text
  FeatureMatrixDataset (Day 16)
             ↓
  Extract Complete Labeled Rows (drop_incomplete_warmup=True)
             ↓
  Chronological Holdout Partitioning (split_chronological_holdout):
    - Train Partition (e.g. 70 sessions)
    - 1-Session Embargo Gap (purged to prevent label outcome leakage)
    - Holdout Partition (e.g. 18 sessions)
             ↓
  Verify Temporal Invariant: train_outcome_cutoff <= holdout_start_date
             ↓
  Fit Native XGBoost Binary Classifier (XGBoostDirectionClassifier):
    - Objective: binary:logistic
    - Metric: logloss
    - Fixed seed: 42
    - Conservative baseline: max_depth=3, lr=0.05, n_estimators=50
             ↓
  Holdout Evaluation & Metrics (compute_classification_metrics):
    - Accuracy, Precision, Recall, F1, Confusion Matrix
    - Pure Python / NumPy metrics engine (zero sklearn dependency)
             ↓
  Deterministic Inference & Serialization (.save_model() to JSON)
  ```
- **Temporal Integrity & Outcome Embargo:**
  - Because target label $y_t$ realizes at session $t+1$, the final training observation $t_{train}$ would observe the close price of session $t_{train}+1$.
  - An explicit 1-session embargo gap purges session $t_{train}$, guaranteeing that every training label's outcome timestamp strictly precedes the first session in the holdout partition.
- **Lean Dependency Architecture:**
  - Employs native `xgb.train()` and `xgb.DMatrix()` to eliminate the heavy `scikit-learn` dependency.
  - Metrics are evaluated with built-in arithmetic and standard library typing.
- **Research Baseline Policy:**
  - Model outputs represent non-calibrated directional probabilities for baseline benchmarking (Phase 4).
  - Explicitly disclaims commercial trading viability or predictive guarantees.

### 4.13. Baseline Comparison & Evaluation Framework (`app/training/baselines.py`)
- **Comparative Evaluation Flow:**
  ```text
  FeatureMatrixDataset (Day 16)
             ↓
  Chronological Holdout Partition with 1-Session Embargo (Day 17)
             ↓
  Parallel Strategy Evaluation on Identical Holdout Observations (N=18):
    ├── Baseline A: MajorityClassClassifier (predicts training majority, e.g. UP)
    ├── Baseline B1: RandomClassifier (Uniform coin flip, P(UP)=0.5, seed=42)
    ├── Baseline B2: RandomClassifier (Stratified empirical train prior, P(UP)=0.5143, seed=42)
    └── Model C: XGBoostDirectionClassifier (Day 17 conservative baseline, seed=42)
             ↓
  Unified Metrics Extraction (compute_classification_metrics):
    - Accuracy, Precision, Recall, F1, Confusion Matrix, Prediction Counts
             ↓
  Comparative Audit Report (BaselineComparisonReport):
    - Determines whether ML model beats non-parametric baselines
    - Detects directional prediction bias (e.g. constant UP predictions)
    - Formal progression gate prior to hyperparameter tuning
  ```
- **Evaluation Parity Principles:**
  - **Shared Data & Partitioning:** All strategies evaluate on identical test indices without partition drift.
  - **Leakage Immunity:** Majority and stratified baselines consume exclusively training labels (`y_train`). Holdout labels are completely invisible.
  - **Honest Defect Identification:** Exposes when complex models underperform simple coin flips or majority voting before escalating complexity.

### 4.14. Multi-Year Historical Evaluation & LightGBM Direction Classifier (`app/training/lightgbm_classifier.py`)
- **Multi-Year Evaluation Architecture:**
  ```text
  5-Year Historical Market Data (1,234 sessions, BHARTIARTL.NS)
             ↓
  Data Cleaning & Corporate Actions Audit (auto_adjust=False, ADR 46)
             ↓
  Feature Matrix Assembly (37 features, 1,198 complete labeled rows)
             ↓
  Chronological Holdout Partitioning with 1-Session Embargo:
    - Train Partition: 957 sessions (2021-12-03 to 2025-10-16, 80%)
    - Embargo Gap: 1 session (2025-10-17, purged to prevent label leakage)
    - Holdout Partition: 240 sessions (2025-10-20 to 2026-10-09, 20%)
             ↓
  Benchmarking Across Identical Test Samples (N=240):
    ├── Baseline A: Majority-Class Classifier (50.00% Acc)
    ├── Baseline B1: Uniform Random (50.14% +/- 3.19% across 50 seeds)
    ├── Baseline B2: Stratified Random (49.72% +/- 3.24% across 50 seeds)
    ├── Model C: XGBoost Direction Classifier (54.17% Acc, 0.5528 UP F1)
    └── Model D: LightGBM Direction Classifier (53.75% Acc, 0.5394 UP F1)
             ↓
  Baseline Comparison Report & Statistical Power Validation
  ```
- **LightGBM Direction Classifier Baseline:**
  - Implemented in `app/training/lightgbm_classifier.py` using native `lgb.train()` and `lgb.Dataset()`.
  - Configured with symmetrical baseline hyperparameters matching XGBoost: `max_depth=3`, `num_leaves=7`, `learning_rate=0.05`, `n_estimators=50`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42`, `num_threads=1`, `deterministic=True`.
  - Feature isolation verified via `validate_feature_matrix_isolation(X)` to guarantee zero target or outcome leakage.
- **Statistical Significance & Sample Size Expansion:**
  - Expanding from Day 18's 18 sessions to Day 19's 240 holdout sessions reduced random baseline standard deviation from ±14.16% to ±3.19%, providing genuine statistical confidence.
  - Both XGBoost (54.17%) and LightGBM (53.75%) produce balanced predictions (~50/50 UP/DOWN) and outperform the majority-class heuristic (50.00%) by ~4 percentage points.
  - Documented disclaimer: ~54% out-of-sample directional accuracy provides preliminary evidence of signal, but does not guarantee live trading profitability after execution slippage and transaction costs.

### 4.15. Walk-Forward Temporal Cross-Validation Layer (`app/training/walk_forward.py`)
- **Walk-Forward Validation Architecture:**
  ```text
  Complete Labeled Feature Matrix (N rows sorted chronologically by timestamp)
             ↓
  Expanding-Window Fold Generation (generate_walk_forward_splits):
    - Configurable initial training ratio: min_train_ratio=0.4 (N_train_init = max(min_train_samples, floor(N * min_train_ratio)), min_train_samples=20)
    - Configurable validation fold count: n_splits=5 (val_size = (N - N_train_init) // n_splits >= min_val_samples=5)
    - Mandatory outcome embargo: embargo_sessions=1 (purged between train & val to prevent forward target leakage)
    - K Expanding Folds: Fold k trains on [0 : v_start - embargo_sessions), embargos [v_start - embargo_sessions : v_start), validates on [v_start : v_end)
             ↓
  Temporal Integrity & Leakage Invariants:
    - Train outcome cutoff: next_timestamp of last train observation strictly <= val_start_date
    - Disjoint index invariant: Train ∩ Embargo = ∅, Embargo ∩ Val = ∅, Train ∩ Val = ∅
    - Monotonically expanding training windows: |Train_{k+1}| > |Train_k|
             ↓
  Parallel Strategy Evaluation on Identical Fold Partitions:
    ├── Baseline A: MajorityClassClassifier (train majority, single-class guard)
    ├── Baseline B1: RandomClassifier (Uniform coin flip, P=0.5, pre-declared seed)
    ├── Baseline B2: RandomClassifier (Stratified random, P=train_prior, pre-declared seed)
    ├── Model C: XGBoostDirectionClassifier (Day 17 conservative baseline, unchanged params)
    └── Model D: LightGBMDirectionClassifier (Day 19 symmetrical baseline, unchanged params)
             ↓
  Dual Aggregation Protocol (WalkForwardReport):
    - Macro-averaged metrics: unweighted fold mean ± sample standard deviation (ddof=1)
    - Micro-pooled metrics: global sum of confusion matrices across all validation sessions
    - Detailed per-fold breakdown table with class distributions and boundary dates
  ```
- **Temporal Leakage Safeguards:**
  - **Outcome Embargo Invariant:** Because target label $y_t$ realizes at session $t+1$, an observation at time $t_{train}$ consumes price data from $t_{train}+1$. An explicit embargo of $\ge 1$ sessions is strictly purged between the training window and validation window, guaranteeing `train_outcome_cutoff <= val_start_date` across all folds.
  - **Strict Split Isolation:** The validation dataset is strictly out-of-sample. Models and baselines are fit exclusively on the training fold; zero hyperparameter tuning, model selection, or feature engineering is permitted using validation feedback.
  - **Feature Matrix Isolation Guard:** Feature matrices are checked via `validate_feature_matrix_isolation` to ensure no target columns, outcome timestamps, or future prices can enter the model.
- **Robustness & Edge-Case Handling:**
  - **Strict Input Validation & Target Integrity:** Tuple inputs validate length equality between $X$ and $y$. DataFrames must contain `target_binary`. Target labels must be non-null and belong strictly to $\{0, 1\}$; unknown or invalid labels are immediately rejected.
  - **Separate Handling of Undersized vs Single-Class Folds:** Undersized training partitions ($N_{train} < min\_train\_samples$) and undersized validation partitions ($N_{val} < min\_val\_samples$) record distinct `SKIPPED_UNDERSIZED_TRAIN` and `SKIPPED_UNDERSIZED_VAL` statuses with explicit reasons, strictly separated from `SKIPPED_SINGLE_CLASS`.
  - **Zero Metric Fabrication Policy:** Skipped fold evaluations record `metrics=None` with zero dummy predictions or fabricated accuracies. Markdown tables display `N/A` or `SKIP` rather than defaulting to `0.0%`.
  - **Reproducibility:** Random baselines use deterministic, pre-declared seeds (seed = `random_seed + fold`) for absolute reproducibility across repeated runs.
- **Empirical Multi-Regime Findings (Day 20 BHARTIARTL.NS Verification):**
  - Walk-forward evaluation across 5 expanding folds (720 total out-of-sample sessions from Nov 2023 to Oct 2026) revealed that Bharti Airtel experienced a sustained secular bull regime during 2023–2024, raising the Majority-Class baseline accuracy to **52.36% ± 2.53%**.
  - LightGBM achieved **51.25% ± 5.16%** macro mean accuracy (pooled 51.25%), while XGBoost achieved **50.69% ± 3.74%** (pooled 50.69%).
  - Walk-forward cross-validation exposed market-regime sensitivity that was invisible in a single static holdout, proving the necessity of multi-fold temporal validation before claiming predictive edge.

### 4.16. Model Error Analysis & Feature Usefulness Audit Layer (`app/training/error_analysis.py`)
- **Error Decomposition & Symmetrical Class Evaluation:**
  - Standard binary classification metrics often emphasize the positive (UP) class. In financial direction forecasting with an upward market drift, a trivial majority-class heuristic attains deceptively high accuracy and 100% UP recall by never predicting a downward move.
  - `FoldErrorAnalysis` computes symmetrical class metrics for both directions: Accuracy, Precision UP/DOWN, Recall UP/DOWN, and F1 UP/DOWN, alongside confusion matrix breakdown (`[TN, FP / FN, TP]`) and predicted vs actual directional counts.
  - Directional prediction bias is explicitly flagged: models predicting 100% UP or 100% DOWN are detected (`is_systematic_direction=True`).
  - Distribution shift between expanding training partitions and out-of-sample validation folds is tracked ($Shift = Val\_UP\% - Train\_UP\%$) to diagnose regime-driven performance degradation.
  - Performance delta relative to the Majority-Class baseline ($Accuracy_{model} - Accuracy_{majority}$) is calculated per fold.
- **Feature Matrix Quality & Collinearity Audit:**
  - Implemented in `audit_feature_usefulness()` with strict training isolation: diagnostics (missingness, constant column checks, variance, min/max, pairwise Pearson correlation) are computed solely on training partitions ($X_{train}$), preventing data leakage into validation folds.
  - Enforces `validate_feature_matrix_isolation()` to ensure no target or future-outcome columns enter feature quality assessments.
  - Detects collinear feature clusters with Pearson $|r| \ge 0.90$. On the canonical 37-feature matrix for `BHARTIARTL.NS`, 59 high-collinearity pairs were identified (e.g., raw OHLC price pairs, moving average pairs, and volatility proxies), cataloging them as candidates for future architectural simplification.
- **Exploratory Tree Feature Importance Protocol:**
  - Extracts native booster feature importance metrics: split weight for XGBoost (`booster.get_score(importance_type="weight")`) and split count for LightGBM (`booster.feature_importance(importance_type="split")`).
  - Strict scientific distinction: tree split counts are documented as exploratory model properties describing tree partition frequency, NOT causal proof of predictive signal or economic alpha.
  - Feature selection or pruning based on holdout cross-validation results is strictly prohibited to prevent meta-overfitting.
- **Empirical Findings on BHARTIARTL.NS (Day 21 Verification):**
  - **Downside Capture:** While Majority Class fails completely on downward sessions (0.0% DOWN Precision/Recall/F1), XGBoost and LightGBM capture downward moves with 45–64% DOWN F1 and up to 73–90% DOWN Recall across folds.
  - **Regime Outperformance:** In Fold 4 (where validation UP ratio dropped to 49.3%), tree models strongly outperformed Majority Class (+6.9% for XGBoost, +9.0% for LightGBM). In strong bull folds (Fold 1, Val UP 56.2%), tree models lagged majority class because they actively hedged downside risk.
  - **Feature Importance Agreement:** Both XGBoost and LightGBM independently identified short-term volatility (`rolling_volatility_5d`, `bb_bandwidth`), candlestick geometry (`candle_body_ratio`, `candle_body_abs`), and momentum (`rolling_return_5d`, `macd_signal`) as the most utilized split features.

### 4.17. Prediction Engine Service Layer (`app/prediction/service.py`)
- **Prediction Service Architecture:**
  ```text
  PredictionRequest(symbol, model_name, as_of_date, lookback_days)
             ↓
  Market Data Ingestion (run_market_data_pipeline via BaseMarketDataProvider)
             ↓
  Data Cleaning & Quality Audit (CleaningSummary, warmup >= 34 bars, staleness check)
             ↓
  Canonical Feature Matrix Assembly (37 features via assemble_feature_matrix)
             ↓
  Inference Observation Extraction (final observation t = N - 1, strictly unlabeled)
             ↓
  Feature Isolation Guard (validate_feature_matrix_isolation rejects target/outcome columns)
             ↓
  Model Resolution & Schema Verification (preloaded, in-memory registry, or disk artifact)
    - Prohibits silent retraining: returns MODEL_UNAVAILABLE if artifact absent
    - Verifies feature order against FEATURE_COLUMNS
             ↓
  Model Inference (model.predict_proba -> P(UP), P(DOWN), binary direction label)
             ↓
  PredictionResult(symbol, direction, probabilities, timestamps, data_quality, disclaimer)
  ```
- **Inference Anti-Leakage Safeguards:**
  - **Point-in-Time Scope:** Data retrieval is strictly bounded by `as_of_date` (or current timestamp), preventing forward information leakage.
  - **Unlabeled Inference Row:** The prediction observation corresponds to session $t = N - 1$, which naturally has no forward target realized (`has_target=False`).
  - **Feature Matrix Isolation:** `validate_feature_matrix_isolation` validates that zero target or outcome columns (`target_*`, `next_*`, `future_*`, `outcome_*`) enter inference.
  - **Strict Feature Ordering:** Feature matrix columns are strictly sorted by canonical `FEATURE_COLUMNS` before passing to booster `predict_proba`.
- **Model Lifecycle Isolation:**
  - Separation of concerns: inference strictly consumes pre-existing model artifacts.
  - Automatic on-the-fly retraining during `predict()` is prohibited to protect model auditability and avoid silent model drift.
  - Models are trained and serialized deliberately using `train_and_persist_baseline_model()`.
- **Explicit Boundary Disclosures:**
  - `PredictionResult` outputs binary direction (`UP` or `DOWN`) and probability.
  - Target prices, percentage return forecasts, and narrative rationales are NOT fabricated.
  - Explicit disclaimer attached to every prediction payload disclosing that predictions reflect directional classification without commercial edge guarantee.

### 4.18. Structured Prediction Output Layer & Transparency Guarantees (`app/prediction/contract.py`)
- **Prediction Output Architecture:**
  ```text
  PredictionResult Payload:
    ├── Core Inference Fields:
    │     ├── symbol: str (e.g. 'BHARTIARTL')
    │     ├── status: PredictionStatus (SUCCESS, MODEL_UNAVAILABLE, INSUFFICIENT_DATA, etc.)
    │     ├── predicted_direction: 'UP' | 'DOWN' | None
    │     └── predicted_label: 1 | 0 | None
    ├── Transparency & Probability Calibration Fields:
    │     ├── probability_up: float (P(UP) in [0.0, 1.0])
    │     ├── probability_down: float (P(DOWN) in [0.0, 1.0], P(UP) + P(DOWN) == 1.00)
    │     ├── is_probability_calibrated: bool (strictly False for uncalibrated tree outputs)
    │     └── probability_calibration: str ("uncalibrated")
    ├── Expected Movement Boundary Fields:
    │     ├── expected_movement: float | None (strictly None for directional classifiers)
    │     └── expected_movement_status: str ("UNSUPPORTED")
    ├── Temporal Provenance Fields:
    │     ├── prediction_timestamp: ISO 8601 UTC string (execution timestamp)
    │     └── latest_input_timestamp: ISO 8601 string (market observation timestamp)
    ├── Model Provenance Metadata:
    │     ├── model_name: 'xgboost' | 'lightgbm'
    │     ├── model_version: str (e.g. 'xgboost-direction-v1')
    │     └── model_metadata: Dict[str, Any] (hyperparameter configuration)
    ├── Input Data Quality Container:
    │     ├── total_bars_fetched: int
    │     ├── cleaned_bars: int
    │     ├── warmup_bars_required: int (34)
    │     ├── warmup_complete: bool
    │     └── missing_feature_count: int (0 on success)
    └── Capability Boundaries & Disclaimer:
          └── disclaimer: str (explicit disclosure that predictions do not constitute financial advice)
  ```
- **Probability Calibration Transparency:**
  - Raw probabilities generated by tree boosters (`predict_proba`) represent leaf sample ratios and split frequencies.
  - To prevent misleading consumers into treating raw model probabilities as calibrated Bayesian confidence, the schema explicitly sets `is_probability_calibrated = False` and `probability_calibration = "uncalibrated"`.
- **Expected Movement Boundary Enforcement:**
  - Directional classifiers are trained exclusively on binary target labels ($y \in \{0, 1\}$).
  - Price movement magnitude ($\Delta Close$) and percentage return ($R$) are not modeled.
  - Rather than fabricating target prices (e.g., ₹1,850.00) or heuristic expected returns, `expected_movement` is strictly returned as `None` with an explicit `expected_movement_status = "UNSUPPORTED"`.
- **Lossless Serialization & Presentation:**
  - `.to_dict()` provides recursive conversion to native Python dictionaries suitable for JSON transmission to downstream databases or REST APIs.
  - `.format_summary()` provides standardized, human-readable terminal/log formatting for operations and verification audits.

### 4.19. Prediction History & Relational Storage Layer (`app/database/`)
- **Architectural Overview (Phase 6 / Day 24):**
  ```text
  PredictionResult
         ↓
  PredictionRepository.save_prediction(result)
         ├── 1. Upsert Stock (stocks table: symbol, company_name, exchange)
         ├── 2. Register Model Version (model_versions: model_name, version, hyperparameters JSON)
         └── 3. Insert Prediction (predictions table)
                    ├── Indexed queryable columns (symbol, timestamps, status, probabilities)
                    ├── Preserved Day 23 semantics (is_calibrated=0, movement=None)
                    └── Full lossless raw JSON (raw_result_json)
                           ↓
  Immutability Enforcement via SQLite Engine Triggers:
    ├── UPDATE -> RAISE(ABORT, 'Predictions are immutable: updates are strictly prohibited.')
    └── DELETE -> RAISE(ABORT, 'Predictions are immutable: deletions are strictly prohibited.')
  ```
- **Relational Schema Design:**
  - **`stocks`**: Equities metadata (`symbol` PK, `company_name`, `exchange` default 'NSE', `is_active`, `created_at`).
  - **`model_versions`**: Registered model configurations (`id` PK, `model_name`, `model_version`, `hyperparameters` JSON, `created_at`, unique on `(model_name, model_version)`).
  - **`predictions`**: Immutable record of all prediction attempts (`id` PK, `prediction_id` UNIQUE, `symbol` FK, `model_name`, `model_version`, `prediction_timestamp`, `latest_input_timestamp`, `status`, `predicted_direction`, `predicted_label`, `probability_up`, `probability_down`, `is_probability_calibrated`, `probability_calibration`, `expected_movement`, `expected_movement_status`, `total_bars_fetched`, `cleaned_bars`, `warmup_bars_required`, `warmup_complete`, `missing_feature_count`, `error_message`, `disclaimer`, `raw_result_json`, `created_at`).
  - **`actuals`**: Planned table for Phase 7 realized market outcomes (`id` PK, `prediction_id` FK UNIQUE, `symbol` FK, `target_date`, `actual_direction`, `actual_label`, `actual_return`, `actual_close`, `recorded_at`).
- **Native SQLite Immutability Triggers:**
  - `trg_prevent_prediction_update`: Any direct SQL `UPDATE` statement targeting the `predictions` table causes the SQLite engine to abort with an exception.
  - `trg_prevent_prediction_delete`: Any direct SQL `DELETE` statement targeting the `predictions` table causes the SQLite engine to abort with an exception.
  - Immutability is enforced at the database engine level, making it impossible for accidental application-level logic or external tools to mutate or purge historical records.
- **Connection Management & Concurrency:**
  - `create_connection()` configures WAL mode (`PRAGMA journal_mode=WAL`), foreign key enforcement (`PRAGMA foreign_keys=ON`), busy timeout (`PRAGMA busy_timeout=5000`), and `sqlite3.Row` factory.
  - `db_session()` provides transactional context management with automatic commit/rollback.
- **Repository Interface (`PredictionRepository`):**
  - Strongly typed data access methods: `save_prediction()`, `get_prediction()`, `list_predictions()`, `count_predictions()`, `upsert_stock()`, `get_stocks()`, and `register_model_version()`.
  - Zero third-party ORM dependencies (Python stdlib `sqlite3` only), adhering to Ponytail minimalism principles.

### 4.20. Outcome Verification & Evaluation Architecture (`app/history/`)
- **Architectural Overview (Phase 7 / Day 25):**
  ```text
  Persisted Predictions (predictions table)
              │
              ▼
  OutcomeVerifier.verify_prediction(prediction_id, market_bars)
              ├── 1. Temporal Alignment & Session Identification:
              │       Locate reference session t = as_of_date
              │       Identify realized target session t+1
              ├── 2. Calendar Gap & Boundary Resolution:
              │       Natural skip across weekends and NSE holidays
              │       Detect if session t+1 is pending (has not closed yet) -> status PENDING
              ├── 3. Canonical Direction & Return Formulation:
              │       Return = Close(t+1) / Close(t) - 1.0
              │       Direction = UP if Return > 0 else DOWN (zero return = DOWN policy)
              ├── 4. Relational Persistence & Provenance Tracking:
              │       Save to actuals table idempotently via PredictionRepository.save_actual()
              │       Preserve data provenance (source='yfinance', recorded_at timestamp)
              │       Reject conflicting outcomes; prevent duplicate records
              └── 5. Immutability Enforcement on Actuals:
                      trg_prevent_actual_update: abort direct UPDATE statements
                      trg_prevent_actual_delete: abort direct DELETE statements
              │
              ▼
  PredictionEvaluator.evaluate(symbol=None, model_name=None)
              ├── 1. Denominator Isolation:
              │       Total Predictions = All saved records
              │       Eligible Predictions = SUCCESS status with valid predicted_direction
              │       Pending Predictions = Target session t+1 not yet completed
              │       Verified Predictions = Eligible predictions with realized actual outcomes (N_verified)
              │       Directional Accuracy = N_correct / N_verified (Pending EXCLUDED from denominator)
              ├── 2. Symmetrical Class Evaluation:
              │       UP & DOWN Precision, Recall, F1 scores
              │       Confusion Matrix: TP, FP, TN, FN
              └── 3. Safe Reporting & Anti-Fabrication:
                      Zero-division safety (None on N_verified == 0)
                      Zero fabricated price magnitude / target returns
                      Uncalibrated raw model probabilities explicitly disclosed
  ```
- **Verification Rule Matrix:**
  | Scenario | Condition | Verification Status | Action |
  |---|---|---|---|
  | Completed Session | $t+1$ bar exists and closed | `VERIFIED` | Compute return & direction; save to `actuals`. |
  | Repeated Run | Actual already recorded identically | `ALREADY_VERIFIED` | Idempotent return of existing record without re-writing. |
  | Conflicting Actual | Incoming data contradicts recorded actual | `CONFLICT` / `ValueError` | Loud rejection; original actual preserved unmutated. |
  | Future / Unclosed | Session $t$ is latest bar; $t+1$ not closed | `PENDING` | Log pending status; zero write to `actuals`; zero leakage. |
  | Missing / Incomplete | Provider data missing or non-positive price | `DATA_UNAVAILABLE` | Graceful diagnostic record; skipped safely. |
  | Ineligible Forecast | Prediction status != SUCCESS | `INELIGIBLE` | Excluded from verification and accuracy evaluation. |
- **Immutability of Realized Outcomes:**
  - Just as predictions are protected from retroactive revision, realized outcomes in the `actuals` table are write-once and permanently immutable.
  - Native SQLite triggers (`trg_prevent_actual_update`, `trg_prevent_actual_delete`) enforce this constraint directly at the database engine level.

### 4.21. Benchmark & Sector Context Engine (`app/market/benchmark.py`)
- **Architectural Overview (Phase 8 / Day 26):**
  ```text
  Raw Equities OHLCV + Benchmark OHLCV (^NSEI, ^NSEBANK, ^CNXIT)
              │
              ▼
  1. Symbol Resolution (YFinanceProvider._resolve_symbols)
        ├── Direct Index Tickers: ^NSEI, ^NSEBANK, ^CNXIT, ^BSESN, ^CRSLDX (no .NS appended)
        └── Friendly Alias Mapping: NIFTY/NIFTY50 -> ^NSEI, BANKNIFTY -> ^NSEBANK, NIFTYIT -> ^CNXIT
              │
              ▼
  2. Point-in-Time Temporal Alignment (align_benchmark_series)
        ├── Match session date strictly on calendar trading day: bar.timestamp.date()
        ├── Missing benchmark sessions paired safely with None (no bar dropping or forward shift)
        └── Zero look-ahead bias: future benchmark sessions are completely inaccessible at t
              │
              ▼
  3. Relative Performance & Risk Metrics (compute_relative_performance)
        ├── Daily Relative Return (Alpha): R_stock,t - R_bench,t
        ├── Relative Strength Ratio: Close_stock,t / Close_bench,t
        ├── Relative Strength Momentum: (RS_t / RS_{t-w}) - 1 for w ∈ {5, 20} sessions
        ├── Rolling Beta (20d): Cov(R_s, R_b) / Var(R_b) with sample ddof=1
        │       └── Zero-variance guard: Var(R_b) < 1e-12 => None
        └── Rolling Correlation (20d): Cov(R_s, R_b) / (Std(R_s) * Std(R_b))
                └── Clamped strictly to [-1.0, 1.0]
              │
              ▼
  4. Cross-Sectional Market Breadth Engine (compute_market_breadth & compute_multi_symbol_breadth_series)
        ├── Advances: Count(R_t > 0)
        ├── Declines: Count(R_t < 0)
        ├── Unchanged: Count(R_t == 0)
        ├── Advance/Decline Ratio (ADR): Advances / Declines (None if Declines == 0)
        ├── Breadth Thrust: Advances / Total Active Stocks
        ├── Net Advances: Advances - Declines
        └── 20-Day SMA Breadth Participation: Fraction of universe with Close_t > SMA20_t
  ```
- **Temporal Invariants & Data Integrity:**
  - **Zero Look-Ahead Invariant:** Relative performance features for trading session $t$ strictly consume prices and returns timestamped $\le t$. Benchmark bars from $t+1$ or later are never referenced.
  - **Calendar Discrepancy Tolerance:** When market holidays or trading halts cause one series to have an observation while the other is missing, unpaired observations evaluate gracefully to `None` without distorting the surrounding time series.
  - **Zero-Division & Low-Variance Guards:** When volatility collapses or series exhibit zero variance, rolling beta and correlation evaluate to `None`, avoiding floating-point exceptions or spurious infinities.

### 4.22. Financial News Ingestion & Cleaning Engine (`app/news/`)
- **Architectural Overview (Phase 9 / Day 27):**
  ```text
  Raw Financial News RSS Feeds (Indian Financial Media / Google News RSS)
              │
              ▼
  1. News Provider Adapter (RSSNewsProvider)
        ├── URL Query Formatting: company name + ticker + 'stock NSE'
        ├── Standard Library XML Parsing: xml.etree.ElementTree
        ├── Header & Attribution Parsing: extracts publisher and strips title suffixes
        ├── Timestamp Normalization: RFC 2822 / ISO parsed to Asia/Kolkata (IST)
        └── Ingestion Stamping: assigns distinct ingested_at timestamp (now)
              │
              ▼
  2. Canonical Schema Normalization (NewsArticle)
        ├── headline: Non-empty string
        ├── source: Publisher name (e.g. 'Economic Times', 'Moneycontrol')
        ├── published_at: Timezone-aware publication datetime
        ├── ingested_at: Distinct timezone-aware system acquisition datetime
        ├── symbols: Tuple of canonical uppercase symbols (e.g. ('BHARTIARTL',))
        ├── url: Validated HTTP/HTTPS URL
        ├── summary: Cleaned description with HTML tags stripped
        ├── provider: Provider name ('rss_news_provider')
        └── article_id: Deterministic SHA-256 hash (16-hex characters)
              │
              ▼
  3. Syndicated News Deduplication (deduplicate_news in cleaner.py)
        ├── 1. Exact Article ID match check
        ├── 2. Exact URL match check
        └── 3. Syndicated Headline Match: identical normalized text within 48h window
                └── Preserves earliest publication as canonical; discards later syndications
              │
              ▼
  4. Point-in-Time Session Filtering (filter_news_point_in_time)
        ├── Enforces published_at <= as_of_time AND ingested_at <= as_of_time
        ├── Optional lookback window (e.g. 24h, 48h)
        └── Zero look-ahead bias: future post-cutoff news strictly eliminated
  ```
- **Temporal Invariants & Anti-Leakage Guarantees:**
  - **Separation of Publication and Ingestion:** Publication timestamp (`published_at`) reflects when the story broke publicly. Ingestion timestamp (`ingested_at`) records when the system acquired the record. Both must precede the market decision cutoff $T_{cutoff}$ for the news item to enter any historical backtest or feature join.
  - **Non-Causal Representation:** The news ingestion layer strictly provides clean textual observations with provenance; it does not infer price directions, target price movements, or claim mechanical market causality.

### 4.23. FinBERT Financial Sentiment Scoring Engine (`app/news/sentiment.py`)
- **Architectural Overview (Phase 9 / Day 28):**
  ```text
  Cleaned & Point-in-Time Verified NewsArticle Records
              │
              ▼
  1. Text Preparation & Boundary Truncation (prepare_article_text)
        ├── Minimum Input Strategy: Non-empty headline is mandatory
        ├── Optional Summary Inclusion: "Headline. Summary" if include_summary=True
        ├── Length Control: Configurable character truncation (default max_length_chars=512)
        └── Boundary Sanitization: Strips excessive whitespace, rejects blank/missing text
              │
              ▼
  2. Sentiment Scoring Adapter Layer (BaseSentimentBackend)
        ├── FinBERTBackend (Hugging Face Transformers + PyTorch):
        │     ├── Lazy Initialization: Zero weights downloaded on package import
        │     ├── Model Selection: ProsusAI/finbert (BertForSequenceClassification)
        │     ├── Dynamic Label Mapping: Resolves id2label dynamically from model.config
        │     │     └── ProsusAI/finbert mapping: {0: 'positive', 1: 'negative', 2: 'neutral'}
        │     ├── Deterministic Inference Mode: model.eval(), torch.inference_mode()
        │     └── Softmax Normalization: Probabilities bounded in [0, 1] and sum to ~1.0
        └── MockSentimentBackend (Deterministic Test Double):
              ├── 100% Offline execution: Zero external network or model weight downloads
              └── Deterministic output mapping for reproducible test suites
              │
              ▼
  3. High-Level Scoring Service (FinBERTSentimentScorer)
        ├── Single Article Scoring: score_article(article)
        ├── Batch Article Scoring: score_articles(articles) preserving input order
        └── Error Quarantining & Anti-Fabrication Safeguards:
              ├── Captures missing dependencies or inference exceptions gracefully
              ├── Explicit ERROR status: status='ERROR', error_message='...'
              └── Zero Fake Neutrals: sentiment_label=None, probabilities=None
              │
              ▼
  4. Canonical Sentiment Output (ArticleSentimentResult)
        ├── article_id: Original 16-hex deterministic SHA-256 hash
        ├── headline: Cleaned headline evaluated
        ├── sentiment_label: 'positive' | 'neutral' | 'negative' | None
        ├── sentiment_score: Winning-class confidence score in [0.0, 1.0] | None
        ├── probabilities: {'positive': P, 'neutral': P, 'negative': P} | None
        ├── model_name: 'ProsusAI/finbert'
        ├── model_version: Model revision or config hash
        ├── scored_at: Timezone-aware execution timestamp (Asia/Kolkata)
        ├── status: 'SUCCESS' | 'ERROR'
        └── error_message: Diagnostic failure message on error | None
  ```
- **Temporal Invariants & Provenance Integrity:**
  - **Temporal Isolation of Scoring:** `scored_at` records the exact execution moment of sentiment evaluation. It remains strictly distinct from the publication timestamp (`published_at`) and the ingestion timestamp (`ingested_at`).
  - **Point-in-Time Compliance:** Sentiment scoring is performed strictly downstream of Day 27 point-in-time filtering (`filter_news_point_in_time`). Articles published or acquired after a market session cutoff $T_{cutoff}$ are never scored or passed to downstream feature models.
- **Strict Boundary Disclosures:**
  - **Sentiment is Classification, Not Forecast:** Article sentiment reflects the linguistic tone of the article text; it is strictly NOT a price forecast, price target, or directional trading recommendation.
  - **Confidence is Not Market Prediction Probability:** Classifier confidence represents Softmax probability across text categories, NOT calibrated Bayesian confidence of market direction.

### 4.24. Macroeconomic, Regulatory & External Events Ingestion Engine (`app/events/`)
- **Architectural Overview (Phase 10 / Day 29):**
  ```text
  Official Regulatory Feeds & Global Time-Series (RBI, SEBI, Yahoo Finance)
              │
              ▼
  1. Provider Adapters (BaseEventProvider):
        ├── RBIEventProvider (https://rbi.org.in/pressreleases_rss.xml):
        │     ├── Ingests official press releases and Monetary Policy Committee (MPC) decisions
        │     ├── Standard library XML parsing (xml.etree.ElementTree)
        │     ├── Classifies MONETARY_POLICY vs REGULATORY and extracts repo rate values
        │     └── Dependency injection support for 100% offline deterministic test doubles
        ├── SEBIEventProvider (https://www.sebi.gov.in/sebirss.xml):
        │     ├── Ingests master circulars, regulatory guidelines, and enforcement orders
        │     ├── Parses SEBI custom date formats localized to Asia/Kolkata (IST)
        │     └── Assigns equity market sector targeting
        └── ExternalMarketProvider:
              ├── Ingests continuous macro variables: Brent Crude (BZ=F), USD/INR (INR=X), S&P 500 (^GSPC)
              ├── Normalizes into ExternalMarketObservation time-series records
              └── Bridges continuous variables into canonical MacroEvent via .to_event()
              │
              ▼
  2. Canonical Event Schemas (MacroEvent & ExternalMarketObservation):
        ├── event_id: Deterministic 16-character SHA-256 hash
        ├── category: MONETARY_POLICY | REGULATORY | GOVERNMENT | MACRO_INDICATOR | EXTERNAL_MARKET
        ├── event_type: E.g., 'monetary_policy_statement', 'circular', 'enforcement_order'
        ├── source_org: Authoritative publishing organization
        ├── Temporal Anchors: published_at, announced_at, effective_at, ingested_at (all timezone-aware)
        ├── structured_value: Optional StructuredEventValue (metric_name, value, unit, prior_value, change)
        ├── affected_sectors: E.g. ('BANKING', 'FINANCIAL_SERVICES') or ('EQUITY_MARKET',)
        └── url & summary: Validated source link and factual description
              │
              ▼
  3. Syndicated Event Deduplication (deduplicate_events in cleaner.py):
        ├── Rule 1: Exact Event ID match
        ├── Rule 2: Exact URL match
        └── Rule 3: Source organization + normalized title match within configurable window (default 72h)
              │
              ▼
  4. Strict Point-in-Time Session Filtering (filter_events_point_in_time):
        ├── Invariants:
        │     - Primary availability timestamp (published_at or announced_at) <= as_of_time
        │     - System acquisition timestamp (ingested_at) <= as_of_time
        │     - Future-published and future-ingested events strictly excluded (zero look-ahead leakage)
        └── Effective Date Preservation: Events announced before cutoff but effective in the future
              are safely preserved with unaltered effective_at timestamps
  ```
- **Temporal Invariants & Provenance Integrity:**
  - **Multi-Timestamp Isolation:** Discrete event records maintain complete separation between when an event was published (`published_at`), when it was verbally announced (`announced_at`), when it becomes legally effective (`effective_at`), and when the local system acquired the record (`ingested_at`).
  - **Preservation of Effective Dates:** A policy announced on a Friday afternoon that takes effect the following Monday morning is eligible for Friday evening decision cutoffs, but its `effective_at` timestamp preserves the true future effective date.
  - **Separation of Time-Series from Discrete Announcements:** Continuous external market measurements (Brent crude, USD/INR, S&P 500) are modeled distinctly as `ExternalMarketObservation` time-series records and are not conflated with discrete regulatory notices or central bank policy decisions.
- **Strict Non-Causal Disclosure:**
  - Macroeconomic, central bank, and regulatory events provide contextual market observations; they do NOT have fixed directional or causal effects on individual stock price movements. No automated trading rules or causal price movements are inferred from macro events.

### 4.25. Trading Session Alignment & Empirical Event Impact Analysis (`app/events/aligner.py`, `app/events/calendar.py`, `app/events/impact.py`)
- **Architectural Overview (Phase 10 / Day 30):**
  ```text
  MacroEvent / ExternalMarketObservation (Normalized from Official Feeds)
              │
              ▼
  1. Indian Equity Trading Calendar (BaseTradingCalendar):
        ├── MarketDataTradingCalendar: Derives official sessions directly from realized MarketOHLCV bars
        │     └── Eliminates guesswork regarding unscheduled holidays, mourning days, or weather halts
        └── ExchangeTradingCalendar: Configurable exchange calendar supporting weekends, holidays, and Muhurat sessions
              │
              ▼
  2. Trading Session Alignment Engine (EventSessionAligner in aligner.py):
        ├── Pre-Market (< 09:15 IST on trading day):
        │     - session_date = T, session_phase = PRE_MARKET
        │     - Eligible for market open auction (t) and closing prediction (t)
        ├── In-Session (09:15 to 15:30 IST on trading day):
        │     - session_date = T, session_phase = IN_SESSION
        │     - Blocked for session open (t); eligible for session close (t)
        ├── Post-Market (> 15:30 IST on trading day):
        │     - Must NEVER leak into session T's closing prediction
        │     - session_date = T+1 (next trading day), session_phase = POST_MARKET
        │     - Eligible for session T+1 open and close
        ├── Non-Trading Days (Weekends & Holidays):
        │     - Mapped to next active trading day T_next as PRE_MARKET
        └── Date-Only Precision Guard (SEBI Circulars lacking time-of-day):
              - Conservatively aligned to T+1 to eliminate unverified same-session closing look-ahead
              │
              ▼
  3. Empirical Market Impact Analyzer (EventImpactAnalyzer in impact.py):
        ├── Aligned Reaction Session T: Measures session open, session close, and same-day return (Close_T / Close_{T-1} - 1)
        ├── Multi-Session Forward Returns:
        │     - 1-session forward return: Close_{T+1} / Close_T - 1
        │     - 3-session forward return: Close_{T+3} / Close_T - 1
        │     - 5-session forward return: Close_{T+5} / Close_T - 1
        │     - Guard: If T+k > latest available bar, returns None with status INCOMPLETE_OUTCOME_WINDOW
        ├── Realized Volatility Windows (5 sessions, ddof=1 via calculate_standard_deviation):
        │     - Pre-event volatility: rolling stdev of daily returns across [T-5 ... T-1]
        │     - Post-event volatility: rolling stdev of daily returns across [T+1 ... T+5]
        │     - Guard: Insufficient prior/post sessions return None with explicit diagnostic reason
        ├── Benchmark Relative Performance:
        │     - Excess return / Alpha: R_{stock, 1d} - R_{bench, 1d} (e.g. against NIFTY 50 ^NSEI)
        └── Multi-Event Aggregate Summary (AggregateImpactSummary):
              - Deduplicates event IDs to prevent multi-counting identical or syndicated notices
              - Computes sample size, valid outcome counts, mean/median/stdev forward returns
              - Mandates NON_CAUSAL_DISCLAIMER on all summaries
  ```
- **Temporal Invariants & Look-Ahead Safeguards:**
  - **Zero Look-Ahead on Post-Close Announcements:** An event published at 17:30 IST on Monday cannot be consumed by a model predicting Monday's close. The aligner strictly routes it to Tuesday's session as pre-session information.
  - **Zero Fabrication of Incomplete Sessions:** Outcomes for sessions that have not completed return `None` with `INCOMPLETE_OUTCOME_WINDOW`. No synthetic forward prices are ever assumed.
  - **Preservation of Original Provenance:** Alignment derives session associations without mutating or overwriting original event timestamps (`published_at`, `announced_at`, `effective_at`, `ingested_at`).
- **Non-Causal Representation:**
  - Event impact measurements describe historical co-movements and realized dispersion; they do NOT assert that an event caused a price movement or that an event category implies a bullish/bearish bias.

---

### 4.26 Contextual LLM Integration Layer (`app/llm/` - Day 31)

Phase 11 implements the local LLM integration foundation, connecting the local Ollama runtime and Gemma 3 12B (`gemma3:12b`) for qualitative contextual analysis without corrupting quantitative machine learning authority.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Verified Point-in-Time Inputs                        │
│   ├── NewsArticle records (app/news/ - filtered as of T_pred)          │
│   └── MacroEvent / Regulatory records (app/events/ - filtered T_pred)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                        ┌───────────▼───────────┐
                        │ Delimiter Sanitizer   │ (Neutralizes XML breakout tags)
                        └───────────┬───────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        app/llm/prompts.py                              │
│                                                                        │
│  Role A: Context Extraction Prompt      Role B: Qualitative Reasoning  │
│  ├── Untrusted <source_context> tags    ├── Target Symbol Isolation    │
│  ├── Anti-injection system rules       ├── Direction: UP/DOWN/NEUTRAL/ │
│  └── JSON schema enforcement            │              INSUFFICIENT    │
│                                         ├── Positive/Negative factors  │
│                                         ├── Downside Risks             │
│                                         └── Non-predictive disclaimer  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         app/llm/client.py                              │
│                                                                        │
│  BaseLLMClient (Abstract Interface)                                    │
│  ├── OllamaLLMClient: Native urllib.request -> /api/generate (POST)    │
│  │     - Target Model: gemma3:12b                                      │
│  │     - Temperature: 0.1 (low randomness, high factual fidelity)      │
│  │     - JSON Mode: format="json"                                      │
│  │     - Error Handling: Typed LLMClientError & LLMResponseError       │
│  └── MockLLMClient: 100% Deterministic Offline Double for Automated CI  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         app/llm/service.py                             │
│                                                                        │
│  LLMService Orchestrator                                               │
│  ├── extract_context():                                                │
│  │     - Returns LLMContextExtraction (entities, sectors, factors)     │
│  │     - Empty input fast-path -> clean empty record (zero LLM call)   │
│  ├── generate_qualitative_reasoning():                                 │
│  │     - Returns LLMReasoningResult (direction, factors, risks)        │
│  │     - Empty input fast-path -> INSUFFICIENT_EVIDENCE (LOW conf)     │
│  │     - Error propagation -> Typed exceptions (zero false neutrals)   │
│  └── Markdown fence stripping (```json ... ```) & JSON validation      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 Strict Separation & Governance Boundary                │
│                                                                        │
│  [ISOLATED] Qualitative LLM Output:                                    │
│    - Does NOT alter quantitative XGBoost/LightGBM probabilities         │
│    - Does NOT modify canonical 37-feature technical matrix             │
│    - Does NOT invent price targets, future returns, or probabilities   │
│    - Does NOT claim causal stock price determination                   │
└────────────────────────────────────────────────────────────────────────┘
```

- **Architectural Tenets:**
  1. **Standard Library Over Framework Bloat:** Uses native `urllib.request` rather than heavy third-party agent frameworks (LangChain, LlamaIndex), preserving the lean, high-performance architecture mandated by Ponytail / Senior Dev rules.
  2. **Security & Anti-Prompt-Injection:** Qualitative context from news feeds is explicitly encapsulated inside XML-like `<source_context>` tags with delimiter neutralization. System prompts strictly instruct the LLM to treat source text as untrusted data rather than system directives.
  3. **Zero Fabrication & Error Integrity:** In the event of network disruption, daemon unavailability, or malformed JSON responses, the service raises typed errors (`LLMClientError`, `LLMParseError`, `LLMValidationError`). Under no circumstances is a synthetic "NEUTRAL" or fabricated reasoning summary substituted.
  4. **Strict Temporal Integrity:** Callers must pass news and events filtered by existing point-in-time engines (`filter_news_point_in_time`, `filter_events_point_in_time`). Qualitative reasoning can never access future-published information.
