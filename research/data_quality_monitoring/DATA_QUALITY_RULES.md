# Data Quality Rules

The monitor reads canonical `MarketOHLCV` records and never sorts, repairs, deletes,
deduplicates, fills, or writes source data. It writes only reports under this directory.

| Check | Status | Rule |
|---|---|---|
| Required fields | FAIL | Symbol, timestamp, close, and source must be present. |
| Price domain | FAIL | Prices must be finite and greater than zero. |
| OHLC geometry | FAIL | Applied only to equity/full OHLC records: high >= open/close and low <= open/close. |
| Volume domain | FAIL | Volume cannot be negative. |
| Duplicate timestamp/order | FAIL | One chronological observation per instrument/session. |
| Missing sessions | UNVERIFIED | Gaps over three calendar days are reported; without an exchange calendar they are not declared missing sessions. |
| Weekend/session classification | UNVERIFIED | Weekend observations require official calendar evidence. |
| Stale data | WARNING | Latest observation older than 3 days. |
| Price jump | WARNING | Absolute close-to-close return >= 20%; may be valid or corporate-action related. |
| Volume change | WARNING | Consecutive reported-volume ratio >= 10x or <= 0.1x. |
| Zero volume | WARNING | Reported zero volume is flagged for review; close-only index volume is not treated as missing. |
| Empty provider response | FAIL | No records returned. |

`PASS` means no finding was emitted. `WARNING` means suspicious but not proven
incorrect. `FAIL` means a structural/domain violation. `UNVERIFIED` means evidence
needed for classification was unavailable.
