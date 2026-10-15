# Long-Term Project Roadmap

This roadmap outlines the planned multi-phase evolution of the Indian Stock Market Prediction System. Development proceeds incrementally across sequential phases. Future phases must not be implemented prematurely.

---

## Roadmap Overview

| Phase | Title | Description | Target Scope |
|:---:|---|---|:---:|
| **1** | **Project Foundation** | Project skeleton, architecture, environment, and validation. | Complete (Day 1-2) |
| **2** | **Historical Market Data** | Reliable historical OHLCV data pipeline for Indian equities. | Complete (Day 3-4) |
| **3** | **Technical Feature Engine** | Mathematical computation of indicators, returns, and volatility. | Complete (Day 5-14) |
| **4** | **First ML Model** | Baseline XGBoost model setup with walk-forward temporal validation. | Complete (Day 15-21) |
| **5** | **Prediction Engine** | Point-in-time quantitative forecasting service. | Complete (Day 22-23) |
| **6** | **Prediction History & Database** | Relational schema and immutable storage for predictions. | Complete (Day 24) |
| **7** | **Verification & Accuracy** | Outcome recording, MAE/RMSE calculation, and accuracy tracking. | Complete (Day 25) |
| **8** | **NIFTY & Sector Context** | Broader market indicators, benchmark relative strength, and sector mapping. | **Complete (Day 26)** |
| **9** | **News & Financial Sentiment** | Financial news ingestion and FinBERT sentiment extraction pipeline. | Future (Next Phase) |
| **10** | **Regulatory & Global Events** | Macroeconomic, RBI, governmental, and geopolitical event parser. | Future |
| **11** | **LLM Integration** | Dual-role LLM setup: contextual entity extraction and independent forecasting. | Future |
| **12** | **ML + LLM Combination** | Ensemble layer combining numerical ML and LLM predictions transparently. | Future |
| **13** | **Web Application** | Interactive FastAPI endpoints and user-facing presentation dashboard. | Future |
| **14** | **Live Data Pipeline** | Point-in-time current price, breadth, and market session intake. | Future |
| **15** | **Model Comparison & Improvement**| Comparative metrics (ML vs. LLM vs. Ensemble) and controlled retraining. | Future |
| **16** | **Final Testing & Evaluation** | Comprehensive end-to-end audit, load testing, and production hardening. | Future |

---

## Detailed Phase Descriptions

### Phase 1: Project Foundation
- Establish workspace structure, virtual environment, and dependency baselines.
- Document system architecture, decision records, and data source protocols.
- Configure version control guidelines and basic foundation test suites.

### Phase 2: Historical Market Data
- Implement data ingestion adapters for Indian equities (NSE/BSE).
- Standardize data formats (date, open, high, low, close, volume, adjust factor).
- Enforce point-in-time timestamping and caching policies.

### Phase 3: Technical Feature Engine
- Implement time-series features: Simple and Exponential Moving Averages (SMA/EMA).
- Momentum and volatility indicators: RSI, MACD, ATR, Bollinger Bands, ROC.
- Candlestick geometric features: body, range, wicks, normalizing ratios, close location, return %, and direction.
- Trend Engine and market structure analysis: confirmed swing highs/lows with $t + k$ confirmation timing, structure transitions (HH, HL, LH, LL), and UPTREND/DOWNTREND/SIDEWAYS classification.
- Continuous returns, volume z-scores, and rolling drawdown measures.

### Phase 4: First ML Model
- Define next-session binary directional prediction target ($Close_{t+1} / Close_t - 1$, UP if $>0$ else DOWN, zero return grouped into DOWN, missing final session target) (Day 15 complete).
- Feature matrix assembly and tabular dataset generation (canonical 37 numeric features, strict X/y isolation guard, explicit timestamp joins, natural warmup missing-value preservation, labeled subset extraction) (Day 16 complete).
- Establish baseline numerical forecasting model using XGBoost (binary direction classification, chronological holdout split with label outcome embargo, native XGBoost Core API, deterministic evaluation) (Day 17 complete).
- Baseline comparison & evaluation protocol (Majority-Class Classifier, Fixed-Seed Random Uniform/Stratified baselines, comparative evaluation report, bias identification) (Day 18 complete).
- Implement walk-forward validation splits (strictly avoiding random cross-validation to prevent temporal leakage; expanding-window folds with outcome embargo gap, macro/pooled aggregation, single-class guardrails, and comparative benchmarking of Majority, Uniform/Stratified Random, XGBoost, and LightGBM) (Day 20 complete).
- Model error analysis & feature usefulness audit (symmetrical class metrics for UP and DOWN, confusion matrix breakdown, directional prediction bias detection, distribution shift analysis, 37-feature matrix quality audit, collinearity group clustering with 59 pairs >= 0.90, exploratory XGBoost and LightGBM tree feature importance, and zero-leakage training isolation) (Day 21 complete).


