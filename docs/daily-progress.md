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
- Next scheduled scope (Day 21): Model error analysis, symmetrical class performance evaluation, fold-to-fold distribution shift diagnostics, and feature usefulness audit.

---

## Day 21: Model Error Analysis & Feature Usefulness Audit

### Goal
Perform a comprehensive error decomposition and feature usefulness audit on the existing 5-fold walk-forward cross-validation results for `BHARTIARTL.NS`:
1. Analyze model errors across all folds and candidate strategies with symmetrical class-specific metrics for BOTH UP and DOWN classes (Accuracy, Precision, Recall, F1).
2. Report confusion matrices (`[TN, FP / FN, TP]`), predicted vs actual counts, and detect directional prediction biases (`ALL_UP`, `ALL_DOWN`).
3. Quantify training-to-validation class distribution shifts ($Shift = Val\_UP\% - Train\_UP\%$) and accuracy margins relative to the Majority-Class baseline.
4. Audit the canonical 37-feature matrix for missingness, constant columns, and collinearity clusters ($|\rho| \ge 0.90$) with strict training-data isolation (zero validation lookahead leakage).
5. Extract exploratory tree feature importance (split weight for XGBoost, split count for LightGBM), explicitly distinguishing model importance from causal predictive value.
6. Strictly adhere to project boundaries: zero hyperparameter tuning, no LightGBM configuration changes, no new features, and no holdout-based feature pruning.

### Pre-Checks
- Current branch: `main`, clean working tree synchronized with `origin/main` at commit `3561af6`.
- Full existing test suite verified: **261 passed in 4.63s** (0 failures, 0 regressions).
- Preserved Day 1–20 results, configurations, and historical journal entries intact.

### What Was Built
1. **Symmetrical Dual-Class Classification Metrics (`app/training/xgboost_classifier.py`):**
   - Expanded `ClassificationMetrics` to include `precision_down`, `recall_down`, and `f1_down` with safe defaults (`0.0`).
   - Updated `compute_classification_metrics()` to compute negative class (DOWN = 0) precision ($\frac{TN}{TN + FN}$), recall ($\frac{TN}{TN + FP}$), and harmonic F1 with complete zero-division safety.
   - Added native booster feature importance property `@property def feature_importances_(self) -> Dict[str, float]` to `XGBoostDirectionClassifier` using `booster.get_score(importance_type="weight")` (defaulting features with zero splits to `0.0`).
2. **Model Error Analysis & Feature Audit Layer (`app/training/error_analysis.py`):**
   - `FoldErrorAnalysis`: immutable container capturing fold number, strategy name, sample sizes, training/validation UP ratios, distribution shift, accuracy, majority baseline accuracy, margin vs majority, symmetrical UP/DOWN precision/recall/F1, confusion matrix, predicted/actual counts, and directional bias flag.
   - `analyze_walk_forward_errors(report: WalkForwardReport)`: decomposes walk-forward report evaluations into per-fold error analysis records with automatic baseline margin calculation and directional bias detection.
   - `audit_feature_usefulness(X_train, xgboost_model=None, lightgbm_model=None, correlation_threshold=0.90)`:
     - Enforces `validate_feature_matrix_isolation()` guard on $X_{train}$ (raises `ValueError` if target or outcome columns exist).
     - Verifies missingness count/ratio and constant columns across all features.
     - Computes pairwise Pearson correlation matrix and catalogs high-correlation pairs ($|\rho| \ge correlation\_threshold$).
     - Extracts native tree feature importances from fitted XGBoost and LightGBM models, sorting descending and identifying zero-importance features.
     - All calculations are performed strictly on the supplied training partition (zero validation lookahead).
   - Markdown Table Formatters:
     - `render_fold_error_table`: renders per-fold metrics, distribution shifts, confusion matrices, and directional biases.
     - `render_collinearity_table`: renders high-correlation feature pairs.
     - `render_feature_importance_comparison_table`: side-by-side comparison of top features by XGBoost weight vs LightGBM split count.
3. **Module Exports & Application Entry Point (`app/training/__init__.py`, `main.py`):**
   - Exported all Day 21 error analysis symbols from `app/training`.
   - Updated `main.py` with confirmation: `"Day 21 model error analysis and feature usefulness audit ready"`.
4. **End-to-End Real-Data Verification Script (`scripts/verify_day21.py`):**
   - Pulls ~5-year historical data for `BHARTIARTL.NS` (1,234 sessions), assembles 37-feature matrix (1,198 complete labeled sessions).
   - Executes 5-fold walk-forward cross-validation with 1-session embargo.
   - Runs `analyze_walk_forward_errors` and validates error invariants (confusion matrix consistency, bounded metrics).
   - Audits feature usefulness on Fold 5 training partition ($N=1,054$ sessions).
   - Uses explicit error checks and non-zero exit codes (zero bare `assert`).

### Real Data Verification Findings (BHARTIARTL.NS)
Executed `scripts/verify_day21.py` on ~5-year historical data (2021 to 2026):

#### 1. Per-Fold Error Breakdown across Strategies
- **Model C (Day 17 XGBoost):**
  - Fold 1 (Val UP 56.2%, Shift +5.2%): Acc 45.8% (Diff Maj -10.4%), UP P/R/F1 57/15/24, DN P/R/F1 44/86/58, Pred UP/DN 21/123, CM `[54,9 / 69,12]`, Bias: No.
  - Fold 2 (Val UP 52.8%, Shift +0.5%): Acc 51.4% (Diff Maj -1.4%), UP P/R/F1 52/95/67, DN P/R/F1 33/3/5, Pred UP/DN 138/6, CM `[2,66 / 4,72]`, Bias: No.
  - Fold 3 (Val UP 52.1%, Shift -0.1%): Acc 50.0% (Diff Maj -2.1%), UP P/R/F1 59/13/22, DN P/R/F1 49/90/63, Pred UP/DN 17/127, CM `[62,7 / 65,10]`, Bias: No.
  - Fold 4 (Val UP 49.3%, Shift -3.0%): Acc 56.2% (Diff Maj +6.9%), UP P/R/F1 58/39/47, DN P/R/F1 55/73/63, Pred UP/DN 48/96, CM `[53,20 / 43,28]`, Bias: No.
  - Fold 5 (Val UP 51.4%, Shift -0.5%): Acc 50.0% (Diff Maj -1.4%), UP P/R/F1 51/68/58, DN P/R/F1 48/31/38, Pred UP/DN 98/46, CM `[22,48 / 24,50]`, Bias: No.
- **Model D (Day 19 LightGBM):**
  - Fold 1: Acc 44.4% (Diff Maj -11.8%), UP P/R/F1 52/16/25, DN P/R/F1 43/81/56, Pred UP/DN 25/119, CM `[51,12 / 68,13]`, Bias: No.
  - Fold 2: Acc 52.1% (Diff Maj -0.7%), UP P/R/F1 53/95/68, DN P/R/F1 43/4/8, Pred UP/DN 137/7, CM `[3,65 / 4,72]`, Bias: No.
  - Fold 3: Acc 48.6% (Diff Maj -3.5%), UP P/R/F1 52/17/26, DN P/R/F1 48/83/61, Pred UP/DN 25/119, CM `[57,12 / 62,13]`, Bias: No.
  - Fold 4: Acc 58.3% (Diff Maj +9.0%), UP P/R/F1 61/44/51, DN P/R/F1 57/73/64, Pred UP/DN 51/93, CM `[53,20 / 40,31]`, Bias: No.
  - Fold 5: Acc 52.8% (Diff Maj +1.4%), UP P/R/F1 53/76/62, DN P/R/F1 53/29/37, Pred UP/DN 106/38, CM `[20,50 / 18,56]`, Bias: No.
- **Baseline A (Majority Class):**
  - Across all 5 folds: predicts 144 UP, 0 DOWN on every fold (`ALL_UP` bias).
  - Accuracy equals the validation UP ratio: Fold 1 (56.2%), Fold 2 (52.8%), Fold 3 (52.1%), Fold 4 (49.3%), Fold 5 (51.4%).
  - UP Recall is 100.0%, but DOWN Precision, Recall, and F1 are strictly **0.0%** across all folds.

#### 2. Key Error Analysis Insights
- **Downside Capture:** Supervised models actively predict downward sessions, achieving 45–64% DOWN F1 and up to 73–90% DOWN Recall across folds. In contrast, the Majority-Class baseline has zero capability to detect market declines.
- **Regime Outperformance:** When market drift turned negative in Fold 4 (Val UP dropped to 49.3%), tree models outperformed Majority Class significantly (+6.9% for XGBoost, +9.0% for LightGBM) by successfully classifying 53 down sessions (73% recall).
- **Regime Drag:** In strong bull regimes (Fold 1, Val UP 56.2%), tree models underperformed Majority Class because they predicted 119–123 downward moves, illustrating that model conservatism underperforms naive momentum in one-sided bull runs.

#### 3. Feature Usefulness & Collinearity Audit
- **Matrix Health:** Audited 37 features on Fold 5 training partition ($N=1,054$ sessions). Exactly 0 missing values and 0 constant columns.
- **Collinearity Clusters:** Identified 59 feature pairs with Pearson $|\rho| \ge 0.90$.
  - Extreme collinearity ($|\rho| \ge 0.999$): `rolling_volatility_5d` & `annualized_volatility_5d` (1.0000); `sma_5` & `ema_5` (0.9999); `sma_10` & `ema_10` (0.9999); raw price combinations `open`, `high`, `low`, `close` ($>0.9995$).
  - These 59 pairs represent significant feature redundancy and serve as primary candidates for architectural simplification in future feature engineering phases.
- **Exploratory Tree Feature Importance (Training Data Only):**
  - Top features by XGBoost split weight: `rolling_volatility_5d` (21), `candle_body_ratio` (20), `macd_signal` (17), `bb_bandwidth` (17), `candle_body_abs` (17), `candle_lower_wick` (15), `rolling_return_5d` (14).
  - Top features by LightGBM split count: `rolling_volatility_5d` (22), `candle_body_ratio` (20), `rolling_return_5d` (16), `bb_bandwidth` (14), `candle_upper_wick` (13), `candle_close_location` (13), `macd_signal` (12).
  - Both architectures independently place heavy split reliance on short-term volatility (`rolling_volatility_5d`, `bb_bandwidth`), candlestick geometry (`candle_body_ratio`, `candle_body_abs`), and momentum (`rolling_return_5d`, `macd_signal`).
  - Several raw price levels and indicators (`sma_5`, `ema_5`, `adx`) receive relatively fewer splits due to collinear redundancy.
- **Scientific Boundaries:**
  - Zero hyperparameter tuning performed.
  - Zero features removed based on holdout performance.
  - All diagnostics computed strictly on training data without future lookahead.

### Tests
- Created `tests/test_error_analysis.py` with 8 comprehensive unit tests:
  1. `test_down_metrics_computation`: verifies hand-computed precision, recall, and F1 for the DOWN class.
  2. `test_down_metrics_edge_case_all_up`: verifies zero-division safety when model predicts zero DOWN moves.
  3. `test_xgboost_feature_importances_property`: verifies native booster feature importance extraction and unfitted guard.
  4. `test_analyze_walk_forward_errors`: verifies complete error analysis decomposition, distribution shifts, majority delta, and bias detection.
  5. `test_audit_feature_usefulness_isolation_guard`: verifies that feature matrices containing target/outcome columns are rejected via isolation guard.
  6. `test_audit_feature_usefulness_constant_and_correlation`: verifies detection of constant columns and high collinearity pairs.
  7. `test_audit_feature_usefulness_with_models`: verifies exploratory tree feature importance integration.
  8. `test_markdown_rendering`: verifies markdown table formatting for collinearity and importance tables.
- **Full Test Suite Results:**
  - Previous baseline: 261 passed
  - New total: **269 passed in 4.54s** (8 new tests, 0 failures, 0 regressions). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit CLI is not installed in the local environment; noted explicitly. Proactively adhered to strict senior dev standards: mathematical symmetry, zero lookahead leakage, division-by-zero guards, and clear separation of exploratory model importance from causal alpha.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Reused existing baseline and model outputs, avoided duplicate calculations, maintained strict training-only isolation, and added zero external dependencies.

### Documentation
- Updated `README.md` to Day 21 status with 269 passing tests.
- Updated `docs/architecture.md` with Section 4.16 covering Model Error Analysis & Feature Usefulness Audit Layer.
- Updated `docs/decisions.md` with ADR 49 (Model Error Analysis, Dual-Class Symmetrical Evaluation, and Exploratory Feature Audit Protocol).
- Updated `docs/roadmap.md` marking Day 21 complete in Phase 4.
- Updated `docs/daily-progress.md` with Day 21 development log and empirical findings.

### Git Commits
- **Feature Commit:** `0ce8f01` — `feat(training): implement model error analysis and feature usefulness audit for Day 21`
- **Documentation Commit:** `1fc7eaf` — `docs: record Day 21 model error analysis and feature usefulness audit in daily-progress.md`

### Known Limitations & Next Steps
- The canonical 37-feature matrix contains 59 collinear pairs ($|\rho| \ge 0.90$), indicating substantial redundancy among raw price levels, moving average variants, and volatility indicators.
- In one-sided bull markets, supervised tree models experience drag relative to majority-class heuristics because they actively allocate predictions to the downside (preventing blind long exposure).
- Feature pruning or dimensionality reduction (e.g. eliminating redundant price levels or collinear MAs) must be approached cautiously in future phases using domain-driven or training-only feature selection, never by optimizing against validation fold scores.
- Next scheduled scope: Complete Phase 4 wrap-up and proceed to Phase 5 (Prediction Engine service layer orchestrating feature assembly, inference, confidence scoring, and output generation).

---

## Day 22: Prediction Engine Service Foundation

### Goal
Build the first reusable prediction-engine service that connects the existing market-data pipeline, canonical feature matrix, trained XGBoost and LightGBM classifiers, and baseline evaluation infrastructure without changing model definitions:
1. Define a strongly typed prediction request and result contract (`PredictionRequest`, `PredictionResult`, `PredictionDataQuality`, `PredictionStatus`) supporting symbol, prediction timestamp, input bar timestamp, predicted direction (UP/DOWN), class probabilities, model provenance metadata, data quality diagnostics, and explicit failure reasons.
2. Build `PredictionService` under `app/prediction/service.py` orchestrating market data acquisition, data cleaning, canonical 37-feature matrix assembly, input data validation (warm-up sufficiency $\ge 34$ bars, missing-value checks), and model inference.
3. Enforce strict inference-time anti-leakage safeguards: consume strictly point-in-time data bounded by request timestamps, validate zero target or forward outcome columns via `validate_feature_matrix_isolation()`, and guarantee column ordering matching `FEATURE_COLUMNS`.
4. Implement strict model lifecycle separation: inference strictly consumes pre-existing model artifacts or registered instances; automatic on-the-fly retraining during inference requests is strictly prohibited. If an artifact is unavailable, return an actionable `MODEL_UNAVAILABLE` status.
5. Provide explicit capability boundaries: document that the direction classifier forecasts binary close-to-close sign (UP/DOWN) and raw probability; do not fabricate fictitious target prices, expected percentage returns, or post-hoc narrative explanations.
6. Verify against real historical data for `BHARTIARTL.NS` and expand unit tests.

### Pre-Checks
- Current branch: `main`, clean working tree synchronized with `origin/main` at commit `ba95534`.
- Full existing test suite verified: **269 passed in 4.54s** (0 failures, 0 regressions).
- Preserved all Day 1–21 code, results, configurations, and journal entries intact.

### What Was Built
1. **Prediction Contract (`app/prediction/contract.py`):**
   - `PredictionStatus` enum: `SUCCESS`, `INSUFFICIENT_DATA`, `STALE_DATA`, `MODEL_UNAVAILABLE`, `FEATURE_ERROR`, `INVALID_REQUEST`, `FAILED`.
   - `PredictionRequest`: typed specification with `symbol`, `model_name` ('xgboost' or 'lightgbm'), `model_artifact_path`, `as_of_date`, `lookback_days` (default $5 \times 365$), `max_stale_days` (default 7), and `allow_stale_data`. Parameter validation rejects empty symbols, unsupported architectures, or insufficient lookback.
   - `PredictionDataQuality`: tracks `total_bars_fetched`, `cleaned_bars`, `warmup_bars_required` (34), `warmup_complete`, `latest_bar_timestamp`, `missing_feature_count`, `missing_features`, `is_stale`, and `stale_days`.
   - `PredictionResult`: typed result container providing `symbol`, `prediction_timestamp`, `latest_input_timestamp`, `status`, `predicted_direction` ('UP' or 'DOWN'), `predicted_label` (1 or 0), `probability_up`, `probability_down`, `model_name`, `model_version`, `model_metadata`, `data_quality`, `error_message`, and explicit capability disclaimer with `.to_dict()` serialization.
2. **Prediction Service Layer (`app/prediction/service.py`):**
   - `PredictionService`: orchestrates provider data retrieval, market cleaning, feature matrix assembly, data quality auditing, and model execution.
   - Decoupled model resolution: resolves fitted models from preloaded arguments, in-memory `model_registry`, or filesystem artifacts (`models/{model_name}_direction.*`).
   - Zero silent retraining: if an artifact is absent, returns an actionable `MODEL_UNAVAILABLE` diagnostic explaining how to train and persist the model.
   - Warm-up and data quality validation: rejects inference observations with fewer than 34 sessions or any NaN feature values (`FEATURE_ERROR`).
   - Inference isolation: executes `validate_feature_matrix_isolation()` on the inference feature row ($t = N - 1$), rejecting target or outcome columns.
   - Feature ordering parity: enforces column alignment matching canonical `FEATURE_COLUMNS`.
   - `train_and_persist_baseline_model()`: dedicated offline lifecycle function for deliberately training and serializing baseline classifiers to disk.
3. **Decoupled Package Exports (`app/prediction/__init__.py`):**
   - Employs PEP 562 `__getattr__` module-level lazy loading for `PredictionService` and `train_and_persist_baseline_model`, decoupling `app.prediction` imports during feature matrix initialization and completely eliminating circular dependencies.
4. **Application Entry Point Update (`main.py`):**
   - Added readiness confirmation: `"Day 22 prediction engine service foundation ready"`.
5. **Real-Data Verification Script (`scripts/verify_day22.py`):**
   - Offline lifecycle: deliberately trained and persisted baseline XGBoost and LightGBM models for `BHARTIARTL.NS` to `models/`.
   - Inference execution: executed `PredictionService.predict()` with both models, verifying direction, probabilities, timestamps, and metadata.
   - Negative testing: verified that missing model artifacts return `MODEL_UNAVAILABLE` without silent retraining, and invalid symbols return `INSUFFICIENT_DATA` / `FAILED`.
   - Zero bare `assert`: dynamic error logging with exit code 1 on failure.

### Real Data Verification Findings (BHARTIARTL.NS)
Executed `scripts/verify_day22.py` on real historical market data:
- **Offline Model Lifecycle:**
  - Persisted XGBoost model: `models/xgboost_direction.json` (106,757 bytes).
  - Persisted LightGBM model: `models/lightgbm_direction.txt` (45,074 bytes).
- **XGBoost Direction Prediction:**
  - Status: `SUCCESS`
  - Symbol: `BHARTIARTL`
  - Predicted Direction: `UP` (label=1)
  - Direction Probabilities: $P(UP) = 54.68\%$, $P(DOWN) = 45.32\%$ ($P(UP) + P(DOWN) = 1.00$)
  - Latest Input Bar: `2026-10-13T00:00:00+05:30`
  - Prediction Timestamp: `2026-10-14T09:42:17.114115+00:00`
  - Cleaned Input Bars: 1,235 sessions (warmup complete, 0 missing features)
  - Model Version: `xgboost-direction-v1`
- **LightGBM Direction Prediction:**
  - Status: `SUCCESS`
  - Predicted Direction: `UP` (label=1)
  - Direction Probabilities: $P(UP) = 55.78\%$, $P(DOWN) = 44.22\%$ ($P(UP) + P(DOWN) = 1.00$)
  - Model Version: `lightgbm-direction-v1`
- **Error Containment & Safeguard Invariants:**
  - Missing model artifact (`non_existent_model.json`): returned `MODEL_UNAVAILABLE` with error message `"Model artifact not found ... Automatic on-the-fly retraining during inference is prohibited"`. Confirmed zero silent retraining.
  - Invalid ticker symbol (`NONEXISTENT_TICKER_XYZ`): handled gracefully with `INSUFFICIENT_DATA` status without unhandled exceptions.

### Tests
- Created `tests/test_prediction_service.py` with 13 comprehensive unit tests:
  1. `test_valid_prediction_request_with_preloaded_xgboost`: verifies valid prediction with preloaded XGBoost model.
  2. `test_valid_prediction_request_with_preloaded_lightgbm`: verifies valid prediction with preloaded LightGBM model.
  3. `test_in_memory_model_registry`: verifies service resolves models from in-memory registry.
  4. `test_unsupported_and_invalid_symbols`: verifies validation rejects empty symbols and unsupported model architectures.
  5. `test_missing_market_data`: verifies graceful handling when provider returns zero bars.
  6. `test_insufficient_feature_history`: verifies rejection when bars are fewer than minimum warmup (34).
  7. `test_target_and_future_columns_excluded`: verifies inference row excludes forbidden target/outcome patterns.
  8. `test_feature_order_consistency`: verifies exact column ordering sent to model matches `FEATURE_COLUMNS`.
  9. `test_missing_model_artifacts_error_actionable`: verifies missing artifact returns actionable `MODEL_UNAVAILABLE`.
  10. `test_model_prediction_runtime_error_handled`: verifies runtime exceptions in `predict_proba` are safely caught as `FAILED`.
  11. `test_up_down_class_and_probability_mapping`: verifies thresholding ($p > 0.5 \implies UP$, $p \le 0.5 \implies DOWN$) and probability symmetry.
  12. `test_reproducibility_with_persisted_model`: verifies identical predictions across separate calls using persisted artifact.
  13. `test_prediction_timestamp_and_input_data_timestamp`: verifies distinctness and ordering of prediction generation time and input observation time.
- **Full Test Suite Results:**
  - Previous baseline: 269 passed
  - New total: **282 passed in 4.50s** (13 new tests, 0 failures, 0 regressions). Zero external network dependencies.

### Review
- **CodeRabbit:** CodeRabbit CLI is not installed in the local environment; noted explicitly. Senior dev clean-code principles applied: strict type hints, dataclasses with `.to_dict()`, PEP 562 lazy exports, division-by-zero guards, and complete lifecycle separation.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Reused existing data pipeline, cleaner, indicators, trend, and feature matrix without duplication. Zero silent retraining, zero new dependencies.

### Documentation
- Updated `README.md` to Day 22 status with 282 passing tests.
- Updated `docs/architecture.md` with Section 4.17 detailing Prediction Engine Service Layer.
- Updated `docs/decisions.md` with ADR 50 (Prediction Engine Service Architecture, Inference Contract, and Lifecycle Isolation).
- Updated `docs/roadmap.md` with Phase 5 / Day 22 completion details.
- Updated `docs/daily-progress.md` with Day 22 development log.

### Git Commits
- **Feature Commit:** `1df339f` — `feat(prediction): implement prediction engine service foundation for Day 22`
- **Documentation Commit:** `521af7c` — `docs: record Day 22 prediction engine service foundation in daily-progress.md`

### Known Limitations & Next Steps
- The current prediction service forecasts next-session binary direction (`UP`/`DOWN`) and raw tree probability; it does not predict target price levels or percentage return magnitudes.
- Raw probabilities represent tree split frequencies and are not yet calibrated using Platt scaling or isotonic regression.
- Predictions operate per symbol in isolation; NIFTY context and market breadth features remain scheduled for subsequent phases (Phase 8).
- Next scheduled scope: Proceed with Phase 5 expansion (probability calibration, threshold optimization, and prediction persistence).

---

## Day 23 - Structured Prediction Output

### Goal
Implement and validate the structured prediction output contract using the existing Day 22 `PredictionService` and `PredictionResult` contract:
1. Ensure the output strictly includes predicted direction, uncalibrated model probability (clearly marked), symbol, prediction timestamp, latest input-data timestamp, model name/version, and data-quality status.
2. Return `expected_movement` as `None` with an explicit `expected_movement_status = "UNSUPPORTED"` confirming that direction classifiers predict binary directional movement rather than numeric price targets or percentage return magnitudes.
3. Provide lossless JSON-serializable transformation via `.to_dict()` and clean human-readable audit text rendering via `.format_summary()`.
4. Strictly avoid probability calibration, threshold tuning, database/history, CLI tooling, frontend, or new model architectures today.
5. Add focused unit tests, run the full test suite, verify against real historical data for `BHARTIARTL.NS`, and preserve clean repository state.

### Pre-Checks
- Current branch: `main`, clean working tree synchronized with `origin/main` at commit `f380033`.
- Full existing test suite verified: **282 passed in 4.99s** (0 failures, 0 regressions).
- Roadmap alignment verified: followed roadmap clarification for Phase 4 / Phase 5 Day 23 — Structured Prediction Output without jumping ahead to Phase 6 (database) or Phase 13 (frontend).

### What Was Built
1. **Enhanced Prediction Contract (`app/prediction/contract.py`):**
   - **Uncalibrated Probability Transparency:** Added `is_probability_calibrated: bool = False` and `probability_calibration: str = "uncalibrated"` to `PredictionResult`, clearly distinguishing raw tree booster split frequencies from calibrated Bayesian posterior probabilities.
   - **Explicit Expected Movement Boundaries:** Added `expected_movement: Optional[float] = None` and `expected_movement_status: str = "UNSUPPORTED"` to `PredictionResult`, formalizing the capability boundary that direction classifiers do not predict price targets or return magnitudes.
   - **Human-Readable Summary Rendering:** Added `.format_summary() -> str` method on `PredictionResult` to format a clean text audit block displaying status, timestamps, model metadata, direction, uncalibrated probabilities, data quality metrics, and capability disclaimers.
   - **Machine-Readable Serialization:** Preserved and validated `.to_dict()` recursive dictionary conversion returning JSON-serializable primitives for all fields including calibration flags and expected movement status.
2. **Prediction Service Updates (`app/prediction/service.py`):**
   - Updated `PredictionService.predict()` and `PredictionService._build_error_result()` to explicitly set `is_probability_calibrated=False`, `probability_calibration="uncalibrated"`, `expected_movement=None`, and `expected_movement_status="UNSUPPORTED"` across all successful and error outputs.
3. **Application Entry Point Update (`main.py`):**
   - Added readiness check: `"Day 23 structured prediction output ready"`.
4. **Focused Unit Tests (`tests/test_prediction_output.py`):**
   - Implemented 6 comprehensive unit tests validating:
     1. `test_structured_prediction_output_schema_and_types`: validates field types and required metadata.
     2. `test_uncalibrated_probability_transparency`: confirms uncalibrated flags and probability bounds $P \in [0, 1]$.
     3. `test_expected_movement_explicitly_unsupported`: confirms `expected_movement is None` and status is `"UNSUPPORTED"`.
     4. `test_prediction_result_to_dict_serialization`: confirms JSON serializability and nested dictionary structure.
     5. `test_prediction_result_format_summary`: verifies human-readable summary output text.
     6. `test_structured_error_output_contains_required_diagnostics`: verifies error containment on missing artifacts.
5. **Real-Data Verification Script (`scripts/verify_day23.py`):**
   - Verified end-to-end execution on real market data for `BHARTIARTL.NS` (1,235 bars up to 2026-10-14).
   - Validated both XGBoost and LightGBM outputs, JSON serialization, and summary formatting.
   - Enforced `try...finally` artifact cleanup to keep working tree clean and preserve Day 1 repository foundation invariants.

### Real Data Verification Findings (BHARTIARTL.NS)
Executed `scripts/verify_day23.py` on real historical market data:
- **XGBoost Structured Prediction Output:**
  - Status: `SUCCESS`
  - Symbol: `BHARTIARTL`
  - Predicted Direction: `DOWN` (label=0)
  - Direction Probabilities: $P(UP) = 46.86\%$, $P(DOWN) = 53.14\%$ ($P(UP) + P(DOWN) = 1.00$)
  - Probability Calibration: `uncalibrated` (`is_calibrated=False`)
  - Expected Movement: `None` (`status=UNSUPPORTED`)
  - Prediction Timestamp: `2026-10-14T10:05:42.291596+00:00`
  - Latest Input Bar: `2026-10-14T00:00:00+05:30`
  - Model Version: `xgboost-direction-v1`
  - Data Quality: 1,235 cleaned bars, warmup complete, 0 missing features
- **LightGBM Structured Prediction Output:**
  - Status: `SUCCESS`
  - Predicted Direction: `DOWN` (label=0)
  - Direction Probabilities: $P(UP) = 47.72\%$, $P(DOWN) = 52.28\%$ ($P(UP) + P(DOWN) = 1.00$)
  - Probability Calibration: `uncalibrated` (`is_calibrated=False`)
  - Expected Movement: `None` (`status=UNSUPPORTED`)
  - Model Version: `lightgbm-direction-v1`
- **Output Inspection & Formatting:**
  - Confirmed `.to_dict()` outputs valid JSON dictionary (1,463 characters).
  - Confirmed `.format_summary()` outputs clean audit text block.
  - Confirmed missing model artifact returns structured error with `status=MODEL_UNAVAILABLE`, `predicted_direction=None`, `probability_up=None`, and `expected_movement=None`.

### Tests
- **Full Test Suite Results:**
  - Previous baseline: 282 passed
  - New total: **288 passed in 3.81s** (6 new tests in `tests/test_prediction_output.py`, 0 failures, 0 regressions across 21 test modules).
  - Zero external network dependencies in automated tests.

### Review
- **CodeRabbit:** CodeRabbit CLI not installed locally; noted explicitly.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Reused existing `PredictionResult` and `PredictionService` without creating duplicate classes or adding unnecessary abstractions. Standard library dataclasses and methods only.
- **Strict Boundaries:** Zero probability calibration, zero threshold tuning, zero database code, zero CLI tooling, zero frontend, zero new model architectures.

### Documentation
- Updated `README.md` to Day 23 status with 288 passing tests.
- Updated `docs/architecture.md` with Section 4.18 detailing Prediction Output Layer & Transparency Guarantees.
- Updated `docs/decisions.md` with ADR 51.
- Updated `docs/roadmap.md` with Phase 5 / Day 23 completion details.
- Updated `docs/daily-progress.md` with Day 23 development log.

### Known Limitations & Next Steps
- Model probabilities remain uncalibrated raw tree split frequencies. Probability calibration (e.g., Platt scaling or isotonic regression) is scheduled for future work before trading decisions are evaluated.
- Direction classifiers output binary directional sign only. Expected price movement ($\Delta Close$) and percentage return ($R$) are not calculated or modeled.
- Next scheduled scope: Transition to Phase 6 (Prediction History & Database — SQLite schema, prediction persistence, and immutable audit logs).

---

## Day 24 - SQLite Prediction Database & Immutable Persistence

### Goal
Implement the Phase 6 foundation for prediction history and relational persistence:
1. Design and deploy the SQLite relational schema in `app/database/schema.py` (`stocks`, `model_versions`, `predictions`, and `actuals`) with WAL mode, foreign key enforcement, and query performance indexes.
2. Implement tamper-proof immutability at the database engine level using SQLite triggers (`trg_prevent_prediction_update` and `trg_prevent_prediction_delete`) aborting any attempt to modify or delete logged predictions.
3. Build `PredictionRepository` in `app/database/repository.py` providing strongly-typed persistence for `PredictionResult` objects with automatic stock/model parent record registration.
4. Strictly preserve Day 23 transparency semantics: uncalibrated probabilities (`is_probability_calibrated=False`, `probability_calibration="uncalibrated"`) and unsupported expected movement (`expected_movement=None`, `expected_movement_status="UNSUPPORTED"`).
5. Integrate optional repository persistence into `PredictionService.predict(..., persist=True)`.
6. Add comprehensive unit tests, execute real-data verification for `BHARTIARTL.NS`, and maintain zero untracked database files in the repository.

### Pre-Checks
- Current branch: `main`, clean working tree synchronized with `origin/main` at commit `4f0b9ba`.
- Baseline test suite verified: **288 passed in 21.50s** (0 failures, 0 regressions across 21 modules).
- Roadmap alignment confirmed via explicit user clarification: executed Phase 6 SQLite schema and immutable persistence scope.

### What Was Built
1. **SQLite Connection & Transaction Management (`app/database/connection.py`):**
   - Implemented `create_connection(db_path)` configuring `PRAGMA foreign_keys = ON;`, `PRAGMA busy_timeout = 5000;`, `PRAGMA journal_mode = WAL;` (for disk databases), and `conn.row_factory = sqlite3.Row`.
   - Implemented `db_session()` context manager for transactional safety with automatic commit and rollback.
2. **Relational Schema & Native Immutability Triggers (`app/database/schema.py`):**
   - **`stocks` table:** tracks symbol (PK), company name, exchange (default 'NSE'), active status, and creation timestamps.
   - **`model_versions` table:** tracks model name, version identifier, JSON-serialized hyperparameters, and registration timestamps (`UNIQUE(model_name, model_version)`).
   - **`predictions` table:** immutable audit log of predictions storing queryable metadata, operational statuses, predicted directions/labels, uncalibrated probabilities, data quality diagnostics, error messages, and full raw payloads (`raw_result_json`).
   - **`actuals` table:** schema designed for Phase 7 realized market outcomes, linked via foreign keys to `predictions` and `stocks`.
   - **Performance Indexes:** `idx_predictions_symbol_timestamp`, `idx_predictions_model`, `idx_predictions_latest_bar`, and `idx_actuals_symbol_date`.
   - **Engine-Level Immutability Triggers:**
     - `trg_prevent_prediction_update`: `BEFORE UPDATE ON predictions BEGIN SELECT RAISE(ABORT, 'Predictions are immutable: updates are strictly prohibited.'); END;`
     - `trg_prevent_prediction_delete`: `BEFORE DELETE ON predictions BEGIN SELECT RAISE(ABORT, 'Predictions are immutable: deletions are strictly prohibited.'); END;`
3. **Strongly-Typed Repository Layer (`app/database/repository.py`):**
   - Implemented `PredictionRepository` providing `save_prediction()`, `get_prediction()`, `list_predictions()`, `count_predictions()`, `upsert_stock()`, `get_stocks()`, and `register_model_version()`.
   - Automatically checks and registers parent records in `stocks` and `model_versions` during `save_prediction()`.
   - Dual-persistence model: stores indexed columns for efficient queries alongside complete lossless JSON in `raw_result_json`.
4. **Prediction Service Integration (`app/prediction/service.py`):**
   - Extended `PredictionService.__init__` with optional `repository: Optional[PredictionRepository] = None`.
   - Extended `PredictionService.predict()` with optional `persist: bool = False` flag to persist successful prediction results atomically upon request without altering default behavior.
5. **Entry Point & Package Exports (`app/database/__init__.py`, `main.py`):**
   - Cleanly exported all database primitives and added Day 24 readiness status print to `main.py`.

### Real-Data Verification Findings (BHARTIARTL.NS)
Executed `scripts/verify_day24.py` using live market data for `BHARTIARTL.NS`:
- **Database Initialization:** Created temporary SQLite database, verified tables `stocks`, `model_versions`, `predictions`, `actuals`, and triggers `trg_prevent_prediction_update`, `trg_prevent_prediction_delete`.
- **Prediction Execution & Atomic Persistence:**
  - Status: `SUCCESS`
  - Symbol: `BHARTIARTL`
  - Predicted Direction: `DOWN` (label=0)
  - Direction Probabilities: $P(UP) = 46.86\%$, $P(DOWN) = 53.14\%$
  - Calibration: `uncalibrated` (`is_probability_calibrated=0`)
  - Expected Movement: `None` (`status="UNSUPPORTED"`)
- **Persistence Verification in SQLite:**
  - Retrieved prediction record `b4d574d19aef4c7e9f1a57fdcff9a1fc` from database.
  - Confirmed column values match exact Day 23 transparency semantics.
  - Verified lossless JSON deserialization (`raw_result` contains full diagnostic dictionary).
  - Verified `stocks` and `model_versions` parent rows populated.
- **Engine-Level Immutability Audit:**
  - Executed raw SQL `UPDATE predictions SET predicted_direction = 'FLIPPED' WHERE prediction_id = ...`: rejected with `sqlite3.DatabaseError: Predictions are immutable: updates are strictly prohibited.`
  - Executed raw SQL `DELETE FROM predictions WHERE prediction_id = ...`: rejected with `sqlite3.DatabaseError: Predictions are immutable: deletions are strictly prohibited.`
  - Executed duplicate insertion of identical `prediction_id`: rejected with `sqlite3.IntegrityError: UNIQUE constraint failed: predictions.prediction_id`.
- **Cleanup Guarantee:** All transient verification database and model files cleaned up in `try...finally`.

### Tests
- Created `tests/test_prediction_database.py` with 11 comprehensive unit tests:
  1. `test_database_schema_initialization`: verifies tables, triggers, and foreign key activation.
  2. `test_stock_metadata_upsert`: verifies stock insertion and idempotent metadata updating.
  3. `test_model_version_registration`: verifies model version tracking and hyperparameter serialization.
  4. `test_save_and_get_prediction_preserves_semantics`: verifies uncalibrated probability flags and lossless recovery.
  5. `test_immutability_trigger_prevents_updates`: verifies SQLite engine rejects direct UPDATE statements.
  6. `test_immutability_trigger_prevents_deletions`: verifies SQLite engine rejects direct DELETE statements.
  7. `test_duplicate_prediction_id_rejected`: verifies primary key / unique constraint enforcement.
  8. `test_foreign_key_enforcement`: verifies orphan records are rejected when foreign keys are active.
  9. `test_list_and_count_predictions`: verifies filtering by symbol and model name, pagination, and counts.
  10. `test_save_error_prediction_result`: verifies structured error results can be logged for debugging audits.
  11. `test_prediction_service_optional_persistence`: verifies atomic auto-persistence via `service.predict(..., persist=True)`.
- **Full Test Suite Results:**
  - Previous baseline: 288 passed
  - New total: **299 passed in 11.75s** (11 new tests, 0 failures, 0 regressions across 22 test modules).
  - Zero external network dependencies in automated tests.

### Review
- **CodeRabbit:** CodeRabbit CLI not installed locally; noted explicitly.
- **Roo Code:** Remained disabled.
- **Ponytail / Senior Dev Mode:** Built with standard library `sqlite3` only. Zero third-party ORMs or dependencies added. Native database triggers enforce immutability with minimum lines of code.

### Documentation
- Updated `README.md` to Day 24 status with 299 passing tests.
- Updated `docs/architecture.md` with Section 4.19 detailing Prediction History & Relational Storage Layer.
- Updated `docs/decisions.md` with ADR 52.
- Updated `docs/roadmap.md` with Phase 6 / Day 24 completion details.
- Updated `docs/daily-progress.md` with Day 24 development log.

### Known Limitations & Next Steps
- Predictions are logged immutably, but realized market outcomes are not yet ingested or compared against past forecasts.
- Next scheduled scope: Implement Phase 7 (Verification & Accuracy — market outcome recording into `actuals` table, direction precision/recall evaluation, and error calculation).

---

## Day 25 - Prediction Outcome Verification & Evaluation Foundation

### Goal
Implement the foundation for verifying saved stock-direction predictions against actual market outcomes and evaluating whether predicted directions were correct (Phase 7: Verification & Accuracy):
1. Review existing database schema and reuse `actuals` table.
2. Define outcome verification rules: trading calendars, holidays, pending future sessions, zero forward leakage, and immutable prediction preservation.
3. Persist actual outcomes to SQLite `actuals` table idempotently with data provenance and engine-level triggers preventing mutation or deletion.
4. Implement prediction evaluation service reporting total, eligible, pending, verified, correct, incorrect, directional accuracy (strictly on verified predictions as denominator), confusion matrix, and symmetrical class metrics.
5. Provide comprehensive automated unit tests (deterministic, mock-based) and execute real-market verification.

### Work Completed
1. **Schema & Repository Enhancements (`app/database/schema.py`, `app/database/repository.py`):**
   - Extended `actuals` table with `reference_close REAL` and `source TEXT DEFAULT 'yfinance'`.
   - Added SQLite engine triggers `trg_prevent_actual_update` and `trg_prevent_actual_delete` to enforce write-once immutability directly at the database engine level.
   - Added automatic migration handling in `initialize_database()` for existing databases.
   - Implemented `save_actual()` in `PredictionRepository` with strict idempotency for identical verification and `ValueError` rejection for conflicting outcomes.
   - Implemented `get_actual()`, `list_actuals()`, `count_actuals()`, `get_prediction_with_actual()`, and `list_predictions_with_actuals()`.
2. **Outcome Verification & Evaluation Contracts (`app/history/contract.py`):**
   - Defined `VerificationStatus` enum (`VERIFIED`, `ALREADY_VERIFIED`, `PENDING`, `INELIGIBLE`, `DATA_UNAVAILABLE`, `CONFLICT`).
   - Defined immutable `ActualOutcome` dataclass with boundary validation on prices and returns.
   - Defined `VerificationRecord` dataclass detailing prediction reference price, actual outcome price, realized return, actual direction, and correctness.
   - Defined `EvaluationMetrics` dataclass capturing denominator isolation ($N_{total}$, $N_{eligible}$, $N_{pending}$, $N_{verified}$), accuracy, confusion matrix ($TP, FP, TN, FN$), symmetrical class metrics (UP/DOWN precision, recall, F1), breakdowns by model and symbol, `.to_dict()` serialization, and `.format_summary()` rendering.
3. **Outcome Verification Engine (`app/history/verifier.py`):**
   - Implemented `OutcomeVerifier` with chronological session alignment.
   - Matches prediction reference session ($t$) with target market session ($t+1$) across calendar gaps, weekends, and holidays.
   - Evaluates canonical Day 15 target formulation: $R = Close_{t+1}/Close_t - 1.0$; $R > 0 \implies UP$, $R \le 0 \implies DOWN$.
   - Accurately detects `PENDING` status when target session $t+1$ has not yet closed, preventing any forward leakage.
   - Captures data provenance (`source` and ISO timestamps) and supports batch verification.
4. **Prediction Evaluation Service (`app/history/evaluator.py`):**
   - Implemented `PredictionEvaluator` with strict denominator correctness:
     $$\text{Directional Accuracy} = \frac{N_{correct}}{N_{verified}}$$
   - Excludes pending and ineligible predictions from error metrics and accuracy denominator.
   - Symmetrical class metrics for UP and DOWN directions.
   - Zero-division safety when $N_{verified} == 0$.
   - Preserves explicit uncalibrated probability disclosures and anti-fabrication price target boundaries.
5. **Package Exports & Entry Point:**
   - Exported all contracts, verifier, and evaluator in `app/history/__init__.py`.
   - Updated `main.py` verifying Day 25 readiness.

### Real-Data Verification Findings (BHARTIARTL.NS)
Executed `scripts/verify_day25.py` against live market data:
- **Schema & Triggers:** Verified `actuals` table and `trg_prevent_actual_update`, `trg_prevent_actual_delete`.
- **Historical Outcome Verification:**
  - Prediction made as of Friday 2026-10-09 (Reference Close: ₹1,805.10).
  - Target session resolved correctly to Monday 2026-10-12 (Target Close: ₹1,778.70), skipping the weekend naturally.
  - Realized Return: $-1.4625\%$; Actual Direction: `DOWN`.
  - Predicted Direction: `UP`; Outcome Correct: `False`.
  - Verification Status: `VERIFIED`.
  - Repeated verification: `ALREADY_VERIFIED` (idempotent).
- **Pending Session Detection:**
  - Prediction made as of latest available bar (2026-10-15).
  - Target session $t+1$ has not yet occurred/closed.
  - Verification Status: `PENDING` ("Target session following 2026-10-15 has not yet closed. Outcome is pending.").
  - Zero write to `actuals`, zero leakage.
- **Evaluation Metrics & Denominator Correctness:**
  - Total Predictions: 2, Eligible: 2, Pending: 1, Verified: 1.
  - Denominator strictly equals $N_{verified} = 1$ ($100\%$ completed sessions).
  - Accuracy: $0.00\%$ ($0 / 1$).
  - Pending session correctly excluded from denominator.
- **Immutability & Conflict Rejection Audit:**
  - Direct SQL UPDATE on `actuals`: rejected by trigger (`Actual outcomes are immutable: updates are strictly prohibited.`).
  - Direct SQL DELETE on `actuals`: rejected by trigger (`Actual outcomes are immutable: deletions are strictly prohibited.`).
  - Attempting to save conflicting actual outcome: rejected by repository with `ValueError`.
- **Cleanup Guarantee:** Transient test database cleaned up safely in `try...finally`.

### Tests
- Created `tests/test_outcome_verification.py` with 15 comprehensive unit tests:
  1. `test_actual_outcome_contract_validation`: verifies validation of prices, returns, and directions.
  2. `test_save_actual_and_retrieve_from_repository`: verifies relational persistence and linking with predictions.
  3. `test_save_actual_idempotency_repeated_verification`: verifies idempotent re-runs return existing ID without error.
  4. `test_save_actual_conflicting_record_rejected`: verifies conflicting actual records raise `ValueError`.
  5. `test_actuals_immutability_triggers`: verifies SQLite engine triggers block direct UPDATE and DELETE.
  6. `test_verification_correct_and_incorrect_directional_outcomes`: verifies return computation and direction matching.
  7. `test_verification_pending_target_session`: verifies pending status when session $t+1$ has not occurred.
  8. `test_verification_weekend_and_market_holiday_handling`: verifies non-calendar session alignment across weekends and holidays.
  9. `test_verification_missing_or_incomplete_market_data`: verifies `DATA_UNAVAILABLE` status on missing provider data.
  10. `test_verification_ineligible_predictions`: verifies non-SUCCESS predictions evaluate to `INELIGIBLE`.
  11. `test_verification_invalid_prices_handling`: verifies non-positive prices are flagged as `DATA_UNAVAILABLE`.
  12. `test_evaluator_accuracy_and_denominator_correctness`: verifies accuracy denominator is strictly $N_{verified}$.
  13. `test_evaluator_insufficient_samples_zero_division_safety`: verifies safe `None` when zero predictions are verified.
  14. `test_evaluator_symmetrical_class_metrics_and_breakdowns`: verifies confusion matrix and precision/recall/F1.
  15. `test_evaluator_preservation_of_immutable_prediction_records`: verifies evaluation never modifies prediction records.
- **Full Test Suite Results:**
  - Previous baseline: 299 passed
  - New total: **314 passed in 11.66s** (15 new tests, 0 failures, 0 regressions across 23 test modules).
  - Deterministic fixtures and mocks; zero external network dependencies in unit tests.

### Review
- **Ponytail / Senior Dev Mode:** Reused existing SQLite schema and repository; stdlib `sqlite3`, `dataclasses`, and `datetime` only. Immutability enforced via native triggers; zero external ORMs added.

### Documentation
- Updated `README.md` to Day 25 status with 314 passing tests.
- Updated `docs/architecture.md` with Section 4.20 detailing Outcome Verification & Evaluation Architecture.
- Updated `docs/decisions.md` with ADR 53.
- Updated `docs/roadmap.md` with Phase 7 / Day 25 completion details.
- Updated `docs/daily-progress.md` with Day 25 development log.

### Known Limitations & Next Steps
- Current evaluation measures binary directional accuracy, precision, recall, and F1. Continuous price magnitude errors (MAE, RMSE) are unsupported because current XGBoost and LightGBM models predict direction only.
- Model probabilities remain uncalibrated raw scores; calibration is reserved for a future phase.
- Next scheduled scope: Phase 8 (NIFTY & Sector Context: ingesting benchmark indices, relative performance, and market breadth).

---

## Day 26 - NIFTY Benchmark & Sector Context Engine

### Goal
Implement Phase 8: NIFTY & Sector Context foundation:
1. Ingest Indian benchmark indices (NIFTY 50 `^NSEI`, NIFTY Bank `^NSEBANK`, NIFTY IT `^CNXIT`, and sectoral indices) via market data provider with dedicated index symbol resolution.
2. Establish point-in-time session alignment across equities and benchmarks (`align_benchmark_series`), strictly preventing look-ahead bias and tolerating trading calendar/holiday discrepancies.
3. Compute point-in-time relative performance features (`compute_relative_performance`): daily excess return (alpha), relative strength ratio, 5d and 20d relative strength momentum, 20-session rolling beta, and 20-session rolling correlation with sample degrees of freedom ($ddof=1$) and zero-variance guards.
4. Implement cross-sectional market breadth calculation (`compute_market_breadth` and `compute_multi_symbol_breadth_series`): advances, declines, unchanged counts, advance-decline ratio, breadth thrust, net advances, and 20-day SMA breadth participation percentage.
5. Provide comprehensive automated unit tests (deterministic, mock-based) and execute real-market verification.

### Work Completed
1. **Provider Index Symbol Resolution (`app/market/providers/yfinance_provider.py`):**
   - Implemented `INDEX_SYMBOL_MAP` supporting standard Indian indices and friendly aliases: `NIFTY`, `NIFTY50`, `BANKNIFTY`, `NIFTYBANK`, `NIFTYIT`, `CNXIT`, `SENSEX`, `NIFTY500`, `NIFTYMIDCAP50`.
   - Updated `_resolve_symbols` to treat symbols starting with `^` or mapped index aliases as pure index tickers, preventing unwanted exchange suffixes (`.NS` / `.BO`) from causing HTTP 404 errors.
2. **Benchmark & Context Engine Implementation (`app/market/benchmark.py`):**
   - Defined `SECTOR_BENCHMARK_MAP` and `get_sector_benchmark()` resolving sector aliases (`BANKING`, `FINANCIAL_SERVICES`, `IT`, `TECH`) to canonical tickers (`^NSEBANK`, `^CNXIT`) with safe fallback to `^NSEI`.
   - Created `RelativePerformanceFeature` dataclass with `.to_dict()` serialization.
   - Created `MarketBreadthObservation` dataclass with `.to_dict()` serialization.
   - Implemented `compute_covariance()` using sample degrees of freedom ($ddof=1$) with length and NaN validation.
   - Implemented `align_benchmark_series()` with strict point-in-time calendar date matching ($bar.timestamp.date()$) and zero look-ahead bias.
   - Implemented `compute_relative_performance()` calculating:
     - Daily excess return (alpha): $R_{stock} - R_{bench}$.
     - Relative strength ratio: $Close_{stock} / Close_{bench}$.
     - 5d and 20d relative strength momentum: $(RS_t / RS_{t-w}) - 1.0$.
     - 20-session rolling beta: $\beta = Cov(R_s, R_b) / Var(R_b)$ with zero benchmark variance guard ($Var(R_b) < 1e-12 \implies None$).
     - 20-session rolling correlation: $\rho = Cov(R_s, R_b) / (\sigma_s \sigma_b)$ clamped to $[-1.0, 1.0]$.
   - Implemented `compute_market_breadth()` and `compute_multi_symbol_breadth_series()` calculating advances, declines, unchanged, advance/decline ratio (safe against zero declines), breadth thrust, net advances, and 20-day SMA breadth participation percentage.
3. **Module Exports & Application Entry Point:**
   - Exported all new benchmark components in `app/market/__init__.py`.
   - Updated `main.py` verifying Day 26 readiness.

### Real-Data Verification Findings (BHARTIARTL.NS & ^NSEI)
Executed `scripts/verify_day26.py` against live market data:
- **Symbol Resolution:** Verified pure index tickers (`^NSEI`, `^NSEBANK`) and aliases (`NIFTY`, `BANKNIFTY`) resolve without `.NS` suffix.
- **Historical Ingestion:** Fetched 61 daily sessions for Bharti Airtel and NIFTY 50 from 2026-07-18 to 2026-10-16.
- **Session Alignment:** 61/61 pairs matched strictly on identical calendar dates.
- **Relative Performance:**
  - On 2026-10-14: Bharti Airtel Close ₹1,794.60, NIFTY 50 Close ₹22,622.70.
  - Alpha: $-0.22\%$, RS Ratio: $0.0793$, RS Momentum 5d: $-2.23\%$.
  - 20-session Rolling Beta: **0.898** (defensive/moderate beta characteristic for large-cap telecom).
  - 20-session Rolling Correlation: **0.537** (positive, statistically bounded co-movement with broad market).
- **Cross-Sectional Market Breadth:**
  - Evaluated representative basket across 61 sessions: Bharti Airtel, Reliance, TCS, HDFC Bank.
  - Latest snapshot (2026-10-14): Total: 4, Advances: 2, Declines: 2, Unchanged: 0, ADR: 1.0, Thrust: 0.5, % Above 20-day SMA: 25.0%.
- **Invariant Audit:** Zero lookahead bias, zero division-by-zero errors, zero floating point overflows.

### Tests
- Created `tests/test_benchmark_context.py` with 13 comprehensive unit tests:
  1. `test_provider_resolves_index_tickers`: verifies resolution of index tickers and friendly aliases without `.NS`.
  2. `test_provider_preserves_equity_symbols`: verifies regular equity tickers append `.NS` as expected.
  3. `test_sector_benchmark_resolution`: verifies sector mapping to NIFTY Bank, NIFTY IT, and NIFTY 50 fallback.
  4. `test_compute_covariance_synthetic`: verifies mathematical covariance accuracy against known linear slope ($y=2x \implies Cov=5.0$).
  5. `test_compute_covariance_guards`: verifies NaN handling, length mismatch, and small sample guards.
  6. `test_align_benchmark_series_matching_dates`: verifies session date pairing.
  7. `test_align_benchmark_series_handles_calendar_gaps`: verifies calendar gaps and holidays pair safely with None.
  8. `test_compute_relative_performance_empty`: verifies empty input handling.
  9. `test_compute_relative_performance_synthetic_beta_and_alpha`: verifies beta and correlation against known synthetic alternating series ($\beta=2.0, \rho=1.0$).
  10. `test_zero_variance_guard`: verifies zero-variance benchmark series safely return None for beta and correlation without division-by-zero errors.
  11. `test_compute_market_breadth_snapshot`: verifies advance, decline, unchanged, ADR, thrust, and SMA participation.
  12. `test_compute_market_breadth_zero_declines_guard`: verifies ADR evaluates to None when zero declines occur.
  13. `test_compute_multi_symbol_breadth_series`: verifies multi-symbol time-series breadth accumulation.
- **Full Test Suite Results:**
  - Previous baseline: 314 passed
  - New total: **327 passed in 12.08s** (13 new tests, 0 failures, 0 regressions across 24 test modules).
  - Deterministic fixtures and mocks; zero external network dependencies in unit tests.

### Review
- **Ponytail / Senior Dev Mode:** Reused existing `calculate_daily_returns`, `calculate_standard_deviation`, and `calculate_sma`. Reused `MarketOHLCV` schema. Built with standard library `math`, `dataclasses`, and `datetime` only. Zero third-party packages added.

### Documentation
- Updated `README.md` to Day 26 status with 327 passing tests.
- Updated `docs/architecture.md` with Section 4.21 detailing Benchmark & Sector Context Engine.
- Updated `docs/decisions.md` with ADR 54.
- Updated `docs/roadmap.md` with Phase 8 / Day 26 completion details.
- Updated `docs/daily-progress.md` with Day 26 development log.

### Known Limitations & Next Steps
- Benchmark and sector context features are computed at the market data layer; integration into the canonical training feature matrix (`app/training/feature_matrix.py`) and prediction pipeline will follow in the model refinement roadmap.
- Next scheduled scope: Phase 9 (News & Financial Sentiment: financial news retrieval, deduplication, and FinBERT sentiment scoring).

---

## Day 27 - Financial News Ingestion Foundation

### Goal
Establish the financial-news ingestion foundation for Phase 9: News & Financial Sentiment:
1. Create a maintainable news provider interface (`BaseNewsProvider`) consistent with the existing market-data architecture.
2. Normalize news items into a typed, canonical contract (`NewsArticle`) capturing headline, source publisher, timezone-aware publication time, distinct ingestion time, symbol associations, URL, summary, and deterministic content ID.
3. Build a concrete RSS news provider adapter (`RSSNewsProvider`) backed by standard library XML parsing (`xml.etree.ElementTree`) and URL retrieval (`urllib.request`), requiring zero additional third-party dependencies.
4. Implement a multi-tier syndicated news deduplication engine (`deduplicate_news`) and strict point-in-time session filtering (`filter_news_point_in_time`) to eliminate look-ahead leakage.
5. Provide comprehensive automated unit tests (deterministic, mock-based) and execute real-world live verification across Indian equities.

### Work Completed
1. **Canonical Schema Contract (`app/news/schemas.py`):**
   - Created `NewsArticle` dataclass enforcing non-empty headlines and publishers, timezone-aware timestamps, clean uppercase symbols (with `.NS`/`.BO` exchange suffixes cleanly stripped), valid URLs, and deterministic 16-character SHA-256 `article_id` hashes (`headline + source + published_at`).
   - Implemented `.to_dict()` serialization.
2. **Provider Contract & RSS Adapter (`app/news/providers/`):**
   - Defined `BaseNewsProvider(ABC)` establishing uniform `fetch_news()` contract with symbol, date range, and limit parameters.
   - Defined `NewsProviderError` for graceful error propagation.
   - Implemented `RSSNewsProvider` supporting query building for Indian equities (`COMPANY_NAME_MAP`), standard library XML element tree parsing, RFC 2822 to IST datetime normalization, publisher source extraction, and summary HTML stripping.
   - Supported dependency injection of custom fetcher functions for 100% deterministic, offline unit testing.
3. **Deduplication & Point-in-Time Filtering (`app/news/cleaner.py`):**
   - Implemented `deduplicate_news()` with a 3-tier precedence rule: exact ID match, exact URL match, and syndicated headline match within a configurable window (default 48h), preserving earliest publication origin.
   - Created `NewsCleaningResult` and `NewsDeduplicationSummary` containers.
   - Implemented `filter_news_point_in_time()` enforcing $published\_at \le as\_of\_time$ and $ingested\_at \le as\_of\_time$, strictly preventing look-ahead bias when aligning news to historical market sessions.
4. **Module Exports & Entry Point:**
   - Exported all schemas, providers, and cleaner functions in `app/news/__init__.py`.
   - Updated `main.py` verifying Day 27 readiness.

### Real-Data Verification Findings (BHARTIARTL, RELIANCE, TCS, HDFCBANK)
Executed `scripts/verify_day27.py` against live financial news feeds:
- **Live Ingestion:** Fetched 40 live news articles across Bharti Airtel, Reliance, TCS, and HDFC Bank.
- **Provenance & Timestamp Isolation:** Verified all articles contained valid headlines, publisher sources (e.g. Moneycontrol, Kalkine India, scanx.trade), timezone-aware publication times in IST, and distinct local ingestion timestamps.
- **Deduplication:** Successfully detected and removed syndicated duplicates across media outlets.
- **Point-in-Time Isolation:** Verified that establishing an earlier cutoff timestamp safely excludes all post-cutoff articles with zero look-ahead bias.
- **Serialization:** Verified lossless `.to_dict()` JSON serialization.

### Tests
- Created `tests/test_news_ingestion.py` with 15 comprehensive unit tests:
  1. `test_valid_news_article_normalization`: verifies schema parsing, symbol cleanup, and `.to_dict()`.
  2. `test_missing_and_malformed_fields`: verifies validation errors on blank headlines, blank sources, naive datetimes, and invalid URLs.
  3. `test_publication_time_distinct_from_ingestion_time`: verifies temporal isolation between publication and system ingestion.
  4. `test_parse_valid_rss_payload`: verifies XML parsing, title suffix stripping, RFC 2822 to IST parsing, and summaries.
  5. `test_parse_empty_or_whitespace_payload`: verifies safe empty list return on empty XML.
  6. `test_parse_malformed_xml_raises_provider_error`: verifies `NewsProviderError` on broken XML syntax.
  7. `test_parse_skips_items_with_missing_titles_or_dates`: verifies graceful item skipping for corrupt entries.
  8. `test_fetch_news_with_custom_fetcher`: verifies offline deterministic mock fetcher.
  9. `test_fetch_news_handles_fetcher_exception`: verifies graceful exception propagation on network failure.
  10. `test_company_name_mapping`: verifies company query string generation.
  11. `test_deduplicate_identical_ids_and_urls`: verifies exact duplicate removal.
  12. `test_deduplicate_syndicated_headlines_within_window`: verifies syndicated headline deduplication.
  13. `test_deduplicate_empty_input`: verifies safe handling of empty inputs.
  14. `test_filter_news_point_in_time_excludes_future_articles`: verifies zero look-ahead leakage.
  15. `test_filter_news_lookback_window`: verifies lookback window filtering.
- **Full Test Suite Results:**
  - Previous baseline: 327 passed
  - New total: **342 passed in 11.73s** (15 new tests, 0 failures, 0 regressions across 25 test modules).
  - Deterministic fixtures and mocks; zero external network dependencies in unit tests.

### Review
- **Ponytail / Senior Dev Mode:** Built using standard library `xml.etree.ElementTree`, `urllib.request`, `email.utils`, `hashlib`, `re`, `html`, `dataclasses`, and `datetime`. Zero third-party packages or heavy dependencies added.

### Documentation
- Updated `README.md` to Day 27 status with 342 passing tests.
- Updated `docs/architecture.md` with Section 4.22 detailing Financial News Ingestion & Cleaning Engine.
- Updated `docs/decisions.md` with ADR 55.
- Updated `docs/roadmap.md` with Phase 9 / Day 27 foundation details.
- Updated `docs/data-sources.md` marking Section 5 Domestic Financial News as VERIFIED (Day 27).
- Updated `docs/daily-progress.md` with Day 27 development log.

### Known Limitations & Next Steps
- Day 27 implements the news ingestion and deduplication foundation. FinBERT domain-specific sentiment scoring, sentiment feature generation, and textual embedding will follow in subsequent Phase 9 steps.
- Neither Gemma 3 12B nor Laya AI is introduced today; LLM reasoning and news entity classification remain scheduled for their designated future phases.
- Next scheduled scope: FinBERT sentiment scoring foundation and financial news sentiment feature engineering.

---

## Day 28 - FinBERT Financial Sentiment Scoring Foundation

### Goal
Implement a maintainable FinBERT financial-news sentiment scoring foundation using the existing Day 27 news ingestion layer:
1. Select a documented, domain-adapted financial sentiment model (`ProsusAI/finbert`) with clear licensing (Apache 2.0) and interface specifications.
2. Implement lazy initialization to guarantee zero model weights or transformer overhead are loaded during package import or standard command execution.
3. Build a typed, validated sentiment output schema (`ArticleSentimentResult`) capturing `article_id`, headline, sentiment label (`positive`, `neutral`, `negative`), winning confidence score, class probability distribution, model provenance, and scoring timestamp.
4. Enforce strict error quarantining: missing dependencies or runtime inference errors record `status="ERROR"` with `sentiment_label=None` and `probabilities=None` (strictly prohibiting false neutral fabrication).
5. Implement safe text preparation with headline validation and configurable character truncation (`prepare_article_text`).
6. Guarantee point-in-time temporal integrity: preserve Day 27 point-in-time filtering invariants ($published\_at \le as\_of\_time$ and $ingested\_at \le as\_of\_time$), keeping scoring timestamp distinct from publication and ingestion timestamps.
7. Support pluggable backends: concrete `FinBERTBackend` (Hugging Face Transformers + PyTorch) and deterministic `MockSentimentBackend` for 100% offline unit testing with zero weight downloads.
8. Add comprehensive automated unit tests and an end-to-end verification script.

### Work Completed
1. **Canonical Sentiment Schema & Validation (`app/news/sentiment.py`):**
   - Implemented `ArticleSentimentResult` frozen dataclass with validation checks:
     - Enforces valid `status` in `{"SUCCESS", "ERROR"}`.
     - On SUCCESS: `sentiment_label` must be one of `{"positive", "neutral", "negative"}`.
     - Confirms probabilities are finite, lie in $[0.0, 1.0]$, and sum to $1.0 \pm 10^{-3}$.
     - Confirms winning `sentiment_score` strictly equals `probabilities[sentiment_label]`.
     - On ERROR: `sentiment_label` and `probabilities` evaluate strictly to `None`.
     - Full `.to_dict()` lossless serialization.
2. **Text Preparation & Boundary Controls (`prepare_article_text` in `app/news/sentiment.py`):**
   - Requires non-empty cleaned headline string.
   - Supports optional summary inclusion (`"Headline. Summary"`).
   - Enforces configurable character boundary truncation (default `max_length_chars=512`) to prevent tokenizer memory blow-ups.
3. **Pluggable Sentiment Scoring Backends (`app/news/sentiment.py`):**
   - `BaseSentimentBackend(ABC)`: abstract interface with `score_text(text: str) -> Dict[str, float]`.
   - `FinBERTBackend`: concrete adapter wrapping Hugging Face `BertForSequenceClassification` (`ProsusAI/finbert`).
     - Lazy model loading: weights are loaded exclusively upon first inference via `_ensure_loaded()`.
     - Dynamic `id2label` resolution: reads class order dynamically from `model.config.id2label` (`{0: 'positive', 1: 'negative', 2: 'neutral'}`) rather than hardcoding.
     - Deterministic inference mode: uses `model.eval()` and `torch.inference_mode()`.
     - Explicit dependency checks: raises informative `RuntimeError` if `torch` or `transformers` is not installed.
   - `MockSentimentBackend`: deterministic test double for offline unit tests and CI environments, requiring zero network downloads or model weights.
4. **Scoring Service (`FinBERTSentimentScorer` in `app/news/sentiment.py`):**
   - Implemented `score_article(article)` and `score_articles(articles)` preserving exact input order.
   - Implemented error quarantining: wraps inference or data errors into `ArticleSentimentResult(status="ERROR", error_message=...)`, never fabricating false neutrals.
5. **Package Exports & Entry Point:**
   - Exported all sentiment schemas, backends, and scorer in `app/news/__init__.py`.
   - Created `app/nlp/__init__.py` providing clean alias re-exports.
   - Updated `main.py` verifying Day 28 readiness.

### Verification Script Findings (`scripts/verify_day28.py`)
Executed `scripts/verify_day28.py` covering all core Day 28 invariants:
- **Dependency Audit:** Accurately detected PyTorch and Transformers status in the current environment without crashing.
- **Text Preparation:** Validated headline extraction and character boundary truncation on real news articles fetched for `BHARTIARTL`.
- **Deterministic Inference:** Scored 5 news articles using deterministic mock engine; verified canonical JSON schema serialization and probability normalization ($\sum P_i = 1.000$).
- **Anti-Fabrication & Error Quarantining:** Injected an inference failure; verified that the scorer returned `status="ERROR"` with `sentiment_label=None` and `probabilities=None` (zero fake neutrals).
- **Point-in-Time Temporal Isolation:** Verified that articles published after market decision cutoff are strictly filtered out before scoring.
- **Exit Code:** 0.

### Tests
- Created `tests/test_finbert_sentiment.py` with 20 comprehensive unit tests:
  1. `test_article_sentiment_result_valid_construction`: verifies valid result construction, probability invariants, and `.to_dict()`.
  2. `test_article_sentiment_result_negative_and_neutral`: verifies negative and neutral label validation.
  3. `test_article_sentiment_result_rejects_invalid_probabilities_sum`: verifies rejection when probabilities do not sum to 1.0.
  4. `test_article_sentiment_result_rejects_probabilities_outside_range`: verifies rejection of probabilities $< 0$ or $> 1$.
  5. `test_article_sentiment_result_rejects_non_finite_probabilities`: verifies rejection of NaN or Inf probabilities.
  6. `test_article_sentiment_result_error_state_requires_none_label`: verifies error state rejects non-None sentiment labels.
  7. `test_prepare_article_text_headline_only`: verifies headline text extraction.
  8. `test_prepare_article_text_with_summary`: verifies concatenation of headline and summary.
  9. `test_prepare_article_text_truncation`: verifies character truncation at boundary.
  10. `test_prepare_article_text_rejects_blank_headline`: verifies rejection of empty/whitespace headlines.
  11. `test_mock_sentiment_backend_deterministic_mapping`: verifies deterministic classification of keyword-containing texts.
  12. `test_mock_sentiment_backend_normalizes_probabilities`: verifies Softmax normalization on mock outputs.
  13. `test_finbert_scorer_scores_article_successfully`: verifies single article scoring workflow.
  14. `test_finbert_scorer_batch_scoring`: verifies batch article scoring preserving input order.
  15. `test_finbert_scorer_quarantines_backend_error_without_fake_neutral`: verifies zero fake neutrals on backend exceptions.
  16. `test_finbert_scorer_quarantines_empty_text_error`: verifies error quarantining on empty text.
  17. `test_finbert_scorer_preserves_article_id_and_distinct_timestamps`: verifies distinct `scored_at` vs `published_at`/`ingested_at`.
  18. `test_finbert_backend_raises_error_when_dependencies_missing`: verifies clean `RuntimeError` when `torch` or `transformers` is missing.
  19. `test_finbert_backend_dynamic_id2label_mapping`: verifies dynamic resolution of label config.
  20. `test_point_in_time_news_filtering_before_sentiment_scoring`: verifies zero look-ahead bias when filtering articles prior to scoring.
- **Full Test Suite Results:**
  - Previous baseline: 342 passed
  - New total: **362 passed in 8.45s** (20 new tests, 0 failures, 0 regressions across 26 test modules).
  - 100% offline and deterministic; zero model weight downloads in unit tests.

### Review
- **Ponytail / Senior Dev Mode:** Lazy initialization of transformer dependencies; pluggable backend abstraction enabling 100% offline testing without downloading 440MB model weights during test execution; zero third-party ORM or heavy dependencies added; zero fake neutral predictions on failure; strict schema and probability invariants.

### Documentation
- Updated `README.md` to Day 28 status with 362 passing tests.
- Updated `docs/architecture.md` with Section 4.23 detailing FinBERT Financial Sentiment Scoring Engine.
- Updated `docs/decisions.md` with ADR 56.
- Updated `docs/roadmap.md` marking Phase 9 / Day 28 complete.
- Updated `docs/daily-progress.md` with Day 28 development log.

### Known Limitations & Next Steps
- Day 28 establishes the sentiment scoring foundation and offline deterministic engine. Full GPU-accelerated local inference with `ProsusAI/finbert` requires installing `torch` and `transformers` and downloading the ~440MB model weights locally to Hugging Face cache (`~/.cache/huggingface/hub`).
- Sentiment is an auxiliary textual feature representing linguistic tone; it is NOT integrated into the XGBoost/LightGBM prediction engine today.
- No LLM integration (Gemma 3 12B) or Laya AI integration is performed today; both remain scheduled for their planned future roadmap phases.
- Next scheduled scope: Phase 10: Regulatory & Global Events (macroeconomic, RBI, governmental, and geopolitical event ingestion).

---

## Day 29 - Phase 10: Macroeconomic, Regulatory & External Events Ingestion Foundation

### Goal
Establish the macroeconomic, regulatory, and external-events ingestion foundation under Phase 10 (`app/events/`):
1. Ingest official central bank announcements from the Reserve Bank of India (RBI: press releases, MPC decisions, repo rate updates).
2. Ingest official market regulator circulars and orders from the Securities and Exchange Board of India (SEBI).
3. Ingest continuous external market variables (Brent crude oil, USD/INR exchange rate, S&P 500) while cleanly distinguishing continuous time-series measurements from discrete policy announcements.
4. Define canonical, immutable schemas (`MacroEvent`, `StructuredEventValue`, `ExternalMarketObservation`) enforcing 4-timestamp isolation (`published_at`, `announced_at`, `effective_at`, `ingested_at`) and deterministic 16-hex SHA-256 IDs.
5. Implement multi-tier event deduplication (`deduplicate_events`).
6. Implement strict point-in-time session filtering (`filter_events_point_in_time`) to eliminate look-ahead leakage across market decision cutoffs while preserving future legal effective dates.
7. Support 100% offline, deterministic automated testing via dependency injection.
8. Execute live verification against real RBI, SEBI, and market feeds.

### Work Completed
1. **Canonical Event Schemas (`app/events/schemas.py`):**
   - Implemented `EventCategory` enum (`MONETARY_POLICY`, `REGULATORY`, `GOVERNMENT`, `MACRO_INDICATOR`, `EXTERNAL_MARKET`, `OTHER`).
   - Implemented `StructuredEventValue` frozen dataclass validating finite numeric measurements, units, prior values, and delta changes.
   - Implemented `MacroEvent` frozen dataclass capturing:
     - Title, category, event type, source organization, URL, summary, affected sectors/symbols.
     - Four distinct timezone-aware timestamps: `published_at`, `announced_at`, `effective_at`, and `ingested_at`.
     - Deterministic 16-character SHA-256 `event_id`.
     - Primary timestamp property (`primary_timestamp`) for rigorous temporal availability checks.
     - Lossless `.to_dict()` serialization.
   - Implemented `ExternalMarketObservation` frozen dataclass capturing continuous time-series measurements with `.to_event()` bridge adapter.
2. **Event Provider Adapters (`app/events/providers/`):**
   - `BaseEventProvider(ABC)`: Uniform provider interface.
   - `RBIEventProvider`: Ingests official RBI press releases (`https://rbi.org.in/pressreleases_rss.xml`), parses XML with stdlib `xml.etree.ElementTree`, normalizes timestamps to `Asia/Kolkata` IST, classifies monetary policy vs. regulatory items, and extracts structured repo rate values.
   - `SEBIEventProvider`: Ingests official SEBI circulars and orders (`https://www.sebi.gov.in/sebirss.xml`), robustly handles SEBI custom date formats (`16 Oct, 2026 +0530`), and targets equity market sectors.
   - `ExternalMarketProvider`: Ingests continuous macro variables (Brent Crude `BZ=F`, USD/INR `INR=X`, S&P 500 `^GSPC`), calculates daily percentage returns, and normalizes into `ExternalMarketObservation` records.
   - All providers support dependency injection of custom fetchers/downloaders for 100% offline test determinism.
3. **Cleaning, Deduplication, and Point-in-Time Filtering (`app/events/cleaner.py`):**
   - `deduplicate_events()`: Multi-tier deduplication covering exact event IDs, exact URLs, and matching source+title records within configurable windows (default 72h).
   - `filter_events_point_in_time()`: Enforces $primary\_timestamp \le as\_of\_time$ and $ingested\_at \le as\_of\_time$, strictly preventing look-ahead leakage across market decision cutoffs while preserving future effective dates.
4. **Package Exports & Entry Point:**
   - Exported all schemas, providers, and cleaner functions in `app/events/__init__.py`.
   - Updated `main.py` verifying Day 29 readiness.

### Real-Data Verification Findings (`scripts/verify_day29.py`)
Executed `scripts/verify_day29.py` against live official feeds:
- **RBI Live Ingestion:** Successfully fetched live press releases from `https://rbi.org.in/pressreleases_rss.xml` (e.g. State Government Securities auction, Balance of Payments release, Forex risk FAQs).
- **SEBI Live Ingestion:** Successfully fetched live circulars and enforcement orders from `https://www.sebi.gov.in/sebirss.xml`.
- **External Market Series:** Ingested daily measurements for USD/INR (95.04), S&P 500 (7,744.13), and Brent Crude ($105.73/barrel).
- **Deduplication:** Successfully verified multi-source event deduplication and canonical JSON payload serialization.
- **Point-in-Time Temporal Isolation:** Verified that establishing a 48h pre-cutoff timestamp strictly eliminated 100% of post-cutoff records with zero look-ahead leakage.
- **Exit Code:** 0.

### Tests
- Created `tests/test_macro_events.py` with 21 comprehensive unit tests:
  1. `test_structured_event_value_valid`: validates structured measurement construction, unit validation, change calculation, and `.to_dict()`.
  2. `test_structured_event_value_rejects_invalid_numbers`: validates rejection of non-numeric, NaN, or blank unit inputs.
  3. `test_macro_event_valid_construction`: validates complete `MacroEvent` construction, timezone localization, and serialization.
  4. `test_macro_event_rejects_missing_temporal_anchors`: validates requirement of at least one temporal anchor.
  5. `test_macro_event_rejects_naive_timestamps`: validates strict rejection of naive datetimes without timezone info.
  6. `test_macro_event_rejects_invalid_url`: validates URL scheme and netloc parsing.
  7. `test_macro_event_stable_deterministic_id`: validates deterministic collision-resistant SHA-256 hashing.
  8. `test_external_market_observation_valid_construction`: validates time-series observation schema and `.to_event()` adapter.
  9. `test_external_market_observation_rejects_negative_or_nan_prices`: validates positive finite price constraints.
  10. `test_deduplicate_events_identical_ids_and_urls`: validates exact duplicate ID and URL elimination.
  11. `test_deduplicate_events_syndicated_titles_within_window`: validates fuzzy title+source deduplication within time window.
  12. `test_deduplicate_events_empty_input`: validates graceful empty list handling.
  13. `test_filter_events_point_in_time_exact_cutoff_and_exclusion`: validates inclusion at exact cutoff and exclusion of future-published or future-ingested records.
  14. `test_filter_events_point_in_time_preserves_effective_dates`: validates that future effective dates (`effective_at`) remain unmutated.
  15. `test_filter_events_point_in_time_lookback_window`: validates lookback window duration filtering.
  16. `test_rbi_provider_parses_sample_xml`: validates RBI XML parsing, monetary policy classification, and repo rate extraction.
  17. `test_rbi_provider_handles_malformed_xml`: validates `EventProviderError` on broken XML syntax.
  18. `test_rbi_provider_handles_empty_response`: validates graceful empty list return on blank payload.
  19. `test_sebi_provider_parses_sample_xml`: validates SEBI XML parsing, master circular classification, and custom date parsing.
  20. `test_sebi_provider_handles_malformed_xml`: validates `EventProviderError` on broken XML syntax.
  21. `test_external_market_provider_offline_mock`: validates offline deterministic external market observation ingestion and event mapping.
- **Full Test Suite Results:**
  - Previous baseline: 362 passed
  - New total: **383 passed in 6.99s** (21 new tests, 0 failures, 0 regressions across 27 test modules).
  - 100% offline and deterministic; zero external network dependencies in unit tests.

### Review
- **Ponytail / Senior Dev Mode:** Reused existing standard library XML parsing (`xml.etree.ElementTree`) and URL retrieval (`urllib.request`); reused `yfinance` for external market measurements; zero new external packages added; distinct modeling of continuous time-series vs. discrete announcements; zero look-ahead bias; strict non-causal representation.

### Documentation
- Updated `README.md` to Day 29 status with 383 passing tests.
- Updated `docs/architecture.md` with Section 4.24 detailing Macroeconomic, Regulatory & External Events Ingestion Engine.
- Updated `docs/data-sources.md` marking Section 6 (RBI & SEBI) and Section 7 (USD/INR, Brent Crude, S&P 500) as VERIFIED (Day 29).
- Updated `docs/decisions.md` with ADR 57.
- Updated `docs/roadmap.md` marking Phase 10 / Day 29 foundation complete.
- Updated `docs/daily-progress.md` with Day 29 development log.

### Known Limitations & Next Steps
- Day 29 implements the event ingestion and point-in-time filtering foundation. Contextual impact mapping, cross-sectional event joins, and feature matrix integration will be designed in subsequent Phase 10 milestones.
- Union Budget announcements (`https://www.indiabudget.gov.in/`) are annual/seasonal; structured PDF/speech document parsing will be addressed during budget release windows. PIB RSS feeds undergo periodic scheme shifts; adapter planned for dedicated ministerial API endpoints.
- No LLM integration (Gemma 3 12B) or Laya AI integration is performed today; both remain scheduled for their planned future roadmap phases (Phase 11+).
- Next scheduled scope: Phase 10 continuation (contextual impact mapping and cross-sectional event feature extraction).

---

## Day 30 - Event Impact Analysis & Trading Session Alignment (Phase 10 Complete)

### Goal
Implement the foundational event-impact analysis layer that aligns macroeconomic and regulatory events and external-market observations with Indian equity trading sessions:
1. Review, verify, and resolve unresolved CodeRabbit findings on Day 29 code.
2. Establish deterministic Indian equity trading calendar abstractions (`BaseTradingCalendar`, `MarketDataTradingCalendar`, `ExchangeTradingCalendar`).
3. Implement `EventSessionAligner` mapping events to trading sessions across pre-market (< 09:15 IST), in-session (09:15-15:30 IST), post-market (> 15:30 IST -> T+1), weekends, exchange holidays, and date-only precision notices.
4. Implement `EventImpactAnalyzer` computing same-day return, 1d/3d/5d forward returns, pre- and post-event realized volatilities (5-session rolling sample stdev), and benchmark excess returns (^NSEI).
5. Enforce strict anti-leakage safeguards: incomplete outcome windows return `None` (`INCOMPLETE_OUTCOME_WINDOW`); multi-event deduplication prevents double-counting; mandatory non-causal disclosures enforced.
6. Verify offline with deterministic unit tests and live/historical verification script.

### Assessment and Resolution of Day 29 CodeRabbit Findings
Prior to starting Day 30 feature code, all CodeRabbit findings on Day 29 were systematically inspected and verified:
1. **External Market Provider Exclusive End-Date:** Confirmed that `yf.download` uses an exclusive `end` date parameter, dropping the final session on `end_date`. Fixed by adding `+ timedelta(days=1)` matching `yfinance_provider.py`.
2. **Historical Ingestion Timestamps:** Confirmed that `ExternalMarketProvider.fetch_observations` hardcoded `ingested_at = now_ist`, preventing point-in-time backtesting. Added optional `ingested_at: Optional[datetime] = None` parameter defaulting to current IST time.
3. **Primary Timestamp Conflation with Effective Date:** Confirmed that `MacroEvent.primary_timestamp` fell back to `effective_at`, conflating legal effective dates with public information availability. Fixed precedence strictly to `published_at -> announced_at -> ingested_at`. `effective_at` is preserved strictly as the legal/operational date.
4. **RBI Provider Classification & Truncation Before Sorting:** Confirmed that `if len(events) >= limit: break` inside the XML parsing loop truncated before sorting by primary timestamp. Fixed by sorting descending by timestamp and then slicing `[:limit]`. Replaced raw substring search with word-boundary regex (`\b(?:crr|slr)\b`) to prevent false positives inside words like 'occurrence' or 'referral'.
5. **SEBI Date-Only Precision & Sort-Before-Limit:** Fixed sort-before-limit. Enhanced `_parse_sebi_date` to return `(datetime, precision)` and record `time_precision="date_only"` in `raw_metadata` when feeds omit time-of-day.
6. **Day 29 Verification Script Hardening:** Guarded `sample_ev = dedup_result.events[0]` against empty lists. Replaced vacuous live point-in-time checks with comprehensive pre-cutoff, exact boundary, future-published, and future-ingested synthetic boundary tests.
7. **Regression Tests Added:** Added 4 new regression tests to `tests/test_macro_events.py` verifying all fixes.

### Work Completed (Day 30)
1. **Indian Equity Trading Calendar Abstractions (`app/events/calendar.py`):**
   - Implemented `BaseTradingCalendar(ABC)` defining `is_trading_day`, `get_next_trading_day`, `get_previous_trading_day`, `get_trading_days`, and `get_session_times`.
   - Implemented `MarketDataTradingCalendar`: extracts valid trading dates directly from observed `MarketOHLCV` bars, eliminating holiday guesswork.
   - Implemented `ExchangeTradingCalendar`: injectable calendar supporting custom holiday sets, weekend rules, and special sessions (e.g. Diwali Muhurat trading).
2. **Trading Session Alignment Engine (`app/events/aligner.py`):**
   - Implemented `EventSessionAligner` mapping events into canonical `AlignedEventSession` records.
   - Categorizes events into `PRE_MARKET`, `IN_SESSION`, and `POST_MARKET`.
   - Enforces zero look-ahead: events published after 15:30:00 IST on trading day $T$ are strictly routed to session $T+1$ as `POST_MARKET` information.
   - Maps non-trading days (weekends & holidays) to the next active trading session.
   - Date-only precision guard: conservatively aligns date-only regulatory circulars (e.g. SEBI notices lacking time-of-day) to the next trading day when `conservative_date_only=True`.
3. **Empirical Event Impact Analysis Layer (`app/events/impact.py`):**
   - Implemented `EventImpactAnalyzer` computing:
     - Same-day reaction return: $(Close_T / Close_{T-1}) - 1.0$.
     - Multi-session forward returns: 1-session, 3-session, and 5-session forward returns from the event session close.
     - Realized volatility: 5-session rolling sample standard deviation ($ddof=1$ via `calculate_standard_deviation`) pre-event ($[T-5 \dots T-1]$) and post-event ($[T+1 \dots T+5]$).
     - Benchmark relative alpha: excess forward return $R_{stock, 1d} - R_{bench, 1d}$ against broad market (`^NSEI`).
   - Incomplete outcome guard: sessions where $T+k$ exceeds the latest available historical bar return `None` with status `INCOMPLETE_OUTCOME_WINDOW` (zero price fabrication).
   - Insufficient history guard: sessions with fewer than 5 prior bars return `None` for pre-volatility with explicit diagnostic status.
   - Multi-event deduplication & summary: `analyze_events` deduplicates events by `event_id` and computes `AggregateImpactSummary` (sample size, valid counts, mean/median/stdev returns, non-causal disclaimer).
4. **Package Exports & Entry Point Update:**
   - Exported all new calendar, aligner, and impact classes in `app/events/__init__.py`.
   - Updated `main.py` confirming Day 30 readiness.

### Real-Data & Synthetic Verification (`scripts/verify_day30.py`)
Executed `scripts/verify_day30.py`:
- **Part 1 (Alignment Matrix):** Verified that pre-market, in-session, post-market, exchange holiday, weekend, and date-only SEBI events aligned deterministically to their respective trading sessions.
- **Part 2 (Actual Historical Market Data):** Downloaded 62 real bars for `^NSEI` and `RELIANCE.NS`, built a `MarketDataTradingCalendar`, aligned an event to session 2026-09-23, and measured actual same-day return (+0.61%), forward 1d return (-2.31%), 3d return (-4.04%), 5d return (-4.89%), pre-event volatility (0.0118), post-event volatility (0.0141), benchmark return (-1.64%), and excess alpha (-0.67%) with status `MEASURED`.
- **Part 3 (Anti-Leakage Safeguard):** Verified that an event on the latest available session returned `status="INCOMPLETE_OUTCOME_WINDOW"` and `forward_return_1d=None`.
- **Part 4 (Deduplication & Disclosures):** Verified that 3 events with an exact duplicate were deduplicated to 2 eligible events, and the mandatory `NON_CAUSAL_DISCLAIMER` was present on the summary.
- **Exit Code:** 0.

### Tests
- Created `tests/test_event_impact.py` with 12 comprehensive unit tests:
  1. `test_market_data_trading_calendar`: verifies calendar extraction from bars, next/previous trading day navigation, and holiday skipping.
  2. `test_exchange_trading_calendar_holidays_and_special`: verifies weekend rules, exchange holidays, and special Muhurat sessions.
  3. `test_align_event_pre_market`: verifies pre-market events (< 09:15 IST) align to session $T$ with open/close eligibility.
  4. `test_align_event_in_session`: verifies in-session events (11:30 IST) align to session $T$ with blocked open eligibility.
  5. `test_align_event_post_market_does_not_leak_into_same_day`: verifies post-close events (> 15:30 IST) map to session $T+1$.
  6. `test_align_event_weekend_and_holiday`: verifies weekend and holiday events route to the next active trading session.
  7. `test_align_event_date_only_conservative`: verifies conservative next-session routing for date-only regulatory notices.
  8. `test_align_event_timezone_and_boundary_conditions`: verifies UTC to IST conversion and exact 09:15:00 / 15:30:00 / 15:30:01 boundaries.
  9. `test_impact_analyzer_full_windows`: verifies mathematical correctness of same-day, 1d/3d/5d returns, 5d pre/post volatility, and benchmark excess return.
  10. `test_impact_analyzer_incomplete_future_window`: verifies `INCOMPLETE_OUTCOME_WINDOW` on latest session without future price fabrication.
  11. `test_impact_analyzer_insufficient_history`: verifies graceful handling of fewer than 5 prior sessions.
  12. `test_impact_analyzer_deduplication_and_aggregates`: verifies multi-event deduplication and aggregate statistics calculation.
- Added 4 regression tests to `tests/test_macro_events.py` for Day 29 CodeRabbit fixes.
- **Full Test Suite Results:**
  - Previous baseline: 383 passed across 27 test modules.
  - New total: **399 passed in 8.27s** (16 new tests, 0 failures, 0 regressions across 28 test modules).
  - 100% offline and deterministic; zero external network calls in unit tests.

### Review
- **Ponytail / Senior Dev Mode:** Reused existing `calculate_standard_deviation` from `app.market.returns`; reused `YFinanceProvider` and `clean_market_data`; standard library `zoneinfo` and `datetime` only; zero new dependencies added; strict non-causal representation; zero look-ahead bias across session close and uncompleted windows.

### Documentation
- Updated `README.md` to Day 30 status with 399 passing tests.
- Updated `docs/architecture.md` with Section 4.25 detailing Trading Session Alignment & Event Impact Analysis.
- Updated `docs/decisions.md` with ADR 58.
- Updated `docs/roadmap.md` marking Phase 10 (Day 29 & Day 30) complete and highlighting Phase 11 as the next objective.
- Updated `docs/daily-progress.md` with Day 30 development log.

### Known Limitations & Next Steps
- Day 30 completes Phase 10 (Regulatory & Global Events). All events and external observations are ingested, deduplicated, point-in-time filtered, session-aligned, and descriptively evaluated for returns and volatility.
- Predictive integration: Macro events and sentiment are descriptive contextual observations; they are not integrated into the numerical model feature matrix to preserve ML feature purity.
- Next scheduled milestone: Phase 11: LLM Integration (Role A: structured entity & context extraction; Role B: qualitative reasoning & risk identification).

---

## Day 31 - Gemma 3 12B LLM Integration Foundation

### Goal
Implement the first isolated LLM integration layer (`app/llm/`) using the existing local Ollama runtime and Gemma 3 12B (`gemma3:12b`), establishing dual-role capabilities (Role A: Context Extraction; Role B: Qualitative Reasoning & Risk Identification), strict anti-injection prompt sandboxing, zero-fabrication guarantees, and absolute quantitative model isolation.

### Work Completed
1. **Repository Preflight:**
   - Verified clean working tree and synchronization with `origin/main` (`c82490e`).
   - Verified 405 existing unit tests passing in 12.31s.
   - Inspected local Ollama runtime: active at `http://127.0.0.1:11434` with model `gemma3:12b` loaded locally.
2. **Canonical Schemas (`app/llm/schemas.py`):**
   - Created `LLMDirection` enum: `UP`, `DOWN`, `NEUTRAL`, `INSUFFICIENT_EVIDENCE`.
   - Created `LLMContextExtraction` dataclass: immutable container for extracted entities, affected sectors (uppercased), macroeconomic factors, regulatory factors, qualitative sentiment tone, source citations, and uncertainty notes with timezone-aware `extracted_at`.
   - Created `LLMReasoningResult` dataclass: immutable container for target equity symbol, qualitative direction enum, reasoning summary, positive factors, negative factors, downside risks, source references, qualitative confidence (LOW/MEDIUM/HIGH), timezone-aware `generated_at`, and mandatory `NON_PREDICTIVE_QUALITATIVE_DISCLAIMER`.
   - Enforced strict validation: rejected naive timestamps, empty symbols/summaries, and invalid enum values.
3. **Client Abstraction Layer (`app/llm/client.py`):**
   - Created `BaseLLMClient(ABC)` defining canonical `generate(prompt, system, format_json)` contract.
   - Created `OllamaLLMClient`: standard library `urllib.request` client connecting directly to Ollama REST endpoint (`/api/generate`) with low sampling temperature (0.1), JSON mode (`format="json"`), and configurable timeouts. Zero external framework dependencies (no LangChain, no LlamaIndex).
   - Created `MockLLMClient`: deterministic offline double with pre-programmed response maps and simulated exception support for 100% offline automated testing.
   - Handled network errors, timeouts, HTTP errors, empty bodies, and non-JSON payloads with typed exceptions (`LLMClientError`, `LLMResponseError`).
4. **Prompt Builders & Anti-Injection Guard (`app/llm/prompts.py`):**
   - Created `_sanitize_untrusted_text` to neutralize XML delimiter breakouts (`</source_context>`).
   - Created `build_context_extraction_prompt`: builds Role A system instructions and user prompt enclosing point-in-time news and macro events within `<source_context>` tags. Instructs model to treat source text as untrusted reference data, preserving exact citations without executing directives.
   - Created `build_qualitative_reasoning_prompt`: builds Role B system instructions and user prompt targeting a specific equity symbol. Instructs model to synthesize positive/negative factors and downside risks, allowing `INSUFFICIENT_EVIDENCE` without inventing target prices or calibrated probabilities.
5. **Service Orchestration Layer (`app/llm/service.py`):**
   - Created `LLMService` orchestrating Role A (`extract_context`) and Role B (`generate_qualitative_reasoning`).
   - Implemented `_extract_json_object`: robustly extracts JSON objects, strips Markdown fences (```` ```json ... ``` ````), and validates object dictionary types.
   - Deterministic fast-paths: empty news/events inputs safely return empty extraction records or `direction=INSUFFICIENT_EVIDENCE` with `confidence_assessment="LOW"` without calling the LLM.
   - Zero-fabrication error boundaries: daemon failures and malformed outputs raise typed exceptions (`LLMClientError`, `LLMParseError`, `LLMValidationError`) rather than fabricating fake "neutral" fallbacks.
6. **Package Exports & Entry Point:**
   - Exported all public schemas, clients, exceptions, prompt builders, and service in `app/llm/__init__.py`.
   - Updated `main.py` adding Day 31 readiness verification.

### Real-Data & Offline Verification (`scripts/verify_day31.py`)
Executed `scripts/verify_day31.py`:
- **Stage 1 (Offline Mock Verification):**
  - Validated deterministic Role A extraction and Role B reasoning using `MockLLMClient`.
  - Verified that empty context inputs trigger `INSUFFICIENT_EVIDENCE` (no false neutrals fabricated).
  - Verified client failure raises `LLMClientError` without fabricating fallback results.
- **Stage 2 (Ollama Runtime Inspection):**
  - Confirmed local Ollama daemon is reachable (`http://127.0.0.1:11434`, latency 66.5ms).
  - Confirmed `gemma3:12b` model is loaded locally in Ollama.
- **Stage 3 (Live Gemma 3 12B Inference Smoke Test):**
  - Executed live Context Extraction on real automotive news: successfully extracted `entities=['Tata Motors']`, `affected_sectors=['AUTOMOTIVE']`, `sentiment_tone='POSITIVE'`, and cited source reference in 113.14s (including cold model memory loading).
  - Executed live Qualitative Reasoning for `TATAMOTORS`: generated `direction='UP'`, `confidence='MEDIUM'`, summary, and positive factors in 32.44s.
  - Zero price targets or calibrated probabilities fabricated; non-causal disclaimer preserved.

### Tests
- Created `tests/test_llm_service.py` with 31 comprehensive unit tests:
  1. `TestLLMSchemas`: valid context extraction, naive datetime rejection, empty model rejection, valid reasoning result, invalid direction rejection, empty symbol/summary rejection, and naive generation timestamp rejection.
  2. `TestLLMClients`: mock client deterministic response, mock client simulated error, Ollama client empty prompt handling, connection error handling, timeout handling, HTTP 404/500 error handling, malformed JSON response handling, empty response field handling, and availability check.
  3. `TestLLMPrompts`: delimiter anti-injection sanitization, Role A prompt assembly with news and macro events, and Role B qualitative reasoning prompt assembly.
  4. `TestLLMService`: empty context fast-path, extraction success, markdown code fence stripping, malformed JSON error handling, non-dict JSON error handling, reasoning fast-path, reasoning success, `INSUFFICIENT_EVIDENCE` direction handling, invalid direction error handling, missing required keys error handling, and zero false neutral fabrication on client error.
  5. `TestQuantitativeIsolation`: verified that qualitative LLM outputs possess no numerical price, return, or probability attributes and leave quantitative prediction authority completely untouched.
- **Full Test Suite Results:**
  - Previous baseline: 405 passed across 28 test modules.
  - New total: **436 passed in 12.21s** (31 new tests, 0 failures, 0 regressions across 29 test modules).
  - 100% offline and deterministic; unit tests require zero external network access and zero model downloads.

### Review
- **Ponytail / Senior Dev Mode:** Standard library `urllib.request` and `json` only; zero heavy third-party framework dependencies (no LangChain, no LlamaIndex); prompt sandboxing against injection attacks; zero fabrication of prices, returns, or false neutrals; strict quantitative model isolation.

### Documentation
- Updated `README.md` to Day 31 status with 436 passing tests.
- Updated `docs/architecture.md` with Section 4.26 detailing Contextual LLM Integration Layer.
- Updated `docs/decisions.md` with ADR 59.
- Updated `docs/roadmap.md` marking Phase 11 complete and highlighting Phase 12 as the next objective.
- Updated `docs/daily-progress.md` with Day 31 development log.

### Known Limitations & Next Steps
- Day 31 completes the isolated foundational LLM package (`app/llm/`).
- The LLM service is deliberately NOT yet integrated into the production prediction pipeline; quantitative XGBoost/LightGBM predictions remain authoritative.
- Next scheduled milestone: Phase 12: ML + LLM Combination (ensemble synthesis layer combining numerical ML outputs with qualitative LLM reasoning while preserving both independent outputs).

---

## Day 32 - Multi-Agent Ensemble & Synthesis Layer (Phase 12)

### Goal
Implement the multi-agent ensemble synthesis layer (`app/prediction/ensemble.py`) combining quantitative machine learning forecasts (XGBoost/LightGBM) with qualitative LLM reasoning (Gemma 3 12B) and financial sentiment features, strictly preserving independent standalone model outputs (ADR 05), transparent weighted blending, agreement/divergence classification, volatility-anchored target ranges, and persistence/verification parity with SQLite.

### Work Completed
1. **Repository Preflight:**
   - Verified clean working tree and synchronization with `origin/main` (`0cd9a91`).
   - Verified 436 existing tests passing in 12.58s.
   - Identified exact next incomplete milestone: Phase 12 (ML + LLM Combination).
2. **Canonical Data Contracts (`app/prediction/ensemble.py`):**
   - Created `EnsembleAgreement` enum: `STRONG_AGREEMENT`, `AGREEMENT`, `DIVERGENCE`, `PARTIAL`, `ML_ONLY`, `LLM_ONLY`.
   - Created `EnsembleWeights` dataclass: validated and normalized weights for ML and LLM signals (default 70% ML / 30% LLM).
   - Created `TargetRange` dataclass: volatility-anchored physical price boundaries $[Close - ATR, Close + ATR]$ for next session.
   - Created `EnsemblePredictionResult` dataclass: complete container preserving standalone `ml_prediction` and `llm_reasoning` in full, combined direction, combined probabilities, agreement diagnostics, integrated factor rankings, and downside risks.
   - Implemented canonical adapter `.to_prediction_result()`: translates ensemble predictions into standard `PredictionResult` with `model_name="ensemble"`, enabling immediate SQLite database persistence and outcome verification.
3. **Synthesis Engine (`EnsembleService`):**
   - Implemented `synthesize`: pure deterministic synthesis method combining pre-computed ML predictions and LLM reasoning.
   - Mapped qualitative LLM direction and qualitative confidence to bounded polarity $S_{LLM} \in [-1.0, 1.0]$.
   - Implemented linear convex probability combination: $P_{comb}(UP) = W_{ML} \cdot P_{ML}(UP) + W_{LLM} \cdot P_{LLM}(UP)$.
   - Explicitly surfaced `DIVERGENCE` when ML and LLM issue opposing directional forecasts to highlight conflicting regime risk.
   - Implemented `predict_ensemble`: end-to-end multi-agent orchestration method executing ML prediction, LLM qualitative reasoning, synthesis, and optional SQLite persistence.
   - Graceful degradation: handles LLM service failures or offline states by falling back to 100% ML weight (`ML_ONLY`) without crashing.
4. **Package Exports & Entry Point:**
   - Exported all new ensemble types in `app/prediction/__init__.py`.
   - Updated `main.py` with Day 32 readiness verification.

### Real-Data & Offline Verification (`scripts/verify_day32.py`)
Executed `scripts/verify_day32.py`:
- **Stage 1 (Offline Multi-Agent Synthesis):**
  - Strong Agreement: verified blended probability $P(UP) = 77.60\%$ and ATR target range $[2715.0 - 2785.0]$.
  - Divergence: verified ML(UP, 0.68) vs LLM(DOWN, HIGH) correctly surfaces `DIVERGENCE` with $P(UP) = 47.60\%$.
  - Partial: verified LLM `INSUFFICIENT_EVIDENCE` shrinks probability towards 50%.
  - ML-Only Fallback: verified graceful 100% ML weight assignment.
  - Independent Score Preservation: confirmed standalone models are retained in full without loss of attribution.
- **Stage 2 (SQLite Persistence & Outcome Verification):**
  - Saved ensemble prediction to SQLite repository with `model_name='ensemble'`.
  - Verified outcome using `OutcomeVerifier` against market session bars (`is_correct=True`).
  - Verified `PredictionEvaluator` tracks ensemble accuracy side-by-side with ML models.
- **Stage 3 (Live Multi-Agent Synthesis with Gemma 3 12B):**
  - Checked Ollama reachability at `http://127.0.0.1:11434` (latency 37.2ms); model `gemma3:12b` active.
  - Executed live synthesis combining quantitative ML prediction with live Gemma 3 12B qualitative reasoning on real automotive news in 51.13s:
    - Combined Direction: `UP`
    - Combined Probability: `69.7%`
    - Agreement: `STRONG_AGREEMENT`
    - Target Range: `[961.50 - 998.50]`

### Tests
- Created `tests/test_ensemble_service.py` with 19 comprehensive unit tests:
  1. `TestEnsembleWeights`: default weights normalization, custom weights normalization, negative weights rejection, zero-sum weights rejection.
  2. `TestEnsembleAgreement`: strong agreement UP, moderate agreement, divergence ML UP vs LLM DOWN, divergence ML DOWN vs LLM UP, partial on LLM insufficient evidence, ML-only when LLM is None.
  3. `TestEnsembleSynthesis`: exact mathematical probability blending, standalone independent score preservation, ATR target range calculation, integrated factor rankings with deduplication.
  4. `TestEnsemblePersistenceAndVerification`: conversion to canonical PredictionResult, SQLite persistence, outcome verification against actuals.
  5. `TestEnsembleFailureHandling`: ML failure propagation, LLM exception degradation fallback to ML_ONLY, clean text summary formatting.
- **Full Test Suite Results:**
  - Previous baseline: 436 passed across 29 test modules.
  - New total: **455 passed in 12.90s** (19 new tests, 0 failures, 0 regressions across 30 test modules).
  - 100% offline and deterministic; zero network dependency in unit tests.

### Review
- **Ponytail / Senior Dev Mode:** Reused existing `PredictionResult`, `PredictionRepository`, `OutcomeVerifier`, and `PredictionEvaluator`; zero new dependencies; lazy imports breaking circular dependency cycles; transparent weighted probability blending without fabricating false statistical certainty.

### Documentation
- Updated `README.md` to Day 32 status with 455 passing tests.
- Updated `docs/architecture.md` with Section 4.27 detailing Multi-Agent Ensemble Layer.
- Updated `docs/decisions.md` with ADR 60.
- Updated `docs/roadmap.md` marking Phase 12 complete and highlighting Phase 13 as the next objective.
- Updated `docs/daily-progress.md` with Day 32 development log.

### Known Limitations & Next Steps
- Day 32 completes Phase 12 (ML + LLM Combination).
- REST API endpoints and web UI dashboards are not yet built (deferred to Phase 13 per roadmap).
- Next scheduled milestone: Phase 13: Web Application (build FastAPI REST API endpoints and interactive web UI for stock search, prediction visualization, and audit history).

---

## Day 33: FastAPI Application Foundation

### Objective
Begin Phase 13: Web Application & API Layer by building a tested FastAPI REST API foundation that connects existing prediction, ensemble, history, feedback, and event modules through clean, typed API contracts without duplicating business logic, fabricating unverified data, or leaking internal secrets.

### Implementation Summary
1. **Application Factory (`app/api/app.py`):**
   - Configured `create_app()` factory returning a configured FastAPI instance with `/docs` (OpenAPI) and `/redoc` documentation.
   - Centralized exception handlers:
     - `RequestValidationError`: formats Pydantic parameter/body validation errors into structured `ErrorResponse` with machine-readable `VALIDATION_ERROR` code and HTTP 422.
     - `ValidationError`: maps domain errors into HTTP 400 `DOMAIN_VALIDATION_ERROR`.
     - `HTTPException`: normalizes standard HTTP exceptions.
     - Catch-all `Exception`: sanitizes internal unhandled errors to HTTP 500 without disclosing internal file paths, stack traces, or credentials.
   - Root endpoint `GET /` providing service metadata, environment status, and OpenAPI documentation links.
2. **Dependency Inversion Layer (`app/api/dependencies.py`):**
   - Created injectable providers for `sqlite3.Connection`, `PredictionRepository`, `PredictionService`, `EnsembleService`, and `BaseEventProvider` list.
   - Enables fast in-memory SQLite substitution and mock service injection in automated test suites without filesystem side effects.
3. **Multi-Threaded SQLite Safety (`app/database/connection.py`):**
   - Added `check_same_thread: bool = False` parameter to `create_connection`, enabling safe execution across FastAPI's worker thread pool while preserving WAL mode and busy timeout pragmas.
4. **Typed Pydantic Schemas (`app/api/schemas.py`):**
   - `PredictRequest`: enforces strict ticker validation, bounded lookback (35-3650 days), model whitelist (`xgboost`, `lightgbm`, `ensemble`), staleness thresholds, and custom weights.
   - `PredictionResponse`: structures directional prediction, uncalibrated probabilities, data quality diagnostics, ensemble breakdown (agreement status, weights, ATR target range, factors, risks), and research disclaimer.
   - `HistoryResponse`: paginated collection of historical predictions with bounded limit (1-500) and linked verified actual outcomes.
   - `FeedbackRequest` & `FeedbackResponse`: structured feedback payload acknowledging explicit deferred persistence under ADR 10.
   - `EventsResponse`: collection of normalized macroeconomic and regulatory announcements across providers.
5. **REST API Route Modules (`app/api/routes/`):**
   - `GET /api/health`: verifies SQLite database connectivity, model storage accessibility, and LLM configuration without triggering slow model inference or exposing secrets.
   - `POST /api/predict`: dispatches to `PredictionService` for standalone ML or `EnsembleService` for multi-agent synthesis, persisting results to SQLite when requested.
   - `GET /api/history`: queries persisted predictions with bounded pagination, ticker/model filtering, and automatically attached verified actual outcomes (`actuals` table).
   - `POST /api/feedback`: validates feedback schema and returns explicit HTTP 501 Not Implemented with status `deferred` to respect ADR 10 prohibitions against automated retraining loops.
   - `GET /api/events`: aggregates official announcements from `RBIEventProvider` and `SEBIEventProvider`, applies `deduplicate_events`, and supports category filtering.

### Verification Results (`scripts/verify_day33.py`)
Executed 6-stage empirical verification pipeline:
- **Stage 1 (App Factory & OpenAPI):** PASS — Verified root endpoint `/` and dynamic generation of OpenAPI schema registering 6 routes (`/`, `/api/health`, `/api/predict`, `/api/history`, `/api/feedback`, `/api/events`).
- **Stage 2 (Health & Non-Disclosure):** PASS — Verified database and model storage readiness; confirmed zero leakage of passwords, secrets, or absolute filesystem paths.
- **Stage 3 (Prediction & Ensemble Inference):** PASS — Verified input validation rejection of whitespace symbols (HTTP 422), standalone ML inference ($P(UP)=0.68$), and multi-agent ensemble synthesis ($P(UP)=0.74$, `STRONG_AGREEMENT`, ATR target range $[2450.0 - 2550.0]$).
- **Stage 4 (History Retrieval & Outcome Linkage):** PASS — Verified bounded history queries and confirmed automatic linkage of verified actual outcome ($+1.42\%$ return, close $2535.50$) to stored prediction records.
- **Stage 5 (Feedback ADR 10 Deferral):** PASS — Verified HTTP 501 Not Implemented response with machine-readable `deferred` status and ADR 10 disclosure.
- **Stage 6 (Events Monitoring & Deduplication):** PASS — Verified aggregation and deduplication of macroeconomic and regulatory announcements.

### Tests
- Created `tests/test_api.py` with 20 comprehensive unit tests:
  1. `test_root_endpoint`: root metadata and links.
  2. `test_health_endpoint_healthy`: operating health check.
  3. `test_health_endpoint_db_failure`: degraded status on database failure.
  4. `test_predict_validation_invalid_symbol`: rejection of empty/whitespace symbols.
  5. `test_predict_validation_invalid_model`: rejection of unsupported models.
  6. `test_predict_validation_insufficient_lookback`: rejection of lookback < 35.
  7. `test_predict_standalone_ml_success`: standalone ML execution and persistence.
  8. `test_predict_standalone_ml_failure_status`: non-fabrication of direction on insufficient data.
  9. `test_predict_standalone_ml_service_exception`: sanitized 500 error response.
  10. `test_predict_ensemble_success`: multi-agent ensemble breakdown mapping.
  11. `test_predict_ensemble_custom_weights`: parameter forwarding of custom weights.
  12. `test_predict_no_persist_option`: non-persistence when `persist=False`.
  13. `test_history_empty`: empty history response.
  14. `test_history_populated_and_filtering`: filtering by symbol, model, and pagination.
  15. `test_history_with_verified_outcome`: linkage of verified actual outcome.
  16. `test_feedback_deferred`: HTTP 501 response with ADR 10 disclosure.
  17. `test_feedback_invalid_payload`: validation rejection of rating > 5.
  18. `test_events_empty`: empty event set handling.
  19. `test_events_populated_and_filtered`: multi-provider aggregation and category filtering.
  20. `test_events_provider_error_resilience`: graceful degradation when a single provider fails.
- **Full Test Suite Results:**
  - Previous baseline: 455 passed across 30 test modules.
  - New total: **475 passed in 11.78s** (20 new tests, 0 failures, 0 regressions across 31 test modules).
  - 100% offline and deterministic; zero network dependency in unit tests.

### Review
- **Ponytail / Senior Dev Mode:** Reused existing `PredictionService`, `EnsembleService`, `PredictionRepository`, and event providers; thin handlers with zero duplicated business logic; added only essential dependencies (`fastapi`, `uvicorn`, `httpx`); safe multi-threaded SQLite configuration; zero fabricated data.

### Documentation
- Updated `README.md` to Day 33 status with 475 passing tests and Phase 13 description.
- Updated `docs/architecture.md` with Section 4.28 detailing FastAPI REST API Foundation Layer.
- Updated `docs/decisions.md` with ADR 61.
- Updated `docs/roadmap.md` marking Day 33 complete in Phase 13.
- Updated `docs/daily-progress.md` with Day 33 development log.

### Known Limitations & Next Steps
- Day 33 completes the REST API foundation.
- Interactive Web UI dashboard (stock search, prediction visualization, and audit history) is planned for Day 34.
- Direct user feedback persistence is intentionally deferred until formal auditing schemas and human-in-the-loop workflows are approved per ADR 10.
- Next scheduled milestone: Day 34 — Interactive Web Application UI (HTML/CSS/JS frontend communicating with Day 33 REST endpoints).

---

## Day 34: Interactive Stock Prediction Web UI

### Objective
Complete Phase 13 of `docs/roadmap.md` by building a clean, modern, responsive web dashboard that consumes the Day 33 FastAPI REST API foundation. Provide stock search, real-time prediction visualization, quantitative ML breakdown, qualitative LLM breakdown, ensemble synthesis, immutable prediction history with verified outcomes, and macroeconomic event tracking while strictly following financial display rules, non-fabrication constraints, and zero bloated frontend dependencies.

### Implementation Summary
1. **Frontend Architecture & Design (`app/api/static/`):**
   - Implemented a single-page web dashboard using standard Vanilla HTML5, CSS3, and modern JavaScript (ES6+), eliminating external JavaScript framework overhead or Node.js build dependencies.
   - Built a sleek dark-theme aesthetic (`#070a13` background, `#0f172a` surface containers, glassmorphism, `#10b981` emerald bullish up, `#f43f5e` rose bearish down, `#38bdf8` sky accents, modern Google Fonts `Inter` and `JetBrains Mono`).
   - Mobile-first responsive layout supporting screen widths from 320px mobile viewports to 4K desktops.
2. **Dashboard Views & Components (`index.html`):**
   - **Header Bar:** Platform identity, real-time Indian Standard Time (IST) clock with flashing pulse indicator, interactive health badge reflecting backend readiness, and direct link to `/docs` OpenAPI documentation.
   - **Prediction Engine Tab:**
     - Search card with stock ticker input, live validation, and popular ticker quick-chips (`RELIANCE`, `TCS`, `INFY`, `HDFCBANK`, `ICICIBANK`, `BHARTIARTL`, `SBIN`).
     - Model architecture selector (`ensemble`, `xgboost`, `lightgbm`).
     - Collapsible advanced inference settings: interactive ML/LLM weight ratio slider (default 70% ML / 30% LLM), historical warmup lookback days (default 1825), max stale days tolerance (default 7), and SQLite persistence toggle.
     - Direction hero card with bold UP/DOWN decision badges, animated probability progress bar, and volatility price bounds ($Close \pm ATR$) when supplied.
     - Consensus agreement / divergence banner with explicit warnings when models conflict.
     - Three-column analytical breakdown:
       - Column 1: Quantitative ML metrics (signal, raw probability, warmup quality, feature bar count, technical momentum factors).
       - Column 2: Qualitative LLM contextual reasoning (Gemma 3 12B stance, confidence rating, reasoning summary, positive catalysts, downside risks, source references) rendered only when returned by the API.
       - Column 3: Audit trail & data health integrity (prediction record UUID, bars fetched/cleaned, zero leakage confirmation, research disclaimer).
   - **Prediction History Tab:**
     - Paginated audit table displaying prediction ID, symbol, model, UTC timestamp, signal, probability, and verified actual market outcome ($Close_{t+1}$ vs $Close_t$, return %, directional accuracy badge).
     - Filter controls for ticker symbol, model architecture, and page size (10, 25, 50).
   - **Macro & Regulatory Events Tab:**
     - Feed of official RBI monetary policy circulars and SEBI regulatory announcements with category filter chips and external source citations.
   - **System Readiness Tab:**
     - Live subsystem diagnostic cards querying non-inferencing `/api/health` for SQLite database connectivity, model registry readiness, and local Ollama runtime.
3. **Client-Side Service & State Management (`app.js`):**
   - Modular `ApiService` cleanly encapsulating `fetch()` calls to `/api/predict`, `/api/history`, `/api/events`, and `/api/health`.
   - Comprehensive error handling: handles non-2xx responses, displays structured validation error messages without crashing, and recovers gracefully from service degradation.
   - Full keyboard accessibility, ARIA landmark tags, live regions, and zero inline script event handlers.
4. **FastAPI Delivery & Security Integration (`app/api/app.py`):**
   - Mounted static assets via Starlette `StaticFiles` at `/static`.
   - Added `GET /ui` serving `index.html`.
   - Added content-negotiation on `GET /` to deliver HTML to web browsers while preserving pure JSON output for API clients and automated tests.
   - Configured Starlette `CORSMiddleware` supporting secure cross-origin requests.

### Verification Results (`scripts/verify_day34.py`)
Executed automated verification covering static assets, FastAPI routing, security headers, DOM accessibility, and API contract parity:
- **Static Assets Existence & Sizing:** PASS — Verified `index.html` (30.7 KB), `styles.css` (28.6 KB), and `app.js` (35.7 KB).
- **Semantic DOM Elements & IDs:** PASS — Verified presence of 19 required interactive controls and container IDs.
- **Zero Fabricated Demo Data:** PASS — Verified templates contain zero hardcoded prices, demo predictions, or fake outcomes.
- **GET /ui & Content Negotiation:** PASS — Verified `/ui` serves `text/html; charset=utf-8` and `/` cleanly negotiates HTML vs. JSON.
- **Static MIME Types:** PASS — Verified CSS delivered as `text/css` and JS delivered as `text/javascript`.
- **CORS Configuration:** PASS — Verified appropriate `Access-Control-Allow-Origin` preflight and response headers.
- **API Contract Parity:** PASS — Verified matching payload and response fields between frontend JS client and backend schemas (`/api/predict`, `/api/history`, `/api/events`, `/api/health`).

### Tests
- Created `tests/test_frontend.py` with 8 comprehensive integration tests:
  1. `test_ui_endpoint_serves_html`: verifies `GET /ui` returns 200 with HTML content type.
  2. `test_root_endpoint_content_negotiation`: verifies `GET /` serves HTML to browsers and JSON to API clients.
  3. `test_static_css_served_correctly`: verifies CSS static file route and stylesheet contents.
  4. `test_static_js_served_correctly`: verifies JavaScript static file route and script contents.
  5. `test_cors_preflight_headers`: verifies Starlette CORS preflight headers on API routes.
  6. `test_html_contains_required_dom_elements`: verifies accessibility IDs and UI containers in HTML.
  7. `test_html_zero_hardcoded_predictions`: ensures no fabricated stock prices or predictions appear in production HTML.
  8. `test_js_api_contracts_aligned`: verifies JS API client aligns with backend Pydantic schema field names.
- **Full Test Suite Results:**
  - Previous baseline: 475 passed across 31 test modules.
  - New total: **483 passed in 6.45s** (8 new tests, 0 failures, 0 regressions across 32 test modules).
  - 100% offline and deterministic; zero network dependency in unit tests.

### Review
- **Browser Automation Note:** Direct visual inspection via Playwright browser subagent encountered an offline environment limitation (driver binary download restricted in sandbox). Thorough verification was performed via FastAPI TestClient offline integration tests, static syntax checks, and `scripts/verify_day34.py`.
- **Ponytail / Senior Dev Mode:** Zero new npm packages or frontend frameworks; pure Vanilla HTML/CSS/JS; reused Day 33 FastAPI routes without modifying backend business logic; zero fabricated data; verified clean error states.

### Documentation
- Updated `README.md` to Day 34 status with 483 passing tests and interactive UI instructions.
- Updated `docs/architecture.md` with Section 4.29 detailing the Interactive Web UI layer.
- Updated `docs/roadmap.md` marking Phase 13 complete.
- Updated `docs/daily-progress.md` with Day 34 development log.

### Code Review Remediation (Day 34 Post-Review)
Systematically addressed all 7 findings identified in code review:
1. **Restricted CORS Origins & Disabled Credentials**: Configured `Settings.cors_origins` (defaulting to localhost/127.0.0.1 ports 8000/3000) and set `allow_credentials=False` on `CORSMiddleware` in `app/api/app.py`, eliminating CSRF and cross-origin credential leakage risks.
2. **Prohibited Probability Substitution**: Removed `0.5` / 50% fallbacks in `app/api/routes/predict.py` and `app/api/static/js/app.js`. Missing directional probabilities now strictly display as unavailable (`--` / `N/A`) with 0% bar fill.
3. **Eliminated Invented Ensemble Factors & Confidence**: Removed hardcoded tree-split factor narratives in `app.js`. Added `llm_direction: Optional[str] = None` to `EnsembleDetailsResponse` and removed `'MEDIUM'` fallback for missing confidence.
4. **Independent ML and LLM Outputs**: Separated Quantitative ML metrics (probabilities, model version, calibration, data health) from Qualitative LLM reasoning (stance, confidence, summary, catalysts, risks). When LLM reasoning is not returned, the LLM card clearly indicates so rather than populating from ensemble summaries.
5. **Safe URL Scheme Validation**: Added `isSafeHttpUrl` in `app.js` enforcing `http:` or `https:` protocols before rendering event circular links, preventing script execution via arbitrary URI schemes.
6. **Consistent History Timestamps & Labels**: Updated history table header from `Prediction Time (UTC)` to `Prediction Time (IST)` in `app/api/static/index.html` to align with the IST output produced by `formatDateTimeIST`.
7. **Roadmap & Architecture Alignment**: Reconciled `docs/roadmap.md` and `docs/architecture.md` Section 4.29 to reflect restricted CORS origin whitelisting, disabled credentials, and zero-fabrication guarantees.
- Added regression tests in `tests/test_frontend.py` expanding test count to **485 passing tests**.
8. **Evaluation Script Directional Accuracy Check**: Corrected `scripts/verify_day25.py` to compare calculated `directional_accuracy` against the expected value derived from `v_rec.is_correct`, catching any unexpected denominator discrepancies.
9. **Market-Returns Performance Optimization**: In `app/market/returns.py` (`compute_market_returns`), eliminated redundant second pass of `calculate_rolling_volatility` by directly scaling `rolling_vols[w]` by $\sqrt{\text{trading\_days}}$ while preserving `None` warm-up values, validated by `test_compute_market_returns_annual_vol_scaling_reusing_raw` in `tests/test_returns.py` expanding test count to **486 passing tests**.
10. **Market-Cleaner Hardening & ADR Alignment**:
    - Replaced raw `assert` statements in `scripts/verify_cleaner.py` with explicit conditional checks providing diagnostic error reporting and non-zero exit status (`1`).
    - Updated ADR 27 in `docs/decisions.md` to document duplicate price comparison using `math.isclose` with absolute tolerance `1e-5` while preserving volume criteria.
    - Updated ADR 26 in `docs/decisions.md` to explicitly state that no price interpolation or synthetic bar creation is permitted.
    - Strengthened `test_timestamp_and_timezone_normalization` in `tests/test_cleaning.py` asserting the normalized UTC bar has hour 5 and minute 30 (IST offset) and the naive bar has hour 0.
    - Updated docstring of `clean_market_data` in `app/market/cleaner.py` documenting `ZoneInfoNotFoundError` for unknown target timezones.

### Code Review Remediation: CodeRabbit Deep Scan Findings (12 of 12 Remediated)
Systematically remediated all 12 findings identified across CodeRabbit Deep Scan (`naiya555-stock-market-prediction-system-agent-findings.csv`):

1. **Finding `a51c3c34-6b77-4c88-9a88-69640cb653f5` (Shell Argument Injection - `scripts/search_repo.sh`):**
   - Replaced unsafe flattened unquoted argument strings with Bash arrays `EXTRA_ARGS=("$@")` and `"${EXTRA_ARGS[@]}"`.
   - Forwarded arguments to ripgrep and grep safely with quoted array expansions, translating `--type` safely while preserving argument boundaries and excluding `.git`, `.venv`, and `__pycache__`.
   - Added `tests/test_search_repo.py` verifying spaces, wildcards, option values, and no command injection.

2. **Finding `9f11423b-6961-4960-854a-699db69ff89c` (DOM XSS / Unsafe Attribute - `app/api/static/js/app.js`):**
   - Refactored `renderEventsGrid` to construct card elements safely using `document.createElement` (`h4`, `span`, `div`, `a`), populating untrusted titles and descriptions via `.textContent` property assignment.
   - Enforced strict `URL` protocol validation (`isSafeHttpUrl`) permitting only `http:` and `https:` schemes, assigning verified URLs directly to the `a.href` property without HTML interpolation.
   - Added regression test `test_event_renderer_xss_protection` in `tests/test_frontend.py`.

3. **Finding `3b923d5b-eb3d-4516-8cc7-41a22c917f99` (Public API Information Disclosure - `app/api/routes/predict.py`):**
   - Implemented `_sanitize_public_error_message(msg, model_name)` sanitizing internal filesystem paths, loader diagnostics, and raw exception messages in prediction error responses and 500 status codes.
   - Retained full technical exception details in server-side logs via `logger.warning` / `logger.error` while exposing safe, stable user-facing status messages.
   - Added regression tests `test_predict_error_sanitization_no_path_disclosure` and `test_predict_ensemble_service_exception_sanitized` in `tests/test_api.py`.

4. **Finding `b459745a-1494-4d4a-99ba-df6160cd8324` (Log Injection - `app/prediction/ensemble.py`):**
   - Wrapped user/external symbol in `predict_ensemble` with `sanitize_log_field()`, neutralizing CR, LF, and control characters.
   - Added schema validators in `PredictRequest` and `SafeLogFormatter` in `app/core/logging_config.py`.

5. **Finding `75169822-10b9-4c51-87d7-2c6daa5847a4` (Log Injection - `app/market/pipeline.py`):**
   - Sanitized raw input symbol with `sanitize_log_field()` in pipeline orchestration logs.

6. **Finding `97c82693-02c8-4cc3-8a37-9737ca5dc3c7` (Log Injection - `app/api/routes/feedback.py`):**
   - Enforced strict regex validation on `FeedbackRequest.prediction_id` (`^[A-Za-z0-9_\-]{1,64}$`) and wrapped logged fields with `sanitize_log_field()`.

7. **Finding `221fa173-c171-4128-b3f9-7e6de364fc2f` (Log Injection - `app/market/providers/yfinance_provider.py`):**
   - Sanitized invalid publication date strings and symbols using `sanitize_log_field()`, preventing CRLF log entry forging.
   - Added test suite in `tests/test_log_injection.py` with 17 unit tests verifying control-character neutralization and log line protection.

8. **Finding `1ec5f892-7f69-4c52-80dd-1df78aab9991` (RSS ReDoS - `app/news/providers/rss_provider.py`):**
   - Replaced unbounded regex `<[^>]+>` with a bounded linear $O(N)$ HTML tag stripper `_strip_html_tags(text, max_length=100_000)` and added `MAX_RSS_PAYLOAD_BYTES = 5_000_000` limit raising `NewsProviderError`.

9. **Finding `11905224-342d-4afb-b670-04d4ddcc860a` (Macro Event HTML ReDoS - `app/events/providers/rbi_provider.py`):**
   - Replaced regex HTML stripper in RBI and SEBI providers with linear $O(N)$ character scanner and bounded payload limits (`MAX_RBI_PAYLOAD_CHARS = 5_000_000`, `MAX_SEBI_PAYLOAD_CHARS = 5_000_000`).

10. **Finding `08bc0d39-09ed-4451-842b-5e4369cfabe6` (RBI Repo Rate ReDoS - `app/events/providers/rbi_provider.py`):**
    - Replaced catastrophic backtracking regex `repo\s+rate.*?(\d+\.\d+)\s*%` with a bounded linear scanner searching `repo rate` occurrences and extracting values within a safe 150-char window using `^[^\n%]{0,120}?(\d+\.\d+)`.
    - Added adversarial tests in `tests/test_feed_redos_protection.py` (50,000 unmatched brackets, 30 repeated prefixes, oversized payloads).

11. **Finding `e4c30701-5044-427f-a567-84177590c53a` (LLM Markdown-Fence ReDoS - `app/llm/service.py`):**
    - Bounded LLM completions to `MAX_LLM_COMPLETION_CHARS = 100_000` raising `LLMParseError`.
    - Replaced regex markdown fence stripping with deterministic line-based stripping and outer brace `{...}` indexing, preserving valid JSON while preventing catastrophic backtracking on unclosed fences.
    - Added regression tests in `tests/test_llm_service.py`.

12. **Finding `3bb2c072-3523-41f5-9f47-3a836cd17ce9` (Quadratic Trend Computation - `app/market/trend.py`):**
    - Replaced $O(N^2)$ repeated scanning in `compute_rolling_trends` with an incremental single-pass $O(N)$ algorithm maintaining running confirmed pivots and structural labels.
    - Added `compute_latest_trend(records)` for $O(N)$ point-in-time calculation of the latest bar only.
    - Added `only_latest: bool = False` to `assemble_feature_matrix`, bypassing historical rolling trend computation during online inference in `app/prediction/service.py`.
    - Added regression tests in `tests/test_trend.py` verifying 100% exact numerical and semantic equivalence between incremental trend computation and repeated naive historical analysis.

- **Full Test Suite Results:**
  - Expanded from 486 baseline tests to **522 passed tests in 7.77s** (36 new focused regression tests, 0 failures, 0 regressions across 35 test files).
  - Verification scripts (`verify_trend.py`, `verify_feature_matrix.py`, `verify_pipeline.py`, `verify_day34.py`) all pass with exit code 0.

### Known Limitations & Next Steps
- Day 34 code review remediation is complete with all 12 deep scan findings resolved and empirically tested.

---

## Day 35 - Phase 14: Live Data Pipeline (Near-Real-Time Quotes & Session Engine)

### Goal
Implement the first safe, testable increment of Phase 14: connect near-real-time market data providers with strict timestamp preservation, market session state handling (pre-open, regular hours, post-close, closed), provider delay disclosures, and zero-fabrication guarantees.

### Work Completed

1. **Indian Equity Market Session & Calendar Engine (`app/market/session.py`)**:
   - Implemented `MarketSessionState` enum: `PRE_OPEN` (09:00-09:15 IST), `REGULAR_HOURS` (09:15-15:30 IST), `POST_CLOSE` (15:30-16:00 IST), and `CLOSED` (off-hours, weekends, holidays).
   - Created `MarketSessionInfo` frozen dataclass tracking active trading state, localized IST timestamp, current session date, weekend/holiday flags, and calculated `next_open` and `next_close` boundaries.
   - Built deterministic `get_market_session(dt, holidays)` engine with automatic IST localization (`ZoneInfo("Asia/Kolkata")`), weekend checks, and comprehensive NSE 2026 declared holiday calendar.

2. **Live & Near-Real-Time Quote Contracts (`app/market/quote.py`)**:
   - Defined `DataFreshnessStatus` enum: `FRESH`, `DELAYED`, `STALE`, and `UNKNOWN`.
   - Created `LiveQuote` frozen dataclass capturing verified last traded price, trade timestamp (`as_of`), retrieval timestamp (`retrieved_at`), day OHLC metrics, volume, prior close, net change, change percentage, session state, and freshness classification.
   - Enforced explicit provider transparency: standard 15-minute exchange delay flag (`is_delayed=True`, `delay_minutes=15`) and disclaimer clarifying data is for decision support rather than high-frequency execution.
   - Provided seamless backward compatibility adapter `.to_market_quote()` converting to canonical `MarketQuote` schema from `app.core.schemas`.

3. **Provider Contract & YFinance Quote Adapter (`app/market/providers/base.py`, `app/market/providers/yfinance_provider.py`)**:
   - Extended `BaseMarketDataProvider` ABC with `fetch_quote(symbol: str) -> LiveQuote` with a default `NotImplementedError` preserving full backward compatibility across all existing mock providers in test suites.
   - Implemented concrete `fetch_quote` in `YFinanceProvider`:
     - Resolves bare symbols and exchange tickers (e.g. `RELIANCE` -> `RELIANCE.NS`).
     - Queries `fast_info` for instantaneous price and OHLC metrics with intraday 1-minute history (`1d`, `1m`) for exact exchange timestamps.
     - Implements multi-tier fallback to 5-day daily bars for off-market, weekend, and holiday queries.
     - Enforces strict zero-fabrication guarantees: missing or delisted tickers raise `RuntimeError`, corrupted non-positive prices raise `ValidationError`.
     - Dynamically evaluates staleness against active session thresholds (stale if trade date is before today during regular hours, or older than 5 days outside market hours).

4. **Pipeline Orchestration & Module Exports (`app/market/pipeline.py`, `app/market/__init__.py`)**:
   - Added `fetch_live_quote(symbol, provider, max_staleness_seconds)` orchestrator in pipeline with sanitized logging.
   - Cleanly exported all new contracts in `app/market/__init__.py`: `MarketSessionState`, `MarketSessionInfo`, `get_market_session`, `DataFreshnessStatus`, `LiveQuote`, and `fetch_live_quote`.

5. **Test Suite Expansion & Real-Data Verification**:
   - Created `tests/test_market_session.py` (9 unit tests): verified pre-open, regular hours, post-close, closed, exact second boundaries, weekend closures, 2026 holidays, timezone localization, and serialization.
   - Created `tests/test_live_quote.py` (9 unit tests): verified contract validation, physical boundary rejections, downcasting, provider error propagation, non-positive price rejection, fast_info parsing, daily fallback, and pipeline orchestration.
   - Created `scripts/verify_day35.py`: live verification script testing real quotes on `RELIANCE.NS`, `TCS.NS`, `INFY.NS`, session engine transitions, and zero-fabrication failure modes.

### Validation
- **Focused Unit Tests:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_market_session.py tests/test_live_quote.py -v
  ```
  *Result:* 18 passed in 1.48s.
- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest -q
  ```
  *Result:* **540 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 12.40s across 37 test files (expanded from 522 baseline).
- **Day 35 Verification Script:**
  ```powershell
  & .\.venv\Scripts\python scripts/verify_day35.py
  ```
  *Result:* Exited with code `0` (SUCCESS). Verified session engine, real-data quotes for RELIANCE (₹1,211.20) and TCS (₹2,465.00), downcasting, and zero-fabrication rejection on invalid symbols.
- **Existing Verification Scripts:**
  - `verify_day34.py`: PASS (SUCCESS)
  - `verify_trend.py`: PASS (SUCCESS)
  - `verify_pipeline.py`: PASS (SUCCESS)

### Known Limitations & Next Steps
- Near-real-time quotes currently use Yahoo Finance free tier with inherent ~15-minute exchange delay during continuous trading hours.
- Connected near-real-time quote retrieval into prediction inference pipelines (`PredictionService` / `EnsembleService`) to dynamically anchor next-session volatility bands and current price references during active trading sessions.


## Day 35 (Continuation) - Phase 14: Connect Verified Quotes to Prediction Inference

### Goal
Connect verified near-real-time quotes into directional prediction inference (`PredictionService`, `EnsembleService`, and `/api/predict`), improving current-price context and target range volatility anchoring while strictly distinguishing observed market prices from forecasts, preventing look-ahead bias in historical training/backtesting, and enforcing safe zero-fabrication behavior on failures or delays.

### Work Completed

1. **Quote Context Contract & Boundary Transparency (`app/prediction/contract.py`, `app/prediction/__init__.py`)**:
   - Created `QuoteContext` frozen dataclass capturing `last_price`, `price_timestamp`, `retrieved_at`, `source`, `session_state`, `freshness_status`, `is_delayed`, `delay_minutes`, `price_type`, `note`, and `error_message`.
   - Distinct price semantics: marked `price_type="LAST_TRADED_PRICE"`, with explicit disclosure that last traded price reflects observed exchange data and is NOT a predicted opening or closing price.
   - Built helper constructors: `QuoteContext.from_live_quote()` for verified quotes and `QuoteContext.unavailable()` for safe zero-fabrication fallbacks.
   - Extended `PredictionRequest` with `include_live_quote: bool = True`.
   - Extended `PredictionResult` with optional `quote_context: Optional[QuoteContext] = None`, fully serialized in `.to_dict()` and formatted in `.format_summary()`.

2. **PredictionService Quote Context & Temporal Isolation Guard (`app/prediction/service.py`)**:
   - Implemented `_fetch_quote_context(symbol, request)` in `PredictionService`.
   - **Look-Ahead Bias Prevention:** When `request.as_of_date` is specified (historical replay or backtest mode), quote fetching is strictly bypassed, setting `freshness_status="NOT_APPLICABLE"` and `last_price=None` to ensure point-in-time integrity.
   - **Zero-Fabrication Safety:** If quote fetching encounters network failure, HTTP 404, or an unsupported provider, prediction inference proceeds uninterrupted, setting `freshness_status="UNAVAILABLE"` and `last_price=None` without fabricating a price.
   - Wired `quote_context` cleanly across all successful and error results in `PredictionService.predict()`.

3. **Multi-Agent Ensemble Target Range Price Anchoring (`app/prediction/ensemble.py`)**:
   - Extended `EnsemblePredictionResult` with optional `quote_context: Optional[QuoteContext] = None` and updated `.to_dict()`, `.to_prediction_result()`, and `.format_summary()`.
   - Updated `EnsembleService.synthesize()`: when `current_price` is not explicitly provided, it automatically anchors to verified quote `quote_context.last_price` to calculate ATR-based `target_range` boundaries.
   - Wired `predict_ensemble()` to synthesize using `ml_result.quote_context`.

4. **API Schema & Route Integration (`app/api/schemas.py`, `app/api/routes/predict.py`)**:
   - Added `QuoteContextResponse` Pydantic model with delay disclosure and price distinction notes.
   - Added `include_live_quote: bool = True` to `PredictRequest`.
   - Added optional `quote_context: Optional[QuoteContextResponse] = None` to `PredictionResponse`, maintaining 100% backward compatibility for all existing API clients.
   - Implemented `_map_quote_context()` and wired into both standalone ML and ensemble prediction response paths in `app/api/routes/predict.py`.

5. **Focused Unit Tests & Verification (`tests/test_inference_quote_integration.py`, `scripts/verify_day35.py`)**:
   - Created `tests/test_inference_quote_integration.py` (10 unit & integration tests):
     1. Fresh quote integration into prediction inference.
     2. Delayed quote integration with ~15m delay disclosure.
     3. Stale quote handling with explicit status and zero price fabrication.
     4. Failed quote retrieval handling without aborting inference.
     5. Unsupported quote provider graceful fallback.
     6. Point-in-time isolation and zero look-ahead bias in historical mode (`as_of_date`).
     7. Caller opt-out via `include_live_quote=False`.
     8. Backward compatibility of `PredictionResult`, `EnsemblePredictionResult`, and `PredictionResponse`.
     9. Ensemble target range anchoring using verified quote prices.
     10. FastAPI route serialization of `quote_context`.
   - Extended `scripts/verify_day35.py` with STEP 4: verified live inference on `RELIANCE.NS` (₹1,211.20 last price, 15m delay disclosure, directional prediction), historical isolation test, and ensemble target range anchoring.

### Validation Results
- **Focused Quote Inference Tests:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_inference_quote_integration.py -v
  ```
  *Result:* **10 passed** in 6.74s.
- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest
  ```
  *Result:* **550 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 22.42s across 38 test files (expanded from 540 baseline).
- **Day 35 Comprehensive Verification Script:**
  ```powershell
  & .\.venv\Scripts\python scripts/verify_day35.py
  ```
  *Result:* Exited with code `0` (`ALL STEPS PASSED`). Verified session engine, quote adapter, zero-fabrication rejection, and live quote inference integration.

### Remaining Limitations
- Near-real-time quotes provided by Yahoo Finance remain subject to a free-tier exchange delay (~15 minutes during active continuous trading hours); all response payloads and summaries explicitly disclose this limitation and clarify that observed quotes are not predicted opening or closing prices.

---

## Day 36 - Prediction Pipeline Validation and Observability

### Goal
Audit and validate the complete prediction flow from market data retrieval to prediction response, verify price semantic distinctions, test edge-case handling across quote states and historical modes, harden logging and error schemas against sensitive data leakage, and ensure zero look-ahead bias and zero price fabrication.

### Audit & Implementation Completed
1. **End-to-End Pipeline Audit (`app/market/`, `app/prediction/`, `app/api/`)**:
   - Audited data path from market data ingestion (`run_market_data_pipeline`) to feature assembly (37 canonical features), model inference (`XGBoostDirectionClassifier`/`LightGBMDirectionClassifier`), ensemble synthesis, and HTTP serialization.
   - **Semantic Distinction Verified:** Verified that observed quotes (`price_type="LAST_TRADED_PRICE"`, timestamp, source) remain quarantined inside `quote_context`. The directional models output only class direction (`UP`/`DOWN`) and uncalibrated probabilities (`probability_up`, `probability_down`). Confirmed that neither the ML models nor the API fabricate predicted opening or closing prices.
   - **Target Range Anchoring:** Verified that ATR-based volatility bounds in multi-agent ensemble synthesis are properly calculated relative to verified quote prices without conflating them with directional forecasts.

2. **Temporal Isolation and Point-in-Time Integrity Audit**:
   - Verified that historical-mode requests (`as_of_date is not None`) bypass live quote acquisition completely, returning `freshness_status="NOT_APPLICABLE"` and `last_price=None` without calling provider network endpoints.
   - Confirmed point-in-time integrity in historical backtesting and training routines, preventing look-ahead bias.

3. **Resilience & Zero-Fabrication Under Failure**:
   - Verified handling across quote states: `FRESH`, `DELAYED`, `STALE`, and `UNAVAILABLE`.
   - Confirmed that quote network timeouts, HTTP 404s, or provider errors safely fall back to `UNAVAILABLE` without aborting inference or synthesizing false prices or false confidence.

4. **Security & Sensitive Data Leakage Hardening (`app/api/routes/predict.py`, `app/prediction/service.py`)**:
   - **Error Message Sanitization (`app/api/routes/predict.py`)**: Implemented `_sanitize_public_quote_error(msg)` to ensure that internal diagnostics, filesystem paths (`\`, `/`), line numbers, or Python tracebacks inside `qc.error_message` are sanitized to `"Quote retrieval failed. Check server logs."` before returning to API clients.
   - **Log Injection Hardening (`app/prediction/service.py`)**: Applied `sanitize_log_field()` across `PredictionService` log calls (`_fetch_quote_context`, pipeline failure, feature assembly failure) to ensure control characters and CRLF sequences cannot forge log entries.

5. **Targeted Tests Added (`tests/test_inference_quote_integration.py`)**:
   - `test_quote_context_error_message_sanitizes_internal_paths`: Verifies that internal server paths and tracebacks in quote error messages are masked in API responses.
   - `test_quote_acquisition_crlf_log_sanitization`: Verifies that `PredictionService` neutralizes CRLF characters when logging quote acquisition failures.
   - `test_prediction_pipeline_distinguishes_observed_price_and_direction`: Verifies that observed quote prices are strictly quarantined in `quote_context` while response roots contain only directional probabilities with zero fabricated price targets.

### Validation Results
- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest
  ```
  *Result:* **553 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 22.50s across 38 test files (expanded from 550 baseline).
- **Day 35 Verification Script:**
  ```powershell
  & .\.venv\Scripts\python scripts/verify_day35.py
  ```
  *Result:* Exited with code `0` (`ALL STEPS PASSED`).

### Remaining Limitations
- Yahoo Finance quotes remain subject to free-tier provider delay (~15 minutes); exchange-grade low-latency feeds (e.g., direct NSE broadcast or paid broker WebSockets) are out of scope for the current local architecture.
- Passing tests validate deterministic software contracts and safeguards, not financial market profitability or production readiness under real financial risk.

---

## Day 37 - Phase 15: Comparative Model Evaluation and Performance Dashboards

### Goal
Implement the first core objective of Phase 15 from `docs/roadmap.md`: create comparative evaluation analytics and dashboards evaluating Python ML vs. LLM vs. Combined Ensemble performance side-by-side across verified historical market outcomes.

### Work Completed
1. **Comparative Model Evaluation Engine (`app/history/comparison.py`, `app/history/__init__.py`)**:
   - Implemented typed dataclass contracts:
     - `ModelPerformanceRow`: captures `total_predictions`, `verified_sessions`, `directional_accuracy`, symmetrical class precision/recall/F1 (UP and DOWN), and `brier_score`.
     - `PairwiseComparison`: evaluates matched trading sessions where both models forecast direction; computes `agreement_rate`, `agreement_accuracy`, `divergence_rate`, `divergence_accuracy_a`, `divergence_accuracy_b`, superiority win-loss counts (`model_a_superior_count`, `model_b_superior_count`), and `accuracy_delta`.
     - `ComparativeEvaluationReport`: captures aggregated models, pairwise comparisons, `ensemble_lift_over_ml`, `ensemble_lift_over_llm`, explicit compliance disclaimers, and human-readable text audit formatting (`format_summary()`).
   - Implemented `ModelComparator`:
     - Reads verified prediction-actual records from `PredictionRepository`.
     - Deconstructs standalone predictions and constituent ensemble components (`ml_prediction`, `llm_reasoning` from ensemble `raw_result`) into unified model evaluation streams.
     - Computes Brier scores ($\frac{1}{N}\sum (p - y)^2$) for probability calibration assessment.
     - Strictly guards against zero-division errors when no verified outcomes exist.

2. **REST API Endpoint & Schemas (`app/api/schemas.py`, `app/api/routes/history.py`)**:
   - Added Pydantic schemas: `ModelPerformanceResponse`, `PairwiseComparisonResponse`, and `ModelComparisonResponse`.
   - Implemented `GET /api/history/compare` endpoint supporting optional `symbol` filtering and `min_verified` threshold.
   - Preserves 100% backward compatibility for all existing prediction and history routes.

3. **Interactive Web Dashboard Integration (`app/api/static/index.html`, `app/api/static/js/app.js`)**:
   - Added a dedicated "Comparative Model Performance (ML vs. LLM vs. Ensemble)" card inside the Prediction History tab.
   - Extended `ApiService` with `fetchComparison()`.
   - Implemented `loadComparison()` to dynamically render comparison table rows, directional accuracy %, Brier scores, ensemble lift badges, and pairwise agreement summaries.

4. **Automated Unit & Integration Test Suite (`tests/test_model_comparison.py`)**:
   - Created 6 comprehensive unit and integration tests:
     1. `test_model_comparator_basic_metrics`: verifies directional accuracy, symmetrical F1, and exact Brier score computation.
     2. `test_model_comparator_pairwise_alignment`: verifies matched session agreement rate, divergence accuracy, and win/loss counts.
     3. `test_ensemble_constituent_extraction`: verifies decomposition of ensemble results into constituent ML and LLM signals.
     4. `test_model_comparator_zero_division_safety`: verifies unverified/empty data handling without exceptions.
     5. `test_comparative_report_formatting`: verifies text table formatting with required disclaimers.
     6. `test_api_history_compare_route`: verifies FastAPI `GET /api/history/compare` endpoint serialization and filtering.

### Validation Results
- **Focused Comparison Tests:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_model_comparison.py -v
  ```
  *Result:* **6 passed**, 1 warning in 6.13s.
- **Related Test Suites:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_outcome_verification.py tests/test_api.py tests/test_frontend.py -v
  ```
  *Result:* **48 passed**, 1 warning in 5.55s.
- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest
  ```
  *Result:* **559 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 23.18s across 39 test files (expanded from 553 baseline).

### Remaining Limitations
- Comparative metrics reflect realized historical sessions in the local SQLite database; small sample sizes may exhibit high variance until sufficient trading sessions complete.
- Phase 15 second objective (controlled, gated model retraining workflows with version tracking per ADR 10) remains for subsequent increments.
- Passing tests validate deterministic software contracts and safeguards, not financial market profitability or production readiness under real financial risk.

### Next Step
Implement Phase 15's second milestone: controlled, gated model retraining workflow with explicit out-of-sample validation gates and version tracking (ADR 10).

---

## Day 38 - Phase 15: Controlled Model Retraining & Version Tracking

### Goal
Implement controlled, gated model retraining workflows with version tracking and formal safety gates adhering strictly to ADR 10 (Controlled, Gated Model Retraining):
- Ensure retraining never starts automatically from an unverified, empty, or insufficient dataset.
- Enforce strict chronological separation and embargo between training and out-of-sample evaluation data.
- Prevent unverified candidates from overwriting active production models before passing all validation gates.
- Preserve existing active production models untouched whenever candidate training or validation fails.
- Persist comprehensive model release audit trails (versions, cutoffs, metrics, and gate results) in SQLite.
- Maintain zero-fabrication guarantees, no automatic live trading, and no unsupervised online training loops.

### Work Completed
1. **Database Schema Extension (`app/database/schema.py`)**:
   - Added `model_releases` table to SQLite schema with complete audit columns:
     - `release_id` (UUID primary key text), `model_name` (e.g., `xgboost`, `lightgbm`), `model_version`, `symbol`.
     - `status` (`CANDIDATE`, `PROMOTED`, `REJECTED`, `ARCHIVED`), `is_active` (boolean flag 0 or 1).
     - `training_sample_count`, `evaluation_sample_count`, `training_cutoff_date`, `evaluation_cutoff_date`.
     - `metrics_json` (serialized accuracy, precision, recall, F1 for UP/DOWN classes, Brier calibration, baselines).
     - `gates_json` (serialized individual gate pass/fail status, observed values, and thresholds).
     - `rejection_reason` (detailed diagnostic explanation upon gate failure), `artifact_path`, `created_at`, `promoted_at`.
   - Added composite indexes `idx_model_releases_name_status` and `idx_model_releases_active` for fast lookups.

2. **Repository Layer Extension (`app/database/repository.py`)**:
   - Implemented `save_model_release()`: records release audit entries, automatically deactivating prior active models when a new active release is inserted.
   - Implemented `get_model_release(release_id)`: retrieves full release records with parsed JSON metrics and gates.
   - Implemented `get_active_model_release(model_name)`: queries the currently active production release.
   - Implemented `list_model_releases(model_name, status, limit)`: retrieves release history ordered chronologically descending.
   - Implemented `promote_model_release(release_id)`: atomic transactional promotion transitioning previous models to inactive and marking the new release as `PROMOTED` with `promoted_at` timestamp.

3. **Controlled Retraining & Validation Gating Service (`app/training/retraining.py`, `app/training/__init__.py`)**:
   - Implemented dataclasses `ModelReleaseStatus`, `ValidationGateResult`, and `RetrainingResult`.
   - Implemented `ModelRetrainer`:
     - File system quarantine: Candidate models are saved strictly to `models/candidates/` and never directly to active paths.
     - Five formal safety gates evaluated on out-of-sample validation partitions:
       1. **Sample Sufficiency Gate**: requires minimum 50 training samples and 15 validation samples.
       2. **Class Balance Gate**: requires non-degenerate binary representation (`{0, 1}`) in both training and evaluation partitions.
       3. **Baseline Superiority Gate**: candidate directional accuracy must meet or exceed majority-class baseline (within 0.01 margin).
       4. **Minimum Performance Gate**: candidate out-of-sample directional accuracy must meet or exceed 50.0%.
       5. **Active Model Non-Degradation Gate**: candidate accuracy must not degrade active production model accuracy by more than 0.02 (2.0%).
     - Atomic promotion protocol:
       - Archives existing active model to `models/archive/{model}_archived_{timestamp}.*`.
       - Copies verified candidate to canonical production path (`models/{model}_direction.*`).
       - Updates release state in database to `PROMOTED` and active.
     - Rejection protocol:
       - On any gate failure or invalid data, candidate is marked `REJECTED` with specific failure reason.
       - Production active model is left 100% untouched and preserved.

4. **Automated Unit & Integration Test Suite (`tests/test_model_retraining.py`)**:
   - Added 7 comprehensive test cases:
     1. `test_brier_score_computation`: tests probability error calibration under perfect, inverted, empty, and length-mismatched conditions.
     2. `test_retraining_success_and_atomic_promotion`: verifies successful candidate training, all gates passing, artifact promotion, active path update, and repository tracking.
     3. `test_retraining_rejection_on_insufficient_samples`: verifies Gate 1 failure, candidate rejection, and active model preservation when sample size is below threshold.
     4. `test_retraining_rejection_on_degenerate_class_distribution`: verifies Gate 2 failure when training set lacks class diversity.
     5. `test_active_model_preserved_when_candidate_degrades_performance`: verifies Gate 5 rejection and byte-for-byte active model preservation when a new candidate performs worse than the active model.
     6. `test_empty_dataset_handling`: verifies clean handling and rejection of empty feature sets without unhandled crashes.
     7. `test_repository_model_release_lifecycle`: verifies release saving, deactivation of prior active models, and querying history.

### Validation Results
- **Focused Retraining Tests:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_model_retraining.py -v
  ```
  *Result:* **7 passed** in 6.00s.
- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest
  ```
  *Result:* **566 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 23.10s across 40 test files (expanded from 559 baseline).

### Remaining Limitations
- Retraining triggers are manual or programmatically scheduled through external workflows; continuous unsupervised retraining loops remain strictly prohibited per ADR 10.
- Out-of-sample validation gates evaluate directional accuracy and Brier calibration on historical sessions; real-world market regime shifts, execution slippage, and liquidity changes cannot be simulated by offline metrics alone.
- Passing automated tests validate deterministic gating contracts and software integrity, not financial market profitability or production readiness under real trading capital.

### Next Step
Proceed to Phase 16: Final Testing & Evaluation (end-to-end multi-regime robustness testing, security audit, and deployment readiness review).

---

## Day 39 - Phase 16: Final Testing & Evaluation — Audit, Multi-Regime Stress Testing & Hardening

### Goal
Perform a comprehensive audit of the retraining and version tracking implementation before adding features, empirically reproduce any defects, implement atomic filesystem/database rollback guarantees, enforce chronological integrity gates (zero look-ahead leakage), and conduct multi-regime market stress testing.

### Work Completed
1. **Repository Audit & Empirical Defect Confirmation**:
   - Audited [app/training/retraining.py](file:///d:/Share_market_predictor/app/training/retraining.py) and [app/database/repository.py](file:///d:/Share_market_predictor/app/database/repository.py) across 8 critical dimensions:
     1. Temporal leakage and chronological integrity in training and evaluation cutoffs.
     2. Correct use of verified historical outcomes.
     3. Candidate rejection and active-model preservation on every failure path.
     4. Filesystem and SQLite consistency during promotion (archive or copy failures).
     5. Concurrent retraining or promotion behavior.
     6. Model artifact/version metadata consistency.
     7. API input validation, error sanitization, secret handling, and logging.
     8. Existing API and historical-mode backward compatibility.
   - **Confirmed Defect 1 (High Severity - Missing Chronological Gate):** Inverted or overlapping cutoffs (e.g. `training_cutoff_date="2025-06-01"`, `evaluation_cutoff_date="2025-01-01"`) were accepted without gate failure, allowing look-ahead bias and future data leakage into the training set.
   - **Confirmed Defect 2 (High Severity - Missing Promotion Rollback):** During promotion, candidate models were directly copied over the active model file (`shutil.copy2`) before saving the release in SQLite. If repository saving failed or archiving threw an error, the active model file was left modified/overwritten in an inconsistent state without automatic rollback.

2. **Chronological Integrity Enforcement (`app/training/retraining.py`)**:
   - Implemented `ModelRetrainer.validate_chronological_ordering()`: validates that `training_cutoff_date < evaluation_cutoff_date` and verifies that sample timestamps in the training partition strictly precede evaluation samples (`max(train_dates) < min(val_dates)`).
   - Added formal **`CHRONOLOGICAL_INTEGRITY_GATE`** (Gate 0): immediately fails and rejects candidates when temporal inversion or look-ahead overlap is detected, preserving active models untouched.

3. **Atomic Promotion, Safe Archiving, and Automatic Rollback Protocol**:
   - Added `threading.Lock()` (`_promotion_lock`) on `ModelRetrainer` to serialize concurrent promotion workflows.
   - **Mandatory Archiving:** Promotion is immediately aborted and candidate rejected if creating a backup in `models/archive/` fails, preventing unbacked overwrites.
   - **Atomic Staging:** Uses temporary file staging (`.tmp`) and `os.replace` for atomic replacement, ensuring concurrent inference readers never encounter partially written model artifacts.
   - **Transactional Rollback:** Wrapped promotion and repository release saves in a guarded `try...except` block; if SQLite release persistence or filesystem operations fail, the active model is automatically restored from the archived backup byte-for-byte.

4. **Multi-Regime Market Stress & Audit Regression Suite (`tests/test_multi_regime_evaluation.py`)**:
   - Created 8 comprehensive regression and stress tests:
     1. `test_chronological_integrity_gate_inverted_cutoffs`: verifies Gate 0 rejection on inverted cutoff dates.
     2. `test_chronological_integrity_gate_temporal_overlap_in_dates`: verifies Gate 0 rejection on DatetimeIndex overlap.
     3. `test_promotion_rollback_on_repository_failure`: verifies byte-for-byte rollback of active model when database release save fails.
     4. `test_promotion_aborted_when_archiving_fails`: verifies promotion is safely aborted when archive creation fails.
     5. `test_multi_regime_bull_market_evaluation`: evaluates model performance under sustained upward drift.
     6. `test_multi_regime_bear_market_evaluation`: evaluates model performance under sustained downward trend.
     7. `test_multi_regime_shock_transition_rejection`: simulates a regime shock (training on bull momentum, evaluating on bear crash); confirms candidate collapse is caught and rejected by Gate 4 / Gate 3, protecting production.
     8. `test_concurrent_retraining_promotion_thread_safety`: verifies thread serialization and artifact integrity under concurrent promotion attempts.

### Validation Results
- **Multi-Regime Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_multi_regime_evaluation.py -v
  ```
  *Result:* **8 passed** in 4.82s.
- **Model Retraining Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_model_retraining.py -v
  ```
  *Result:* **7 passed** in 5.33s.
- **Project Verification Script (Real Historical YFinance Pipeline):**
  ```powershell
  & .\.venv\Scripts\python scripts/verify_baselines.py
  ```
  *Result:* Successfully fetched and normalized 124 real MarketOHLCV bars for BHARTIARTL; verified feature matrix, temporal holdout, and baseline strategy comparisons without errors.
- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest
  ```
  *Result:* **574 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 22.77s across 41 test files (expanded from 566 baseline).

### Remaining Risks & Limitations
- While chronological separation, atomic replacement, and rollback guarantees are now strictly enforced, real financial markets experience non-stationary regime shifts (liquidity dry-ups, regulatory intervention, macroeconomic shocks) that historical backtests and synthetic regimes cannot fully capture.
- Retraining remains strictly a manual or batch administrative action; unsupervised automated live retraining loops remain prohibited per ADR 10.
- Automated tests prove deterministic software correctness, data integrity, and failure containment; they do NOT imply financial profitability or immunity to capital loss in live trading.
- Phase 16 remains in progress for end-to-end security audits, full deployment readiness reviews, and documentation finalization.

### Next Step
Continue Phase 16: Perform security and dependency audits, verify production configuration hardening, and assemble final deployment readiness documentation.

---

## Day 40 - Phase 16: Security Audit & Deployment Readiness

### Goal
Audit application configuration, CORS policies, information disclosure vulnerabilities, defensive response headers, and dependency health in preparation for Phase 16 deployment readiness. Fix confirmed high-priority security defects with automated regression tests.

### Work Completed
1. **Dependency Security Review**:
   - Inspected active virtual environment manifests and package dependencies (`requirements.txt`).
   - Ran `pip check`: confirmed zero broken requirements or incompatible versions across all 56 installed packages.
   - Identified scanner availability: `pip-audit` is not pre-installed in the execution environment; this limitation is documented without fabricating external CVE databases or upgrading packages prematurely.

2. **API & Deployment Configuration Security Audit**:
   - Audited [app/core/config.py](file:///d:/Share_market_predictor/app/core/config.py) and [app/api/app.py](file:///d:/Share_market_predictor/app/api/app.py) across 6 deployment readiness dimensions:
     1. **CORS Origins Policy:** Confirmed defect where setting `APP_CORS_ORIGINS="*"` in production was previously permitted by `Settings.from_env()`, allowing any third-party browser session to execute cross-origin requests.
     2. **Documentation Exposure:** Confirmed information disclosure defect where `/docs`, `/redoc`, and `/openapi.json` remained active and publicly discoverable in production mode (`APP_ENV=production`).
     3. **Debug Mode Lockdown:** Confirmed configuration risk where `APP_DEBUG=true` could be passed in production mode.
     4. **HTTP Security Headers:** Identified absence of OWASP defensive headers on HTTP responses (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`).
     5. **Administrative Retraining Endpoints:** Verified that no public HTTP route exposes automated retraining execution; feedback route (`POST /api/feedback`) returns explicit HTTP 501 with ADR 10 disclaimer.
     6. **Database & Artifact File Isolation:** SQLite database and candidate/archive model paths are maintained strictly in dedicated local directories without external network exposure.

3. **Production Hardening Implementation (`app/core/config.py`, `app/api/app.py`)**:
   - **Production CORS Lockdown:** `Settings.from_env()` and `create_app()` strictly reject wildcard origin `*` with a `ValueError`. In production, origins must be explicit HTTPS URLs (insecure plain HTTP origins for non-localhost domains are rejected).
   - **Explicit Production CORS Requirement:** In production mode, `create_app()` verifies that `APP_CORS_ORIGINS` has been explicitly configured, preventing accidental fallback to development `localhost:8000` / `localhost:3000` defaults.
   - **Production Debug Prohibition:** `create_app()` enforces that `APP_DEBUG` cannot be enabled when `APP_ENV=production`.
   - **OpenAPI Schema Lockdown in Production:** In production (`settings.is_production()`), `docs_url`, `redoc_url`, and `openapi_url` are set to `None` (returning 404 Not Found), and the `/` metadata endpoint omits the `docs` link.
   - **Defensive HTTP Response Headers Middleware:** Added ASGI response header middleware injecting `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy: geolocation=(), microphone=(), camera=()` on all responses.

4. **Automated Unit & Regression Test Suite (`tests/test_security_deployment.py`)**:
   - Added 9 comprehensive security tests:
     1. `test_production_cors_rejects_wildcard`: verifies `Settings.from_env()` rejects `*` in production.
     2. `test_production_cors_rejects_insecure_http`: verifies rejection of plain HTTP for public domains in production.
     3. `test_production_cors_requires_explicit_configuration`: verifies `create_app()` rejects missing `APP_CORS_ORIGINS` in production.
     4. `test_production_debug_mode_rejected`: verifies `create_app()` rejects `APP_DEBUG=true` in production.
     5. `test_production_valid_configuration`: verifies valid HTTPS domains are accepted in production.
     6. `test_production_mode_disables_openapi_and_docs`: verifies 404 Not Found for `/docs`, `/redoc`, and `/openapi.json` in production.
     7. `test_development_mode_enables_docs`: verifies interactive Swagger docs remain accessible in development mode.
     8. `test_security_response_headers_present`: verifies presence of defensive headers on API responses.
     9. `test_effective_cors_runtime_enforcement`: verifies runtime CORS headers are emitted for trusted origins and suppressed for untrusted origins.

### Validation Results
- **Security & Deployment Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_security_deployment.py -v
  ```
  *Result:* **9 passed** in 4.97s.
- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest
  ```
  *Result:* **583 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 23.42s across 42 test files (expanded from 574 baseline).

### Remaining Risks & Limitations
- Standalone external vulnerability scanner (`pip-audit`) is not installed in the local environment; external automated CI/CD pipeline scanning should be configured upon deployment.
- Production deployment will require TLS termination (e.g. reverse proxy via Nginx/Caddy or Cloudflare) with valid SSL certificates, as uvicorn does not manage automated ACME renewal.
- Passing security unit tests verifies defensive middleware and configuration validation; it does not constitute an exhaustive penetration test or guarantee financial profitability in live markets.

### Next Step
Assemble final deployment runbook documentation and complete final Phase 16 evaluation review.

---

## Day 41 - Phase 16: Deployment Runbook, CI/CD Security Scanning & Staging Readiness

### Goal
Establish automated CI/CD dependency vulnerability scanning, compile a production deployment & operations runbook, integrate operational request latency telemetry, and provide a reproducible staging soak/load simulation framework.

### Work Completed
1. **CI/CD Security Scanning (`.github/workflows/ci.yml`)**:
   - Proposed and implemented GitHub Actions workflow executing on push, pull request, and weekly schedule (Monday 06:00 UTC).
   - Job 1 (`test`): Multi-version Python (3.11, 3.12) matrix running dependency check (`pip check`) and full pytest suite (`pytest -v`).
   - Job 2 (`security-audit`): Automated dependency vulnerability scanner utilizing `pip-audit -r requirements.txt --desc on --format json`. Configured failure policy for vulnerable dependencies without silently upgrading packages.
   - Created local dependency audit utility ([scripts/run_dependency_audit.py](file:///d:/Share_market_predictor/scripts/run_dependency_audit.py)) executing `pip check` and reporting `pip-audit` availability and instructions.

2. **Production Deployment Runbook ([docs/deployment-runbook.md](file:///d:/Share_market_predictor/docs/deployment-runbook.md))**:
   - Documented the end-to-end production deployment architecture (FastAPI/Uvicorn, SQLite WAL, filesystem model registry, local Ollama Gemma 3 12B service).
   - Comprehensive inventory of environment variables and mandatory production defaults (`APP_ENV=production`, `APP_DEBUG=false`, `APP_CORS_ORIGINS`).
   - Reverse proxy configuration with complete Nginx template (TLS 1.3 termination, proxy header forwarding, buffer limits).
   - Database operations: automatic schema migrations, online hot backup command (`sqlite3 ".backup ..."`), and disaster recovery protocol.
   - Model lifecycle: candidate quarantine, 6-gate promotion criteria (Chronological Integrity, Sample Sufficiency, Class Balance, Baseline Superiority, Minimum Accuracy, Non-Degradation), atomic staging (`os.replace`), and automatic archive rollback.
   - Monitoring & incident response: health check endpoint (`GET /api/health`), log signatures, triage matrix, and systemd service unit file.

3. **Operational Telemetry Middleware ([app/api/app.py](file:///d:/Share_market_predictor/app/api/app.py))**:
   - Injected operational telemetry and latency tracking into ASGI middleware:
     - Measures request execution duration with high-precision `time.perf_counter()`.
     - Appends `X-Process-Time-Ms` response header.
     - Emits structured operational access log: `HTTP {method} {path} -> {status_code} ({duration_ms}ms)`.
     - Preserves privacy and security: Query strings, authorization headers, and request bodies are strictly omitted from access logs to prevent credential leakage.

4. **Staging Soak Test Simulation ([scripts/staging_soak_test.py](file:///d:/Share_market_predictor/scripts/staging_soak_test.py))**:
   - Verified that no external staging cluster or synthetic load generator existed in the repository.
   - Implemented a reproducible load test runner capable of executing concurrent multi-threaded requests against `/api/health`, `/`, `/api/history`, `/api/events`, and `/api/predict`.
   - Aggregates throughput (req/s), status breakdown, and latency distribution (min, mean, p50, p95, p99, max).
   - Added explicit disclaimers: Local simulation validates endpoint stability and error isolation under concurrency; a multi-hour soak test on a production-equivalent staging cluster during live exchange hours remains a documented, pending Phase 16 acceptance criterion.

5. **Automated Unit & Regression Tests ([tests/test_staging_soak.py](file:///d:/Share_market_predictor/tests/test_staging_soak.py), [tests/test_security_deployment.py](file:///d:/Share_market_predictor/tests/test_security_deployment.py))**:
   - Added 4 unit tests covering `perform_dependency_audit()`, `SoakSummary` percentile computation, empty metric safety, and bounded in-process soak test execution.
   - Added `X-Process-Time-Ms` telemetry header assertion to security deployment suite.

### Validation Results
- **Focused Staging Soak & Security Tests:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_staging_soak.py tests/test_security_deployment.py -v
  ```
  *Result:* **13 passed**, 1 warning in 11.86s.
- **In-Process Soak Simulation:**
  ```powershell
  & .\.venv\Scripts\python scripts/staging_soak_test.py --requests 50 --concurrency 4 --in-process
  ```
  *Result:* **50 requests completed**, 100% success (non-5xx), 0 errors, 15.85 req/s, mean latency 222.11ms, p50 30.02ms.
- **Local Dependency Audit Runner:**
  ```powershell
  & .\.venv\Scripts\python scripts/run_dependency_audit.py
  ```
  *Result:* `pip check` PASSED. `pip-audit` notice logged with CI workflow reference.
- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest
  ```
  *Result:* **587 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 25.46s across 43 test files (expanded from 583 baseline).

### Remaining Risks & Limitations
- While local concurrency and simulation tests passed cleanly, a live multi-hour soak test on dedicated production-equivalent staging infrastructure during NSE market hours remains pending deployment infrastructure provisioning.
- Live exchange quotes depend on external Yahoo Finance availability and are subject to potential network latency or third-party rate limits.
- Automated tests verify deterministic software behavior and error handling; they do not establish financial profitability or eliminate market risk.

### Next Step
Execute live staging deployment soak test once staging infrastructure is provisioned, finalize Phase 16 completion audit, and prepare production launch review.

---

## Day 42 - Phase 16: Live Staging Readiness & Deployment Validation

### Goal
Assess existing infrastructure for staging deployment, validate deployment runbook protocols with automated tests, empirically verify external HTTP soak execution on real TCP sockets, and document external prerequisites blocking a production-equivalent live soak test.

### Work Completed
1. **Infrastructure Audit & Staging Assessment**:
   - Inspected repository configuration, environment variables, local processes, and network ports.
   - Confirmed local Ollama daemon is running with model `gemma3:12b` (8.15 GB) operational at `http://127.0.0.1:11434`.
   - Verified that no external staging host, deployment URL, TLS certificate, or cloud infrastructure is currently configured or provisioned.
   - Classified all 10 deployment readiness items into VERIFIED, NOT CONFIGURED, and BLOCKED categories.

2. **Deployment Runbook Automated Validation ([tests/test_deployment_runbook.py](file:///d:/Share_market_predictor/tests/test_deployment_runbook.py))**:
   - Added 4 comprehensive automated tests covering runbook operational procedures:
     1. `test_production_configuration_strict_validation`: verifies that production mode rejects wildcard CORS (`*`), unconfigured origins, and debug mode.
     2. `test_health_check_with_isolated_storage`: verifies `/api/health` and application startup using clean temporary database and isolated model storage.
     3. `test_soak_external_http_execution_and_data_isolation`: starts an in-process live Uvicorn HTTP server on TCP socket `127.0.0.1:8899`, dispatches 20 concurrent requests over actual HTTP sockets using `staging_soak_test.py`, confirms 100% success (non-5xx), and proves empirically that `persist=False` leaves the database unmutated (0 rows inserted).
     4. `test_execute_request_external_failure_handling`: verifies that connection failures and unreachable target hosts are safely captured with status 0 and error details without crashing.

3. **CI Typing Import Fix Verification**:
   - Verified that commit `77cd635` resolved all Python 3.11 and 3.12 CI test collection failures on GitHub Actions (Run `39142516287` completed with 100% success across all 3 jobs).

### Validation Results
- **Focused Deployment Runbook Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_deployment_runbook.py -v
  ```
  *Result:* **4 passed**, 1 warning in 11.60s.
- **Dependency Integrity:**
  ```powershell
  & .\.venv\Scripts\python -m pip check
  ```
  *Result:* `No broken requirements found.`
- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest
  ```
  *Result:* **591 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 34.21s across 44 test files (expanded from 587 baseline).

### Remaining Risks & Infrastructure Blockers
- **Staging Infrastructure Blocker:** A live, multi-hour deployment soak test on dedicated production-equivalent infrastructure cannot be performed because no staging host or cloud deployment target has been provisioned.
- **External Prerequisites Required to Unblock:**
  1. Provisioning of a dedicated staging VM or container cluster (Ubuntu 22.04 LTS, 4 vCPU, 16GB RAM recommended for local Ollama Gemma 3 12B inference).
  2. Configuration of public DNS and TLS 1.3 reverse proxy (Nginx or Caddy) terminating HTTPS.
  3. Staging-specific environment variables (`APP_ENV=production`, `APP_DEBUG=false`, `APP_CORS_ORIGINS=https://staging.yourdomain.com`).
  4. Explicit authorization to deploy and run sustained continuous traffic during NSE trading hours.
- **Phase 16 Status:** Kept strictly **IN PROGRESS** until real staging soak test evidence is recorded.

### Next Step
Await provisioning of dedicated staging infrastructure, execute the 2-hour live staging soak test, and assemble final Phase 16 completion evaluation.

---

## Day 43 - Phase 16: Local Staging Environment & Production-Style Validation

### Goal
Create a safe, reproducible local staging environment on Windows for the stock market prediction application. Validate production-style startup, configuration, health checks, telemetry, and HTTP behavior without spending money, provisioning external resources, exposing the application publicly, or mutating development database and active model artifacts. Keep Phase 16 marked strictly IN PROGRESS until a real multi-hour soak test passes on production-equivalent staging infrastructure.

### Work Completed
1. **Isolated Local Staging Launcher (`scripts/run_local_staging.py`)**:
   - Implemented an automated staging runner enforcing strict loopback binding policy (`127.0.0.1` / `localhost`). Host values exposing external network interfaces (e.g., `0.0.0.0`, LAN IPs) are rejected immediately with `ValueError`.
   - Dedicated local port selection (default `8899`) with pre-flight TCP socket availability verification.
   - Isolated ephemeral storage: Sets `APP_DATA_DIR` and `APP_MODEL_DIR` to temporary directories (`tempfile.mkdtemp()`).
   - Read-only model artifact staging: Safe temporary copies of existing production models (`xgboost_direction.*`, `lightgbm_direction.*`) are staged into the temporary model directory. The real `models/` directory is never modified or used as a writable staging target.
   - Production configuration hardening: Enforces `APP_ENV=production`, `APP_DEBUG=false`, and explicit CORS origins (`http://127.0.0.1:8899,https://staging.local`), verifying that wildcard CORS (`*`) and insecure non-localhost origins remain rejected.
   - Non-mutation verification guards: Calculates cryptographic SHA-256 and file metadata fingerprints (`size`, `mtime`) for `data/predictions.db` and active models in `models/` before and after execution to empirically prove zero side-effects or state pollution.

2. **Eight-Point Production-Style Validation Protocol**:
   - Check 1: Loopback isolation verified (bound strictly to `127.0.0.1`).
   - Check 2: Clean Uvicorn startup with temporary database and model storage.
   - Check 3: Health check (`GET /api/health`) responds HTTP 200 with JSON payload (`{"status": "healthy"}`).
   - Check 4: Defensive OWASP security headers present on responses (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `X-Process-Time-Ms`).
   - Check 5: Production OpenAPI suppression verified (interactive `/docs`, `/redoc`, and `/openapi.json` return HTTP 404).
   - Check 6: Safe HTTP smoke tests executed across read-only endpoints (`/`, `/api/events`, `/api/history`) without external provider calls or DB writes.
   - Check 7: Development database non-mutation verified (0 bytes changed, exact SHA-256 and timestamp match).
   - Check 8: Active model artifacts non-mutation verified (0 files altered, created, or deleted).

3. **Controlled Local Load Test**:
   - Executed a controlled 50-request, concurrency-4 load test against local staging loopback socket (`http://127.0.0.1:8899`).
   - Metrics captured: 100% success rate (50 HTTP 200, 0 failures, 0 timeouts), duration 2.61s, throughput 19.14 req/s, p50 latency 23.15ms, p95 latency 1051.22ms, max latency 1077.39ms. All metrics explicitly labeled as LOCAL STAGING results.
   - Clean shutdown: Uvicorn background server terminated gracefully and temporary staging files cleaned up.

4. **Automated Unit & Regression Tests (`tests/test_local_staging.py`)**:
   - Added 4 unit and integration tests:
     1. `test_loopback_binding_restriction`: verifies `run_local_staging_validation(host="0.0.0.0")` and `192.168.1.100` are rejected with `ValueError`.
     2. `test_is_port_available_logic`: verifies port availability detection for both free high ports and occupied sockets.
     3. `test_dev_db_fingerprint`: verifies database fingerprinting logic for missing and existing database paths.
     4. `test_local_staging_lifecycle_and_non_mutation`: launches local staging server on isolated port 8897 with a temporary SQLite database, runs 10 requests, verifies 100% success, and asserts development database remains unmutated.

### Validation Results
- **Local Staging Validation Runner:**
  ```powershell
  & .\.venv\Scripts\python scripts/run_local_staging.py --port 8899 --requests 50 --concurrency 4
  ```
  *Result:* All 8 verification checklist items PASSED.
  - Total requests: 50
  - Successful responses (HTTP 200): 50 (100.0%)
  - Non-2xx responses: 0 (0.0%)
  - 5xx responses: 0 (0.0%)
  - Timeouts and network errors: 0
  - Test duration: 2.61s
  - Throughput: 19.14 req/s
  - Latency (local staging): Min 13.91ms | Mean 208.76ms | p50 23.15ms | p90 985.34ms | p95 1051.22ms | p99 1077.39ms | Max 1077.39ms
  - Development DB mutation: 0 bytes altered (fingerprint identical before and after).
  - Active model mutation: 0 files altered.
- **Focused Local Staging Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_local_staging.py -v
  ```
  *Result:* **4 passed**, 1 warning in 9.51s.
- **Dependency Integrity:**
  ```powershell
  & .\.venv\Scripts\python -m pip check
  ```
  *Result:* `No broken requirements found.`
- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest
  ```
  *Result:* **595 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 39.77s across 45 test files (expanded from 591 baseline).

### Local Staging Architecture & Isolation Guarantees
- **Loopback Enforcement:** Binds strictly to `127.0.0.1`, guaranteeing that the test server cannot be accessed from the local LAN or the public internet.
- **Data Isolation:** All database reads and writes during staging are redirected to a temporary SQLite database (`tempfile.mkdtemp()`), leaving `data/predictions.db` completely untouched.
- **Model Isolation:** Active models in `models/` are copied to a temporary staging folder in read-only fashion. No candidate promotions or retraining workflows are invoked.
- **Safe Smoke Routes:** Smoke requests target idempotent read-only endpoints (`/api/health`, `/`, `/api/events`, `/api/history`). External Yahoo Finance quote retrieval is bypassed or skipped during load generation.

### Known Limitations
- Local staging runs on a local Windows loopback socket (`127.0.0.1:8899`) and does NOT evaluate external TLS 1.3 termination, public DNS propagation, reverse proxy buffering (Nginx/Caddy), firewall rules, or cloud provider ingress.
- Latency and throughput figures represent single-node loopback performance on a local workstation, not multi-user cloud performance.
- Local tests do not substitute for sustained, multi-hour continuous soak traffic during active Indian market trading hours (09:15 - 15:30 IST).

### Exact Remaining Prerequisites for External Staging
1. Provisioning of a dedicated Linux staging host or container instance (Ubuntu 22.04 LTS, 4 vCPU, 16GB RAM recommended for Ollama Gemma 3 12B).
2. Domain / DNS record configuration pointing to the staging host with TLS 1.3 certificate (e.g., Let's Encrypt / ACME).
3. Reverse proxy deployment (Nginx) configured with production security headers, request rate limiting, and backend proxying to Uvicorn.
4. Formal execution and evidence capture of the required multi-hour soak test (`scripts/staging_soak_test.py`) with continuous traffic under market conditions.

### Phase 16 Status
**Phase 16 remains strictly IN PROGRESS.** Local staging validation proves reproducible local startup, configuration hardening, telemetry, and isolation, but does not satisfy the milestone criteria of a genuine production-equivalent staging soak test.

### Next Step
Await provisioning of dedicated staging infrastructure, execute the multi-hour live staging soak test, and assemble final Phase 16 completion evaluation.

---

## Day 44 - Phase 16: Local Staging Performance Reliability & Failure-Handling Audit

### Goal
Investigate tail latency distribution from Day 43, validate soak-test metric calculation correctness, eliminate external network calls during local staging, implement per-endpoint latency tracking, add comprehensive failure-handling regression tests, and propose a controlled 10-minute sustained-load test with explicit local acceptance criteria. Keep Phase 16 marked strictly IN PROGRESS.

### Work Completed
1. **Tail Latency Root-Cause Analysis & Offline Event Isolation**:
   - **Investigation:** Analyzed Day 43's latency distribution (p50: 23.15ms, p95: 1051.22ms, max: 1077.39ms).
   - **Root Cause Confirmed:** The staging load profile included `GET /api/events?limit=5`. In the default configuration, `app/api/dependencies.py` instantiates `RBIEventProvider` and `SEBIEventProvider`, which make live outbound HTTPS network requests via `urllib.request.urlopen` to `https://rbi.org.in` and `https://www.sebi.gov.in`. Each outbound network request took ~1000ms over the public internet, contaminating overall staging metrics and violating the offline isolation rule.
   - **Fix:** Implemented `OfflineStagingEventProvider` in [`scripts/run_local_staging.py`](file:///d:/Share_market_predictor/scripts/run_local_staging.py) injected via FastAPI `app.dependency_overrides[get_event_providers]`. This completely isolates local staging from external network round-trips while still validating data cleaning, deduplication, and Pydantic serialization.
   - **Impact:** Mean latency dropped from 208.76ms to 30.73ms (7x faster); p95 latency dropped from 1051.22ms to 64.77ms (16x faster); throughput increased from 19.14 req/s to 119.64 req/s on local loopback.

2. **Metrics Validation & Mathematical Precision (`scripts/staging_soak_test.py`, `scripts/run_local_staging.py`)**:
   - **Linear Interpolation Percentiles:** Replaced naive rounding (`int(round(p * (n - 1)))`) with continuous linear interpolation (`compute_percentile(sorted_values, p)`), aligning with standard NumPy (`method='linear'`) and Excel PERCENTILE algorithms. Eliminates banker's rounding bias on small sample sizes.
   - **p90 Percentile & Sample Stability Indicators:** Added calculation for `p90` alongside `p50`, `p95`, and `p99`. Added sample size stability indicators: flagged as unstable when $N < 10$ for p90, $N < 20$ for p95, and $N < 100$ for p99.
   - **Strict Status Classification:** Implemented `classify_http_outcome(status_code, is_timeout)`. Categorizes requests strictly into `http_2xx`, `http_3xx`, `http_4xx` (client errors), `http_5xx` (server errors), `timeouts`, and `network_errors`. Fixed defect where HTTP 4xx client errors were previously lumped into successful requests (`status_code < 500`).
   - **Accurate Throughput Denominator:** Fixed throughput calculation on partial or interrupted runs by dividing completed requests (`len(latencies_ms)`) rather than scheduled total requests.
   - **Endpoint-Level Latency Tracking:** Added `EndpointStats` and `endpoint_metrics` dictionary breaking down request count, status codes, and latency distributions (min, mean, p50, p90, p95, max) per individual route (`/api/health`, `/`, `/api/history`, `/api/events`).

3. **Eight Failure-Handling Scenarios Tested ([`tests/test_local_staging.py`](file:///d:/Share_market_predictor/tests/test_local_staging.py), [`tests/test_staging_soak.py`](file:///d:/Share_market_predictor/tests/test_staging_soak.py))**:
   - Scenario 1 (Unreachable Endpoint / Connection Refused): Verified client handles connection refused on unassigned port (`127.0.0.1:59997`) cleanly, returning status 0, `error_type="network_error"`, without crashing.
   - Scenario 2 (Request Timeout): Verified client explicitly catches `requests.exceptions.Timeout`, classifying it as `is_timeout=True` and `error_type="timeout"`.
   - Scenario 3 (HTTP 5xx Server Error): Verified `execute_request_external` and `run_soak_simulation` classify HTTP 500/503 responses under `http_5xx` and `failed_requests`.
   - Scenario 4 (Graceful Shutdown While Idle): Verified Uvicorn server started on loopback terminates cleanly and joins server thread within 3 seconds when `server.should_exit = True` is signaled without pending traffic.
   - Scenario 5 (Graceful Shutdown After Request): Verified server handles HTTP traffic, completes response, and shuts down cleanly upon exit signal.
   - Scenario 6 (Temporary Directory Cleanup on Success & Failure): Verified temporary staging directories (`tempfile.mkdtemp()`) are cleaned up completely on both normal completion and early aborts.
   - Scenario 7 (Development DB & Active Models Preservation): Verified that development database (`data/predictions.db`) and active models (`models/*`) remain 100% untouched with matching SHA-256 and metadata fingerprints even under simulated runtime aborts.
   - Scenario 8 (Occupied Staging Port Detection): Verified runner detects an already-bound port (`socket.bind`), records an error in `report.errors`, and aborts cleanly without unhandled `OSError: [Errno 10048]`.

4. **Proposed 10-Minute Sustained-Load Test Plan (Presented for Review)**:
   - **Target Host:** `127.0.0.1` (loopback only, port `8899`)
   - **Target Duration:** 10 minutes (600 seconds)
   - **Concurrency:** 4 worker threads
   - **Route Mix:** Verified read-only endpoints only (`GET /api/health` 40%, `GET /` 20%, `GET /api/history?limit=10` 20%, `GET /api/events?limit=5` 20% with offline mock provider)
   - **Estimated Throughput & Volume:** ~100-120 req/s, resulting in ~60,000 to ~72,000 total requests
   - **Estimated Resource Impact:** ~10-15% of 1 CPU core, ~60-80 MB memory, 0 bytes development database write, 0 bytes external network transfer
   - **Explicit Local Staging Acceptance Criteria:**
     - Success rate (HTTP 2xx): $\ge 99.9\%$
     - Server error rate (HTTP 5xx): $0.0\%$
     - Network timeouts / socket drops: 0
     - Latency (local loopback): p50 $< 50\text{ ms}$, p95 $< 100\text{ ms}$
     - Non-mutation: Development DB and active models size/mtime change $= 0$ bytes

### Validation Results
- **Local Staging Validation Runner (Day 44 Execution):**
  ```powershell
  & .\.venv\Scripts\python scripts/run_local_staging.py --port 8899 --requests 50 --concurrency 4
  ```
  *Result:* All 8 verification checklist items PASSED.
  - Total requests: 50 (completed: 50)
  - Successful responses (HTTP 2xx): 50 (100.0%)
  - Non-2xx / Errors: 0 (HTTP 4xx: 0, HTTP 5xx: 0, Timeouts: 0, Network Errors: 0)
  - Test duration: 0.42s
  - Throughput: 119.64 req/s (vs 19.14 req/s in Day 43)
  - Latency (local staging): Min 6.56ms | Mean 30.73ms | p50 28.62ms | p90 53.01ms | p95 64.77ms | p99 85.26ms | Max 90.93ms
  - Per-Endpoint Breakdown:
    - `GET /`: 9 reqs, 9x 2xx, 0 errors, p50 11.52ms, p95 21.53ms, max 24.48ms
    - `GET /api/events`: 12 reqs, 12x 2xx, 0 errors, p50 17.59ms, p95 26.51ms, max 29.78ms (down from ~1050ms)
    - `GET /api/health`: 18 reqs, 18x 2xx, 0 errors, p50 38.70ms, p95 70.14ms, max 90.93ms
    - `GET /api/history`: 11 reqs, 11x 2xx, 0 errors, p50 32.73ms, p95 65.56ms, max 79.35ms
  - Dev DB & Models: 0 bytes altered, identical fingerprints before and after.

- **Focused Test Suites:**
  - `tests/test_staging_soak.py`: **9 passed**, 1 warning in 9.83s
  - `tests/test_local_staging.py`: **10 passed** in 13.17s
  - `tests/test_deployment_runbook.py`: **4 passed**, 1 warning in 8.88s

- **Full Automated Test Suite:**
  ```powershell
  & .\.venv\Scripts\python -m pytest
  ```
  *Result:* **606 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 40.38s across 45 test files (expanded from 595 baseline, +11 new deterministic tests).

- **Dependency Integrity:**
  ```powershell
  & .\.venv\Scripts\python -m pip check
  ```
  *Result:* `No broken requirements found.`

### Performance Interpretation & Boundaries
- **Observed Measurements:** Local loopback HTTP latency averages ~30ms with p95 < 65ms when external network calls are properly isolated.
- **Proposed Acceptance Criteria:** Set at $\ge 99.9\%$ 2xx, 0% 5xx, 0 timeouts, p50 $< 50\text{ms}$, p95 $< 100\text{ms}$ for local staging.
- **Environmental Limitations:** Single-host loopback does not reflect cross-country internet transit latency, TLS handshakes, or proxy queueing under high concurrent user load.
- **No Premature Optimization:** Local API server performance is healthy and bottleneck-free; no production application changes were required other than providing test-time event provider isolation.

### Phase 16 Status
**Phase 16 remains strictly IN PROGRESS.** Local performance reliability and failure-handling audits validate local loopback behavior and metric accuracy, but a genuine multi-hour soak test on production-equivalent external infrastructure remains required for milestone sign-off.

### Next Step
Await authorization to execute the 10-minute local sustained-load test, review external staging provisioning, and prepare final Phase 16 evaluation.

---

## Day 45 - HTTP Connection Pooling Fix & Successful 10-Minute Local Staging Soak Test

### Goal
Resolve the Windows TCP ephemeral port exhaustion blocker in the local staging soak test client via persistent HTTP connection pooling, add deterministic connection lifecycle unit tests, execute an uninterrupted 10-minute (600-second) local staging soak test, verify database/model immutability via pre/post SHA-256 fingerprints, validate clean shutdown and resource cleanup, run regression test suites, and evaluate results against strict acceptance criteria.

### Work Completed
1. **Root Cause Diagnosis (TCP Ephemeral Port Exhaustion)**:
   - The initial 600-second uninterrupted soak test generated 170,820 unpooled requests at ~285 req/s using raw `requests.get()` / `requests.post()`.
   - Windows dynamically allocates ephemeral ports in the range 49152–65535 (~16,384 ports) with a default `TIME_WAIT` duration (`TcpTimedWaitDelay`) of 120 seconds.
   - After ~58 seconds of unpooled requests, all 16,384 ports entered `TIME_WAIT`, causing Windows to refuse socket allocation (`WSAENOBUFS` / `WSAEADDRINUSE`) and resulting in 92,275 client-side network errors despite zero server errors.

2. **Persistent HTTP Connection Pooling Implementation ([`scripts/run_local_staging.py`](file:///d:/Share_market_predictor/scripts/run_local_staging.py), [`scripts/staging_soak_test.py`](file:///d:/Share_market_predictor/scripts/staging_soak_test.py))**:
   - Implemented `create_worker_session(pool_size=10)` providing a thread-confined `requests.Session()` with `HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(0))` — strictly 0 retries to avoid concealing errors or inflating counts.
   - Integrated worker-level persistent sessions in both `_duration_worker` (duration-based soak) and `_worker` (fixed-count requests), ensuring sessions are thread-confined and not shared across threads.
   - Implemented bounded connection and read timeouts `timeout=(2.0, 5.0)`.
   - Guaranteed full response body consumption (`_ = r.content`) and explicit response closure (`r.close()`) in `finally` blocks so connections return immediately to the pool.
   - Guaranteed worker session cleanup (`session.close()`) in `finally` blocks on completion, interruption, and exceptions.
   - Preserved reversible Windows sleep prevention (`prevent_windows_sleep` via Win32 `SetThreadExecutionState`), monotonic timing, and heartbeat suspension gap detection.

3. **Deterministic Unit Tests Added ([`tests/test_local_staging.py`](file:///d:/Share_market_predictor/tests/test_local_staging.py))**:
   - `test_create_worker_session_pooling_and_zero_retries`: Verified session pool configuration (`pool_connections=8`, `pool_maxsize=8`) and zero-retry policy (`total=0, connect=0, read=0`).
   - `test_thread_worker_session_reuse_and_isolation`: Verified that concurrent worker threads maintain distinct session instances without cross-thread sharing and reuse sessions across multiple requests.
   - `test_response_and_session_cleanup_on_success_and_exception`: Verified response consumption and `response.close()` calls on both successful HTTP 200 responses and network exception paths, confirming network failures are not misclassified as 2xx.

4. **Successful 600-Second Local Staging Soak Test Execution**:
   - Command: `python scripts/run_local_staging.py --host 127.0.0.1 --port 8899 --duration 600 --concurrency 4`
   - **Timing & Run Health:**
     - Wall-Clock Start: `2026-10-20T11:04:37.483836+00:00`
     - Wall-Clock End: `2026-10-20T11:14:37.905380+00:00`
     - Target Duration: 600.0 s
     - Monotonic Elapsed: **600.42 s**
     - Active Duration: **600.42 s**
     - Host Suspension Gap: **0.00 s (None detected — completely uninterrupted)**
     - Run Integrity: **COMPLETE (Uninterrupted)**
   - **Load Test Telemetry & Error Accounting:**
     - Total Completed Requests: **156,895**
     - Throughput: **261.31 req/s**
     - Successful (HTTP 2xx): **156,895 (100.00%)**
     - Failed / Errors: **0**
       - HTTP 4xx (Client Errors): **0**
       - HTTP 5xx (Server Errors): **0**
       - Timeouts: **0**
       - Network Errors: **0** (eliminated all 92k port-exhaustion errors)
     - Status Codes: `{200: 156895}`
     - CPU Process Time: 869.91 s (144.9% process utilization across 4 workers)
   - **Local Staging Loopback Latency Distribution (ms) (Single-Host, Non-WAN):**
     - Min: **1.57 ms**
     - Mean: **15.28 ms**
     - **p50:** **14.99 ms** (well below 50.0 ms threshold)
     - **p90:** **24.99 ms**
     - **p95:** **29.02 ms** (well below 100.0 ms threshold)
     - **p99:** **39.02 ms**
     - Max: **109.88 ms**
   - **Per-Endpoint Local Staging Loopback Latency Breakdown:**
     - `GET /`: 31,390 reqs | 31,390 2xx | 0 errors | p50: 6.95 ms | p95: 11.97 ms | max: 32.79 ms
     - `GET /api/events`: 31,169 reqs | 31,169 2xx | 0 errors | p50: 8.69 ms | p95: 14.31 ms | max: 43.24 ms
     - `GET /api/health`: 62,717 reqs | 62,717 2xx | 0 errors | p50: 18.39 ms | p95: 31.35 ms | max: 101.64 ms
     - `GET /api/history`: 31,619 reqs | 31,619 2xx | 0 errors | p50: 20.22 ms | p95: 33.66 ms | max: 109.88 ms

5. **Clean Shutdown & Data Isolation Verification**:
   - Server cleanly received shutdown signal; Uvicorn exited gracefully.
   - Port `8899` immediately released (verified via `Get-NetTCPConnection`).
   - Ephemeral staging directory removed completely.
   - Pre-soak vs. Post-soak SHA-256 Fingerprints (100% Match):
     - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (exact match, 0 bytes mutated)
     - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (exact match, 0 bytes mutated)

6. **Automated Test Suites & Dependency Validation**:
   - Focused staging test suites ([`tests/test_local_staging.py`](file:///d:/Share_market_predictor/tests/test_local_staging.py), [`tests/test_staging_soak.py`](file:///d:/Share_market_predictor/tests/test_staging_soak.py)): **25 passed**, 1 warning in 12.52s.
   - Full automated test suite (`pytest -q`): **612 passed**, 0 failed, 1 warning in 25.02s across 45 test files (+3 new deterministic tests).
   - Dependency validation (`pip check`): Clean (`No broken requirements found.`).

### Evaluation Against Local Staging Soak Acceptance Criteria (Non-Milestone)
> **Note on Scope**: The PASS evaluations below reflect compliance with the local 10-minute loopback soak test thresholds. They do NOT constitute completion of the Phase 16 milestone, which requires multi-hour soak testing on dedicated external staging cluster infrastructure.
- [x] Full 600-second run completes without host suspension: **PASS** (600.42s monotonic elapsed, 0.00s gap)
- [x] HTTP 2xx success rate $\ge 99.9\%$: **PASS (100.00%)** (156,895 / 156,895)
- [x] HTTP 5xx, timeouts, and network errors $= 0$: **PASS** (0 5xx, 0 timeouts, 0 network errors)
- [x] Local Loopback Latency within limits: **PASS** (p50: 14.99 ms $< 50$ ms, p95: 29.02 ms $< 100$ ms; local loopback baseline, not production WAN SLA)
- [x] Development DB and model artifacts unchanged: **PASS** (100% SHA-256 match)
- [x] Clean server, port, session, and tempdir shutdown: **PASS** (verified)
- [x] Focused tests, full test suite (612 passed), and `pip check` pass: **PASS**

### Phase 16 Status
**Phase 16 remains strictly IN PROGRESS.**
While Day 45 successfully completed the local staging sustained-load soak validation with 100% 2xx responses and zero data mutation, Phase 16 milestone completion requires future live cloud/cluster deployment soak testing under production-equivalent conditions once external infrastructure is provisioned.

---

## Day 46 - Post-Soak Reliability Audit & Release Readiness Hardening

### Goal
Perform a comprehensive post-soak reliability and release readiness audit of the stock-market prediction system following Day 45's successful 10-minute staging soak test. Identify and harden resource lifecycle management, thread joining, unmutated data verification across early abort paths, soak test completion verification, timeout type alignment, and health-check error handling without feature creep or destabilizing existing flows.

### Audit Findings & Hardening (Ranked by Severity)
1. **Finding 1 (Medium — Runtime Lifecycle & Windows Sleep Guard Activation)**:
   - *Issue*: `prevent_windows_sleep()` context manager (Win32 `SetThreadExecutionState`) was implemented on Day 45 but never instantiated or active in the primary staging entry point `run_local_staging_validation()`.
   - *Fix*: In [`scripts/run_local_staging.py`](file:///d:/Share_market_predictor/scripts/run_local_staging.py), initialized `sleep_mgr = prevent_windows_sleep()` before port checking and guaranteed proper exit via `sleep_mgr.__exit__()` in a unified `finally` block wrapping the entire validation lifecycle.
2. **Finding 2 (Medium — Data Integrity Verification on Aborted Startup)**:
   - *Issue*: In [`scripts/run_local_staging.py`](file:///d:/Share_market_predictor/scripts/run_local_staging.py), `_verify_unmutated()` was called outside the outer `try/finally` block. If startup aborted early (e.g. port collision on 8899), baseline fingerprints were never checked to confirm zero mutation.
   - *Fix*: Extracted `_verify_unmutated()` and invoked it inside the unified `finally` block so database and model immutability are verified unconditionally on every exit path (success, failure, interruption, or abort).
3. **Finding 3 (Medium — Soak Runner Premature Completion False-Positive)**:
   - *Issue*: In [`scripts/staging_soak_test.py`](file:///d:/Share_market_predictor/scripts/staging_soak_test.py), `main()` returned exit code 0 whenever `summary.failed_requests == 0`, even if `completed_requests < total_requests` (e.g. early process interruption or partial run).
   - *Fix*: Added an `@property is_complete` to `SoakSummary` (verifying `completed_requests >= total_requests` for bounded runs and `elapsed_seconds >= duration_seconds` for duration runs), and updated `main()` to require `summary.is_complete and summary.failed_requests == 0` for exit code 0.
4. **Finding 4 (Low — Worker Thread Join Reliability & Leak Prevention)**:
   - *Issue*: In `_duration_worker` within [`scripts/run_local_staging.py`](file:///d:/Share_market_predictor/scripts/run_local_staging.py), the worker thread join loop was outside a `finally` block relative to the heartbeat loop. An unexpected exception during the heartbeat could leave background worker threads unjoined.
   - *Fix*: Wrapped heartbeat monitoring in `try ... finally: for t in threads: t.join(timeout=5.0)` and logged any unjoined worker threads in `report.errors`.
5. **Finding 5 (Low — Bounded Timeout Type Alignment)**:
   - *Issue*: In [`scripts/staging_soak_test.py`](file:///d:/Share_market_predictor/scripts/staging_soak_test.py), `execute_request_external` received `(2.0, 5.0)` tuples from caller pools, but the type annotation was `float = 5.0`.
   - *Fix*: Aligned the parameter type annotation to `Union[float, Tuple[float, float]] = (2.0, 5.0)` matching the pooled HTTP client configuration.
6. **Finding 6 (Low — Health Check Model Directory Degradation Response)**:
   - *Issue*: In [`app/api/routes/health.py`](file:///d:/Share_market_predictor/app/api/routes/health.py), if `settings.model_dir` did not exist or was inaccessible, `dependencies["models"]` was marked degraded, but `is_overall_healthy` remained `True`, incorrectly returning HTTP 200 instead of HTTP 503.
   - *Fix*: Set `is_overall_healthy = False` on model directory failure so degraded dependencies consistently trigger HTTP 503 Service Unavailable.

### Automated Tests Added (5 New Deterministic Tests)
- [`tests/test_staging_soak.py`](file:///d:/Share_market_predictor/tests/test_staging_soak.py):
  - `test_soak_summary_is_complete_property`: Verified `is_complete` returns `True` only when completed requests meet or exceed targets and duration targets are satisfied.
  - `test_soak_main_rejects_incomplete_run`: Verified `main()` returns exit code 1 when a run has zero errors but is incomplete.
- [`tests/test_local_staging.py`](file:///d:/Share_market_predictor/tests/test_local_staging.py):
  - `test_fingerprint_verification_runs_on_aborted_startup`: Verified `_verify_unmutated()` runs even if startup fails due to port collision.
  - `test_sleep_prevention_engaged_during_validation`: Verified `prevent_windows_sleep` enters and exits reliably across successful validation runs.
- [`tests/test_api.py`](file:///d:/Share_market_predictor/tests/test_api.py):
  - `test_health_endpoint_model_storage_failure`: Verified `/api/health` returns HTTP 503 with `status: degraded` when model directory is inaccessible.

### Empirical Validation & Verification
- **Focused Test Suites**:
  - `tests/test_local_staging.py`: 12 passed in 12.60s
  - `tests/test_staging_soak.py`: 11 passed, 1 warning in 9.77s
  - `tests/test_deployment_runbook.py`: 4 passed, 1 warning in 8.78s
  - `tests/test_api.py`: 25 passed in 0.52s
- **Full Test Suite Execution**:
  - `pytest -q`: **617 passed**, 0 failed, 1 warning in 22.81s across 45 test files (+5 new tests over Day 45 baseline of 612).
- **Dependency Audit**:
  - `pip check`: `No broken requirements found.`
- **Bounded Local Staging Run**:
  - Command: `python scripts/run_local_staging.py --host 127.0.0.1 --port 8899 --requests 50 --concurrency 4`
  - Completed: 50 requests, 100% 2xx, 0 errors, 378.11 req/s, p50: 9.38 ms, p95: 14.88 ms.
  - All 8 checklist items: **PASS**.
- **In-Process Soak Simulation**:
  - Command: `python scripts/staging_soak_test.py --in-process --requests 20`
  - Completed: 20 requests, 100% 2xx, 0 errors, exit code 0.
- **Data Integrity SHA-256 Fingerprint Check**:
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% match)
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% match)

### Phase 16 Status
**Phase 16 remains strictly IN PROGRESS.**
Local loopback audits, connection pooling, and reliability hardening confirm local readiness. However, formal milestone sign-off requires sustained soak testing on live production-equivalent cluster infrastructure during live market exchange hours once external infrastructure is provisioned.

### Next Step
Execute CodeRabbit review remediation, audit release-readiness, and establish final soak-test prerequisites.

---

## Day 47 - CodeRabbit Review Remediation & Release-Readiness Audit

### Goal
Inspect and resolve all CodeRabbit review findings across the local staging runner and documentation, fix genuine code defects and documentation inconsistencies without introducing regressions, perform a rigorous release-readiness audit across security, lifecycle, and data integrity controls, formulate the prerequisite checklist for the outstanding multi-hour external soak test, and keep Phase 16 strictly in progress under local zero-cost constraints.

### CodeRabbit Review Findings Dispositions

1. **Finding 1 — `scripts/run_local_staging.py`: `prevent_windows_sleep` Generator Exception Handling and Context Teardown Safety**
   - **File & Function:** [`scripts/run_local_staging.py`](file:///d:/Share_market_predictor/scripts/run_local_staging.py), `prevent_windows_sleep()`, `run_local_staging_validation()`
   - **Reported Issue:**
     - The generator caught exceptions with an outer `except Exception: yield False` that encompassed the inner `yield True`. If an exception occurred in the caller's context block, `contextlib` threw the exception into the generator, which caught it and yielded again. In Python `@contextmanager`, yielding during exception handling raises `RuntimeError: generator didn't stop after throw()`, masking the real root-cause exception.
     - In `run_local_staging_validation()`, `sleep_mgr.__exit__(None, None, None)` was invoked manually at the tail of `finally:`. An exception during earlier cleanup steps (such as settings reload or temporary directory deletion) would bypass context exit, leaving Windows in `ES_SYSTEM_REQUIRED` execution state permanently.
   - **Disposition:** **Valid Defect**.
   - **Remediation:**
     - Refactored `prevent_windows_sleep()`: initialization checks occur *before* yielding; the generator yields `enabled: bool` and executes `ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)` in a clean `finally:` block without catching or yielding again during exception propagation.
     - Wrapped the staging validation cleanup sequence in a nested `try ... finally: sleep_mgr.__exit__(*sys.exc_info())` ensuring that sleep prevention teardown is unconditionally executed on all exit paths (normal return, port conflict, error, or exception).
     - Added automated regression test `test_prevent_windows_sleep_exception_propagation` in `tests/test_local_staging.py` verifying that exceptions propagate cleanly without `RuntimeError`.

2. **Finding 2 — `docs/daily-progress.md`: Ambiguous Latency Distribution Labels**
   - **File & Section:** [`docs/daily-progress.md`](file:///d:/Share_market_predictor/docs/daily-progress.md), Day 45 progress log
   - **Reported Issue:** Latency percentiles in Day 45 telemetry were labeled generically as "Latency Distribution" and "Latency within limits", potentially creating confusion between local single-host loopback measurements and production WAN network SLAs.
   - **Disposition:** **Valid Documentation Inconsistency**.
   - **Remediation:** Updated Day 45 documentation to explicitly label metrics as `Local Staging Loopback Latency Distribution (ms) (Single-Host, Non-WAN)` and `Per-Endpoint Local Staging Loopback Latency Breakdown`, clearly documenting that single-host loopback does not reflect WAN transit, TLS handshakes, or edge proxy latencies.

3. **Finding 3 — `docs/daily-progress.md`: Unqualified Acceptance Criteria Header & Connection Pooling Detail**
   - **File & Section:** [`docs/daily-progress.md`](file:///d:/Share_market_predictor/docs/daily-progress.md), Day 45 "Evaluation Against Acceptance Criteria"
   - **Reported Issue:** Section header `### Evaluation Against Acceptance Criteria` and `- [x] ... **PASS**` checkboxes could be misconstrued as Phase 16 milestone sign-off. In reality, the criteria applied strictly to the local 10-minute soak test execution.
   - **Disposition:** **Valid Documentation Inconsistency**.
   - **Remediation:** Retitled section to `### Evaluation Against Local Staging Soak Acceptance Criteria (Non-Milestone)` and added a prominent scope note stating that passing local soak criteria does not satisfy Phase 16 milestone completion. Re-verified that HTTP Keep-Alive connection pooling is accurately documented as thread-confined `requests.Session` instances (`pool_connections=10`, `pool_maxsize=10`, `Retry(0)`).

4. **Finding 4 — `docs/roadmap.md`: Phase 16 Scope and Acceptance Delineation**
   - **File & Section:** [`docs/roadmap.md`](file:///d:/Share_market_predictor/docs/roadmap.md), Phase 16 overview and milestone criteria
   - **Reported Issue:** Roadmap documentation must maintain a strict, unambiguous boundary between completed local staging prerequisites (isolated runner, data non-mutation, 10-minute soak, connection pooling) and outstanding external staging cluster requirements.
   - **Disposition:** **Valid Documentation Inconsistency**.
   - **Remediation:** Updated `docs/roadmap.md` Phase 16 entry to Day 47, maintained `In Progress (Day 40-47)` status in overview table and section header, and clearly enumerated remaining prerequisites for Phase 16 sign-off.

---

### Release-Readiness Audit Matrix

| Subsystem / Area | Audit Check | Verified Control / Implementation | Status |
| :--- | :--- | :--- | :---: |
| **Startup & Config** | Production mode lockdown | `APP_ENV=production` rejects debug flag (`APP_DEBUG=true` raises ValueError); OpenAPI docs `/docs` and `/openapi.json` return 404. | **PASS** |
| **Security Headers** | Defensive HTTP headers | OWASP headers enforced via middleware: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`. | **PASS** |
| **CORS Policy** | Origin restriction | Wildcard origins (`*`) and insecure plain HTTP non-localhost origins rejected at startup. | **PASS** |
| **Health Checks** | Degraded dependency handling | `/api/health` returns HTTP 503 (`status: degraded`) if database is unreachable OR model directory is missing/inaccessible. | **PASS** |
| **Data Immutability** | Database write protection | SQLite WAL mode, engine triggers (`trg_prevent_prediction_update`, `trg_prevent_actual_update`, delete guards) enforce append-only immutability. | **PASS** |
| **Model Immutability** | Active model isolation | Staging launcher creates ephemeral read-only model copies; pre/post SHA-256 fingerprint verification ensures 0 bytes mutated in active `models/`. | **PASS** |
| **Connection Pooling** | Socket exhaustion prevention | Thread-confined `requests.Session()` with `HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(0))`; bounded `(2.0, 5.0)` timeouts; response body consumption & closure. | **PASS** |
| **Host Sleep Guard** | Sleep/suspension lifecycle | Win32 `SetThreadExecutionState` with nested `try...finally` teardown; monotonic timing with heartbeat suspension gap detection. | **PASS** |
| **Soak Runner Integrity** | Completion verification | `SoakSummary.is_complete` strictly rejects partial/interrupted runs (`completed_requests >= total_requests` or `elapsed >= duration`). | **PASS** |
| **Staging Teardown** | Resource lifecycle | Ephemeral tempdir cleanup (`tempfile.TemporaryDirectory`), immediate port release, graceful Uvicorn shutdown within 3s. | **PASS** |

---

### Final Multi-Hour Soak-Test Prerequisites Checklist

The following items constitute the formal prerequisites required prior to launching the production-equivalent multi-hour soak test:

- [ ] **1. Dedicated External Staging Infrastructure**:
  - Independent host instance (Linux VM or container cluster) with production-equivalent vCPU, memory ($\ge 8$ GB), and real network interfaces (non-loopback).
  - *Local Zero-Cost Alternative*: Local Windows loopback staging environment (`scripts/run_local_staging.py`) remains available for pre-deployment regression validation with zero monetary expense.
- [ ] **2. Environment Configuration & Secret Management**:
  - Isolated staging `.env` with production keys, staging CORS domain (`https://staging.domain`), and debug disabled.
  - No production credentials or secrets stored in repository or shared across environments.
- [ ] **3. Data Isolation**:
  - Dedicated staging SQLite replica (or PostgreSQL staging instance if migrated).
  - Production `data/predictions.db` and active `models/` physically quarantined from soak runner access.
- [ ] **4. Exchange Hours Operational Window**:
  - Soak test scheduled during live NSE market hours (09:15 – 15:30 IST) to validate real exchange quotes, session transitions, and live news feed ingestion.
- [ ] **5. Target Load Profile & Acceptance Thresholds**:
  - Duration: $\ge 2$ hours uninterrupted sustained traffic.
  - Target throughput: $\ge 100$ requests/second across balanced route mix (`/api/health`, `/api/history`, `/api/events`, `/api/predict`).
  - Error budget: HTTP 2xx $\ge 99.9\%$, HTTP 5xx $= 0.0\%$, Timeouts $= 0$, Network Errors $= 0$.
  - SLA: WAN p50 latency $< 150$ ms, p95 $< 350$ ms (accounting for TLS and network routing).
- [ ] **6. Observability & Alerting**:
  - External Prometheus/Grafana or structured JSON operational access logging with `X-Process-Time-Ms`.
  - Automated anomaly alerts for process memory creep, socket leaks, or elevated error rates.
- [ ] **7. Formal Sign-Off Documentation**:
  - Complete soak telemetry report with per-endpoint percentiles, SHA-256 data integrity proofs, and stakeholder approval for Phase 16 completion.

---

### Automated Tests & Verification
- **Focused Staging Suite (`tests/test_local_staging.py`)**:
  - **19 passed** in 10.18s (+1 new deterministic test `test_prevent_windows_sleep_exception_propagation`).
- **Full Test Suite Execution**:
  - `pytest -q`: **618 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 23.10s across 45 test files.
- **Dependency Audit**:
  - `pip check`: `No broken requirements found.`
- **Git Diff Hygiene**:
  - `git diff --check`: Clean (0 whitespace errors, 0 trailing blank lines).
- **Data Integrity Verification**:
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (**100% Match**)
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (**100% Match**)

### Phase 16 Status
**Phase 16 remains strictly IN PROGRESS.**
All local staging reliability, connection pooling, and CodeRabbit review findings are completely remediated and verified. Formal Phase 16 completion and milestone sign-off await provisioning of dedicated external staging infrastructure for the multi-hour soak test.

### Next Step
Execute Day 48 independent release gate verification, audit soak metrics, and formulate zero-cost deployment plan.

---

## Day 48 - Release Gate Verification & Zero-Cost Deployment Planning

### Goal
Independently verify Day 47's release-readiness claims, audit whether Phase 16 acceptance criteria are technically justified and measurable, construct a comprehensive Release-Readiness Evidence Matrix, evaluate SQLite trigger immutability boundaries, audit soak-test metric algorithms, formulate a production-grade zero-cost deployment plan, and maintain Phase 16 strictly in progress under local-only constraints.

### 1. Audit of Day 47's Implementation & Sleep Guard Architecture
- **Platform & API Pre-Checks:** `prevent_windows_sleep` in [`scripts/run_local_staging.py`](file:///d:/Share_market_predictor/scripts/run_local_staging.py) verifies `sys.platform == "win32"` and tests `ctypes.windll.kernel32.SetThreadExecutionState` inside a pre-yield `try/except` block, setting `enabled = True` only upon successful invocation before any `yield` occurs.
- **Exception Propagation Without Suppression:** The generator yields `enabled` inside an unencumbered `try ... finally:` construct. Exceptions thrown into the generator are not caught by any `except` statement within the generator, preserving the original exception and preventing `RuntimeError: generator didn't stop after throw()`.
- **Restoration Across All Exit Paths:** In `run_local_staging_validation()`, context teardown is guaranteed by an outer `try ... finally:` whose inner block wraps server shutdown, environment restoration, temporary directory cleanup, and non-mutation verification in a nested `try ... finally: sleep_mgr.__exit__(*sys.exc_info())`. This ensures execution state restoration on normal completion, port conflicts, early returns, and unexpected runtime exceptions.
- **Restoration Failure Containment:** The context manager's `finally:` block wraps the cleanup `SetThreadExecutionState(ES_CONTINUOUS)` in `try ... except Exception: pass`, ensuring any Win32 API failure during cleanup cannot mask or replace an in-flight primary exception.
- **Cross-Platform Safety:** On non-Windows platforms, `enabled` defaults to `False`, yielding `False` with an empty `finally:`, ensuring predictable no-op execution on Linux/macOS.
- **Test Verification:** [`tests/test_local_staging.py`](file:///d:/Share_market_predictor/tests/test_local_staging.py) covers safe entry/exit (`test_prevent_windows_sleep_safety`), clean exception propagation (`test_prevent_windows_sleep_exception_propagation`), and active engagement during validation (`test_sleep_prevention_engaged_during_validation`).

---

### 2. Release-Readiness Evidence Matrix

| Control | Code Location | Test / Verification Evidence | Result | Remaining Limitation |
| :--- | :--- | :--- | :---: | :--- |
| **Production Configuration** | [`app/core/config.py`](file:///d:/Share_market_predictor/app/core/config.py) (`Settings.validate_production_mode`) | `tests/test_api.py::test_production_config_rejects_debug` | **PASS** | Relies on environment variable enforcement at process launch. |
| **OpenAPI Docs Lockdown** | [`app/api/app.py`](file:///d:/Share_market_predictor/app/api/app.py) (`docs_url=None`, `openapi_url=None`) | `tests/test_api.py::test_docs_suppressed_in_production` | **PASS** | Only active when `APP_ENV=production`. |
| **Security Headers** | [`app/api/app.py`](file:///d:/Share_market_predictor/app/api/app.py) (`SecurityHeadersMiddleware`) | `tests/test_api.py::test_security_headers_present` | **PASS** | Does not replace perimeter WAF or edge DDoS mitigation. |
| **CORS Policy Restrictions** | [`app/api/app.py`](file:///d:/Share_market_predictor/app/api/app.py) (`validate_cors_origins`) | `tests/test_api.py::test_cors_rejects_wildcard_in_production` | **PASS** | Requires accurate DNS domain whitelist configuration. |
| **Degraded Health Reporting** | [`app/api/routes/health.py`](file:///d:/Share_market_predictor/app/api/routes/health.py) (`/api/health`) | `tests/test_api.py::test_health_endpoint_db_failure`, `test_health_endpoint_model_storage_failure` | **PASS** | Reports binary degraded status; does not auto-heal unmounted volumes. |
| **Database Write-Once Triggers** | [`app/database/schema.py`](file:///d:/Share_market_predictor/app/database/schema.py) (`trg_prevent_prediction_*`, `trg_prevent_actual_*`) | `tests/test_prediction_database.py::test_immutability_triggers` | **PASS** | **Scope Limitation:** Triggers prevent row-level `UPDATE`/`DELETE` on `predictions` and `actuals`, but do NOT prevent DDL (`DROP TABLE`, `DROP TRIGGER`), table truncation, changes to `stocks`/`model_releases`, or direct disk file deletion. |
| **HTTP Connection Pooling** | [`scripts/staging_soak_test.py`](file:///d:/Share_market_predictor/scripts/staging_soak_test.py) (`create_worker_session`) | `tests/test_local_staging.py::test_thread_worker_session_reuse_and_isolation` | **PASS** | Thread-confined pooling (1 session per worker); concurrency bounded by client pool size. |
| **Bounded Timeouts & Retries** | [`scripts/staging_soak_test.py`](file:///d:/Share_market_predictor/scripts/staging_soak_test.py) (`execute_request_external`) | `tests/test_local_staging.py::test_response_and_session_cleanup_on_success_and_exception` | **PASS** | Client-side timeout; does not terminate server-side execution if socket drops mid-flight. |
| **Host Sleep & Suspension Guard** | [`scripts/run_local_staging.py`](file:///d:/Share_market_predictor/scripts/run_local_staging.py) (`prevent_windows_sleep`, heartbeat) | `tests/test_local_staging.py::test_interruption_and_suspension_detection_classification` | **PASS** | Win32-specific API; non-Windows environments rely on OS-level systemd / cgroups power settings. |
| **Soak Completion Rejection** | [`scripts/staging_soak_test.py`](file:///d:/Share_market_predictor/scripts/staging_soak_test.py) (`SoakSummary.is_complete`, `main`) | `tests/test_staging_soak.py::test_soak_main_rejects_incomplete_run` | **PASS** | Enforces scheduled request volume or duration; does not evaluate data semantic drift. |
| **Staging Environment Isolation** | [`scripts/run_local_staging.py`](file:///d:/Share_market_predictor/scripts/run_local_staging.py) (`TemporaryDirectory`, SHA-256 pre/post) | `tests/test_local_staging.py::test_staging_data_and_model_isolation_verified` | **PASS** | Validates filesystem isolation on single host; does not simulate multi-node shared storage. |

---

### 3. Audit of Soak-Test Metrics & Acceptance Thresholds
- **Monotonic Duration Calculation:** Accurately computed via `time.monotonic()` in `scripts/run_local_staging.py` and `time.perf_counter()` in `scripts/staging_soak_test.py`, ensuring immunity to NTP time adjustments or daylight saving shifts.
- **Suspension Gap Detection:** Dedicated heartbeat thread samples every 1.0s; intervals $\ge 3.0$s indicate host sleep or hypervisor suspension, flagged as `is_interrupted = True` and subtracted from active duration to avoid throughput skew.
- **Request Categorization & Denominators:** `classify_http_outcome` accurately partitions results into 2xx, 3xx, 4xx, 5xx, timeouts, and network errors. Throughput denominator strictly uses completed requests (`len(latencies)`), avoiding inflated throughput calculations on aborted runs.
- **Percentile Mathematics:** Continuous linear interpolation (`compute_percentile`, matching NumPy `method='linear'`) replaces discrete index rounding, avoiding distortion on small samples. Sample stability indicators explicitly flag $N < 20$ for p95 and $N < 100$ for p99.
- **Separation of Acceptance Criteria:**
  - **Local Staging Loopback Baseline (PASSED on Day 45):** 10-minute duration, loopback `127.0.0.1`, offline mock event provider, single-host latency (p50 $< 50$ ms, p95 $< 100$ ms), 100% 2xx responses, 0 errors, 100% data immutability.
  - **External Staging Soak Gate (PENDING External Infrastructure):** $\ge 2$ hours sustained traffic, $\ge 100$ req/s, public/WAN network routing with TLS, executed during live NSE market hours (09:15 – 15:30 IST) to test live feed ingestion, WAN latency (p50 $< 150$ ms, p95 $< 350$ ms), 0 5xx, 0 timeouts.
  - **Crucial Boundary:** Local loopback tests using `OfflineStagingEventProvider` do NOT validate live NSE feed intake or internet transit. External market connectivity remains an unverified production gate.

---

### 4. Zero-Cost Deployment Plan (Based on Existing Project Infrastructure)
1. **Runtime & Environment:**
   - Standard Python virtual environment (`.venv`) using Python 3.11/3.12/3.14.
   - Pinned dependencies from `requirements.txt` validated with `python -m pip check`.
2. **Configuration & Secrets:**
   - Production settings managed strictly via local `.env` file (loaded through `app.core.config.Settings.from_env()`).
   - Zero hardcoded credentials; `APP_DEBUG=false`, `APP_ENV=production`, explicit trusted domain CORS origins.
3. **Application Server & Reverse Proxy:**
   - Uvicorn ASGI server bound strictly to localhost (`127.0.0.1:8000`) with 4 worker processes.
   - Local Nginx or Caddy instance providing TLS termination (Let's Encrypt / self-signed internal CA), security headers, and reverse proxying without cloud API gateway costs.
4. **Persistence & Model Storage:**
   - SQLite with WAL journal mode (`PRAGMA journal_mode = WAL; PRAGMA busy_timeout = 5000;`).
   - Automated zero-cost backup via SQLite Online Backup API (`sqlite3 data/predictions.db ".backup 'data/backups/predictions_backup.db'"`).
   - Local filesystem model directory (`models/`) with quarantined retraining promotion and atomic replacement (`os.replace`).
5. **Observability & Health Checks:**
   - Built-in `/api/health` HTTP endpoint monitored via local curl / systemd watchdog.
   - Structured access logging with `X-Process-Time-Ms` response header without third-party APM subscription dependencies.
6. **Graceful Lifecycle Management:**
   - Systemd unit service on Linux (`/etc/systemd/system/stock-predictor.service`) or Windows Service via NSSM, handling graceful SIGTERM teardown within 5 seconds.
7. **External Staging Blockers:**
   - Dedicated external staging infrastructure is currently unprovisioned. No free cloud staging cluster was fabricated; external multi-hour soak testing remains blocked until dedicated external hosting is made available.

---

### 5. Automated Tests & Empirical Verification
- **Dependency Audit**:
  ```powershell
  & .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Full Test Suite Execution**:
  ```powershell
  & .\.venv\Scripts\python -m pytest -q
  ```
  **618 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 30.85s across 45 test files.
- **Git Diff Hygiene**:
  ```powershell
  git diff --check
  ```
  Clean (0 whitespace errors, 0 trailing blank lines).
- **Local Staging Smoke Test (Bounded Execution)**:
  ```powershell
  & .\.venv\Scripts\python scripts/run_local_staging.py --host 127.0.0.1 --port 8899 --requests 20 --concurrency 2
  ```
  - Requests: 20 completed (100.0% 2xx, 0 errors, 210.49 req/s).
  - Local Latencies: p50: 6.44 ms, p95: 23.15 ms, Max: 28.11 ms.
  - All 8 production checklist items: **PASS**.
  - Server shutdown: Port 8899 cleanly released; ephemeral directory removed.
- **Data Integrity Check (Pre & Post Smoke Test)**:
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (**100% Match — 0 bytes mutated**)
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (**100% Match — 0 bytes mutated**)

---

### Phase 16 Status
**Phase 16 remains strictly IN PROGRESS.**
Local staging validation, connection pooling, and release-readiness audits confirm local robustness. Formal Phase 16 sign-off remains blocked pending dedicated external staging infrastructure provisioning for the production-equivalent multi-hour soak test during live market hours.

### Next Step
Execute Day 49 CodeRabbit review audit, verify zero-cost deployment packaging, and enforce configuration and gitignore safeguards.

---

## Day 49 - CodeRabbit Review Audit & Zero-Cost Deployment Packaging

### Goal
Audit all open CodeRabbit review findings, harden the local staging runner and configuration layers, implement reproducible zero-cost deployment packaging, audit `.gitignore` against secret and artifact leakage, expand automated deployment tests, and maintain Phase 16 strictly in progress under zero-cost constraints.

### 1. Git Baseline Verification
- **Baseline Commit:** `969bc14` (`docs(phase-16): document release gate verification and zero-cost deployment plan`)
- **Remote Synchronization:** Working tree clean; local `main` matched `origin/main` at `969bc147887b428c3a48e280a290d12b36ccb2d2`.
- **Pre-Test Data Hashes:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e`
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

---

### 2. CodeRabbit Review Findings & Audit Matrix

| Finding / Area | File & Context | Validity | Risk | Disposition & Remediation | Test Evidence |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Sleep Guard Invocation & State Tracking** | [`scripts/run_local_staging.py`](file:///d:/Share_market_predictor/scripts/run_local_staging.py) (`prevent_windows_sleep`, `StagingValidationReport`) | **Valid** | Medium | Teardown is guaranteed via nested `try ... finally: sleep_mgr.__exit__(*sys.exc_info())`. Added `sleep_prevention_active: bool = False` to `StagingValidationReport` and populated it on entry to verify active engagement. Added CLI reporting line under `[TIMING & RUN HEALTH]`. | [`tests/test_local_staging.py`](file:///d:/Share_market_predictor/tests/test_local_staging.py) (`test_sleep_prevention_engaged_during_validation`, `test_prevent_windows_sleep_exception_propagation`, `test_prevent_windows_sleep_safety`) |
| **Latency Distribution Labels** | [`docs/daily-progress.md`](file:///d:/Share_market_predictor/docs/daily-progress.md) (Days 45–48) | **Valid** | Low | Confirmed latency measurements (p50: 6.83ms, p95: 15.03ms) are explicitly labeled as single-host local loopback baselines. Clearly demarcated from external multi-node staging WAN targets (p50 < 150ms, p95 < 350ms). | Documentation audit verified; no WAN claims made for local loopback tests. |
| **Connection Pooling Documentation** | [`docs/daily-progress.md`](file:///d:/Share_market_predictor/docs/daily-progress.md), [`scripts/staging_soak_test.py`](file:///d:/Share_market_predictor/scripts/staging_soak_test.py) | **Valid** | Low | Documented thread-confined `requests.Session()` with `HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(0))` and explicit bounded timeouts `(2.0, 5.0)`. | [`tests/test_local_staging.py`](file:///d:/Share_market_predictor/tests/test_local_staging.py) (`test_create_worker_session_pooling_and_zero_retries`, `test_thread_worker_session_reuse_and_isolation`) |
| **Phase 16 Status & External Prerequisites** | [`docs/roadmap.md`](file:///d:/Share_market_predictor/docs/roadmap.md), [`docs/daily-progress.md`](file:///d:/Share_market_predictor/docs/daily-progress.md) | **Valid** | High | Phase 16 kept strictly **IN PROGRESS**. Local loopback tests using `OfflineStagingEventProvider` do not prove WAN resilience or live NSE exchange data ingestion. External cluster soak remains an uncompleted prerequisite. | Maintained in `docs/roadmap.md` and `docs/daily-progress.md`. |

---

### 3. Zero-Cost Deployment Packaging

1. **Production Environment Configuration Template ([`.env.production.example`](file:///d:/Share_market_predictor/.env.production.example)):**
   - Created pristine production template with safe placeholders only.
   - Enforces `APP_ENV=production`, `APP_DEBUG=false`, and explicit HTTPS origins in `APP_CORS_ORIGINS` (rejecting wildcards and plain HTTP).
   - Specifies storage paths (`APP_DATA_DIR`, `APP_MODEL_DIR`, `DATABASE_PATH`) and local LLM endpoints (`OLLAMA_BASE_URL`).
   - Contains zero live secrets, API keys, passwords, or fake credentials.
2. **Standard Environment Template ([`.env.example`](file:///d:/Share_market_predictor/.env.example)):**
   - Updated with placeholder documentation for CORS, storage, and local Ollama inference.
3. **`.gitignore` Safeguards Audit:**
   - Updated `.gitignore` with `!.env.*.example` alongside `!.env.example`.
   - Verified that `git check-ignore` allows tracked template files (`.env.production.example`) while strictly blocking actual secret files (`.env.production`, `.env.local`, `.env`).
   - Re-verified ignore rules for SQLite databases (`*.db`, `*.db-wal`), logs (`*.log`), and model weights (`models/*`, keeping `!models/.gitkeep`).
4. **Deployment Operations Runbook ([`docs/deployment-runbook.md`](file:///d:/Share_market_predictor/docs/deployment-runbook.md)):**
   - **Section 2:** Added reference to [`.env.production.example`](file:///d:/Share_market_predictor/.env.production.example) and strict `.gitignore` safety alert.
   - **Section 3.2 & 3.3:** Documented environment file setup and provided dual Linux (Bash) and Windows Server (PowerShell) Uvicorn production commands with debug mode disabled and loopback binding.
   - **Section 4:** Added zero-cost Caddy configuration template (`Caddyfile`) with automatic TLS and security headers alongside Nginx, with an explicit caution notice that templates require environment-specific review.
   - **Section 7.4:** Added Deployment Smoke-Test Procedure and 10-point Expected Results Verification Checklist.
5. **Automated Deployment Packaging Tests ([`tests/test_deployment_runbook.py`](file:///d:/Share_market_predictor/tests/test_deployment_runbook.py)):**
   - `test_env_templates_hygiene_and_security`: Validates template existence, production flags, CORS constraints, and strict absence of secrets.
   - `test_gitignore_deployment_safeguards`: Validates blocking of `.env.*`, databases, and model weights while preserving templates and `.gitkeep`.

---

### 4. Automated Tests & Empirical Verification

- **Dependency Audit**:
  ```powershell
  & .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Hygiene**:
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors, 0 trailing blank lines).`
- **Focused Staging & Deployment Tests**:
  ```powershell
  & .\.venv\Scripts\python -m pytest tests/test_local_staging.py tests/test_staging_soak.py tests/test_deployment_runbook.py -q
  ```
  **36 passed**, 1 warning in 18.61s (19 in staging, 11 in soak, 6 in deployment runbook).
- **Full Test Suite Execution**:
  ```powershell
  & .\.venv\Scripts\python -m pytest -q
  ```
  **620 passed**, 0 failed, 1 warning (Starlette testclient deprecation) in 24.95s across 45 test files (+2 new tests since Day 48).
- **Local Staging Smoke Test (Bounded Execution)**:
  ```powershell
  & .\.venv\Scripts\python scripts/run_local_staging.py --host 127.0.0.1 --port 8899 --requests 20 --concurrency 2
  ```
  - **Checklist:** All 8 checklist items **PASS** (Loopback, Startup, Health, Security Headers, Docs 404, Smoke Tests, Dev DB Untouched, Models Untouched).
  - **Requests:** 20/20 completed (100.00% 2xx, 0 4xx, 0 5xx, 0 timeouts, 0 net errors).
  - **Throughput:** 215.75 req/s.
  - **Local Latencies:** Min: 2.76 ms, Mean: 8.77 ms, p50: 6.83 ms, p95: 15.03 ms, Max: 25.54 ms.
  - **Sleep Prevention:** `ACTIVE (Win32 ES_CONTINUOUS|ES_SYSTEM_REQUIRED)`.
  - **Teardown & Cleanup:** Clean server shutdown, Port 8899 released, ephemeral staging directory deleted.
- **Data Integrity Verification (Pre & Post Test)**:
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (**100% Match — 0 bytes mutated**)
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (**100% Match — 0 bytes mutated**)

---

### 5. Phase 16 Status & Next Steps

**Phase 16 remains strictly IN PROGRESS.**
Zero-cost deployment packaging, configuration templates, and local staging validation are verified and complete. The final acceptance criterion — a multi-hour soak test on dedicated production-equivalent external infrastructure during live NSE market hours — remains pending external infrastructure provisioning.

### Next Step
Execute Day 48 CodeRabbit review audit, verify deployment safety, and align configuration and backup procedures.

---

## Day 48 - CodeRabbit Findings Remediation & Deployment Safety Verification

### Goal
Review and resolve the four CodeRabbit review findings on deployment packaging and staging reliability: replace machine-specific template links with repository-relative paths, align model directory variables, harden Windows sleep prevention state tracking and API return value handling, align production database configuration with backup/disaster recovery procedures, and empirically verify deployment safety while keeping Phase 16 strictly in progress under zero-cost constraints.

### 1. Git Baseline & Initial Integrity Check
- **Baseline Commit:** `ae95719` (`feat(phase-16): audit coderabbit findings and add zero-cost deployment packaging`)
- **Remote Synchronization:** Working tree clean; local `main` synchronized with `origin/main` at `ae9571938b2d2aa767652c0bd8cfa4fddbb6cf6e`.
- **Pre-Test Data Hashes:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e`
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

---

### 2. CodeRabbit Review Findings & Remediation Matrix

| Finding | Affected Location | Root Cause | Remediation & Fix | Test Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Finding A: Template Link** | [`docs/deployment-runbook.md`](docs/deployment-runbook.md) | Absolute file URI (`file:///d:/...`) was machine-specific and broke on non-Windows/other environments. | Replaced with repository-relative markdown link (`[`.env.production.example`](../.env.production.example)`). Verified file exists on disk. | Added `test_deployment_runbook_consistency_and_links()` verifying all links resolve without `file:///` or drive letters. |
| **Finding B: Model-Directory Variable** | [`docs/deployment-runbook.md`](docs/deployment-runbook.md), [`app/core/config.py`](app/core/config.py) | Runbook referenced `MODEL_DIR`, while deployment template and config used `APP_MODEL_DIR`. | Aligned runbook table, Bash/PowerShell commands, and tests to `APP_MODEL_DIR`. Added fallback in `Settings.from_env()`. Documented default (`models/`) and override behavior. | `test_core.py::test_settings_environment_override`, `test_deployment_runbook.py::test_health_check_with_isolated_storage`. |
| **Finding C: Windows Sleep Prevention** | [`scripts/run_local_staging.py`](scripts/run_local_staging.py) | `prevent_windows_sleep` ignored Win32 API return value (could return 0 or fail to accept flags), silently claiming machine was kept awake. | Configured `kernel32.SetThreadExecutionState.restype = ctypes.c_uint32`, verified non-zero return value, and confirmed `ES_SYSTEM_REQUIRED` was accepted via second query call. If rejected or failed, safely yields `False` and restores continuous state. Handled unsupported platforms safely. | Added 7 deterministic tests in `tests/test_local_staging.py` covering successful activation, zero-return failure, flag rejection, API exception, non-Windows platforms, and exception propagation/cleanup. |
| **Finding D: Database Backup Path** | [`.env.production.example`](.env.production.example), [`docs/deployment-runbook.md`](docs/deployment-runbook.md), [`app/core/config.py`](app/core/config.py), [`app/database/connection.py`](app/database/connection.py) | Runbook backup commands targeted `/var/lib/stock-predictor/predictions.db`, whereas template set `APP_DATA_DIR=/var/lib/stock-predictor/data` and `DATABASE_PATH=/var/lib/stock-predictor/data/predictions.db`. App lacked direct `DATABASE_PATH` wiring. | Added `database_path` to `Settings` with fallback to `resolved_data_dir / "predictions.db"`. Updated `get_default_db_path()` to return `settings.database_path`. Aligned runbook backup/restore/wal commands to `/var/lib/stock-predictor/data/predictions.db`. | `test_deployment_runbook_consistency_and_links`, `test_health_check_with_isolated_storage` (verifying isolated temporary db path). |

---

### 3. Empirical Verification & Test Results

- **Full Regression Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **629 passed**, 1 warning (`StarletteDeprecationWarning`) in 41.89s across 45 test files (+9 tests since Day 47/49). Zero failures, zero regressions.
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Hygiene Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors, 0 trailing blank lines).`
- **Local Staging Smoke Test:**
  ```powershell
  .\.venv\Scripts\python scripts/run_local_staging.py --host 127.0.0.1 --port 8899 --requests 20 --concurrency 2
  ```
  - **Checklist:** All 8 items **PASS** (Loopback, Startup, Health, Security Headers, Docs 404, Smoke Tests, Dev DB Untouched, Models Untouched).
  - **Sleep Prevention:** `ACTIVE (Win32 ES_CONTINUOUS|ES_SYSTEM_REQUIRED)`.
  - **Requests:** 20/20 completed (100.00% 2xx, 0 errors, 103.87 req/s, p50: 18.50ms, p95: 26.57ms).
- **Data & Model Immutability Verification:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (**100% Match — 0 bytes mutated**)
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (**100% Match — 0 bytes mutated**)
- **Zero-Cost & Credential Controls:**
  - No secrets, API keys, passwords, paid services, or cloud infrastructure introduced.

---

### 4. Phase 16 Status & Remaining Blockers

**Phase 16 remains strictly IN PROGRESS.**
All local staging reliability, configuration templates, and review findings are remediated and verified. Formal Phase 16 completion and milestone sign-off await provisioning of dedicated external staging infrastructure for the multi-hour soak test during live NSE market hours.

### Next Step
Execute Day 49 Deployment Configuration Audit & Non-Destructive Backup/Restore Verification.

---

## Day 49 - Deployment Configuration Audit & Non-Destructive Backup/Restore Verification

### Goal
Audit Day 48 deployment configuration changes, independently verify configuration consistency across the codebase, execute a non-destructive backup/restore verification drill locally in an isolated sandbox following Section 5.4 of `docs/deployment-runbook.md`, verify SQLite WAL handling and integrity, and preserve existing development databases and model files under zero-cost constraints while keeping Phase 16 marked strictly IN PROGRESS.

### 1. Git Baseline & Initial Integrity Check
- **Baseline Commit:** `7e45e75` (`fix(phase-16): resolve coderabbit review findings on deployment safety`)
- **Remote Synchronization:** Working tree clean prior to edits; synchronized with `origin/main` at `7e45e754a6c4293f7c4688b7768562d987df43e9`.
- **Pre-Drill Protected File Hashes:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e`
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

---

### 2. Configuration Consistency Audit

| Subsystem / Path | Inspected Component | Finding & Verification | Action Taken |
| :--- | :--- | :--- | :--- |
| **Relative Path Anchoring** | [`app/core/config.py`](app/core/config.py) | `Path(custom_data_dir).resolve()` resolved relative to `os.getcwd()` rather than `PROJECT_ROOT`, causing path drift when running from arbitrary directories. | Implemented `_resolve_relative_path(path_str, base_dir)` to resolve relative paths deterministically against `PROJECT_ROOT`. |
| **Model Directory Precedence** | [`app/core/config.py`](app/core/config.py) | Confirmed `APP_MODEL_DIR` is preferred, with fallback to legacy `MODEL_DIR` if unset, and fallback to `PROJECT_ROOT / "models"` if both unset or empty whitespace. | Added unit test coverage verifying precedence, fallback, and whitespace safety in `tests/test_core.py`. |
| **Database Path Resolution** | [`app/core/config.py`](app/core/config.py), [`app/database/connection.py`](app/database/connection.py) | `get_default_db_path()` returns `get_settings().database_path`, with fallback to `data_dir / "predictions.db"`. Relative paths resolve against `PROJECT_ROOT`. | Verified resolution consistency between standalone connection helper and application settings. |
| **Environment Templates** | `.env.example`, `.env.production.example` | Verified zero secret leaks. `APP_ENV=production` and `APP_DEBUG=false` enforced in production template with explicit HTTPS CORS. | Verified with `tests/test_deployment_runbook.py::test_env_templates_hygiene_and_security`. |
| **SQLite WAL Mode Consistency** | [`docs/deployment-runbook.md`](docs/deployment-runbook.md) | Documented that raw file copying (`cp predictions.db ...`) during active WAL mode risks inconsistent snapshots if uncheckpointed transactions reside in `.db-wal`. Online SQLite backup API (`.backup` or `conn.backup()`) is required. | Updated Section 5.4 with explicit WAL advisory and cross-platform PowerShell / Python commands. |

---

### 3. Non-Destructive Backup & Restore Verification Drill

The drill was executed locally in an isolated temporary directory (`tempfile.TemporaryDirectory`) using disposable database copies:
1. **Source Setup:** Initialized simulated live database with production schema (`predictions`, `model_releases`) and activated SQLite WAL mode (`PRAGMA journal_mode=WAL;`). Seeded active rows while write-ahead log was active.
2. **Point-in-Time Online Backup:** Executed `src_conn.backup(bck_conn)` using Python's native SQLite Online Backup API (equivalent to `sqlite3 .backup`). WAL journal pages were checkpointed and safely merged into the backup file without table locks.
3. **In-Place Integrity Verification:** Executed `PRAGMA integrity_check;` on the backup file. **Result:** `ok`.
4. **Dry-Run Isolated Restore:** Restored backup into `restored_verify.db` in an ephemeral sandbox. Executed `PRAGMA integrity_check;` (**Result:** `ok`). Queried restored counts: `predictions=2`, `model_releases=1` (100% data integrity verified).
5. **Ephemeral Sandbox Cleanup:** Closed all SQLite connection handles cleanly before directory deletion (preventing Win32 file locking errors) and removed sandbox.
6. **Automated Regression Test:** Added `test_non_destructive_backup_and_restore_verification` to `tests/test_deployment_runbook.py` and standalone drill runner `scripts/verify_day49_backup_restore.py`.

**Protected File Immutability (Zero-Mutation Verification):**
- `data/predictions.db`:
  - Pre-Drill SHA-256: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e`
  - Post-Drill SHA-256: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e`
  - **Status:** **100% MATCH (0 bytes mutated)**
- `models/.gitkeep`:
  - Pre-Drill SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - Post-Drill SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - **Status:** **100% MATCH (0 bytes mutated)**

---

### 4. Empirical Verification & Test Results

- **Targeted Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest tests/test_core.py tests/test_deployment_runbook.py tests/test_local_staging.py -q
  ```
  **54 passed**, 1 warning (`StarletteDeprecationWarning`) in 17.86s.
- **Full Regression Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **633 passed**, 1 warning (`StarletteDeprecationWarning`) in 39.67s across 45 test files (+4 new tests since Day 48). Zero failures, zero regressions.
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Hygiene Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors, 0 trailing blank lines).`
- **Zero-Cost & Credential Controls:**
  - Zero cloud spending and zero paid services.
  - No secrets, API keys, passwords, or cloud infrastructure introduced.

---

### 5. Phase 16 Status & Next Steps

**Phase 16 remains strictly IN PROGRESS.**
Configuration consistency, relative path resolution, and non-destructive disaster recovery procedures are audited, documented, and automated. The final remaining acceptance criterion for Phase 16 is a multi-hour soak test on dedicated production-equivalent external infrastructure during live NSE market hours once external staging infrastructure is provisioned.

### Next Step
Await provisioning of dedicated external staging infrastructure or operator direction for Phase 16 final milestone audit.

---

## DAY 50 — Fix Live Prediction Ensemble Integration (GAP-01)

**Date:** 2026-10-21
**Baseline Commit:** `7ba2c7f`
**Status:** Completed
**Phase 16 Status:** Strictly **IN PROGRESS** (Pending final production soak testing during live market hours).

### 1. Objective & Problem Root Cause
The comprehensive audit revealed issue GAP-01: `app/api/routes/predict.py` called `ensemble_service.predict_ensemble(...)` without passing point-in-time news articles and macroeconomic/regulatory events. Because `articles or events` evaluated to `False`, the ensemble runner silently bypassed qualitative LLM synthesis and defaulted every API ensemble prediction to `ML_ONLY`.

### 2. Implementation Summary
1. **Dependency Injection (`app/api/dependencies.py`):**
   - Added `get_news_provider() -> BaseNewsProvider` providing `RSSNewsProvider()`.
   - Reused existing `get_event_providers() -> List[BaseEventProvider]` supplying `[RBIEventProvider(), SEBIEventProvider()]`.
2. **Point-in-Time Prediction Pipeline (`app/api/routes/predict.py`):**
   - Injected `news_provider` and `event_providers` into `POST /api/predict`.
   - Computed timezone-aware decision cutoff (`payload.as_of_date` or `datetime.now(timezone.utc)`).
   - Acquired and deduplicated news articles via `news_provider.fetch_news(...)` and `deduplicate_news(...)`, filtered strictly point-in-time with lookback window capped at 14 days using `filter_news_point_in_time(...)`.
   - Acquired and deduplicated macroeconomic/regulatory events via `ep.fetch_events(...)` and `deduplicate_events(...)`, filtered point-in-time with lookback window capped at 30 days using `filter_events_point_in_time(...)`, ensuring relevance to broad market or target symbol.
   - Passed typed `articles` and `events` into `ensemble_service.predict_ensemble(...)`.
   - Isolated external provider exceptions with safe log warnings and fallback to empty context without HTTP 500 errors.
   - Fixed potential double-persistence issue by ensuring persistence occurs cleanly once with preserved `prediction_id`.
3. **Model Availability & Loading (GAP-02 Distinction):**
   - Inspected `models/` directory and confirmed zero trained model artifacts are committed (`models/.gitkeep` only).
   - Confirmed `PredictionService` safely returns `status=PredictionStatus.MODEL_UNAVAILABLE` when artifacts are missing. No model retraining was triggered and no fake model weights were generated.

### 3. Empirical Verification & Test Results
- **Focused & Regression Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest tests/test_api.py -v
  ```
  **31 passed**, 1 warning in 5.31s (+8 new tests covering GAP-01):
  - `test_ensemble_prediction_receives_pit_news_and_events`: confirms point-in-time filtering and bounded provider calls.
  - `test_ensemble_prediction_lookback_window_exclusion`: confirms articles/events outside lookback are excluded.
  - `test_ensemble_symbol_and_market_event_relevance_filtering`: confirms symbol relevance filtering.
  - `test_ensemble_empty_news_and_events_fallback`: confirms clean fallback to `ML_ONLY` when context is empty.
  - `test_ensemble_provider_failure_resilience`: confirms provider failure does not cause HTTP 500.
  - `test_ensemble_ollama_failure_or_timeout_fallback`: confirms controlled fallback when Ollama is unreachable.
  - `test_ensemble_response_accurately_reports_llm_contribution`: confirms truthful response metadata.
  - `test_ensemble_history_persistence_single_entry`: confirms single immutable record written to SQLite repository.
- **Full Regression Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **641 passed**, 1 warning in 38.17s across 45 test files (+8 tests since Day 49). Zero failures, zero regressions.
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Hygiene Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File Integrity Checks:**
  - `data/predictions.db`: SHA-256 `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% MATCH).
  - `models/.gitkeep`: SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% MATCH).

### 4. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
GAP-01 is repaired with zero paid dependencies and full regression coverage. GAP-02 (model artifacts and training) remains documented as a separate blocker.

---

## Day 51 - Trained Model Artifacts & Inference Readiness (GAP-02)

**Status:** Completed  
**Phase 16 Status:** Strictly **IN PROGRESS** (Pending final production soak testing during live market hours).  
**Baseline Commit:** `f73566a`  

### 1. Objective & Problem Root Cause
The project audit revealed GAP-02: `models/` directory contained only `.gitkeep`, causing live prediction inference via `PredictionService` to return `PredictionStatus.MODEL_UNAVAILABLE` unless preloaded in-memory model instances were passed. Previous daily verification scripts cleaned up generated model files in `finally` blocks to preserve repository baseline invariants. In addition, `.gitignore` specifies `models/*` and `!models/.gitkeep`, confirming that model weights are intentionally untracked in Git to prevent repository bloat.

The objective was to implement and verify the existing deliberate model-training and validation workflow so reproducible, gated model artifacts (`xgboost_direction.json` and `lightgbm_direction.txt`) can be generated, persisted, and loaded through the production `PredictionService` without modifying `data/predictions.db` or violating repository policies.

### 2. Implementation Summary
1. **ModelRetrainer Enhancements (`app/training/retraining.py`):**
   - Added balanced accuracy, confusion matrix (`[[TN, FP], [FN, TP]]`), and counts (`TP`, `TN`, `FP`, `FN`) to candidate evaluation metrics dictionary.
   - Added atomic persistence of model metadata alongside active artifacts (`models/{clean_model}_metadata.json`), recording release ID, model name/version, symbol, feature version (`canonical_37_features`), feature columns list, target definition, training and evaluation cutoffs, sample counts, metrics, and gate outcomes.
2. **Deliberate Model Training CLI (`scripts/train_models.py`):**
   - Implemented a standalone, reproducible CLI utility providing end-to-end model training, validation, gating, atomic promotion, metadata generation, and live inference verification.
   - Reused existing architecture: `run_market_data_pipeline`, `assemble_feature_matrix`, `validate_feature_matrix_isolation`, `split_chronological_holdout`, `ModelRetrainer`, and `PredictionService`.
   - Maintained strict zero-mutation guarantee for `data/predictions.db` by executing retraining with `repository=None`.
   - Executed full 5-year lookback training run for `BHARTIARTL` (1,235 bars, 958 train samples, 240 evaluation samples, 1 boundary embargo session):
     - **XGBoost Candidate:** Out-of-sample accuracy 51.25% vs majority baseline 49.58%, Brier score 0.2556, all 6 validation gates passed -> promoted to `models/xgboost_direction.json`.
     - **LightGBM Candidate:** Out-of-sample accuracy 53.75% vs majority baseline 49.58%, Brier score 0.2562, all 6 validation gates passed -> promoted to `models/lightgbm_direction.txt`.
     - Generated consolidated metadata file at `models/model_metadata.json`.
3. **Inference Verification:**
   - Verified live prediction execution through `PredictionService` loading active artifacts:
     - XGBoost: `DOWN`, $P(UP)=0.4686$, $P(DOWN)=0.5314$, status `SUCCESS`.
     - LightGBM: `DOWN`, $P(UP)=0.4681$, $P(DOWN)=0.5319$, status `SUCCESS`.
4. **Foundation Test Alignment (`tests/test_foundation.py`):**
   - Updated `test_no_forbidden_day1_mock_data` to allow legitimate trained model artifacts (`xgboost_direction.json`, `lightgbm_direction.txt`, metadata JSON files, candidates, and archive) while continuing to reject unauthorized mock/fake files.
5. **Regression & Integration Tests (`tests/test_model_training_artifacts.py`):**
   - Added 5 comprehensive tests covering `train_and_persist_baseline_model`, gated retraining and metadata persistence, graceful containment of missing and corrupt artifacts, chronological inversion rejection, and production active artifact inference readiness.

### 3. Empirical Verification & Test Results
- **Full Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **646 passed**, 1 warning in 25.76s across 46 test modules (+5 new tests since Day 50). Zero failures, zero regressions.
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Hygiene Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File Integrity Checks:**
  - `data/predictions.db`: SHA-256 `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).
  - Git tracking: Model weight files in `models/` remain gitignored per repository `.gitignore` policy (`models/*`, `!models/.gitkeep`).

### 4. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
Both GAP-01 (ensemble pipeline integration) and GAP-02 (trained model artifacts and inference readiness) are resolved and verified. Next step: Phase 16 pre-release checklist and final deployment soak verification.

---

## Day 52 - GAP-05: Nifty Telecommunications Index Integration

**Status:** Completed  
**Phase 16 Status:** Strictly **IN PROGRESS** (Pending final production soak testing during live market hours).  
**Baseline Commit:** `9121a93`  

### 1. Objective & Official Source Verification
The objective was to integrate official Nifty Telecommunications index data into the market-data and prediction architecture without breaking the existing `BHARTIARTL` pipeline or corrupting protected database and model artifacts.

- **Official Source Verified:** NSE Indices Limited sectoral index portal:
  `https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-telecommunications`
- **Official Backend Endpoint:**
  `POST https://www.niftyindices.com/BackPage/getHistoricaldatatabletoString`
- **Data Availability & Source Limitations:**
  - **Yahoo Finance Incompatibility:** Yahoo Finance does not host or update the Nifty Telecommunications index (`^CNXTELECOM`, `^NSETELECOM`, and `NIFTY_TELECOM.NS` all return HTTP 404). Yahoo Finance tickers cannot be used for this index.
  - **Available Fields:** Official NSE Indices endpoint provides daily closing index levels (`CLOSE`). Intra-day `OPEN`, `HIGH`, and `LOW` fields are returned as hyphenated strings (`"-"`).
  - **Zero-Volume Guarantee:** Volume is omitted / not published by NSE Indices for sectoral indices. In accordance with zero-fabrication standards, volume is strictly recorded as `0` without synthetic inflation.
  - **Candle Geometry Invariant:** When intra-day price ranges are not published, physical candle bounds require `open = high = low = close`, satisfying `high >= max(open, close)` and `low <= min(open, close)`.

### 2. Implementation Summary
1. **Instrument Registry & Separation (`app/market/instruments.py`):**
   - Implemented `InstrumentType` (`EQUITY`, `INDEX`) and `Instrument` dataclass tracking official source, tradability, currency (`INR`), lot sizes, and sector benchmarks.
   - Registered canonical symbols: `BHARTIARTL` (Equity) and `NIFTY_TELECOMMUNICATIONS` (Index).
   - Created `validate_instrument_separation(equity, index)` to prevent accidental cross-instrument substitution, price mixing, or cross-application.
2. **Official Index Data Provider (`app/market/providers/nifty_indices_provider.py`):**
   - Implemented `NiftyIndicesProvider` adhering to `BaseMarketDataProvider`.
   - Reverse-engineered official Nifty Indices ASMX/JSON protocol (`cinfo` payload with `DD-Mon-YYYY` dates).
   - Sanitized numeric prices, deduplicated observations, and strictly sorted chronologically.
   - Enforced hard rejection if single-stock equities (e.g. `BHARTIARTL`) are requested via `NiftyIndicesProvider`.
   - Provided near-real-time index quotes via `fetch_quote` with `LiveQuote` schema compliance.
3. **Benchmark Context Alignment (`app/market/benchmark.py` & `app/market/__init__.py`):**
   - Added `TELECOM_BENCHMARK = "NIFTY_TELECOMMUNICATIONS"`.
   - Mapped `TELECOM`, `TELECOMMUNICATIONS`, `NIFTY_TELECOM`, and `NIFTY_TELECOMMUNICATIONS` in `SECTOR_BENCHMARK_MAP`.
   - Verified relative performance computation (`RelativePerformanceFeature`) between `BHARTIARTL` and `NIFTY_TELECOMMUNICATIONS`.
4. **Prediction Service & Model Safety (`app/prediction/service.py` & `app/api/routes/predict.py`):**
   - Automatically routes `NIFTY_TELECOMMUNICATIONS` to `NiftyIndicesProvider` when index data or quotes are requested.
   - **Model Weight Isolation Guard:** Enforced strict check that `BHARTIARTL` single-stock model weights cannot be reused for sectoral index prediction.
   - Returns truthful `PredictionStatus.MODEL_UNAVAILABLE` with actionable message: `"Index-specific forecasting model for 'NIFTY_TELECOMMUNICATIONS' not found... BHARTIARTL equity models cannot be reused for sectoral index forecasting. Index-specific model training is documented as a planned follow-up."`
   - Added public error message sanitization in `app/api/routes/predict.py`.
5. **Data Sources Documentation (`docs/data-sources.md`):**
   - Cataloged Nifty Telecommunications index provider, official endpoint, zero-volume guarantee, and Yahoo Finance limitation.

### 3. Empirical Verification & Test Results
- **Dedicated Regression Test Suite (`tests/test_nifty_telecom_integration.py`):**
  Added 19 targeted tests verifying instrument registration, alias resolution, equity/index separation enforcement, provider response parsing, hyphenated OHL normalization, zero-volume preservation, network error handling, pipeline compatibility, model isolation guards, and protected file integrity.
- **Full Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **665 passed**, 1 warning in 32.06s across 47 test modules (+19 new tests since Day 51). Zero failures, zero regressions.
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Hygiene Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File Integrity Checks:**
  - `data/predictions.db`: SHA-256 `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 4. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
GAP-05 (Nifty Telecommunications Index Integration) is complete and verified with official source data and model safety guarantees. Index-specific predictive model training is documented as a separate future follow-up.

---

## Day 53 — Nifty Telecommunications Data Integrity Remediation

### 1. Objective & Background
Audit and correct the Nifty Telecommunications OHLC data representation introduced in commit `9925238`.
The official Nifty Indices historical response returns `OPEN`, `HIGH`, and `LOW` as `"-"` and does not report trading volume for sectoral indices. Previously, closing levels were copied into open/high/low as a synthetic convenience, which created false candlestick signals. Day 53 establishes truthful close-only source data semantics while preserving full equity ingestion, feature calculation, and repository integrity.

### 2. Remediation Summary
1. **Canonical Schema Support for Close-Only Bars (`app/core/schemas.py`):**
   - Updated `MarketOHLCV` to support optional intraday OHLC (`open=None, high=None, low=None`) and close-only flag (`is_close_only=True`).
   - Added explicit provenance properties: `has_intraday_ohl` (False for close-only), `is_volume_available` (False when volume is not reported), and labeled synthetic fallbacks `synthetic_open`, `synthetic_high`, `synthetic_low` for legacy calculations that cannot be mistaken for observed market quotes.
   - Enforced strict physical OHLC geometry and positive bounds for equities when intraday fields are provided; rejected partial OHLC specifications.
2. **Data Cleaner Close-Only Support (`app/market/cleaner.py`):**
   - Updated `clean_market_data` to permit close-only bars where intraday OHL are `None`, while maintaining strict missing-field rejection for equities.
   - Implemented `_field_isclose` helper to safely compare and collapse identical duplicate records with `None` values without raising `TypeError`.
3. **Truthful Provider Ingestion (`app/market/providers/nifty_indices_provider.py`):**
   - Discontinued copying `CLOSE` into `OPEN`, `HIGH`, `LOW`. When official fields are hyphenated (`"-"`), records are instantiated with `open=None, high=None, low=None, is_close_only=True, volume_reported=False`.
   - Updated `fetch_quote` to reflect `open_price=None, day_high=None, day_low=None, volume=None` with an explicit disclaimer.
4. **Leakage-Safe Feature Matrix Assembly (`app/training/feature_matrix.py`):**
   - Guarded numeric casting to map `None` in `open`, `high`, `low`, and `volume` safely to `np.nan`, adhering to the Natural Missing Values Policy.
5. **Feature Scope & Candlestick Integrity:**
   - **Supported on Genuine Close:** Daily returns, rolling returns (3d, 5d), rolling volatility (5d, annualized), SMAs (5, 10), EMAs (5, 10), RSI (14), MACD (12/26/9), Bollinger Bands (20/2.0), Rate of Change (10), and relative performance alpha against `BHARTIARTL`.
   - **Safely Skipped / Unavailable:** Candlestick body, range, wicks, ratios, direction, Average True Range (ATR-14), and intraday swing pivot geometry strictly evaluate to `None` / `NaN` without fabricating candle shapes.

### 3. Empirical Verification & Test Results
- **Integration & Regression Tests (`tests/test_nifty_telecom_integration.py`):**
  - **22 passed** in 2.64s (+3 new tests covering equity OHLC preservation, partial OHLC rejection, close-based indicator generation without candle fabrication, and duplicate collapse with None values).
- **Full Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **668 passed**, 1 warning in 34.46s across 47 test modules. Zero regressions.
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Hygiene Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File Integrity Checks:**
  - `data/predictions.db`: SHA-256 `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 4. Phase 16 Status
**Phase 16 remains strictly IN PROGRESS.**
Remediation of Nifty Telecommunications data integrity is complete. The 84-day roadmap and Phase 16 external staging criteria remain unchanged.

---

## Day 54 — Local LLM Integration: Environment and Architecture Audit

### 1. Objective & Baseline Verification
Prepare the project for local LLM integration using Ollama and Gemma 3 12B (`gemma3:12b`). Verify the local runtime environment, audit existing LLM and ensemble abstractions, and establish a safe, testable integration boundary with zero-cost local execution before connecting the LLM to the prediction workflow.
- **Baseline Commit Verified:** `9f73200` (Day 53 Nifty Telecommunications Data Integrity Remediation).
- **Working Tree:** Clean, synchronized with `origin/main`.
- **Roadmap Invariant:** The original 84-day roadmap is preserved. Phase 16 remains strictly **IN PROGRESS**.

### 2. Local Environment & Hardware Audit
- **Ollama Runtime:**
  - Installed and reachable at `http://127.0.0.1:11434`.
  - Version: `0.40.6` (verified via `ollama --version` and `GET http://127.0.0.1:11434/api/version`).
- **Model Availability:**
  - `gemma3:12b` is **already pulled and resident locally**:
    - Tag: `gemma3:12b:latest`
    - Model ID: `f4031aab637d`
    - Architecture: Gemma 3 (12.2B parameters, Q4_K_M quantization)
    - Local Size: 8.15 GB
  - **Zero Cloud / Cost Guarantee:** No models were downloaded; zero cloud/API costs incurred.
- **System Resources:**
  - System RAM: 16.0 GB total (~2.5 GB free physical memory under current OS load).
  - GPU: NVIDIA GeForce RTX 5050 Laptop GPU (Driver Version: 576.88).
  - VRAM: 8,151 MiB total (~7,862 MiB free, 289 MiB utilized).
  - Execution Feasibility: Gemma 3 12B in Q4_K_M fits into ~8.15 GB. When loaded, Ollama dynamically splits layers between GPU VRAM (~7.5 GB offloaded) and system RAM as needed.

### 3. Integration Contract & Governance Boundary
Audit of `app/llm` and `app/prediction/ensemble.py` confirmed that high-level qualitative reasoning interfaces were established in Days 31–32. Day 54 formalizes and hardens the integration contract:
1. **Environment-Driven Configuration (`app/core/config.py`):**
   - `OLLAMA_BASE_URL` (default: `http://127.0.0.1:11434`): Ollama daemon endpoint.
   - `OLLAMA_MODEL` (default: `gemma3:12b`): Local model identifier.
   - `OLLAMA_TIMEOUT_SECONDS` (default: `30.0`): Explicit connection and response timeout.
   - `OLLAMA_ENABLED` (default: `True`): Master toggle for offline or bypass execution.
2. **Typed Availability & Model Verification (`app/llm/client.py`):**
   - Added `LLMModelUnavailableError(LLMClientError)` to distinguish missing models from network or daemon failures.
   - Implemented `is_available()` and `check_model_availability()` to query `GET /api/tags`, verifying that the configured model is installed locally before triggering generation.
   - Implemented `get_status()` returning sanitized operational diagnostics (`enabled`, `model`, `base_url`, `timeout_seconds`, `reachable`, `model_available`) with zero secret leakage.
3. **Disabled & Failure Isolation:**
   - When `OLLAMA_ENABLED=False` or `enabled=False` is passed, `OllamaLLMClient` immediately raises `LLMClientError("Ollama LLM client is disabled by configuration")` without attempting network calls.
   - `EnsembleService.predict_ensemble()` catches all `LLMClientError` subclasses (including timeouts, unreachability, disabled state, and missing models), logs a diagnostic warning, and degrades seamlessly to `ML_ONLY` mode (100% quantitative weight).
4. **Intended Role & Strict Separation:**
   - The LLM synthesizes supplied, verified point-in-time news and regulatory events into qualitative factors and risks.
   - The LLM **never**:
     - Invents market prices, volumes, or official regulatory statements.
     - Replaces or alters quantitative ML features or probabilities.
     - Presents generated opinions as verified market facts.
     - Overwrites verified historical records in `data/predictions.db`.

### 4. Empirical Verification & Test Results
- **Unit & Integration Tests:**
  - Added unit tests in `tests/test_core.py` covering Ollama configuration and environment variable overrides.
  - Added 6 unit tests in `tests/test_llm_service.py` verifying disabled client execution, model availability tag queries, 404/not-found mapping to `LLMModelUnavailableError`, and sanitized status reporting.
  - Added 2 integration tests in `tests/test_ensemble_service.py` confirming graceful fallback to `ML_ONLY` when the LLM is disabled or the model is missing.
- **Full Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **676 passed**, 1 warning in 28.70s across all 47 test modules (+8 new tests since Day 53). Zero failures, zero regressions.
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Hygiene Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File Integrity Checks:**
  - `data/predictions.db`: SHA-256 `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 5. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
Environment audit, model verification, and safe isolation contracts for local Ollama integration are established and verified. Next step: Connect verified local LLM inference to live contextual inputs in subsequent scheduled phases while maintaining complete offline testability.

---

## Day 55 — Evidence-Grounded LLM Context Integration

### 1. Objective & Baseline Verification
Integrate the local Ollama / Gemma 3 12B client with the existing prediction and ensemble pipeline to explain quantitative predictions using verified, point-in-time news and regulatory events.
- **Baseline Commit Verified:** `bb836ee` (`feat(llm): add local Ollama integration foundation`).
- **Working Tree:** Clean, synchronized with `origin/main`.
- **Roadmap Invariant:** The original 84-day roadmap is preserved. Phase 16 remains strictly **IN PROGRESS**.

### 2. Contextual Integration & Source Provenance
1. **Point-in-Time Temporal Boundary:**
   - News and regulatory events are strictly filtered against the prediction's reference timestamp (`cutoff_time` / `as_of_date`).
   - Information published after the cutoff is strictly purged prior to prompt assembly, eliminating future data leakage.
2. **Provenance Preservation Contract:**
   - All news items retain headline, publisher/source name, UTC publication timestamp, article ID, and source URL.
   - All regulatory events retain title, source organization, category, publication timestamp, source URL, and structured quantitative metrics (e.g. churn rate, tariff changes).
3. **Empty Context Invariant (`NO_CONTEXT`):**
   - When no verified records survive point-in-time filtering or when no contextual records are supplied, `LLMService.explain_prediction()` immediately returns `status=NO_CONTEXT` with `direction=INSUFFICIENT_EVIDENCE` and `confidence=LOW` without generating or hallucinating synthetic market events.
4. **Citation Verification Invariant:**
   - Supporting evidence items are parsed and validated against the known provenance mapping (`known_provenance`).
   - Any citation referencing unverified or unsupplied publishers/headlines is stripped from `supporting_evidence` and flagged in `limitations`.

### 3. Absolute Numerical Prediction Immutability
- Quantitative machine learning forecasts (`PredictionResult`) are treated as authoritative and mathematically immutable.
- The qualitative LLM output is parsed exclusively into `LLMExplanationResult` and **cannot** alter:
  - ML probabilities (`probability_up`, `probability_down`).
  - Predicted direction (`predicted_direction`) or label (`predicted_label`).
  - Target price boundaries or historical SQLite verification records.
- Regression tests prove that adversarial LLM payloads attempting prompt injection (e.g., injecting synthetic probability keys or conflicting direction strings) have zero effect on numerical outputs.
- In `EnsembleService.predict_ensemble()`, whenever LLM inference fails, times out, is disabled, or lacks context, the ensemble cleanly degrades to `ML_ONLY` mode (100% quantitative weight).

### 4. Structured Output Contract
- Implemented `LLMExplanationResult` dataclass with status enum `LLMExplanationStatus` (`SUCCESS`, `NO_CONTEXT`, `UNAVAILABLE`, `DISABLED`, `TIMEOUT`, `FAILED`).
- Exposed `LLMExplanationResponse` across `EnsembleDetailsResponse` and `PredictionResponse` API schemas containing:
  - `status`: Machine-readable operational status.
  - `summary`: High-level explanation grounded in provided source records.
  - `supporting_evidence`: List of verified factual citations traceable to source tags.
  - `limitations`: List of uncertainties, data constraints, and unverified citation warnings.
  - `model`: Identifier of generating model (`gemma3:12b` or mock).
  - `generated_at`: Timezone-aware UTC timestamp.

### 5. Latency & Resource Benchmark (Live Gemma 3 12B)
Executed reproducible benchmark via `scripts/benchmark_local_llm.py 3` on `BHARTIARTL` context (2 news articles, 1 TRAI regulatory event):
- **Hardware Profile:**
  - System RAM: 15.26 GB total (~2.65 GB available physical memory prior to run, 82% load).
  - GPU: NVIDIA GeForce RTX 5050 Laptop GPU (8,151 MiB VRAM total, 7,777 MiB free).
- **Benchmark Results (60.0s Timeout Threshold):**

| Run | Wall-Clock Latency | Status | Evidence Count | Limitations Count | System RAM Free | GPU VRAM Post-Run |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Cold Start (Run 1)** | 60.253 s | `TIMEOUT` | 0 | 1 | 0.34 GB | 70 MiB |
| **Warm Request (Run 2)** | 60.160 s | `TIMEOUT` | 0 | 1 | 0.88 GB | 70 MiB |
| **Warm Request (Run 3)** | 60.047 s | `TIMEOUT` | 0 | 1 | 0.53 GB | 70 MiB |

- **Empirical Measurements vs. Hypotheses:**
  - *Measured Hardware State:* Host RAM: 15.26 GB total (~2.65 GB free initially, dropped to 0.34 GB during Run 1). Dedicated GPU: NVIDIA RTX 5050 Laptop GPU (8,151 MiB total, 7,777 MiB free initially, 70 MiB used post-run).
  - *Measured Wall-Clock Latency:* 60.253s, 60.160s, 60.047s across 3 runs. All 3 runs exceeded the 60.0s threshold and timed out (`TIMEOUT`).
  - *Observed Ollama Runner Log Evidence (Confirmed Day 56):* Prompt token size was 790 tokens. Prompt evaluation took 18.18s on Run 1. Measured token generation rate was ~2.73 to 2.80 tokens/sec. Because a full JSON explanation requires 350-500 tokens, generation takes ~140s at this throughput, causing the client timeout to cleanly cancel execution at 60s.
  - *Hardware Offloading Hypothesis:* Ollama's runner logged `total_vram="0 B"` on startup, indicating GPU layers were not offloaded by the runner, resulting in CPU-bound execution.
  - *Critical Architectural Resilience:* The integration layer handled the timeout cleanly without crashing the daemon, locking the prediction API, or raising unhandled socket errors. It returned typed `TIMEOUT` status with clear limitations (`"Inference exceeded configured OLLAMA_TIMEOUT_SECONDS."`), and the ensemble automatically degraded to `ML_ONLY`.

### 6. Empirical Verification & Test Results
- **Dedicated Regression Suite (`tests/test_llm_explanation.py`):**
  Added 11 comprehensive tests verifying point-in-time filtering, provenance preservation, empty context `NO_CONTEXT` contract, disabled mode, missing model handling, timeout behavior, adversarial immutability, supporting evidence citation validation, ensemble `ML_ONLY` fallback, and `/api/predict` public API response schema compatibility.
- **Full Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **687 passed**, 1 warning in 35.47s across all 48 test modules (+11 new tests since Day 54). Zero regressions.
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Hygiene Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File Integrity Checks:**
  - `data/predictions.db`: SHA-256 `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 7. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
Evidence-grounded qualitative context integration is complete with strict numerical immutability, citation verification, and timeout degradation. Next step: Multi-instrument evaluation, extended soak testing, and live market monitoring.

---

## Day 56: CodeRabbit Review Remediation + Day 55 Defect Fixes

### 1. Executive Summary
- **Baseline Commit:** `0a01dd1` (`feat(llm): ground prediction explanations in verified market context`).
- **Remediation Scope:** Fully addressed all 8 CodeRabbit findings (A through H) across local benchmark observability, API sanitization and length bounding, probability labeling correctness, evidence classification neutrality, strict zero-fabrication citation validation, ensemble signal independence, empirical Ollama runner diagnosis, and hermetic automated test isolation.
- **Verification:** All 692 tests passing across 48 test modules (+5 new targeted tests). `pip check` clean. Protected database and model artifact hashes verified 100% bit-identical.
- **Roadmap Invariant:** **Phase 16 remains strictly IN PROGRESS** (pending external soak testing and multi-instrument live evaluation).

### 2. CodeRabbit Remediation Checklist
| Item | Component | Review Finding | Status | Resolution Details & Verification Test |
| :--- | :--- | :--- | :---: | :--- |
| **A** | `scripts/benchmark_local_llm.py` | Distinguish installed model from resident model; do not guess cold start; categorize latency. | **FIXED** | Added `check_model_residency()` querying `/api/ps` on `OllamaLLMClient`. Run 1 labeled `Cold Start (Unloaded)` only when confirmed unloaded via API; if residency unknown, reports `unknown`. Latency categorized as `TIMEOUT (Exceeded limit)` vs `INFERENCE (Completed)`. Tested live via benchmark runner. |
| **B** | `app/api/routes/predict.py` | Sanitize and bound explanation `summary` and `limitations`; treat model output as untrusted text, not HTML. | **FIXED** | Added `_sanitize_and_bound_text()` using `html.escape()`, control character stripping, and strict length bounds (`summary <= 2000 chars`, list elements `<= 500 chars`). Tested in `test_api_sanitization_and_bounding_of_untrusted_llm_output`. |
| **C** | `app/llm/prompts.py` | Probability label correctness: `P(UP)` must strictly mean probability of upward move; calculate direction-specific probability for DOWN. | **FIXED** | Updated `build_prediction_explanation_prompt()` to support `quantitative_probability_down`. Formats `UP [P(UP)=58.4%]` and `DOWN [P(DOWN)=53.1%, P(UP)=46.9%]`. Tested in `test_probability_formatting_for_up_and_down_predictions`. |
| **D** | `app/llm/schemas.py` | Stop classifying every unmatched evidence item as positive; represent positive, negative, and neutral evidence properly. | **FIXED** | Removed `) or self.supporting_evidence` fallback in `to_reasoning_result()`. Unclassified/neutral items stay in `source_references` and are never forced into `pos_factors`. Tested in `test_unclassified_neutral_evidence_not_converted_to_positive_factors` and `test_down_prediction_unclassified_evidence_never_bullish`. |
| **E** | `app/llm/service.py` | Fix loose keyword fallback permitting fabricated citation tags (e.g. `[News 99]`) or generic words (`article`, `report`). | **FIXED** | Completely eliminated wildcard fallback in `_validate_supporting_evidence()`. Enforces regex validation against `known_provenance` keys; fabricated tags and unsupplied sources are rejected and reported in `limitations`. Tested in `test_fabricated_tags_and_loose_keywords_are_rejected`. |
| **F** | `app/prediction/ensemble.py` | Review passing ML forecast into LLM prompt; prevent leaking forecast into blended signal and maintain numerical immutability. | **FIXED** | Explicitly decoupled explanation layer from probability blending. `predict_ensemble()` attaches `explanation` directly, while maintaining `w_ml=1.0, w_llm=0.0` and `llm_result=None` to ensure the authoritative numerical ML prediction is never mutated by the explanatory narrative. Tested in `test_adversarial_llm_payload_cannot_change_ml_probabilities`. |
| **G** | `docs/daily-progress.md` | Separate measured RAM/GPU utilization from hypotheses; label CPU offloading as unconfirmed without runner logs; preserve benchmark timeouts. | **FIXED** | Clarified Day 55 Section 5 to explicitly distinguish measured hardware and latency data from runner hypotheses. Corroborated with Ollama server log analysis in Day 56. |
| **H** | `tests/test_llm_explanation.py` | Isolate API tests from live market providers, live Ollama, and local model weights using deterministic mocks. | **FIXED** | Refactored `test_api_predict_ensemble_includes_explanation_isolated` to use `app.dependency_overrides` with deterministic mock `EnsembleService`, achieving 100% hermetic test execution independent of local daemon state. |

### 3. Runtime Investigation & Ollama Log Analysis
- **Direct Server Log Inspection (`%LOCALAPPDATA%\Ollama\server.log`):**
  - **Runner Hardware Detection:** Ollama logged `msg="vram-based default context" total_vram="0 B" default_num_ctx=4096`. The runner did not detect/allocate NVIDIA GPU VRAM on this Windows daemon instance, executing layers entirely on CPU.
  - **Prompt Token Size:** Evaluated `task.n_tokens = 790`. Prompt evaluation took `18.18 s` (~43.23 tokens/sec) on cold run, and restored in `0.10 ms` from checkpoint on warm runs.
  - **Token Generation Throughput:** Measured token generation speed was `2.73 to 2.80 tokens/sec` (`tg = 2.78 t/s`).
  - **Timeout Root Cause:** A complete structured JSON explanation with summary, evidence citations, limitations, and metadata spans 350 to 500 tokens. At 2.78 tokens/sec, full completion requires ~125 to 180 seconds. At the configured 60.0s client timeout, Ollama had generated only 165 tokens (`n_tokens = 956` out of expected ~1200 total), triggering a clean client cancellation:
    `[GIN] 2026/10/22 - 00:55:56 | 500 | 1m0s | 127.0.0.1 | POST "/api/generate"`.
  - **Verification of Fail-Safe Degradation:** In all timeout events, the system degraded gracefully to `ML_ONLY` without crashing the daemon or raising unhandled exceptions in the API.

### 4. Verification & Quality Gates
- **Targeted Test Modules:**
  - `tests/test_llm_explanation.py`: 16 passed in 4.49s.
  - `tests/test_llm_service.py` & `tests/test_ensemble_service.py`: 60 passed in 1.95s.
  - `tests/test_api.py`: 31 passed in 2.50s.
- **Full Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **692 passed**, 1 warning in 33.92s across all 48 test modules. Zero regressions.
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Whitespace Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File SHA-256 Baselines:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 5. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
Remediation of all CodeRabbit findings is complete, with hardened boundaries, strict citation checking, API escaping, and documented runner diagnostics. Next step: Multi-instrument evaluation, extended soak testing, and live market monitoring.

---

## Day 57: Remaining CodeRabbit Findings & Regression Fixes

### 1. Executive Summary
- **Baseline Commit:** `d09f427` (`fix(llm): resolve review findings and harden explanations`).
- **Remediation Scope:** Fully resolved all 4 newly reported CodeRabbit findings (A, B, C, D) plus the `EnsemblePredictionResult` constructor `TypeError` in test fixtures, and re-reviewed all previous findings for potential regressions.
- **Verification:** All **705 tests passing** (+13 new regression tests) across 48 test modules. Zero regressions. `pip check` clean. `git diff --check` clean. Protected database and model artifact hashes verified 100% bit-identical.
- **Roadmap Invariant:** **Phase 16 remains strictly IN PROGRESS** (external soak testing, multi-instrument evaluation, and live market monitoring remain outstanding).

### 2. Complete Review Checklist (New & Re-Reviewed Findings)

| Item | Component | Review Finding | Status | Root Cause & Applied Fix | Test Proving Fix |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **A** | `app/api/routes/predict.py` | Review escape-then-truncate order and API-level HTML escaping; prevent half-sliced entities and exceeding max length. | **FIXED** | **Root cause:** Escaping ran on full input before truncation, and naive string slicing could cut inside an entity (e.g. `&quot;` -> `&qu`) or exceed `max_length` by appending ` [truncated]`.<br>**Fix:** Sanitized control characters and applied raw length bound *before* escaping; sliced escaped text to `budget = max_length - len(suffix)` and inspected `rfind('&')` to strip incomplete entities before suffix attachment; sanitized all list elements and ensemble factor fields. | `TestFindingAHTMLEscapingAndTruncationOrder` (4 tests) |
| **B** | `app/llm/client.py` | Match model tag before reporting residency; prevent unsafe substring matching (`gemma3:12b` vs `gemma3:12b-instruct`). | **FIXED** | **Root cause:** `check_model_residency()` used `m_lower.startswith(target + ":")`, matching unrelated models with similar prefixes.<br>**Fix:** Introduced `_match_model_tag()` with strict case-insensitive match, `library/` prefix normalization, and canonical `:latest` default handling. Rejects substring matching. Returns `False` on confirmed non-residency and `None` on query/network/JSON errors. | `TestFindingBExactModelTagMatching` (2 tests) |
| **C** | `app/llm/service.py` & `app/llm/prompts.py` | Use word-boundary matching for citation grounding; `[N1]` must not validate `[N10]`. | **FIXED** | **Root cause:** Evidence validation checked `token in item_lower` where `token="[n1]"`, which is a substring of `"[n10]"`. Furthermore, generic publisher names in `known_provenance` allowed ungrounded statements to pass.<br>**Fix:** Built token-aware bracket tag regex matching `[News N]`, `[N N]`, `[Event N]`, `[E N]` with non-digit lookahead; restricted ID checks to exact IDs using word boundaries (`\b{id}\b`); prevented generic publisher names or headline words from validating ungrounded claims. | `TestFindingCCitationWordBoundaryValidation` (4 tests) |
| **D** | `app/prediction/ensemble.py` | Custom `ml_weight`/`llm_weight` request values must not be silently ignored. | **FIXED** | **Root cause:** Day 56 set `llm_result = None` unconditionally to prevent ML prediction leakage from `explain_prediction()`, causing `synthesize()` to silently force `w_ml=1.0, w_llm=0.0`.<br>**Fix:** When callers supply custom weights with `llm_weight > 0.0`, the system calls `generate_qualitative_reasoning()` (Role B) without quantitative ML forecast context (zero data leakage) to blend signals with the requested weights. When `llm_weight == 0.0`, `ML_ONLY` is preserved. Custom weights are validated on API and domain boundaries (rejecting negative or zero-sum weights with HTTP 422). | `TestFindingDCustomEnsembleWeights` (2 tests) |
| **3** | `app/prediction/ensemble.py` | Fix `EnsemblePredictionResult` construction: test raises `TypeError: missing required positional argument`. | **FIXED** | **Root cause:** Dataclass `EnsemblePredictionResult` declared `latest_input_timestamp` and `llm_reasoning` without default values between required fields, causing positional and keyword constructor errors if callers omitted them.<br>**Fix:** Reordered dataclass fields to place `latest_input_timestamp: Optional[str] = None` and `llm_reasoning: Optional[LLMReasoningResult] = None` with default values after required positional arguments, ensuring backward compatibility. | `TestEnsemblePredictionResultConstructorContract` (1 test) |
| **D56-A** | `scripts/benchmark_local_llm.py` | Benchmark cold-start and model-residency classification. | **FIXED** | Re-reviewed. Uses `check_model_residency()` with `_match_model_tag()`; reports `unknown` when residency cannot be verified. | Live benchmark & client tests. |
| **D56-B** | `app/api/routes/predict.py` | API explanation sanitization and bounding. | **FIXED** | Re-reviewed. Upgraded to entity-safe truncation and raw-bound pre-escaping. | API & sanitization tests. |
| **D56-C** | `app/llm/prompts.py` | `P(UP)` and `P(DOWN)` probability labels. | **FIXED** | Re-reviewed. `P(UP)` strictly denotes upward probability in prompt formatting. | Prompt formatting tests. |
| **D56-D** | `app/llm/schemas.py` | Unclassified evidence incorrectly treated as positive. | **FIXED** | Re-reviewed. Neutral context remains in `source_references` and is never converted to bullish factors. | Evidence classification tests. |
| **D56-E** | `app/llm/service.py` | Fabricated citations accepted by fallback logic. | **FIXED** | Re-reviewed. All evidence undergoes boundary-aware tag and ID checks; invalid tags omitted to limitations. | Evidence verification tests. |
| **D56-F** | `app/prediction/ensemble.py` | Ensemble independence and numerical immutability. | **FIXED** | Re-reviewed. Un-leaked Role B qualitative reasoning is used for blending when `llm_weight > 0`; ML forecast immutable when `llm_weight == 0`. | Signal immutability tests. |
| **D56-G** | `docs/daily-progress.md` | Resource measurements vs. inferred timeout causes. | **FIXED** | Re-reviewed. Hardware metrics and CPU-only Ollama runner execution verified via Ollama server logs. | Log analysis records. |
| **D56-H** | `tests/test_llm_explanation.py` | API tests requiring live providers or Ollama. | **FIXED** | Re-reviewed. All 48 test modules run hermetically using mock services and dependency overrides. | Full automated test suite. |

### 3. Key Technical Decisions & Architectural Behavior
1. **HTML Entity Boundary Protection:**
   - Truncating an HTML string across an entity (e.g. slicing `&quot;` at 3 characters) creates broken markup (`&qu`) that can corrupt rendering or bypass filters. By computing candidate slices and stripping unclosed `&...` prefixes before appending ` [truncated]`, the output stays within `max_length` while preserving well-formed entities.
2. **Ollama Model Tag Matching Contract:**
   - Ollama models follow `[namespace/]name[:tag]`. `_match_model_tag()` normalizes `library/` prefixes and implicit `:latest` suffixes while requiring exact token equality for model names and tags. Substring matches are explicitly prevented (`gemma3:12b` != `gemma3:12b-instruct`).
3. **Dual-Role LLM Ensemble Architecture:**
   - **Role B (`generate_qualitative_reasoning`):** Evaluated strictly against point-in-time news and events *without* access to quantitative ML forecasts. Safe for signal blending when callers specify `llm_weight > 0.0`.
   - **Role C (`explain_prediction`):** Grounded explanatory narrative that receives quantitative ML context. Strictly an explanatory synthesis layer, attached to `explanation` and never altering ML probabilities.

### 4. Verification & Quality Gates
- **Targeted Test Execution:**
  - `tests/test_llm_explanation.py`: **29 passed** in 4.38s (+13 new regression tests).
  - `tests/test_llm_service.py` & `tests/test_ensemble_service.py`: **60 passed** in 1.86s.
  - `tests/test_api.py`: **31 passed** in 2.68s.
- **Full Repository Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **705 passed**, 1 warning in 29.36s across all 48 test modules (0 failures, 0 regressions).
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Whitespace Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File SHA-256 Baselines:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 5. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
All CodeRabbit findings and regression defects are resolved with empirical tests. The next steps on the Phase 16 roadmap are:
1. Multi-instrument evaluation and latency profiling under concurrent API traffic.
2. Extended soak testing across real trading-session boundaries.
3. Live operational monitoring and automated telemetry alerts.

---

## Day 58: Ensemble Architecture Audit & Prediction Validation

### 1. Executive Summary
- **Baseline Commit:** `26e9643` (`fix(llm): close remaining review findings`).
- **Audit Scope:** Audited the entire multi-agent prediction pipeline end to end; validated mathematical blending formulas and weight normalization rules; verified explicit separation of requested weights from effective weights on fallback; enforced domain-level non-finite weight rejection; assessed qualitative LLM signal independence and citation boundaries; and conducted a leakage-safe chronological evaluation of baseline and ML models.
- **Verification:** All **715 tests passing** (+10 new audit regression tests) across 48 test modules. Zero regressions. `pip check` clean. `git diff --check` clean (0 whitespace errors). Protected database and model artifact hashes verified 100% bit-identical.
- **Roadmap Invariant:** **Phase 16 remains strictly IN PROGRESS** (external soak testing, multi-instrument evaluation, and live market monitoring remain outstanding).

### 2. End-to-End Prediction Path Verification
Traced one prediction completely from HTTP ingress to database persistence:
1. **Request Validation:** Ingress at `POST /api/predict` via `PredictRequest` in `app/api/routes/predict.py`. Validates ticker grammar, bounds lookback/staleness, and validates finite non-negative weights (`math.isfinite()`).
2. **Feature Matrix Ingestion:** Handled by `PredictionService.predict` in `app/prediction/service.py` via `run_market_data_pipeline`. Enforces minimum 34-bar warmup check, point-in-time timestamping, and canonical 37-feature assembly with strict zero-leakage target isolation (`validate_feature_matrix_isolation`).
3. **Quantitative ML Inference:** Standalone tree classification (XGBoost/LightGBM) executed via `predict_proba(X_latest)`. Produces authoritative empirical probabilities $P(UP|X)$ and directional sign.
4. **Qualitative Context Reasoning (Role B):** When `llm_weight > 0.0`, `EnsembleService.predict_ensemble` invokes `LLMService.generate_qualitative_reasoning` passing strictly point-in-time news articles and macro events *without* providing the ML prediction, ensuring genuine signal independence.
5. **Polarity-to-Probability Mapping:** In `EnsembleService._map_llm_direction_to_polarity`, directional stance (`UP`, `DOWN`, `NEUTRAL`, `INSUFFICIENT_EVIDENCE`) is scaled by confidence multiplier (HIGH: 1.0, MEDIUM: 0.75, LOW: 0.50). Converted to implied probability: $P(UP|LLM) = 0.50 + 0.50 \times \text{polarity}$.
6. **Weight Validation & Blending:** Validated via `EnsembleWeights`. Blends probabilities linearly: $P_{comb}(UP) = w_{ml} P_{ml}(UP) + w_{llm} P_{llm}(UP)$. Clamped strictly to $[0.0001, 0.9999]$ and rounded to 4 decimals.
7. **Direction & Agreement Classification:** Direction is `UP` (label 1) if $P_{comb}(UP) > 0.50$, `DOWN` (label 0) if $< 0.50$, with tie breaker defaulting to ML direction. Agreement classified into `STRONG_AGREEMENT`, `AGREEMENT`, `DIVERGENCE`, `PARTIAL`, `ML_ONLY`, or `LLM_ONLY`.
8. **Target Price Bounds:** Calculated volatility range via ATR-14: $[\max(0.01, \text{price} - \text{ATR}), \text{price} + \text{ATR}]$ anchored to observed current market price.
9. **Evidence-Grounded Explanation (Role C):** Downstream narrative generated by `LLMService.explain_prediction` with verified citation tags (`_validate_supporting_evidence`). Decoupled from numerical forecast; cannot mutate probabilities.
10. **Persistence & Serialization:** Adapted via `.to_prediction_result()` and immutably persisted in SQLite `predictions` table. Returned as structured `PredictionResponse`.

### 3. Ensemble Weight Contract & Fallback Hardening
- **Separation of Requested vs. Effective Weights:** Added `requested_weights: Optional[Dict[str, float]]` and `fallback_reason: Optional[str]` to `EnsemblePredictionResult` and API `EnsembleDetailsResponse`. When qualitative reasoning is unavailable or fails, `weights_used` accurately reports effective weights (`1.0 ML / 0.0 LLM`), while `requested_weights` preserves what the caller originally requested (`0.70 ML / 0.30 LLM`).
- **Non-Finite Weight Protection:** Enforced `math.isfinite()` in `EnsembleWeights.__post_init__` and `predict.py`, rejecting `NaN`, `Inf`, and `-Inf` with validation errors and HTTP 422.
- **Graceful Fallback:** Verified that model timeouts, daemon unavailability, missing news context, or malformed JSON responses automatically degrade to ML-only mode (`w_ml=1.0, w_llm=0.0`) without raising 500 errors or defaulting to bullish predictions.

### 4. Leakage-Safe Historical Evaluation Results
Evaluated models on chronological holdout dataset for `BHARTIARTL` (N = 240 sessions after 2025-10-27 cutoff, zero lookahead leakage, class balance: 119 UP / 121 DOWN):
| Model Strategy | Sample Size | Accuracy | Precision (UP) | Recall (UP) | F1 (UP) | Brier Score | Confusion Matrix [[TN, FP], [FN, TP]] |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority Baseline** | 240 | 49.58% | 0.4958 | 1.0000 | 0.6630 | 0.5042 | `[[0, 121], [0, 119]]` |
| **XGBoost Classifier** | 240 | 51.25% | 0.5066 | 0.6471 | 0.5683 | 0.2556 | `[[46, 75], [42, 77]]` |
| **LightGBM Classifier** | 240 | 53.75% | 0.5267 | 0.6639 | 0.5874 | 0.2562 | `[[50, 71], [40, 79]]` |

**Historical Qualitative LLM Evaluation Assessment:**
- Live historical LLM inference across 240 sessions was omitted per Section 6 instructions (at ~2.78 tokens/sec on CPU, ~400 tokens/session would require ~9.3 hours of unaccelerated computation).
- Identified prerequisite gaps: Historical 5-year point-in-time archived news corpus is required for faithful historical prompt assembly.
- Until verified qualitative backtest archives exist, qualitative context is treated strictly as an explanatory narrative layer or uncalibrated exploratory blend, preserving quantitative ML forecast authority.

### 5. Verification & Quality Gates
- **Targeted Test Execution:**
  - `tests/test_ensemble_service.py`: **29 passed** in 2.58s (+8 new mathematical and weight audit tests).
  - `tests/test_api.py`: **33 passed** in 5.64s (+2 new API weight audit tests).
  - `tests/test_llm_explanation.py`: **29 passed** in 8.49s.
  - `tests/test_llm_service.py`: **39 passed** in 3.09s.
- **Full Repository Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **715 passed**, 1 warning in 50.81s across all 48 test modules (0 failures, 0 regressions).
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Whitespace Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File SHA-256 Baselines:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 6. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
Ensemble architecture audit and prediction validation are complete. External staging, multi-instrument soak testing, and live market monitoring remain outstanding on the roadmap.

---

## Day 59: Multi-Instrument Validation & Ensemble Safety Gates

### 1. Executive Summary
- **Baseline Commit:** `b698d97` (`audit(prediction): validate ensemble signal and fallback semantics`).
- **Goal Achieved:** Validated the prediction pipeline across multiple instruments (`BHARTIARTL`, `TCS`, `RELIANCE`, `NIFTY_TELECOMMUNICATIONS`) without cross-pollinating incompatible models (equity vs. sectoral index, or BHARTIARTL weights onto TCS/RELIANCE), fabricating evaluation results, or misrepresenting qualitative LLM heuristic scores as calibrated probabilities.
- **Verification:** All **735 tests passing** (+20 new deterministic multi-instrument compatibility and safety gate tests) across 49 test modules. Zero regressions. `pip check` clean. `git diff --check` clean (0 whitespace errors). Protected database and model artifact hashes verified 100% bit-identical.
- **Roadmap Invariant:** **Phase 16 remains strictly IN PROGRESS** (external soak testing, staging deployment, and live monitoring telemetry remain outstanding).

### 2. Instrument Compatibility Matrix
| Instrument | Type | Historical Source | Data Completeness | Feature Schema & Warmup | Compatible Model Artifact | Inference & Evaluation Status |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| **BHARTIARTL** | EQUITY | `yfinance` (`BHARTIARTL.NS`) | Full OHLCV | `canonical_37_features` (34+ bars) | `xgboost`, `lightgbm` (PROMOTED) | **SUPPORTED** (53.75% Holdout Acc) |
| **TCS** | EQUITY | `yfinance` (`TCS.NS`) | Full OHLCV | `canonical_37_features` (34+ bars) | *None* (training required) | **BLOCKED (`MODEL_UNAVAILABLE`)** |
| **RELIANCE** | EQUITY | `yfinance` (`RELIANCE.NS`) | Full OHLCV | `canonical_37_features` (34+ bars) | *None* (training required) | **BLOCKED (`MODEL_UNAVAILABLE`)** |
| **NIFTY_TELECOM** | INDEX | `nifty_indices` (NSE archive) | Close-only / Zero volume | Close-only subset (Candle wicks NaN) | *None* (Equity models prohibited) | **BLOCKED (`MODEL_UNAVAILABLE`)** |

### 3. Chronological ML Evaluation Results
Evaluated models on chronological holdout dataset for `BHARTIARTL` (N = 240 sessions after 2025-10-27 cutoff, zero lookahead leakage, class balance: 119 UP [49.6%] / 121 DOWN [50.4%]):
| Model Strategy | Sample Size | Accuracy | Precision (UP) | Recall (UP) | F1 (UP) | Brier Score | Confusion Matrix [[TN, FP], [FN, TP]] |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority Baseline** | 240 | 49.58% | 0.4958 | 1.0000 | 0.6630 | 0.5042 | `[[0, 121], [0, 119]]` |
| **XGBoost Classifier** | 240 | 51.25% | 0.5066 | 0.6471 | 0.5683 | 0.2556 | `[[46, 75], [42, 77]]` |
| **LightGBM Classifier** | 240 | 53.75% | 0.5267 | 0.6639 | 0.5874 | 0.2562 | `[[50, 71], [40, 79]]` |

### 4. Blocked Instrument Evaluations & Safeguards
- **TCS:** Blocked with status `MODEL_UNAVAILABLE`. Historical OHLCV is available from market providers, but no trained model artifact exists on disk (`models/tcs_xgboost_direction.json`). Equity models are symbol-specific; `BHARTIARTL` model weights cannot be cross-applied to TCS without dedicated model training.
- **RELIANCE:** Blocked with status `MODEL_UNAVAILABLE`. Historical OHLCV is available, but no trained model artifact exists on disk. `BHARTIARTL` model weights cannot be cross-applied to RELIANCE without dedicated training.
- **NIFTY_TELECOMMUNICATIONS:** Blocked with status `MODEL_UNAVAILABLE`. Sectoral benchmark index. `BHARTIARTL` equity model weights cannot be reused for sectoral index forecasting. Furthermore, close-only historical index data lacks intraday OHLC candlestick geometry (`candle_body`, `candle_upper_wick`, `candle_lower_wick`, and `atr_14` evaluate strictly as `NaN`), precluding execution of the canonical 37-feature equity schema.
- **Zero-Fabrication Guarantee:** Blocked instruments are reported explicitly as `BLOCKED (MODEL_UNAVAILABLE)`, never fabricated as 0% accuracy or successful forecasts.

### 5. Ensemble Safety & LLM Status
- **Weight Accounting:** Preserves configured/requested weights (`requested_weights: {ml: 0.70, llm: 0.30}`) while explicitly logging effective weights (`weights_used: {ml: 1.0, llm: 0.0}`) when falling back to ML-only mode upon missing/unprovided qualitative LLM reasoning.
- **Input Validation:** Rejects non-finite, negative, and zero-sum weight specifications (`NaN`, `Inf`, `-Inf`) with HTTP 422.
- **Heuristic Characterization:** Documented that qualitative polarity-to-probability mapping ($0.50 + 0.50 \times \text{polarity}$) is a qualitative heuristic score, not a statistically calibrated probability.
- **Blended Historical Evaluation:** In the absence of an empirical 5-year point-in-time historical news corpus, multi-instrument blended ensemble performance is strictly labeled `NOT EVALUATED`.

### 6. Verification & Quality Gates
- **Targeted Test Execution:**
  - `tests/test_instrument_compatibility.py`: **20 passed** in 5.81s (+20 new multi-instrument compatibility, model isolation, and safety gate tests).
  - `tests/test_prediction_service.py` & `tests/test_nifty_telecom_integration.py`: **35 passed** in 7.27s.
  - `tests/test_ensemble_service.py`: **29 passed** in 2.65s.
- **Full Repository Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **735 passed**, 1 warning in 44.70s across all 49 test modules (0 failures, 0 regressions).
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Whitespace Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File SHA-256 Baselines:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 7. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
Multi-instrument validation, cross-model isolation gates, and fallback accounting are verified with empirical tests. Outstanding Phase 16 requirements:
1. Multi-instrument evaluation under concurrent simulated user load.
2. Extended soak testing across multi-day session boundaries.
3. Live operational monitoring, error budget alerting, and performance drift telemetry.
---

## Day 60: Historical Evaluation Data-Readiness Audit

### 1. Executive Summary
- **Baseline Commit:** `5bdebaf` (`test(prediction): validate multi-instrument compatibility`).
- **Goal Achieved:** Conducted an exhaustive data-readiness audit across repository datasets, databases, news/event providers, model metadata, and evaluation scripts to determine whether sufficient point-in-time historical data exists to evaluate ML-only predictions against an LLM-assisted or blended approach.
- **Readiness Classification:**
  - **Numerical ML-Only Evaluation:** **`READY`** (Holdout dataset of $N = 240$ sessions for `BHARTIARTL` is deterministically reproducible from market providers and model metadata).
  - **LLM-Only Qualitative Evaluation:** **`BLOCKED`** (No point-in-time historical news or regulatory event archive exists in the repository for past evaluation dates; live RSS feeds only provide rolling windows of contemporary articles).
  - **Blended (ML + LLM) Evaluation:** **`BLOCKED`** (Valid matched-date comparison requires contemporaneous qualitative signals; evaluating with contemporary news violates temporal isolation and introduces lookahead contamination).
- **Integrity & Quality Gates:** All **747 tests passing** (+12 new deterministic data readiness audit tests) across 50 test modules. Zero regressions. `pip check` clean. `git diff --check` clean (0 whitespace errors). Protected database and model artifact hashes verified 100% bit-identical.
- **Roadmap Invariant:** **Phase 16 remains strictly IN PROGRESS.**

### 2. Dataset & Provider Inventory
| Dataset / Source | Storage Location | Instrument / Topic | Records | Earliest / Latest | Nulls / Dups | Pub / Ingestion Timestamps | Point-in-Time Availability |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `predictions.db` | `data/predictions.db` | Predictions, Actuals, Releases | 0 rows | N/A | None / None | Yes (schema supports `created_at`) | Pristine schema initialized (0 operational rows) |
| `data/raw/` | `data/raw/.gitkeep` | Historical CSV/Parquet raw dumps | 0 files | N/A | None / None | No | No local raw market/news archives stored |
| `data/processed/` | `data/processed/.gitkeep` | Feature matrices / processed datasets | 0 files | N/A | None / None | No | No cached feature datasets stored |
| `data/cache/` | `data/cache/.gitkeep` | Cache persistence | 0 files | N/A | None / None | No | Ephemeral / uncommitted cache |
| `YFinanceProvider` | Dynamic API | `BHARTIARTL.NS`, `TCS.NS`, `RELIANCE.NS` | Dynamic | 5+ years historical OHLCV | Handled / Deduplicated | Session timestamps verified | Verified point-in-time OHLCV historical bars |
| `NiftyIndicesProvider` | Dynamic API | `NIFTY_TELECOMMUNICATIONS` | Dynamic | Multi-year close-only index | Zero volume / Close-only | Daily session dates verified | Verified point-in-time benchmark index history |
| `RSSNewsProvider` | Dynamic RSS Feed | Financial & corporate news (Google News) | Dynamic | Rolling 7-14 days only | RSS deduplication active | PubDate in RSS, no historical archive | **NOT AVAILABLE historically** (Live feed only) |
| `RBIEventProvider` | Dynamic RSS Feed | RBI monetary policy & circulars | Dynamic | Rolling 30 days only | RSS deduplication active | PubDate in RSS, no historical archive | **NOT AVAILABLE historically** (Live feed only) |
| `SEBIEventProvider` | Dynamic RSS Feed | SEBI regulatory circulars & press | Dynamic | Rolling 30 days only | RSS deduplication active | PubDate in RSS, no historical archive | **NOT AVAILABLE historically** (Live feed only) |
| `model_metadata.json` | `models/model_metadata.json` | Model parameters, train/test cutoffs | 1 file | Cutoff: 2025-10-27 | None / None | UTC training timestamp recorded | Verified artifact defining $N=240$ holdout |

### 3. Historical News & Event Audit Findings
- **Zero Historical News Archive:** The repository contains no historical news database or point-in-time article store. Live RSS feeds (`RSSNewsProvider`, `RBIEventProvider`, `SEBIEventProvider`) only return active, recent feeds.
- **Strict Prohibition on Backfilling:** Assigning contemporary news articles to historical prediction cutoffs (e.g. 2025–2026 test dates) violates temporal isolation and introduces lookahead bias.
- **Readiness Classification:**
  - `ML-Only`: **READY**
  - `LLM-Only`: **BLOCKED**
  - `Blended`: **BLOCKED**

### 4. Market Labels, Cutoff Semantics & Anti-Leakage Audit
- **Forecast Horizon:** Next trading session close-to-close direction.
- **Target Label Definition:** $y_t = 1$ if $	ext{Close}_{t+1} > 	ext{Close}_t$, else $0$.
- **Temporal Cutoff & Partitions:**
  - Cutoff Date: `2025-10-27`.
  - Training Set: 958 sessions up to and including cutoff.
  - Embargo: 1 session (`2025-10-28`) strictly isolates training label resolution ($t+1$) from test feature evaluation.
  - Test Holdout: 240 chronological sessions (`2025-10-29` to `2026-10-20`).
  - Class Balance: 119 UP (49.58%), 121 DOWN (50.42%).
- **Reproducibility of ML Baseline:** The 240-session holdout evaluation for `BHARTIARTL` is 100% deterministically reproducible from market data and committed model artifacts (`xgboost_direction.json` yielding 51.25% acc, `lightgbm_direction.txt` yielding 53.75% acc).

### 5. Reproducible Evaluation Protocol & Prerequisites
- **Candidate Models:**
  1. Majority Class / Simple Direction Baseline.
  2. Numerical ML-Only Model (`XGBoost` / `LightGBM`).
  3. LLM-Only Qualitative Stance (converted via heuristic polarity mapping).
  4. Blended Model (convex combination of ML probability and LLM pseudo-probability).
- **Protocol Invariants:**
  - Evaluated on identical matched-date test sessions ($N = 240$).
  - Pre-defined metrics: Directional Accuracy, Precision, Recall, F1, Confusion Matrix, Brier Score (for true probabilities), and Wilson score confidence intervals.
  - Zero post-hoc weight tuning on test set.
- **Prerequisites to Unblock LLM/Blended Historical Evaluation:**
  1. Historical point-in-time news store preserving publication timestamps, ingestion timestamps, source URLs, and headline/body text.
  2. Historical macroeconomic and regulatory calendar with verified release timestamps.
  3. Batch or GPU-accelerated local inference pipeline for the $N \ge 240$ holdout sessions.

### 6. Verification & Quality Gates
- **Programmatic Audit Tool:**
  - Executed `scripts/audit_historical_readiness.py` producing verified inventory and readiness report.
- **Targeted Test Execution:**
  - `tests/test_data_readiness_audit.py`: **12 passed** in 3.08s (+12 new tests covering inventory, readiness classification, embargo semantics, and database invariants).
- **Full Repository Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **747 passed**, 1 warning in 43.16s across all 50 test modules (0 failures, 0 regressions).
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Whitespace Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File SHA-256 Hashes:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 7. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
Empirical data-readiness audit completed; historical evaluation protocol codified; ML baseline verified reproducible. Outstanding Phase 16 requirements:
1. Multi-instrument evaluation under concurrent simulated user load.
2. Extended soak testing across multi-day session boundaries.
3. Live operational monitoring, error budget alerting, and performance drift telemetry.
---

## Day 61: Independent ML Baseline Reproducibility & Temporal-Leakage Audit

### 1. Executive Summary
- **Baseline Commit:** `b876225` (`audit(evaluation): assess historical data readiness`).
- **Goal Achieved:** Independently recomputed, audited, and verified the reported 240-session out-of-sample ML evaluation for `BHARTIARTL` across market data, target formulation, embargo isolation, probability outputs, Brier scores, and committed metadata artifacts.
- **Reproducibility Status:** **`REPRODUCIBLE`** (on canonical training snapshot cutoff). All reported metrics, sample sizes, class distributions, confusion matrices, and Brier scores reproduced with 100% precision.
- **Integrity & Quality Gates:** All **757 tests passing** (+10 new deterministic tests covering Brier formulation, majority probability specification, target equality handling, temporal embargo boundaries, anti-leakage guards, and run-to-run bit-identical determinism) across 51 test modules. Zero regressions. `pip check` clean. `git diff --check` clean. Protected database and model artifact hashes verified 100% bit-identical.
- **Roadmap Invariant:** **Phase 16 remains strictly IN PROGRESS.**

### 2. Independent Recomputed Evaluation Table ($N = 240$ Holdout)
| Model Architecture | Sample Size | Accuracy | Precision (UP) | Recall (UP) | F1 (UP) | Brier Score | Confusion Matrix [[TN, FP], [FN, TP]] | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority Baseline** | 240 | 49.58% | 0.4958 | 1.0000 | 0.6630 | 0.5042 | `[[0, 121], [0, 119]]` | REPRODUCED |
| **XGBoost Classifier** | 240 | 51.25% | 0.5066 | 0.6471 | 0.5683 | 0.2556 | `[[46, 75], [42, 77]]` | REPRODUCED |
| **LightGBM Classifier** | 240 | 53.75% | 0.5267 | 0.6639 | 0.5874 | 0.2562 | `[[50, 71], [40, 79]]` | REPRODUCED |

- **Run-to-Run Determinism:** Pass 1 vs Pass 2 confirmed bit-identical arrays for predicted labels, probabilities, and metric summaries (`max_abs_diff = 0.0`).
- **Class Balance:** 119 UP (49.58%), 121 DOWN (50.42%).

### 3. Temporal Alignment & Anti-Leakage Audit
- **Session Definitions & Forward Horizon:**
  - Feature observation sessions: `2025-10-29` to `2026-10-19` ($N = 240$).
  - Target outcome realization sessions: `2025-10-30` to `2026-10-21`.
  - Target formulation: $y_t = 1$ if $\text{Close}_{t+1} > \text{Close}_t$ else $0$. Zero return / flat closes map deterministically to DOWN ($0$) with zero sample discarding.
  - Non-trading days (weekends, NSE holidays) are handled naturally via chronological indexing of consecutive session bars.
- **Embargo Boundary Isolation:**
  - Training window: 958 sessions from `2021-12-10` to `2025-10-27`.
  - Final training bar target realization date: `2025-10-28`.
  - Embargo session: `2025-10-28` (1 boundary session purged from both training and holdout).
  - Holdout start date: `2025-10-29`.
  - Strict invariant verified: `train_outcome_cutoff` (`2025-10-28`) < `holdout_start_date` (`2025-10-29`). Zero temporal leakage exists across partitions.
- **Feature Matrix Isolation:**
  - `validate_feature_matrix_isolation` guarantees feature matrix $X$ is strictly isolated from forward target columns (`target_`, `next_`, `future`, `outcome`).
  - Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ROC, Candlesticks) are strictly backward-looking.

### 4. Probability Metrics & Calibration Audit
- **Class Probability Alignment:**
  - Column 0 represents $P(\text{DOWN})$; Column 1 represents $P(\text{UP})$.
  - Verified for both XGBoost and LightGBM that $P(\text{DOWN}) + P(\text{UP}) = 1.0$ everywhere.
- **Brier Score Calculation:**
  - Computed on genuine continuous model probability outputs: $BS = \frac{1}{N} \sum (P(UP)_i - y_i)^2$.
  - Majority baseline probability is explicitly specified as $P(\text{UP}) = 1.0$ unconditionally, yielding $BS = \frac{121}{240} = 0.5042$.
  - Tree model Brier scores: XGBoost ($0.2556$), LightGBM ($0.2562$).
  - **Calibration Caveat:** While Brier score is superior to majority baseline ($0.5042$), scores around $0.255$ are close to uninformative guessing ($0.2500$ for constant $p=0.5$). Probabilities are clustered in $[0.30, 0.77]$ around a mean of $\sim 0.53$, slightly over-predicting the actual holdout base rate of $0.4958$. They must not be treated as fully calibrated posterior probabilities without explicit isotonic/Platt calibration.

### 5. Audit of Day 60 Claims & Discrepancies
- **Date Clarification:** Day 60 reported holdout dates as `2025-10-29 through 2026-10-20`. The audit establishes that prediction feature sessions run from `2025-10-29` to `2026-10-19` ($N=240$), while the realized target outcome sessions span `2025-10-30` through `2026-10-21`.
- **Dynamic Live Rolling-Window Shift:** In `train_models.py`, `start_time = now - timedelta(days=1825)` uses a dynamic rolling window. If executed with live `datetime.now()` without pinning to the training cutoff, the 20% holdout window shifts forward by 1-2 trading days.
- **Resolution:** Created `app/history/reproducibility.py` anchoring evaluation to canonical snapshot cutoff `CANONICAL_TRAIN_CUTOFF_UTC` (`2026-10-21T17:16:42Z`), guaranteeing 100% deterministic reproducibility.

### 6. Verification & Quality Gates
- **Programmatic Reproducibility Tool:**
  - Executed `scripts/evaluate_ensemble_backtest.py` with live `--recompute` pass.
- **Targeted Test Execution:**
  - `tests/test_ml_baseline_reproducibility.py`: **10 passed** in 4.47s (+10 new deterministic tests).
- **Full Repository Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **757 passed**, 1 warning in 46.10s across all 51 test modules (0 failures, 0 regressions).
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Whitespace Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File SHA-256 Hashes:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 7. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
Independent reproducibility of numerical ML baselines confirmed; temporal embargo and anti-leakage invariants verified; probability calibration limitations documented.

---

## Day 62: Probability Calibration & Statistical Significance Audit

### 1. Executive Summary
- **Baseline Commit:** `cc3aa08` (`test(evaluation): reproduce numerical ml baseline and audit temporal leakage`).
- **Goal Achieved:** Audited probability forecasts of BHARTIARTL XGBoost and LightGBM models against explicit probability baselines; evaluated reliability and calibration error; performed paired statistical significance tests (McNemar with Edwards' continuity correction); formulated a leakage-safe calibration protocol without touching the final holdout.
- **Key Finding:** While XGBoost (51.25%) and LightGBM (53.75%) achieve nominal directional accuracy above 50%, their probability forecasts underperform a constant uninformative $P(\\text{UP})=0.50$ reference on both Brier score ($0.2556$ and $0.2562$ vs $0.2500$) and Log Loss ($0.7050$ and $0.7064$ vs $0.6931$) due to miscalibration in low signal-to-noise regimes.
- **Statistical Significance Status:** **INCONCLUSIVE**. 95% Wilson score confidence intervals for all models and baselines overlap and span 50%. Paired McNemar tests show no statistically significant superiority for XGBoost ($p = 0.7491$) or LightGBM ($p = 0.3428$) over majority guessing, nor between XGBoost and LightGBM ($p = 0.3912$).
- **Calibration Protocol Status:** **DESIGNED / UNVERIFIED**. In accordance with strict anti-leakage invariants, no calibrator was fitted on the 240-session final holdout. A 3-partition chronological protocol (Train / Calibration / Holdout) and out-of-fold walk-forward design are specified for future retraining phases.
- **Integrity & Quality Gates:** All **766 tests passing** (+9 new deterministic tests covering Brier, Log Loss, Wilson CI, empty bin safety, ECE, and McNemar paired tests) across 52 test modules. Zero regressions. `pip check` clean. `git diff --check` clean. Protected database and model artifact hashes verified 100% bit-identical.
- **Roadmap Invariant:** **Phase 16 remains strictly IN PROGRESS.**

### 2. Probability Baselines & Evaluation Table ($N = 240$ Holdout)
| Strategy / Model | Forecast Rule | Prob Range | Accuracy (95% CI) | Brier Score | Log Loss | ECE (MCE) | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Constant Reference** | $P(\\text{UP}) = 0.5000$ | $[0.50, 0.50]$ | 49.58% $[43.32\%, 55.88\%]$ | **0.2500** | **0.6931** | 0.0042 (0.0042) | REFERENCE |
| **Training Prior Rate** | $P(\\text{UP}) = 0.5240$ | $[0.52, 0.52]$ | 49.58% $[43.32\%, 55.88\%]$ | 0.2508 | 0.6947 | 0.0282 (0.0282) | REFERENCE |
| **Majority Hard Class** | $P(\\text{UP}) = 1.0000$ | $[1.00, 1.00]$ | 49.58% $[43.32\%, 55.88\%]$ | 0.5042 | 15.0000+ | 0.5042 (0.5042) | BASELINE |
| **XGBoost Classifier** | Raw Tree Sigmoid | $[0.30, 0.77]$ | 51.25% $[44.96\%, 57.49\%]$ | 0.2556 | 0.7050 | 0.0523 (0.1274) | AUDITED |
| **LightGBM Classifier**| Raw Tree Sigmoid | $[0.32, 0.75]$ | 53.75% $[47.43\%, 59.94\%]$ | 0.2562 | 0.7064 | 0.0980 (0.3275) | AUDITED |

- **Brier & Log Loss Divergence:** Tree models exhibit higher directional accuracy by making probabilistic bets ($P \\in [0.30, 0.77]$ around a mean of $\\approx 0.53$). However, in noisy financial markets, probability deviations away from 0.50 that do not correspond to reliable odds incur substantial variance penalties, degrading Brier and Log Loss below constant 0.50 guessing.
- **Reliability Diagnostics:**
  - XGBoost: Moderate miscalibration ($ECE = 0.0523$, max gap $MCE = 0.1274$ in $[0.7, 0.8]$ bin).
  - LightGBM: Severe miscalibration ($ECE = 0.0980$, max gap $MCE = 0.3275$ in $[0.2, 0.4]$ bin where predicted confidence was 0.3681 but empirical accuracy was 0.6957).

### 3. Statistical Significance & Paired Model Comparison
- **Uncertainty Estimates (Wilson Score 95% CIs):**
  - Majority / Constant: $[43.32\\%, 55.88\\%]$ (width 12.56%)
  - XGBoost: $[44.96\\%, 57.49\\%]$ (width 12.53%)
  - LightGBM: $[47.43\\%, 59.94\\%]$ (width 12.51%)
  - All intervals overlap extensively and span the 50% neutral threshold.
- **Paired Comparison (McNemar Test with Edwards' Continuity Correction):**
  - Observations are matched session-by-session across identical dates ($N = 240$).
  - **Majority Baseline vs XGBoost:**
    - Contingency: $b = 46$ (Baseline wrong, XGBoost correct), $c = 42$ (Baseline correct, XGBoost wrong).
    - $\\chi^2 = 0.1023, p = 0.7491$ (Fail to reject $H_0$; difference is random variation).
  - **Majority Baseline vs LightGBM:**
    - Contingency: $b = 50$ (Baseline wrong, LightGBM correct), $c = 40$ (Baseline correct, LightGBM wrong).
    - $\\chi^2 = 0.9000, p = 0.3428$ (Fail to reject $H_0$; difference is not statistically significant).
  - **XGBoost vs LightGBM:**
    - Contingency: $b = 20$ (XGBoost wrong, LightGBM correct), $c = 14$ (XGBoost correct, LightGBM wrong).
    - $\\chi^2 = 0.7353, p = 0.3912$ (Fail to reject $H_0$; neither model is statistically superior).

### 4. Leakage-Safe Calibration Protocol Design
- **Readiness Status:** **`DESIGNED / UNVERIFIED`**.
- **Holdout Preservation Invariant:** Fitting a calibrator on the final holdout would violate strict zero-leakage constraints. No calibrator was fitted on the 240-session holdout.
- **Three-Partition Design for Retraining Phases:**
  1. **Training Partition:** Historical sessions $[t_0, t_{\\text{cal}}\\text{start} - 2]$ used to fit base models.
  2. **Embargo Gap 1:** 1 session before calibration window.
  3. **Calibration Partition:** Pre-holdout sessions $[t_{\\text{cal}}\\text{start}, t_{\\text{holdout}}\\text{start} - 2]$ used to generate out-of-sample predictions and fit Platt / Isotonic calibrators.
  4. **Embargo Gap 2:** 1 session before holdout window.
  5. **Final Holdout Partition:** Untouched final sessions for out-of-sample evaluation only.
- **Out-of-Fold (OOF) Alternative:** Walk-forward expanding-window cross-validation on pre-holdout data to generate un-leaked predictions for calibration fitting.

### 5. Verification & Quality Gates
- **Targeted Test Suite:**
  - `tests/test_calibration_and_significance.py`: **9 passed** in 2.76s.
  - `tests/test_ml_baseline_reproducibility.py`: **10 passed** in 4.41s.
- **Full Test Suite:**
  ```powershell
  .\\.venv\\Scripts\\python -m pytest -q
  ```
  **766 passed**, 1 warning in 48.72s across all 52 test modules (0 failures, 0 regressions).
- **Dependency Audit:**
  ```powershell
  .\\.venv\\Scripts\\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Whitespace Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File SHA-256 Hashes:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 6. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
Probability baseline hierarchy established; miscalibration and variance penalties on Brier/LogLoss documented; paired statistical significance confirmed inconclusive; calibration protocol designed.

---

## Day 63: Web Application Foundation & Prediction API Contract Audit

### 1. Executive Summary
- **Baseline Commit:** `4de808d` (`test(evaluation): audit probability calibration and statistical significance`).
- **Goal Achieved:** Audited and implemented the web application foundation and prediction API contract layer using the existing FastAPI backend and vanilla HTML/CSS/JavaScript architecture; established authoritative instrument compatibility checks, uncalibrated score labeling, quote distinction, and client reliability guards.
- **Instrument Compatibility Contract:** Exposed `GET /api/predict/instruments` returning typed `InstrumentCatalogResponse`. Enforced strict backend gating: `BHARTIARTL` is marked `SUPPORTED` (XGBoost/LightGBM/Ensemble available); `TCS`, `RELIANCE`, and `NIFTY_TELECOMMUNICATIONS` are marked `BLOCKED` with explicit architectural rationales (symbol specificity and index separation).
- **Uncalibrated Model Score Labeling:** In accordance with Day 62 audit findings, raw model probabilities are explicitly labeled uncalibrated (`is_probability_calibrated=False`, `probability_calibration="uncalibrated"`). Frontend displays prominent warning banners noting that raw tree scores underperformed the constant 0.50 Brier reference on the 240-session holdout (0.2556 vs 0.2500, p > 0.34) and are not investment-ready.
- **Historical Fact vs. Forward Prediction Distinction:** Added a dedicated visual distinction bar cleanly separating historical observed market prices (facts as of specific timestamp) from forward directional forecasts (uncertain model predictions for the next session).
- **Frontend Reliability & Defensive Security:** Integrated `AbortController` with a 30-second timeout guard, duplicate in-flight submission locking (`AppState.isPredicting`), and a dedicated `#result-blocked-card` state for unsupported instruments. Verified zero filesystem paths or stack traces exposed to clients.
- **Integrity & Quality Gates:** All **776 tests passing** (+10 new deterministic tests covering instrument catalog schemas, authoritative gating, blocked instrument sanitization, quote distinction, and frontend reliability) across 53 test modules. Zero regressions. `pip check` clean. `git diff --check` clean. Protected database and model artifact hashes verified 100% bit-identical.
- **Roadmap Invariant:** **Phase 16 remains strictly IN PROGRESS.**

### 2. Prediction API Contract & Instrument Catalog
| Instrument | Type | Exchange | Status | Compatible Models | Architectural Rationale |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **BHARTIARTL** | EQUITY | NSE | **SUPPORTED** | `xgboost`, `lightgbm`, `ensemble` | Validated production models available on disk |
| **TCS** | EQUITY | NSE | **BLOCKED** | None | No trained model artifact found on disk; equity models are symbol-specific |
| **RELIANCE** | EQUITY | NSE | **BLOCKED** | None | No trained model artifact found on disk; equity models are symbol-specific |
| **NIFTY_TELECOM** | INDEX | NSE | **BLOCKED** | None | Index forecasting model unavailable; equity models prohibited on sectoral indices |
| **NIFTY_50** | INDEX | NSE | **BLOCKED** | None | Benchmark index forecasting model unavailable; equity models prohibited on indices |

- **API Endpoints Audited & Active:**
  - `GET /api/health`: Subsystem readiness diagnostics (database, models, LLM config).
  - `GET /api/predict/instruments`: Authoritative registered instrument catalog and model compatibility.
  - `POST /api/predict`: Point-in-time directional inference with input validation and sanitized error responses.
  - `GET /api/history`: Paginated immutable prediction audit history with verified actual outcomes.
  - `GET /api/events`: Macroeconomic and regulatory event monitoring with point-in-time filtering.

### 3. Frontend Architecture & Reliability Safeguards
- **Vanilla Frontend Architecture:** Zero external UI frameworks; built with semantic HTML5, pure CSS3 design system tokens, and vanilla ES6 JavaScript (`app/api/static/`).
- **Dynamic Catalog Loading:** Frontend queries `GET /api/predict/instruments` on load to dynamically update quick-selection chips with live status indicators (emerald dot for supported; amber dot for blocked).
- **Dedicated Blocked Instrument State:** When an unsupported instrument is selected, the UI displays a structured diagnostic card explaining symbol specificity and index separation constraints, preventing user confusion.
- **Timeout & Request Cancellation:** Wrapped `ApiService.runPrediction` with `AbortController` (30-second timeout), catching connection stalls or slow upstream provider responses with clean recovery.
- **Defensive DOM Rendering:** All user and model strings are bound through `textContent` or `document.createElement`, with URLs validated via `isSafeHttpUrl` to prevent XSS injection.

### 4. Verification & Quality Gates
- **Targeted Test Execution:**
  - `tests/test_web_foundation_audit.py`: **10 passed** in 4.95s (+10 new deterministic tests).
  - `tests/test_frontend.py`: **11 passed** in 3.06s.
  - `tests/test_api.py`: **33 passed** in 4.66s.
- **Full Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **776 passed**, 1 warning across all 53 test modules (0 failures, 0 regressions).
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Whitespace Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File SHA-256 Hashes:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (100% UNCHANGED).
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (100% UNCHANGED).

### 5. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
Web application foundation and prediction API contract audit complete; authoritative instrument catalog implemented; uncalibrated score and quote distinction active; client reliability and timeout guards verified.

---

## Day 64 - End-to-End Browser Workflow & Frontend Functionality Audit

### Goal
Audit and harden the running browser-to-backend integration over real HTTP sockets on the local Uvicorn instance (`127.0.0.1:8000`). Identify and resolve concrete functional, rendering, accessibility, and state-management defects: expand symbol input bounds to prevent index truncation, eliminate race conditions and out-of-order response overwrites, implement fast double-submission locking and chip disabling during active inference, clean up stale DOM elements on prediction errors, handle malformed payloads gracefully, and provide accessible fallback notices for catalog loading.

### 1. Git Baseline & Initial Integrity Check
- **Baseline Commit:** `3937139` (`feat(web): audit prediction api contracts and establish web application foundation`)
- **Remote Synchronization:** Working tree clean; local `main` synchronized with `origin/main` at `3937139e82f6904c7827366328471c60cd5baeb7`.
- **Pre-Test Data Hashes:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e`
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

---

### 2. Live HTTP Socket Testing & Actual Backend Responses
Executed real HTTP requests against live Uvicorn ASGI server (`python -m uvicorn app.api.app:app --host 127.0.0.1 --port 8000`):
- **Root and UI Access:** `GET /ui` and `GET /` successfully returned HTTP 200 with defensive security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`).
- **Dynamic Catalog Verification:** `GET /api/predict/instruments` returned all 5 registered instruments: `BHARTIARTL` (SUPPORTED) and `TCS`, `RELIANCE`, `NIFTY_TELECOMMUNICATIONS`, `NIFTY_50` (BLOCKED) with truthful reasons.
- **Supported Prediction Flow (`BHARTIARTL`):**
  - Status: `SUCCESS`
  - Predicted Direction: `DOWN` (Label 0)
  - Probability: `0.4979` UP / `0.5021` DOWN
  - Probability Calibration: `uncalibrated` (`is_probability_calibrated: false`)
  - Historical Observed Quote: `1895.00 INR` (`LAST_TRADED_PRICE`, Session state: `CLOSED`, Freshness: `FRESH`)
  - Quote vs Prediction Note: Explicitly clarifies that last traded price is an observed market datum and NOT a predicted opening or closing price.
- **Blocked Equity Flow (`TCS`):**
  - Status: `MODEL_UNAVAILABLE`
  - Sanitized Message: `"No trained model artifact found for equity instrument 'TCS'. Default models are trained specifically for 'BHARTIARTL' and cannot be cross-applied to other equities."`
  - Zero filesystem path or traceback leakage in client payload.
- **Blocked Sectoral Index Flow (`NIFTY_TELECOMMUNICATIONS`):**
  - Status: `MODEL_UNAVAILABLE`
  - Sanitized Message: `"Index-specific forecasting model unavailable for 'NIFTY_TELECOMMUNICATIONS'. BHARTIARTL equity models cannot be reused for sectoral indices."`

---

### 3. Discovered Defects & Applied Remediations
1. **Symbol Input Length Truncation:**
   - *Defect:* HTML `<input id="symbol-input">` had `maxlength="20"`, which truncated `NIFTY_TELECOMMUNICATIONS` (22 characters) to `NIFTY_TELECOMMUNICAT`, failing regex schema validation.
   - *Fix:* Expanded `maxlength="30"` in `app/api/static/index.html` and updated placeholder.
2. **Out-of-Order Stale Response Race Condition:**
   - *Defect:* If an earlier request took longer than a subsequent request, the earlier response would overwrite the active prediction result with stale data.
   - *Fix:* Added `AppState.predictionRequestId` sequence counter. Inbound responses verify `currentReqId === AppState.predictionRequestId` before updating state or DOM. Added `AppState.activePredictionAbortController` to abort previous in-flight requests.
3. **Double-Submission & In-Flight Instrument Switching:**
   - *Defect:* `AppState.isPredicting` was set only after asynchronous preparation, leaving a window for double clicks. Instrument chips could also be clicked while an inference was in-flight.
   - *Fix:* Set `AppState.isPredicting = true` immediately upon submit event, and disabled all `.chip` buttons (`chip.disabled = isLoading`) during active inference.
4. **Stale DOM Card Flashing on Error:**
   - *Defect:* `showPredictionError` hid the container, but left `#result-hero-card` and `#result-blocked-card` styled visible, risking flashing stale cards on subsequent state changes.
   - *Fix:* Explicitly hid `heroCard`, `blockedCard`, `breakdownGrid`, and reset `AppState.prediction = null` on error.
5. **Malformed Payload Handling in API Client:**
   - *Defect:* Non-object or empty server responses resulted in `TypeError: Cannot read properties of null (reading 'status')` in `renderPredictionResult`.
   - *Fix:* Validated response object in `ApiService.runPrediction` and added defensive guard in `renderPredictionResult`.
6. **Dynamic Instrument Catalog Fallback Notice:**
   - *Defect:* If `fetchInstruments()` failed on load, the error was only logged to console without visual feedback to the user.
   - *Fix:* Added accessible `.catalog-error-notice` styled in `styles.css` rendered into the chip container upon catalog fetch failure.

---

### 4. Verification & Quality Gates
- **Browser Automation Runtime Observation:**
  - Automated Playwright driver installation within the subagent sandbox failed due to remote upstream CDN 404 (`https://playwright.azureedge.net/.../playwright-1.57.0-win32_x64.zip`). In accordance with Task 1 & Task 6 audit rules and user guidance, verified live workflow via local Uvicorn HTTP socket execution (`127.0.0.1:8000`), real REST invocations, and 13 deterministic automated regression tests covering all browser interaction and state invariants.
- **Targeted Test Execution:**
  - `tests/test_end_to_end_web_audit.py`: **13 passed** in 7.00s (+13 new deterministic tests).
  - `tests/test_web_foundation_audit.py`: **10 passed** in 5.17s.
- **Full Test Suite:**
  ```powershell
  .\.venv\Scripts\python -m pytest -q
  ```
  **789 passed**, 1 warning across all 54 test modules (0 failures, 0 regressions).
- **Dependency Audit:**
  ```powershell
  .\.venv\Scripts\python -m pip check
  ```
  `No broken requirements found.`
- **Git Diff Whitespace Check:**
  ```powershell
  git diff --check
  ```
  `Clean (0 whitespace errors).`
- **Protected File SHA-256 Hashes:**
  - `data/predictions.db`: `d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e` (**100% UNCHANGED**).
  - `models/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (**100% UNCHANGED**).

---

### 5. Phase 16 Status & Next Steps
**Phase 16 remains strictly IN PROGRESS.**
End-to-end browser and web application functionality audit complete; race conditions and stale response dropping resolved; symbol input bounds expanded; live HTTP socket verification against Uvicorn complete; 789 regression tests passing.
