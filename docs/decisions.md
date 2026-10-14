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

---

## ADR 14: Environment-Driven Configuration with Zero-Secret Commitment
- **Status:** Accepted
- **Context:** Applications need flexible runtime configuration across development, testing, and production without hardcoding values or leaking credentials.
- **Decision:** Application settings are managed centrally via `app/core/config.py` using standard dataclasses and `python-dotenv`. Default values are restricted strictly to safe, non-sensitive parameters. Secrets must be supplied via environment variables at runtime and are guarded by `.gitignore`.
- **Consequences:** Configuration is centralized, typed, immutable, and immune to credential leaks in version control.

---

## ADR 15: Centralized Standard-Library Logging Foundation
- **Status:** Accepted
- **Context:** Modules across ingestion, prediction, and API need uniform log formatting, timestamps, and log-level control without adding heavy third-party telemetry dependencies.
- **Decision:** Logging is implemented centrally in `app/core/logging_config.py` using Python's standard `logging` library. Modules obtain namespaced loggers via `get_logger(__name__)`.
- **Consequences:** Zero external dependencies, consistent output formatting across all future modules, and clean debuggability.

---

## ADR 16: Canonical Internal Schemas Separated from External Providers
- **Status:** Accepted
- **Context:** Financial data providers (NSE, Yahoo Finance, brokers) use wildly differing field names, timestamp formats, and JSON structures. Direct usage throughout downstream code causes tight coupling and fragile pipelines.
- **Decision:** All internal pipelines consume only canonical schema contracts (`app/core/schemas.py`). External payloads must be mapped into canonical contracts immediately at the adapter boundary.
- **Consequences:** Downstream feature engineering and modeling are insulated from upstream provider format changes.

---

## ADR 17: Strict Preservation of Timestamps and Data Provenance
- **Status:** Accepted
- **Context:** Time-series models and point-in-time prediction verification depend on knowing exactly when an observation occurred and where it originated.
- **Decision:** All canonical market data structures require explicit `timestamp` (as valid `datetime` objects) and non-empty `source` tags.
- **Consequences:** Prevents temporal leakage, eliminates look-ahead bias, and provides an immutable audit trail for every data point.

---

## ADR 18: Strict Structural and Domain Validation on Market Contracts
- **Status:** Accepted
- **Context:** Corrupted or unphysical market records (negative prices, high lower than low, inverted OHLC relationships) cause silent failures or distorted features in ML models.
- **Decision:** Canonical contracts enforce domain validation at instantiation time (positive prices, non-negative volume, high >= max(open, close), low <= min(open, close)).
- **Consequences:** Malformed data fails fast with explicit `ValidationError` before corrupting cached datasets or model training matrices.

---

## ADR 19: Centralized Canonical Schemas Preserved Without Duplication
- **Status:** Accepted
- **Context:** As domain packages like `app/market/` are established, there is a risk of defining competing duplicate dataclasses or models for OHLCV bars.
- **Decision:** The canonical market-data contracts remain strictly centralized in `app/core/schemas.py`. The `app/market/` package re-exports and consumes these contracts directly rather than declaring duplicate representations.
- **Consequences:** Eliminates schema fragmentation, guarantees single-point validation, and avoids duplicate type maintenance.

---

## ADR 20: Separation of Historical Collection from Minimal Provider Abstraction
- **Status:** Accepted
- **Context:** Implementing concrete data ingestion collectors before establishing contracts risks building over-engineered or source-coupled systems.
- **Decision:** Establish a minimal abstract provider contract (`BaseMarketDataProvider`) on Day 3 defining `fetch_historical_ohlcv(symbol, start_date, end_date, interval)` without writing any concrete network scrapers, downloads, or collectors today.
- **Consequences:** Satisfies Ponytail/YAGNI principles, sets clean boundaries between contract design (Day 3) and data collection (Day 4), and isolates provider-specific formats from downstream pipelines.

---

## ADR 21: Verification-First Stance on External Market Data Sources
- **Status:** Accepted
- **Context:** Public financial data sources are frequently assumed to have free, stable, and unrestricted APIs, which often breaks upon real deployment due to anti-bot measures, rate limits, or paywalls.
- **Decision:** No external provider is assumed to have a free, permanent public API without empirical verification. Evaluated sources are explicitly classified with statuses (`VERIFIED`, `PLANNED`, `TO BE VERIFIED`, `NOT SELECTED`). `yfinance` is selected as the primary Day 4 candidate marked `PLANNED / TO BE VERIFIED`, with official NSE Bhavcopy as the benchmark verification reference.
- **Consequences:** Prevents false architectural assumptions, protects against API surprises, and ensures Day 4 begins with explicit verification tests before data acquisition.

---

## ADR 22: Mandatory Point-in-Time Temporal Integrity and Provenance Guarantees
- **Status:** Accepted
- **Context:** Time-series ML models easily suffer from look-ahead bias and data leakage if market records lack unambiguous timestamps or if post-event revisions are used as historical observations.
- **Decision:** All provider adapters must supply explicit market bar observation `timestamp` and immutable `source` identifiers. Generic labels (e.g., "market_data") are prohibited. Data timestamped after forecast time $T_{pred}$ is strictly excluded from feature extraction.
- **Consequences:** Eliminates look-ahead bias, supports forensic auditability of past forecasts, and guarantees verifiable out-of-sample backtesting.

---

## ADR 23: Adoption and Empirical Verification of Yahoo Finance as Baseline Historical Collector
- **Status:** Accepted
- **Context:** Day 3 shortlisted Yahoo Finance (`yfinance`) with status `PLANNED / TO BE VERIFIED`. Before building downstream pipelines, empirical verification of network access, rate limits, and Indian equity coverage (`BHARTIARTL.NS`) is required.
- **Decision:** Yahoo Finance is accepted as the primary baseline historical provider after empirically verifying live data retrieval for `BHARTIARTL.NS` (fetching 6 canonical daily bars with 100% domain validation pass rate).
- **Consequences:** Provides a zero-cost, zero-auth historical pipeline for development; provider-specific quirks (e.g., exclusive end date in API calls) are encapsulated cleanly in `YFinanceProvider`.

---

## ADR 24: Raw Unadjusted Price Convention for Historical Market Bars
- **Status:** Accepted
- **Context:** Financial data providers provide both raw prices and retroactively adjusted prices (accounting for historical splits and dividends). Applying retroactive adjustments directly to bar OHLC prices distorts physical candle integrity (wicks, high/low bounds) and mixes raw volume with synthetic prices.
- **Decision:** The collector uses raw unadjusted prices (`auto_adjust=False`) for `MarketOHLCV` bars. Close, Open, High, Low reflect the exact traded prices during that historical session. Corporate action adjustments needed for continuous return calculations will be applied downstream in Day 6 feature engineering.
- **Consequences:** Preserves authentic market reality, ensures physical candle validity (`High >= max(Open, Close)`, `Low <= min(Open, Close)`), and prevents silent data corruption.

---

## ADR 25: Isolation of Provider DataFrames at Adapter Boundary
- **Status:** Accepted
- **Context:** Upstream libraries like `yfinance` produce Pandas DataFrames with library-specific indexes, columns, and types. Leaking DataFrames across the core architecture creates tight coupling and fragility.
- **Decision:** All Pandas DataFrames remain strictly private within `app/market/providers/yfinance_provider.py`. The provider adapter normalizes every row into canonical, immutable `MarketOHLCV` dataclass instances before returning them.
- **Consequences:** Downstream consumers receive strictly validated, typed dataclasses independent of any specific data vendor or tabular library.

