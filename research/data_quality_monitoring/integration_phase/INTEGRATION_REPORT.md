# Phase 2 Monitoring Integration and Calendar Verification

## Monitoring integration

The existing read-only monitor is now invoked before Phase 5 research loading,
the training CLI, and runtime `PredictionService` feature assembly. Status is
instrument-specific and logged as PASS, WARNING, FAIL, UNVERIFIED, or FAILED
when the monitor itself raises an exception. The integration is advisory only:
workflows continue, and no data, model, prediction, or database behavior is
changed.

The report path displayed in logs is
`research/data_quality_monitoring/baseline_quality_report.json`.

## Calendar verification

Fourteen dates were evaluated. Eight are officially verified NSE special
sessions: 2019-10-27, 2020-02-01, 2020-11-14, 2023-11-12, 2024-01-20,
2024-03-02, 2024-05-18, and 2026-11-08. Six remain UNVERIFIED:
2016-11-16, 2018-01-01, 2019-01-01, 2019-02-13, 2019-03-29, and 2026-02-01.

Verified regular sessions: 0. Verified holidays: 0. A weekday or a calendar
omission was not treated as proof of a regular session or holiday.

## Limitations

The six unresolved dates require an official source that explicitly establishes
their session classification. The calendar monitor has no exchange-calendar
adapter yet, so runtime gap findings remain UNVERIFIED rather than errors.
