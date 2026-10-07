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
