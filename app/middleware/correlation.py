"""
Correlation ID middleware.

Generates a unique request ID for each incoming request and propagates it
through the request context so that all log messages include it.

The ID is also returned in the X-Request-ID response header for client-side
correlation.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger
from app.core.request_context import set_request_id

logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to every request."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        # Accept client-provided ID or generate a new one
        incoming_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(incoming_id)

        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[call-arg]
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "%s %s %d %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response
