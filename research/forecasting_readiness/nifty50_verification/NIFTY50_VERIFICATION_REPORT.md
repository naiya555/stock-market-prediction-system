# NIFTY 50 Historical Calendar and Data Reconciliation

## Result

The current retrieval on 2026-11-15 found 2,489 official NSE Indices records
and 2,476 Yahoo Finance records. All 2,476 overlapping dates matched within
the existing 0.01 absolute / 0.01% relative tolerance. There were zero
mismatches, 13 current NSE-only dates, and no interpolated values.

The earlier 2,465 matched / 14 unmatched result remains a valid prior snapshot.
The current endpoint now contains 2016-11-16, so the snapshot changed from 14
unmatched dates to 13. Previous artifacts were not rewritten.

## Calendar classification

Nine dates are now officially verified special sessions, including
2026-02-01 via NSE/CMTR/72349. Five dates remain UNVERIFIED:
2016-11-16, 2018-01-01, 2019-01-01, 2019-02-13, and 2019-03-29.
No regular session or holiday was asserted because holiday-list omission and
weekday status are not sufficient evidence.

The eight previously verified special sessions remain preserved. The complete
date-level result is in `date_by_date_calendar_audit.csv`.

## Remaining blockers

NIFTY 50 remains `PARTIALLY_READY`. Yahoo Finance lacks 13 current NSE-only
observations, five calendar classifications remain unresolved, and the two
provider snapshots have different coverage. Research must freeze a dated
snapshot and use only explicitly comparable dates.
