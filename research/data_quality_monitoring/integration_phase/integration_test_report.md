# Integration Test Report

Commands and results:

- `.\.venv\Scripts\python.exe -m pytest -q tests\test_quality_integration.py tests\test_data_quality.py tests\test_pipeline.py tests\test_cleaning.py`: **24 passed**.
- `.\.venv\Scripts\python.exe -m pytest -q tests\test_prediction_service.py`: **13 passed**.
- `.\.venv\Scripts\python.exe -m py_compile app\market\quality\integration.py app\prediction\service.py scripts\run_regression_phase5.py scripts\train_models.py tests\test_quality_integration.py`: **passed**.
- `git diff --check`: **passed**.
- Calendar CSV/JSON assertions: **passed**; 14 rows, 8 verified special sessions, 6 unresolved.

The integration tests use in-memory canonical records. They verify instrument
separation, visible advisory status, report-path exposure, and that monitor
exceptions produce `FAILED`, never `PASS`.
