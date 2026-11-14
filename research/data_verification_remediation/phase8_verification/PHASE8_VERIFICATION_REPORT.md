# Phase 8 Independent Data & Statistical Verification

## Results

- **BHARTIARTL:** PARTIALLY VERIFIED. One official NSE dividend record-date filing was accessible; complete corporate-action and adjustment history remains UNVERIFIED.
- **TCS:** PARTIALLY VERIFIED. An NSE corporate-actions search result exposed an interim-dividend listing; complete event and adjustment history remains UNVERIFIED.
- **NIFTY 50 unmatched dates:** All 14 remain UNVERIFIED as regular/special/holiday sessions because an official session-calendar record was not accessible. Weekend status is observable from the date, but special-session validity was not asserted.
- **NIFTY Telecommunications:** UNVERIFIED for independent reconciliation. The existing official series was available, but no exact-index independent overlapping series was accessible.

## Residual independence

Phase 6-style OOS residuals were recomputed from the existing provider pipeline using previous-close predictions and five chronological folds. Ljung–Box tests at lags 5, 10, and 20 were calculated with SciPy. Results, fold stability, ACFs, p-values, and sample sizes are in `residual_independence_tests.json`.

| Instrument | OOS samples | Ljung–Box p(5) | p(10) | p(20) | 0.05 result |
|---|---:|---:|---:|---:|---|
| BHARTIARTL | 1482 | 0.366091 | 0.063617 | 0.009888 | reject at lag 20 |
| TCS | 1482 | 0.884189 | 0.842017 | 0.940556 | do not reject |
| NIFTY_50 | 1486 | 0.241025 | 0.362810 | 0.480357 | do not reject |
| NIFTY_TELECOMMUNICATIONS | 1486 | 0.278828 | 0.282988 | 0.482934 | do not reject |

The tests assess serial autocorrelation only. A non-significant result does not prove independence, and temporal residuals remain subject to heteroscedasticity and regime dependence.

## Remaining blockers

- Complete official corporate-action histories and adjustment factors for both equities.
- Official session-calendar verification for all 14 NIFTY 50 dates.
- An exact-index independent NIFTY Telecommunications series.
- Residual independence is not established by Ljung–Box alone.

No production, database, model, prior research, or targeted-audit artifact was modified.
