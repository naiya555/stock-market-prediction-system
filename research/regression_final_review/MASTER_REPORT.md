# Combined Research Review: Phases 2-7

## Executive summary

Phases 2-4 tested return, feature/model, target, and horizon alternatives. No candidate consistently beat previous-close on both MAE and RMSE in every chronological fold. Phase 5 found structurally usable provider data and no classified feature leakage, but independent price and corporate-action verification remained unresolved. Phase 6 confirmed materially larger previous-close residuals in high-volatility regimes, while its empirical intervals were not uniformly calibrated.

Historical data is **PARTIALLY VERIFIED**, not fully verified. The evaluation methodology is **PARTIALLY VERIFIED**: target alignment, chronological folds, baseline alignment, and Phase 6 prior-out-of-sample residual history are supported; formal preprocessing-contamination and residual-independence proofs were not completed.

No instrument has an accepted numerical model. Continue using the previous-close baseline (Recommendation D) for all four instruments. Resolve independent data/corporate-action verification before another isolated forecasting experiment.

## Phase findings

- **Phase 2:** XGBoost and LightGBM next-session-return models were rejected because fold-consistent MAE/RMSE superiority was absent.
- **Phase 3:** Ridge/linear, XGBoost, LightGBM, exponential smoothing, volatility-adjusted models, and richer return/volatility/momentum/context features were evaluated where dependencies allowed; all failed the gate. Random Forest, Extra Trees, HistGradientBoosting, and ARIMA were skipped because dependencies were not installed.
- **Phase 4:** One-, three-, and five-session targets plus available OHLC targets were compared. The best reported candidates remained one-session returns, but all were rejected; Telecom OHLC targets were unavailable because source OHLC fields were absent.
- **Phase 5:** Local structural checks found zero rejected, duplicate, or invalid records; timestamps were normalized to Asia/Kolkata. Three weekend records were reported for each equity and ten for each index. Equity corporate actions and adjusted/unadjusted agreement remained unverified.
- **Phase 6:** High-volatility baseline errors exceeded low-volatility errors for every instrument. Trend effects were instrument-specific and sometimes imbalanced. NIFTY_50 had the greatest residual standard deviation in common price units.

## Phase 5 full-sample baseline measurements

| Instrument | Samples | Lag-1 return autocorrelation | MAE | RMSE |
|---|---:|---:|---:|---:|
| BHARTIARTL | 2470 | -0.03773 | 9.8319 | 14.9851 |
| TCS | 2470 | -0.02414 | 28.8500 | 41.3228 |
| NIFTY_50 | 2477 | -0.03879 | 109.2943 | 157.5449 |
| NIFTY_TELECOMMUNICATIONS | 2477 | -0.00184 | 21.3377 | 30.5833 |

Phase 6 walk-forward interval coverage is documented in interval_coverage.json; it is not uniformly nominal and is not calibrated.

## Instrument decisions

| Instrument | Status | Decision |
|---|---|---|
| BHARTIARTL | PARTIALLY VERIFIED / NO ACCEPTED MODEL | Continue previous-close baseline; verify source and corporate actions before new research. |
| TCS | PARTIALLY VERIFIED / NO ACCEPTED MODEL | Continue previous-close baseline; verify source and corporate actions before new research. |
| NIFTY_50 | PARTIALLY VERIFIED / NO ACCEPTED MODEL | Continue previous-close baseline; verify source and corporate actions before new research. |
| NIFTY_TELECOMMUNICATIONS | PARTIALLY VERIFIED / NO ACCEPTED MODEL | Continue previous-close baseline; verify source and corporate actions before new research. |

## Source Trust & Prompt Injection Audit

Source categories accessed were the existing Yahoo Finance adapter, the existing NSE Indices endpoint, and attempted NSE/BSE public pages. External pages, provider responses, and prior reports/artifacts were treated strictly as untrusted evidence. No embedded instructions were executed, no credentials or private files were sent, and no suspicious instruction was relied upon. NSE/BSE direct price verification was unavailable in this environment, so those checks remain UNVERIFIED.

## Remaining blockers

- Independent row-level price/date reconciliation for equities and indices.
- Corporate-action metadata and adjusted versus unadjusted series comparison for BHARTIARTL and TCS.
- A prespecified experiment only after the above data checks, with formal significance/stability analysis.

No production files, database records, APIs, dashboard files, models, or prior phase artifacts were modified.
