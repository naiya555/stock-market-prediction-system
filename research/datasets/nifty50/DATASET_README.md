# NIFTY 50 Frozen Research Dataset

## Overview

This directory contains the canonical, frozen research-only historical dataset for the **NIFTY 50** benchmark index, spanning **2016-11-01** to **2026-11-13** (requested coverage through 2026-11-15).

This dataset is strictly for reproducibility, data provenance, and quality auditing. **Forecasting experiments remain on hold.**

---

## 1. Provenance and Source Providers

Both raw source snapshots were reproducibly retrieved on **2026-11-15** using the project's verified provider adapters:

| Provider | Role | Adapter / Endpoint | Symbol / Ticker | Actual Trading Dates | Record Count |
|---|---|---|---|---|---|
| **NSE Indices Limited** | Primary Official Index Provider | `NiftyIndicesProvider`<br>`https://www.niftyindices.com/BackPage/getHistoricaldatatabletoString` | `NIFTY_50` (`Nifty 50`) | 2016-11-01 to 2026-11-13 | 2,489 |
| **Yahoo Finance** | Secondary Cross-Validation Provider | `YFinanceProvider`<br>`yfinance.Ticker` | `^NSEI` | 2016-11-01 to 2026-11-13 | 2,476 |

- **Preservation of Raw Snapshots:** The raw files `nifty50_nse_indices_raw.csv` and `nifty50_yahoo_raw.csv` preserve original provider fields and floating-point precision exactly as delivered by the provider adapters.
- **Zero Modification / Interpolation:** No prices are fabricated, forward-filled, interpolated, or averaged. Sources are preserved separately.

---

## 2. Dataset Files and Directory Structure

