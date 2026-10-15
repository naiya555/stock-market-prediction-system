# Indian Stock Market Prediction System

> **Status:** Ongoing Project — Day 28: FinBERT Financial Sentiment Scoring Foundation<br/>
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
   - **Numerical ML:** Gradient-boosted time-series models (XGBoost / LightGBM) compute expected price movement and directional probability.
   - **Financial NLP:** FinBERT processes extracted financial news to compute structured sentiment features.
   - **Contextual LLM:** An LLM performs structured context analysis and produces an independent prediction with rationale and risk factors.
5. **Ensemble & Synthesis Layer:** Combines numerical ML and LLM predictions transparently, retaining independent scores.
6. **Immutable Output:** Outputs direction (`UP` / `DOWN` / `SIDEWAYS`), target range in ₹ and %, confidence score, key factors, and downside risks.
7. **Storage & Verification:** The prediction is logged to a relational database with strict timestamps. Once market outcomes materialize, actual prices are recorded and prediction error is calculated without ever mutating original prediction records.

---

## 3. Major Components

- **`app/api/`**: FastAPI application endpoints and route handlers (planned).
- **`app/core/`**: Centralized configuration (`config.py`), logging foundation (`logging_config.py`), and canonical schema contracts (`schemas.py`).
- **`app/database/`**: Relational database persistence (SQLite schema, WAL mode, foreign keys, immutability triggers, and PredictionRepository).
- **`app/market/`**: Market data acquisition, cleaning, technical feature engineering (returns, volatility, moving averages, RSI, MACD, Bollinger Bands, ATR, ROC, candlestick features), trend engine (swing points, market structure, trend classification), market breadth and benchmark relative performance (`benchmark.py`), pipeline orchestration, and visualization.
- **`app/news/`**: Financial news ingestion (`providers/base.py`, `providers/rss_provider.py`), typed article schemas (`schemas.py`), deduplication, point-in-time filtering (`cleaner.py`), and FinBERT sentiment scoring foundation (`sentiment.py`).
- **`app/nlp/`**: FinBERT sentiment scoring foundation and textual analysis (`app/nlp/__init__.py`).
- **`app/prediction/`**: Target formulation (`target.py`), directional prediction service (`service.py`), and inference contract (`contract.py`).
- **`app/training/`**: Walk-forward validation, dataset splits without temporal leakage, baseline benchmark comparison suite, XGBoost and LightGBM models, model error analysis, feature usefulness audit, and controlled retraining.
- **`app/history/`**: Prediction audit logs, outcome verification engine (`verifier.py`), evaluation service (`evaluator.py`), and accuracy tracking.

---

## 4. Current Status: Day 28 (FinBERT Financial Sentiment Scoring Foundation)

Day 28 completes Phase 9: Financial News Ingestion & FinBERT Sentiment Foundation (`app/news/` and `app/nlp/`). It introduces a domain-specific financial sentiment scoring architecture using `ProsusAI/finbert` (Apache 2.0 open-source license), fine-tuned on Financial PhraseBank.

Crucially, lazy initialization guarantees zero model weights or transformer overhead are loaded during package imports or standard CLI operations. Pluggable scoring backends support live `FinBERTBackend` (Hugging Face Transformers + PyTorch) and deterministic `MockSentimentBackend`, enabling 100% offline, reproducible automated tests with zero weight downloads. Error quarantining guarantees that inference failures record an explicit `status="ERROR"` without silently fabricating false neutral classifications. All Day 27 point-in-time temporal boundaries are rigorously preserved, and text sentiment is explicitly documented as textual tone classification rather than a stock price forecast.

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
- Technical Feature Matrix Assembly (`app/training/feature_matrix.py`):
  - 37 canonical numeric features across 8 domains: OHLCV (5), Returns & Volatility (5), Moving Averages (4), Momentum & Oscillators (4), Volatility Bands (5), Range Volatility & Relative Velocity (2), Candlestick Geometry (11), and Market Structure (1).
  - Explicit numeric encodings: `candle_direction_encoded` (bullish=1, neutral=0, bearish=-1) and `trend_regime_encoded` (UPTREND=1, SIDEWAYS=0, DOWNTREND=-1, INSUFFICIENT_DATA=NaN).
  - Explicit timestamp-keyed join on `(symbol, timestamp)` aligning feature bar $t$ with Day 15 target computed from $t+1$.
  - Strict model-input/target isolation: guards against `target_*`, `next_*`, `future_*`, `outcome_*` appearing in $X$.
  - Natural indicator warmup preservation: missing values from rolling windows are preserved as `NaN` (zero blind imputation/scaling across the dataset).
  - Separate labeled training selector: `dataset.get_labeled_dataset(drop_incomplete_warmup=True)` providing transparent row accounting without mutating the aligned dataset.
  - Final observation ($t = N - 1$) explicitly identified as unlabeled (`has_target=False`).
