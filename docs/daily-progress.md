# Daily Development Progress Journal

This journal documents the step-by-step development history of the Indian Stock Market Prediction System. Each development day captures explicit deliverables, validation steps, and commit history.

---

## Day 1 - Project Foundation

### Goal
Establish the foundational infrastructure, architecture documentation, environment, testing framework, and Git repository setup for the Indian Stock Market Prediction System without implementing any predictive, mock, or downstream features prematurely.

### Work Completed
1. **Workspace Inspection & Preservation:** Inspected root workspace; verified and preserved existing Ponytail rules and agent customizations (`AGENTS.md`, `GEMINI.md`, `.agents/`).
2. **Directory Architecture:** Created clean modular project layout:
   - `app/` domain packages (`api/`, `core/`, `database/`, `market/`, `news/`, `nlp/`, `prediction/`, `training/`, `history/`).
   - `data/` directories (`raw/`, `processed/`, `cache/`) with `.gitkeep` placeholders.
   - `models/` model artifact directory with `.gitkeep`.
   - `docs/` technical documentation directory.
   - `tests/` automated test suite directory.
3. **Environment & Dependency Management:**
   - Initialized Python virtual environment (`.venv`) on Python 3.14.7.
   - Created minimal `requirements.txt` containing only baseline dependencies (`python-dotenv`, `pytest`).
   - Created comprehensive `.gitignore` preventing commits of virtual environments, secrets, caches, logs, and untracked datasets.
4. **Core Application Entry Point:**
   - Created `app/__init__.py` with package version `0.1.0`.
   - Created `main.py` entry point verifying application foundation readiness without fake/mock data.
5. **Testing Suite:**
   - Created `tests/test_foundation.py` with 4 test cases verifying package imports, clean execution of `main.py`, directory existence, and the strict absence of forbidden mock market data.
6. **Documentation Suite:**
   - `README.md`: Project objectives, workflow, philosophy, setup instructions, and validation steps.
   - `docs/architecture.md`: Detailed end-to-end multi-layer architecture and data-isolation principles.
   - `docs/roadmap.md`: 16-phase sequential development plan.
   - `docs/decisions.md`: 13 Architectural Decision Records (ADRs).
   - `docs/data-sources.md`: Data sources plan classified as `PLANNED / TO BE VERIFIED`.
   - `docs/daily-progress.md`: Daily audit log and development journal.
7. **Quality & Minimalism Review:**
   - Verified compliance with Ponytail minimalism and YAGNI standards (no unnecessary abstractions, no premature dependencies).
   - Confirmed no secrets, tokens, or mock financial logic exist in the repository.

### Validation
- **Application Execution:**
  ```powershell
  & .\.venv\Scripts\python.exe main.py
  ```
  *Result:* Exited with code `0`. Output: `Stock Market Prediction System` / `Day 1 environment ready`.
- **Test Suite:**
  ```powershell
  & .\.venv\Scripts\pytest.exe -v
  ```
  *Result:* 4 passed in 0.02s (`test_core_package_import`, `test_main_execution`, `test_required_project_directories_exist`, `test_no_forbidden_day1_mock_data`).

### Git Commit
- **Foundation Commit Message:** `chore: initialize project foundation`
- **Hash:** `6f82f71`
- **Branch:** `main`

### GitHub Setup & Push Verification
- **Repository:** `naiya555/stock-market-prediction-system` (Public)
- **URL:** `https://github.com/naiya555/stock-market-prediction-system`
- **Remote:** `origin` -> `https://github.com/naiya555/stock-market-prediction-system.git`
- **Tracking Branch:** `origin/main`
- **Push Status:** SUCCESS (`git push -u origin main` completed with status 0)
- **Remote Verification:** Verified via GitHub API/MCP:
  - Repository created and accessible.
  - Branch `main` points to commit `6f82f71`.
  - Project tree and `README.md` verified on remote.

### Next Step (Day 2 Starting Point)
Configure application environment configurations, core settings, logging primitives, and data schema contracts in `app/core/` to prepare for Phase 2 historical market data integration.

---

## Day 2 - Core Application Foundation

### Goal
Build the core application foundation required prior to historical market data integration:
1. Environment-driven application configuration layer.
2. Centralized structured logging foundation.
3. Canonical market-data schema contracts with domain and point-in-time validation.

### Work Completed
1. **Application Configuration (`app/core/config.py`):**
   - Implemented immutable `Settings` dataclass reading safe defaults and environment variable overrides via `python-dotenv`.
   - Defined paths (`base_dir`, `data_dir`, `model_dir`), runtime environments, logging level, and timezone (`Asia/Kolkata`).
   - Created cached singleton retrieval helper `get_settings()`.
   - Created `.env.example` template with explicit guidance prohibiting secret commits.
2. **Centralized Logging (`app/core/logging_config.py`):**
   - Implemented standardized structured logging format (`timestamp | level | logger | message`).
   - Configured root handler with dynamic log-level support and standard output stream.
   - Implemented `get_logger(name)` for namespaced logging across all current and future modules.
3. **Canonical Data Schema Contracts (`app/core/schemas.py`):**
   - Defined immutable `MarketOHLCV` contract enforcing explicit point-in-time timestamps, non-empty sources, positive prices, non-negative volume, and physical bounds (`high >= max(open, close)`, `low <= min(open, close)`).
   - Defined immutable `MarketQuote` contract for real-time/latest price quotes.
   - Defined `DataSourceMetadata` contract for data provenance tracking.
   - Defined explicit `ValidationError` exception for fast-failure boundary checking.
4. **Core Package Exports (`app/core/__init__.py`):**
   - Cleanly exported `Settings`, `get_settings`, `setup_logging`, `get_logger`, `MarketOHLCV`, `MarketQuote`, `DataSourceMetadata`, `ValidationError`.
5. **Application Entry Point Update (`main.py`):**
   - Integrated `get_settings()` and `setup_logging()` to verify end-to-end initialization on startup.
6. **Comprehensive Unit Testing (`tests/test_core.py`):**
   - Added 16 new test cases covering default settings, environment overrides, singleton caching, logging setup, valid and invalid OHLCV bars, invalid quote rejection, and metadata provenance.
   - Verified regression: all 4 Day 1 foundation tests continue to pass (20 total tests passing).
7. **Documentation Updates:**
   - Updated `README.md` reflecting Day 2 status and current capabilities.
   - Updated `docs/architecture.md` with Section 4 detailing core primitives.
   - Updated `docs/decisions.md` with ADRs 14 through 18.

### Validation
- **Application Startup Execution:**
  ```powershell
  & .\.venv\Scripts\python.exe main.py
  ```
  *Result:* Exited code 0. Logged initialization and displayed readiness messages.
- **Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\pytest.exe -v
  ```
  *Result:* 20 passed in 0.05s.

### Review
- **Ponytail / Minimalism Review:** Verified standard library usage (`dataclasses`, `logging`, `pathlib`, `datetime`). Zero unnecessary third-party packages or speculative abstractions added.
- **Security Check:** Verified no credentials or secrets exist in configuration, source, or test fixtures. `.env` remains strictly ignored by `.gitignore`.

### Git Commit
- **Commit Message:** `feat: add core application foundation`

### GitHub
- **Push Status:** PUSHED to `origin/main`

### Next Step (Day 3 Starting Point)
Begin Phase 2: Historical market data architecture, provider adapter interfaces, and point-in-time data ingestion pipelines for Indian equities.

---

## Day 3 - Market Data Schema + Source Investigation

### Goal
Define the market-data layer architecture, provider contracts, and source requirements before building the historical data collector on Day 4:
1. Review and preserve canonical core schemas (`MarketOHLCV`, `MarketQuote`, `DataSourceMetadata` from Day 2).
2. Create minimal market-data module (`app/market/` and `app/market/providers/`).
3. Define minimal historical provider abstraction (`BaseMarketDataProvider`).
4. Investigate and evaluate realistic Indian equity market data sources.
5. Select and justify the candidate provider for Day 4 without implementing live collection today.
6. Designate initial stock target (`BHARTIARTL`) without downloading or mocking data.
7. Add deterministic contract tests without external API dependencies.

### Source Investigation
Investigated 5 candidate sources for Indian equities (NSE/BSE):
1. **Yahoo Finance (`yfinance` / Yahoo Query API)**:
   - Status: `PLANNED / TO BE VERIFIED`
   - Granularity: Daily (multi-year), intraday (limited).
   - Auth/Cost: Free community access, no API key, internal session cookie/crumb.
   - Suitability: Primary candidate for Day 4 development prototype.
2. **NSE Official Bhavcopy (National Stock Exchange of India)**:
   - Status: `TO BE VERIFIED`
   - Granularity: Daily (1D) EOD settlement reports with delivery volume.
   - Auth/Cost: Free statutory public archive, automated requests need session headers and navigate anti-bot protections.
   - Suitability: Authoritative secondary benchmark for official settlement data.
3. **Alpha Vantage**:
   - Status: `NOT SELECTED`
   - Rationale: Free tier limit (25 calls/day) is insufficient; patchy and inconsistent coverage for Indian equities.
4. **Indian Broker APIs (Zerodha Kite Connect, Upstox, Angel One)**:
   - Status: `PLANNED` (Phase 14 Live Data Pipeline)
   - Rationale: Production-grade real-time and historical ticks, but requires KYC brokerage account, API subscription fees (Kite), and daily TOTP authentication.
5. **Google Finance / HTML Scraping**:
   - Status: `NOT SELECTED`
   - Rationale: No supported historical API, violates Terms of Service, fragile structure.

### Decisions
1. **ADR 19: Centralized Canonical Schemas Preserved Without Duplication**: `MarketOHLCV`, `MarketQuote`, and `DataSourceMetadata` remain exclusively defined in `app/core/schemas.py`. `app/market/` re-exports them without creating duplicate types.
2. **ADR 20: Separation of Historical Collection from Minimal Provider Abstraction**: Created `BaseMarketDataProvider` ABC with `fetch_historical_ohlcv(symbol, start_date, end_date, interval)` and `name`. Strict boundary: no downloader or scraper implemented on Day 3.
3. **ADR 21: Verification-First Stance on External Market Data Sources**: No provider assumed to be free or public without verification. Shortlisted `yfinance` as `PLANNED / TO BE VERIFIED` for Day 4. Initial target stock set to `BHARTIARTL`.
4. **ADR 22: Mandatory Point-in-Time Temporal Integrity and Provenance Guarantees**: Strict observation timestamps and provider source identity required. Information timestamped after $T_{pred}$ is strictly excluded.

### Work Completed
1. **Market Data Module Foundation (`app/market/`):**
   - Created `app/market/providers/base.py` containing `BaseMarketDataProvider` ABC.
   - Created `app/market/providers/__init__.py` cleanly exposing `BaseMarketDataProvider`.
   - Created `app/market/__init__.py` exposing `BaseMarketDataProvider` alongside canonical contracts (`MarketOHLCV`, `MarketQuote`, `DataSourceMetadata`).
2. **Deterministic Contract Unit Tests (`tests/test_market.py`):**
   - Implemented 6 deterministic tests verifying clean module imports, canonical schema reference identity, abstract class enforcement, subclass contract compliance, and fast-failure domain validation.
   - Total test suite expanded from 20 to 26 passing tests with zero external API calls.
3. **Application Entry Point Update (`main.py`):**
   - Added Day 3 market data foundation readiness status check.
4. **Comprehensive Documentation Updates:**
   - Updated `README.md` to reflect Day 3 completion.
   - Updated `docs/architecture.md` with Section 4.4 detailing market data flow.
   - Updated `docs/data-sources.md` with Section 11 detailing source evaluation matrix, `BHARTIARTL` initial target, and Day 4 provider decision.
   - Updated `docs/decisions.md` with ADRs 19 through 22.

### Validation
- **Application Startup Execution:**
  ```powershell
  & .\.venv\Scripts\python.exe main.py
  ```
  *Result:* Exited code 0. Logged initialization and displayed readiness messages for Days 1, 2, and 3.
- **Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\pytest.exe -v
  ```
  *Result:* 26 passed in 0.06s.

### Review
- **Ponytail / Minimalism Review:** Standard library only (`abc`, `datetime`, `typing`). Zero speculative abstractions, factories, or premature dependencies added to `requirements.txt`.
- **Strict Boundary Review:** Confirmed zero collectors, zero downloaders, zero mock data, zero indicators, zero ML, zero DB, and zero frontend implemented.

### Git Commit
- **Commit Message:** `feat: add market data foundation and source investigation`

### GitHub
- **Push Status:** PUSHED to `origin/main`

### Next Step
Day 4: Historical Data Collector — verify `yfinance` connectivity for `BHARTIARTL.NS`, build concrete collector adapter implementing `BaseMarketDataProvider`, and capture verified historical daily OHLCV bars into canonical `MarketOHLCV` structures.

---

## Day 4 - Historical Data Collector

### Goal
Build the first real historical market-data collector for Indian equities:
1. Empirically verify the shortlisted provider (`yfinance`) for target equity `BHARTIARTL.NS`.
2. Implement the concrete `YFinanceProvider` adapter adhering to `BaseMarketDataProvider`.
3. Normalize provider output into canonical `MarketOHLCV` records.
4. Enforce strict raw unadjusted price convention (`auto_adjust=False`) and observation timestamp fidelity.
5. Create comprehensive deterministic offline unit tests and an isolated live verification script.
6. Verify live historical collection for `BHARTIARTL.NS` with zero fake data.

### Provider Verification
- **Target Equity:** `BHARTIARTL` (queried as `BHARTIARTL.NS`).
- **Package:** `yfinance` 1.7.0 installed cleanly into Python 3.14 virtual environment.
- **Empirical Check:** Executed live historical retrieval for `BHARTIARTL.NS` (2026-09-01 to 2026-09-08).
- **Result:** Successfully returned 6 daily trading bars with columns `['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Dividends', 'Stock Splits']`.
- **Timestamp Fidelity:** `pandas.DatetimeIndex` localized to `Asia/Kolkata` (`+05:30`), aligning precisely with Indian market trading sessions.
- **Price Convention:** Raw unadjusted prices (`auto_adjust=False`) selected to preserve authentic traded levels and physical candle relationships.
- **Quirk Handled:** In Yahoo Finance's API, the `end` date parameter is exclusive (`[start, end)`). The adapter resolves this by querying `end_date + timedelta(days=1)` and filtering to the inclusive observation window.
- **Verification Status:** `VERIFIED`.

### Implementation
1. **Concrete Provider Adapter (`app/market/providers/yfinance_provider.py`):**
   - Implements `BaseMarketDataProvider` contract.
   - Resolves bare Indian symbols (`BHARTIARTL` -> `BHARTIARTL.NS`).
   - Fetches daily OHLCV bars using `yf.Ticker.history(..., auto_adjust=False)`.
   - Isolates Pandas DataFrames within the adapter boundary.
   - Maps each row to immutable, canonical `MarketOHLCV` dataclasses.
   - Validates physical candle bounds and positive prices at ingestion.
2. **Provider Package Exports:**
   - Exported `YFinanceProvider` in `app/market/providers/__init__.py` and `app/market/__init__.py`.
3. **Application Entry Point (`main.py`):**
   - Added Day 4 historical collector readiness check.
4. **Dependencies (`requirements.txt`):**
   - Added `yfinance>=1.7.0`.

### Real Data Verification
Executed isolated verification script (`scripts/verify_collector.py`):
```powershell
& .\.venv\Scripts\python.exe scripts/verify_collector.py
```
- Query: `BHARTIARTL` from 2026-09-01 to 2026-09-08 (6 trading sessions, 1d interval).
- Result: 6 canonical `MarketOHLCV` bars retrieved.
- First Bar (2026-09-01): Open 1852.00, High 1877.20, Low 1848.50, Close 1877.20, Volume 9,900,740.
- Last Bar (2026-09-08): Open 1846.20, High 1848.80, Low 1829.00, Close 1844.00, Volume 4,169,706.
- 100% of bars passed canonical validation rules.

### Tests
- **Unit Test Suite (`tests/test_yfinance_provider.py`):**
  - Added 9 deterministic offline unit tests mocking `yfinance.Ticker` (testing initialization, symbol resolution, unadjusted price mapping, empty responses, missing columns, network error propagation, NaN filtering, input bounds, and unphysical bar rejection).
- **Full Test Suite Execution:**
  ```powershell
  & .\.venv\Scripts\pytest.exe -v
  ```
  - Total tests: 35 PASSED in 1.00s.
  - Zero external network dependencies in standard test run.

### Review
- **CodeRabbit Finding Addressed:** Corrected documentation consistency issue in `docs/data-sources.md` and verification scripts where the observation window was described as 5 sessions instead of the actual 6 trading sessions (6 daily bars across Sep 1, 2, 3, 4, 7, 8).
- **Ponytail / Minimalism Review:** Single concrete provider adapter (`YFinanceProvider`), zero premature provider registries, zero ETL frameworks, zero factories, standard library and minimal dependencies only.
- **Strict Boundary Review:** Confirmed zero cleaning pipelines (Day 5), zero returns/volatility (Day 6), zero charts (Day 7), zero technical indicators, zero ML/LLM, zero database.

### Documentation
- Updated `README.md` to Day 4 completion with 35 passing tests.
- Updated `docs/architecture.md` with Section 4.4 detailing ingestion data flow and schedule boundaries.
- Updated `docs/data-sources.md` with Section 12 empirical verification record (corrected to 6 trading sessions / 6 daily bars).
- Updated `docs/decisions.md` with ADRs 23 through 25.

### Git Commit
- **Commit Message:** `feat: implement historical market data collector`
- **Fix Commit Message:** `fix: correct historical verification session count`

### GitHub
- **Push Status:** PUSHED to `origin/main`

### Issues
- CodeRabbit finding: "Fix the session count in the verification record" — Resolved (corrected documentation and script comment from 5 to 6 trading sessions matching the 6 retrieved bars).

### Next Step
Day 5: Data Cleaning — implement missing-value detection, duplicate timestamp resolution, price anomaly filtering, and sequential date/time normalization pipelines.

---

## Day 5 - Data Cleaning

### Goal
Build the deterministic data-cleaning layer for the historical market data produced by the Day 4 collector:
1. Define explicit cleaning rules for missing values, duplicate timestamps, incorrect values, sorting, and timezone normalization.
2. Implement non-destructive cleaning pipeline in `app/market/cleaner.py`.
3. Provide auditable `CleaningSummary` tracking input, output, rejected, missing, and duplicate counts.
4. Add comprehensive unit tests covering all cleaning edge cases with zero external dependencies.
5. Verify that real historical market data collected from Day 4 flows cleanly through the cleaner.

### Cleaning Rules
1. **Missing Values:** Records with missing/null/blank/NaN prices, volume, symbol, or source are quarantined/rejected. Zero blind forward-filling or interpolation is permitted.
2. **Duplicate Timestamps:**
   - Identical duplicates (same symbol, timestamp, OHLC, volume) are safely collapsed into 1 canonical bar.
   - Conflicting duplicates (different prices/volume for the same symbol and timestamp) are quarantined/rejected to prevent fabricating artificial market reality.
3. **Invalid Values:** Non-positive prices (`<= 0`), negative volume (`< 0`), and violated physical candle geometry (`High < Low`, `High < max(Open, Close)`, `Low > min(Open, Close)`) are rejected.
4. **Timezone Normalization:** Standardized to `Asia/Kolkata`. Naive daily timestamps are interpreted as `Asia/Kolkata` sessions preserving calendar dates; aware timestamps are localized via timezone conversion.
5. **Chronological Sorting:** All output records are strictly sorted by `(symbol, timestamp)` ascending.
6. **Non-Destructive Preservation:** Raw input records remain untouched; cleaned records are newly instantiated.

