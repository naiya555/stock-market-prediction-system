# Monitoring Workflow Integration

Monitoring is advisory and runs before data is used by:

1. `scripts/run_regression_phase5.py` (and the Phase 6 chain through its shared loader).
2. `scripts/train_models.py` before feature/model work.
3. `PredictionService.predict` after retrieval and before feature assembly/inference.

Each workflow calls `app.market.quality.integration.run_advisory_monitor` with
the instrument-specific raw canonical records and provider name. The helper logs
the status, counts for PASS/WARNING/FAIL/UNVERIFIED, and the report location:

`research/data_quality_monitoring/baseline_quality_report.json`

`FAIL`, `UNVERIFIED`, and monitor exceptions are logged clearly. They do not
silently become `PASS`, but the workflow remains non-blocking by design. No
prediction result, model selection, feature matrix, source record, or database
record is changed.
