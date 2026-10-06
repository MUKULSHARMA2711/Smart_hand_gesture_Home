from fastapi import APIRouter

from app.api.deps import MLServiceDep
from app.api.schemas import AnomalyCheckRequest, ErrorResponse, PredictRequest
from app.ml.models import AnomalyReport, AnomalyResult, MLStatus, Prediction

router = APIRouter(prefix="/ml", tags=["ml"])

_ERRORS = {
    400: {"model": ErrorResponse, "description": "No model for this device"},
    404: {"model": ErrorResponse, "description": "Unknown device"},
    422: {"model": ErrorResponse, "description": "Invalid request or feature names"},
    503: {"model": ErrorResponse, "description": "ML is unavailable"},
}


@router.get("/status", response_model=MLStatus, summary="Model versions, evaluation metrics and data notes")
async def ml_status(ml: MLServiceDep) -> MLStatus:
    return ml.status()


@router.post(
    "/predict",
    response_model=Prediction,
    responses=_ERRORS,
    summary="Predict whether a device will be needed soon (Random Forest)",
    description="Features are derived from the live HomeState; any provided `features` override them "
    "(null means 'missing' and is imputed). A prediction is a recommendation, never an action.",
)
async def predict(request: PredictRequest, ml: MLServiceDep) -> Prediction:
    return ml.predict(request.device_id, overrides=request.features)


@router.get("/anomalies", response_model=AnomalyReport, summary="Energy anomalies: live devices and recent readings")
async def anomalies(ml: MLServiceDep) -> AnomalyReport:
    return ml.anomaly_report()


@router.post(
    "/anomalies/check",
    response_model=AnomalyResult,
    responses=_ERRORS,
    summary="Assess one power reading (Isolation Forest)",
    description="Assesses a reading against the device's current setting. Anomalies are recorded in the "
    "event log with source 'ml'.",
)
async def check_reading(request: AnomalyCheckRequest, ml: MLServiceDep) -> AnomalyResult:
    return ml.check_reading(request.device_id, request.power_w, request.timestamp)
