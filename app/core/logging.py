"""
Structured logging configuration.

Usage in any module:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
"""

import logging
import os
import re


# Patterns to redact from log output
_REDACT_PATTERNS = [
    (re.compile(r"(password|secret|token|api_key|apikey)=\S+", re.IGNORECASE), r"\1=***REDACTED***"),
    (re.compile(r"(Bearer\s+)\S+", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(://[^:]+:)[^@]+(@)", re.IGNORECASE), r"\1***@"),
]


def _redact(message: str) -> str:
    """Remove sensitive values from log messages."""
    for pattern, replacement in _REDACT_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


def _is_production() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "production"


class RedactingFormatter(logging.Formatter):
    """Formatter that strips sensitive data from log messages."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return _redact(original)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger with redacting formatter.

    Args:
        name: Module name, typically __name__.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        formatter = RedactingFormatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, level, logging.INFO))

    return logger
