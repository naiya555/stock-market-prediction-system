# Data Sources Planning Guide

This document catalogs the candidate data sources required for the Indian Stock Market Prediction System across all planned dimensions.

> **CRITICAL VERIFICATION NOTICE:**  
> All sources listed below are currently classified as **`PLANNED / TO BE VERIFIED`**.  
> No source should be treated as free, publicly accessible, legally permitted, rate-limit friendly, or reliable until it has been formally connected, validated, and verified during its respective implementation phase.

---

## 1. Indian Equity Market Data (Equities & Cash Market)

| Information | Candidate Providers / Mechanisms | Status | Notes / Verification Requirements |
|---|---|:---:|---|
| Historical OHLCV (NSE/BSE) | `yfinance`, NSE direct endpoints, broker APIs (Zerodha Kite, Upstox, Angel One) | **PLANNED / TO BE VERIFIED** | Verify rate limits, split/bonus adjustment accuracy, and data consistency. |
| Intraday / Current Quotes | Broker WebSockets, NSE official public feeds | **PLANNED / TO BE VERIFIED** | Verify licensing, latency, WebSocket stability, and market hours handling. |
| Volume & Trade Distribution | NSE bhavcopy, broker market depth APIs | **PLANNED / TO BE VERIFIED** | Verify delivery % vs. speculative intraday volume availability. |

---

## 2. Benchmark Index & Market Breadth Data

| Information | Candidate Providers / Mechanisms | Status | Notes / Verification Requirements |
|---|---|:---:|---|
| NIFTY 50, NIFTY Next 50, NIFTY 500 | NSE official indices data, `yfinance` (`^NSEI`) | **PLANNED / TO BE VERIFIED** | Verify index level accuracy and constituent weightings availability. |
| Market Breadth (Advances / Declines) | NSE Market Activity reports, Bhavcopy aggregations | **PLANNED / TO BE VERIFIED** | Verify calculation mechanism across NSE broad-market stocks. |
| India VIX (Volatility Index) | NSE VIX data feeds | **PLANNED / TO BE VERIFIED** | Benchmark for overall domestic volatility context. |

---

## 3. Sectoral & Thematic Indices

| Information | Candidate Providers / Mechanisms | Status | Notes / Verification Requirements |
|---|---|:---:|---|
| NIFTY Bank, NIFTY IT, NIFTY Auto, NIFTY Pharma, NIFTY Metal, NIFTY FMCG | NSE sectoral indices feeds | **PLANNED / TO BE VERIFIED** | Necessary for computing relative strength and sector-level rotation. |

---

## 4. Company Fundamentals & Corporate Announcements

| Information | Candidate Providers / Mechanisms | Status | Notes / Verification Requirements |
|---|---|:---:|---|
| Corporate Filings & Earnings Releases | NSE Corporate Announcements RSS/API, BSE announcements | **PLANNED / TO BE VERIFIED** | Verify point-in-time timestamping of earnings release vs. market reaction. |
| Shareholding Pattern & Insider Trades | NSE/BSE disclosure filings | **PLANNED / TO BE VERIFIED** | Ingest promoter pledges, insider trades, and FII/DII institutional holdings. |

---

## 5. Financial News

| Information | Candidate Providers / Mechanisms | Status | Notes / Verification Requirements |
|---|---|:---:|---|
| Domestic Financial Media Headlines | Economic Times, Moneycontrol, Livemint, Business Standard RSS | **PLANNED / TO BE VERIFIED** | Verify scraping/RSS policies, deduplication across outlets, and timestamp reliability. |
| Global Financial News Feeds | Reuters, Bloomberg, Yahoo Finance RSS feeds | **PLANNED / TO BE VERIFIED** | Verify coverage of India-focused multi-national developments. |

---

## 6. Governmental & Regulatory Information

| Information | Candidate Providers / Mechanisms | Status | Notes / Verification Requirements |
|---|---|:---:|---|
| RBI Monetary Policy & Notifications | Reserve Bank of India (RBI) Press Releases & Circulars | **PLANNED / TO BE VERIFIED** | Interest rate decisions, liquidity announcements, and banking regulatory changes. |
| SEBI Regulatory Circulars | SEBI notifications & enforcement orders | **PLANNED / TO BE VERIFIED** | Market structure changes, derivative rules, circuit limit modifications. |
| Union Ministry / Government Releases | Press Information Bureau (PIB) India feeds | **PLANNED / TO BE VERIFIED** | Sector subsidies, export/import duties, PLI scheme announcements. |

---

