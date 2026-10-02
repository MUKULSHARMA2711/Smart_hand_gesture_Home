"""Request/response models specific to the HTTP API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.devices.base import DeviceSnapshot
from app.devices.commands import DeviceCommand
from app.events.models import CommandSource, DeviceEvent


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
