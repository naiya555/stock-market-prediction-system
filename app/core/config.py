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

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables with safe defaults."""
        env = os.getenv("APP_ENV", "development").lower()
        debug_val = os.getenv("APP_DEBUG", "false").lower() in ("1", "true", "yes", "on")
        log_level = os.getenv("APP_LOG_LEVEL", "INFO").upper()
        timezone = os.getenv("APP_TIMEZONE", "Asia/Kolkata")

        custom_data_dir = os.getenv("APP_DATA_DIR")
        custom_model_dir = os.getenv("APP_MODEL_DIR")

        return cls(
            app_name=os.getenv("APP_NAME", "Indian Stock Market Prediction System"),
            environment=env,
            debug=debug_val,
            log_level=log_level,
            timezone=timezone,
            base_dir=PROJECT_ROOT,
            data_dir=Path(custom_data_dir).resolve() if custom_data_dir else PROJECT_ROOT / "data",
            model_dir=Path(custom_model_dir).resolve() if custom_model_dir else PROJECT_ROOT / "models",
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