### Phase 5: Prediction Engine
- Build the core prediction service orchestrating feature assembly and model inference (`PredictionService` in `app/prediction/service.py`, typed `PredictionRequest` and `PredictionResult` contracts, zero silent retraining, strict inference isolation) (Day 22 complete).
- Structured prediction output & transparency layer: generate validated directional forecast (`UP` / `DOWN`), class probabilities explicitly marked uncalibrated (`is_probability_calibrated=False`), input data quality auditing, explicit expected movement boundaries (`expected_movement=None`, `expected_movement_status="UNSUPPORTED"` for direction classifiers), full JSON serialization via `.to_dict()`, and text audit formatting via `.format_summary()` without fabricating target prices or uncalibrated confidence scores (Day 23 complete).

### Phase 6: Prediction History & Database
- Design SQLite database schema (predictions, stocks, actuals, model_versions) with WAL mode, foreign key constraints, and performance indexes (Day 24 complete).
- Implement immutable prediction persistence: predictions cannot be edited after creation via SQLite engine triggers (`trg_prevent_prediction_update`, `trg_prevent_prediction_delete`) and strongly-typed `PredictionRepository` (Day 24 complete).

### Phase 7: Verification & Accuracy (Current)
- Outcome verification engine (`OutcomeVerifier` in `app/history/verifier.py`): match persisted predictions with realized market sessions ($t+1$), respect trading calendar/holidays/pending sessions, compute canonical target direction/returns ($Close_{t+1}/Close_t - 1$, $R > 0 \implies UP$, $R \le 0 \implies DOWN$), data provenance tracking, and idempotent persistence into SQLite `actuals` table (Day 25 complete).
- Actuals immutability & relational integrity: prevent duplicate or conflicting outcome records, SQLite engine triggers (`trg_prevent_actual_update`, `trg_prevent_actual_delete`) enforce write-once immutability, and atomic foreign-key linking to `predictions` (Day 25 complete).
- Prediction evaluation service (`PredictionEvaluator` in `app/history/evaluator.py`): isolate evaluation denominator strictly to verified predictions ($N_{verified}$), exclude pending and ineligible predictions from error metrics, report symmetrical class metrics (UP/DOWN precision, recall, F1) and confusion matrix breakdown, zero division safety for insufficient samples, without fabricating target prices or calibrated probabilities (Day 25 complete).
- Compute continuous prediction error metrics (MAE, RMSE, direction magnitude correlation) when magnitude models are introduced in later phases.

### Phase 8: NIFTY & Sector Context (Complete - Day 26)
- Ingest NIFTY 50 (`^NSEI`), NIFTY Bank (`^NSEBANK`), NIFTY IT (`^CNXIT`), and relevant sector indices via provider index symbol mapping.
- Calculate point-in-time relative performance: daily relative return / alpha ($R_{stock} - R_{bench}$), relative strength ratio ($Close_{stock} / Close_{bench}$), and 5d/20d relative strength momentum.
- Compute 20-session rolling beta ($\beta_{20} = Cov(R_s, R_b) / Var(R_b)$) and 20-session rolling correlation ($\rho_{20} = Cov(R_s, R_b) / (\sigma_s \sigma_b)$) with zero-variance safeguards.
- Cross-sectional market breadth calculation: advances, declines, unchanged counts, advance-decline ratio, breadth thrust, net advances, and 20-day SMA breadth participation percentage across equity universes.
- Strict session alignment preventing look-ahead bias and handling calendar discrepancies.

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
