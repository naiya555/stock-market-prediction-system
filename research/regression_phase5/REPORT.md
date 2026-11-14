# Phase 5 Data Quality, Feature Validity and Market-Regime Audit

Production code, APIs, dashboard, database, and Phase 2-4 artifacts were not modified.

## Measurement summary

| Instrument | Sessions | Rejected | Weekend records | Missing OHLC rows | Return mean | Return std | Lag-1 autocorrelation | Baseline MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BHARTIARTL | 2471 | 0 | 3 | 0 | 0.000983 | 0.018173 | -0.037734 | 9.8319 |
| TCS | 2471 | 0 | 3 | 0 | 0.000437 | 0.015360 | -0.024142 | 28.8500 |
| NIFTY_50 | 2478 | 0 | 10 | 0 | 0.000511 | 0.010200 | -0.038786 | 109.2943 |
| NIFTY_TELECOMMUNICATIONS | 2478 | 0 | 10 | 2478 | 0.000556 | 0.015783 | -0.001841 | 21.3377 |

## Conclusions

1. Historical data is structurally usable after the existing cleaner, but this audit cannot verify provider corporate-action adjustments or independent source agreement.
2. Canonical close-to-close features are classified SAFE for prediction at session close. They are not valid for same-session opening targets; no direct future-information path was detected.
3. Regimes are reproducibly defined by 20-session volatility, 20-session return slope, and drawdown thresholds recorded in regime_analysis.json.
4. Previous-close is difficult to beat because one-session returns have limited serial dependence while price-level errors scale with volatility and price level.
5. Instrument-specific volatility and regime counts support separate strategy evaluation rather than one universal model.
6. Only descriptive baseline residual intervals are available. They are not validated model confidence intervals.

## Limitations and unresolved issues

- Weekend records and long gaps are reported as observed provider anomalies and were not removed or corrected.
- Equity corporate actions and adjusted-versus-unadjusted consistency remain UNVERIFIABLE without an independent source and metadata.
- The feature audit is based on source and transformation inspection; it is not a formal symbolic execution proof.
- The empirical interval coverage is descriptive in-sample baseline coverage, not calibrated out-of-sample model coverage.

See JSON and CSV artifacts for per-instrument measurements, exclusions, regime counts, feature classifications, and uncertainty limitations.