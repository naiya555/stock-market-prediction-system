# Indian Stock Market Prediction System

> **Status:** Ongoing Project — Day 9: Expand Historical Data & RSI Technical Indicator  
> **Development Philosophy:** `PREDICT → EXPLAIN → VERIFY → EVALUATE → IMPROVE`

---

## 1. Project Objective

The Indian Stock Market Prediction System is an end-to-end, multi-agent AI and machine-learning platform designed to predict, explain, and evaluate stock movements in the Indian equity markets (NSE/BSE).

The core philosophy of this project is strict integrity and continuous verification:
```
PREDICT ➔ EXPLAIN ➔ VERIFY ➔ EVALUATE ➔ IMPROVE
```
- **Predict:** Generate independent quantitative and contextual predictions.
- **Explain:** Ground predictions with concrete factor attributions and news/event drivers (no unverified post-hoc narratives).
- **Verify:** Record predictions immutably before the market outcome occurs, then capture actual market performance.
- **Evaluate:** Systematically assess directional accuracy, price error (MAE/RMSE), and probability calibration.
- **Improve:** Use verified out-of-sample findings for controlled, versioned model retraining.

---

## 2. Long-Term Architecture & Workflow

When fully developed, the end-user workflow will operate as follows:

1. **User Interaction:** Select an Indian ticker (e.g., `RELIANCE`, `TCS`, `INFY`) and request a prediction.
2. **Data Orchestration:** Historical OHLCV, technical indicators, current live movement, market breadth, and sector/NIFTY context are retrieved.
3. **Information Pipelines:** Real-time financial news and macroeconomic/regulatory events are collected, deduplicated, and timestamp-indexed.
4. **Independent Model Evaluation:**
   - **Numerical ML:** A gradient-boosted time-series model (e.g., XGBoost / LightGBM) computes expected price movement and directional probability.
   - **Financial NLP:** FinBERT processes extracted financial news to compute structured sentiment features.
   - **Contextual LLM:** An LLM performs structured context analysis and produces an independent prediction with rationale and risk factors.
5. **Ensemble & Synthesis Layer:** Combines numerical ML and LLM predictions transparently, retaining independent scores.
6. **Immutable Output:** Outputs direction (`UP` / `DOWN` / `SIDEWAYS`), target range in ₹ and %, confidence score, key factors, and downside risks.
7. **Storage & Verification:** The prediction is logged to a relational database with strict timestamps. Once market outcomes materialize, actual prices are recorded and prediction error is calculated without ever mutating original prediction records.

---

## 3. Major Components

- **`app/api/`**: FastAPI application endpoints and route handlers (planned).
- **`app/core/`**: Centralized configuration (`config.py`), logging foundation (`logging_config.py`), and canonical schema contracts (`schemas.py`).
- **`app/database/`**: Relational database persistence (SQLite initially, PostgreSQL migration path).
- **`app/market/`**: Market data acquisition, cleaning, technical feature engineering (returns, volatility, moving averages, RSI), market breadth, pipeline orchestration, and visualization.
- **`app/news/`**: Financial news ingestion, deduplication, and entity linking.
- **`app/nlp/`**: FinBERT sentiment scoring and textual analysis.
- **`app/prediction/`**: Numerical ML predictor, LLM predictor, and ensemble synthesis.
- **`app/training/`**: Walk-forward validation, dataset splits without temporal leakage, and controlled retraining.
- **`app/history/`**: Prediction audit logs, performance evaluation, and accuracy tracking.

---

## 4. Current Status: Day 9 (Expand Historical Data & RSI Technical Indicator)

Day 9 resolves the Day 8 six-session historical data limitation by enabling flexible 6–12 month historical window lookbacks (`lookback_days`), confirms full warmup of SMA-5, EMA-5, SMA-10, and EMA-10, and delivers Wilder's Relative Strength Index (RSI) calculation.

### Current Features
- Defined 16-phase long-term project roadmap and architecture documentation.
- Centralized, environment-driven configuration layer (`app/core/config.py`) with safe non-secret defaults.
- Structured application logging system (`app/core/logging_config.py`) with configurable log levels.
- Canonical market-data contracts (`MarketOHLCV`, `MarketQuote`, `DataSourceMetadata` in `app/core/schemas.py`) enforcing point-in-time timestamps and structural bounds.
- Market-data module package (`app/market/` and `app/market/providers/`).
- Historical provider abstraction (`BaseMarketDataProvider`) and concrete `YFinanceProvider` for Indian cash equities.
- Data cleaning pipeline (`clean_market_data` in `app/market/cleaner.py`):
  - Missing-value detection with quarantine/rejection policy (zero blind interpolation).
  - Deterministic duplicate resolution (identical duplicates collapsed; conflicting duplicates quarantined).
  - Physical OHLCV candle validation (positive prices, non-negative volume, strict wick geometry).
  - Timezone normalization to `Asia/Kolkata` with calendar session date preservation.
  - Chronological ascending sorting by `(symbol, timestamp)`.
  - Comprehensive audit summary metrics (`CleaningSummary`).
