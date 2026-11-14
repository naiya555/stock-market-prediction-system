# Complete Independent Market-Data Verification

## Overall decision

**NO — the historical datasets are not sufficiently independently verified to resume forecasting experiments.** NIFTY 50 has strong row-level agreement on 2,465 comparable observations. Of the 14 unmatched dates, eight are now independently confirmed NSE special sessions and six remain unresolved. Complete corporate-action histories and independent equity price series remain unavailable, and no independent equivalent NIFTY Telecommunications series was obtained.

## Readiness

| Instrument | Status | Evidence |
|---|---|---|
| BHARTIARTL | PARTIALLY_VERIFIED | Two official dividend record-date filings plus secondary corroboration; this is partial event evidence, not a complete ledger. |
| TCS | PARTIALLY_VERIFIED | Three official dividend filings plus secondary bonus/split/rights corroboration; this is partial event evidence, not a complete ledger. |
| NIFTY 50 | PARTIALLY_VERIFIED | 2,465/2,465 comparable rows matched within tolerance; 8 special sessions verified and 6 dates remain unresolved. |
| NIFTY TELECOMMUNICATIONS | UNVERIFIED | No independent equivalent historical series obtained. |

## Corporate actions

The corporate-action CSVs contain **partial event evidence**, not complete corporate-action ledgers. Official NSE filings verify the listed BHARTIARTL and TCS dividend record-date events. BSE search-result evidence corroborates selected BHARTIARTL dividends, while secondary Trendlyne evidence reports a TCS 1:1 bonus and no split/rights history; these secondary rows are explicitly not treated as official verification. Complete 2016–2026 split, bonus, rights, merger, demerger, dividend ex-date, and adjustment-factor coverage remains unresolved. No adjustment factor was inferred. The project's Yahoo adapter requests `auto_adjust=False`; this documents the requested raw/unadjusted mode, but no complete independent price comparison proves continuity around every event.

## NIFTY 50 unmatched dates

The 14 unmatched dates are divided as follows:

- **8 independently verified NSE special sessions:** 2019-10-27, 2020-02-01, 2020-11-14, 2023-11-12, 2024-01-20, 2024-03-02, 2024-05-18, and 2026-11-08.
- **6 unresolved dates:** 2016-11-16, 2018-01-01, 2019-01-01, 2019-02-13, 2019-03-29, and 2026-02-01.

The six unresolved dates remain unclassified because the retrieved official evidence did not establish a regular session, holiday, special session, or source-coverage explanation. Missing values were not fabricated.

## NIFTY Telecommunications

The official NSE Indices endpoint confirms the index identity and methodology, but it is the project's existing source, not an independent series. Search results for other pages were different indices or non-comparable analytics pages. Consequently, comparable, matched, mismatched, and coverage counts against an independent series are zero/unavailable, not zero discrepancies.

## Corrections and safety

No historical data was changed. Proposed corrections are documentation-only. No forecasting experiment, model training, production/API/frontend change, database change, package installation, staging, commit, or push was performed.

See the accompanying CSV/JSON artifacts for source URLs, retrieval date, evidence class, tolerances, limitations, and reconciliation counts. The NIFTY 50 reconciliation fields are `total_unmatched_dates=14`, `verified_special_sessions=8`, and `unresolved_dates=6`.
