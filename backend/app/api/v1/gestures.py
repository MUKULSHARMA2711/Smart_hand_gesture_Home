from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import GestureHistoryDep, GestureServiceDep, HomeStateDep
from app.api.schemas import (
    ErrorResponse,
    GestureCommandRequest,
    GestureCommandResponse,
    GestureConfigResponse,
    GestureMapping,
)
from app.gestures.models import GESTURE_INTENTS, GestureEvent

router = APIRouter(prefix="/gestures", tags=["gestures"])


@router.get("/config", response_model=GestureConfigResponse, summary="Gesture mapping and confidence threshold")
async def get_gesture_config(gestures: GestureServiceDep) -> GestureConfigResponse:
    return GestureConfigResponse(
        confidence_threshold=gestures.confidence_threshold,
        blocked_actions=sorted(gestures.blocked_actions),
        gestures=[GestureMapping(gesture=g, intent=i) for g, i in GESTURE_INTENTS.items()],
    )


@router.post(
    "/commands",
    response_model=GestureCommandResponse,
    summary="Execute a recognised gesture on the target device",
    responses={
        400: {"model": ErrorResponse, "description": "Intent not applicable to the target device"},
        403: {"model": ErrorResponse, "description": "Action not allowed by gesture"},
        404: {"model": ErrorResponse, "description": "Unknown target device"},
        422: {"model": ErrorResponse, "description": "Invalid, mismatched, non-actionable or low-confidence gesture"},
    },
)
async def execute_gesture(
    request: GestureCommandRequest,
    gestures: GestureServiceDep,
    home: HomeStateDep,
) -> GestureCommandResponse:
    result = await gestures.handle(request.to_command())
    return GestureCommandResponse(
        gesture_event=result.gesture_event,
        device_event=result.device_event,
        device=home.devices.get(request.target_device_id).snapshot(),
        confirmation=result.confirmation,
    )


@router.get("/events", response_model=list[GestureEvent], summary="Recent gesture events, newest first")
async def list_gesture_events(
    history: GestureHistoryDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[GestureEvent]:
    return history.recent(limit=limit)
