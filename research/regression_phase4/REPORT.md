# Phase 4 Forecasting Strategy and Target Optimization

Isolated target/horizon research. Production prediction routes, dashboard code, model artifacts, and database records were not modified.

Acceptance requires lower MAE and RMSE than the previous-close baseline in every fold, using identical validation dates.

## Availability

- NumPy linear/Ridge, XGBoost, LightGBM, exponential smoothing: evaluated.
- Random Forest, Extra Trees, HistGradientBoosting and ARIMA: not evaluated because their dependencies are not installed.
- XGBoost and LightGBM experiments used CPU execution; no GPU acceleration was claimed.

## Decisions

| Instrument | Target | Horizon | Best candidate | Mean MAE | Baseline MAE | Consistent |
|---|---|---:|---|---:|---:|---|
| BHARTIARTL | return_1 | 1 | xgboost | 0.0108 | 0.0106 | REJECT |
| TCS | return_1 | 1 | ridge | 0.0107 | 0.0103 | REJECT |
| NIFTY_50 | return_1 | 1 | xgboost | 0.0067 | 0.0065 | REJECT |
| NIFTY_TELECOMMUNICATIONS | return_1 | 1 | ridge | 0.0108 | 0.0107 | REJECT |

## Recommendations

No target/horizon/model should be integrated into production unless it passes the all-fold MAE/RMSE gate and a separate production review.