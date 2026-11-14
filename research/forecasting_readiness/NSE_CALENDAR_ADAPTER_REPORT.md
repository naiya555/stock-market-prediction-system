# NSE Calendar Adapter Report

The adapter is a small, read-only loader in
`app/market/quality/nse_calendar.py`. It consumes cached CSV evidence and
returns `NSECalendarEvidence` objects. It supports
`REGULAR_SESSION`, `SPECIAL_SESSION`, `HOLIDAY`, `NON_TRADING_DAY`, and
`UNVERIFIED`. It never infers a classification from weekday or weekend.

The 14-date set contains eight officially verified special sessions and six
UNVERIFIED dates. No regular session or holiday was asserted. Official URLs
and limitations are recorded in `calendar_evidence_manifest.json`.

The monitor accepts this evidence through its optional `calendar_evidence`
argument. Unresolved dates remain `UNVERIFIED`; the integration stays advisory.
