# Indian Stock Market Prediction System

> **Status:** Ongoing Project — Day 15: Define the ML Prediction Target<br/>
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
2. **Data Orchestration:** Historical OHLCV, technical indicators, candlestick features, trend structure, current live movement, market breadth, and sector/NIFTY context are retrieved.
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
- **`app/market/`**: Market data acquisition, cleaning, technical feature engineering (returns, volatility, moving averages, RSI, MACD, Bollinger Bands, ATR, ROC, candlestick features), trend engine (swing points, market structure, trend classification), market breadth, pipeline orchestration, and visualization.
- **`app/news/`**: Financial news ingestion, deduplication, and entity linking.
- **`app/nlp/`**: FinBERT sentiment scoring and textual analysis.
- **`app/prediction/`**: Target formulation (`target.py`), numerical ML predictor, LLM predictor, and ensemble synthesis.
- **`app/training/`**: Walk-forward validation, dataset splits without temporal leakage, and controlled retraining.
- **`app/history/`**: Prediction audit logs, performance evaluation, and accuracy tracking.

---

## 4. Current Status: Day 15 (Define the ML Prediction Target)

Day 15 defines a mathematically precise, leakage-safe target for the first stock-market ML model. It formulates next-session directional prediction using close-to-close returns, implements an initial binary baseline where zero returns are deterministically grouped into `DOWN`, indexes natural trading-session spacing without calendar day gaps, and enforces that the final session has an explicitly missing target.

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
    - Fast EMA period: 12 default ($EMA_{12}$); Slow EMA period: 26 default ($EMA_{26}$); Signal EMA period: 9 default ($EMA_9$).
    - MACD Line, Signal Line, and MACD Histogram with 3-tuple sequence unpacking and dedicated `MACDSeries` container.
  - Bollinger Bands (`calculate_bollinger_bands`):
    - Default window: 20 sessions; multiplier: 2.0; population standard deviation (`ddof=0`).
    - Middle Band, Upper Band, Lower Band, Band Width, and %B with 5-tuple sequence unpacking and `BollingerBandsSeries` container.
  - Average True Range (`calculate_atr` & `calculate_true_range`):
    - True Range: $\max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|)$. First session policy uses $High_0 - Low_0$.
    - Wilder's smoothing recurrence: initial ATR seeded with arithmetic mean of first 14 TR values ($t=13$), followed by $ATR_t = ((period - 1) \times ATR_{t-1} + TR_t) / period$.
  - Rate of Change (`calculate_roc`):
    - Formula: $ROC_t = ((Close_t / Close_{t-n}) - 1) \times 100$. Default 10 sessions.
- Candlestick Feature Engine (`app/market/candlestick.py`):
  - Signed Body: $Close - Open$.
  - Absolute Body: $|Close - Open|$.
  - Candle Range: $High - Low$.
  - Upper Wick: $High - \max(Open, Close)$.
  - Lower Wick: $\min(Open, Close) - Low$.
  - Body-to-Range Ratio: $|Close - Open| / (High - Low)$, when $Range > 0$ (else `None`).
  - Upper-Wick-to-Range Ratio: $UpperWick / (High - Low)$, when $Range > 0$ (else `None`).
  - Lower-Wick-to-Range Ratio: $LowerWick / (High - Low)$, when $Range > 0$ (else `None`).
  - Close Location within Range: $(Close - Low) / (High - Low)$, when $Range > 0$ (else `None`).
  - Body Return Percentage: $((Close / Open) - 1) \times 100$, when $Open > 0$ (else `None`).
  - Candle Direction: `bullish` if $Close > Open$, `bearish` if $Close < Open$, and `neutral` if $Close == Open$.
  - Geometric Partition Invariant: $Body_{abs} + UpperWick + LowerWick = Range$.
  - Ratio Partition Invariant: $Ratio_{body} + Ratio_{upper} + Ratio_{lower} = 1.0$ (when $Range > 0$).
  - Safe zero-range handling: zero body and range values are preserved; ratios evaluate strictly to `None`; direction is `neutral`.
  - Physical OHLC geometry validation: verifies $High \ge Low$, $High \ge \max(Open, Close)$, and $Low \le \min(Open, Close)$; invalid geometry safely masks features with `None`.
  - Dedicated immutable typed container `CandlestickFeatures` with `.to_dict()` serialization and convenience properties.
  - Multi-symbol isolation and chronological sorting via `compute_candlestick_features`.
  - Non-predictive disclaimer: candlestick features quantify single-bar geometry without asserting predictive price direction.
