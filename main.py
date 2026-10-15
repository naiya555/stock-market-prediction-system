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
    print("Day 9 technical indicators (RSI & expanded history) ready")
    print("Day 10 MACD technical indicator ready")
    print("Day 11 Bollinger Bands ready")
    print("Day 12 ATR and ROC ready")
    print("Day 13 candlestick features ready")
    print("Day 14 trend engine ready")
    print("Day 15 ML prediction target ready")
    print("Day 16 technical feature matrix ready")
    print("Day 17 XGBoost direction classifier ready")
    print("Day 18 baseline comparison ready")
    print("Day 19 multi-year evaluation and LightGBM benchmark ready")
    print("Day 20 walk-forward temporal cross-validation ready")
    print("Day 21 model error analysis and feature usefulness audit ready")
    print("Day 22 prediction engine service foundation ready")
    print("Day 23 structured prediction output ready")
    print("Day 24 prediction database & immutable persistence ready")
    print("Day 25 prediction outcome verification & evaluation ready")
    print("Day 26 NIFTY benchmark & sector context engine ready")
    print(f"Python runtime: {sys.version.split()[0]}")
    print(f"Environment: {settings.environment}")
    print(f"Project root: {Path(__file__).resolve().parent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
