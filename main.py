"""Indian Stock Market Prediction System - Main Entry Point."""

import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.logging_config import get_logger, setup_logging

logger = get_logger("app.main")


def main() -> int:
    """Verify application configuration, logging, and environment readiness."""
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info("Initializing %s in %s mode", settings.app_name, settings.environment)

    print("Stock Market Prediction System")
    print("Day 1 environment ready")
    print("Day 2 core foundation ready")
    print("Day 3 market data foundation ready")
    print("Day 4 historical collector ready")
    print("Day 5 data cleaning ready")
    print("Day 6 returns and volatility ready")
    print("Day 7 visualization pipeline ready")
    print("Day 8 moving averages ready")
    print(f"Python runtime: {sys.version.split()[0]}")
    print(f"Environment: {settings.environment}")
    print(f"Project root: {Path(__file__).resolve().parent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