- Returns and Volatility feature engine (`app/market/returns.py`):
  - Daily simple percentage return calculation ($R_t = P_t / P_{t-1} - 1$) with explicit `None` for unavailable initial observation.
  - Multi-session rolling return calculations (3-session and 5-session default windows) with strict point-in-time boundaries (zero lookahead leakage).
  - Sample standard deviation ($ddof=1$) calculation using built-in standard library mathematics.
  - Rolling realized volatility metrics: raw daily return standard deviation and annualized volatility scaled by $\sqrt{252}$ (252 trading sessions per year in Indian markets).
  - Machine-readable feature container (`ReturnFeatures`) with `.to_dict()` serialization and type-safe convenience properties.
  - Safe zero/negative previous price handling (division-by-zero protection returning `None` rather than generating `inf` or crashing).
  - Multi-symbol grouping with isolated per-ticker chronological sorting.
- Technical Indicators & Momentum Engine (`app/market/indicators.py`):
  - Simple Moving Average (`calculate_sma`) with configurable session windows (default 5 and 10 sessions).
  - Exponential Moving Average (`calculate_ema`) with recursive smoothing factor $\alpha = \frac{2}{W + 1}$ and `allow_negative` parameter for oscillator series.
  - Relative Strength Index (`calculate_rsi`) using Wilder's smoothing method ($\alpha = 1 / W$) with configurable periods (standard 14-session default).
  - Moving Average Convergence Divergence (`calculate_macd`):
    - Fast EMA period: 12 default ($EMA_{12}$).
    - Slow EMA period: 26 default ($EMA_{26}$).
    - Signal EMA period: 9 default ($EMA_9$).
    - MACD Line: $EMA_{fast} - EMA_{slow}$.
    - Signal Line: 9-period EMA of the MACD line.
    - MACD Histogram: $MACD - Signal$ (verified strictly via floating-point identity).
    - Unpacking protocol: `macd, signal, hist = calculate_macd(prices)`.
    - Dedicated immutable container `MACDSeries` supporting both sequence unpacking and attribute access.
  - Explicit RSI edge-case handling: neutral 50.0 for flat prices, 100.0 for pure gains, 0.0 for pure losses; bounded strictly within $[0.0, 100.0]$.
  - Multi-session indicator orchestrator (`compute_moving_averages` / `compute_technical_indicators`) producing immutable `MovingAverageFeatures` dataclasses with `rsi_14`, `macd_line`, `signal_line`, and `histogram` properties and flat `.to_dict()` export.
  - Strict point-in-time guarantees preventing future-data leakage.
  - Un-warmed window sessions ($t < W - 1$ for MAs, $t < W$ for RSI, $t < slow - 1$ for MACD line, $t < slow + signal - 2$ for Signal line and Histogram) safely return `None`.
  - Raw price basis: strictly unadjusted closing prices (`close`).
- Market Data Pipeline Orchestrator (`app/market/pipeline.py`):
  - Unified pipeline connecting provider retrieval, data cleaning, return/volatility feature computation, and technical indicators (`run_market_data_pipeline` and `process_market_data`).
  - Supports configurable `macd_fast=12`, `macd_slow=26`, `macd_signal=9` parameters with complete feature preservation.
  - Supports flexible historical range lookbacks via `lookback_days` (defaulting to 180 days / ~6 months, or 365 days / ~12 months) when `start_date` is omitted, while retaining deterministic explicit date support.
  - Immutable pipeline container (`MarketDataPipelineResult`) preserving raw records, cleaned records, cleaning summary, return features, and technical indicators.
- Historical Market Visualizer (`app/market/visualizer.py`):
  - Headless Matplotlib rendering (`Agg` backend) generating publication-quality PNG charts.
  - Historical closing price chart (`plot_closing_prices`) with formatted INR pricing and session date labels.
  - Daily percentage returns chart (`plot_daily_returns`) with color-coded positive/negative bars and zero baseline.
  - Batch chart generator (`generate_market_charts`) saving to `data/processed/charts/` (strictly ignored by `.gitignore`).
- 118 automated unit tests passing across foundation, settings, logging, canonical schemas, provider adapters, data cleaning, returns/volatility calculations, pipeline orchestration, moving averages, RSI, MACD, and visualizer.

---

## 5. Environment Setup & Validation

### Prerequisites
- Python 3.11+ (Python 3.14 compatible)
- Git

### Virtual Environment Setup

**Windows (PowerShell):**
```powershell
# Create virtual environment (if not already present)
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install baseline dependencies
pip install -r requirements.txt
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running Day 1 Validation

Run the foundation entry point:
```powershell
python main.py
```
*Expected output:*
```
Stock Market Prediction System
Day 1 environment ready
Python runtime: 3.14.x
Project root: ...
```

Run the foundation test suite:
```powershell
pytest -v
```
*Expected output:*
```
tests/test_foundation.py::test_core_package_import PASSED
tests/test_foundation.py::test_main_execution PASSED
tests/test_foundation.py::test_required_project_directories_exist PASSED
tests/test_foundation.py::test_no_forbidden_day1_mock_data PASSED
```

---

## 6. Project Documentation Index

- [docs/architecture.md](docs/architecture.md) — Comprehensive technical architecture.
- [docs/roadmap.md](docs/roadmap.md) — 16-phase milestone roadmap.
- [docs/decisions.md](docs/decisions.md) — Architectural Decision Records (ADRs).
- [docs/data-sources.md](docs/data-sources.md) — Data source inventory and verification guidelines.
- [docs/daily-progress.md](docs/daily-progress.md) — Day-by-day development log and audit trail.
