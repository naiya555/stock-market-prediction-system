"""Centralized Application Logging Module.

Provides consistent formatting, configurable log levels, and timestamped output
for all system components without heavy external observability frameworks.
"""

import logging
import sys
from typing import Optional

# Standard structured log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_logging_initialized = False


def setup_logging(log_level: Optional[str] = None) -> None:
    """Initialize the root application logging configuration.

    Args:
        log_level: Desired log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                   Defaults to INFO if unspecified.
    """
    global _logging_initialized

    level_name = (log_level or "INFO").upper()
    numeric_level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers on re-initialization
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)

    _logging_initialized = True


def get_logger(name: str) -> logging.Logger:
    """Obtain a namespaced logger instance.

    Args:
        name: Hierarchical module name (typically __name__).

    Returns:
        logging.Logger configured for the application.
    """
    if not _logging_initialized:
        setup_logging()
    return logging.getLogger(name)
