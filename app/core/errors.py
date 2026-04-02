"""
Standardized error handling for the API.

All error responses follow the envelope format:
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable description",
        "request_id": "abc123def456"
    }
}
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.core.request_context import get_request_id

logger = get_logger(__name__)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Build a standardized error JSON response."""
    body: dict = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    request_id = get_request_id()
    if request_id:
        body["error"]["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=body)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException with standard envelope."""
    code = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
    }.get(exc.status_code, "ERROR")

    return _error_response(exc.status_code, code, str(exc.detail))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with standard envelope."""
    errors = exc.errors()
    if errors:
        first = errors[0]
        field = " -> ".join(str(loc) for loc in first.get("loc", []))
        msg = f"{field}: {first.get('msg', 'Invalid value')}"
    else:
        msg = "Request validation failed"

    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, msg)
    return _error_response(422, "VALIDATION_ERROR", msg)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — log the full traceback."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")


def register_error_handlers(app: FastAPI) -> None:
    """Attach all custom error handlers to the FastAPI app."""
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]
