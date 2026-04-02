"""
Structured logging configuration.

- Production: JSON-formatted output for log aggregators
- Development: Human-readable output with request IDs

Usage in any module:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
"""

import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import get_request_id

# Patterns to redact from log output
_REDACT_PATTERNS = [
    (
        re.compile(r"(password|secret|token|api_key|apikey)=\S+", re.IGNORECASE),
        r"\1=***REDACTED***",
    ),
    (re.compile(r"(Bearer\s+)\S+", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(://[^:]+:)[^@]+(@)", re.IGNORECASE), r"\1***@"),
    (
        re.compile(r"(jwt_secret_key|sendgrid_api_key|sso_jwt_secret)\s*[:=]\s*\S+", re.IGNORECASE),
        r"\1=***REDACTED***",
    ),
]


def _redact(message: str) -> str:
    """Remove sensitive values from log messages."""
    for pattern, replacement in _REDACT_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


def _is_production() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "production"


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production.

    Outputs one JSON object per line with fields:
    timestamp, level, logger, message, request_id, and any extras.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact(record.getMessage()),
        }

        # Include correlation/request ID if available
        request_id = get_request_id()
        if request_id:
            log_entry["request_id"] = request_id

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": _redact(str(record.exc_info[1])),
            }

        return json.dumps(log_entry, default=str)


class RedactingFormatter(logging.Formatter):
    """Human-readable formatter that strips sensitive data from log messages."""

    def format(self, record: logging.LogRecord) -> str:
        # Inject request_id into the record for the format string
        record.request_id = get_request_id() or "-"  # type: ignore[attr-defined]
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

        if _is_production():
            formatter: logging.Formatter = JSONFormatter()
        else:
            fmt = "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s"
            formatter = RedactingFormatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")

        handler.setFormatter(formatter)
        logger.addHandler(handler)

        level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, level, logging.INFO))

    return logger
