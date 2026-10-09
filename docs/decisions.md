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

