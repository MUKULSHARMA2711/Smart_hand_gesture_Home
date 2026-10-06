"""Maps domain and validation errors to a consistent JSON error envelope."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas import ErrorDetail, ErrorResponse
from app.domain.errors import (
    DeviceNotFoundError,
    DeviceUnavailableError,
    DomainError,
    IntentNotApplicableError,
    InvalidCommandError,
    UnsupportedCommandError,
)
from app.gestures.errors import GestureActionBlockedError, GestureRejectedError
from app.ml.errors import InvalidFeatureError, MLUnavailableError, PredictionNotSupportedError

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    DeviceNotFoundError: 404,
    UnsupportedCommandError: 400,
    InvalidCommandError: 422,
    DeviceUnavailableError: 503,
    IntentNotApplicableError: 400,
    GestureRejectedError: 422,
    GestureActionBlockedError: 403,
    PredictionNotSupportedError: 400,
    InvalidFeatureError: 422,
    MLUnavailableError: 503,
}


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
