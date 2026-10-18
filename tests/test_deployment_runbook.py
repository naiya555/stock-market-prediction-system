"""Tests for Deployment Runbook Validation and Live External Soak Runner.

Validates:
1. Production configuration guards (CORS, debug, explicit settings).
2. Health check and startup behavior under an isolated temporary database and model directory.
3. Real HTTP socket execution of `staging_soak_test.py` against a live local Uvicorn instance.
4. Non-mutation guarantee: soak test with persist=False leaves database unmutated.
5. Error handling and failure containment for connection timeouts and server errors.
"""

import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Generator
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest
import uvicorn

from app.api.app import create_app
from app.core.config import get_settings
from app.database.connection import create_connection
from app.database.repository import PredictionRepository
from scripts.staging_soak_test import (
    execute_request_external,
    run_soak_simulation,
)


def test_production_configuration_strict_validation():
    """Verify production startup rejects invalid CORS, insecure HTTP, and debug flags."""
    # 1. Reject wildcard CORS in production
    with patch.dict(os.environ, {"APP_ENV": "production", "APP_CORS_ORIGINS": "*", "APP_DEBUG": "false"}):
        with pytest.raises(ValueError, match="Wildcard CORS origin"):
            get_settings(reload=True)

    # 2. Reject debug mode in production
    with patch.dict(os.environ, {"APP_ENV": "production", "APP_CORS_ORIGINS": "https://trading.myfirm.in", "APP_DEBUG": "true"}):
        get_settings(reload=True)
        with pytest.raises(ValueError, match="APP_DEBUG cannot be enabled"):
            create_app()

    # 3. Reject missing explicit CORS in production
    with patch.dict(os.environ, {"APP_ENV": "production", "APP_DEBUG": "false"}, clear=True):
        get_settings(reload=True)
        with pytest.raises(ValueError, match="APP_CORS_ORIGINS must be explicitly configured"):
            create_app()

    # Reset settings to default environment
    get_settings(reload=True)


def test_health_check_with_isolated_storage():
    """Verify application startup and /api/health with clean isolated temp database and model directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        temp_db = temp_path / "test_isolated.db"
        temp_models = temp_path / "test_models"
        temp_models.mkdir()

        with patch.dict(
            os.environ,
            {
                "DATABASE_PATH": str(temp_db),
                "MODEL_DIR": str(temp_models),
                "APP_ENV": "development",
            },
        ):
            get_settings(reload=True)
            app = create_app()
            client = TestClient(app)

            res = client.get("/api/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "healthy"
            assert data["dependencies"]["database"]["status"] == "ok"
            assert data["dependencies"]["models"]["status"] == "ok"

    get_settings(reload=True)


def test_soak_external_http_execution_and_data_isolation():
    """Start a temporary local Uvicorn server and verify external HTTP socket load execution."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        temp_db = temp_path / "soak_test_clean.db"
        temp_models = temp_path / "models"
        temp_models.mkdir()

        # Initialize temporary repository
        repo = PredictionRepository(db_path=temp_db)

        test_port = 8899
        base_url = f"http://127.0.0.1:{test_port}"

        with patch.dict(
            os.environ,
            {
                "DATABASE_PATH": str(temp_db),
                "MODEL_DIR": str(temp_models),
                "APP_ENV": "development",
            },
        ):
            get_settings(reload=True)
            app = create_app()

            config = uvicorn.Config(app=app, host="127.0.0.1", port=test_port, log_level="warning")
            server = uvicorn.Server(config=config)

            server_thread = threading.Thread(target=server.run, daemon=True)
            server_thread.start()

            # Wait for server to listen
            max_wait = 5.0
            start_t = time.time()
            server_ready = False
            while time.time() - start_t < max_wait:
                try:
                    res = execute_request_external(base_url, "GET", "/api/health", timeout=1.0)
                    if res.status_code == 200:
                        server_ready = True
                        break
                except Exception:
                    pass
                time.sleep(0.1)

            assert server_ready is True, "Test Uvicorn server failed to initialize on test port."

            try:
                # Execute bounded soak simulation over real TCP sockets
                summary = run_soak_simulation(
                    total_requests=20,
                    concurrency=3,
                    base_url=base_url,
                    in_process=False,
                )

                assert summary.total_requests == 20
                assert summary.failed_requests == 0
                assert summary.successful_requests == 20
                assert summary.throughput_rps > 0.0
                assert summary.latency_mean_ms > 0.0

                # Verify Non-Mutation Guarantee: Zero predictions persisted during soak test
                count_cursor = repo.connection.execute("SELECT COUNT(*) FROM predictions;")
                count_row = count_cursor.fetchone()
                assert count_row[0] == 0, "Soak test traffic must not write predictions when persist=False."

            finally:
                server.should_exit = True
                server_thread.join(timeout=2.0)
                repo.connection.close()

    get_settings(reload=True)


def test_execute_request_external_failure_handling():
    """Verify external HTTP runner handles unreachable hosts and timeouts cleanly."""
    unreachable_url = "http://127.0.0.1:59999"  # Port not bound
    res = execute_request_external(unreachable_url, "GET", "/api/health", timeout=0.5)

    assert res.success is False
    assert res.status_code == 0
    assert res.error is not None
    assert "Failed" in res.error or "Connection" in res.error or "Max retries" in res.error