### Implementation
1. **Data Cleaning Module (`app/market/cleaner.py`):**
   - Implemented `clean_market_data(records, target_timezone="Asia/Kolkata") -> CleaningResult`.
   - Defined immutable dataclasses `CleaningSummary` and `CleaningResult`.
   - Exposed `clean_market_data`, `CleaningResult`, and `CleaningSummary` via `app/market/__init__.py`.
2. **Application Entry Point Update (`main.py`):**
   - Added Day 5 data cleaning readiness check.
3. **Real-Data Verification Script (`scripts/verify_cleaner.py`):**
   - Validates end-to-end integration: `YFinanceProvider` -> `clean_market_data` -> verified `MarketOHLCV` output.

### Real Data Verification
Executed `scripts/verify_cleaner.py`:
```powershell
& .\.venv\Scripts\python.exe scripts/verify_cleaner.py
```
- Input: 6 raw canonical bars retrieved from `YFinanceProvider` for `BHARTIARTL.NS` (2026-09-01 to 2026-09-08).
- Audit Metrics:
  - Input Count: 6
  - Output Count: 6
  - Missing Records: 0
  - Invalid Records: 0
  - Identical Duplicates: 0
  - Conflicting Duplicates: 0
  - Total Rejected: 0
  - Chronologically Sorted: True
- Result: 100% of real market bars passed cleaning without loss or distortion.

### Tests
- **Unit Test Suite (`tests/test_cleaning.py`):**
  - Added 9 deterministic offline unit tests covering:
    - Preservation of clean data
    - Empty input handling
    - Detection of missing values (null, blank, NaN)
    - Rejection of invalid/impossible OHLCV and negative volume
    - Identical duplicate collapse
    - Conflicting duplicate quarantine
    - Chronological sorting
    - Timezone and calendar session preservation
    - CleaningSummary serialization and metrics
- **Full Test Suite Execution:**
  ```powershell
  & .\.venv\Scripts\pytest.exe -v
  ```
  - Total tests: 44 PASSED in 0.85s.
  - Zero external network dependencies.

### Review
- **CodeRabbit Finding Addressed:** Resolved issue on `app/market/cleaner.py` by removing the unused `timezone` import from `datetime` without altering any cleaning logic.
- **Ponytail / Minimalism Review:** Clean functional pipeline with standard library collections and dataclasses (`defaultdict`, `ZoneInfo`, `dataclass`). Zero bulky ETL frameworks, zero unnecessary abstractions.
- **Strict Boundary Review:** Confirmed zero returns/volatility calculations (Day 6), zero charts (Day 7), zero technical indicators, zero ML/LLM, zero database.

### Documentation
- Updated `README.md` to Day 5 completion with 44 passing tests.
- Updated `docs/architecture.md` with Section 4.4 showing data cleaning pipeline and schedule boundaries.
- Updated `docs/decisions.md` with ADRs 26 through 29.
- Updated `docs/daily-progress.md` with Day 5 audit log and CodeRabbit review resolution.

### Git Commit
- **Feature Commit:** `6a0a7d1` — `feat: add historical market data cleaning pipeline`
- **Review Fix Commit:** `fix: remove unused timezone import`

### GitHub
- **Push Status:** PUSHED to `origin/main`

### Issues
- CodeRabbit finding on `cleaner.py` (unused `timezone` import) — Resolved.

### Next Step
Day 6: Returns + Volatility — implement continuous log returns, simple percentage returns, rolling realized volatility, and statistical spread features.

---

## Day 6 - Returns + Volatility

### Goal
Build the point-in-time return and volatility feature layer on top of cleaned historical market data (`MarketOHLCV`):
1. Daily simple percentage returns.
2. Multi-session rolling returns (3-session and 5-session windows).
3. Sample standard deviation ($ddof=1$).
4. Rolling realized volatility (raw daily stdev and annualized volatility with factor $\sqrt{252}$).
5. Point-in-time temporal integrity and zero lookahead data leakage.
6. Safe division-by-zero handling.
7. Validation and unit testing on mathematical and time-series edge cases.
8. Real-data verification on cleaned `BHARTIARTL.NS` historical bars.

### Return Convention
- **Daily simple percentage return:** $R_t = \frac{P_t}{P_{t-1}} - 1$.
- **First observation:** Explicitly yields `None` (unavailable); zero artificial 0% fabrication or forward-filling.
- **Division-by-zero safety:** Non-positive prior prices ($P_{t-1} \le 0$) safely yield `None` rather than generating infinity or raising an exception.
- **Consistent price basis:** Uses raw unadjusted close prices from canonical `MarketOHLCV` (aligned with ADR 24).
- **Rolling returns:** Multi-session cumulative return $R_{t, w} = \frac{P_t}{P_{t-w}} - 1$ over configurable session windows (default 3-session and 5-session). Points with $t < w$ return `None`. Point-in-time calculation with zero future observations.

### Volatility Convention
- **Sample standard deviation:** Sample standard deviation with Bessel correction ($ddof=1$) on valid return series: $\sigma = \sqrt{\frac{1}{N - 1} \sum (R_i - \bar{R})^2}$.
- **Rolling realized volatility:** Computed across rolling windows of daily returns (default 5-session window). Requires $w$ valid returns in the window. If any value is `None` (including initial observations), rolling volatility returns `None`.
- **Primary metric:** Raw daily return standard deviation (`volatility_5d`).
- **Annualized volatility:** Explicitly scaled via factor $\sqrt{252}$ (`annualized_volatility_5d`) reflecting 252 annual trading sessions in Indian markets (NSE/BSE).

### Implementation
1. **Returns & Volatility Feature Engine (`app/market/returns.py`):**
   - Implemented `calculate_daily_returns(prices) -> List[Optional[float]]`.
   - Implemented `calculate_rolling_returns(prices, window) -> List[Optional[float]]`.
   - Implemented `calculate_standard_deviation(values, ddof=1) -> Optional[float]`.
   - Implemented `calculate_rolling_volatility(daily_returns, window, ddof=1, annualized=False, trading_days=252) -> List[Optional[float]]`.
   - Implemented `compute_market_returns(records, rolling_return_windows=(3, 5), volatility_windows=(5,), trading_days=252) -> List[ReturnFeatures]`.
   - Defined immutable dataclass `ReturnFeatures` with `.to_dict()` and property accessors (`rolling_return_3d`, `rolling_return_5d`, `volatility_5d`, `annualized_volatility_5d`).
2. **Market Package Exports (`app/market/__init__.py`):**
   - Cleanly exported `ReturnFeatures`, `compute_market_returns`, and calculation functions.
3. **Application Entry Point Update (`main.py`):**
   - Added Day 6 readiness confirmation check.
4. **Real-Data Verification Script (`scripts/verify_returns.py`):**
   - Validates end-to-end integration: `YFinanceProvider` -> `clean_market_data` -> `compute_market_returns`.

### Real Data Verification
Executed `scripts/verify_returns.py` on real `BHARTIARTL.NS` historical bars:
- Input Clean Record Count: 6 bars (2026-09-01 to 2026-09-08)
- Daily Returns Produced: 5 valid daily returns (first observation strictly `None`)
- 3-Session Rolling Returns: 3 available
- 5-Session Rolling Returns: 1 available (at final session 2026-09-08: -1.7686%)
- 5-Session Rolling Volatility: 1 available (at final session 2026-09-08: 0.009157 raw daily stdev)
- Timestamp Alignment: 100% (6/6 records matched 1:1 with input timestamps and prices)
- Chronological Sorting: Verified ascending order across all sessions

### Tests
- **Unit Test Suite (`tests/test_returns.py`):**
  - Added 21 deterministic unit tests covering daily returns (positive, negative, zero, first observation, chronological order), rolling returns (known windows, insufficient history, no future leakage), standard deviation (known calculation, zero variance, insufficient samples), rolling volatility (correctness, insufficient history, consistent series), and validation edge cases (unsorted input, zero/negative prices, timestamp alignment, empty/single input, multi-symbol separation, property accessors, invalid window arguments).
- **Full Test Suite Execution:**
  - 65 passed in 0.85s (`pytest -v`). Zero external network dependencies.

### Review
- **CodeRabbit Review Remediation:**
  1. *Row width alignment:* Resolved column width mismatch between table headers and data rows in `scripts/verify_returns.py` (standardized widths: 12, 12, 14, 14, 14, 14).
  2. *Verification assertion replacement:* Replaced `assert` statements in `scripts/verify_returns.py` with explicit conditional validation checks that output descriptive errors to `sys.stderr` and return exit code 1.
  3. *Windows currency encoding robustness:* Configured `sys.stdout.reconfigure(encoding="utf-8")` when available, with dynamic detection and safe `INR` fallback if `₹` cannot be encoded by the terminal stream.
- **Ralph Loop:** Ralph Loop unavailable — manual bounded cycle completed.
- **Ponytail / Minimalism Review:** Pure standard library implementation (`math`, `typing`, `dataclasses`, `collections`, `datetime`). Zero third-party mathematical or ML dependencies added. Zero speculative abstractions.

### Documentation
- Updated `README.md` to Day 6 completion with 65 passing tests.
- Updated `docs/architecture.md` with Section 4.5 detailing the returns & volatility feature pipeline.
- Updated `docs/decisions.md` with ADRs 30 through 33.
- Updated `docs/daily-progress.md` with Day 6 audit log and CodeRabbit remediation details.

### Git Commit
- **Feature Commit:** `25b6cb7` — `feat: add returns and volatility features`
- **Remediation Commit:** `fix: address returns verification review findings`

### GitHub
- PUSHED to `origin/main`

### Issues
- CodeRabbit finding on table row width mismatch — Resolved.
- CodeRabbit finding on `assert` statements in verification script — Resolved.
- Windows console currency symbol encoding — Resolved via dynamic UTF-8 reconfiguration and safe `INR` fallback.

### Next Step
Day 7: First market chart + data pipeline completion — implement price chart, volume chart, initial moving-average visualization, and end-to-end data pipeline completion.

---

## Day 7 - First Market Chart + Data Pipeline Completion

### Goal
Complete the Phase 1/Phase 2 historical market data foundation by building a reusable, unified market-data pipeline and generating publication-quality visual charts for `BHARTIARTL.NS`:
1. Build a unified pipeline connecting the historical collector, data cleaning pipeline, and returns/volatility feature engine without duplicating logic.
2. Implement headless chart generator for historical closing prices and daily percentage returns.
3. Use real collected and cleaned market data only (zero synthetic or fabricated prices).
4. Save charts to ignored output directory `data/processed/charts/` without polluting git tracking.
5. Add deterministic offline unit tests for pipeline orchestration and chart generation (zero external network dependencies).
6. Verify the end-to-end pipeline against real historical market data for `BHARTIARTL.NS`.

### Implementation
1. **Pipeline Orchestrator (`app/market/pipeline.py`):**
   - Implemented `run_market_data_pipeline(symbol, start_date, end_date, provider=None, ...)` orchestrating collector, cleaner, and return/volatility feature computation.
   - Implemented `process_market_data(raw_records, ...)` for deterministic offline pipeline processing.
   - Defined immutable dataclass `MarketDataPipelineResult` maintaining raw records, cleaned records, cleaning summary, and features, with helper serialization methods.
2. **Headless Market Visualizer (`app/market/visualizer.py`):**
   - Configured Matplotlib headless `Agg` backend (`matplotlib.use("Agg")`).
   - Implemented `plot_closing_prices(records, output_path, title=None)`: Line plot with markers, formatted INR y-axis, rotated date formatting, and light gridlines.
   - Implemented `plot_daily_returns(features, output_path, title=None)`: Bar plot with positive (green) and negative (red) returns, percentage y-axis, and dashed zero baseline.
   - Implemented `generate_market_charts(features, output_dir="data/processed/charts", symbol=None)`.
3. **Package Exports (`app/market/__init__.py`):**
   - Cleanly exported `MarketDataPipelineResult`, `process_market_data`, `run_market_data_pipeline`, `plot_closing_prices`, `plot_daily_returns`, `generate_market_charts`.
4. **Real-Data Verification Script (`scripts/verify_pipeline.py`):**
   - Orchestrates end-to-end pipeline and generates real PNG charts in `data/processed/charts/` for `BHARTIARTL.NS`.
5. **Application Entry Point Update (`main.py`):**
   - Added Day 7 readiness confirmation.
6. **Dependencies (`requirements.txt`):**
   - Added `matplotlib>=3.8.0`.

### Real Data Verification
Executed `scripts/verify_pipeline.py` on real `BHARTIARTL.NS` historical bars (2026-09-01 to 2026-09-08):
- Input: 6 raw canonical bars from `YFinanceProvider`
- Cleaning: 6 cleaned bars (0 missing, 0 invalid, 0 rejected)
- Features: 6 feature records (5 daily returns, 3 3-session returns, 1 5-session return, 1 5-session volatility)
- Charts Generated:
  - Closing price chart: `data/processed/charts/bhartiartl_close_price.png` (98,198 bytes)
  - Daily returns chart: `data/processed/charts/bhartiartl_daily_returns.png` (50,641 bytes)
- Verification: Valid PNG signatures confirmed, 0 encoding errors, exit code 0.

### Tests
- **Unit Test Suites (`tests/test_pipeline.py` and `tests/test_visualization.py`):**
  - Added 11 deterministic offline unit tests covering pipeline processing, empty inputs, mock provider orchestration, closing price image generation, daily return bar chart generation, batch chart output, and invalid/empty input handling.
- **Full Test Suite Execution:**
  - 76 passed in 1.78s (`pytest -v`). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit local CLI unavailable. CodeRabbit standards maintained: exact row/header width alignment, explicit validation checks rather than assertions in verification script, and robust currency symbol encoding.
- **Ralph Loop:** Ralph Loop unavailable — manual bounded cycle completed.
- **Ponytail / Minimalism Review:** Minimal orchestration without speculative abstractions; Matplotlib scoped strictly to visualization with headless rendering.

### Documentation
- Updated `README.md` to Day 7 completion with 76 passing tests.
- Updated `docs/architecture.md` with Section 4.6 detailing pipeline orchestration and visualization.
- Updated `docs/decisions.md` with ADR 34.
- Updated `docs/daily-progress.md` with Day 7 log and empirical verification results.

### Git Commit
- `feat: add historical market visualization pipeline`

### GitHub
- PUSHED to `origin/main`

### Issues
- None.

### Next Step
Phase 3: Technical Indicators & Feature Engineering (SMA, EMA, RSI, MACD, Bollinger Bands, ATR).

---

## Day 8 - Technical Indicators: Moving Averages

### Goal
Integrate Simple Moving Average (SMA) and Exponential Moving Average (EMA) calculations into the existing market-feature workflow:
1. Configurable moving-average windows, including 5-session and 10-session windows.
2. Chronological market data using raw unadjusted close price basis.
3. Strict prevention of future-data leakage (point-in-time calculation).
4. Deterministic behavior for insufficient history, missing values, and invalid inputs.
5. Non-destructive pipeline integration preserving raw historical records.
6. Empirical verification against real `BHARTIARTL.NS` historical market data.

### Implementation
1. **Moving Average Technical Indicators (`app/market/indicators.py`):**
   - Implemented `calculate_sma(prices, window)`: Simple Moving Average over configurable positive window $W$ ($SMA_{t} = \frac{1}{W} \sum_{i=0}^{W-1} P_{t-i}$). Returns `None` for early un-warmed sessions ($t < W - 1$) and handles empty or invalid price lists.
   - Implemented `calculate_ema(prices, window)`: Exponential Moving Average using recursive smoothing multiplier $\alpha = \frac{2}{W + 1}$ initialized with seed SMA. Suppresses un-warmed values prior to window $W$ ($t < W - 1$).
   - Implemented `MovingAverageFeatures` dataclass: Encapsulates `symbol`, `timestamp`, `close`, `smas: Dict[int, Optional[float]]`, `emas: Dict[int, Optional[float]]`, with convenience properties (`sma_5`, `sma_10`, `ema_5`, `ema_10`) and `.to_dict()` tabular serialization.
   - Implemented `compute_moving_averages(records, sma_windows=(5, 10), ema_windows=(5, 10))`: Multi-symbol, chronological indicator engine producing aligned feature dataclasses without mutating input bars.
2. **Package Exports (`app/market/__init__.py`):**
   - Cleanly exported `MovingAverageFeatures`, `calculate_sma`, `calculate_ema`, `compute_moving_averages`.
3. **Pipeline Orchestrator Integration (`app/market/pipeline.py`):**
   - Extended `MarketDataPipelineResult` with `indicators: List[MovingAverageFeatures]` and `to_indicator_dicts()` serialization.
   - Updated `process_market_data()` and `run_market_data_pipeline()` to orchestrate provider collection, cleaning, return/volatility feature computation, and moving average calculation in a unified flow.
4. **Dependencies (`requirements.txt`):**
   - Added `pandas>=2.0.0` for technical indicators and rolling series support.
5. **Real-Data Verification Script (`scripts/verify_indicators.py`):**
   - End-to-end verification script executing `run_market_data_pipeline` on `BHARTIARTL.NS` (2026-09-01 to 2026-09-08).
   - Validates chronological ordering, point-in-time boundaries, mathematical correctness, window warmup, and insufficient history handling.
   - Outputs an aligned table with matched column widths and Windows UTF-8 / currency safe encoding.
6. **Application Entry Point Update (`main.py`):**
   - Added `print("Day 8 moving averages ready")`.

### Indicator Definitions & Specifications
- **Price Basis:** Raw unadjusted close price (`close` attribute from `MarketOHLCV`).
- **Configured Windows:** Default 5-session (`sma_5`, `ema_5`) and 10-session (`sma_10`, `ema_10`) windows; extensible to any positive integer window.
- **Insufficient History & Missing Data Policy:**
  - For $t < W - 1$, returns strictly `None`. Zero synthetic padding or partial-window distortion.
  - When total available sessions $< W$ (e.g. 6 sessions available for a 10-session window), all values for window $W$ evaluate to `None`.
  - Empty or invalid inputs (e.g., non-positive prices) return empty lists or `None` without crashing.
- **Future-Data Leakage Prevention:**
  - Calculation at session $t$ strictly indexes prices up to $t$.
  - Unit tests verify that altering future prices has zero impact on indicators at prior sessions.

### Real Data Verification
Executed `scripts/verify_indicators.py` on real `BHARTIARTL.NS` historical bars (2026-09-01 to 2026-09-08):
- Input: 6 raw canonical bars collected via `YFinanceProvider`
- Cleaning: 6 cleaned bars (0 missing, 0 invalid, 0 rejected)
- Features: 6 feature records + 6 moving average indicator records
- Results Table:
  ```text
  ---------------------------------------------------------------------------------------
  Date         Close (₹)      SMA-5          EMA-5          SMA-10         EMA-10        
  ---------------------------------------------------------------------------------------
  2026-09-01   1877.20        None (<5d)     None (<5d)     None (<10d)    None (<10d)   
  2026-09-02   1862.80        None (<5d)     None (<5d)     None (<10d)    None (<10d)   
  2026-09-03   1869.00        None (<5d)     None (<5d)     None (<10d)    None (<10d)   
  2026-09-04   1840.00        None (<5d)     None (<5d)     None (<10d)    None (<10d)   
  2026-09-07   1854.00        1860.60        1858.56        None (<10d)    None (<10d)   
  2026-09-08   1844.00        1853.96        1853.71        None (<10d)    None (<10d)   
  ---------------------------------------------------------------------------------------
  ```
- Summary Metrics:
  - 1:1 bar alignment: 6/6 records matched
  - SMA-5 available: 2 sessions (sessions 5 and 6)
  - EMA-5 available: 2 sessions (sessions 5 and 6)
  - SMA-10 / EMA-10: 0 available (correctly `None` due to 6 available sessions $< 10$)
  - Verification exit code: 0