- Market Data Pipeline Orchestrator (`app/market/pipeline.py`):
  - Unified pipeline connecting provider retrieval, data cleaning, return/volatility feature computation, technical indicators, candlestick features, and trend analysis (`run_market_data_pipeline` and `process_market_data`).
  - Immutable pipeline container (`MarketDataPipelineResult`) preserving raw records, cleaned records, cleaning summary, return features, technical indicators, candlestick features, and trend analysis (`result.trend`, `trend_classification`, and `.to_dict()`).
- Baseline XGBoost Direction Classifier Layer (`app/training/xgboost_classifier.py`):
  - Binary direction classifier predicting next-session movement (`UP`=1, `DOWN`=0) using native `xgb.train` and `xgb.DMatrix` (zero `scikit-learn` dependency).
  - Conservative, explicit baseline hyperparameters: `objective='binary:logistic'`, `eval_metric='logloss'`, `max_depth=3`, `learning_rate=0.05`, `n_estimators=50`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42`, `n_jobs=1`.
  - Chronological holdout partitioning (`split_chronological_holdout`) enforcing an explicit 1-session embargo gap so that training label outcome timestamps (`next_timestamp`) never touch or overlap with holdout session timestamps.
  - Complete labeled row extraction policy: rejects missing values during baseline training, transparently accounting for excluded indicator warmup rows (33 sessions) and the final unlabeled observation.
  - Pure Python / NumPy evaluation metrics engine (`compute_classification_metrics`) calculating Accuracy, Precision, Recall, F1, and Confusion Matrix with positive class convention 1 (`UP`).
  - Native model serialization (.save_model() to JSON) and deterministic prediction reproducibility.
  - Research baseline disclaimer: uncalibrated probabilities, no financial edge claim.
- Baseline Comparison & Evaluation Framework (`app/training/baselines.py`):
  - MajorityClassClassifier: predicts training label majority (with deterministic tie-breaking to class 1).
  - RandomClassifier: deterministic pseudo-random predictions with fixed seed (uniform p=0.5 and stratified p=train_prior policies).
  - Comparative evaluation pipeline (`evaluate_baseline_comparison`): benchmarks XGBoost and LightGBM against non-parametric baselines on identical holdout samples with 1-session embargo.
- LightGBM Direction Classifier Layer (`app/training/lightgbm_classifier.py`):
  - Second reproducible gradient-boosted decision tree binary classifier predicting next-session direction (`UP`=1, `DOWN`=0) using native `lgb.train` and `lgb.Dataset` (zero `scikit-learn` dependency).
  - Symmetrical baseline hyperparameters matching XGBoost: `objective='binary'`, `metric='binary_logloss'`, `max_depth=3`, `num_leaves=7`, `learning_rate=0.05`, `n_estimators=50`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42`, `num_threads=1`, `deterministic=True`.
  - Feature isolation verified via `validate_feature_matrix_isolation(X)` to guarantee zero target or outcome leakage.
  - Native model persistence (`.save_model()` and `.load_model()`) and feature importance extraction.
- Walk-Forward Temporal Cross-Validation Layer (`app/training/walk_forward.py`):
  - Chronological expanding-window fold generator (`generate_walk_forward_splits`) with explicit configurable defaults: `n_splits=5`, `min_train_ratio=0.4` (initial train size $N_{train\_init} \ge min\_train\_samples=20$), validation step size $val\_size \ge min\_val\_samples=5$, and mandatory outcome embargo (`embargo_sessions=1`).
  - Strict leakage safeguards: verifies `train_outcome_cutoff <= val_start_date` and zero index overlap across train, embargo, and validation sets.
  - Consistent input validation: validates $(X, y)$ tuple row counts, requires `target_binary` in DataFrames, and rejects null or non-binary labels.
  - Comparative strategy evaluation across identical folds for Majority Class, Uniform Random, Stratified Random, XGBoost, and LightGBM.
  - Dual aggregation metrics: macro-averaged fold mean ± sample standard deviation ($ddof=1$) and micro-pooled confusion matrix accumulation.
  - Robust edge-case handling: separate `SKIPPED_UNDERSIZED_TRAIN` and `SKIPPED_UNDERSIZED_VAL` handling distinct from `SKIPPED_SINGLE_CLASS`, with zero dummy metric fabrication (renders `N/A` or `SKIP`).
