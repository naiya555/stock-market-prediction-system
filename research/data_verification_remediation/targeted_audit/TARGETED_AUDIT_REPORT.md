# Targeted Remediation Audit

## Residual provenance

The remediation `residual_diagnostics.json` is **VERIFIED as full-sample**, not genuinely out-of-sample: it was produced from fresh cleaned provider closes and computes consecutive close differences across the full series. Its BHARTIARTL MAE 9.8318989 and 2470 samples match Phase 5's full-sample baseline exactly. Phase 6 is the separate genuinely out-of-sample population: five chronological validation folds, one-session embargo, 1482 BHARTIARTL validation residuals, and fold-specific training thresholds.

Every recorded baseline residual is `actual close[t] - previous close[t-1]`; the previous close precedes the target. The remediation full-sample statistic is descriptive and must not be called an OOS estimate.

## BHARTIARTL regime discrepancy

The discrepancy is **not a calculation error in either artifact**. Remediation uses full-sample volatility quartiles and all 2470 residuals: high MAE 8.76498, low 9.64298, normal 10.55047. Phase 6 uses only 1482 OOS residuals and derives volatility thresholds separately from each fold's training history; its comparable metrics are high MAE 21.8548 from 15 rows, low 9.9971 from 822, normal 15.0244 from 645. These are different samples and labels. The Phase 6 high-volatility BHARTIARTL group is extremely small, so its result is unstable. The earlier broad claim “high volatility was larger for all four” is true for the Phase 6 OOS aggregates, not for the full-sample remediation population.

## NIFTY 50 unmatched dates

The 14 rows are listed in `nifty50_unmatched_dates.csv`. Weekend dates are classified as non-weekday observations, but special-session status was not independently verified. Weekday gaps and the 2016 start-date gap remain source coverage or calendar possibilities marked UNVERIFIED; no missing values were fabricated.

## Corporate actions

BHARTIARTL and TCS remain **UNVERIFIED**. NSE/BSE evidence retrieval was unavailable, so no split, bonus, dividend, ex-date, record-date, or adjustment factor is asserted. The project Yahoo adapter's raw/unadjusted convention is known, but that does not verify corporate-action history.

## Final status

No methodology defect was found or corrected. All four instruments remain **PARTIALLY VERIFIED** and not ready for a new forecasting experiment. Residual independence remains unproven; formal Ljung–Box was unavailable. No production or prior research artifact was modified.