### Tests
- **Unit Test Suites (`tests/test_indicators.py` and `tests/test_pipeline.py`):**
  - Added 19 comprehensive unit tests covering:
    - Known mathematical calculations for SMA and EMA against manual floating-point baselines.
    - Window 1 trivial identity.
    - Invalid window parameter validation ($W \le 0$).
    - Empty input handling.
    - Insufficient history / warmup `None` yields.
    - Zero future-data leakage verification.
    - Multi-symbol grouping isolation.
    - Unsorted input handling and automatic chronological sorting.
    - Pipeline integration and dictionary serialization.
- **Full Test Suite Execution:**
  - 95 passed in 4.22s (`pytest -v`). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit CLI is not installed/configured in this environment. CodeRabbit design rules were proactively maintained: exact header/row table width matching, explicit non-assert validation checks in verification scripts with stderr diagnostic output, and safe Windows UTF-8 / currency fallback encoding.
- **Roo Code:** Remains disabled as required.
- **Ponytail / Minimalism Review:** Efficient vectorization via Pandas, minimal footprint, pure functions with point-in-time guarantees, zero speculative abstractions.

### Documentation
- Updated `README.md` to Day 8 status with 95 passing tests.
- Updated `docs/architecture.md` with Section 4.7 detailing moving average technical indicators.
- Updated `docs/decisions.md` with ADR 35 (Moving Average Technical Indicators, Price Basis, and Point-in-Time Integrity).
- Updated `docs/daily-progress.md` with Day 8 implementation, formulas, and verification results.

### Known Limitations & Next Steps
- Current test range (2026-09-01 to 2026-09-08) contains 6 trading sessions, leaving 10-session moving averages un-warmed (`None`). Longer historical windows will naturally populate 10-session, 20-session, 50-session, and 200-session moving averages when multi-month historical data ranges are queried.
- Next scheduled scope (Day 9): Additional technical indicators (RSI, MACD, Bollinger Bands, ATR) building on this foundation.

---

## Day 9 - Expand Historical Data & RSI Technical Indicator

### Goal
1. Investigate and resolve the Day 8 six-record historical data limitation.
2. Enable collection of longer historical periods (targeting 6–12 months of daily OHLCV data).
3. Verify moving averages (SMA-5, EMA-5, SMA-10, EMA-10) with sufficient data.
4. Implement Wilder's Relative Strength Index (RSI) with configurable periods, robust edge-case handling, and zero future leakage.
5. Add unit tests and regression tests for both the 6-record case and expanded history case.
6. Verify against real historical market data for `BHARTIARTL.NS`.

### Investigation & Root Cause of Six-Record Limitation
- **Investigation:** Examined `YFinanceProvider`, `clean_market_data()`, `run_market_data_pipeline()`, and historical verification scripts.
- **Root Cause Verified:**
  The provider (`YFinanceProvider`) and collection logic were fully functional and capable of fetching hundreds of historical bars over multi-year ranges. The 6-record result occurred because verification scripts (`scripts/verify_collector.py`, `scripts/verify_returns.py`, `scripts/verify_pipeline.py`, `scripts/verify_indicators.py`) explicitly hardcoded an 8-calendar-day window:
  `start_dt = datetime(2026, 9, 1)` and `end_dt = datetime(2026, 9, 8)`.
  In that calendar span, there were only 6 NSE trading sessions (Sept 1, 2, 3, 4, 7, 8; Sept 5 and 6 were weekends).
  Because `run_market_data_pipeline()` required mandatory `start_date` and `end_date` parameters, callers lacked an ergonomic mechanism to request standard lookback periods.
- **Implemented Fix:**
  Enhanced `run_market_data_pipeline()` in `app/market/pipeline.py` to support `lookback_days` (defaulting to 180 calendar days / ~6 months, or 365 calendar days / ~12 months) when `start_date` is omitted, while preserving exact explicit date handling when provided.

### Implementation
1. **Relative Strength Index (`calculate_rsi` in `app/market/indicators.py`):**
   - Implemented J. Welles Wilder's smoothing formulation ($\alpha = 1 / W$).
   - Seeded initial averages at $t = period$ via arithmetic mean over the first $period$ price changes ($period + 1$ prices).
   - Applied recursive Wilder smoothing for $t > period$:
     $$AvgGain_t = \frac{AvgGain_{t-1} \times (W - 1) + Gain_t}{W}, \quad AvgLoss_t = \frac{AvgLoss_{t-1} \times (W - 1) + Loss_t}{W}$$
     $$RSI = 100 \times \frac{AvgGain}{AvgGain + AvgLoss}$$
   - Explicit edge-case handling:
     - Flat prices ($AvgGain = 0$ and $AvgLoss = 0$): returns `50.0` (neutral baseline).
     - Pure gains ($AvgLoss = 0$ and $AvgGain > 0$): returns `100.0`.
     - Pure losses ($AvgGain = 0$ and $AvgLoss > 0$): returns `0.0`.
     - Output is bounded strictly in $[0.0, 100.0]$ when defined.
     - Un-warmed sessions ($t < period$): returns `None`.
     - Zero future-data leakage (temporal point-in-time preservation).
   - Documented explicit disclaimer that RSI is a momentum indicator and not a guaranteed price-direction predictor.
2. **Feature Dataclass & Container Updates (`MovingAverageFeatures`):**
   - Added `rsi: Dict[int, Optional[float]] = field(default_factory=dict)` and convenience property `rsi_14`.
   - Updated `.to_dict()` to serialize `rsi_{period}` fields for tabular ML consumption.
3. **Indicator Orchestration (`compute_moving_averages` / `compute_technical_indicators`):**
   - Added `rsi_periods: Sequence[int] = (14,)` parameter to compute multi-period RSI alongside SMAs and EMAs.
   - Defined `compute_technical_indicators = compute_moving_averages` alias.
4. **Pipeline Orchestrator (`app/market/pipeline.py`):**
   - Extended `process_market_data` and `run_market_data_pipeline` with `rsi_periods=(14,)` and `lookback_days`.
5. **Exports (`app/market/__init__.py`):**
   - Exported `calculate_rsi` and `compute_technical_indicators`.
6. **Real-Data Verification Script (`scripts/verify_indicators.py`):**
   - Updated to verify both the expanded 180-day historical range and the 6-record regression fixture.
7. **Application Entry Point Update (`main.py`):**
   - Added `print("Day 9 technical indicators (RSI & expanded history) ready")`.

### Real Data Verification
Executed `scripts/verify_indicators.py` on real `BHARTIARTL.NS` historical data:
- **Part 1: Expanded Historical Range (lookback_days=180, ~6 months):**
  - Date Range: 2026-04-13 to 2026-10-09 (124 sessions)
  - SMA-5 available: 120 / 124 sessions (warmed up at session 5)
  - EMA-5 available: 120 / 124 sessions (warmed up at session 5)
  - SMA-10 available: 115 / 124 sessions (warmed up at session 10)
  - EMA-10 available: 115 / 124 sessions (warmed up at session 10)
  - RSI-14 available: 110 / 124 sessions (warmed up at session 15 / 14 price changes)
  - Latest Observation (2026-10-09): Close=1805.10, SMA-5=1806.80, EMA-5=1802.94, SMA-10=1786.01, EMA-10=1800.50, RSI-14=46.63
- **Part 2: Regression Verification (original 6-session range 2026-09-01 to 2026-09-08):**
  - Bars: 6
  - SMA-5: 2 values
  - SMA-10: 0 values (all `None`)
  - RSI-14: 0 values (all `None`)
- Verification Status: Exit code 0, 1:1 bar alignment, zero encoding errors.

### Tests
- **Unit Test Suite (`tests/test_indicators.py` and `tests/test_pipeline.py`):**
  - Added 12 new automated tests covering:
    - Textbook manual calculation verification (period=3, prices=[100, 102, 101, 104, 103])
    - Standard 14-period RSI on strictly increasing (100.0), decreasing (0.0), and flat (50.0) series
    - Insufficient history / warmup behavior
    - Strict boundedness within $[0.0, 100.0]$
    - Point-in-time invariant (zero future price leakage)
    - Non-positive / invalid price handling
    - MovingAverageFeatures integration with `rsi_14` property and dictionary serialization
    - Regression test for the 6-record case
    - Expanded history test (20 bars verifying sequential warmups)
    - Pipeline execution with `lookback_days`
- **Full Test Suite Execution:**
  - **107 passed in 4.26s** (`pytest -v`). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit local CLI is not available in this environment. Proactively enforced CodeRabbit formatting standards (aligned column widths, explicit non-assert validation checks with exit codes, and safe UTF-8 / currency symbol handling).
- **Roo Code:** Remained disabled.
- **Ponytail / Minimalism Review:** Minimal, clean Wilder smoothing loop, seamless backward compatibility with existing interfaces, zero unnecessary dependencies.

### Documentation
- Updated `README.md` to Day 9 status with 107 passing tests.
- Updated `docs/architecture.md` with Section 4.7 covering technical indicators, momentum oscillators, and milestone updates.
- Updated `docs/decisions.md` with ADR 36 (RSI Smoothing, Edge-Case Handling, and Flexible Historical Lookbacks).
- Updated `docs/daily-progress.md` with Day 9 progress journal.

### Known Limitations & Next Steps
- Historical data lookback is configured by default to 180 days (~6 months / ~124 sessions), which easily satisfies 5, 10, 14, 20, and 50-session indicators. Long-term indicators like 200-day SMA will require passing `lookback_days=365` or greater.
- Next scheduled scope (Day 10): Additional technical indicators (MACD, Bollinger Bands, ATR) and indicator feature matrix assembly.

---

## Day 10: MACD Technical Indicator Implementation & Real-Data Verification

### Goal
Implement Moving Average Convergence Divergence (MACD) technical indicator with standard defaults (12-fast, 26-slow, 9-signal), ensure point-in-time integrity, guarantee the mathematical identity $Histogram = MACD - Signal$, support configurable parameters and error handling, expand unit tests, and empirically verify on real `BHARTIARTL.NS` historical data.

### Pre-Checks
- Current branch: `main`, clean working tree.
- Prior commit: `024373b83879aa6650a8b636bc1739946aad6f9d` ("feat: expand market history and add RSI indicator").
- Existing test baseline verified: 107 passing tests.
- Roo Code remained disabled.

### What Was Built
1. **Generalization of Exponential Moving Average (`calculate_ema` in `app/market/indicators.py`):**
   - Added `allow_negative: bool = False` parameter.
   - Preserves price domain validation ($P > 0$) by default, while allowing oscillator series (such as MACD line, which oscillates around zero and goes negative during downtrends) to be recursively smoothed without treating negative values as corrupt or spamming logger warnings.
   - Refined NaN/None masking to guarantee that unobserved sessions emit `None` rather than carrying forward values.
2. **Moving Average Convergence Divergence (`calculate_macd` in `app/market/indicators.py`):**
   - Default periods: `fast_period=12`, `slow_period=26`, `signal_period=9`.
   - Comprehensive input validation: all periods must be positive integers ($W \ge 1$), and `fast_period < slow_period`. Invalid parameters raise `ValueError` or `TypeError`.
   - Empty input sequence handling: returns empty `MACDSeries`.
   - Mathematical definitions:
     - $EMA_{fast, t} = EMA(prices, window=fast\_period)$
     - $EMA_{slow, t} = EMA(prices, window=slow\_period)$
     - $MACD_t = EMA_{fast, t} - EMA_{slow, t}$
     - $Signal_t = EMA(MACD, window=signal\_period)$
     - $Histogram_t = MACD_t - Signal_t$
   - Warm-up and Insufficient History Policy:
     - Fast EMA warms up at session index $fast - 1$ (index 11 for fast=12).
     - Slow EMA warms up at session index $slow - 1$ (index 25 for slow=26).
     - MACD line requires both fast and slow EMAs, warming up at index $slow - 1$ (index 25 for 12/26). Sessions $t < slow - 1$ return `None`.
     - Signal line requires $signal$ valid MACD observations, warming up at index $(slow - 1) + (signal - 1) = slow + signal - 2$ (index 33, 34th bar, for 12/26/9). Sessions $t < 33$ return `None`.
     - Histogram requires both MACD and Signal, warming up at index 33. Sessions $t < 33$ return `None`.
     - Undefined intermediate values and missing prices return `None` without fabricating numbers.
   - Point-in-time invariant: Calculation at time $t$ uses strictly observations up to and including $t$; changing future prices never affects earlier or current values.
   - Non-predictive disclaimer documented: MACD is a momentum/trend indicator, not a guaranteed predictor of future price direction.
3. **Dedicated Immutable Container (`MACDSeries`):**
   - `@dataclass(frozen=True)` holding `macd: List[Optional[float]]`, `signal: List[Optional[float]]`, `histogram: List[Optional[float]]`.
   - Implements sequence unpacking via `__iter__`: supports `macd, signal, hist = calculate_macd(prices)` as well as attribute access.
4. **Feature Container Integration (`MovingAverageFeatures`):**
   - Added fields `macd: Optional[float] = None`, `macd_signal: Optional[float] = None`, `macd_histogram: Optional[float] = None`.
   - Added convenience properties `macd_line`, `signal_line`, `histogram`.
   - Updated `.to_dict()` to serialize `"macd"`, `"macd_signal"`, `"macd_histogram"`.
5. **Indicator Orchestration (`compute_moving_averages` / `compute_technical_indicators`):**
   - Added `macd_fast: Optional[int] = 12`, `macd_slow: Optional[int] = 26`, `macd_signal: Optional[int] = 9`.
   - Computes MACD per symbol with complete ticker isolation and chronological sorting.
6. **Pipeline Integration (`app/market/pipeline.py`):**
   - Added `macd_fast`, `macd_slow`, `macd_signal` parameters to `process_market_data` and `run_market_data_pipeline`.
7. **Module Exports (`app/market/__init__.py`):**
   - Exported `MACDSeries` and `calculate_macd`.
8. **Real-Data Verification Script (`scripts/verify_indicators.py`):**
   - Updated to verify real `BHARTIARTL.NS` historical data (180 days lookback) and original 6-session regression fixture.

### Real Data Verification
Executed `scripts/verify_indicators.py` on real `BHARTIARTL.NS` data:
- **Part 1: Expanded Historical Range (lookback_days=180, ~6 months):**
  - Date Range: 2026-04-13 to 2026-10-09 (124 sessions)
  - SMA-5 available: 120 / 124 sessions (warmed up at session 5)
  - EMA-5 available: 120 / 124 sessions (warmed up at session 5)
  - SMA-10 available: 115 / 124 sessions (warmed up at session 10)
  - EMA-10 available: 115 / 124 sessions (warmed up at session 10)
  - RSI-14 available: 110 / 124 sessions (warmed up at session 15 / 14 price changes)
  - MACD Line available: 99 / 124 sessions (warmed up at session 26 / index 25)
  - Signal Line available: 91 / 124 sessions (warmed up at session 34 / index 33)
  - Histogram available: 91 / 124 sessions (warmed up at session 34 / index 33)
  - Histogram identity verified: $Histogram == MACD - Signal$ strictly verified within $\pm 10^{-6}$ on every session.
  - Latest Observation (2026-10-09): Close=1805.10, RSI-14=46.63, MACD=-19.92, Signal=-25.39, Histogram=+5.47
- **Part 2: Regression Verification (original 6-session range 2026-09-01 to 2026-09-08):**
  - Bars: 6
  - SMA-5: 2 values
  - SMA-10: 0 values (all `None`)
  - RSI-14: 0 values (all `None`)
  - MACD Line: 0 values (all `None`)
  - Signal Line: 0 values (all `None`)
  - Histogram: 0 values (all `None`)
- Verification Status: Exit code 0, 1:1 bar alignment, zero encoding errors.

### Tests
- **Unit Test Suite (`tests/test_indicators.py` and `tests/test_pipeline.py`):**
  - Added 11 new tests covering:
    - Manual trace verification on small sequence (`fast=2`, `slow=4`, `signal=2`, exact floating-point comparisons)
    - Subtraction identity ($MACD = EMA_{fast} - EMA_{slow}$) and histogram identity ($Histogram = MACD - Signal$)
    - Insufficient history and warm-up policies (20 bars, 26 bars, 34 bars)
    - Parameter validation: $fast \ge slow$, non-positive periods, non-integer types raising errors
    - Empty input handling
    - Point-in-time invariant (future price mutation does not change earlier values)
    - Negative value handling (downtrends where fast < slow producing negative MACD and Signal lines)
    - Invalid price handling (masking affected sessions)
    - Multi-symbol grouping, ticker isolation, and chronological sorting
    - Feature dataclass `.to_dict()` and property serialization
    - Pipeline integration and dictionary serialization
    - Regression tests for 6-record case and expanded 40-record case
- **Full Test Suite Execution:**
  - **118 passed in 4.41s** (`pytest -v`). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit local CLI is not available in this environment. Proactively enforced standards: explicit validation checks with return codes, aligned table format, float tolerance checks, and safe currency encoding.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Reused existing `calculate_ema` with minimal single flag (`allow_negative=True`) instead of duplicating EMA logic; zero added dependencies; shortest working diff.

### Documentation
- Updated `README.md` to Day 10 status with 118 passing tests.
- Updated `docs/architecture.md` with Section 4.7 covering MACD formulation and Day 10 milestone completion.
- Updated `docs/decisions.md` with ADR 37 (MACD indicator architecture, recursive signal smoothing, and point-in-time integrity).
- Updated `docs/daily-progress.md` with Day 10 journal.

### Known Limitations & Next Steps
- Current indicator suite includes SMA, EMA, RSI, and MACD. Additional standard technical features (Bollinger Bands, ATR, VWAP) remain for subsequent phases.
- Indicator features are computed per symbol in isolation; cross-sectional features (e.g. index-relative strength) will be implemented in future feature-engineering phases.
- Next roadmap step (Day 11): Additional volatility indicators (Bollinger Bands) or technical feature matrix assembly for machine learning dataset preparation.

---

## Day 11: Bollinger Bands Technical Indicator Implementation & Real-Data Verification

### Goal
Implement Bollinger Bands technical indicator (Middle Band, Upper Band, Lower Band, Band Width, Percent B) with canonical defaults (window=20, multiplier=2.0, population standard deviation $ddof=0$), ensure point-in-time integrity, safe zero-denominator handling for flat series, expand unit tests, update documentation, and empirically verify on real `BHARTIARTL.NS` historical data.

### Pre-Checks
- Current branch: `main`, clean working tree.
- Prior commit: `6c25ec37f8c5fded909a62cd09b2c39d63eb6d8a` ("feat: add MACD technical indicator").
- Existing test baseline verified: 118 passing tests.
- Roo Code remained disabled.

### What Was Built
1. **Bollinger Bands Calculation (`calculate_bollinger_bands` in `app/market/indicators.py`):**
   - Default parameters: `window=20`, `multiplier=2.0` (accepts `num_std` alias), `ddof=0` (canonical population standard deviation).
   - Parameter validation: `window` must be an integer $\ge 1$, `multiplier` must be a positive finite float ($> 0$), `ddof` must satisfy $0 \le ddof < window$.
   - Mathematical definitions:
     - $Middle_t = SMA_{t, W}(prices)$ (20-session rolling arithmetic mean).
     - $\sigma_{t, W} = \sqrt{\frac{1}{W - ddof} \sum_{i=0}^{W-1} (P_{t-i} - Middle_t)^2}$ (rolling standard deviation).
     - $Upper_t = Middle_t + multiplier \times \sigma_{t, W}$.
     - $Lower_t = Middle_t - multiplier \times \sigma_{t, W}$.
     - $BandWidth_t = \frac{Upper_t - Lower_t}{Middle_t}$ when $Middle_t > 0$.
     - $\%B_t = \frac{Close_t - Lower_t}{Upper_t - Lower_t}$ when $Upper_t > Lower_t$.
   - Warm-up & Missing Observation Policy:
     - Early sessions prior to window completion ($t < W - 1$, indices 0..18 for $W=20$) return `None` across all 5 outputs.
     - Sessions with missing, NaN, or non-positive price observations invalidate the rolling window, returning `None`.
     - Zero synthetic values or artificial zero padding are introduced.
   - Zero-Denominator & Flat-Series Safety:
     - When all prices in the window are identical ($Upper == Lower == Middle$), $\sigma = 0.0$.
     - Band Width numerator is 0.0, evaluating safely to `0.0` when $Middle > 0$.
     - %B denominator is $(Upper - Lower) = 0.0$, evaluating safely to `None` without division-by-zero errors.
     - Non-positive middle band ($Middle \le 0$) yields `None` for Band Width.
   - Point-in-time invariant: Calculation at time $t$ strictly uses observations up to and including $t$; changing future prices never leaks into earlier band values.
   - Non-predictive disclaimer: Band touches and squeezes are quantitative descriptive features, never guaranteed buy or sell signals.