---

## ADR 26: Strict Quarantine Policy for Missing Market OHLCV Values
- **Status:** Accepted
- **Context:** Missing values in critical financial time series (prices or volume) pose severe risks. Blind forward-filling, mean imputation, or linear interpolation fabricates artificial market transactions, distorts volatility calculations, and biases model predictions.
- **Decision:** The data cleaning layer strictly rejects/quarantines records with missing, null, or NaN prices, volume, or timestamps. Zero price interpolation or synthetic bar creation is permitted.
- **Consequences:** Guarantees historical data integrity; missing observations are made explicit in `CleaningSummary` audit logs rather than silently masked.

---

## ADR 27: Deterministic Duplicate Resolution Policy
- **Status:** Accepted
- **Context:** Historical feeds can deliver duplicate records for the same `(symbol, timestamp)` due to vendor republishing or boundary overlaps. Duplicates may be identical or contain conflicting numbers.
- **Decision:** The cleaning pipeline applies a two-tier deterministic policy:
  1. Identical duplicates (identical prices and volume) are collapsed safely into a single canonical bar.
  2. Conflicting duplicates (different prices/volume for the same timestamp) are quarantined/rejected entirely without guessing a preferred value.
- **Consequences:** Eliminates double-counting in backtests while preventing ungrounded heuristics from fabricating consensus prices.

---

## ADR 28: Asia/Kolkata Timezone Normalization with Trading Session Date Preservation
- **Status:** Accepted
- **Context:** Timestamps across financial vendors arrive with varying timezone representations (UTC, naive, localized). Inadvertent timezone conversion can shift midnight bars to previous or subsequent calendar dates, misaligning market session days.
- **Decision:** All timestamps are normalized to `Asia/Kolkata`. Timezone-naive daily bars are interpreted directly as `Asia/Kolkata` sessions (preserving the exact calendar date), and aware timestamps are converted via standard timezone offsets.
- **Consequences:** Guarantees consistent point-in-time temporal alignment across Indian market sessions without calendar drift.

---

## ADR 29: Non-Destructive Raw Data Pipeline Architecture
- **Status:** Accepted
- **Context:** Destructively altering raw collected market records makes retrospective error investigation, cleaning rule audits, and provenance verification impossible.
- **Decision:** Raw collector outputs are never mutated. `clean_market_data` accepts inputs immutably and returns newly constructed, validated `MarketOHLCV` lists alongside structured `CleaningSummary` audit metrics.
- **Consequences:** Preserves raw source provenance, maintains a complete audit trail from provider to cleaned dataset, and allows re-running updated cleaning rules without re-fetching data.

---

## ADR 30: Daily Simple Percentage Return Convention with Unavailable First Observation
- **Status:** Accepted
- **Context:** Financial return series can be calculated via simple percentage returns $((P_t / P_{t-1}) - 1)$ or log returns $(\ln(P_t / P_{t-1}))$. Additionally, the first observation has no prior closing price, and naive implementations risk fabricating artificial zero returns or dividing by zero.
- **Decision:** The feature layer standardizes on simple percentage returns $R_t = (P_t / P_{t-1}) - 1$ using raw unadjusted close prices. The first observation explicitly yields `None` (unavailable). Any non-positive prior price ($P_{t-1} \le 0$) safely yields `None` rather than raising a division-by-zero error or generating infinity.
- **Consequences:** Provides an interpretable, additive price-change metric aligned with canonical equity modeling without fabricating ungrounded initial data.

---

## ADR 31: Multi-Session Rolling Return Calculation with Strict Point-in-Time Guarantees
- **Status:** Accepted
- **Context:** Downstream models benefit from multi-day price momentum features over various horizons. If rolling calculations inadvertently use forward indexing (`shift(-1)`), future data leaks into current features.
- **Decision:** Rolling returns are defined as $R_{t, w} = (P_t / P_{t-w}) - 1$ over configurable sessions (default 3-session and 5-session windows). Calculations are strictly point-in-time: at session $t$, only observations at or prior to $t$ are accessed. Observations where $t < w$ remain `None`.
- **Consequences:** Completely eliminates lookahead bias in rolling feature creation, ensuring valid out-of-sample backtesting.

---

## ADR 32: Sample Standard Deviation with Bessel Correction (ddof=1) for Time-Series Volatility
- **Status:** Accepted
- **Context:** Standard deviation can be computed as population ($N$, `ddof=0`) or sample ($N-1$, `ddof=1`). Ambiguity across libraries leads to subtle feature discrepancies between training and inference.
- **Decision:** All return standard deviation and realized volatility calculations strictly use sample standard deviation with Bessel correction ($ddof=1$) computed via Python standard library mathematics. If valid samples $\le ddof$, the statistic yields `None`.
- **Consequences:** Provides an unbiased estimate of historical return dispersion and maintains mathematical consistency with standard econometric libraries.

---

## ADR 33: Raw Realized Volatility Basis with Explicit Annualization Scaling for Indian Equities
- **Status:** Accepted
- **Context:** Volatility is often cited in annualized terms, but mixing raw daily return volatility with annualized figures causes scale mismatch in machine learning feature sets.
- **Decision:** The primary realized volatility metric is raw rolling daily return standard deviation. When annualized volatility is required, it is computed in an explicitly distinct attribute (`annualized_volatility`) scaled by $\sqrt{252}$ reflecting the ~252 annual trading sessions in the Indian market (NSE/BSE).
- **Consequences:** Prevents confusion between daily standard deviations and annualized figures while ensuring proper feature scaling for downstream gradient-boosted models.

---

## ADR 34: Headless Matplotlib Visualization Layer and Ignored Chart Artifact Storage
- **Status:** Accepted
- **Context:** Market time-series inspection requires visual charts (price history, daily percentage returns), but execution occurs across headless CI environments, CLI commands, and servers lacking active display windows. Additionally, binary image files must not pollute git commit history.
- **Decision:** Adopt Matplotlib as a lightweight visualization dependency using the headless `Agg` backend (`matplotlib.use("Agg")`). All generated chart files are written to `data/processed/charts/` which is ignored by version control.
- **Consequences:** Enables reliable automated chart generation across headless OS environments and keeps git repositories free of binary bloat.

---

## ADR 35: Moving Average Technical Indicators, Price Basis, and Point-in-Time Integrity
- **Status:** Accepted
- **Context:** Downstream predictive models and market regime analyzers require trend-following and momentum features like Simple Moving Averages (SMA) and Exponential Moving Averages (EMA). Naive implementations risk subtle future data leakage (lookahead bias), improper handling of early sessions where historical bars are fewer than the window size ($t < W$), or mutating source OHLCV data.
- **Decision:**
  1. **Price Basis:** Moving averages are strictly computed using raw, unadjusted closing prices (`close` from canonical `MarketOHLCV`).
  2. **Window Selection & Extensibility:** Default windows are configured for 5 sessions (`sma_5`, `ema_5`) and 10 sessions (`sma_10`, `ema_10`), with arbitrary positive integer window support.
  3. **Zero Future Leakage:** For any session $t$, the calculation window spans strictly $[t - W + 1, t]$. Future observations are never accessed.
  4. **Insufficient History Handling:** Sessions prior to full window warmup ($t < W - 1$) return `None`. No arbitrary synthetic zeros or partial-window distortions are introduced into standard SMA.
  5. **EMA Recursive Formulation:** EMA applies smoothing factor $\alpha = \frac{2}{W + 1}$ initialized with the first SMA or historical seed and suppresses outputs (`None`) until $W$ sessions have elapsed, matching point-in-time warmup expectations.
  6. **Non-Destructive Feature Container:** Raw market records are never modified. Results are encapsulated in `MovingAverageFeatures` dataclasses with `.to_dict()` tabular serialization.
