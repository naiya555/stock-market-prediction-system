# Previous-Close Baseline Validation Specification: NIFTY 50

## 1. Objective & Non-Execution Scope

This document specifies the exact, reproducible evaluation protocol for the non-parametric **Previous-Close Baseline** and **Zero-Return Baseline** on the NIFTY 50 index.

> [!IMPORTANT]
> This document is a **formal specification only**. No numerical model training or predictive experiments are executed during this audit.

---

## 2. Mathematical Baseline Formulations

For an indexed chronological sequence of verified included trading sessions $t = 0, 1, \dots, N-1$ with observed closing prices $P_t$:

### 1. Close-Price Persistence Baseline (Naive Random Walk)
For forward horizon $h \in \{1, 3, 5\}$ sessions:
$$\hat{P}_{t+h} = P_t$$
*Interpretation:* The predicted close price for session $t+h$ is identical to the currently known close price at session $t$.

### 2. Zero-Return Baseline
$$\hat{R}_{t, h} = 0.0$$
*Interpretation:* The expected forward return over the horizon is 0.0% (martingale price assumption).

### 3. Directional Persistence Baseline
$$\hat{D}_{t, h} = \begin{cases} 1 & \text{if } \text{MajorityClass}(y_{\text{train}}) = 1 \\ 0 & \text{if } \text{MajorityClass}(y_{\text{train}}) = 0 \end{cases}$$
Where $y_{\text{train}}$ represents binary direction labels $\{1 = \text{UP}, 0 = \text{DOWN}\}$ strictly from the training partition.

---

## 3. Observation Population & Session Ordering

- **Canonical Dataset Source:** [`research/datasets/nifty50/nifty50_aligned.csv`](file:///D:/Share_market_predictor/research/datasets/nifty50/nifty50_aligned.csv).
- **Inclusion Filter:** Strictly observations where `inclusion_status == 'INCLUDED'`.
- **Total Population ($N$):** Exactly **2,475** trading sessions spanning `2016-11-01` to `2026-11-13`.
- **Session Ordering:** Chronological index sequence $t = 0, 1, \dots, 2474$.
- **Exclusion of Intervening Dates:** All 14 excluded dates (9 special sessions + 4 unverified NSE-only + 1 calendar-unverified `2016-11-16`) are filtered out prior to session indexing. No forward-filling across excluded dates is permitted.

---

## 4. Multi-Horizon Target Formulation ($h \in \{1, 3, 5\}$)

For each included session $t$:

| Horizon ($h$) | Target Return ($R_{t, h}$) | Directional Target ($D_{t, h}$) | Unlabeled Tail Sessions ($t \ge N-h$) |
|---|---|---|---|
| **$h = 1$ (1 session)** | $\frac{P_{t+1}}{P_t} - 1.0$ | $1 \text{ if } R_{t, 1} > 0.0 \text{ else } 0$ | Final 1 session ($t = 2474$) receives `None` |
| **$h = 3$ (3 sessions)** | $\frac{P_{t+3}}{P_t} - 1.0$ | $1 \text{ if } R_{t, 3} > 0.0 \text{ else } 0$ | Final 3 sessions ($t \in [2472, 2474]$) receive `None` |
| **$h = 5$ (5 sessions)** | $\frac{P_{t+5}}{P_t} - 1.0$ | $1 \text{ if } R_{t, 5} > 0.0 \text{ else } 0$ | Final 5 sessions ($t \in [2470, 2474]$) receive `None` |

---

## 5. Walk-Forward Temporal Validation Partitioning

Validation must strictly utilize the existing `generate_walk_forward_splits` layer in `app/training/walk_forward.py`:

- **Number of Folds ($K$):** 5 expanding-window chronological folds.
- **Minimum Initial Training Ratio:** 40% of observations ($\approx 990$ sessions).
- **Purging & Embargo Buffer:**
  - For $h = 1$: `embargo_sessions = 1`.
  - For $h = 3$: `embargo_sessions = 3`.
  - For $h = 5$: `embargo_sessions = 5`.
  - Partition boundaries:
    $$\text{Train}_k = [0, v_{k, \text{start}} - \text{embargo})$$
    $$\text{Val}_k = [v_{k, \text{start}}, v_{k, \text{end}})$$

### Approximate Fold Boundaries Across 2,475 Included Sessions:
- **Total Valid Labeled Samples:** $N_{\text{valid}} = 2475 - h$.
- **Initial Training Window:** Folds expand from $\approx 990$ sessions (2016–2020) up to $\approx 2,180$ sessions (2016–2025).
- **Out-of-Sample Validation Windows:** 5 consecutive contiguous slices of $\approx 290$ sessions each, evaluating market regimes from 2020 through 2026.

---

## 6. Evaluation Metrics

Both regression and classification metrics must be evaluated on the identical out-of-sample validation dates:

### 1. Regression Metrics (Price & Return)
- **Mean Absolute Error (MAE):**
  $$\text{MAE} = \frac{1}{M} \sum_{i=1}^M |P_i - \hat{P}_i|$$
- **Root Mean Squared Error (RMSE):**
  $$\text{RMSE} = \sqrt{\frac{1}{M} \sum_{i=1}^M (P_i - \hat{P}_i)^2}$$
- **Mean Absolute Percentage Error (MAPE):**
  $$\text{MAPE} = \frac{100\%}{M} \sum_{i=1}^M \left|\frac{P_i - \hat{P}_i}{P_i}\right|$$

### 2. Directional Classification Metrics
- **Directional Accuracy:** Fraction of correctly predicted signs ($\hat{D}_i = D_i$).
- **Precision, Recall, F1-Score:** Separately for positive class ($1 = \text{UP}$) and macro-averaged across both classes.
- **Confusion Matrix:** Full $2 \times 2$ counts: True Positive, False Positive, True Negative, False Negative.

---

## 7. Reporting & Validation Output Protocol

When authorized to execute in future phases, validation outputs must produce:
1. **Fold-Level Breakdown:** Performance per fold to detect non-stationarity across volatility regimes (e.g. COVID crash fold vs bull market fold).
2. **Pooled Micro-Total & Macro-Average:** Mean $\pm$ std across folds alongside aggregate pooled sample totals.
3. **Statistical Superiority Gate:** Candidate ML models (XGBoost, LightGBM) must demonstrate statistically significant outperformance over the Previous-Close baseline before advancing to production consideration.