- Model Error Analysis & Feature Usefulness Audit Layer (`app/training/error_analysis.py`):
  - Symmetrical dual-class evaluation: calculates Accuracy, Precision UP/DOWN, Recall UP/DOWN, and F1 UP/DOWN with zero-division safety.
  - Per-fold error breakdown: confusion matrices (`[TN, FP / FN, TP]`), predicted vs actual counts, and directional bias detection (`ALL_UP` / `ALL_DOWN`).
  - Distribution shift analysis: computes training-to-validation UP ratio shift ($Val\_UP\% - Train\_UP\%$) and delta vs Majority Class per fold.
  - Strict training-isolated feature matrix audit: verifies 0 missing values, 0 constant columns across 37 features without lookahead leakage.
  - Collinearity clustering: identifies 59 high-correlation feature pairs ($|r| \ge 0.90$) as simplification candidates.
  - Exploratory tree feature importance: compares XGBoost split weight against LightGBM split count with documented non-causal caveats.
- Prediction Engine Service Layer (`app/prediction/service.py` & `app/prediction/contract.py`):
  - Typed prediction contract (`PredictionRequest`, `PredictionResult`, `PredictionDataQuality`, `PredictionStatus`).
  - End-to-end inference orchestration consuming market-data provider, data cleaning, and canonical 37-feature matrix without code duplication.
  - Strict model lifecycle isolation: consumes pre-existing persisted model artifacts or registered instances; zero hidden on-the-fly retraining during inference.
  - Actionable error reporting when model artifacts are missing (`MODEL_UNAVAILABLE`).
  - Data quality and warm-up validation: verifies minimum 34 sessions required for indicators and identifies any missing feature values.
  - Strict inference feature matrix isolation: validates absence of target/outcome columns and enforces feature order matching `FEATURE_COLUMNS`.
  - Discloses model boundaries: binary direction (UP/DOWN) and class probability without fabricated target prices or confidence scores.
- Structured Prediction Output & Transparency Layer (Day 23 complete):
  - Explicit probability calibration transparency: tree probabilities explicitly marked uncalibrated (`is_probability_calibrated=False`, `probability_calibration="uncalibrated"`).
  - Explicit expected movement boundaries: price/return magnitude explicitly set to `None` with `expected_movement_status="UNSUPPORTED"` for direction classifiers.
  - Full machine-readable serialization via `.to_dict()` for downstream JSON consumers.
  - Human-readable text audit rendering via `.format_summary()`.
  - Symmetrical class probability guarantees ($P(UP) + P(DOWN) == 1.00$).
- Historical Market Visualizer (`app/market/visualizer.py`):
  - Headless Matplotlib rendering (`Agg` backend) generating publication-quality PNG charts.
- Prediction Database & Immutable Persistence Layer (`app/database/` - Day 24 complete):
  - SQLite relational schema with WAL mode, foreign key enforcement, and performance indexes.
  - Relational tables: `stocks`, `model_versions`, `predictions`, and `actuals`.
  - Native SQLite engine immutability triggers (`trg_prevent_prediction_update` and `trg_prevent_prediction_delete`) strictly prohibiting any in-place mutation or deletion of logged predictions.
  - Strongly-typed `PredictionRepository` providing `save_prediction()`, `get_prediction()`, `list_predictions()`, `count_predictions()`, `upsert_stock()`, and `register_model_version()`.
  - Retention of Day 23 transparency semantics: uncalibrated probabilities, unsupported expected movement, and dual indexed + lossless JSON storage.
  - Seamless optional repository persistence integrated directly into `PredictionService.predict(..., persist=True)`.
- Prediction Outcome Verification & Evaluation Foundation (`app/history/` - Day 25 complete):
  - Canonical outcome verification engine (`OutcomeVerifier` in `app/history/verifier.py`) aligning prediction sessions with realized market sessions ($t+1$) across weekends and holidays.
  - Verification statuses: `VERIFIED`, `ALREADY_VERIFIED`, `PENDING`, `INELIGIBLE`, `DATA_UNAVAILABLE`, `CONFLICT`.
  - Target formulation adherence: $R = Close_{t+1}/Close_t - 1.0$; $R > 0 \implies UP$, $R \le 0 \implies DOWN$.
  - Engine-level write-once immutability triggers on realized outcomes (`trg_prevent_actual_update`, `trg_prevent_actual_delete`).
  - Idempotent repeated verification and strict rejection of conflicting outcome records.
  - Evaluation service (`PredictionEvaluator` in `app/history/evaluator.py`) isolating directional accuracy strictly to completed, verified sessions ($N_{verified}$) as the denominator, excluding pending/ineligible sessions from error metrics.
  - Symmetrical class metrics: UP and DOWN precision, recall, F1, and confusion matrix breakdown ($TP, FP, TN, FN$).
  - Full machine-readable serialization (`.to_dict()`) and formatted evaluation summary rendering (`.format_summary()`).