2. **Dedicated Immutable Container (`BollingerBandsSeries`):**
   - `@dataclass(frozen=True)` holding `middle`, `upper`, `lower`, `bandwidth`, and `percent_b` lists.
   - Implements sequence protocol `__iter__` to allow 5-tuple sequence unpacking:
     `middle, upper, lower, bw, pb = calculate_bollinger_bands(prices)`
     as well as attribute access and `.band_width` alias.
3. **Feature Container Integration (`MovingAverageFeatures`):**
   - Added fields `bb_middle`, `bb_upper`, `bb_lower`, `bb_bandwidth`, `bb_percent_b`.
   - Added convenience properties `bollinger_middle`, `bollinger_upper`, `bollinger_lower`, `bollinger_bandwidth`, `bollinger_band_width`, `bollinger_percent_b`.
   - Updated `.to_dict()` to export both short keys (`bb_middle`, `bb_upper`, `bb_lower`, `bb_bandwidth`, `bb_percent_b`) and descriptive keys (`bollinger_middle`, etc.) for tabular and ML downstream models.
4. **Indicator Orchestration (`compute_moving_averages` / `compute_technical_indicators`):**
   - Added `bb_window=20`, `bb_multiplier=2.0`, `bb_ddof=0` parameters.
   - Computes Bollinger Bands per ticker with complete multi-symbol isolation and chronological sorting.
5. **Pipeline Integration (`app/market/pipeline.py`):**
   - Added `bb_window`, `bb_multiplier`, `bb_ddof` parameters to `process_market_data` and `run_market_data_pipeline`.
6. **Package Exports (`app/market/__init__.py`):**
   - Exported `BollingerBandsSeries` and `calculate_bollinger_bands`.
7. **Application Entry Point Update (`main.py`):**
   - Added Day 11 status readiness confirmation (`print("Day 11 Bollinger Bands ready")`).
8. **Real-Data Verification Script (`scripts/verify_indicators.py`):**
   - Extended to verify Bollinger Bands warmup, mathematical relationships, table inspection, summary metrics, and 6-session regression fixture.

### Real Data Verification
Executed `scripts/verify_indicators.py` on real `BHARTIARTL.NS` historical data:
- **Part 1: Expanded Historical Range (lookback_days=180, ~6 months):**
  - Raw bars collected: 124
  - Cleaned bars produced: 124
  - Indicator records: 124
  - Date Range: 2026-04-13 to 2026-10-09 (124 trading sessions)
  - SMA-5 available: 120 / 124 sessions
  - EMA-5 available: 120 / 124 sessions
  - SMA-10 available: 115 / 124 sessions
  - EMA-10 available: 115 / 124 sessions
  - RSI-14 available: 110 / 124 sessions
  - MACD Line available: 99 / 124 sessions
  - Signal Line available: 91 / 124 sessions
  - Histogram available: 91 / 124 sessions
  - Bollinger Bands available: 105 / 124 sessions (warmed up at session 20 / index 19)
  - Mathematical identities verified:
    - $Upper \ge Middle \ge Lower$ across all sessions
    - Band symmetry: $(Upper - Middle) == (Middle - Lower)$ within floating-point tolerance
    - Band Width identity: $BandWidth == (Upper - Lower) / Middle$ strictly verified
    - Percent B identity: $\%B == (Close - Lower) / (Upper - Lower)$ strictly verified
  - Latest Observation (2026-10-09): Close=₹1805.10, Middle=₹1810.06, Upper=₹1879.10, Lower=₹1741.03, BandWidth=0.0763, %B=0.4640
- **Part 2: Regression Verification (original 6-session range 2026-09-01 to 2026-09-08):**
  - Clean bars: 6
  - SMA-5: 2 values
  - SMA-10: 0 values (all `None`)
  - RSI-14: 0 values (all `None`)
  - MACD Line: 0 values (all `None`)
  - Signal Line: 0 values (all `None`)
  - Histogram: 0 values (all `None`)
  - Bollinger Bands: 0 values (all `None`, warmup requires 20 bars)
- Verification Status: Exit code 0, 1:1 bar alignment, zero encoding errors.

### Tests
- **Unit Test Suite (`tests/test_indicators.py` and `tests/test_pipeline.py`):**
  - Added 12 new tests covering:
    - Known calculation trace on manual 5-session prices with $W=3, M=2.0$ against exact manual calculations
    - Verification of sample standard deviation ($ddof=1$) convention
    - Configurable window ($W=5$) and multiplier ($M=1.5$)
    - Insufficient history and warm-up policies (20-bar warmup at index 19)
    - Parameter validation: non-positive window, non-positive or non-finite multiplier, $ddof \ge window$, type errors
    - Empty input sequence handling
    - Point-in-time invariant (future price mutation does not change earlier band values)
    - Invalid price handling (masking affected rolling windows with `None`)
    - Zero-denominator and flat series handling (band width evaluates to `0.0`, %B evaluates to `None`)
    - Multi-symbol grouping, ticker isolation, and chronological sorting
    - Feature dataclass `.to_dict()` and property serialization
    - Pipeline integration and dictionary serialization
    - Regression updates for 6-record case and expanded 40-record case
- **Full Test Suite Execution:**
  - **130 passed in 1.44s** (`pytest -v`). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit CLI / review integration is not available in this local environment; noted explicitly. Proactively adhered to strict clean-code principles: type annotations, domain parameter validation, safe division handling, and mathematical identity verification.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Reused existing pandas/numpy rolling and standard deviation calculations, avoided unnecessary helper wrappers, implemented minimal clean diff, zero new external dependencies.

### Documentation
- Updated `README.md` to Day 11 status with 130 passing tests.
- Updated `docs/architecture.md` Section 4.7 covering Bollinger Bands formulation, pipeline integration, and development schedule.
- Updated `docs/decisions.md` with ADR 38 (Bollinger Bands architecture, degrees of freedom convention, zero-denominator safety).
- Updated `docs/daily-progress.md` with Day 11 development log.

### Known Limitations & Next Steps
- Current indicator suite includes SMA, EMA, RSI, MACD, and Bollinger Bands. Additional volatility/volume indicators (e.g., ATR, VWAP) remain for subsequent phases.
- Indicators operate on unadjusted closing prices per individual symbol; volume-weighted and cross-sectional market features are scheduled for subsequent phases.
- Next roadmap step (Day 12): Volume-Weighted Average Price (VWAP) / Average True Range (ATR) or Technical Feature Matrix Assembly.

---

## Day 12: Volatility and Momentum Features — Average True Range (ATR) & Rate of Change (ROC)

### Goal
Implement Average True Range (ATR) with Wilder's smoothing recurrence and documented first-session policy, and Rate of Change (ROC) with configurable lookback and safe division; integrate both indicators into technical indicators, feature containers, and the market pipeline; enforce strict point-in-time integrity, chronological ordering, and ticker isolation; expand test suites and verify against real historical data for `BHARTIARTL.NS`.

### Pre-Checks
- Current branch: `main`, clean working tree at commit `4aeaf812899bddbf18f060d9c2e70d798376b921`.
- Verified 130 passing tests prior to starting.
- Roo Code remained disabled.

### What Was Built
1. **Average True Range (`calculate_true_range` and `calculate_atr` in `app/market/indicators.py`):**
   - True Range formula:
     - First-session initialization policy ($t=0$): $TR_0 = High_0 - Low_0$ when valid.
     - Subsequent sessions ($t > 0$): $TR_t = \max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|)$.
   - Wilder's Smoothing Recurrence:
     - Seeded at index $period - 1$ ($t=13$ for default 14-period) with simple arithmetic mean of first 14 valid True Range values:
       $ATR_{13} = \frac{1}{14} \sum_{i=0}^{13} TR_i$.
     - Recursive formula for $t \ge period$:
       $ATR_t = \frac{(period - 1) \times ATR_{t-1} + TR_t}{period}$.
   - Un-warmed sessions ($t < period - 1$, first 13 sessions for $period=14$) strictly return `None`.
   - Input validation: accepts either `MarketOHLCV` record sequences or individual high, low, close float sequences. Validates physical OHLC candle geometry ($high \ge low$, positive prices).
   - Non-predictive disclaimer documented: ATR measures historical trading volatility range without directional bias; does not predict price direction.
2. **Rate of Change (`calculate_roc` in `app/market/indicators.py`):**
   - Formula: $ROC_{t, n} = ((Close_t / Close_{t-n}) - 1) \times 100$.
   - Configurable positive integer `period` / `lookback` (default: 10 sessions).
   - Un-warmed sessions ($t < n$) strictly return `None`.
   - Division-by-zero & negative price safety: returns `None` if $Close_{t-n} \le 0$ or if price is missing. Flat price series evaluate safely to `0.0`.
   - Relative price momentum indicator measuring percentage rate of change over the lookback window.
3. **Feature Container & Dataclass Integration (`MovingAverageFeatures`):**
   - Added `atr: Dict[int, Optional[float]] = field(default_factory=dict)` and `roc: Dict[int, Optional[float]] = field(default_factory=dict)`.
   - Convenience properties: `atr_14`, `roc_10`.
   - Tabular export: `.to_dict()` serializes `atr_{p}` and `roc_{p}` keys.
4. **Indicator Orchestration (`compute_moving_averages` / `compute_technical_indicators`):**
   - Added `atr_periods: Sequence[int] = (14,)` and `roc_periods: Sequence[int] = (10,)`.
   - Per-symbol isolation and chronological sorting preserved.
5. **Pipeline Integration (`app/market/pipeline.py`):**
   - Added `atr_periods` and `roc_periods` to `process_market_data` and `run_market_data_pipeline`.
6. **Package Exports (`app/market/__init__.py`):**
   - Exported `calculate_true_range`, `calculate_atr`, and `calculate_roc`.
7. **Application Entry Point Update (`main.py`):**
   - Added `print("Day 12 ATR and ROC ready")`.
8. **Real-Data Verification Script (`scripts/verify_indicators.py`):**
   - Updated to verify ATR-14 and ROC-10 on expanded history (123 sessions of `BHARTIARTL.NS`) and the 6-record regression fixture.

### Real Data Verification
Executed `scripts/verify_indicators.py` on real `BHARTIARTL.NS` historical data:
- **Part 1: Expanded Historical Range (lookback_days=180, ~6 months):**
  - Raw bars collected: 123
  - Cleaned bars produced: 123
  - Indicator records: 123
  - Date Range: 2026-04-15 to 2026-10-09 (123 trading sessions)
  - SMA-5 available: 119 / 123 sessions
  - EMA-5 available: 119 / 123 sessions
  - SMA-10 available: 114 / 123 sessions
  - EMA-10 available: 114 / 123 sessions
  - RSI-14 available: 109 / 123 sessions
  - MACD Line available: 98 / 123 sessions
  - Signal Line available: 90 / 123 sessions
  - Histogram available: 90 / 123 sessions
  - Bollinger Bands available: 104 / 123 sessions
  - ATR-14 available: 110 / 123 sessions (warmed up at session 14 / index 13)
  - ROC-10 available: 113 / 123 sessions (warmed up at session 11 / index 10)
  - Mathematical identities verified:
    - ATR-14 Wilder recurrence strictly verified across all valid sessions.
    - ROC-10 formula identity strictly verified against closing prices.
  - Latest Observation (2026-10-09): Close=₹1805.10, High=₹1820.00, Low=₹1801.40, TR=₹18.60, ATR-14=₹33.96, ROC-10=+0.52%
- **Part 2: Regression Verification (original 6-session range 2026-09-01 to 2026-09-08):**
  - Clean bars: 6
  - SMA-5: 2 values
  - SMA-10, RSI-14, MACD, Signal, Hist, BB, ATR-14, ROC-10: all 0 values (strictly `None`)
- Verification Status: Exit code 0, 1:1 bar alignment, zero encoding errors.

### Tests
- Added 15 new unit tests across `tests/test_indicators.py` and `tests/test_pipeline.py`.
- **Full Test Suite Execution:**
  - **145 passed in 1.71s** (`pytest -v`). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit local CLI is not available in this environment; noted explicitly. Proactively enforced standards: explicit validation checks with return codes, aligned table format, float tolerance checks, and safe currency encoding.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Minimalist, pure Python/numpy calculation without heavy dependencies or speculative abstractions.

### Documentation
- Updated `README.md` to Day 12 status with 145 passing tests.
- Updated `docs/architecture.md` Section 4.7 with ATR and ROC formulations and Day 12 completion.
- Updated `docs/decisions.md` with ADR 39.
- Updated `docs/daily-progress.md` with Day 12 development log.

### Known Limitations & Next Steps
- Current indicator suite includes SMA, EMA, RSI, MACD, Bollinger Bands, ATR, and ROC.
- Next scheduled scope (Day 13): Candlestick pattern recognition and feature engineering.

---

## Day 13: Candlestick Feature Engine

### Goal
Implement a reusable, typed candlestick feature engine capturing single-session OHLC geometric properties, wick and body dimensions, ratios, close location, percentage intra-session return, and candle direction; enforce strict point-in-time calculation, safe zero-denominator handling, and physical OHLC geometry validation; integrate into the market data pipeline and test against real data for `BHARTIARTL.NS`.

### Pre-Checks
- Current branch: `main`, clean working tree at commit `111632102865bf16a7953825dd1ae721b1df56e7`.
- Verified 145 passing tests prior to starting.
- Roo Code remained disabled.

### What Was Built
1. **Candlestick Feature Module (`app/market/candlestick.py`):**
   - Implemented immutable `CandlestickFeatures` dataclass encapsulating:
     - `symbol: str`, `timestamp: datetime`
     - `open`, `high`, `low`, `close`
     - `candle_body = Close - Open` (signed)
     - `candle_body_abs = abs(Close - Open)`
     - `candle_range = High - Low`
     - `candle_upper_wick = High - max(Open, Close)`
     - `candle_lower_wick = min(Open, Close) - Low`
     - `candle_body_ratio = candle_body_abs / candle_range` when $Range > 0$ (else `None`)
     - `candle_upper_wick_ratio = candle_upper_wick / candle_range` when $Range > 0$ (else `None`)
     - `candle_lower_wick_ratio = candle_lower_wick / candle_range` when $Range > 0$ (else `None`)
     - `candle_close_location = (Close - Low) / (High - Low)` when $Range > 0$ (else `None`)
     - `candle_body_return_pct = ((Close / Open) - 1.0) * 100.0` when $Open > 0$ (else `None`)
     - `candle_direction`: `"bullish"` if $Close > Open$, `"bearish"` if $Close < Open$, and `"neutral"` if $Close == Open$.
     - Convenience aliases: `.body`, `.body_abs`, `.range`, `.upper_wick`, `.lower_wick`, `.body_ratio`, `.upper_wick_ratio`, `.lower_wick_ratio`, `.close_location`, `.body_return_pct`, `.direction`, `.is_bullish`, `.is_bearish`, `.is_neutral`.
     - `.to_dict()` serializing all features with ISO formatted timestamps.
   - Core functional calculator: `calculate_candlestick_features` supporting either a sequence of `MarketOHLCV` bars or separate parallel float sequences.
   - Single-bar calculator: `calculate_single_candlestick`.
   - Multi-symbol orchestrator: `compute_candlestick_features` providing ticker isolation and chronological sorting by timestamp ascending.
2. **Mathematical Invariants & Geometry Validation:**
   - Physical OHLC geometry validation: verifies $High \ge Low$, $High \ge \max(Open, Close)$, and $Low \le \min(Open, Close)$. Invalid geometry, non-positive prices, or non-finite numbers safely mask all features with `None`.
   - Safe zero-range policy: for flat sessions ($High == Low == Open == Close$), valid zero dimensions ($0.0$) are preserved, body return evaluates to $0.0\%$, candle direction evaluates to `"neutral"`, and undefined ratios evaluate strictly to `None` without division-by-zero crashes.
   - Geometric partition invariant: $Body_{abs} + UpperWick + LowerWick = Range$.
   - Ratio partition invariant: $Ratio_{body} + Ratio_{upper} + Ratio_{lower} = 1.0$ (when $Range > 0$).
   - Strict point-in-time calculation: strictly uses contemporaneous candle prices; zero future observations affect earlier features.
   - Non-predictive disclaimer: candlestick features represent single-bar price action and geometry without asserting predictive signals or guaranteed market direction.
3. **Feature Container & Pipeline Integration:**
   - Extended `MovingAverageFeatures` in `app/market/indicators.py` with candle fields and `.to_dict()` keys.
   - Updated `compute_moving_averages` to compute candlestick features per bar.
   - Extended `MarketDataPipelineResult` in `app/market/pipeline.py` with `candlesticks: List[CandlestickFeatures]`, `.to_candlestick_dicts()`, and `"candlestick_count"` in summary dictionary.
   - Updated `process_market_data` to compute candlestick features and attach to pipeline result.
4. **Package Exports (`app/market/__init__.py`):**
   - Cleanly exported `CandlestickFeatures`, `calculate_candlestick_features`, `calculate_single_candlestick`, `compute_candlestick_features`.
5. **Application Entry Point Update (`main.py`):**
   - Added `print("Day 13 candlestick features ready")`.
6. **Real-Data Verification Script (`scripts/verify_candlestick.py`):**
   - Built dedicated verification script testing real market data, edge cases, zero-range handling, and regression scenarios.

### Real Data Verification
Executed `scripts/verify_candlestick.py` on real `BHARTIARTL` historical market data:
- **Part 1: Expanded Historical Range (lookback_days=180, ~6 months):**
  - Raw bars collected: 124
  - Cleaned bars produced: 124
  - Candlestick records: 124
  - Date Range: 2026-04-15 to 2026-10-12 (124 trading sessions)
  - Chronological ordering & 1:1 alignment: Verified across all 124 sessions.
  - Mathematical identities verified:
    - Geometric partition identity ($Body_{abs} + Upper + Lower == Range$) verified on all 124 bars.
    - Ratio partition identity ($BodyRatio + UpperRatio + LowerRatio == 1.0$) verified on all non-zero bars.
    - Close location within bounds $[0.0, 1.0]$ verified on all bars.
    - Candle directions distribution: 57 Bullish, 67 Bearish, 0 Neutral.
  - Recent Observations:
    - 2026-10-06: O=₹1777.00, H=₹1810.50, L=₹1771.40, C=₹1810.50 -> BULLISH (body=+33.50, range=39.10, body_ratio=0.857, ret=+1.89%)
    - 2026-10-07: O=₹1823.00, H=₹1854.70, L=₹1810.50, C=₹1833.90 -> BULLISH (body=+10.90, range=44.20, body_ratio=0.247, ret=+0.60%)
    - 2026-10-08: O=₹1847.80, H=₹1847.80, L=₹1789.70, C=₹1804.60 -> BEARISH (body=-43.20, range=58.10, body_ratio=0.744, ret=-2.34%)
    - 2026-10-09: O=₹1804.60, H=₹1820.00, L=₹1801.40, C=₹1805.10 -> BULLISH (body=+0.50, range=18.60, body_ratio=0.027, ret=+0.03%)
    - 2026-10-12: O=₹1805.30, H=₹1809.00, L=₹1758.60, C=₹1770.00 -> BEARISH (body=-35.30, range=50.40, body_ratio=0.700, ret=-1.96%)
