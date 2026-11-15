# Snapshot Equivalence Audit Report: NIFTY 50

## 1. Executive Summary and Final Verdict

**Audit Verdict:** `PARTIAL_MATCH`

The November 15, 2026 frozen provider snapshots are **not an exact match** to the earlier November 14, 2026 snapshot in date sets or row counts. However, they are also **not a count-only match**: for every overlapping date between the two snapshots, **the close values are 100.0% numerically identical with zero price drift** across both providers.

The November 15 snapshot represents an **expanded, verified superset** of the November 14 snapshot:
1. It adds 10 earlier trading sessions (`2016-11-01` to `2016-11-15`) due to an explicit requested start date of 2016-11-01 (instead of dynamic `now() - 3650 days`).
2. On `2016-11-16`, the NSE Indices endpoint delivered an observation (`8111.60`) that was missing in the November 14 retrieval, resolving that date into an overlapping match with Yahoo Finance.
3. Every single historical close price for all 2,478 shared NSE dates and all 2,466 shared Yahoo dates matches exactly between the November 14 and November 15 snapshots.

---

## 2. Historical Source Artifacts Inspected

| Snapshot | Artifact Path | Retrieval Date | Format & Content |
|---|---|---|---|
| **Earlier Snapshot** | [`research/data_verification_remediation/price_reconciliation.csv`](file:///D:/Share_market_predictor/research/data_verification_remediation/price_reconciliation.csv)<br>Accompanied by:<br>- [`targeted_audit/nifty50_unmatched_dates.csv`](file:///D:/Share_market_predictor/research/data_verification_remediation/targeted_audit/nifty50_unmatched_dates.csv)<br>- [`complete_source_verification/reconciliation_summary.json`](file:///D:/Share_market_predictor/research/data_verification_remediation/complete_source_verification/reconciliation_summary.json) | 2026-11-14 | 2,479 rows for NIFTY_50.<br>Contains `date`, `primary_close` (NSE), `secondary_close` (Yahoo), and reconciliation `status`.<br>*Limitation:* Full OHLCV (open, high, low, volume) was not persisted as separate raw CSVs in the Nov 14 audit. |
| **Current Frozen Snapshot** | [`research/datasets/nifty50/nifty50_nse_indices_raw.csv`](file:///D:/Share_market_predictor/research/datasets/nifty50/nifty50_nse_indices_raw.csv)<br>[`research/datasets/nifty50/nifty50_yahoo_raw.csv`](file:///D:/Share_market_predictor/research/datasets/nifty50/nifty50_yahoo_raw.csv)<br>[`research/datasets/nifty50/nifty50_aligned.csv`](file:///D:/Share_market_predictor/research/datasets/nifty50/nifty50_aligned.csv)<br>[`research/datasets/nifty50/dataset_manifest.json`](file:///D:/Share_market_predictor/research/datasets/nifty50/dataset_manifest.json) | 2026-11-15 | 2,489 rows in aligned and NSE raw; 2,476 rows in Yahoo raw.<br>Contains full OHLCV series, original precision, alignment differences, calendar classifications, and SHA-256 hashes. |

---

## 3. Date Set and Record Count Comparison

| Metric | November 14 Snapshot | November 15 Frozen Snapshot | Difference / Finding |
|---|---|---|---|
| **Date Range Covered** | 2016-11-16 to 2026-11-13 | 2016-11-01 to 2026-11-13 | Nov 15 extends 10 trading days earlier |
| **Total Unique Dates** | 2,479 | 2,489 | +10 dates |
| **NSE Indices Record Count** | 2,478 | 2,489 | +11 dates (+10 earlier + 1 on 2016-11-16) |
| **Yahoo Finance Record Count** | 2,466 | 2,476 | +10 dates (+10 earlier) |
| **Overlapping Dates** | 2,465 | 2,476 | +11 dates (+10 earlier + 1 on 2016-11-16) |
| **Matched Within Tolerance** | 2,465 | 2,476 | 100% of overlapping dates match |
| **Price Mismatches** | 0 | 0 | 0 mismatches in both |
| **NSE-Only Dates** | 13 | 13 | Exactly identical 13 dates |
| **Yahoo-Only Dates** | 1 (`2016-11-16`) | 0 | Resolved by NSE data presence |

---

## 4. Record-Level Price Comparison on Overlapping Dates

To determine whether the snapshots are genuinely equivalent or merely count-aligned, every common observation was compared:

1. **NSE Indices Overlap (2,478 common trading dates):**
   - Exact price matches (`abs(diff) < 1e-4`): **2,478 (100.0%)**
   - Price discrepancies: **0**
   - Max absolute difference: **0.00000000**
2. **Yahoo Finance Overlap (2,466 common trading dates):**
   - Exact price matches (`abs(diff) < 1e-4`): **2,466 (100.0%)**
   - Price discrepancies: **0**
   - Max absolute difference: **0.00000000**

This confirms that the underlying historical price series retrieved on November 15 is identical to the series retrieved on November 14. There has been no revision or drift of past index levels by either provider.

---

## 5. In-Depth Analysis of 2016-11-16

Date `2016-11-16` exhibited divergent provider behavior across the two snapshots:

- **November 14 Retrieval:**
  - Query parameters: `START = now() - timedelta(days=3650)`.
  - Date `2016-11-16` was the exact boundary start date.
  - NSE Indices provider returned records starting on `2016-11-17`, omitting `2016-11-16` (`status = MISSING_FROM_PRIMARY`).
  - Yahoo Finance returned `2016-11-16` with close `8111.60009765625`.
  - Resulted in 14 unmatched dates (13 NSE-only + 1 Yahoo-only).
- **November 15 Retrieval:**
  - Query parameters: `START = 2016-11-01`.
  - Date `2016-11-16` fell well inside the query range.
  - NSE Indices provider returned `2016-11-16` with close `8111.60`.
  - Yahoo Finance returned `2016-11-16` with close `8111.60009765625` (identical to Nov 14).
  - Absolute difference: `0.00009765625` (well within 0.01 tolerance).
  - Resulted in `MATCHED` status between providers, reducing unmatched dates to 13.
- **Calendar Verification Status:**
  - Despite data presence in both providers, `2016-11-16` remains **UNVERIFIED** for official capital-market calendar classification (Circular NSE/CMTR/31297 verifies the Nov 14 holiday but does not explicitly verify the Nov 16 trading session).
  - Handled per the frozen inclusion policy as `EXCLUDED_UNRESOLVED_CALENDAR`.

---

## 6. Date Set Differences (The 11 Divergent Dates)

Documented in [`date_set_differences.csv`](file:///D:/Share_market_predictor/research/datasets/nifty50/snapshot_audit/date_set_differences.csv):

1. **10 Pre-Start Dates (`NEW_DATE_IN_NOV15_PRE_START`):**
   - Dates: `2016-11-01`, `2016-11-02`, `2016-11-03`, `2016-11-04`, `2016-11-07`, `2016-11-08`, `2016-11-09`, `2016-11-10`, `2016-11-11`, `2016-11-15`.
   - Reason: Requested query boundary difference (`2016-11-01` in Nov 15 vs. `2016-11-16` in Nov 14). Both providers contain data and match within tolerance on all 10 dates.
2. **1 Endpoint Coverage Change (`ENDPOINT_COVERAGE_CHANGE_20161116`):**
   - Date: `2016-11-16`.
   - Reason: ASMX endpoint query boundary variation. Absent in Nov 14; present and matching Yahoo Finance in Nov 15.

There are **zero dates missing** in the November 15 snapshot that were present in the November 14 snapshot.

---

## 7. Retrieval Timestamps and Provenance

- **Earlier Snapshot Retrieval:** 2026-11-14 (per `research/data_verification_remediation/source_manifest.json`).
- **Frozen Snapshot Retrieval:** 2026-11-15 (per `research/datasets/nifty50/dataset_manifest.json`).
- **Sub-Second Provenance Limitation:** Upstream providers (NSE Indices ASMX service and Yahoo Finance daily bars) do not supply bar-level upstream ingestion timestamps. Only daily dates are provided.
- **Raw OHLCV Limitation:** The November 14 audit did not persist separate raw OHLCV CSVs (only the reconciled close series in `price_reconciliation.csv` was preserved). Full OHLCV equivalence is therefore only verifiable on close prices.

---

## 8. Verdict Justification

- **Why not `EXACT_MATCH`:** The snapshots have different date ranges (2016-11-01 vs 2016-11-16), different row counts (2,489 vs 2,478 for NSE), and differing provider coverage on 2016-11-16.
- **Why not `COUNT_ONLY_MATCH`:** The agreement is not merely superficial row counts. In fact, the counts differ, but every single overlapping price matches with 100.0% precision across 2,478 NSE and 2,466 Yahoo observations.
- **Why not `NOT_VERIFIABLE`:** Historical close prices from November 14 are fully preserved in `price_reconciliation.csv` and are completely auditable.
- **Why `PARTIAL_MATCH`:** The November 15 frozen dataset is a verified, expanded superset that preserves exact numerical equivalence on all shared dates while transparently extending coverage and incorporating the updated endpoint response on 2016-11-16.
