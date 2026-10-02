from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import EventStoreDep
from app.events.models import DeviceEvent

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[DeviceEvent], summary="Recent device events, newest first")
async def list_events(
    events: EventStoreDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    device_id: str | None = None,
) -> list[DeviceEvent]:
    return events.recent(limit=limit, device_id=device_id)