- **Part 2: Edge-Case, Zero-Range & Geometry Verification:**
  - Zero-range candle safe division: dimensions=0.0, ratios=None, direction='neutral' passed.
  - Invalid geometry (High < Close, Low > Close) correctly masked with None.
  - Non-positive prices correctly masked with None.
- **Part 3: Regression Verification (original 6-session fixture 2026-09-01 to 2026-09-08):**
  - Clean bars: 6, all 6 bars produced valid candlestick features.
  - Verified exit code 0 across both `scripts/verify_candlestick.py` and `scripts/verify_indicators.py`.

### Tests
- Added 13 new unit tests in `tests/test_candlestick.py`.
- **Full Test Suite Execution:**
  - **158 passed in 4.85s** (`pytest -v`). Zero external network dependencies, zero regressions.

### Review
- **CodeRabbit:** CodeRabbit CLI is not installed in the local environment; noted accurately. Clean senior developer review conducted following Ponytail mode: type safety, mathematical invariants, zero code duplication, zero unnecessary dependencies, and safe edge-case division.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Concise pure Python calculations adhering to mathematical definitions, zero bloat, shortest working diff with complete test verification.

### Documentation
- Updated `README.md` to Day 13 status with 158 passing tests.
- Updated `docs/architecture.md` Section 4.8 with Candlestick Feature Engine formulation and schedule boundaries.
- Updated `docs/decisions.md` with ADR 40.
- Updated `docs/daily-progress.md` with Day 13 development log.

### Known Limitations & Next Steps
- Current indicator suite includes SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ROC, and single-bar candlestick features.
- Next scheduled scope (Day 14): Trend and regime detection engine / technical feature matrix assembly.

---

## Day 14 - Trend Engine & Market Structure Analysis

### Goal
Implement a reusable, production-conscious Trend Engine that classifies historical stock price structure into `UPTREND`, `DOWNTREND`, or `SIDEWAYS`:
1. Deterministic swing high and swing low identification from historical OHLC data with configurable flank window ($k$).
2. Explicit swing confirmation timing ($t + k$) strictly preventing look-ahead bias and premature trend claims.
3. Sequential market structure transition labeling: Higher High (`HH`), Higher Low (`HL`), Lower High (`LH`), Lower Low (`LL`).
4. Strict trend classification rules:
   - `UPTREND`: Sufficient Higher Highs and Higher Lows.
   - `DOWNTREND`: Sufficient Lower Highs and Lower Lows.
   - `SIDEWAYS`: Sufficient confirmed swings exist, but directional structure is mixed or consolidating.
   - `None` (`INSUFFICIENT_DATA`): Safe representation when fewer than minimum required confirmed swings exist (never mislabeled as `SIDEWAYS`).
5. Point-in-time rolling series alignment (`compute_rolling_trends`) with zero future leakage.
6. Seamless pipeline integration into `MarketDataPipelineResult` and backward compatibility with all existing indicators.
7. Unit tests and real-data verification on `BHARTIARTL.NS`.

### Implementation
1. **Trend Engine Core Module (`app/market/trend.py`):**
   - Implemented `SwingPoint` dataclass: encapsulates `index`, `timestamp`, `price`, `swing_type` (`HIGH`/`LOW`), `confirmation_index` ($t + k$), `confirmation_timestamp`, `structure_label` (`HH`, `LH`, `HL`, `LL`), and `.to_dict()`.
   - Implemented `TrendAnalysisResult` dataclass: encapsulates `symbol`, `as_of_timestamp`, `classification` (`UPTREND`, `DOWNTREND`, `SIDEWAYS`, or `None`), `status` (`CONFIRMED`, `INSUFFICIENT_DATA`), `swing_window`, `min_swings`, `total_bars`, `swing_highs`, `swing_lows`, `last_high_structure`, `last_low_structure`, boolean properties (`is_uptrend`, `is_downtrend`, `is_sideways`, `is_confirmed`), and `.to_dict()`.
   - Implemented `identify_swings(bars, swing_window=2)`: Deterministic local extreme detector with asymmetric left/right flank comparison preventing duplicate consecutive pivots on flat tops/bottoms.
   - Implemented `label_market_structure(swings)`: Labels consecutive confirmed swings as `HH`/`LH`/`EH` (highs) or `HL`/`LL`/`EL` (lows).
   - Implemented `classify_market_structure(swing_highs, swing_lows, min_swings=2)`: Strictly applies market structure classification matrix with explicit `INSUFFICIENT_DATA` gating.
   - Implemented `analyze_market_trend(bars, swing_window=2, min_swings=2, as_of_index=None)`: Evaluates market structure point-in-time up to cutoff `as_of_index`, strictly filtering out unconfirmed swings.
   - Implemented `compute_rolling_trends(bars, swing_window=2, min_swings=2)`: Generates 1:1 aligned rolling trend classification sequence across all bars with zero lookahead bias.
2. **Pipeline Integration (`app/market/pipeline.py`):**
   - Extended `MarketDataPipelineResult` with `trend: Optional[TrendAnalysisResult] = None`.
   - Updated `process_market_data` and `run_market_data_pipeline` to accept `swing_window=2` and `min_swings=2` and attach trend analysis to pipeline results.
   - Updated pipeline serialization (`.to_dict()`) with `"trend"` details and `"trend_classification"`.
3. **Package Exports (`app/market/__init__.py`):**
   - Cleanly exported `SwingPoint`, `TrendAnalysisResult`, `TrendClassification`, `identify_swings`, `label_market_structure`, `classify_market_structure`, `analyze_market_trend`, `compute_rolling_trends`.
4. **Application Entry Point Update (`main.py`):**
   - Added `print("Day 14 trend engine ready")`.
5. **Real-Data Verification Script (`scripts/verify_trend.py`):**
   - Validates real data acquisition on `BHARTIARTL.NS`, chronological ordering, confirmed swing points, structural transitions, classification rules consistency, absence of lookahead leakage across temporal cutoffs, and rolling alignment.

### Trend Classification Rules & Look-Ahead Bias Safeguards
- **Confirmation Timing Rule:** A swing extreme occurring at bar $t$ requires $k$ subsequent bars to confirm; confirmation occurs strictly at bar $t + k$.
- **Look-Ahead Prevention Rule:** In any point-in-time evaluation at index $T$, any pivot with confirmation index $> T$ is unconfirmed and strictly excluded from evidence.
- **Classification Matrix:**
  - `UPTREND`: Latest confirmed high is `HH` and latest confirmed low is `HL`.
  - `DOWNTREND`: Latest confirmed high is `LH` and latest confirmed low is `LL`.
  - `SIDEWAYS`: Confirmed swings $\ge min\_swings$, but mixed structure (e.g. `HH` + `LL`, `LH` + `HL`, `EH`, `EL`).
  - `None` (`INSUFFICIENT_DATA`): Confirmed highs $< min\_swings$ or confirmed lows $< min\_swings$.
- **Non-Predictive Baseline Disclaimer:** Trend classifications describe historical price action structure; they do not predict future returns, directional continuation, or provide trading signals.

### Real Data Verification
Executed `scripts/verify_trend.py` on real `BHARTIARTL` historical market data:
- **Symbol:** `BHARTIARTL`
- **Data Range:** 2026-04-15 to 2026-10-12 (124 usable historical sessions)
- **Parameters:** `swing_window=2`, `min_swings=2`
- **Results:**
  - Confirmed Swing Highs: 14
  - Confirmed Swing Lows: 18
  - Latest High Structure: `LH` (Lower High at Bar 120, ₹1854.70 confirmed at Bar 122)
  - Latest Low Structure: `LL` (Lower Low at Bar 117, ₹1726.30 confirmed at Bar 119)
  - Trend Classification: `DOWNTREND` (satisfies `LH` + `LL` => `DOWNTREND`)
- **Temporal Sub-Window Look-Ahead Leakage Test:** Passed on all sub-windows ($T = 41, 62, 119$). All visible swings strictly satisfied `confirmation_index <= T`.
- **Rolling Series Alignment:** 124 bars evaluated, exactly aligned with static evaluation. Exit code: 0.

### Tests
- Created `tests/test_trend.py` with 14 comprehensive unit tests:
  1. Uptrend with HH and HL
  2. Downtrend with LH and LL
  3. Sideways range-bound contracting triangle
  4. Mixed broadening megaphone (HH + LL) handled as SIDEWAYS
  5. Insufficient historical candles policy (None / INSUFFICIENT_DATA, never mislabeled as SIDEWAYS)
  6. Missing, NaN, and non-finite values handled safely
  7. Invalid unphysical OHLC geometry handled safely
  8. Duplicate highs/lows and equal-price tie-breaking
  9. Swing confirmation timing ($t + k$) and zero lookahead leakage
  10. Deterministic results across repeated runs
  11. Configurable swing window and minimum swings
  12. Point-in-time rolling trend series alignment
  13. Pipeline integration and serialization
  14. SwingPoint and TrendAnalysisResult `.to_dict()` serialization
- **Test Suite Results:**
  - Previous baseline: 158 tests passing
  - New total: **172 passed in 4.60s** (14 new trend tests, 0 regressions). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit CLI is not installed locally; reported accurately. Manual senior dev code review conducted: clean type hints, frozen dataclasses, strict lookahead prevention, no unnecessary dependencies, and standard library datetime/math.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Shortest working diff, reusable modular functions, explicit confirmation timing, full edge-case coverage.

### Documentation
- Updated `README.md` to Day 14 status with 172 passing tests.
- Updated `docs/architecture.md` with Section 4.9 detailing Trend Engine, swing detection, confirmation timing, and classification logic.
- Updated `docs/decisions.md` with ADR 41.
- Updated `docs/roadmap.md` with Day 14 completion details.
- Updated `docs/daily-progress.md` with Day 14 development entry.

### Git Commit
- `feat: build technical feature engine`
- Commit Hash: `e5a76f06a7af2f712b69767f7b0dfc4b111eed3c`

### GitHub
- PUSHED to `origin/main` (commit verified on remote: `e5a76f06a7af2f712b69767f7b0dfc4b111eed3c`)

### Known Limitations & Next Steps
- Current trend classification provides descriptive structural regime labeling based on confirmed swing points.
- Next scheduled scope (Day 15): ML prediction target definition.

---

## Day 15 - ML Prediction Target Definition

### Goal
Define a mathematically precise, leakage-safe target for the first stock-market ML model:
1. Predict next trading session's direction for a selected stock using close-to-close returns.
2. Binary classification baseline:
   - `UP`: next session's close-to-close return is strictly positive ($target\_return[t] > 0.0$).
   - `DOWN`: next session's close-to-close return is zero or negative ($target\_return[t] \le 0.0$).
   - Explicitly document that zero-return sessions ($close[t+1] == close[t]$) are grouped into `DOWN` for this initial binary experiment without silently discarding samples.
3. Natural trading-session alignment: $close[t]$ is reference price and $close[t+1]$ is outcome price across trading days (weekends and holidays do not require a calendar daily row).
4. Strict leakage prevention:
   - Input features at time $t$ use only information at or before $t$.
   - Outcome closing price and forward return are isolated as target labels and never included in feature sets.
   - The final observation without a known next-session close strictly evaluates to `None` (missing target), not a fabricated label.
5. Implementation of reusable target module and comprehensive unit tests with zero external ML dependencies.

### Implementation
1. **Target Definition Module (`app/prediction/target.py`):**
   - Implemented `DirectionTarget`: Canonical string constants (`UP = "UP"`, `DOWN = "DOWN"`) and binary integers (`UP_BINARY = 1`, `DOWN_BINARY = 0`).
   - Implemented `TargetObservation` dataclass: Encapsulates `symbol`, `timestamp` (session $t$), `current_close`, `next_timestamp` (session $t+1$), `next_close`, `target_return`, `target_direction`, `target_binary`, convenience properties (`is_up`, `is_down`, `has_target`), and `.to_dict()`.
   - Implemented `calculate_forward_return(current_close, next_close)`: Safe calculation of $(Close_{t+1} / Close_t) - 1.0$ with non-positive price and non-finite guards.
   - Implemented `classify_forward_direction(target_return)`: Evaluates strictly positive return to `("UP", 1)` and zero/negative return to `("DOWN", 0)`.
   - Implemented `compute_target_series(closes)`: Low-level numerical sequence evaluator returning parallel lists `(returns, directions, binaries)` with final observation strictly evaluating to `None`.
   - Implemented `generate_direction_targets(records)`: High-level sequence generator accepting `MarketOHLCV` records, ensuring ticker isolation, ascending chronological ordering, non-calendar spacing, and missing final observation targets.
2. **Package Exports (`app/prediction/__init__.py`):**
   - Cleanly exported `DirectionTarget`, `TargetObservation`, `calculate_forward_return`, `classify_forward_direction`, `compute_target_series`, `generate_direction_targets`.
3. **Application Entry Point Update (`main.py`):**
   - Added `print("Day 15 ML prediction target ready")`.
4. **Real-Data Verification Script (`scripts/verify_target.py`):**
   - Validates real data acquisition on `BHARTIARTL.NS` (124 sessions), 1:1 alignment, forward return accuracy, weekend/holiday transitions, missing final target invariant, and empirical class balance.

### Mathematical Formulation & Leakage Safeguards
- **Formula:**
  $$target\_return[t] = \frac{Close_{t+1}}{Close_t} - 1.0$$
  $$target\_direction[t] = \text{"UP" if } target\_return[t] > 0.0 \text{ else "DOWN"}$$
  $$target\_binary[t] = 1 \text{ if } target\_return[t] > 0.0 \text{ else } 0$$
- **Zero-Return Baseline Policy:** Sessions with $target\_return == 0.0$ are grouped into `"DOWN"` ($binary=0$). They are explicitly retained to prevent survivorship or selection bias.
- **Trading Session Spacing:** Indexing strictly follows the chronological sequence of available trading sessions (e.g. Friday $t$ pairs with Monday $t+1$).
- **Missing Final Target Invariant:** For the latest session $t = N - 1$, no subsequent close is realized; $target\_return$, $target\_direction$, and $target\_binary$ are strictly `None` (`has_target=False`).
- **Feature-Outcome Separation:** Target logic is strictly separated from feature calculation (`app/market/`) and model training (`app/training/`).

### Real Data Verification
Executed `scripts/verify_target.py` on real `BHARTIARTL` historical market data:
- **Symbol:** `BHARTIARTL`
- **Data Range:** 2026-04-15 to 2026-10-12 (124 usable historical sessions)
- **Results:**
  - Total Historical Sessions: 124
  - Labeled Observations: 123
  - Final Session (2026-10-12): Next Date=`UNKNOWN`, Next Close=`N/A`, Forward Return=`N/A`, Target=`MISSING`, Binary=`None` (Zero leakage verified).
  - Class Distribution: UP = 60 (48.8%), DOWN = 63 (51.2%) (Healthy, realistic balance).
  - Friday-to-Monday transition verified: 2026-10-09 (₹1805.10) links to 2026-10-12 (₹1778.70, -1.46% => DOWN).
- **Exit Code:** 0.

### Tests
- Created `tests/test_target.py` with 13 comprehensive unit tests:
  1. Positive next-session return produces UP (binary 1)
  2. Negative next-session return produces DOWN (binary 0)
  3. Zero return follows documented binary rule (DOWN, binary 0)
  4. Missing next-session close on final observation strictly produces None
  5. Invalid, non-positive, zero, NaN, and infinite prices handled safely
  6. Unsorted input ordered chronologically per symbol
  7. Weekends and market holidays do not require calendar daily rows
  8. Target is aligned to correct prediction date
  9. Future outcome columns cannot leak into feature set
  10. Multi-symbol isolation guarantees targets do not cross ticker boundaries
  11. Deterministic results across repeated runs
  12. Low-level numerical `compute_target_series` functionality
  13. `TargetObservation.to_dict()` serialization
- **Test Suite Results:**
  - Previous baseline: 172 passed
  - New total: **185 passed in 4.98s** (13 new target tests, 0 regressions). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit CLI is not installed locally; reported accurately. Clean senior developer review conducted following Ponytail mode: type safety, mathematical invariants, zero code duplication, zero unnecessary dependencies, and standard library datetime/math.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Concise pure Python calculations adhering to mathematical definitions, zero bloat, shortest working diff with complete test verification.

### Documentation
- Updated `README.md` to Day 15 status with 185 passing tests.
- Updated `docs/architecture.md` with Section 4.10 detailing ML Prediction Target Definition and schedule boundaries.
- Updated `docs/decisions.md` with ADR 42.
- Updated `docs/roadmap.md` with Day 15 completion details.
- Updated `docs/daily-progress.md` with Day 15 development entry.

### Git Commit
- `feat: define next-session direction target`
- Commit Hash: `4feb2c26043270774c822dcd4e2432f69178fd63`

### GitHub
- PUSHED to `origin/main` (commit verified on remote: `4feb2c26043270774c822dcd4e2432f69178fd63`)

### Known Limitations & Next Steps
- Target definition provides the forward binary label for single-step directional forecasting.
- Next scheduled scope (Day 16): Technical feature matrix assembly and tabular dataset generation connecting features to targets.

---

## Day 16 - Technical Feature Matrix Assembly

### Goal
Build a reusable, deterministic feature-matrix assembly pipeline that combines the existing market features with the Day 15 next-session direction targets:
1. Reusable assembly module under `app/training/feature_matrix.py` joining all technical features available at session $t$ with forward targets realized at session $t+1$.
2. Strict isolation between feature matrix $X$ and target $y$, enforced by an automated isolation guard rejecting target/future columns in $X$.
3. Canonical schema of 37 numeric features across 8 domains (OHLCV, returns, volatility, moving averages, momentum oscillators, Bollinger Bands, ATR/ROC, candlestick geometry, and trend regimes).
4. Explicit timestamp join on `(symbol, timestamp)` with duplicate and non-chronological integrity validation.
5. Natural missing-value preservation policy: rolling indicator warm-up periods naturally produce NaNs; preserve them without arbitrary zero-filling so that imputation/scaling can be fitted strictly on cross-validation folds.
6. Transparent labeled subset extraction mechanism (`get_labeled_dataset()`) reporting exact row counts and exclusion reasons.
7. Verification on real `BHARTIARTL.NS` historical market data and comprehensive deterministic unit tests.

### Implementation
1. **Feature Matrix Assembly Module (`app/training/feature_matrix.py`):**
   - Implemented `FEATURE_COLUMNS`: Ordered list of 37 numeric features (`open`, `high`, `low`, `close`, `volume`, `daily_return`, `rolling_return_3d`, `rolling_return_5d`, `rolling_volatility_5d`, `annualized_volatility_5d`, `sma_5`, `sma_10`, `ema_5`, `ema_10`, `rsi_14`, `macd`, `macd_signal`, `macd_histogram`, `bb_middle`, `bb_upper`, `bb_lower`, `bb_bandwidth`, `bb_percent_b`, `atr_14`, `roc_10`, `candle_body`, `candle_body_abs`, `candle_range`, `candle_upper_wick`, `candle_lower_wick`, `candle_body_ratio`, `candle_upper_wick_ratio`, `candle_lower_wick_ratio`, `candle_close_location`, `candle_body_return_pct`, `candle_direction_encoded`, `trend_regime_encoded`).
   - Implemented `METADATA_COLUMNS`: `symbol`, `timestamp`, `next_timestamp`, `current_close`, `next_close`.
   - Implemented `TARGET_COLUMNS`: `target_return`, `target_direction`, `target_binary`.
   - Implemented categorical numerical encoders: `encode_candle_direction` (+1.0 bullish, -1.0 bearish, 0.0 neutral), `encode_trend_regime` (+1.0 UPTREND, -1.0 DOWNTREND, 0.0 SIDEWAYS, NaN unconfirmed).
   - Implemented `validate_feature_matrix_isolation(X)`: Automated guard rejecting columns matching forbidden patterns (`target`, `next_`, `future`, `outcome`).
   - Implemented `validate_chronological_integrity(records)`: Enforces chronological ordering and catches duplicate timestamps.
   - Implemented `FeatureMatrixDataset` dataclass: Encapsulates `symbol`, `df`, `X`, `y`, `metadata`, `feature_names`, `total_rows`, `labeled_rows`, `unlabeled_rows`, `.missing_value_summary()`, `.get_labeled_dataset(drop_incomplete_warmup)`, and `.to_dict()`.
   - Implemented `assemble_feature_matrix(data)`: High-level orchestrator connecting pipeline features, point-in-time rolling trends, and Day 15 prediction targets.
