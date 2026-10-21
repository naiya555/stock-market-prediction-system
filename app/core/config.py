"""Application Configuration Module.

Provides centralized, environment-aware configuration with safe defaults.
Does not store or hardcode secrets. Supports overriding via .env / environment variables.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional

# Attempt to load local .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_relative_path(raw_path: Optional[str], default_path: Path) -> Path:
    """Resolve a raw path string against PROJECT_ROOT if relative, or return default."""
    if not raw_path or not raw_path.strip():
        return default_path
    p = Path(raw_path.strip())
    if p.is_absolute():
        return p.resolve()
    return (PROJECT_ROOT / p).resolve()


@dataclass(frozen=True)
class Settings:
    """Immutable application settings container."""

    app_name: str = "Indian Stock Market Prediction System"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    timezone: str = "Asia/Kolkata"

    # Directory paths
    base_dir: Path = field(default_factory=lambda: PROJECT_ROOT)
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    model_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "models")
    database_path: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "predictions.db")

    # Security & CORS origins (restricted to trusted local web environments by default)
    cors_origins: tuple = field(
        default_factory=lambda: (
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        )
    )

    # Local Ollama LLM integration settings
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:12b"
    ollama_timeout_seconds: float = 30.0
    ollama_enabled: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables with safe defaults."""
        env = os.getenv("APP_ENV", "development").lower()
        debug_val = os.getenv("APP_DEBUG", "false").lower() in ("1", "true", "yes", "on")
        log_level = os.getenv("APP_LOG_LEVEL", "INFO").upper()
        timezone = os.getenv("APP_TIMEZONE", "Asia/Kolkata")

        custom_data_dir = os.getenv("APP_DATA_DIR")
        custom_model_dir = os.getenv("APP_MODEL_DIR") or os.getenv("MODEL_DIR")
        custom_db_path = os.getenv("DATABASE_PATH")

        resolved_data_dir = _resolve_relative_path(custom_data_dir, PROJECT_ROOT / "data")
        resolved_model_dir = _resolve_relative_path(custom_model_dir, PROJECT_ROOT / "models")
        resolved_db_path = _resolve_relative_path(custom_db_path, resolved_data_dir / "predictions.db")

        cors_env = os.getenv("APP_CORS_ORIGINS")
        if cors_env:
            cors_list = tuple(origin.strip() for origin in cors_env.split(",") if origin.strip())
        else:
            cors_list = (
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            )

        if env == "production" and cors_env:
            if any(origin == "*" for origin in cors_list):
                raise ValueError(
                    "Wildcard CORS origin '*' is strictly prohibited in production. Specify explicit trusted domain(s)."
                )
            for origin in cors_list:
                if origin.startswith("http://") and not any(h in origin for h in ("localhost", "127.0.0.1")):
                    raise ValueError(
                        f"Insecure HTTP origin '{origin}' is strictly prohibited in production CORS settings (must use HTTPS)."
                    )

        # Ollama settings from environment
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        ollama_model = os.getenv("OLLAMA_MODEL", "gemma3:12b").strip()
        try:
            ollama_timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30.0"))
        except ValueError:
            ollama_timeout = 30.0

        ollama_enabled_raw = os.getenv("OLLAMA_ENABLED", "true").lower()
        ollama_enabled = ollama_enabled_raw in ("1", "true", "yes", "on")

        return cls(
            app_name=os.getenv("APP_NAME", "Indian Stock Market Prediction System"),
            environment=env,
            debug=debug_val,
            log_level=log_level,
            timezone=timezone,
            base_dir=PROJECT_ROOT,
            data_dir=resolved_data_dir,
            model_dir=resolved_model_dir,
            database_path=resolved_db_path,
            cors_origins=cors_list,
            ollama_base_url=ollama_base_url,
            ollama_model=ollama_model,
            ollama_timeout_seconds=ollama_timeout,
            ollama_enabled=ollama_enabled,
        )

    def is_production(self) -> bool:
        """Check whether the active environment is production."""
        return self.environment == "production"

    def is_testing(self) -> bool:
        """Check whether the active environment is testing."""
        return self.environment == "testing"


# Cached singleton instance
_settings: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """Retrieve the cached application settings instance or create one."""
    global _settings
    if _settings is None or reload:
        _settings = Settings.from_env()
    return _settings