| File | Description | Records |
|---|---|---|
| [`nifty50_nse_indices_raw.csv`](file:///D:/Share_market_predictor/research/datasets/nifty50/nifty50_nse_indices_raw.csv) | Exact raw OHLCV series from official NSE Indices provider | 2,489 rows |
| [`nifty50_yahoo_raw.csv`](file:///D:/Share_market_predictor/research/datasets/nifty50/nifty50_yahoo_raw.csv) | Exact raw OHLCV series from secondary Yahoo Finance provider | 2,476 rows |
| [`nifty50_aligned.csv`](file:///D:/Share_market_predictor/research/datasets/nifty50/nifty50_aligned.csv) | Canonical outer-joined comparison dataset with differences, availability, calendar status, and inclusion policy | 2,489 rows |
| [`excluded_observations.csv`](file:///D:/Share_market_predictor/research/datasets/nifty50/excluded_observations.csv) | Full register of all 14 excluded / unavailable / unresolved observations with official evidence and rationales | 14 rows |
| [`dataset_manifest.json`](file:///D:/Share_market_predictor/research/datasets/nifty50/dataset_manifest.json) | Comprehensive machine-readable metadata, column schemas, and alignment rules | JSON |
| [`alignment_summary.json`](file:///D:/Share_market_predictor/research/datasets/nifty50/alignment_summary.json) | Summary record counts, reconciliation metrics, and calendar breakdown | JSON |
| [`hash_manifest.json`](file:///D:/Share_market_predictor/research/datasets/nifty50/hash_manifest.json) | Cryptographic SHA-256 digests of all frozen files | JSON |
| [`dataset_quality_report.json`](file:///D:/Share_market_predictor/research/datasets/nifty50/dataset_quality_report.json) | Automated quality audit report covering integrity, tolerance, schemas, and ordering | JSON |
| [`verify_dataset.py`](file:///D:/Share_market_predictor/research/datasets/nifty50/verify_dataset.py) | Standalone verification script that recalculates hashes and validates all quality checks | Python |
| [`FINAL_READINESS_DECISION.md`](file:///D:/Share_market_predictor/research/datasets/nifty50/FINAL_READINESS_DECISION.md) | Formal readiness reassessment and gating decision | Markdown |

---

## 3. Date Alignment and Reconciliation Rules

- **Alignment Key:** Explicit trading date (`YYYY-MM-DD`).
- **Reconciliation Tolerance:**
  - Absolute tolerance: **0.01**
  - Relative tolerance: **0.0001 (0.01%)**
- **Match Condition:** `abs_diff <= 0.01 OR rel_diff <= 0.0001`.
- **Reconciliation Outcome:**
  - Total unique trading dates: **2,489**
  - Overlapping dates: **2,476**
  - Matched observations within tolerance: **2,476 (100.0% of overlaps)**
  - Mismatches: **0**
  - NSE-only dates: **13**
  - Yahoo-only dates: **0**

---

## 4. Treatment of Unmatched and Unresolved Observations

### A. The 13 NSE-Only Observations
All 13 NSE-only observations are omitted by Yahoo Finance and therefore lack secondary price corroboration:
1. **9 Officially Verified Special Sessions (`EXCLUDED_SECONDARY_UNAVAILABLE_SPECIAL_SESSION`):**
   - `2019-10-27` (Diwali Muhurat, NSE/CMTR/42483)
   - `2020-02-01` (Union Budget Saturday Session, NSE/FAOP/43291)
   - `2020-11-14` (Diwali Muhurat, NSE/CMTR/46230)
   - `2023-11-12` (Diwali Muhurat, NSE/CMTR/59124)
   - `2024-01-20` (Disaster Recovery site switch live session, NSE/MSD/59999)
   - `2024-03-02` (Disaster Recovery site switch live session, NSE/MSD/60677)
   - `2024-05-18` (Special Live Trading Session, NSE/MSD/62061)
   - `2026-02-01` (Union Budget Sunday Live Session, NSE/CMTR/72349)
   - `2026-11-08` (Diwali Muhurat, NSE/CMTR/76941)
2. **4 Unverified Weekday Observations (`EXCLUDED_SECONDARY_UNAVAILABLE_UNVERIFIED`):**
   - `2018-01-01` (Monday, Close: 10435.55, NSE/CMTR/36475)
   - `2019-01-01` (Tuesday, Close: 10910.10, NSE/CMTR/39612)
   - `2019-02-13` (Wednesday, Close: 10793.65, NSE/CMTR/39612)
   - `2019-03-29` (Friday, Close: 11623.90, NSE/CMTR/39612)

### B. The Five Documented Unresolved Dates
The five unresolved dates identified in prior research are treated with full transparency:
- `2016-11-16`: Both providers have prices (NSE 8111.60, Yahoo 8111.600098) that match within tolerance, but capital-market session classification is UNVERIFIED and the prior 2026-11-14 snapshot lacked the NSE observation. Excluded (`EXCLUDED_UNRESOLVED_CALENDAR`).
- `2018-01-01`: NSE only; Yahoo missing; calendar UNVERIFIED (`EXCLUDED_SECONDARY_UNAVAILABLE_UNVERIFIED`).
- `2019-01-01`: NSE only; Yahoo missing; calendar UNVERIFIED (`EXCLUDED_SECONDARY_UNAVAILABLE_UNVERIFIED`).
- `2019-02-13`: NSE only; Yahoo missing; calendar UNVERIFIED (`EXCLUDED_SECONDARY_UNAVAILABLE_UNVERIFIED`).
- `2019-03-29`: NSE only; Yahoo missing; calendar UNVERIFIED (`EXCLUDED_SECONDARY_UNAVAILABLE_UNVERIFIED`).

---

## 5. Transparent Inclusion / Exclusion Policy

| Inclusion Status | Count | Description |
|---|---|---|
| `INCLUDED` | **2,475** | Dual-source verified observations matching within documented tolerance without unresolved calendar blockers. |
| `EXCLUDED_UNRESOLVED_CALENDAR` | **1** | Overlapping match (`2016-11-16`) where official trading session circular is unverified and snapshot history had coverage variation. |
| `EXCLUDED_SECONDARY_UNAVAILABLE_SPECIAL_SESSION` | **9** | Verified official NSE special sessions where Yahoo Finance coverage is absent. |
| `EXCLUDED_SECONDARY_UNAVAILABLE_UNVERIFIED` | **4** | NSE-only weekday sessions where Yahoo Finance coverage is absent and official session evidence is not established. |
| **Total** | **2,489** | Complete outer-join coverage across both provider snapshots. |

---

## 6. SHA-256 Hash Manifest

| File | SHA-256 Digest |
|---|---|
| `nifty50_nse_indices_raw.csv` | `fd65f0dad5fb81c2f693df8c423447067ca9240584913881b3b6cf85b04af4c1` |
| `nifty50_yahoo_raw.csv` | `dae00e6673cdc8f1768b8d92886798221662a8d2d30de9d97d1561194fa87e55` |
| `nifty50_aligned.csv` | `9fc9bdf536c3402c8fe0e9ed7f1eea4723cb19d6a841824b4480f781143bb869` |
| `excluded_observations.csv` | `1547ae741481d2eb4b4e7c0e418e57430ae366797325bb43ba4fcb743b94cb0c` |
| `dataset_manifest.json` | `95a91a3f5fbd8ed5dff70d6eb6162206b3d9042224f60b9c1d2a64cb5783d233` |

---

## 7. Running Verification

To independently recalculate SHA-256 digests and rerun all dataset quality checks:

```powershell
.\.venv\Scripts\python.exe research/datasets/nifty50/verify_dataset.py
```
