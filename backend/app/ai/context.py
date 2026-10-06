"""Compact, implementation-free view of the home given to the AI."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.devices.types import Capability, DeviceStatus, DeviceType
from app.domain.home_state import EnergySnapshot, HomeState
from app.events.store import EventStore
from app.ml.models import MLInsights
from app.ml.service import MLService
from app.sensors.base import SensorReadings


class DeviceContext(BaseModel):
    id: str
    name: str
    type: DeviceType
    room: str
    status: DeviceStatus
    capabilities: list[Capability]
    state: dict[str, Any]
    power_w: float


class EventContext(BaseModel):
    timestamp: datetime
    device_id: str
    action: str
    value: Any = None
    source: str


class HomeContext(BaseModel):
    timestamp: datetime
    devices: list[DeviceContext]
    environment: SensorReadings
    energy: EnergySnapshot
    recent_events: list[EventContext]
    # Real ML output for this request (None when ML is unavailable). Never estimated by the planner.
    ml: MLInsights | None = None

    def device(self, device_id: str) -> DeviceContext | None:
        return next((device for device in self.devices if device.id == device_id), None)


def build_home_context(
    home: HomeState, events: EventStore, *, recent_events: int = 5, ml: MLService | None = None
) -> HomeContext:
    snapshot = home.snapshot()
    return HomeContext(
        timestamp=snapshot.timestamp,
        devices=[
            DeviceContext(
                id=d.id,
                name=d.name,
                type=d.device_type,
                room=d.room,
                status=d.status,
                capabilities=d.capabilities,
                state=d.state,
                power_w=d.power_w,
            )
            for d in snapshot.devices
        ],
        environment=snapshot.environment,
        energy=snapshot.energy,
        recent_events=[
            EventContext(
                timestamp=e.timestamp, device_id=e.device_id, action=e.action, value=e.value, source=e.source
            )
            for e in events.recent(limit=recent_events)
        ],
        ml=ml.insights(snapshot) if ml else None,
    )
