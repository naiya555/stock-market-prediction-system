# Indian Stock Market Prediction System

> **Status:** Ongoing Project — Day 2: Core Application Foundation Complete  
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
- **`app/market/`**: Market data acquisition, cleaning, technical feature engineering, and market breadth.
- **`app/news/`**: Financial news ingestion, deduplication, and entity linking.
- **`app/nlp/`**: FinBERT sentiment scoring and textual analysis.
- **`app/prediction/`**: Numerical ML predictor, LLM predictor, and ensemble synthesis.
- **`app/training/`**: Walk-forward validation, dataset splits without temporal leakage, and controlled retraining.
- **`app/history/`**: Prediction audit logs, performance evaluation, and accuracy tracking.

---

## 4. Current Status: Day 2 (Core Application Foundation)

Day 2 establishes the core application configuration, logging foundation, and canonical market-data schema contracts required prior to data collection.

### Current Features
- Defined 16-phase long-term project roadmap and architecture documentation.
- Centralized, environment-driven configuration layer (`app/core/config.py`) with safe non-secret defaults.
- Structured application logging system (`app/core/logging_config.py`) with configurable log levels.
- Canonical market-data contracts (`MarketOHLCV`, `MarketQuote`, `DataSourceMetadata` in `app/core/schemas.py`) enforcing point-in-time timestamps and structural bounds.
- 20 automated unit tests passing across foundation, settings, logging, and schemas.

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
