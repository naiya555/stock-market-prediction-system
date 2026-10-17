"""Centralized Application Logging Module.

Provides consistent formatting, configurable log levels, and timestamped output
for all system components without heavy external observability frameworks.
"""

import logging
import sys
from typing import Any, Optional

# Standard structured log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_logging_initialized = False


def sanitize_log_field(val: Any) -> str:
    """Sanitize arbitrary user-controlled or external field for safe log emission.

    Replaces control characters (including CR, LF, tabs, and non-printables) with escaped equivalents.
    """
    if val is None:
        return ""
    s = str(val)
    if not any(ord(c) < 32 or ord(c) == 127 for c in s):
        return s
    replacements = {"\r": "\\r", "\n": "\\n", "\t": "\\t"}
    out = []
    for c in s:
        if c in replacements:
            out.append(replacements[c])
        elif 32 <= ord(c) < 127:
            out.append(c)
        else:
            out.append(f"\\x{ord(c):02x}")
    return "".join(out)


class SafeLogFormatter(logging.Formatter):
    """Log formatter that neutralizes carriage returns, newlines, and control characters in records."""

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        if record.exc_text:
            parts = formatted.split("\nTraceback (most recent call last):\n", 1)
            msg_part = parts[0].replace("\r", "\\r").replace("\n", "\\n")
            return msg_part + "\nTraceback (most recent call last):\n" + parts[1]
        return formatted.replace("\r", "\\r").replace("\n", "\\n")


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
        formatter = SafeLogFormatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)
            handler.setFormatter(SafeLogFormatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT))

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
