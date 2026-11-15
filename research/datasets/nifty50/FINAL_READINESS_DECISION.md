# Final Readiness Decision — NIFTY 50

## 1. Readiness Determination

**Current Status:** `PARTIALLY_READY`  
**Promotion Decision:** **NOT PROMOTED** to `RESEARCH_READY`.

---

## 2. Evidence and Reconciliation Assessment

1. **Source Reconciliation Result:** **PASS (for overlapping observations)**  
   - 2,476 overlapping trading dates between official NSE Indices and Yahoo Finance.
   - All 2,476 observations match within the documented tolerance (0.01 absolute, 0.0001 relative / 0.01%).
   - Zero numerical price mismatches under the standard tolerance.

2. **Observations Breakdown:**
   - **Total Unique Dates:** 2,489
   - **Included in Verified Research Baseline:** 2,475 observations
   - **Excluded from Verified Research Baseline:** 14 observations
     - 9 verified special sessions omitted by Yahoo Finance.
     - 4 unverified weekday sessions omitted by Yahoo Finance (2018-01-01, 2019-01-01, 2019-02-13, 2019-03-29).
     - 1 unverified calendar session with price match (2016-11-16).

3. **Calendar Classification Impact:**
   - 9 sessions are verified via official NSE circulars.
   - 5 dates remain **UNVERIFIED** (2016-11-16, 2018-01-01, 2019-01-01, 2019-02-13, 2019-03-29).
   - Under the frozen inclusion/exclusion policy, these five dates are explicitly segregated and excluded from the core verified baseline. However, the presence of unverified calendar sessions across the 10-year span prevents automated assertion of a defect-free exchange calendar.

4. **Reproducibility:** **PASS**  
   - Both provider snapshots are reproducibly obtainable via the verified adapters (`NiftyIndicesProvider` and `YFinanceProvider`).
   - Cryptographic SHA-256 hashes are fixed in `hash_manifest.json`.
   - Running `verify_dataset.py` independently recalculates identical hashes and validates all 9 quality checks.

5. **Target and Chronological Validation Requirements:** **CONDITIONALLY SATISFIED**  
   - The 2,475 contiguous included observations provide sufficient temporal depth (10 years) for walk-forward evaluation without lookahead leakage.
   - However, target definitions spanning multi-day horizons must explicitly handle the excluded dates without forward-filling across missing sessions.

---

## 3. Remaining Blockers Before Numerical Experiments Can Start

Before numerical forecasting experiments can be permitted on NIFTY 50, the following mandatory conditions must be satisfied:

1. **Formal Resolution of the 5 Unverified Calendar Dates:**
   - Official capital-market trading or holiday circulars must be retrieved for 2016-11-16, 2018-01-01, 2019-01-01, 2019-02-13, and 2019-03-29, OR an explicit project-wide waiver must formalize their exclusion from all horizon targets.
2. **Special Session Horizon Boundary Policy:**
   - A deterministic convention must be codified for whether returns spanning weekend special sessions (e.g., 1-hour Diwali Muhurat trading or Budget sessions) are modeled as distinct 1-day steps or aggregated into regular-session returns.
3. **Previous-Close Baseline Re-Validation:**
   - Leakage audits, chronological split definitions, and random walk / naive previous-close baseline benchmarks must be executed strictly against the 2,475 included observations.
4. **Independent Secondary Data Source for Telecommunications and Equities:**
   - While NIFTY 50 has dual-source price reconciliation, full market prediction pipelines that incorporate sectoral or constituent context (BHARTIARTL, TCS, NIFTY Telecommunications) remain constrained by lack of independent provider corroboration.

---

## 4. Final Rule Compliance

- **Forecasting experiments remain strictly ON HOLD.**
- **No models were trained.**
- **No production code, database records (`data/predictions.db`), or established research findings were altered.**