- **Consequences:** Guarantees deterministic, reproducible, leak-free indicator generation that integrates seamlessly with existing pipeline and future machine learning models.

---

## ADR 36: Relative Strength Index (RSI) Smoothing, Edge-Case Handling, and Flexible Historical Lookbacks
- **Status:** Accepted
- **Context:**
  1. The Day 8 historical verification returned only 6 sessions because verification scripts hardcoded a bounded 8-calendar-day range (`2026-09-01` to `2026-09-08`). As a consequence, 10-session MAs could not warm up, and longer indicators like 14-period RSI were uncomputable. Callers required a flexible historical lookback parameter without breaking existing explicit date contracts.
  2. Momentum feature engineering requires the Relative Strength Index (RSI). Ambiguity in smoothing methods (Wilder's vs simple EMA vs SMA-based RS) and undefined divisions (flat prices, zero losses, zero gains) can cause numerical instabilities or leakage between training and inference.
- **Decision:**
  1. **Flexible Pipeline Lookback:** `run_market_data_pipeline` supports `lookback_days` (defaulting to 180 calendar days / ~120 trading sessions when `start_date` is omitted), while preserving explicit `start_date` and `end_date` parameters for deterministic testing.
  2. **Wilder's Smoothing Formulation:** RSI adopts J. Welles Wilder's recursive smoothing method with multiplier $\alpha = 1 / W$. The first $W$ price changes (at index $W$, requiring $W+1$ prices) are seeded via simple arithmetic mean:
     $$AvgGain_{W} = \frac{1}{W} \sum_{i=1}^{W} U_i, \quad AvgLoss_{W} = \frac{1}{W} \sum_{i=1}^{W} D_i$$
     Subsequent sessions apply Wilder's recursive smoothing:
     $$AvgGain_t = \frac{AvgGain_{t-1} \times (W - 1) + U_t}{W}, \quad AvgLoss_t = \frac{AvgLoss_{t-1} \times (W - 1) + D_t}{W}$$
  3. **Edge-Case Resolution & Boundedness:**
     $$RSI = 100 \times \frac{AvgGain}{AvgGain + AvgLoss}$$
     - Flat prices ($AvgGain = 0$ and $AvgLoss = 0$): returns `50.0` (neutral baseline).
     - Gains without losses ($AvgGain > 0$ and $AvgLoss = 0$): returns `100.0`.
     - Losses without gains ($AvgLoss > 0$ and $AvgGain = 0$): returns `0.0`.
     - Output is bounded strictly in $[0.0, 100.0]$ when defined.
  4. **Warmup & Insufficient History:** For sessions $t < W$ (fewer than $W$ price changes), RSI evaluates strictly to `None`. No synthetic padding is introduced.
  5. **Non-Predictive Disclaimer:** RSI is strictly treated as an empirical momentum feature and input to downstream ML models, never as a guaranteed standalone predictor of price direction.
- **Consequences:** Provides robust, leak-free momentum indicator calculation and allows collecting 6 to 12 months of clean historical data for comprehensive feature evaluation.

---

## ADR 37: Moving Average Convergence Divergence (MACD) Architecture, Recursive Signal Smoothing, and Point-in-Time Integrity
- **Status:** Accepted
- **Context:** Downstream models and technical feature pipelines require trend-following and momentum indicators that capture interactions between short-term and medium-term price trends. The standard Moving Average Convergence Divergence (MACD) indicator is widely recognized, but naive implementations often suffer from:
  1. Lookahead data leakage if smoothing recursions access future values.
  2. Fabricating numbers during warm-up periods or when intermediate values are undefined.
  3. Treating negative MACD line values as invalid errors in general-purpose EMA routines designed only for asset price series ($P > 0$).
  4. Histogram divergence where $Histogram \ne MACD - Signal$ due to rounding, asynchronous updates, or mismatched smoothing parameters.
- **Decision:**
  1. **Canonical Formulation:**
     - Fast EMA: $EMA_{fast, t} = EMA(prices, window=fast\_period)$ with standard default 12.
     - Slow EMA: $EMA_{slow, t} = EMA(prices, window=slow\_period)$ with standard default 26.
     - MACD Line: $MACD_t = EMA_{fast, t} - EMA_{slow, t}$.
     - Signal Line: $Signal_t = EMA(MACD, window=signal\_period)$ with standard default 9.
     - MACD Histogram: $Histogram_t = MACD_t - Signal_t$.
  2. **EMA Generalization & Oscillator Compatibility:**
     - Extended existing `calculate_ema` with `allow_negative: bool = False`.
     - When `allow_negative=False` (default, price series), non-positive or NaN values are treated as invalid.
     - When `allow_negative=True` (used for MACD oscillator series), negative and zero values are valid floats, allowing standard recursive smoothing without error or spurious warnings.
  3. **Strict Warm-up & Undefined Values Policy:**
     - Fast period must be strictly less than slow period ($fast < slow$), and all periods must be positive integers ($W \ge 1$).
     - Insufficient history: Fast EMA warms up at $t = fast - 1$; Slow EMA warms up at $t = slow - 1$.
     - MACD line requires both fast and slow EMAs, so for $t < slow - 1$, MACD line returns `None`.
     - Signal line is the signal-period EMA of the MACD line; it requires $signal$ valid observations of the MACD line. Therefore, for $t < (slow - 1) + (signal - 1) = slow + signal - 2$ (first 33 sessions for 12/26/9), Signal line returns `None`.
     - Histogram requires both MACD line and Signal line; for $t < slow + signal - 2$, Histogram returns `None`.
     - Numbers are never fabricated or padded; undefined sessions return `None`.
  4. **Strict Histogram Identity:**
     - For all sessions where the Signal line is defined, $Histogram = MACD - Signal$ holds strictly within floating-point tolerance ($10^{-6}$).
  5. **Container & Unpacking Ergonomics:**
     - Created `MACDSeries(macd, signal, histogram)` implementing sequence protocol `__iter__` to allow both 3-tuple unpacking (`macd, signal, hist = calculate_macd(prices)`) and attribute access (`res.macd`, `res.signal`, `res.histogram`).
     - Integrated MACD features into `MovingAverageFeatures` with properties `macd_line`, `signal_line`, `histogram` and tabular `.to_dict()` export (`"macd"`, `"macd_signal"`, `"macd_histogram"`).
  6. **Pipeline Integration:**
     - Added `macd_fast=12`, `macd_slow=26`, `macd_signal=9` parameters to `process_market_data` and `run_market_data_pipeline`.
  7. **Non-Predictive Disclaimer:**
     - MACD is strictly treated as an empirical trend-following momentum feature, never as a guaranteed price-direction predictor.
- **Consequences:** Guarantees leak-free, mathematically verified MACD calculation that integrates seamlessly with existing pipeline and test suites.

---

## ADR 38: Bollinger Bands Technical Indicator Architecture, Degrees of Freedom Convention, and Zero-Denominator Safety
- **Status:** Accepted
- **Context:** Downstream models and market regime analyzers require volatility bands around moving averages to quantify volatility expansion, contraction (squeezes), and relative price location. The canonical Bollinger Bands indicator consists of a middle moving average, an upper band, a lower band, Band Width, and %B. Naive implementations often suffer from:
  1. Ambiguity in standard deviation degrees of freedom: Python/pandas `.std()` defaults to sample standard deviation ($ddof=1$), whereas John Bollinger's canonical specification uses population standard deviation ($ddof=0$, dividing by $N$).
  2. Fabricating numbers during warm-up periods ($t < W - 1$) or across missing price sessions.
  3. Division by zero in Band Width ($(Upper - Lower) / Middle$) when the middle band is zero/negative, or in %B ($(Close - Lower) / (Upper - Lower)$) during flat-price regimes where upper equals lower.
  4. Future data leakage if rolling windows access forward prices.
  5. Misinterpreting band touches as mechanical buy/sell signals rather than quantitative volatility and location features.
- **Decision:**
  1. **Canonical Formulation & Defaults:**
     - Rolling Window: $W = 20$ trading sessions.
     - Multiplier: $M = 2.0$ standard deviations (parameterized as `multiplier` with `num_std` alias).
     - Standard Deviation Convention: Default population standard deviation ($ddof=0$):
       $$\sigma_{t, W} = \sqrt{\frac{1}{W} \sum_{i=0}^{W-1} (P_{t-i} - Middle_t)^2}$$
       Configurable $ddof$ supported, validating $0 \le ddof < W$.
     - Middle Band: $Middle_t = SMA_{t, W}(prices)$.
     - Upper Band: $Upper_t = Middle_t + M \times \sigma_{t, W}$.
     - Lower Band: $Lower_t = Middle_t - M \times \sigma_{t, W}$.
     - Band Width: $BandWidth_t = \frac{Upper_t - Lower_t}{Middle_t}$.
     - Percent B (%B): $\%B_t = \frac{Close_t - Lower_t}{Upper_t - Lower_t}$.
  2. **Safe Zero-Denominator & Edge-Case Handling:**
     - For flat-price series where all prices in the window are identical: $Upper == Lower == Middle$, so $\sigma = 0.0$.
     - Band Width numerator is 0.0, evaluating safely to `0.0` when $Middle > 0$.
     - %B denominator is $(Upper - Lower) = 0.0$; evaluates safely to `None` without division-by-zero crashes.
     - Non-positive middle band ($Middle \le 0$) yields `None` for Band Width.
  3. **Strict Warm-up & Missing Observation Policy:**
     - Sessions prior to full window warmup ($t < W - 1$, first 19 sessions for $W=20$) strictly return `None` across all 5 series.
     - Missing, NaN, or non-positive price observations invalidate affected rolling windows, returning `None`.
     - Zero data fabrication or artificial zero-padding.
  4. **Container & Unpacking Ergonomics:**
     - Created `BollingerBandsSeries` dataclass holding `middle`, `upper`, `lower`, `bandwidth`, and `percent_b` lists.
     - Implements sequence protocol `__iter__` to allow 5-tuple sequence unpacking:
       `middle, upper, lower, bw, pb = calculate_bollinger_bands(prices)`
       as well as attribute access and `.band_width` alias.
  5. **Feature Container & Pipeline Integration:**
     - Integrated Bollinger Bands into `MovingAverageFeatures` with properties `bollinger_middle`, `bollinger_upper`, `bollinger_lower`, `bollinger_bandwidth`, `bollinger_band_width`, and `bollinger_percent_b`.
     - Serializes both `bb_*` and `bollinger_*` keys in `.to_dict()` for downstream tabular and ML dataset convenience.
     - Added `bb_window=20`, `bb_multiplier=2.0`, `bb_ddof=0` parameters to `process_market_data` and `run_market_data_pipeline`.
  6. **Non-Predictive Baseline Disclaimer:**
     - Bollinger Bands and %B are strictly quantitative features representing volatility regimes and relative price positioning; band touches are never treated as guaranteed buy or sell signals.
- **Consequences:** Guarantees leak-free, mathematically verified Bollinger Bands calculations adhering strictly to canonical definitions and robust edge-case handling.

---

## ADR 39: Average True Range (ATR) and Rate of Change (ROC) Technical Indicators Architecture, Wilder Smoothing Recurrence, and Safe Relative Momentum
- **Status:** Accepted
- **Context:** Downstream numerical machine learning models require volatility and momentum features that reflect trading range expansion/contraction and price velocity. The system requires two foundational indicators: Average True Range (Wilder's ATR) and Rate of Change (ROC). Naive implementations often suffer from:
  1. Ambiguity in first-session True Range initialization when no prior closing price exists ($t=0$).
  2. Inconsistent smoothing formulas: confusion between simple rolling average, standard EMA ($\alpha = 2 / (N+1)$), and Wilder's smoothing recurrence ($\alpha = 1 / N$).
  3. Failure to validate physical OHLC candle geometry ($high \ge low$, positive prices) leading to negative or nonsense ranges.
  4. Division by zero or crashes in ROC when historical closing prices are missing, zero, or non-positive.
  5. Future data leakage or cross-symbol contamination in rolling series calculations.
  6. False claims of price direction prediction: ATR measures volatility magnitude regardless of direction, while ROC measures past price change rate without forecasting future trajectory.
- **Decision:**
  1. **Average True Range (ATR) Formulation & Wilder Recurrence:**
     - Parameter: Configurable positive integer `period` (default 14 sessions).
     - True Range ($TR_t$):
       - First session policy ($t=0$): $TR_0 = High_0 - Low_0$ when valid.
       - Subsequent sessions ($t > 0$):
         $$TR_t = \max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|)$$
     - Wilder Smoothing Recurrence:
       - Initial seed at index $t = period - 1$ (e.g., $t=13$ for $period=14$): Simple arithmetic mean of first $period$ valid True Range values:
         $$ATR_{period-1} = \frac{1}{period} \sum_{i=0}^{period-1} TR_i$$
       - Subsequent sessions ($t \ge period$):
         $$ATR_t = \frac{(period - 1) \times ATR_{t-1} + TR_t}{period}$$
     - Sessions prior to full period warmup ($t < period - 1$) strictly return `None`.
     - Dual-mode input signature: accepts either a sequence of `MarketOHLCV` records or separate sequences of high, low, and close floats.
  2. **Rate of Change (ROC) Formulation & Safe Momentum:**
     - Parameter: Configurable positive integer `period` / `lookback` (default 10 sessions).
     - Formula:
       $$ROC_{t, n} = \left(\frac{Close_t}{Close_{t-n}} - 1\right) \times 100$$
     - Warmup: Sessions where $t < n$ strictly return `None`.
     - Zero & Negative Denominator Protection: Returns `None` if $Close_{t-n} \le 0$ or if historical price is invalid/missing.
     - Flat Price Regimes: Series with identical prices evaluate safely to `0.0`.
  3. **Point-in-Time Integrity & Multi-Symbol Isolation:**
     - Indicator computations operate exclusively on historical and contemporaneous observations up to session timestamp $t$.
     - When calculating across multi-symbol datasets, records are isolated by ticker symbol and sorted chronologically before feature calculation.
  4. **Container & Pipeline Integration:**
     - Integrated `atr: Dict[int, Optional[float]]` and `roc: Dict[int, Optional[float]]` into `MovingAverageFeatures`.
     - Provided convenience properties `atr_14` and `roc_10`.
     - Serializes `atr_{p}` and `roc_{p}` keys in `.to_dict()` tabular output.
     - Extended `process_market_data` and `run_market_data_pipeline` with `atr_periods=(14,)` and `roc_periods=(10,)` parameters.
  5. **Non-Predictive Baseline Disclaimer:**
     - ATR strictly quantifies price range volatility and carries no directional information; it does not predict whether prices will move up or down.
     - ROC measures historical price momentum and velocity; it does not constitute a guaranteed directional trading signal.
- **Consequences:** Guarantees leak-free, mathematically verified ATR and ROC calculations adhering to canonical formulas, Wilder's smoothing recurrence, and robust edge-case validation.

---

## ADR 40: Candlestick Feature Engineering Architecture, Geometric Wick-Body Partitioning, and Non-Predictive Intra-Session Price Dynamics
- **Status:** Accepted
- **Context:** Downstream numerical machine learning models require tabular feature representations of price action dynamics occurring within individual trading sessions. While moving averages and multi-session indicators capture trend and momentum across days, candlestick features capture intra-session supply and demand balance, rejection of price extremes (wicks), and closing conviction (body and close location). Naive implementations often suffer from:
  1. Inconsistent definitions of candle body, range, and upper/lower wicks across bullish and bearish regimes.
  2. Division-by-zero crashes or NaN explosions during flat or zero-range trading sessions where $High == Low$.
  3. Failure to validate physical OHLC candle geometry ($High \ge \max(Open, Close)$, $Low \le \min(Open, Close)$) leading to negative wicks or impossible close locations.
  4. False claims of predictive certainty: labeling candle shapes (e.g. hammers, engulfing bars, dojis) as guaranteed trading signals rather than neutral quantitative features.
  5. Inconsistent container naming, missing multi-symbol isolation, or accidental mutation of raw canonical records.
- **Decision:**
  1. **Canonical Geometric Formulations:**
     - For each valid OHLC candle observation:
       - Signed Body: $Close - Open$
       - Absolute Body: $|Close - Open|$
       - Candle Range: $High - Low$
       - Upper Wick: $High - \max(Open, Close)$
       - Lower Wick: $\min(Open, Close) - Low$
       - Body-to-Range Ratio: $\frac{|Close - Open|}{High - Low}$ when $Range > 0$ (evaluates safely to `None` when $Range = 0$).
       - Upper-Wick-to-Range Ratio: $\frac{UpperWick}{High - Low}$ when $Range > 0$ (evaluates safely to `None` when $Range = 0$).
       - Lower-Wick-to-Range Ratio: $\frac{LowerWick}{High - Low}$ when $Range > 0$ (evaluates safely to `None` when $Range = 0$).
       - Close Location within Range: $\frac{Close - Low}{High - Low}$ when $Range > 0$ (evaluates safely to `None` when $Range = 0$).
       - Body Return Percentage: $\left(\frac{Close}{Open} - 1\right) \times 100$ when $Open > 0$ (evaluates safely to `None` when $Open \le 0$).
       - Candle Direction: `bullish` if $Close > Open$, `bearish` if $Close < Open$, and `neutral` if $Close == Open$.
  2. **Geometric Partition & Ratio Invariants:**
     - The calculation preserves the exact physical partition identity:
       $$Body_{abs} + UpperWick + LowerWick = Range$$
     - When $Range > 0$, the normalized ratio partition identity holds:
       $$Ratio_{body} + Ratio_{upper} + Ratio_{lower} = 1.0$$
     - All ratios and the close location property are mathematically bounded in $[0.0, 1.0]$.
  3. **Safe Zero-Range & Invalid Geometry Handling:**
     - Zero-range sessions ($High == Low == Open == Close$) preserve valid zero dimensions ($Body=0.0$, $Range=0.0$, $Upper=0.0$, $Lower=0.0$), evaluate body return to `0.0%`, assign direction `neutral`, and set undefined zero-denominator ratios safely to `None`.
     - Invalid geometry ($High < Low$, $High < \max(Open, Close)$, $Low > \min(Open, Close)$) or non-finite/non-positive prices are safely masked with `None` across all calculated features.
  4. **Strict Point-in-Time Integrity & Multi-Symbol Isolation:**
     - Calculations depend exclusively on contemporaneous OHLC values of the current bar; zero lookahead or future observations affect earlier features.
     - `compute_candlestick_features` isolates records by ticker symbol and sorts chronologically by timestamp ascending.
     - Raw `MarketOHLCV` records are treated as immutable and never mutated.
  5. **Container & Pipeline Integration:**
     - Created `CandlestickFeatures` frozen dataclass with `.to_dict()` and convenience properties (`is_bullish`, `is_bearish`, `is_neutral`, `.body`, `.range`, etc.).
     - Integrated candlestick features into `MovingAverageFeatures` (both attribute access and `.to_dict()` serialization).
     - Extended `MarketDataPipelineResult` with `candlesticks: List[CandlestickFeatures]`, `.to_candlestick_dicts()`, and `"candlestick_count"` in summary dictionary.
  6. **Non-Predictive Baseline Disclaimer:**
     - Candlestick features are strictly quantitative representations of single-bar geometry; they do not constitute guaranteed directional trading signals or predictive forecasts.
- **Consequences:** Guarantees leak-free, mathematically verified candlestick features adhering to strict geometric validation, safe zero-denominator handling, and seamless pipeline integration.

---

## ADR 41: Trend Engine Architecture, Swing Confirmation Timing, and Market Structure Classification
- **Status:** Accepted
- **Context:** Downstream technical feature engineering and baseline price classification require identifying broader market regimes (uptrend, downtrend, or sideways) from historical OHLC price action. Naive swing detection or moving-average heuristics often suffer from:
  1. Look-ahead bias: labeling a historical price peak or trough as a "swing point" at the exact moment it occurs, ignoring that confirmation requires subsequent candles ($t + k$).
  2. Ambiguous trend definitions: misclassifying consolidation, broadening patterns, or insufficient history as sideways or directional trends without explicit rules.
  3. Insufficient data confusion: mislabeling warm-up periods or sparse data as `SIDEWAYS` rather than explicitly reporting `None` / `INSUFFICIENT_DATA`.
  4. Flaky tie-breaking on flat tops/bottoms: duplicate or consecutive identical swing extremes corrupting sequence counts.
  5. Tight coupling to execution or forecasting: conflating descriptive market structure with directional price predictions or trading advice.
- **Decision:**
  1. **Deterministic Local Extreme Rule & Configurable Flank Window:**
     - A bar at index $t$ is an identified **Swing High** if its `high` is strictly greater than all preceding $k$ bars ($t - k \dots t - 1$) and greater than or equal to all subsequent $k$ bars ($t + 1 \dots t + k$).
     - A bar at index $t$ is an identified **Swing Low** if its `low` is strictly less than all preceding $k$ bars ($t - k \dots t - 1$) and less than or equal to all subsequent $k$ bars ($t + 1 \dots t + k$).
     - Asymmetric strictness on the left flank prevents duplicate consecutive pivots during flat multi-bar extremes.
     - Default window $k=2$ is fully configurable via parameter `swing_window`.
  2. **Explicit Confirmation Timing & Look-Ahead Prevention:**
     - A swing pivot occurring at bar index $t$ becomes confirmed strictly at bar index $t + k$.
     - When analyzing historical data as-of cutoff index $T$, only swing points with `confirmation_index <= T` are considered confirmed and visible.
     - Candidate pivots occurring within the trailing $k$ bars ($t > T - k$) remain unconfirmed and are invisible to point-in-time decision logic.
  3. **Sequential Market Structure Labeling:**
     - Confirmed swings are compared to the immediately preceding confirmed swing of the same type:
       - Highs: Higher High (`HH` if $Price_n > Price_{n-1}$), Lower High (`LH` if $Price_n < Price_{n-1}$), Equal High (`EH` if $Price_n == Price_{n-1}$).
       - Lows: Higher Low (`HL` if $Price_n > Price_{n-1}$), Lower Low (`LL` if $Price_n < Price_{n-1}$), Equal Low (`EL` if $Price_n == Price_{n-1}$).
  4. **Strict Trend Classification Matrix:**
     - Requires at least `min_swings` (default 2) confirmed swing highs and 2 confirmed swing lows. If fewer confirmed swings exist, classification evaluates to `None` with status `INSUFFICIENT_DATA`.
     - `UPTREND`: Latest confirmed high is `HH` and latest confirmed low is `HL`.
     - `DOWNTREND`: Latest confirmed high is `LH` and latest confirmed low is `LL`.
     - `SIDEWAYS`: Sufficient confirmed swings exist, but structural relationships are mixed or conflicting (e.g. `HH` + `LL`, `LH` + `HL`, `EH`, `EL`).
  5. **Point-in-Time Rolling Series Alignment:**
     - Provided `compute_rolling_trends` which evaluates structure at each bar $t$ using exclusively historical data up to $t$, generating a 1:1 aligned sequence with zero future leakage.
  6. **Pipeline Integration & Non-Predictive Baseline Disclaimer:**
     - Integrated `trend: Optional[TrendAnalysisResult]` into `MarketDataPipelineResult` and `process_market_data` with complete dictionary serialization (`.to_dict()`).
     - Explicitly documented that trend classifications represent descriptive structural geometry and do not constitute forward price predictions or trading recommendations.
- **Consequences:** Guarantees deterministic, leak-free, typed market structure analysis and trend classification with zero lookahead bias, fully tested across synthetic fixtures, edge cases, and real market data.

---

## ADR 42: Machine Learning Prediction Target Formulation, Binary Direction Baseline, and Zero-Return Policy
- **Status:** Accepted
- **Context:** Supervised machine learning models in Phase 4 require an explicit, leakage-safe target variable ($y_t$) to train binary directional classifiers. Designing a financial market target introduces critical design challenges:
  1. Forward-looking leakage: Accidentally including the future outcome price ($Close_{t+1}$) or future return ($R_{t+1}$) in the feature vector of session $t$.
  2. Calendar-day vs. trading-day mismatch: Naively assuming that session $t+1$ is calendar day $t+1$, which fails across weekends, market holidays, and unscheduled exchange closures.
  3. Zero-return handling: Sessions where $Close_{t+1} == Close_t$ produce an exact zero return ($0.0\%$). Naively discarding them introduces survivorship and selection bias, while creating an ambiguous third class complicates binary classification.
  4. Final-observation leakage: The most recent historical bar ($t = N - 1$) has no realized next-session close. Fabricating or forward-filling a target creates synthetic false training data.
- **Decision:**
  1. **Mathematical Formulation:**
     - For a chronological sequence of trading sessions $t = 0, 1, \dots, N - 1$:
       $$target\_return[t] = \frac{Close_{t+1}}{Close_t} - 1.0$$
       $$target\_direction[t] = \begin{cases} \text{"UP"}, & \text{if } target\_return[t] > 0.0 \\ \text{"DOWN"}, & \text{if } target\_return[t] \le 0.0 \end{cases}$$
       $$target\_binary[t] = \begin{cases} 1, & \text{if } target\_return[t] > 0.0 \\ 0, & \text{if } target\_return[t] \le 0.0 \end{cases}$$
  2. **Initial Binary Baseline & Zero-Return Policy:**
     - For this initial binary classification baseline, zero-return sessions ($target\_return == 0.0$) are deterministically grouped into `"DOWN"` ($binary=0$).
     - Zero-return samples are explicitly retained in the dataset and never silently discarded.
     - Multi-class extensions (e.g. `UP`, `DOWN`, `FLAT`) or volatility-based threshold margins may be explored in subsequent iterations.
  3. **Trading-Session Alignment (Non-Calendar Spacing):**
     - $Close_t$ is the reference price of trading session $t$.
     - $Close_{t+1}$ is the outcome price of the NEXT AVAILABLE trading session in the chronological series.
     - Weekends (e.g. Friday to Monday) and market holidays (e.g. Diwali, Holi) are resolved naturally by chronological session indexing without calendar day synthesis.
  4. **Strict Leakage Prevention & Final-Observation Invariant:**
     - Features at session $t$ use only information available at or before session $t$.
     - The target $y_t$ is stored separately from feature vectors in `TargetObservation`.
     - The final observation ($t = N - 1$) has no realized future session; its target values evaluate strictly to `None` (`target_return=None`, `target_direction=None`, `target_binary=None`, `has_target=False`).
  5. **Component Separation:**
     - Target generation logic is isolated in `app/prediction/target.py` and kept strictly separate from feature calculation (`app/market/`) and model training (`app/training/`).
- **Consequences:** Provides a leak-free, deterministic, mathematically verified prediction target adhering to project return conventions, with robust handling of market calendar gaps and zero returns.

---

## ADR 43: Technical Feature Matrix Assembly, Model-Input/Target Isolation, and Natural Missing-Value Policy
- **Status:** Accepted
- **Context:** Supervised machine learning algorithms (such as gradient boosting models planned for Day 17) require tabular training datasets ($X, y$) constructed by joining historical technical features with forward prediction targets. Assembling tabular datasets in time-series finance introduces subtle hazards:
  1. Subtle target leakage: Accidental inclusion of future outcome columns (`next_close`, `target_return`, `target_direction`, `target_binary`) in feature matrix $X$, causing artificially inflated training metrics and total real-world failure.
  2. Blind global imputation: Filling rolling indicator warmup periods (e.g. SMA-10, MACD-26, Bollinger-20, ATR-14) with zeros prior to cross-validation splits. Blind zero-filling distorts distributions (e.g. replacing missing RSI with 0.0 falsely implies extreme oversold conditions) and fitting scalers/imputers across the full dataset causes global data leakage.
  3. Row misalignment: Joining features and targets by implicit array position rather than explicit timestamps, which can silently misalign samples if any row is dropped or shifted.
  4. Silent row dropping: Dropping warmup rows or unlabeled rows without transparent accounting, making audit verification impossible.
- **Decision:**
  1. **Strict Feature Matrix (X) and Target (y) Isolation:**
     - The assembly pipeline isolates numerical feature columns in `X`, binary labels in `y`, and audit fields in `metadata`.
     - Built-in validation guard (`validate_feature_matrix_isolation`) scans all columns in $X$ and strictly rejects any column containing forbidden terms (`target`, `next_`, `future`, `outcome`).
  2. **Canonical 37-Feature Schema:**
     - Features include exclusively information available at or before session $t$:
       - OHLCV Price & Volume: `open`, `high`, `low`, `close`, `volume`.
       - Returns & Volatility: `daily_return`, `rolling_return_3d`, `rolling_return_5d`, `rolling_volatility_5d`, `annualized_volatility_5d`.
       - Moving Averages: `sma_5`, `sma_10`, `ema_5`, `ema_10`.
       - Momentum & Oscillators: `rsi_14`, `macd`, `macd_signal`, `macd_histogram`.
       - Volatility Bands: `bb_middle`, `bb_upper`, `bb_lower`, `bb_bandwidth`, `bb_percent_b`.
       - True Range & Relative Velocity: `atr_14`, `roc_10`.
       - Candlestick Geometry: `candle_body`, `candle_body_abs`, `candle_range`, `candle_upper_wick`, `candle_lower_wick`, `candle_body_ratio`, `candle_upper_wick_ratio`, `candle_lower_wick_ratio`, `candle_close_location`, `candle_body_return_pct`, `candle_direction_encoded`.
       - Market Structure: `trend_regime_encoded` (point-in-time confirmed swing structure).
  3. **Explicit Key Joins & Integrity Validation:**
     - Target observations from Day 15 are joined strictly by `(symbol, timestamp)`. Missing join keys or mismatched timestamps fail loudly.
     - Input records are verified for duplicate timestamps and chronological order before assembly.
  4. **Preservation of Natural Warmup Missing Values:**
     - Missing values resulting from rolling indicator warmups are preserved as `np.nan` in the assembled dataset. Zero-filling is strictly avoided.
     - Documented requirement: Any imputation or scaling must be fitted strictly on training folds during cross-validation (Day 17) to prevent temporal data leakage.
  5. **Transparent Labeled Subset Extraction:**
     - `FeatureMatrixDataset.get_labeled_dataset()` provides transparent accounting: initial total rows, unlabeled final row exclusions ($y=NaN$), optional warmup row exclusions, and final retained row counts.
- **Consequences:** Guarantees leak-free, mathematically verified tabular dataset assembly with strictly isolated feature matrix $X$, verified alignment to Day 15 targets, and complete preservation of natural warmup missing values.

---

## ADR 44: Baseline XGBoost Direction Classifier, Chronological Holdout Partitioning, and Temporal Label Embargo
- **Status:** Accepted
- **Context:** Training the project's first machine learning model (Phase 4, Day 17) introduces critical risks of data leakage and unrealistic performance claims:
  1. Non-chronological leakage: Random k-fold or random train/test splits allow future data to predict past samples, creating artificially inflated metrics.
  2. Boundary label leakage: When partitioning chronologically, the final training observation at session $t_{train}$ has an outcome label evaluated at $t_{train} + 1$. If $t_{train} + 1$ is the first observation of the holdout period, the training target depends on future holdout closing prices.
  3. External dependency overhead: Using `xgboost.sklearn` forces an unneeded heavy dependency on `scikit-learn` when native XGBoost APIs (`xgb.train`, `xgb.DMatrix`) already provide complete gradient-boosting capabilities with zero sklearn dependency.
  4. Hyperparameter overfitting: Tuning hyperparameters or thresholds on the holdout partition invalidates the out-of-sample holdout guarantee.
  5. Unjustified performance claims: Claiming a predictive edge or calibrated trading probabilities based on an initial research baseline.
- **Decision:**
  1. **Native XGBoost Core API:** Use native `xgb.train()` and `xgb.DMatrix()` with explicit `binary:logistic` objective, `logloss` metric, and fixed random seed (42). This avoids adding `scikit-learn` to project dependencies while maintaining full control over feature schema and determinism.
  2. **Conservative Baseline Hyperparameters:** Use fixed, explicit hyperparameters (`max_depth=3`, `learning_rate=0.05`, `n_estimators=50`, `subsample=0.8`, `colsample_bytree=0.8`, `n_jobs=1`) without evaluation set tuning.
  3. **Strict Chronological Holdout with Temporal Embargo:** Implement `split_chronological_holdout` preserving strict ascending chronological order. Enforce an explicit 1-session embargo gap between train and holdout partitions such that the training outcome cutoff date is strictly prior to the holdout start date ($train\_outcome\_cutoff \le holdout\_start\_date$).
  4. **Strict Complete Labeled Row Extraction:** Supervised training is performed strictly on complete labeled rows (`drop_incomplete_warmup=True`), explicitly accounting for excluded warmup rows (33 sessions) and the final unlabeled observation (1 session).
  5. **Pure Python Metric Engine:** Implement `compute_classification_metrics` calculating Accuracy, Precision, Recall, F1, and Confusion Matrix using standard library and numpy, maintaining positive class convention as 1 (`UP`).
  6. **Research Baseline Disclaimer:** Document explicitly that this model is a non-calibrated research baseline with zero claims of commercial trading edge or guaranteed directional profitability.
- **Consequences:** Eliminates temporal leakage across split boundaries, maintains lean dependencies, ensures deterministic repeatability, and establishes an auditable baseline for Phase 4 benchmarking.

---

## ADR 45: Baseline Comparison Benchmark Protocol Prior to Model Optimization
- **Status:** Accepted
- **Context:** Directional stock market models are prone to misleading validation claims when assessed without simple non-parametric baselines. In small or regime-shifted holdout windows, a classifier predicting predominantly one class (e.g., UP) can easily show superficial positive recall or F1 while failing to beat trivial majority-class heuristics or stratified coin flips. Escalating model complexity or tuning hyperparameters before proving that a model beats simple baselines is premature optimization.
- **Decision:**
  1. **Mandatory Baseline Benchmarks:** Every directional model must be evaluated against three standard baselines under identical chronological partitions, identical sample indices, and identical metric conventions:
     - *Baseline A (Majority-Class Classifier):* Predicts the most frequent class in the training partition, with deterministic tie-breaking.
     - *Baseline B1 (Uniform Random Classifier):* Fixed-seed (seed=42) pseudo-random coin flip with $P(UP) = 0.5$.
     - *Baseline B2 (Stratified Random Classifier):* Fixed-seed (seed=42) pseudo-random generation matching training class prior $P(UP) = P(y_{train} = 1)$.
  2. **Evaluation Parity:** All baselines must consume identical holdout partitions, respect identical 1-session embargo gaps, and use canonical `compute_classification_metrics`.
  3. **Optimization Gate:** If a complex model fails to beat majority-class or class-prior random baselines, hyperparameter tuning and model deployment are suspended in favor of expanding sample history and analyzing structural feature representation.
- **Consequences:** Enforces rigorous scientific humility, exposes upward/downward prediction biases transparently, and prevents false claims of predictive edge.

---

## ADR 46: Multi-Year Price Adjustment Semantics, Corporate Action Invariants, and Dividend Policy
- **Status:** Accepted
- **Context:** Expanding historical data to multi-year windows (~5 years, 1,234 sessions) introduces corporate action events (cash dividends and stock splits). Using raw close prices ($Close$) vs dividend-adjusted prices ($Adj Close$) raises methodological trade-offs:
  1. Mixing adjusted $Close$ with unadjusted $Open$, $High$, $Low$ creates artificial candlestick distortions (e.g. $Close > High$ or $Close < Low$).
  2. Enabling `auto_adjust=True` scales historical OHLC values backward every time a future corporate action occurs. This retroactively alters historical numbers, violating point-in-time stability and masking actual traded price levels.
  3. Cash dividends cause an ex-date price drop equal to the dividend payout per share, which can superficially make a raw price return negative even if the total economic return was positive.
- **Decision:**
  1. **Preservation of Raw Unadjusted Price Convention (`auto_adjust=False`):**
     - Canonical `MarketOHLCV` records retain raw traded prices, ensuring physical candlestick geometry ($Low \le Open, Close \le High$), authentic intraday spreads, and point-in-time permanence.
     - Historical prices must never be retroactively rewritten upon subsequent dividend distributions.
  2. **Distinction Between Raw Price Direction and Total Return:**
     - *Raw Close-to-Close Price Direction:* Measures nominal traded price change ($Close_{t+1} / Close_t - 1.0 > 0$). It reflects exchange quote movement and capital gains/losses excluding cash flows.
     - *Dividend-Inclusive Total Return:* Measures investor economic wealth accrual ($[Close_{t+1} + Dividend_{t+1}] / Close_t - 1.0 > 0$). It reflects the true economic payoff of holding the equity across ex-dividend dates.
  3. **Empirical Dividend Impact Audit on Target Equity (BHARTIARTL.NS):**
     - Across the 5-year observation period (1,234 sessions), exactly 5 dividend events occurred (totaling ₹55.00/share).
     - Directional label impact: On 4 of the 5 dividend dates (80%), the directional classification was identical between raw price returns and dividend-adjusted returns.
     - Exactly 1 session (2024-08-07, ₹8.00 payout) experienced a direction flip (-0.12% raw vs +0.43% dividend-adjusted).
     - *Methodological Caveat:* High empirical label agreement (99.919% across all sessions) demonstrates sample sensitivity for BHARTIARTL over this window, but raw-versus-adjusted directional comparisons alone do NOT establish that raw price direction is the economically "correct" label. For an investor, cash received is genuine return; treating an ex-dividend price drop as a negative outcome misrepresents economic performance on that single session.
  4. **Preservation of Existing Target Policy (No Silent Alteration):**
     - For the Day 19 and Day 20 baselines, the supervised binary classification target remains defined strictly by next-session raw close-to-close returns ($Close_{t+1} / Close_t - 1.0 > 0$), consistent with ADR 42.
  5. **Unresolved Limitations & Future Decision Pathway:**
     - *Limitations:* Mechanical ex-dividend price gaps introduce artificial downward label bias on ex-dates. On high-yielding equities, utilities, or REITs, directional divergences between raw price return and total return will be significantly larger than 0.081%.
     - *Future Decision:* If trading strategy backtesting, execution modeling, or portfolio performance evaluation is introduced (Phases 5+), a separate architectural decision will formally define a Total Return Target Layer (or corporate-action adjustment policy) without mutating canonical raw market data records.
- **Consequences:** Preserves data contract integrity, prevents retroactive look-ahead scaling of historical candles, documents corporate-action effects with scientific precision, and avoids conflating exchange quote forecasting with economic total return.

---

## ADR 47: LightGBM Direction Classifier Baseline & Multi-Year Benchmark Protocol
- **Status:** Accepted
- **Context:** Following the multi-year expansion, a second gradient-boosted decision tree architecture (LightGBM) is evaluated to test architectural generalization against XGBoost and non-parametric baselines.
- **Decision:**
  1. **Native LightGBM Core API:** Implement `LightGBMDirectionClassifier` using native `lgb.train()` and `lgb.Dataset()` with single-thread determinism (`num_threads=1`, `deterministic=True`, `seed=42`) and zero dependency on `scikit-learn`.
  2. **Symmetrical Baseline Hyperparameters:** Use hyperparameters equivalent to the baseline XGBoost classifier (`max_depth=3`, `num_leaves=7`, `learning_rate=0.05`, `n_estimators=50`, `subsample=0.8`, `colsample_bytree=0.8`) with zero tuning on holdout data.
  3. **Strict Evaluation Parity:** Evaluate LightGBM on the exact same multi-year chronological holdout (240 sessions), same 1-session embargo gap, and identical feature matrix schema as XGBoost and baselines.
  4. **Preliminary Evidence Disclaimer:** Out-of-sample holdout metrics (~53.75% for LightGBM, ~54.17% for XGBoost) provide preliminary empirical evidence of modest signal over majority class (50.00%), but do not constitute proof of a commercial trading edge or profitable market strategy.
- **Consequences:** Provides a fair, reproducible, deterministic second tree-model benchmark with zero test-set leakage.

---

## ADR 48: Walk-Forward Temporal Cross-Validation, Expanding-Window Architecture, and Outcome Embargo Safeguards
- **Status:** Accepted
- **Context:** Single-split chronological holdout evaluations (e.g. Day 17–19) assess model performance on only a single out-of-sample time window. In non-stationary financial markets, performance on a single window is highly susceptible to the specific market regime (e.g., strong trend vs consolidation) present during that window. Standard randomized k-fold cross-validation is forbidden because it shuffles past and future data, causing catastrophic temporal lookahead leakage.
- **Decision:**
  1. **Expanding-Window Chronological Folds:**
     - Implement `generate_walk_forward_splits` and `evaluate_walk_forward` in `app/training/walk_forward.py`.
     - An initial training partition (default 40% of observations, $N_{train\_init} \ge min\_train\_samples$) is established for the first fold.
     - The remaining dataset is partitioned into $K$ contiguous, non-overlapping validation folds ($K=5$ default).
     - Each fold $k$ expands the training window to include all historical observations prior to its validation window.
  2. **Mandatory Outcome Embargo Gap:**
     - Enforce a purged embargo window of at least 1 session ($\ge 1$) immediately preceding each validation fold ($[V_{start} - embargo \dots V_{start})$).
     - Because the next-session return label for observation $t$ materializes at $t+1$, the final training observation's outcome date is guaranteed to fall on or before the embargo boundary and strictly prior to the first validation session ($train\_outcome\_cutoff \le val\_start\_date$).
  3. **Multi-Strategy Evaluation Parity:**
     - Every fold evaluates the exact same sample observations across all candidate strategies: Majority-Class, Fixed-Seed Uniform Random ($P=0.5$), Fixed-Seed Stratified Random ($P=train\_prior$, fitted strictly on each fold's $y_{train}$), Day 17 XGBoost, and Day 19 LightGBM.
     - Model hyperparameters remain completely fixed; zero hyperparameter tuning or post-hoc threshold selection is performed on validation data.
  4. **Dual Aggregation Protocol (Macro + Pooled Micro):**
     - *Macro-Averaging:* Compute unweighted mean and sample standard deviation with Bessel correction ($ddof=1$) across folds for Accuracy, Precision, Recall, and F1.
     - *Micro-Pooled Aggregation:* Sum confusion matrices across all folds ($\sum TN, \sum FP, \sum FN, \sum TP$) across all validation observations (720 sessions across 5 folds) to calculate aggregate out-of-sample performance.
  5. **Fault Tolerance & Explicit Degradation:**
     - If a fold training set contains only a single class ($len(unique(y)) < 2$) or is undersized, the evaluation records an explicit `SKIPPED_SINGLE_CLASS` status with reason, preventing silent crashes or fabricated metrics.
  6. **Scientific Humility & Disclaimer:**
     - Document that walk-forward cross-validation performance (~50.7% XGBoost, ~51.3% LightGBM, ~52.4% Majority Class across 5 folds on BHARTIARTL) reflects realistic regime shifts and confirms that a single holdout score cannot be extrapolated as a permanent commercial trading edge.
- **Consequences:** Eliminates regime-specific overfitting, prevents temporal data leakage across fold boundaries, and establishes an auditable, multi-cycle cross-validation standard for all future ML models.


