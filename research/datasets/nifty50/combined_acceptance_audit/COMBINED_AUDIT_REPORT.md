# NIFTY 50 Combined Research Acceptance & Validation Audit

## Executive Summary

This report documents the coordinated, read-only research audit of the **NIFTY 50** historical dataset, executed strictly following the mandatory 6-stage sequence.

- **Final Readiness Verdict:** **`PARTIALLY_READY`** (Promotion to `RESEARCH_READY` is **DENIED**).
- **Core Strengths:** 2,475 clean, contiguous, dual-source verified observations matching within 0.01 / 0.0001 tolerance (0 price discrepancies across 2,478 shared NSE dates and 2,466 shared Yahoo dates); verified causal feature engineering; verified chronological expanding-window walk-forward splits; robust baseline specifications.
- **Key Blockers:** 5 dates remain unverified for official capital-market equity session classification; Yahoo Finance omits 13 dates (including 9 verified special sessions); earlier Nov 14 raw OHLCV files were not archived; cross-asset constituents (BHARTIARTL, TCS, NIFTY Telecommunications) remain uncorroborated.

---

## Stage 1 — Historical Snapshot Equivalence Audit

### 1. Verdict Confirmation
The verdict **`PARTIALLY_MATCH`** established in [`snapshot_audit/SNAPSHOT_EQUIVALENCE_REPORT.md`](file:///D:/Share_market_predictor/research/datasets/nifty50/snapshot_audit/SNAPSHOT_EQUIVALENCE_REPORT.md) is **CONFIRMED**.

- **Closing Price Identity:** Across all 2,478 shared NSE dates and all 2,466 shared Yahoo dates between the November 14 and November 15 retrievals, the closing prices are **100.0% numerically identical** (0 discrepancies $> 1e-4$). Max absolute difference: **0.00000000**.
- **Date-Set Divergence (+11 dates):**
  - **10 Pre-Start Dates (`2016-11-01` to `2016-11-15`):** Requested start date in Nov 15 was fixed at `2016-11-01` rather than dynamic `now() - 3650 days`. Both providers have data matching within tolerance on all 10 dates.
  - **1 Endpoint Coverage Change (`2016-11-16`):** On Nov 14, NSE Indices ASMX backend omitted `2016-11-16` (start-of-query boundary omission). On Nov 15, the endpoint returned `8111.60`, matching Yahoo Finance (`8111.600098`) within tolerance.
- **Provenance Limitation:** Raw full OHLCV (open, high, low, volume) from the November 14 snapshot was not preserved as separate CSV files. Equivalence is verified on close prices.
- **Artifact Consistency:** Prior references to "2,465 matched" vs "2,476 matched" are fully reconciled by the 10 pre-start dates plus the resolution of `2016-11-16`.

---

## Stage 2 — Unresolved Dates Assessment

The five documented unresolved dates were reviewed individually against official exchange circulars and provider data:

| Date | Weekday | Provider Presence | Available Close | Official Status | Evidence Status | Circular / Reference | Decision | Target Impact |
|---|---|---|---|---|---|---|---|---|
| **2016-11-16** | Wednesday | Both Present | NSE: 8111.60<br>Yahoo: 8111.60 | `UNVERIFIED` | `UNVERIFIED` | Circular NSE/CMTR/31297 | `EXCLUDE` | Bridging across unverified date risks temporal ordering error |
| **2018-01-01** | Monday | NSE Only | NSE: 10435.55<br>Yahoo: None | `UNVERIFIED` | `UNVERIFIED` | Circular NSE/CMTR/36475 | `EXCLUDE` | Distorts 3-session and 5-session horizons across year-end |
| **2019-01-01** | Tuesday | NSE Only | NSE: 10910.10<br>Yahoo: None | `UNVERIFIED` | `UNVERIFIED` | Circular NSE/CMTR/39612 | `EXCLUDE` | Distorts multi-session forward return windows across year-end |
| **2019-02-13** | Wednesday | NSE Only | NSE: 10793.65<br>Yahoo: None | `UNVERIFIED` | `UNVERIFIED` | Circular NSE/CMTR/39612 | `EXCLUDE` | Mid-week gap shifts session index t+1 relative to external feeds |
| **2019-03-29** | Friday | NSE Only | NSE: 11623.90<br>Yahoo: None | `UNVERIFIED` | `UNVERIFIED` | Circular NSE/CMTR/39612 | `EXCLUDE` | Financial year-end week; affects Q4 FY19 boundary returns |

> [!CAUTION]
> In accordance with project standards, holiday circular omission and weekday status are **not** treated as positive evidence of a trading session. All 5 dates remain excluded from the verified research baseline.

---

## Stage 3 — Thirteen NSE-Only Observations Assessment

The 13 observations present in official NSE Indices but omitted by Yahoo Finance fall into two distinct groups:

### 1. Nine Officially Verified Special Sessions (`SPECIAL_SESSION`, `VERIFIED`)
- `2019-10-27` (Sunday, Diwali Muhurat, NSE/CMTR/42483)
- `2020-02-01` (Saturday, Union Budget, NSE/FAOP/43291)
- `2020-11-14` (Saturday, Diwali Muhurat, NSE/CMTR/46230)
- `2023-11-12` (Sunday, Diwali Muhurat, NSE/CMTR/59124)
- `2024-01-20` (Saturday, DR Site Switch, NSE/MSD/59999)
- `2024-03-02` (Saturday, DR Site Switch, NSE/MSD/60677)
- `2024-05-18` (Saturday, Special Live Session, NSE/MSD/62061)
- `2026-02-01` (Sunday, Union Budget, NSE/CMTR/72349)
- `2026-11-08` (Sunday, Diwali Muhurat, NSE/CMTR/76941)

**Microstructure & Target Impact:** These sessions have truncated duration (e.g. 60-min Muhurat sessions) and atypical liquidity. Merging them into standard daily series distorts rolling return volatility, ATR, and 1-session, 3-session, and 5-session forward targets. **Decision: Excluded from regular baseline modeling; designated for isolated regime research only (`ISOLATE_ONLY`).**

### 2. Four Unverified Weekday Observations (`UNVERIFIED`, `UNVERIFIED`)
- `2018-01-01`, `2019-01-01`, `2019-02-13`, `2019-03-29`
- Lacking both positive official session proof and secondary provider corroboration. **Decision: Excluded unconditionally.**

---

## Stage 4 — Frozen Dataset Leakage Audit

A comprehensive code and artifact inspection verified all 9 leakage vectors:

| Check ID | Vector | Implementation Reference | Evidence Status | Finding / Assessment |
|---|---|---|---|---|
| **LEAK-01** | Causal Feature Engineering | `app/training/feature_matrix.py#L54-L61` | `VERIFIED` | Target patterns strictly blacklisted from feature matrix X |
| **LEAK-02** | Rolling Window Isolation | `app/market/indicators.py#L75-L120` | `VERIFIED` | Indicators evaluate over closed past intervals ending at session t |
| **LEAK-03** | Target Shift & Alignment | `app/prediction/target.py#L7-L10` | `VERIFIED` | Target return formulated as $P_{t+1}/P_t - 1$; final row has `target = None` |
| **LEAK-04** | Verified Session Ordering | `app/prediction/target.py#L183-L188` | `PARTIALLY_VERIFIED` | Requires pre-filtering of 14 excluded dates prior to session indexing |
| **LEAK-05** | Chronological Splits | `app/training/walk_forward.py#L107-L136` | `VERIFIED` | Expanding-window walk-forward splits; zero temporal shuffling |
| **LEAK-06** | Preprocessing Isolation | `app/training/feature_matrix.py#L19-L21` | `VERIFIED` | Scaling/imputation transformers fitted strictly on training folds |
| **LEAK-07** | Embargo Enforcement | `app/training/walk_forward.py#L102` | `VERIFIED` | Enforces $\ge 1$ session embargo for $h=1$; must be $\ge h$ for multi-step |
| **LEAK-08** | Identical Validation Dates | `app/training/walk_forward.py#L9` | `VERIFIED` | Baselines and candidate ML models scored on identical holdout samples |
| **LEAK-09** | Missing Target Handling | `app/prediction/target.py#L218-L224` | `VERIFIED` | Zero synthetic target fabrication; clean segregation of unverified dates |

---

## Stage 5 — Previous-Close Baseline Validation Specification

Formal evaluation specification defined in [`baseline_validation_specification.md`](file:///D:/Share_market_predictor/research/datasets/nifty50/combined_acceptance_audit/baseline_validation_specification.md):

1. **Price Baseline (Naive Random Walk):** $\hat{P}_{t+h} = P_t$ for $h \in \{1, 3, 5\}$.
2. **Return Baseline (Martingale):** $\hat{R}_{t, h} = 0.0$.
3. **Directional Baseline:** Majority class from training labels $\hat{D}_{t, h} = \text{MajorityClass}(y_{\text{train}})$.
4. **Included Population:** Strictly the 2,475 contiguous included regular sessions from `nifty50_aligned.csv`.
5. **Partitioning:** 5 expanding-window folds with 40% initial training ratio and $h$-session outcome embargo gap.
6. **Metrics:** MAE, RMSE, MAPE for prices; Directional Accuracy, Precision, Recall, F1-score for classification.
7. **Execution Status:** **Specification only.** No predictive models were executed.

---

## Stage 6 — Integrated Readiness Decision

- **Readiness Classification:** **`PARTIALLY_READY`**
- **Promotion Decision:** **NOT PROMOTED** to `RESEARCH_READY`.
- **Primary Blockers Remaining:**
  1. Five unverified calendar dates lack positive exchange circular evidence.
  2. Yahoo Finance lacks observations for 13 NSE dates.
  3. Secondary price series for constituent equities and sector index remain unverified.
- **Safety Compliance:**
  - `data/predictions.db` was not modified.
  - Frozen CSV files and SHA-256 hashes remain untouched.
  - Production code, algorithms, and models remain unchanged.
  - Forecasting experiments remain strictly **ON HOLD**.
