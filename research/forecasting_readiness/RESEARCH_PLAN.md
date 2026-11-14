# Numerical Forecasting Research Plan

No experiments are executed by this task.

1. **Finalize data and targets.** Define next-session close, open, return, and
   multi-session targets separately. Use only close/return targets for the
   close-only telecommunications index.
2. **Revalidate the benchmark.** Use previous available close for close
   forecasts and 0% for return forecasts on identical chronological dates.
   Report fold-level MAE, RMSE, MAPE where meaningful, and directional accuracy.
3. **Run isolated candidates.** Evaluate Ridge/linear regression, XGBoost,
   LightGBM, and an appropriate smoothing/ARIMA method per instrument.
4. **Walk forward by regime.** Use chronological folds, embargo, fold-level
   metrics, trend/sideways/high-volatility groups, residual autocorrelation,
   and heteroscedasticity diagnostics.
5. **Calibrate uncertainty.** Measure interval coverage and width; label
   descriptive residual intervals separately from calibrated prediction
   intervals.
6. **Accept conservatively.** A candidate must beat the previous-close
   benchmark consistently across prespecified folds and important metrics,
   without material deterioration elsewhere. Otherwise retain the baseline.

Every run must be isolated under `research/`, preserve raw data, record
versions and hashes, and receive separate review before any production change.
