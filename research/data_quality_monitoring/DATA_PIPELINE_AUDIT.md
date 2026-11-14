# Market Data Pipeline Audit

## Existing flow

`BaseMarketDataProvider.fetch_historical_ohlcv` returns canonical immutable
`MarketOHLCV` records. `run_market_data_pipeline` retrieves records, calls
`clean_market_data`, then computes returns, indicators, candlesticks, and trend.
The quality monitor runs against the provider output before downstream research
and does not alter that flow.

## Instrument differences

- **BHARTIARTL, TCS:** Yahoo Finance daily equity OHLCV; OHLC and reported volume are expected.
- **NIFTY_50:** official NSE Indices close series in the project; provider availability of OHLC fields is observed rather than assumed.
- **NIFTY_TELECOMMUNICATIONS:** official NSE Indices close-only limitation; OHLC and volume checks are not applied.

## Findings and weaknesses

The existing cleaner validates required values, positive prices, OHLC geometry,
negative volume, duplicates, timezone normalization, and ordering, but it is a
transformation/quarantine layer rather than an independent monitoring report.
The provider contract exposes a provider name but not a uniform retrieval URL,
calendar, retry policy, or response completeness metadata. Calendar gaps cannot
be safely classified without exchange-calendar evidence. Equity corporate-action
and adjusted/unadjusted provenance remain external verification limitations.

The monitor therefore reports anomalies separately, preserves raw records, and
uses `UNVERIFIED` rather than guessing holiday/session classifications.
