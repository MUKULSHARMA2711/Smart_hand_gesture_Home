import logging
from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter

from app.api.deps import MLServiceDep
from app.api.schemas import AnomalyCheckRequest, ErrorResponse, PredictRequest
from app.domain.errors import DomainError
from app.ml.errors import MLUnavailableError
from app.ml.models import AnomalyReport, AnomalyResult, MLStatus, Prediction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml", tags=["ml"])
T = TypeVar("T")

_ERRORS = {
    400: {"model": ErrorResponse, "description": "No model for this device"},
    404: {"model": ErrorResponse, "description": "Unknown device"},
    422: {"model": ErrorResponse, "description": "Invalid request or feature names"},
    503: {"model": ErrorResponse, "description": "ML is unavailable"},
}


def _run(operation: str, fn: Callable[[], T]) -> T:
    """A model failure becomes a clear 503 for this request; the rest of the backend is unaffected."""
    try:
        return fn()
    except DomainError:
        raise
    except Exception as exc:
        logger.exception("ML %s failed", operation)
        raise MLUnavailableError(f"The ML {operation} failed, so no result is available.") from exc


@router.get("/status", response_model=MLStatus, responses={503: _ERRORS[503]}, summary="Model versions, evaluation metrics and data notes")
async def ml_status(ml: MLServiceDep) -> MLStatus:
    return ml.status()


@router.post(
    "/predict",
    response_model=Prediction,
    responses=_ERRORS,
    summary="Predict whether a device will be needed soon (Random Forest)",
    description="Features are derived from the live HomeState; any provided `features` override them "
    "(null means 'missing' and is imputed). Values outside plausible ranges are rejected. "
    "A prediction is a recommendation, never an action.",
)
async def predict(request: PredictRequest, ml: MLServiceDep) -> Prediction:
    return _run("prediction", lambda: ml.predict(request.device_id, overrides=request.features))


@router.get(
    "/anomalies",
    response_model=AnomalyReport,
    responses={503: _ERRORS[503]},
    summary="Energy anomalies: live devices and recent readings",
)
async def anomalies(ml: MLServiceDep) -> AnomalyReport:
    return _run("anomaly check", ml.anomaly_report)


@router.post(
    "/anomalies/check",
    response_model=AnomalyResult,
    responses=_ERRORS,
    summary="Assess one power reading (Isolation Forest)",
    description="Assesses a reading against the device's current setting. Anomalies are recorded in the "
    "event log with source 'ml'.",
)
async def check_reading(request: AnomalyCheckRequest, ml: MLServiceDep) -> AnomalyResult:
    return _run("anomaly check", lambda: ml.check_reading(request.device_id, request.power_w, request.timestamp))