- NIFTY Benchmark & Sector Context Engine (`app/market/benchmark.py` - Day 26 complete):
  - Historical index ticker resolution in `YFinanceProvider._resolve_symbols` supporting pure indices (`^NSEI`, `^NSEBANK`, `^CNXIT`, `^BSESN`, `^CRSLDX`) and alias mappings (`NIFTY`, `BANKNIFTY`, `NIFTYIT`).
  - Sector benchmark mapping (`SECTOR_BENCHMARK_MAP` and `get_sector_benchmark`).
  - Strict point-in-time temporal alignment (`align_benchmark_series`) matching session dates ($bar.timestamp.date()$) without look-ahead bias and tolerating calendar/holiday discrepancies.
  - Relative performance features (`compute_relative_performance`): daily excess return (alpha), relative strength ratio, 5d and 20d relative strength momentum.
  - 20-session rolling beta and correlation with sample degrees of freedom ($ddof=1$) and zero-variance guards ($Var(R_b) < 1e-12 \implies None$).
  - Cross-sectional market breadth calculation (`compute_market_breadth` & `compute_multi_symbol_breadth_series`): advances, declines, unchanged, advance-decline ratio, breadth thrust, net advances, and 20-day SMA breadth participation percentage.
- Financial News Ingestion Foundation (`app/news/` - Day 27 complete):
  - Abstract news provider interface `BaseNewsProvider` and concrete `RSSNewsProvider` adapter acquiring live financial news for Indian equities (NSE/BSE).
  - Canonical immutable `NewsArticle` schema capturing cleaned headline, publisher source, timezone-aware publication time (`Asia/Kolkata`), distinct ingestion time, symbol associations, URL, summary, and deterministic 16-character SHA-256 `article_id`.
  - Multi-tier syndicated news deduplication engine (`deduplicate_news` in `cleaner.py`): removes exact ID duplicates, URL duplicates, and syndicated matching headlines across outlets within configurable time windows (default 48h) while preserving earliest publication provenance.
  - Strict point-in-time session filtering (`filter_news_point_in_time`): enforces $published\_at \le as\_of\_time$ and $ingested\_at \le as\_of\_time$, strictly preventing look-ahead leakage when joining news with historical trading sessions.
  - Non-causal representation: headlines are preserved as clean textual observations without mechanical causal inferences.
- FinBERT Financial Sentiment Scoring Foundation (`app/news/sentiment.py` & `app/nlp/` - Day 28 complete):
  - Domain-specific financial sentiment scoring using `ProsusAI/finbert` (Apache 2.0 open-source license).
  - Lazy model initialization ensuring zero overhead or heavy dependencies are loaded during package imports or standard CLI operations.
  - Dynamic `id2label` mapping resolution directly from model configuration, safely accommodating model output order variations.
  - Pluggable backend architecture: concrete `FinBERTBackend` for PyTorch/Transformers inference and deterministic `MockSentimentBackend` enabling 100% offline unit testing without downloading model weights.
  - Error quarantining & anti-fabrication: captures missing dependencies or inference exceptions into `status="ERROR"` with `sentiment_label=None` and `probabilities=None` (zero fake neutrals).
  - Text preparation with headline validation and configurable character boundary truncation (`prepare_article_text`).
  - Canonical immutable `ArticleSentimentResult` schema validating finite probabilities in $[0, 1]$ summing to $1.0 \pm 10^{-3}$, winning confidence score equality, and distinct `scored_at` execution timestamps.
  - Strict capability disclosures: text sentiment is strictly classified linguistic tone, not a stock price forecast.
- 362 automated unit tests passing across foundation, settings, logging, canonical schemas, provider adapters, data cleaning, returns/volatility calculations, pipeline orchestration, moving averages, RSI, MACD, Bollinger Bands, ATR, ROC, candlestick features, trend engine, prediction target layer, technical feature matrix assembly, XGBoost direction classifier, LightGBM direction classifier, baseline comparison suite, walk-forward cross-validation engine, model error analysis, feature usefulness audit, prediction service engine, structured prediction output, visualizer, SQLite prediction database, outcome verification/evaluation, benchmark context engine, financial news ingestion foundation, and FinBERT financial sentiment scoring foundation.

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