## 7. Global Macroeconomic & Currency Markets

| Information | Candidate Providers / Mechanisms | Status | Notes / Verification Requirements |
|---|---|:---:|---|
| Currency (USD/INR, EUR/INR) | Central bank feeds, Forex market APIs | **PLANNED / TO BE VERIFIED** | Essential for IT, Pharma (exporters) and Oil/Commodity (importers). |
| Commodities (Brent Crude, Gold, Natural Gas) | Multi-Commodity Exchange (MCX), global commodity APIs | **PLANNED / TO BE VERIFIED** | Direct cost input for aviation, paint, oil marketing, and fertilizer sectors. |
| US & Asian Markets (S&P 500, Nasdaq, Nikkei, GIFT Nifty) | Global market APIs, GIFT City IFSC data | **PLANNED / TO BE VERIFIED** | Overnight sentiment indicator for domestic morning opening sessions. |

---

## 8. Environmental, Weather & Commodity Disruptions

| Information | Candidate Providers / Mechanisms | Status | Notes / Verification Requirements |
|---|---|:---:|---|
| Monsoon & Weather Data | India Meteorological Department (IMD) bulletins | **PLANNED / TO BE VERIFIED** | Critical for agricultural input, rural FMCG, and tractor/fertilizer demand. |
| Supply Chain & Port Logistics | Port authority bulletins, global freight indices (e.g., Baltic Dry) | **PLANNED / TO BE VERIFIED** | Monitor container freight rate shifts and shipping lane bottlenecks. |

---

## 9. Technology & Geopolitical Events

| Information | Candidate Providers / Mechanisms | Status | Notes / Verification Requirements |
|---|---|:---:|---|
| Technology Disruption / Cybersecurity | CERT-In advisories, global tech incident registries | **PLANNED / TO BE VERIFIED** | Evaluate enterprise-wide technology disruptions or cyber risk events. |
| Geopolitical & Trade Policy Events | Ministry of External Affairs releases, global conflict trackers | **PLANNED / TO BE VERIFIED** | Tariffs, sanctions, cross-border tensions impacting supply chains. |

---

## 10. Data Ingestion Guidelines & Temporal Isolation Rules

1. **Mandatory Point-in-Time Stamping:**  
   Every ingested item must be accompanied by two timestamps:
   - `event_timestamp`: When the event occurred in the real world.
   - `data_available_at`: When the data record was ingested and accessible to the system.
2. **Filtering by Inference Timestamp:**  
   When generating a prediction at $T_{pred}$, all records where `data_available_at > T_pred` are strictly inaccessible to the model.
3. **Graceful Degradation:**  
   If an external data source experiences downtime, pipelines must fail safely with explicit warning logs without corrupting the historical database.

---

## 11. Day 3 Market Data Source Investigation & Provider Decision

### 11.1. Candidate Source Evaluation

| Source / Provider | Data Type & Granularity | Access Method & Auth | Pricing & Limits | Reliability & Caveats | Symbol Coverage | Status |
|---|---|---|---|---|---|:---:|
| **Yahoo Finance (`yfinance`)** | Historical OHLCV (1d, 1wk, 1mo, intraday 1m–60m) | Python package / HTTP REST. No API key required; session cookie/crumb handshake. | Free community access. Rate limits on rapid bursts. | High development utility; unofficial API subject to upstream structure shifts. Must handle corporate adjustments explicitly (`auto_adjust=False`). | Comprehensive Indian equities (`.NS` for NSE, `.BO` for BSE) | **PLANNED / TO BE VERIFIED** |
| **NSE Official Bhavcopy** | Official EOD settlement OHLCV, deliverable volume, trades (1d) | HTTP archive download from `nseindia.com`. No auth for manual; session headers required for automation. | Free public statutory disclosure. CDN / Akamai bot protection. | Exchange authoritative ground truth. URL schemes change periodically; lacks intraday resolution. | All NSE listed equities | **TO BE VERIFIED** |
| **Alpha Vantage** | Historical OHLCV (1d, intraday 1m–60m) | REST API. API key required. | Free tier capped at 25 requests/day. Paid plans from $49.99/mo. | Inadequate free throughput for multi-year training datasets. Spotty/delayed Indian equity coverage. | Limited/inconsistent Indian ticker coverage | **NOT SELECTED** |
| **Indian Broker APIs (Zerodha Kite, Upstox, Angel One)** | Tick-by-tick, historical 1m–1d OHLCV, market depth | Official REST API & WebSockets. API key + Secret + TOTP auth. | Kite: ₹2,000/mo (API) + ₹2,000/mo (historical). Upstox/Angel One: Free tiers for account holders. | High reliability, exchange-grade fidelity. Requires Indian KYC brokerage account and daily token management. | Full NSE/BSE coverage | **PLANNED** (Phase 14 Live) |
| **Google Finance / Scraping** | Web quotes | HTML scraping. No supported public API. | Free display on web. Scraping strictly prohibited. | Fragile, violates Terms of Service, no reliable historical series API. | Global / Indian | **NOT SELECTED** |

