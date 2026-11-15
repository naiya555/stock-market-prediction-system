# Session Inclusion & Horizon Target Policy: NIFTY 50

## 1. Purpose & Scope

This policy defines the deterministic rules governing session eligibility, exclusion criteria, and multi-session target construction ($h=1, 3, 5$) for NIFTY 50 research datasets.

It establishes a rigorous boundary between **standard regular market sessions** and **heterogeneous special sessions**, preventing temporal distortion in forward returns, rolling volatility, and technical indicators.

---

## 2. Standard Evidence Status Mapping

All session categorizations must conform strictly to the project's standard evidence status vocabulary:

| Category | Definition | Evidence Status | Dual-Source Baseline Decision |
|---|---|---|---|
| **Regular Trading Sessions** | Standard 6.25-hour market hours (09:15–15:30 IST), dual-source matching within 0.01 / 0.0001 tolerance. | `CORROBORATED` (via dual-provider price identity) | `INCLUDE` (2,475 observations) |
| **Verified Special Sessions** | Off-calendar / weekend sessions verified by official NSE circulars (e.g. 60-min Muhurat, Budget, DR switch). | `VERIFIED` (via official exchange circulars) | `EXCLUDE` (9 observations) |
| **Unverified Weekday Sessions** | NSE observations lacking secondary provider data and missing positive circular confirmation. | `UNVERIFIED` | `EXCLUDE` (4 observations) |
| **Unverified Calendar Overlap** | Overlapping dual-provider observations lacking positive trading circular confirmation (2016-11-16). | `UNVERIFIED` | `EXCLUDE` (1 observation) |

---

## 3. Policy Rules by Session Category

### Rule A: Regular Trading Sessions (Included Baseline)
- **Eligibility:** Observation must be present in both primary (NSE Indices) and secondary (Yahoo Finance) snapshots and match within tolerance (`abs_diff <= 0.01` OR `rel_diff <= 0.0001`).
- **Session Duration:** Must represent standard full-day trading hours (09:15 to 15:30 IST).
- **Population:** Exactly **2,475** contiguous sessions between `2016-11-01` and `2026-11-13` qualify for the verified core research baseline.

### Rule B: Verified Special Sessions (Isolated / Excluded)
- **Population:** Exactly **9** sessions (`2019-10-27`, `2020-02-01`, `2020-11-14`, `2023-11-12`, `2024-01-20`, `2024-03-02`, `2024-05-18`, `2026-02-01`, `2026-11-08`).
- **Microstructure Rationale:**
  1. *Diwali Muhurat Trading:* 60-minute evening session (18:15–19:15 IST). Truncated volume, festive ceremonial sentiment, and atypical bid-ask spreads prevent comparability with 375-minute regular sessions.
  2. *Disaster Recovery Switch Sessions:* Split sessions operating from primary and disaster-recovery sites with interrupted trading blocks.
  3. *Budget Sessions:* Saturday/Sunday sessions operating under unique macroeconomic news flow.
- **Decision:** Excluded from standard daily forecasting models. In specialized micro-regime research, they may be analyzed only as an isolated test group (`ISOLATE_ONLY`), never merged into contiguous daily rolling windows.

### Rule C: Unresolved Calendar Dates (Strictly Excluded)
- **Population:** Exactly **5** dates (`2016-11-16`, `2018-01-01`, `2019-01-01`, `2019-02-13`, `2019-03-29`).
- **Decision:** Excluded from the verified baseline until positive, primary capital-market equity circulars certifying official market sessions are retrieved. Weekday status, omission from holiday circulars, or provider agreement are explicitly rejected as proof.

---

## 4. Multi-Horizon Target Construction ($h=1, 3, 5$) Across Excluded Dates

For any sequence of verified included sessions $t = 0, 1, \dots, N-1$ with closing prices $P_t$:

$$R_{t, h} = \frac{P_{t+h}}{P_t} - 1.0$$

$$D_{t, h} = \begin{cases} 1 & \text{if } R_{t, h} > 0.0 \\ 0 & \text{if } R_{t, h} \le 0.0 \end{cases}$$

### Horizon Alignment Invariants:
1. **Contiguous Index Stepping:** Index step $t+1$ represents the *next verified included session*, NOT calendar day $t+1$.
2. **Pre-Filtering Exclusion:** All 14 excluded dates must be removed from the series *before* indexing $t, t+1, \dots, t+h$. This prevents missing sessions from creating null target holes inside the feature matrix.
3. **Horizon Boundary Purging (Embargo):**
   - For horizon $h$, the final $h$ observations in the series ($t = N-h, \dots, N-1$) have no realized outcome and evaluate strictly to `target = None`.
   - In walk-forward cross-validation, the temporal embargo gap between training and validation partitions must be set to $\ge h$ sessions to prevent target overlap leakage.

---

## 5. Comparative Evaluation: Research Readiness With vs. Without Special Sessions

| Dimension | Baseline Without Special Sessions (2,475 Sessions) | Baseline With Special Sessions (2,484 Sessions) |
|---|---|---|
| **Provider Corroboration** | **100% Dual-Source Corroborated** (NSE Indices + Yahoo Finance agree on all dates) | **Partially Corroborated** (Yahoo Finance lacks all 9 special sessions) |
| **Microstructure Homogeneity** | **Strictly Homogeneous** (all sessions standard 375-min regular hours) | **Heterogeneous** (mixes 60-min Muhurat and DR sessions with regular days) |
| **Volatility & Return Stability** | Daily returns and rolling ATR represent identical holding intervals | Muhurat returns compress volatility, artificially skewing rolling metrics |
| **Leakage & Target Integrity** | Fully compliant with standard chronological walk-forward validation | Requires complex custom step logic to prevent horizon distortion |
| **Readiness Recommendation** | **Viable for Controlled Baseline Validation** | **High Risk; Restricted to Dedicated Regime Studies** |
