from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class CommandSource(StrEnum):
    """Who issued a command or recorded an event."""

    FRONTEND = "frontend"
    AUTOMATION = "automation"
    GESTURE = "gesture"
    AI_AGENT = "ai_agent"
    MQTT = "mqtt"
    ML = "ml"  # observations only (e.g. energy anomalies); ML never issues commands


class DeviceEvent(BaseModel):
    """Audit record of a device action, or of an observation about a device (``event_type``)."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    device_id: str
    action: str
    value: Any = None
    previous_state: dict[str, Any]
    new_state: dict[str, Any]
    source: CommandSource
    event_type: str = "device_command"  # or "energy_anomaly"
    details: dict[str, Any] | None = None
