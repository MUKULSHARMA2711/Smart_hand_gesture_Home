"""Maps every error to one JSON envelope: ``{"error": {"code", "message", "details"}}``.

Domain errors keep their own code; framework errors (unknown route, wrong method,
malformed request) and unexpected exceptions are mapped here, so clients never have
to parse a second error format.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.ai.errors import AIUnavailableError
from app.api.schemas import ErrorDetail, ErrorResponse
from app.domain.errors import (
    DeviceNotFoundError,
    DeviceStateMismatchError,
    DeviceTimeoutError,
    DeviceUnavailableError,
    DomainError,
    IntentNotApplicableError,
    InvalidCommandError,
    UnsupportedCommandError,
)
from app.gestures.errors import GestureActionBlockedError, GestureRejectedError
from app.ml.errors import InvalidFeatureError, MLUnavailableError, PredictionNotSupportedError

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    DeviceNotFoundError: 404,
    UnsupportedCommandError: 400,
    InvalidCommandError: 422,
    DeviceUnavailableError: 503,
    DeviceTimeoutError: 504,  # the device did not acknowledge in time
    DeviceStateMismatchError: 502,  # the device acknowledged with a state that does not reflect the command
    IntentNotApplicableError: 400,
    GestureRejectedError: 422,
    GestureActionBlockedError: 403,
    PredictionNotSupportedError: 400,
    InvalidFeatureError: 422,
    MLUnavailableError: 503,
    AIUnavailableError: 503,
}

_HTTP_CODES = {404: "not_found", 405: "method_not_allowed"}


def _status_for(exc: DomainError) -> int:
    # Walk the class hierarchy so subclasses inherit their base error's status.
    for cls in type(exc).__mro__:
        if cls in _STATUS_BY_ERROR:
            return _STATUS_BY_ERROR[cls]
    return 400


def _error_response(status_code: int, code: str, message: str, details: object = None) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return _error_response(_status_for(exc), exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return _error_response(
            422, "invalid_request", "Request validation failed.", errors
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        message = (
            f"No endpoint matches {request.method} {request.url.path}."
            if exc.status_code in _HTTP_CODES
            else str(exc.detail)
        )
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Log the full traceback server-side; never leak internals to the client.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error_response(500, "internal_error", "An unexpected server error occurred.")
