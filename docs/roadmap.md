# Long-Term Project Roadmap

This roadmap outlines the planned multi-phase evolution of the Indian Stock Market Prediction System. Development proceeds incrementally across sequential phases. Future phases must not be implemented prematurely.

---

## Roadmap Overview

| Phase | Title | Description | Target Scope |
|:---:|---|---|:---:|
| **1** | **Project Foundation** | Project skeleton, architecture, environment, and validation. | **Current Phase (Day 1)** |
| **2** | **Historical Market Data** | Reliable historical OHLCV data pipeline for Indian equities. | Future |
| **3** | **Technical Feature Engine** | Mathematical computation of indicators, returns, and volatility. | Future |
| **4** | **First ML Model** | Baseline XGBoost model setup with walk-forward temporal validation. | Future |
| **5** | **Prediction Engine** | Point-in-time quantitative forecasting service. | Future |
| **6** | **Prediction History & Database** | Relational schema and immutable storage for predictions. | Future |
| **7** | **Verification & Accuracy** | Outcome recording, MAE/RMSE calculation, and accuracy tracking. | Future |
| **8** | **NIFTY & Sector Context** | Broader market indicators, benchmark relative strength, and sector mapping. | Future |
| **9** | **News & Financial Sentiment** | Financial news ingestion and FinBERT sentiment extraction pipeline. | Future |
| **10** | **Regulatory & Global Events** | Macroeconomic, RBI, governmental, and geopolitical event parser. | Future |
| **11** | **LLM Integration** | Dual-role LLM setup: contextual entity extraction and independent forecasting. | Future |
| **12** | **ML + LLM Combination** | Ensemble layer combining numerical ML and LLM predictions transparently. | Future |
| **13** | **Web Application** | Interactive FastAPI endpoints and user-facing presentation dashboard. | Future |
| **14** | **Live Data Pipeline** | Point-in-time current price, breadth, and market session intake. | Future |
| **15** | **Model Comparison & Improvement**| Comparative metrics (ML vs. LLM vs. Ensemble) and controlled retraining. | Future |
| **16** | **Final Testing & Evaluation** | Comprehensive end-to-end audit, load testing, and production hardening. | Future |

---

## Detailed Phase Descriptions

### Phase 1: Project Foundation (Current)
- Establish workspace structure, virtual environment, and dependency baselines.
- Document system architecture, decision records, and data source protocols.
- Configure version control guidelines and basic foundation test suites.

### Phase 2: Historical Market Data
- Implement data ingestion adapters for Indian equities (NSE/BSE).
- Standardize data formats (date, open, high, low, close, volume, adjust factor).
- Enforce point-in-time timestamping and caching policies.

### Phase 3: Technical Feature Engine
- Implement time-series features: Simple and Exponential Moving Averages (SMA/EMA).
- Momentum and volatility indicators: RSI, MACD, ATR, Bollinger Bands.
- Continuous returns, volume z-scores, and rolling drawdown measures.

### Phase 4: First ML Model
- Establish baseline numerical forecasting model using XGBoost.
- Benchmark against LightGBM.
- Implement walk-forward validation splits (strictly avoiding random cross-validation to prevent temporal leakage).

### Phase 5: Prediction Engine
- Build the core prediction service orchestrating feature assembly and model inference.
- Generate directional forecast (`UP` / `DOWN` / `SIDEWAYS`), confidence, and target range.

### Phase 6: Prediction History & Database
- Design SQLite database schema (predictions, stocks, actuals, model_versions).
- Implement immutable prediction persistence: predictions cannot be edited after creation.

### Phase 7: Verification & Accuracy
- Ingest realized market outcomes.
- Compute prediction error: Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and directional precision/recall.

### Phase 8: NIFTY & Sector Context
- Ingest NIFTY 50, NIFTY Bank, NIFTY IT, and relevant sector indices.
- Calculate relative performance and market breadth features.

### Phase 9: News & Financial Sentiment
- Implement financial news retrieval and deduplication.
- Integrate FinBERT for domain-specific positive/neutral/negative sentiment scoring.

### Phase 10: Regulatory & Global Events
- Structured ingestion of RBI monetary policy, Union Budget announcements, SEBI circulars, and global indicators (crude oil, USD/INR, US markets).
- Contextual impact mapping instead of naive headline matching.

### Phase 11: LLM Integration
- Deploy LLM for structured context extraction (Role A).
- Implement independent LLM direct forecast (Role B) with input attribution and risk identification.

### Phase 12: ML + LLM Combination
- Implement ensemble layer synthesizing numerical ML predictions with qualitative LLM reasoning.
- Retain both independent scores and weighted synthesis in the output payload.

### Phase 13: Web Application
- Build FastAPI REST API endpoints.
- Develop interactive web UI for stock search, prediction visualization, and audit history.

### Phase 14: Live Data Pipeline
- Connect near-real-time market data providers with strict timestamp preservation.
- Handle market session states (pre-open, market hours, post-close).

### Phase 15: Model Comparison & Improvement
- Create comparative dashboards evaluating Python ML vs. LLM vs. Combined performance.
- Implement controlled, gated model retraining workflows with version tracking.

### Phase 16: Final Testing & Evaluation
- End-to-end integration testing and robustness verification under adverse market regimes.
- Security audit, documentation finalization, and deployment readiness review.
