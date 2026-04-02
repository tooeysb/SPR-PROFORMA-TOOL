"""
Request context using contextvars for correlation ID propagation.

Stores the current request ID so that loggers, error handlers, and
any code running within a request can access it without passing it explicitly.
"""

import contextvars
import uuid

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    """Get the current request's correlation ID."""
    return _request_id_var.get()


def set_request_id(request_id: str | None = None) -> str:
    """Set the current request's correlation ID.

    Args:
        request_id: An explicit ID to use, or None to generate a new UUID.

    Returns:
        The request ID that was set.
    """
    if request_id is None:
        request_id = uuid.uuid4().hex[:12]
    _request_id_var.set(request_id)
    return request_id