2. **Package Exports (`app/training/__init__.py`):**
   - Cleanly exported `FEATURE_COLUMNS`, `FORBIDDEN_FEATURE_PATTERNS`, `METADATA_COLUMNS`, `TARGET_COLUMNS`, `FeatureMatrixDataset`, `assemble_feature_matrix`, `validate_feature_matrix_isolation`.
3. **Application Entry Point Update (`main.py`):**
   - Added `print("Day 16 technical feature matrix ready")`.
4. **Real-Data Verification Script (`scripts/verify_feature_matrix.py`):**
   - End-to-end verification script for `BHARTIARTL.NS` (124 sessions), validating row alignment, zero leakage, warmup missing values accounting, class balance, and labeled training extraction.

### Feature Matrix Schema & Isolation Guards
- **Observation Alignment Invariant:** Each row $t$ contains features available at or before session $t$.
- **Strict Model-Input / Target Isolation:** $X$ contains strictly 37 numeric feature columns. Target labels ($y$), future prices ($Close_{t+1}$), and outcome timestamps are strictly isolated in `y` and `metadata`.
- **Final Observation Policy:** The final historical observation ($t = N - 1$) has no realized next session; $y$ is strictly `NaN` (unlabeled).
- **Missing Value Preservation:** Warmup periods naturally produce NaNs (e.g. 33 sessions for MACD/Signal); these are preserved without zero-filling. Imputers and scalers must be fitted on training folds only (Day 17) to prevent global leakage.

### Real Data Verification
Executed `scripts/verify_feature_matrix.py` on real `BHARTIARTL` historical market data:
- **Symbol:** `BHARTIARTL`
- **Data Range:** 2026-04-15 to 2026-10-12 (124 usable historical sessions)
- **Results:**
  - Total Aligned Rows: 124
  - Feature Columns in X: 37 (Zero target/future columns present)
  - Labeled Rows: 123 (y in {0.0, 1.0})
  - Unlabeled Final Row: 1 (y = NaN)
  - Target Class Balance: UP = 60 (48.8%), DOWN = 63 (51.2%)
  - Warmup Missing Values: OHLCV (0), Returns (5), SMAs (9), MACD/RSI (33), Bollinger (19), ATR/ROC (13), Candlesticks (0), Trend (15)
  - Supervised Training Subset Extraction: 124 initial -> 1 unlabeled excluded -> 33 incomplete warmup excluded -> 90 complete training rows
- **Exit Code:** 0.

### Tests
- Created `tests/test_feature_matrix.py` with 14 comprehensive unit tests:
  1. Correct feature-column schema and order (37 canonical features)
  2. Correct timestamp alignment with Day 15 targets
  3. Final unlabeled observation (y = NaN)
  4. Duplicate timestamp rejection (raises ValueError)
  5. Unsorted input ordered chronologically
  6. Missing values preserved for indicator warmup
  7. Target leakage rejection guard (raises ValueError on contaminated X)
  8. Future outcome columns strictly excluded from X
  9. Trend confirmation timing in feature matrix
  10. Stable row counts and deterministic repeated results
  11. Empty and insufficient input handled gracefully
  12. get_labeled_dataset accounting and optional complete warmup filtering
  13. Compatibility with existing MarketDataPipelineResult and raw bars
  14. Categorical numerical encoders mapping
- **Test Suite Results:**
  - Previous baseline: 185 passed
  - New total: **199 passed in 1.99s** (14 new feature matrix tests, 0 regressions). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit CLI tool is not installed in the local environment; reported accurately. Clean senior developer review conducted following Ponytail mode: type safety, mathematical invariants, zero code duplication, zero unnecessary dependencies, and safe edge-case handling.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Concise pandas and pure Python orchestration adhering to architectural boundaries, shortest working diff with complete test verification.

### Documentation
- Updated `README.md` to Day 16 status with 199 passing tests.
- Updated `docs/architecture.md` with Section 4.11 detailing Technical Feature Matrix Assembly Layer and schedule boundaries.
- Updated `docs/decisions.md` with ADR 43.
- Updated `docs/roadmap.md` with Day 16 completion details.
- Updated `docs/daily-progress.md` with Day 16 development entry.

### Git Commit
- `feat: assemble technical feature matrix`
- Commit Hash: `0ece524b0bb31bae95c5518b864eb4ac519a4eec`

### GitHub
- PUSHED to `origin/main` (commit verified on remote: `0ece524b0bb31bae95c5518b864eb4ac519a4eec`)

### Known Limitations & Next Steps
- Day 16 focuses exclusively on tabular dataset assembly, target joining, and leakage validation. No ML models were trained, tuned, or evaluated.
- Next scheduled scope (Day 17): First baseline ML model training (e.g. XGBoost/LightGBM) with walk-forward validation and evaluation.

---

## Day 17 - First XGBoost Direction Classifier Baseline

