"""Indian Stock Market Prediction System - Day 1 Foundation Entry Point."""

import sys
from pathlib import Path


def main() -> int:
    """Verify application foundation and environment readiness."""
    print("Stock Market Prediction System")
    print("Day 1 environment ready")
    print(f"Python runtime: {sys.version.split()[0]}")
    print(f"Project root: {Path(__file__).resolve().parent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
