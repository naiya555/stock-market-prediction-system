"""Unit and Regression Tests for Security Audit and Deployment Readiness (Phase 16).

Validates:
1. Production CORS origin lockdown (rejection of wildcards, insecure HTTP, and unconfigured defaults).
2. Production debug mode prohibition (prevents stack trace / memory leak exposure).
3. Production OpenAPI documentation disabling (/docs, /redoc, /openapi.json disabled).
4. Defensive HTTP security headers (nosniff, DENY, strict-origin-when-cross-origin, permissions-policy).
5. Effective runtime CORS enforcement across trusted and untrusted origins.
"""

import os
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from app.api.app import create_app
from app.core.config import Settings, get_settings


def test_production_cors_rejects_wildcard():
    """Verify Settings.from_env() rejects wildcard '*' in production CORS."""
    with patch.dict(os.environ, {"APP_ENV": "production", "APP_CORS_ORIGINS": "*"}):
        with pytest.raises(ValueError, match="Wildcard CORS origin '\\*' is strictly prohibited in production"):
            Settings.from_env()


def test_production_cors_rejects_insecure_http():
    """Verify Settings.from_env() rejects non-localhost HTTP origins in production."""
    with patch.dict(os.environ, {"APP_ENV": "production", "APP_CORS_ORIGINS": "http://insecure-domain.com"}):
        with pytest.raises(ValueError, match="Insecure HTTP origin 'http://insecure-domain.com' is strictly prohibited"):
            Settings.from_env()


def test_production_cors_requires_explicit_configuration():
    """Verify create_app() rejects missing APP_CORS_ORIGINS in production."""
    env = os.environ.copy()
    env["APP_ENV"] = "production"
    env.pop("APP_CORS_ORIGINS", None)
    with patch.dict(os.environ, env, clear=True):
        get_settings(reload=True)
        with pytest.raises(ValueError, match="APP_CORS_ORIGINS must be explicitly configured in production"):
            create_app()
    get_settings(reload=True)


def test_production_debug_mode_rejected():
    """Verify create_app() rejects APP_DEBUG=true in production environment."""
    with patch.dict(os.environ, {"APP_ENV": "production", "APP_DEBUG": "true", "APP_CORS_ORIGINS": "https://api.myfirm.in"}):
        get_settings(reload=True)
        with pytest.raises(ValueError, match="APP_DEBUG cannot be enabled in production"):
            create_app()
    get_settings(reload=True)


def test_production_valid_configuration():
    """Verify Settings.from_env() accepts valid HTTPS origins in production."""
    with patch.dict(os.environ, {"APP_ENV": "production", "APP_DEBUG": "false", "APP_CORS_ORIGINS": "https://app.myfirm.in,https://admin.myfirm.in"}):
        s = Settings.from_env()
        assert s.is_production() is True
        assert s.debug is False
        assert s.cors_origins == ("https://app.myfirm.in", "https://admin.myfirm.in")


def test_production_mode_disables_openapi_and_docs():
    """Verify /docs, /redoc, and /openapi.json are disabled in production mode."""
    with patch.dict(os.environ, {"APP_ENV": "production", "APP_DEBUG": "false", "APP_CORS_ORIGINS": "https://app.myfirm.in"}):
        # Force reload settings
        get_settings(reload=True)
        prod_app = create_app()
        client = TestClient(prod_app)

        # OpenAPI and interactive docs must be disabled (404 Not Found)
        res_docs = client.get("/docs")
        assert res_docs.status_code == 404

        res_redoc = client.get("/redoc")
        assert res_redoc.status_code == 404

        res_openapi = client.get("/openapi.json")
        assert res_openapi.status_code == 404

        # Root metadata should omit docs link in production
        res_root = client.get("/")
        assert res_root.status_code == 200
        assert res_root.json().get("docs") is None

    # Reset settings back to test/dev environment
    get_settings(reload=True)


def test_development_mode_enables_docs():
    """Verify /docs and /openapi.json remain active in development mode."""
    with patch.dict(os.environ, {"APP_ENV": "development"}):
        get_settings(reload=True)
        dev_app = create_app()
        client = TestClient(dev_app)

        res_docs = client.get("/docs")
        assert res_docs.status_code == 200

        res_openapi = client.get("/openapi.json")
        assert res_openapi.status_code == 200

    # Reset settings
    get_settings(reload=True)


def test_security_response_headers_present():
    """Verify defensive security headers are injected into all HTTP responses."""
    app = create_app()
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200

    # Verify OWASP defensive response headers
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in res.headers.get("Permissions-Policy", "")


def test_effective_cors_runtime_enforcement():
    """Verify runtime CORS middleware accepts trusted origin and denies untrusted origin."""
    trusted_origin = "https://dashboard.myfirm.in"
    untrusted_origin = "https://malicious-website.com"

    with patch.dict(os.environ, {"APP_ENV": "production", "APP_DEBUG": "false", "APP_CORS_ORIGINS": trusted_origin}):
        get_settings(reload=True)
        app = create_app()
        client = TestClient(app)

        # Trusted origin receives CORS allow header
        res_trusted = client.get("/api/health", headers={"Origin": trusted_origin})
        assert res_trusted.status_code == 200
        assert res_trusted.headers.get("access-control-allow-origin") == trusted_origin

        # Untrusted origin does not receive CORS allow header
        res_untrusted = client.get("/api/health", headers={"Origin": untrusted_origin})
        assert res_untrusted.status_code == 200
        assert res_untrusted.headers.get("access-control-allow-origin") is None

    # Reset settings
    get_settings(reload=True)
