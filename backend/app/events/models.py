from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class CommandSource(StrEnum):
    """Who issued a command. Only ``frontend`` is used today."""

    FRONTEND = "frontend"
    AUTOMATION = "automation"
    GESTURE = "gesture"
    AI_AGENT = "ai_agent"
    MQTT = "mqtt"


class DeviceEvent(BaseModel):
    """Audit record of one successful device action."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    device_id: str
    action: str
    value: Any = None
    previous_state: dict[str, Any]
    new_state: dict[str, Any]
    source: CommandSource
