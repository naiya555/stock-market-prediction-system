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
                "APP_MODEL_DIR": str(temp_models),
                "APP_ENV": "development",
            },
        ):
            settings = get_settings(reload=True)
            assert settings.database_path == temp_db
            assert settings.model_dir == temp_models

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
                "APP_MODEL_DIR": str(temp_models),
                "APP_ENV": "development",
            },
        ):
            settings = get_settings(reload=True)
            assert settings.database_path == temp_db
            assert settings.model_dir == temp_models

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
                # Execute bounded soak simulation over real TCP sockets with resilient read timeout
                summary = run_soak_simulation(
                    total_requests=20,
                    concurrency=3,
                    base_url=base_url,
                    in_process=False,
                    request_timeout=(2.0, 15.0),
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


def test_env_templates_hygiene_and_security():
    """Verify .env.example and .env.production.example contain strictly safe placeholders."""
    project_root = Path(__file__).resolve().parent.parent

    # 1. Base .env.example must exist
    dev_example = project_root / ".env.example"
    assert dev_example.exists(), ".env.example must exist at project root."
    dev_content = dev_example.read_text(encoding="utf-8")
    assert "APP_ENV=development" in dev_content

    # 2. Production .env.production.example must exist
    prod_example = project_root / ".env.production.example"
    assert prod_example.exists(), ".env.production.example must exist for zero-cost deployment packaging."
    prod_content = prod_example.read_text(encoding="utf-8")

    # 3. Production template must enforce production and debug=false
    assert "APP_ENV=production" in prod_content
    assert "APP_DEBUG=false" in prod_content
    assert "APP_DEBUG=true" not in prod_content

    # 4. Mandatory CORS configuration with explicit HTTPS (no wildcards)
    assert "APP_CORS_ORIGINS=" in prod_content
    assert "https://" in prod_content
    # Ensure no wildcard origins are configured
    for line in prod_content.splitlines():
        if line.startswith("APP_CORS_ORIGINS="):
            origins = line.split("=", 1)[1].split(",")
            assert "*" not in origins
            assert not any("http://" in o and "localhost" not in o for o in origins)

    # 5. Security audit: no real secrets, passwords, or live tokens
    forbidden_tokens = ["api_key=", "secret_key=", "password=", "bearer ", "ghp_"]
    for token in forbidden_tokens:
        assert token not in dev_content.lower()
        assert token not in prod_content.lower()

    # 6. Storage variables alignment
    assert "APP_MODEL_DIR" in dev_content
    assert "APP_MODEL_DIR=" in prod_content
    assert "APP_DATA_DIR=" in prod_content
    assert "DATABASE_PATH=/var/lib/stock-predictor/data/predictions.db" in prod_content


def test_deployment_runbook_consistency_and_links():
    """Verify deployment runbook links exist, no absolute paths, and configuration variables are aligned."""
    import re
    project_root = Path(__file__).resolve().parent.parent
    runbook_path = project_root / "docs" / "deployment-runbook.md"
    assert runbook_path.exists(), "docs/deployment-runbook.md must exist."
    content = runbook_path.read_text(encoding="utf-8")

    # 1. No machine-specific absolute file URIs or windows drive letters in links
    assert "file:///" not in content
    assert "d:/share_market_predictor" not in content.lower()

    # 2. All markdown links must resolve to existing files
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    assert len(links) > 0, "Runbook should contain reference links."
    docs_dir = runbook_path.parent
    for text, link in links:
        if link.startswith("#"):
            continue
        resolved_link = (docs_dir / link).resolve()
        assert resolved_link.exists(), f"Broken link in runbook: {text} -> {link} (resolved: {resolved_link})"

    # 3. Model directory variable consistency
    assert "APP_MODEL_DIR" in content
    assert 'export APP_MODEL_DIR="/var/lib/stock-predictor/models"' in content
    assert '$env:APP_MODEL_DIR = "models"' in content

    # 4. Database path alignment across runbook, template, and recovery
    assert "DATABASE_PATH" in content
    assert "/var/lib/stock-predictor/data/predictions.db" in content
    assert 'sqlite3 /var/lib/stock-predictor/data/predictions.db ".backup' in content


def test_gitignore_deployment_safeguards():
    """Verify .gitignore blocks deployment secrets, local databases, and model weights."""
    project_root = Path(__file__).resolve().parent.parent
    gitignore_path = project_root / ".gitignore"
    assert gitignore_path.exists(), ".gitignore must exist."
    content = gitignore_path.read_text(encoding="utf-8")

    # Critical security ignores
    assert ".env\n" in content or ".env\r\n" in content
    assert ".env.*" in content
    assert "!.env.example" in content
    assert "!.env.*.example" in content

    # Database and model weights ignores
    assert "*.db" in content
    assert "*.db-wal" in content
    assert "models/*" in content
    assert "!models/.gitkeep" in content
    assert "*.log" in content
