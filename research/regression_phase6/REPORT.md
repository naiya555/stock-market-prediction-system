# Phase 6 Regime-Stratified Walk-Forward Residual Research

Previous-close predictions are evaluated out of sample in five chronological folds with a one-session embargo. Regime thresholds are derived from each fold's training history only.

## Overall out-of-sample residuals

| Instrument | OOS samples | MAE | RMSE | Residual std |
|---|---:|---:|---:|---:|
| BHARTIARTL | 1482 | 12.3051 | 17.8834 | 16.6950 |
| TCS | 1482 | 33.6974 | 46.6814 | 46.5908 |
| NIFTY_50 | 1486 | 131.2049 | 179.2862 | 178.1974 |
| NIFTY_TELECOMMUNICATIONS | 1486 | 25.7885 | 35.9964 | 35.3094 |

Highest residual variability: **NIFTY_50** (residual standard deviation 178.1974).

## Walk-forward interval coverage

Coverage below is weighted across folds 2-5; fold 1 is unavailable because fewer than 50 prior out-of-sample residuals existed.

| Instrument | 50% nominal | 80% nominal | 90% nominal | 95% nominal |
|---|---:|---:|---:|---:|
| BHARTIARTL | 0.3820 | 0.6425 | 0.7681 | 0.8541 |
| TCS | 0.5059 | 0.8002 | 0.8954 | 0.9384 |
| NIFTY_50 | 0.4693 | 0.7519 | 0.8545 | 0.9167 |
| NIFTY_TELECOMMUNICATIONS | 0.4256 | 0.7115 | 0.8343 | 0.9024 |

## Conclusions

1. High-volatility regimes explain larger out-of-sample baseline errors for all four instruments: BHARTIARTL 21.855 MAE vs 9.997 low-volatility, TCS 42.896 vs 26.391, NIFTY 50 183.684 vs 91.502, and Telecom 33.071 vs 17.353.
2. Trend-regime comparisons are reported separately and must be interpreted with group sample counts and fold stability.
3. NIFTY_50 has the highest residual variability in the common price units used by this audit.
4. Empirical intervals do not uniformly achieve nominal coverage: BHARTIARTL and NIFTY 50 are materially under-covered, while TCS is closest to nominal.
5. Regime information explains error heterogeneity but provides no evidence to change the production baseline or integrate uncertainty bands.

## Limitations

- Residuals are from the previous-close baseline, not a learned model.
- First-fold intervals may be unavailable until 50 prior residuals exist.
- Regime labels are coarse and threshold-dependent.
- No statistical significance test or multiple-comparison correction is applied.