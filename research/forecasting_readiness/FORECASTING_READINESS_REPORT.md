# Instrument Forecasting Readiness

## Evidence basis

This assessment uses the existing regression Phases 2–6, source verification,
Phase 8/8.1 diagnostics, complete-source-verification artifacts, data-quality
baseline, and the new cached NSE adapter. No new forecasting experiment was run.

## Decisions

| Instrument | Level | Main reason |
|---|---|---|
| BHARTIARTL | NOT_READY | No independent price reconciliation, incomplete corporate-action ledger, and unresolved calendar evidence. |
| TCS | NOT_READY | No independent price reconciliation, incomplete corporate-action ledger, and unresolved calendar evidence. |
| NIFTY 50 | PARTIALLY_READY | 2,465 comparable rows match, but six dates remain unresolved and 14 unmatched dates need explicit treatment. |
| NIFTY TELECOMMUNICATIONS | NOT_READY | No independent equivalent series; close-only source and calendar evidence remain limited. |

`RESEARCH_READY` requires clean sufficient observations, defensible session
classification, target/source treatment, leakage audit, identical-date
baseline comparison, and reproducible walk-forward metrics. None of the four
instruments currently satisfies every gate. `PRODUCTION_READY` additionally
requires independently reviewed superiority, calibrated uncertainty,
operational monitoring, and explicit approval.

The minimum conditions and production blockers are in
`remaining_blockers.csv`. Forecasting remains on hold.