### Goal
Train the first reproducible XGBoost binary classifier predicting the next available trading session's direction (`UP`=1, `DOWN`=0) using the Day 15 target formulation and Day 16 technical feature matrix:
1. Conduct pre-training audit, resolve date lookback investigations, and verify data freshness.
2. Build reusable training module (`app/training/xgboost_classifier.py`) adhering to native XGBoost APIs (`xgb.train`, `xgb.DMatrix`) to eliminate unneeded `scikit-learn` dependencies.
3. Configure conservative, explicit baseline hyperparameters (`max_depth=3`, `learning_rate=0.05`, `n_estimators=50`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42`, `n_jobs=1`).
4. Implement strict chronological holdout partitioning with a 1-session outcome embargo gap ensuring zero temporal label leakage into the training set.
5. Extract complete labeled rows (`drop_incomplete_warmup=True`), accounting transparently for excluded warmup rows (33 sessions) and the final unlabeled observation.
6. Evaluate out-of-sample holdout metrics (Accuracy, Precision, Recall, F1, Confusion Matrix) using a pure Python / NumPy metrics engine.
7. Verify 100% deterministic prediction reproducibility and validate native model persistence.
8. Retain explicit research baseline disclaimers (no trading edge or calibrated odds claims).

### Pre-Training Audit & Date Range Investigation
- **Date Discrepancy Investigation:**
  - Audited repository history and active verification scripts (`scripts/verify_target.py` and `scripts/verify_feature_matrix.py`).
  - Found that the codebase has consistently requested a lookback of 180 calendar days defaulting from `datetime.now()` (`2026-10-13`).
  - Actual first and last returned timestamps: `2026-04-16` to `2026-10-13` (123 historical sessions).
  - Data cache is empty (`data/cache/` contains only `.gitkeep`), confirming live HTTP data retrieval via `yfinance`.
  - Date references to 2024 (e.g. `2024-04-12 to 2024-10-11`) were never generated or saved by this codebase; they stem from external prompt evaluation templates created in October 2024, whereas the live environment clock and NSE market data reflect October 2026.
  - Confirmed data is fresh, verified, clean, and not stale.

### Implementation
1. **Dependency Management (`requirements.txt`):**
   - Added `xgboost>=2.0.0`. Installed `xgboost-3.4.1` in the virtual environment.
   - Avoided installing `scikit-learn` by leveraging native XGBoost core APIs (`xgb.train`, `xgb.DMatrix`), adhering strictly to Ponytail minimalist dependency rules.
2. **XGBoost Direction Classifier Module (`app/training/xgboost_classifier.py`):**
   - Implemented `XGBoostConfig`: Immutable configuration container specifying `objective="binary:logistic"`, `eval_metric="logloss"`, `random_state=42`, conservative tree parameters, and `.to_params_dict()`.
   - Implemented `ClassificationMetrics`: Container for Accuracy, Precision, Recall, F1, Confusion Matrix (`[[TN, FP], [FN, TP]]`), and class distribution counts with positive class convention 1 (`UP`).
   - Implemented `compute_classification_metrics(y_true, y_pred)`: Pure Python / NumPy metrics calculator with zero-division safeguards.
   - Implemented `ChronologicalSplitResult` & `split_chronological_holdout()`: Partitions time series chronologically with an explicit 1-session embargo gap, mathematically verifying that `train_outcome_cutoff <= holdout_start_date`.
   - Implemented `XGBoostDirectionClassifier`: Object-oriented model wrapper supporting `.fit()`, `.predict()`, `.predict_proba()`, `.save_model()`, and `.load_model()` using native XGBoost JSON format.
   - Implemented `train_baseline_classifier()` and `run_training_pipeline()`: High-level functional orchestrators for clean pipeline integration.
3. **Package Exports (`app/training/__init__.py`):**
   - Cleanly exported `ChronologicalSplitResult`, `ClassificationMetrics`, `DirectionTrainingResult`, `XGBoostConfig`, `XGBoostDirectionClassifier`, `compute_classification_metrics`, `run_training_pipeline`, `split_chronological_holdout`, `train_baseline_classifier`.
4. **Application Entry Point Update (`main.py`):**
   - Added `print("Day 17 XGBoost direction classifier ready")`.
5. **Real-Data Verification Script (`scripts/verify_xgboost.py`):**
   - End-to-end verification script for `BHARTIARTL.NS` (123 sessions), validating data pipeline execution, tabular feature assembly, warmup exclusion accounting, chronological embargo split, baseline model fitting, holdout metric computation, and deterministic repeatability.

### Real Data Verification Results
Executed `scripts/verify_xgboost.py` on real `BHARTIARTL` historical market data:
- **Symbol:** `BHARTIARTL`
- **Data Range:** 2026-04-16 to 2026-10-13 (123 usable historical sessions)
- **Sample Accounting:**
  - Initial Total Observations: 123
  - Unlabeled Final Row Excluded: 1
  - Incomplete Indicator Warmup Rows Excluded: 33
  - Retained Complete Labeled Observations: 89
- **Chronological Holdout Split:**
  - Train Partition: 70 sessions [2026-06-04 to 2026-09-10]
  - Embargo Gap: 1 session [2026-09-11] (purged to prevent label outcome leakage)
  - Holdout Partition: 18 sessions [2026-09-15 to 2026-10-09]
  - Train Outcome Cutoff: 2026-09-11 <= Holdout Start Date: 2026-09-15 (Zero temporal leakage verified).
- **Class Distributions:**
  - Train: DOWN(0) = 34 (48.6%), UP(1) = 36 (51.4%)
  - Holdout: DOWN(0) = 9 (50.0%), UP(1) = 9 (50.0%)
- **Holdout Evaluation Metrics (Unseen Data):**
  - Holdout Sessions: 18
  - Accuracy: 0.4444 (44.44%)
  - Precision (UP=1): 0.4706
  - Recall (UP=1): 0.8889
  - F1 Score (UP=1): 0.6154
  - Confusion Matrix: `[[TN=0, FP=9], [FN=1, TP=8]]`
- **Deterministic Repeatability:** 100% identical predictions and probabilities across repeated runs with seed=42.
- **Exit Code:** 0.

### Tests
- Created `tests/test_xgboost_classifier.py` with 14 comprehensive unit tests:
  1. Default conservative hyperparameters, fixed seed (42), and config serialization.
  2. Successful model fitting and probability inference on synthetic dataset.
  3. Strict feature column order preservation and permuted column alignment.
  4. Missing value rejection policy in baseline mode (`allow_missing=False`).
  5. Empty dataset rejection handling (raises ValueError).
  6. Single-class dataset rejection handling (raises ValueError).
  7. Target and future-column leakage rejection via isolation guard.
  8. Chronological split boundaries and partition size conservation.
  9. Prevention of holdout leakage into training (temporal embargo validation).
  10. Deterministic, reproducible predictions across repeated runs.
  11. Model serialization and persistence verification (JSON format).
  12. Classification metric calculations and zero-division edge cases.
  13. Graceful handling when optional xgboost is unavailable.
  14. Full training pipeline orchestration on synthetic FeatureMatrixDataset.
- **Test Suite Results:**
  - Previous baseline: 199 passed
  - New total: **213 passed in 2.51s** (14 new classifier tests, 0 regressions). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit CLI tool is not installed in the local environment; reported accurately. Clean senior developer review conducted following Ponytail mode: type safety, mathematical invariants, zero code duplication, zero unnecessary dependencies (pure Python metrics, native XGBoost Core API without scikit-learn), and safe edge-case handling.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Minimalist, robust, leak-free gradient-boosted baseline with full test verification.

### Documentation
- Updated `README.md` to Day 17 status with 213 passing tests.
- Updated `docs/architecture.md` with Section 4.12 detailing Baseline XGBoost Direction Classifier Layer.
- Updated `docs/decisions.md` with ADR 44.
- Updated `docs/roadmap.md` with Day 17 completion details.
- Updated `docs/daily-progress.md` with Day 17 development entry.

### Git Commit
- `feat: train first XGBoost direction classifier`
- Commit Hash: `076bf01`

### Known Limitations & Next Steps
- This is a research baseline with fixed default hyperparameters; it exhibits an upward bias on the small holdout window (predicting UP for 17 of 18 sessions).
- No claim is made of commercial viability, calibrated probabilities, or a profitable trading edge.
- Next scheduled scope (Day 18): Baseline comparisons (random and majority class baselines), evaluation metrics expansion, and LightGBM comparison.

---

## Day 18 - Baseline Comparison & XGBoost Evaluation

### Goal
Evaluate the existing Day 17 XGBoost binary direction classifier against standard non-parametric baselines on the same dataset, target definition, chronological holdout, and evaluation metrics:
1. Reproduce Day 17 XGBoost holdout results from the active codebase.
2. Implement Baseline A: Majority-Class Classifier (predicts training label majority with deterministic tie-breaking).
3. Implement Baseline B: Fixed-Seed Random Classifier (supports uniform $p=0.5$ and stratified $p=train\_prior$ policies, fixed seed=42).
4. Evaluate Model C: Existing Day 17 XGBoost Classifier without modifying hyperparameters or feature schema.
5. Apply fair, leakage-safe evaluation protocol with 1-session embargo gap on identical holdout samples.
6. Generate a comprehensive comparative evaluation table and answer core empirical audit questions.
7. Add deterministic automated unit tests and retain strict research honesty.

### Implementation
1. **Baseline Classifiers & Evaluation Layer (`app/training/baselines.py`):**
   - Implemented `MajorityClassClassifier`: Evaluates training partition class counts (`class_counts_`), determines majority class, and handles ties deterministically via `tie_break_class` (default 1 / UP). Evaluates test samples with zero holdout leakage.
   - Implemented `RandomClassifier`: Deterministic pseudo-random direction generator using fixed seed (default 42). Supports `uniform` ($p=0.5$), `stratified` ($p = \text{train prior}$), and `custom` policies.
   - Implemented `BaselineComparisonRow` & `BaselineComparisonReport`: Structured containers capturing per-strategy Accuracy, Precision, Recall, F1, Confusion Matrix, UP/DOWN prediction counts, and correct counts, with Markdown table generation (`.summary_table()`).
   - Implemented `evaluate_baseline_comparison()`: Unified comparative orchestrator executing fair, parallel evaluation of all four strategies across identical test observations.
2. **Package Exports (`app/training/__init__.py`):**
   - Cleanly exported `MajorityClassClassifier`, `RandomClassifier`, `BaselineComparisonRow`, `BaselineComparisonReport`, and `evaluate_baseline_comparison`.
3. **Application Entry Point Update (`main.py`):**
   - Added `print("Day 18 baseline comparison ready")`.
4. **Real-Data Verification Script (`scripts/verify_baselines.py`):**
   - End-to-end verification script for `BHARTIARTL.NS` running the complete pipeline, feature matrix assembly, chronological embargo split, and comparative baseline evaluation.

### Comparative Evaluation Results (BHARTIARTL Holdout, N=18)
Executed `scripts/verify_baselines.py` on real market data (Holdout: `2026-09-15` to `2026-10-09`, 9 UP and 9 DOWN actual outcomes):

| Strategy | Accuracy | UP Precision | UP Recall | UP F1 | Confusion Matrix (TN,FP,FN,TP) | Pred UP/DOWN | Correct UP/DOWN |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline A (Majority Class)** | 50.00% | 50.00% | 100.00% | 0.6667 | `[[0, 9], [0, 9]]` | 18 / 0 | 9 / 0 |
| **Baseline B1 (Uniform Random, p=0.5)** | 44.44% | 44.44% | 44.44% | 0.4444 | `[[4, 5], [5, 4]]` | 9 / 9 | 4 / 4 |
| **Baseline B2 (Stratified Random, p=train_prior)** | 55.56% | 55.56% | 55.56% | 0.5556 | `[[5, 4], [4, 5]]` | 9 / 9 | 5 / 5 |
| **Model C (Day 17 XGBoost)** | 44.44% | 47.06% | 88.89% | 0.6154 | `[[0, 9], [1, 8]]` | 17 / 1 | 8 / 0 |

### Empirical Findings & Audit Questions
1. **Which strategy performed best on the holdout?**
   - By accuracy: Baseline B2 (Stratified Random) achieved 55.56%, followed by Baseline A (Majority Class) at 50.00%.
   - By F1 score: Baseline A (Majority Class) achieved 0.6667.
2. **Did XGBoost outperform the majority-class baseline?**
   - **NO.** Majority-class accuracy was 50.00% (F1 = 0.6667), whereas XGBoost achieved 44.44% (F1 = 0.6154).
3. **Did XGBoost outperform the fixed-seed random baseline?**
   - **NO.** Uniform Random tied XGBoost on accuracy (44.44% vs 44.44%) while making balanced predictions, and Stratified Random beat XGBoost (55.56% vs 44.44%).
4. **Is the XGBoost UP prediction bias still present?**
   - **YES.** XGBoost predicted UP for 17 of 18 holdout sessions (94.4% of samples), capturing 0 of the 9 downward sessions (TN = 0, FP = 9).
5. **Is the holdout window large enough to support a definitive conclusion?**
   - **NO.** 18 sessions (~3.5 weeks) has low statistical power; a 1-sample difference shifts accuracy by 5.55 percentage points.
6. **What should the next model development step be based on the evidence?**
   - Expand historical lookback (multi-year dataset) to provide statistical power.
   - Benchmark LightGBM on the exact same baseline comparison framework before tuning.
   - Investigate class weighting and decision threshold calibration for tree models.

### Tests
- Created `tests/test_baselines.py` with 12 comprehensive unit tests:
  1. Majority-class selection uses training labels only.
  2. Deterministic tie-handling in MajorityClassClassifier.
  3. MajorityClassClassifier shape, values, and probabilities.
  4. MajorityClassClassifier error handling on invalid or empty inputs.
  5. Reproducibility of fixed-seed random predictions.
  6. Policy enforcement for RandomClassifier ('uniform', 'stratified', 'custom').
  7. RandomClassifier input validation and error handling.
  8. Identical holdout indices and fair evaluation across strategies.
  9. Leakage prevention: holdout outcomes strictly invisible to baselines.
  10. Consistent metric calculations and confusion-matrix correctness.
  11. BaselineComparisonReport generation, summary table, and serialization.
  12. Regression protection for existing Day 17 XGBoost classifier within comparison.
- **Test Suite Results:**
  - Previous baseline: 213 passed
  - New total: **225 passed in 2.62s** (12 new baseline tests, 0 regressions). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit CLI tool is not installed in the local environment; reported accurately. Clean senior developer review conducted following Ponytail mode: type safety, mathematical invariants, zero code duplication, zero unnecessary dependencies (pure Python / NumPy baseline implementations), and safe edge-case handling.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Minimalist, robust, leak-free non-parametric baselines with full test verification.

### Documentation
- Updated `README.md` to Day 18 status with 225 passing tests.
- Updated `docs/architecture.md` with Section 4.13 detailing Baseline Comparison & Evaluation Framework.
- Updated `docs/decisions.md` with ADR 45.
- Updated `docs/roadmap.md` with Day 18 completion details.
- Updated `docs/daily-progress.md` with Day 18 development entry.

### Git Commit
- `feat: implement baseline comparison and evaluate XGBoost`
- Commit Hash: `ea515bf`

### Known Limitations & Next Steps
- Baseline comparison proves that un-tuned XGBoost on a short 180-day slice behaves similarly to a majority-UP heuristic.
- Next scheduled scope (Day 19): Multi-year historical lookback expansion and LightGBM directional benchmark against the baseline framework.

---

## Pre-Day 19 - Validation Gate (Reliability Audit & Historical Capability)

### Goal
Execute two focused validation gates prior to commencing Day 19 work (validation-only gate, not a roadmap day):
1. **Audit A — Random Baseline Reliability:** Measure sampling variability of pseudo-random baselines across 50 predeclared seeds on the unchanged 18-session holdout, referencing Majority-Class and Day 17 XGBoost baselines.
2. **Audit B — Historical Provider Capability:** Inspect `YFinanceProvider` and test a read-only 5-year historical data request for `BHARTIARTL.NS`, verifying session counts, duplicates, missing values, physical OHLC invariants, corporate actions, and price adjustment semantics.
3. Formulate an evidence-based recommendation on whether Day 19 can safely begin.

### Audit A: Random Baseline Reliability (50 Predeclared Seeds)
- **Holdout Configuration:** Identical 18-session chronological holdout (`2026-09-15` to `2026-10-09`, 9 UP and 9 DOWN actual outcomes). Training set: 70 sessions (`2026-06-04` to `2026-09-10`, 36 UP and 34 DOWN, prior $P(UP) = 0.5143$). Embargo: 1 session (`2026-09-11`).
- **Seed Protocol:** Evaluated 50 predeclared fixed seeds (`seeds = list(range(1, 51))`) for Uniform ($P(UP) = 0.5$) and Stratified ($P(UP) = 0.5143$) random baselines. Stratified probability derived strictly from training labels with zero holdout leakage.
- **Reference Strategies (Deterministic):**
  - **Baseline A (Majority Class):** Accuracy = **50.00%** | UP F1 = **0.6667** | Confusion Matrix = `[[0, 9], [0, 9]]` | Predictions: 18 UP, 0 DOWN
  - **Model C (Day 17 XGBoost):** Accuracy = **44.44%** | UP F1 = **0.6154** | Confusion Matrix = `[[0, 9], [1, 8]]` | Predictions: 17 UP, 1 DOWN
- **Multi-Seed Random Baseline Distribution ($N=50$ Seeds):**
  - **Uniform Random ($P(UP) = 0.5000$):**
    - Accuracy: Mean = **52.78%** | Std = **14.16%** | Min = **27.78%** | Max = **94.44%**
    - UP F1: Mean = **0.5159** | Std = **0.1642** | Min = **0.1333** | Max = **0.9474**
  - **Stratified Random ($P(UP) = 0.5143$):**
    - Accuracy: Mean = **47.33%** | Std = **14.43%** | Min = **5.56%** | Max = **72.22%**
    - UP F1: Mean = **0.4734** | Std = **0.1652** | Min = **0.0000** | Max = **0.7619**
- **Methodological Finding:**
  - Repeated seeds measure the sampling variability of the random baseline on this small $N=18$ holdout; they **do not** increase the effective number of independent market observations.
  - The wide spread of accuracy across seeds (27.8% to 94.4% for uniform; 5.6% to 72.2% for stratified) proves that on an 18-session holdout, accuracy is dominated by small-sample variance ($\sigma \approx 14.2\%$). XGBoost's 44.44% score falls well within 1 standard deviation of random guessing, confirming that no predictive edge can be claimed on this sample.

### Audit B: Historical Provider Capability & Data Integrity
- **Provider Inspected:** `YFinanceProvider` (`app/market/providers/yfinance_provider.py`), querying `BHARTIARTL.NS`.
- **Maximum Lifetime Historical Availability:** 6,027 trading sessions spanning `2002-07-01` to `2026-10-13` (~24.1 years of continuous daily data available via Yahoo Finance).
- **Read-Only 5-Year Historical Request:**
  - Requested Period: `2021-10-14` to `2026-10-13` (~5 calendar years).
  - Returned Period: `2021-10-14` to `2026-10-13` (1,234 trading sessions).
  - Unique Sessions: 1,234 | Duplicate Sessions: **0** | Missing / NaN Bars: **0**.
  - Physical OHLC Boundary Invariants: **0 breaches** ($Low \le Open \le High$, $Low \le Close \le High$, $Volume \ge 0$, Prices $> 0$).
  - Calendar Validation: Weekends and NSE exchange holidays correctly identified as non-trading sessions (not missing bars).
- **Corporate Actions & Price Adjustment Semantics:**
  - Stock Splits (5-year): **0** (no split adjustments needed for BHARTIARTL.NS in this window).
  - Dividends (5-year): **5 payout events** totaling ₹55.00/share (2022: ₹3.0, 2023: ₹4.0, 2024: ₹8.0, 2025: ₹16.0, 2026: ₹24.0).
  - Provider Semantics: `auto_adjust=False` preserves raw traded prices (`Close`), ensuring authentic physical candlestick bounds and true intraday volatility.
  - Mean absolute difference between raw `Close` and dividend-adjusted `Adj Close` is ₹26.34 (maximum ₹41.93).
  - Limitation Documented: Ex-dividend dates create small artificial downward price gaps on raw price series unless dividend adjustments are incorporated.

### Git Commit
- `chore: execute pre-Day 19 validation gate on baselines and historical provider`
- Commit Hash: `18cf838`

### Validation Gate Recommendation
1. **Audit A Conclusion:** The 18-session holdout is statistically inadequate for reliable model evaluation ($\pm 5.55\%$ per sample; random guessing ranges from 5.6% to 94.4%). Multi-year data is mandatory before drawing architectural conclusions.
2. **Audit B Conclusion:** 5 years (1,234 sessions) of clean, high-quality, zero-duplicate daily market data is immediately accessible via `YFinanceProvider`.
3. **Recommendation:** **DAY 19 CAN SAFELY PROCEED** to expand historical data lookback and implement the LightGBM directional classifier baseline.

---

## Day 19 - Multi-Year Historical Data & LightGBM Benchmark

### Goal
1. Expand the existing `BHARTIARTL.NS` historical dataset to approximately 5 years (1,234 trading sessions) using the verified `YFinanceProvider`.
2. Audit corporate action events (cash dividends and stock splits) and price adjustment semantics before using raw returns as the supervised target.
3. Rebuild the evaluation dataset with a high-powered chronological training/embargo/holdout protocol (80/20 split, 1-session embargo).
4. Re-evaluate existing non-parametric baselines (Majority Class, Uniform Random, Stratified Random) and Day 17 XGBoost classifier across identical 240-session holdout observations.
5. Evaluate sampling variability of random baselines across 50 predeclared seeds.
6. Implement the LightGBM Direction Classifier baseline (`app/training/lightgbm_classifier.py`) adhering to native APIs, seed determinism, and zero test leakage.
7. Benchmark LightGBM fairly against XGBoost and baselines on the multi-year holdout.

### Phase 1: Corporate Actions & Dividend Adjustment Audit (ADR 46)
- **Provider Semantics Evaluated:** `auto_adjust=False` vs `auto_adjust=True` in `YFinanceProvider` for `BHARTIARTL.NS`.
  - `auto_adjust=False`: Preserves raw traded prices in `Close` and records dividend-adjusted values in `Adj Close`. Candlestick physical geometry ($Low \le Open, Close \le High$) and intraday volatility are 100% authentic.
  - `auto_adjust=True`: Scales all OHLC prices backward by dividend adjustment factors. Every time a new dividend occurs, all past prices are retroactively revised, which violates point-in-time stability in live settings.
- **5-Year Corporate Action Audit on BHARTIARTL.NS:**
  - Stock Splits: **0 events** (no split adjustments required).
  - Cash Dividends: **5 events** totaling ₹55.00/share:
    1. `2022-08-01`: ₹3.00 payout | Raw: +2.43% (UP) vs Adj: +2.89% (UP) — Direction Match: **YES**
    2. `2023-08-11`: ₹4.00 payout | Raw: -0.49% (DOWN) vs Adj: -0.03% (DOWN) — Direction Match: **YES**
    3. `2024-08-07`: ₹8.00 payout | Raw: -0.12% (DOWN) vs Adj: +0.43% (UP) — Direction Match: **NO (Flip)**
    4. `2025-07-18`: ₹16.00 payout | Raw: -1.50% (DOWN) vs Adj: -0.67% (DOWN) — Direction Match: **YES**
    5. `2026-07-24`: ₹24.00 payout | Raw: -1.70% (DOWN) vs Adj: -0.46% (DOWN) — Direction Match: **YES**
- **Methodological Finding & Decision (ADR 46):**
  - Direction flipped on exactly 1 session out of 1,234 trading sessions (0.081% of the dataset: 2024-08-07, ₹8.00 payout, -0.12% raw vs +0.43% dividend-adjusted).
  - Maintained canonical raw unadjusted price convention (`auto_adjust=False`) to preserve authentic traded levels and physical candle bounds without retroactive price revision.
  - *Distinction Between Raw Direction and Total Return:* Raw close-to-close price direction tracks nominal exchange quoted movement ($Close_{t+1} / Close_t - 1.0 > 0$), whereas total return models investor economic wealth including cash distributions ($[Close_{t+1} + Div_{t+1}] / Close_t - 1.0 > 0$).
  - *Critical Clarification:* High empirical directional agreement (99.919%) shows low sensitivity on this specific ticker, but empirical raw-versus-adjusted agreement alone does NOT establish raw price direction as the economically "correct" label. For an investor, cash received is actual return.
  - *Unresolved Limitations & Future Decision:* Mechanical price drops on ex-dividend dates create artificial downward label bias on ex-dates. On high-dividend stocks, divergence will be higher. If trading execution or portfolio backtesting is introduced in later phases, a separate methodological decision will formally define a Total Return Target Layer while preserving raw candle records.

### Phase 2 & 3: Multi-Year Historical Pipeline & Dataset Rebuild
- **Historical Query:** `BHARTIARTL` queried via `YFinanceProvider` from `2021-10-14` to `2026-10-13` (5 calendar years).
- **Data Quality Results:**
  - Raw Bars Collected: 1,234
  - Cleaned Bars: 1,234 (0 missing, 0 invalid, 0 identical duplicates, 0 conflicting duplicates, 0 rejections).
  - Chronological Order: Strictly ascending `(symbol, timestamp)`.
- **Feature Matrix & Target Assembly:**
  - Initial Sessions: 1,234
  - Excluded Unlabeled Final Row: 1 ($y = NaN$, future unknown)
  - Excluded Incomplete Warmup Rows: 35 (natural indicator warmups: MACD-26, Bollinger-20, ATR-14, RSI-14)
  - Retained Complete Labeled Rows: **1,198**
- **Chronological Embargo Split (80/20):**
  - **Training Partition:** 957 sessions (`2021-12-03` to `2025-10-16`, 500 UP / 457 DOWN, $P(UP) = 52.25\%$)
  - **Embargo Gap (Purged):** 1 session (`2025-10-17`, outcome cutoff $\le$ holdout start date)
  - **Holdout Partition:** **240 sessions** (`2025-10-20` to `2026-10-09`, 120 UP / 120 DOWN, exactly $50.00\%$ balanced)

### Phase 4 & 5: Baseline and Model Evaluation (Holdout N=240 Sessions)
Executed `scripts/verify_day19.py` on real market data:

| Strategy | Accuracy | UP Precision | UP Recall | UP F1 | Confusion Matrix (TN,FP,FN,TP) | Pred UP/DOWN | Correct UP/DOWN |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline A (Majority Class)** | 50.00% | 50.00% | 100.00% | 0.6667 | `[[0, 120], [0, 120]]` | 240 / 0 | 120 / 0 |
| **Baseline B1 (Uniform Random, seed=42)** | 45.42% | 45.38% | 45.00% | 0.4519 | `[[55, 65], [66, 54]]` | 119 / 121 | 54 / 55 |
| **Baseline B2 (Stratified Random, seed=42)**| 53.75% | 53.49% | 57.50% | 0.5542 | `[[60, 60], [51, 69]]` | 129 / 111 | 69 / 60 |
| **Model C (Day 17 XGBoost)** | **54.17%** | 53.97% | 56.67% | 0.5528 | `[[62, 58], [52, 68]]` | 126 / 114 | 68 / 62 |
| **Model D (Day 19 LightGBM)** | **53.75%** | 53.72% | 54.17% | 0.5394 | `[[64, 56], [55, 65]]` | 121 / 119 | 65 / 64 |

### Deep Audit: Random Baseline Sampling Variance (50 Predeclared Seeds)
- **Uniform Random ($P(UP) = 0.5000$):**
  - Accuracy: Mean = **50.14%** | Std = **3.19%** (vs 14.16% on N=18)
  - UP F1: Mean = **0.4997** | Std = **0.0358**
- **Stratified Random ($P(UP) = 0.5225$):**
  - Accuracy: Mean = **49.72%** | Std = **3.24%** (vs 14.43% on N=18)
  - UP F1: Mean = **0.5095** | Std = **0.0367**
- **Methodological Significance:**
  - Expanding the holdout sample from $N=18$ to $N=240$ reduced standard error of the mean by over **77%** ($\sigma$ dropped from 14.2% to 3.2%).
  - On this sample, both tree models exceed mean random performance by ~4 percentage points, exceeding 1 standard deviation of the random baseline distribution.

### Empirical Findings & Audit Conclusions
1. **Did expanding to 5 years eliminate the extreme UP prediction bias?**
   - **YES.** In Day 18 (N=18), XGBoost predicted UP for 94.4% of sessions (17 UP / 1 DOWN). On the 5-year dataset (N=240), XGBoost predicted 126 UP and 114 DOWN (52.5% / 47.5%), and LightGBM predicted 121 UP and 119 DOWN (50.4% / 49.6%), aligning naturally with the true 50/50 test distribution.
2. **Did XGBoost beat the majority-class baseline on the multi-year holdout?**
   - **YES.** XGBoost achieved 54.17% accuracy vs Majority Class at 50.00% (+4.17 percentage points).
3. **How does LightGBM compare to XGBoost under identical conditions?**
   - Both gradient-boosted decision tree architectures perform within 0.42 percentage points of each other (XGBoost: 54.17%, LightGBM: 53.75%).
   - XGBoost achieved slightly higher recall on UP sessions (56.67% vs 54.17%); LightGBM achieved slightly higher specificity on DOWN sessions (53.33% vs 51.67%).
4. **Does ~54% directional accuracy prove a viable trading edge?**
   - **NO.** A single chronological holdout window is preliminary evidence of predictive signal, not proof of a deployable trading edge. Real-world execution involves bid-ask spread, transaction fees, securities transaction tax (STT), and regime shifts.

### Tests
- Created `tests/test_lightgbm_classifier.py` with 14 comprehensive unit tests:
  1. LightGBMConfig defaults and parameter dictionary serialization.
  2. Model fitting and prediction on synthetic dataset.
  3. Feature column schema preservation and column realignment.
  4. Missing value rejection policy (`allow_missing=False`).
  5. Empty dataset rejection handling.
  6. Single-class dataset rejection handling.
  7. Target and future-column leakage rejection (isolation guard).
  8. Deterministic, reproducible predictions with fixed seed.
  9. Probability prediction structure (`predict_proba` valid distribution summing to 1.0).
  10. Model persistence (save and reload booster from file).
  11. Feature importance extraction (`feature_importances_`).
  12. Graceful ImportError handling when `lightgbm` is unavailable.
  13. Small dataset rejection handling (<10 samples).
  14. Sample count mismatch rejection.
- Added LightGBM integration test `test_baseline_comparison_with_lightgbm` in `tests/test_baselines.py`.
- Added 3 regression tests in `tests/test_baselines.py` for CodeRabbit review findings:
  1. `test_sample_count_validation_baselines`: verifies boolean rejection, non-positive integer rejection, and type check in `predict` and `predict_proba`.
  2. `test_majority_class_zero_reporting_in_evaluation`: verifies correct reporting and prediction when training majority class is 0 (DOWN), preventing falsy `0 or 1` default.
  3. `test_random_classifier_stratified_non_binary_labels`: verifies rejection of non-binary training labels in stratified `RandomClassifier.fit`.
- **Full Test Suite Results:**
  - Previous baseline: 225 passed
  - Post-LightGBM: 240 passed
  - Post-CodeRabbit remediation: **243 passed in 2.60s** (0 failures, 0 regressions). Zero external network dependencies.

### Review & Remediation (CodeRabbit Findings in `app/training/baselines.py`)
- **Finding 1 (Sample Count Handling in `predict` / `predict_proba`):**
  - *Analysis:* Passing booleans (e.g. `True` / `False`) or non-positive values was not strictly validated; in Python, `bool` is a subclass of `int`.
  - *Fix:* Added `_resolve_n_samples(X)` helper that explicitly checks `isinstance(X, bool)` and rejects with `TypeError`, checks `n_samples <= 0` and rejects with `ValueError`, and validates `hasattr(X, "__len__")`.
- **Finding 2 (Falsy `0 or 1` Default in `BaselineComparisonReport`):**
  - *Analysis:* In `evaluate_baseline_comparison`, `train_majority_class=clf_majority.majority_class_ or 1` inadvertently remapped majority class `0` (DOWN) to `1` (UP).
  - *Fix:* Added explicit fitted guard (`if not clf_majority.is_fitted or clf_majority.majority_class_ is None: raise ValueError(...)`) and passed `clf_majority.majority_class_` directly without the falsy fallback.
- **Finding 3 (Non-Binary Label Validation in `RandomClassifier.fit`):**
  - *Analysis:* Stratified policy accepted non-binary integers without verifying labels strictly belong to `{0, 1}`.
  - *Fix:* Added strict check `if n_zero + n_one != len(y_arr): raise ValueError("Labels must be strictly binary integers in {0, 1}.")`.
- **Invariance Verification:** Ran `scripts/verify_pre_day19_gate.py`, `scripts/verify_baselines.py`, and `scripts/verify_day19.py`. All Day 18 and Day 19 empirical metrics are 100% invariant.
- **Ponytail / Senior Dev Mode:** Reused existing baseline framework, canonical feature matrix schema, and chronological embargo splitter without code duplication. Native `lgb.train` API used without `scikit-learn` dependency.
- **Roo Code:** Remained disabled.

### Documentation
- Updated `README.md` to Day 19 status with 243 passing tests.
- Updated `docs/architecture.md` with Section 4.14 detailing Multi-Year Historical Evaluation & LightGBM Baseline.
- Updated `docs/decisions.md` with ADR 46 (Dividend Adjustment & Corporate Actions Policy) and ADR 47 (LightGBM Direction Classifier Baseline).
- Updated `docs/roadmap.md` with Day 19 completion.
- Updated `docs/daily-progress.md` with Day 19 audit log and CodeRabbit remediation notes.

### Git Commit & Push
- **Feature Commit:** `76b283b` — `feat: implement LightGBM binary classifier baseline and corresponding tests`
- **Documentation Commit:** `4a40492` — `docs: record Day 19 commit hash and next steps in daily-progress.md`
- **Remediation Commit:** `82d0572` — `feat: add baseline direction classifiers and comparative evaluation suite with tests and documentation`
- **Remote Status:** PUSHED and verified on `origin/main` (`https://github.com/naiya555/stock-market-prediction-system`)

### Known Limitations & Next Steps
- Both XGBoost (54.17%) and LightGBM (53.75%) achieve ~54% directional accuracy on the out-of-sample holdout, beating the majority class (50.00%) and random baseline distributions (~50.0% +/- 3.2%). However, single-split holdout metrics are preliminary evidence of signal and must be tested under rolling walk-forward cross-validation.
- **Random Baseline Aggregation Conventions:** `scripts/verify_day19.py` reports standard deviation using `numpy.std` default `ddof=0` (population stdev: ±3.19% for uniform, ±3.24% for stratified on N=50 seeds), whereas `scripts/verify_pre_day19_gate.py` explicitly uses `ddof=1` (sample stdev: ±14.16% on N=18 holdout). For N=50 seeds, sample standard deviation ($ddof=1$) scales standard error by $\sqrt{50/49} \approx 1.0102$ (±3.22% uniform, ±3.27% stratified), leaving all substantive conclusions unchanged.
- **Corporate Action Semantics:** Supervised targets currently predict raw nominal close-to-close price direction, which models exchange quote direction rather than dividend-inclusive investor wealth accrual. Cash dividends create mechanical downward price jumps on ex-dividend dates; a dedicated Total Return Target Layer will be evaluated in future phases if portfolio backtesting or execution modeling is introduced.
- Transaction costs, market slippage, and securities transaction taxes (STT) are not yet integrated into the strategy evaluation.
- Next scheduled scope (Day 20): Walk-forward temporal cross-validation across multiple market cycles and rolling regimes without lookahead leakage.

---

## Day 20 - Walk-Forward Temporal Cross-Validation

### Goal
Implement and verify leakage-safe walk-forward temporal cross-validation for the existing `BHARTIARTL.NS` direction-prediction pipeline:
1. Create a reusable walk-forward temporal evaluation engine under `app/training/walk_forward.py`.
2. Generate chronological expanding-window folds where each fold trains strictly on observations available prior to its validation window.
3. Enforce a configurable outcome embargo gap ($\ge 1$ session) purged between training and validation windows to eliminate forward target leakage across boundaries ($train\_outcome\_cutoff \le val\_start\_date$).
4. Require explicit fold accounting: train/validation start and end dates, row counts, class distributions, and outcome cutoff timestamps.
5. Verify that train, embargo, and validation indices are mutually disjoint ($Train \cap Embargo = \emptyset$, $Embargo \cap Val = \emptyset$, $Train \cap Val = \emptyset$).
6. Evaluate all 5 benchmark strategies on identical validation folds: Majority Class, Uniform Random ($P=0.5$), Stratified Random ($P=train\_prior$, fitted exclusively on training labels), Day 17 XGBoost, and Day 19 LightGBM.
7. Preserve model hyperparameters unchanged (zero hyperparameter tuning, feature selection, or retraining on validation feedback).
8. Implement dual aggregation: macro-averaged fold mean $\pm$ sample standard deviation ($ddof=1$) and micro-pooled confusion matrix accumulation.
9. Guard against edge cases: explicit single-class training handling (`SKIPPED_SINGLE_CLASS`), undersized fold termination, and pre-declared seeds (`base_seed + fold_idx * 1000`) for reproducible pseudo-random baselines.
10. Verify end-to-end against real multi-year market data for `BHARTIARTL.NS` and maintain scientific humility (no claim of commercial trading edge).

### Implementation
1. **Walk-Forward Cross-Validation Module (`app/training/walk_forward.py`):**
   - Implemented `WalkForwardFoldSplit`: Encapsulates fold index, train/embargo/val indices, start/end timestamps, sample sizes, class distributions, and `train_outcome_cutoff`.
   - Implemented `generate_walk_forward_splits()`: Generates $K$ chronological expanding-window folds with configurable initial training size (`n_initial_train`), fixed validation size (`val_size`), and mandatory outcome embargo (`embargo_size >= 1`). Verifies temporal ordering, expanding train windows, and zero index overlap.
   - Implemented `WalkForwardFoldEvaluation`: Captures per-fold evaluation metrics for all strategies, sample sizes, class counts, and status (`COMPLETED` or `SKIPPED_SINGLE_CLASS`).
   - Implemented `WalkForwardStrategySummary`: Holds macro-averaged metrics (mean $\pm$ sample standard deviation with Bessel correction $ddof=1$) and micro-pooled confusion matrices across all validation sessions.
   - Implemented `WalkForwardReport`: Container for all fold splits, fold evaluations, strategy summaries, and Markdown comparison table rendering (`.summary_table()`).
   - Implemented `evaluate_walk_forward()`: High-level orchestrator conducting fair, parallel evaluation across all 5 strategies on identical validation splits, with feature isolation checks and single-class guards.
2. **Package Exports (`app/training/__init__.py`):**
   - Exported `WalkForwardFoldSplit`, `WalkForwardFoldEvaluation`, `WalkForwardStrategySummary`, `WalkForwardReport`, `generate_walk_forward_splits`, `evaluate_walk_forward`.
3. **Application Entry Point Update (`main.py`):**
   - Added `print("Day 20 walk-forward temporal cross-validation ready")`.
4. **Real-Data Verification Script (`scripts/verify_day20.py`):**
   - End-to-end verification script for `BHARTIARTL.NS` across ~5 years, verifying fold boundaries, 1-session embargo invariants, class distributions, and comparative performance across all 5 strategies.

### Real Data Verification Results (BHARTIARTL.NS, 5-Year Lookback)
Executed `scripts/verify_day20.py` on real market data:
- **Symbol:** `BHARTIARTL`
- **Data Range:** 2021-10-14 to 2026-10-14 (1,235 total trading sessions)
- **Data Quality:** 1,235 clean bars (0 missing, 0 invalid, 0 duplicates).
- **Feature Matrix & Target Assembly:**
  - Initial Sessions: 1,235
  - Excluded Unlabeled Final Row: 1 ($y = NaN$, 2026-10-14)
  - Excluded Incomplete Warmup Rows: 35 (MACD-26, Bollinger-20, ATR-14, RSI-14)
  - Retained Complete Labeled Observations: **1,199**
- **Fold Configuration:**
  - Initial Train Window: 476 sessions (~40% of observations)
  - Validation Window: 144 sessions (~7 calendar months)
  - Embargo Gap: 1 session purged before each validation window
  - Generated Folds: **5 expanding folds** covering **720 total out-of-sample validation sessions**

#### Detailed Fold Partition & Leakage Integrity Breakdown
| Fold | Train Window | Train Size | Train UP / DOWN (Prior) | Embargo Date | Val Window | Val Size | Val UP / DOWN | Outcome Cutoff <= Val Start |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0** | 2021-12-03 to 2023-11-07 | 476 | 262 / 214 (55.04%) | 2023-11-08 | 2023-11-09 to 2024-06-11 | 144 | 76 / 68 (52.78%) | 2023-11-08 <= 2023-11-09 (**PASS**) |
| **1** | 2021-12-03 to 2024-06-11 | 621 | 338 / 283 (54.43%) | 2024-06-12 | 2024-06-13 to 2025-01-09 | 144 | 75 / 69 (52.08%) | 2024-06-12 <= 2024-06-13 (**PASS**) |
| **2** | 2021-12-03 to 2025-01-09 | 766 | 413 / 353 (53.92%) | 2025-01-10 | 2025-01-13 to 2025-08-14 | 144 | 81 / 63 (56.25%) | 2025-01-10 <= 2025-01-13 (**PASS**) |
| **3** | 2021-12-03 to 2025-08-14 | 911 | 494 / 417 (54.23%) | 2025-08-18 | 2025-08-19 to 2026-03-24 | 144 | 77 / 67 (53.47%) | 2025-08-18 <= 2025-08-19 (**PASS**) |
| **4** | 2021-12-03 to 2026-03-24 | 1054 | 571 / 483 (54.17%) | 2026-03-25 | 2026-03-26 to 2026-10-13 | 144 | 68 / 76 (47.22%) | 2026-03-25 <= 2026-03-26 (**PASS**) |

- **Outcome Embargo Invariant:** `train_outcome_cutoff <= val_start_date` was verified on 100% of folds (5 of 5).
- **Index Disjointness:** Confirmed $Train \cap Embargo = \emptyset$, $Embargo \cap Val = \emptyset$, and $Train \cap Val = \emptyset$ across all folds.

#### Walk-Forward Comparative Strategy Benchmark (5 Expanding Folds, N=720 Total Out-of-Sample Sessions)
| Strategy | Macro Accuracy (mean ± std) | Macro UP F1 (mean ± std) | Pooled Accuracy (720 sessions) | Pooled UP F1 | Pooled Confusion Matrix (TN, FP, FN, TP) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Majority Class** | **52.36% ± 2.53%** | **0.6870 ± 0.0210** | **52.36%** (377/720) | **0.6873** | `[[0, 343], [0, 377]]` |
| **Uniform Random** | 50.69% ± 5.71% | 0.5228 ± 0.0631 | 50.69% (365/720) | 0.5217 | `[[177, 166], [189, 188]]` |
| **Stratified Random** | 50.00% ± 5.53% | 0.5284 ± 0.0543 | 50.00% (360/720) | 0.5288 | `[[155, 188], [172, 205]]` |
| **XGBoost Classifier** | 50.69% ± 3.74% | 0.5342 ± 0.0639 | 50.69% (365/720) | 0.5330 | `[[170, 173], [182, 195]]` |
| **LightGBM Classifier**| 51.25% ± 5.16% | 0.5273 ± 0.0694 | 51.25% (369/720) | 0.5275 | `[[178, 165], [186, 191]]` |

#### Per-Fold Accuracy Progression
- **Fold 0 (Val 2023-11 to 2024-06):** Majority = 52.78% | Uniform = 56.94% | Stratified = 52.78% | XGBoost = 51.39% | LightGBM = 53.47%
- **Fold 1 (Val 2024-06 to 2025-01):** Majority = 52.08% | Uniform = 49.31% | Stratified = 52.78% | XGBoost = 54.17% | LightGBM = 56.94%
- **Fold 2 (Val 2025-01 to 2025-08):** Majority = 56.25% | Uniform = 49.31% | Stratified = 46.53% | XGBoost = 52.08% | LightGBM = 48.61%
- **Fold 3 (Val 2025-08 to 2026-03):** Majority = 53.47% | Uniform = 43.06% | Stratified = 43.06% | XGBoost = 44.44% | LightGBM = 44.44%
- **Fold 4 (Val 2026-03 to 2026-10):** Majority = 47.22% | Uniform = 54.86% | Stratified = 54.86% | XGBoost = 51.39% | LightGBM = 52.78%

### Core Methodological Insights & Audit Answers
1. **Did walk-forward cross-validation alter the single-holdout conclusion from Day 19?**
   - **YES, PROFOUNDLY.** In Day 19, on a single static 240-session holdout (2025-10 to 2026-10), both XGBoost (54.17%) and LightGBM (53.75%) outperformed the Majority-Class baseline (50.00%) because that specific test period happened to have an exact 50/50 balance.
   - Across the 5 expanding walk-forward folds (720 total out-of-sample sessions spanning 2023 to 2026), Bharti Airtel was in a broad secular upward trend during 2023–2024 (55% UP in training and 53–56% UP in Folds 0–3). Consequently, the simple **Majority-Class heuristic achieved 52.36% ± 2.53%**, whereas LightGBM achieved **51.25% ± 5.16%** and XGBoost achieved **50.69% ± 3.74%**.
2. **Did tree models exhibit consistent edge across all regimes?**
   - **NO.** In Folds 0, 1, and 4, tree models achieved 51.4%–56.9% accuracy. However, in Fold 3 (Aug 2025 to Mar 2026), both XGBoost and LightGBM dropped to 44.44%, while Majority Class held at 53.47%. This demonstrates regime sensitivity that a single holdout cannot detect.
3. **Did the 1-session embargo prevent target leakage?**
   - **YES.** On every fold, the training outcome cutoff was verified to be strictly less than or equal to the validation window start date. Zero next-session closing prices or forward returns leaked across boundaries.
4. **Is there any claim of commercial trading edge?**
   - **ABSOLUTELY NOT.** Directional accuracy near 51% across multiple cycles with high fold variability confirms that default, un-tuned gradient-boosted decision trees on raw technical features cannot produce a viable trading edge after slippage, STT, and execution friction. This empirically proves the necessity of multi-phase engineering (contextual LLM reasoning, macroeconomic factors, sentiment, and calibration).

### Tests
- Created `tests/test_walk_forward.py` with 12 comprehensive unit tests:
  1. `test_generate_walk_forward_splits_basic`: verifies correct fold counts, expanding training sizes, fixed validation sizes, and step progression.
  2. `test_embargo_gap_and_outcome_leakage_prevention`: verifies `train_outcome_cutoff <= val_start_date` across all folds.
  3. `test_pairwise_index_disjointness`: verifies zero overlap between train, embargo, and validation sets.
  4. `test_insufficient_samples_handling`: verifies explicit ValueError when total samples are insufficient for initial train and validation.
  5. `test_feature_matrix_isolation_in_walk_forward`: verifies that forbidden leak columns (`target_return_leak`) trigger an immediate ValueError via the isolation guard.
  6. `test_single_class_training_handling`: verifies safe handling and `SKIPPED_SINGLE_CLASS` status when historical training partition lacks variation.
  7. `test_reproducibility_of_random_baselines`: verifies 100% deterministic reproducibility across repeated evaluations with identical seeds.
  8. `test_dual_aggregation_math`: verifies hand-computed macro mean, Bessel sample standard deviation ($ddof=1$), and micro-pooled confusion matrix accumulation.
  9. `test_summary_table_generation`: verifies structured Markdown table output containing macro and pooled metrics for all strategies.
  10. `test_undersized_fold_safety`: verifies safe termination when remaining rows are fewer than validation size.
  11. `test_dataframe_and_series_compatibility`: verifies robust handling of both pandas DataFrames/Series and NumPy arrays.
  12. `test_regression_tree_models_in_walk_forward`: verifies end-to-end integration and execution of XGBoost and LightGBM inside the walk-forward evaluation loop.
- **Full Test Suite Results:**
  - Previous baseline: 243 passed
  - New total: **255 passed in 4.66s** (12 new walk-forward tests, 0 failures, 0 regressions). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit CLI tool is not installed in the local environment; reported accurately. Clean senior developer review conducted following Ponytail mode: type safety, mathematical invariants, zero code duplication, zero unnecessary dependencies, and safe edge-case handling.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Reused existing baseline classifiers, XGBoost, and LightGBM models without code modification. Shortest working diff, pure Python / NumPy metrics, explicit outcome embargo, and comprehensive automated test suite.

### Documentation
- Updated `README.md` to Day 20 status with 255 passing tests.
- Updated `docs/architecture.md` with Section 4.15 detailing Walk-Forward Temporal Cross-Validation Layer, expanding-window schema, and outcome embargo safeguards.
- Updated `docs/decisions.md` with ADR 48.
- Updated `docs/roadmap.md` with Day 20 completion details in Phase 4.
- Updated `docs/daily-progress.md` with Day 20 development log and empirical audit findings.

### Git Commit
- **Feature Commit:** `31a0132` — `feat: implement walk-forward temporal cross-validation with outcome embargo and comprehensive tests`
- **Documentation Commit:** `b0f0a5d` — `docs: record Day 20 walk-forward cross-validation log in daily-progress.md`

### Review & Remediation (CodeRabbit Findings in Walk-Forward Cross-Validation)
- **Finding 1 (Zero Dummy Metric Fabrication on Skipped Folds):**
  - *Analysis:* When a fold was skipped due to single-class training labels, `evaluate_walk_forward` computed dummy metrics using an all-zero prediction array, calculating and storing an arbitrary accuracy score. Furthermore, `fold_breakdown_table` and `summary_table` defaulted to `0.0%` for missing/skipped evaluations.
  - *Fix:* Made `WalkForwardFoldEvaluation.metrics` optional (`None` for skipped evaluations). Removed dummy metric computation. Updated table formatters to display `SKIP` or `N/A` rather than inventing accuracy values. Filtered only evaluated strategies (`folds_evaluated > 0`) when identifying best strategies.
- **Finding 2 (Input Validation & Target Label Integrity):**
  - *Analysis:* Input DataFrames missing `target_binary`, tuples with mismatched row/label counts, or target arrays containing NaNs or invalid non-binary labels (e.g. `2`, `-1`) could enter split generation undetected.
  - *Fix:* Added upfront checks in `generate_walk_forward_splits` enforcing `target_binary` presence in DataFrames, matching lengths in `(X, y)` tuples, absence of nulls/NaNs, and strict adherence of labels to $\{0, 1\}$.
- **Finding 3 (Consistent Parameter Defaults Across Code & Documentation):**
  - *Analysis:* Documentation previously referenced `n_initial_train=240` and `val_size=144`, whereas the code implementation dynamically calculates them via `min_train_ratio=0.4` and `n_splits=5`.
  - *Fix:* Reconciled parameter names and defaults across `app/training/walk_forward.py`, `docs/architecture.md`, `docs/decisions.md` (ADR 48), `docs/roadmap.md`, and `README.md`.
- **Finding 4 (Separate Handling of Undersized Folds vs Single-Class Folds):**
  - *Analysis:* Undersized partitions were conflated with single-class folds or raised late.
  - *Fix:* Implemented separate fault-tolerant checks in `evaluate_walk_forward`: partitions with $N_{train} < min\_train\_samples$ record `SKIPPED_UNDERSIZED_TRAIN`, partitions with $N_{val} < min\_val\_samples$ record `SKIPPED_UNDERSIZED_VAL`, and partitions lacking target variance record `SKIPPED_SINGLE_CLASS`, each with explicit sample-count reasons.
- **Finding 5 (Dynamic Invariant Validation in Verification Script):**
  - *Analysis:* `scripts/verify_day20.py` relied on a bare `assert` statement and printed hardcoded text without programmatically verifying the configured fold count and structural invariants.
  - *Fix:* Replaced bare assertions with explicit conditional error reporting (`file=sys.stderr`, return code 1). Added dynamic validation verifying that `len(report.folds) == n_splits`, indices are pairwise disjoint, training windows expand monotonically, and embargo sizing matches `embargo_sessions`.
- **Finding 6 (Regression Tests):**
  - Added 6 focused regression tests in `tests/test_walk_forward.py`:
    1. `test_walk_forward_no_fabricated_metrics_on_skipped_evaluation`
    2. `test_walk_forward_summary_table_unfitted_strategy_renders_na`
    3. `test_walk_forward_input_validation_missing_target_binary`
    4. `test_walk_forward_input_validation_tuple_length_mismatch`
    5. `test_walk_forward_input_validation_invalid_target_labels`
    6. `test_walk_forward_separate_handling_undersized_train_and_val`
  - **Full Test Suite:** **261 passed in 4.63s** (0 failures, 0 regressions). Zero external network dependencies.

### Known Limitations & Next Steps
- Walk-forward CV establishes that directional accuracy fluctuates between 44% and 57% across market regimes, averaging ~50.7% (XGBoost) and ~51.3% (LightGBM).
- Phase 4 baseline modeling is now complete. The numerical baseline models are established, verified, benchmarked against non-parametric heuristics, and audited across multi-year expanding folds without leakage.
- Next scheduled scope (Phase 5): Prediction Engine service layer orchestrating feature assembly, inference, confidence scoring, and output generation.




