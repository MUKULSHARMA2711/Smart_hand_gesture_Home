"""Request/response models specific to the HTTP API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.devices.base import DeviceSnapshot
from app.devices.commands import DeviceCommand
from app.devices.types import Capability
from app.domain.intents import Intent
from app.events.models import CommandSource, DeviceEvent
from app.gestures.models import Gesture, GestureCommand, GestureEvent


class CommandRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"action": "turn_on"},
                {"action": "set_brightness", "value": 70},
            ]
        },
    )

    action: str = Field(min_length=1, max_length=64)
    value: Any = None
    source: CommandSource = CommandSource.FRONTEND

    def to_command(self) -> DeviceCommand:
        return DeviceCommand(action=self.action, value=self.value)


class CommandResponse(BaseModel):
    event: DeviceEvent
    device: DeviceSnapshot


class GestureCommandRequest(BaseModel):
    """A gesture recognised on the client. Only the result is sent, never video frames."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "gesture": "THUMBS_UP",
                    "intent": "TURN_ON",
                    "confidence": 0.96,
                    "target_device_id": "light_living_room",
                }
            ]
        },
    )

    gesture: Gesture
    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    target_device_id: str = Field(min_length=1, max_length=64)

    def to_command(self) -> GestureCommand:
        return GestureCommand(**self.model_dump())


class GestureCommandResponse(BaseModel):
    gesture_event: GestureEvent
    device_event: DeviceEvent | None
    device: DeviceSnapshot


class AICommandRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"message": "Turn on the living room light"}, {"message": "I'm leaving home"}]},
    )

    message: str = Field(min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message must not be blank.")
        return value.strip()


class DeviceCapabilities(BaseModel):
    device_id: str
    name: str
    device_type: str
    capabilities: list[Capability]


class AIStatusResponse(BaseModel):
    provider: str
    model: str
    mock: bool
    intents: list[Intent]
    devices: list[DeviceCapabilities]
    security_policy: dict[str, Any]


class GestureMapping(BaseModel):
    gesture: Gesture
    intent: Intent


class GestureConfigResponse(BaseModel):
    confidence_threshold: float
    blocked_actions: list[str]
    gestures: list[GestureMapping]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str


class RootResponse(BaseModel):
    name: str
    description: str
    status: str
    docs: str | None
    api: str