### 11.2. Initial Stock Target: `BHARTIARTL`
- **Target Equity:** Bharti Airtel Limited (`BHARTIARTL`)
- **Sector Focus:** Nifty Telecommunications / Nifty 50
- **Exchange Identifier:** `BHARTIARTL` (NSE), `BHARTIARTL.NS` (Yahoo Finance)
- **Rationale:** Liquid large-cap constituent representing the telecommunications sector with extensive historical series, active options/futures chains, and substantial news coverage.
- **Strict Boundary:** No market data for `BHARTIARTL` is fetched or fabricated on Day 3. Real acquisition occurs exclusively in Day 4.

### 11.3. Day 4 Provider Decision
- **Shortlisted Primary Provider:** **Yahoo Finance (`yfinance`)**
- **Decision Status:** **PLANNED / TO BE VERIFIED**
- **Justification:** Offers the lowest friction path for bootstrapping historical daily OHLCV for Indian equities without requiring immediate paid brokerage subscriptions, KYC verification, or complex daily session handshakes.
- **Verification Requirements for Day 4:**
  1. Empirically verify network availability and download integrity for `BHARTIARTL.NS`.
  2. Confirm accurate unadjusted vs. adjusted close handling (`auto_adjust=False`).
  3. Validate timezone localization from UTC to Indian Standard Time (`Asia/Kolkata`).
- **Official Ground Truth Fallback:** **NSE Bhavcopy** (Status: **TO BE VERIFIED** for reconciliation and official settlement volume).

### 11.4. Provenance and Temporal Integrity Guarantees
- Every market record emitted by any provider adapter must be mapped into `app.core.schemas.MarketOHLCV`.
- Required provenance attributes: `source` (provider name), `timestamp` (market bar time), `symbol` (uppercase ticker).
- At prediction time $T_{pred}$, temporal leakage is strictly forbidden: $\forall t_{obs} > T_{pred}$, data is inaccessible to feature extraction or model inference.

---

## 12. Day 4 Historical Provider Empirical Verification Record

### 12.1. Verification Summary

| Dimension | Verified State |
|---|---|
| **Provider** | Yahoo Finance (`yfinance` v1.7.0) |
| **Verification Status** | **VERIFIED** (Empirical live test successful) |
| **Target Symbol** | `BHARTIARTL` (queried as `BHARTIARTL.NS`) |
| **Observation Window** | 2026-09-01 to 2026-09-08 (5 trading sessions, 6 daily bars captured) |
| **Data Interval** | `1d` (Daily) |
| **Price Convention** | **Raw Unadjusted OHLCV** (`auto_adjust=False`). Preserves actual traded prices and physical candle relationships (`High >= max(Open, Close)`, `Low <= min(Open, Close)`). |
| **Timestamp Fidelity** | Returned as `pandas.DatetimeIndex` localized to `Asia/Kolkata` (`+05:30`). Mapped to Python `datetime` objects retaining calendar session integrity without synthetic intraday hour fabrication. |
| **Domain Validation** | 100% of returned bars passed canonical `MarketOHLCV` domain bounds (positive prices, non-negative volume, valid candle wicks). |
| **Verification Timestamp** | 2026-10-08T21:38:34+05:30 |
| **Fallback Status** | NSE Bhavcopy remains **TO BE VERIFIED** as official ground truth benchmark. |

### 12.2. Empirical Limitations Identified
1. **Exclusive End Date:** In Yahoo Finance's underlying API, the `end` date parameter is exclusive (`[start, end)`). The adapter resolves this by querying `end_date + timedelta(days=1)` and filtering records to the inclusive observation window.
2. **Missing/Delisted Symbols:** Yahoo Finance returns an empty DataFrame rather than an explicit JSON error for delisted or nonexistent tickers. The adapter differentiates network exceptions from empty result sets.
3. **Burst Rate Limiting:** High-frequency consecutive requests can trigger Yahoo crumb expiration or rate limits. The adapter isolates upstream exceptions and raises actionable errors with logging.