- Trend Engine & Market Structure Analysis (`app/market/trend.py`):
  - Deterministic swing detection (`identify_swings`) using configurable flank window $k$ (default 2) with asymmetric left/right flank comparison preventing duplicate consecutive pivots on flat tops/bottoms.
  - Explicit swing confirmation timing: a pivot occurring at bar index $t$ becomes confirmed strictly at bar index $t + k$.
  - Zero look-ahead bias: in any point-in-time evaluation at index $T$, candidate pivots pending confirmation ($t > T - k$) are strictly excluded.
  - Sequential market structure labeling (`label_market_structure`):
    - Highs: Higher High (`HH`), Lower High (`LH`), Equal High (`EH`).
    - Lows: Higher Low (`HL`), Lower Low (`LL`), Equal Low (`EL`).
  - Strict rule-based trend classification matrix (`classify_market_structure`):
    - `UPTREND`: Latest confirmed high is `HH` and latest confirmed low is `HL`.
    - `DOWNTREND`: Latest confirmed high is `LH` and latest confirmed low is `LL`.
    - `SIDEWAYS`: Confirmed swings $\ge min\_swings$, but mixed or consolidating structure (e.g. `HH` + `LL`, `LH` + `HL`).
    - `None` (`INSUFFICIENT_DATA`): Evaluates safely to `None` with status `INSUFFICIENT_DATA` when fewer than `min_swings` (default 2) confirmed pivots exist. Insufficient history is never mislabeled as `SIDEWAYS`.
  - Point-in-time rolling trend series alignment (`compute_rolling_trends`): generates 1:1 aligned rolling trend classifications across all bars with zero future leakage.
  - Typed immutable results container (`TrendAnalysisResult`) and swing representation (`SwingPoint`) with complete `.to_dict()` serialization and boolean flags (`.is_uptrend`, `.is_downtrend`, `.is_sideways`, `.is_confirmed`).
  - Non-predictive baseline disclaimer: trend classifications describe historical price action structure; they do not predict future returns, directional continuation, or provide trading signals.
- ML Prediction Target Layer (`app/prediction/target.py`):
  - Forward close-to-close return formula: $target\_return[t] = (Close_{t+1} / Close_t) - 1.0$.
  - Initial binary directional classification: `UP` (binary 1) if $target\_return[t] > 0.0$ else `DOWN` (binary 0).
  - Deterministic zero-return baseline policy: sessions where $Close_{t+1} == Close_t$ are grouped into `DOWN` without sample dropping.
  - Non-calendar trading session alignment: consecutive records index the next available trading day (handles weekends and exchange holidays naturally).
  - Missing final target invariant: the latest session $t = N - 1$ has no realized future and strictly receives `None` (`has_target=False`), preventing temporal leakage.
  - Typed immutable container `TargetObservation` with complete `.to_dict()` serialization.
- Market Data Pipeline Orchestrator (`app/market/pipeline.py`):
  - Unified pipeline connecting provider retrieval, data cleaning, return/volatility feature computation, technical indicators, candlestick features, and trend analysis (`run_market_data_pipeline` and `process_market_data`).
  - Immutable pipeline container (`MarketDataPipelineResult`) preserving raw records, cleaned records, cleaning summary, return features, technical indicators, candlestick features, and trend analysis (`result.trend`, `trend_classification`, and `.to_dict()`).
- Historical Market Visualizer (`app/market/visualizer.py`):
  - Headless Matplotlib rendering (`Agg` backend) generating publication-quality PNG charts.
- 185 automated unit tests passing across foundation, settings, logging, canonical schemas, provider adapters, data cleaning, returns/volatility calculations, pipeline orchestration, moving averages, RSI, MACD, Bollinger Bands, ATR, ROC, candlestick features, trend engine, prediction target layer, and visualizer.

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
