from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain.intents import Intent
from app.events.models import DeviceEvent


class Gesture(StrEnum):
    THUMBS_UP = "THUMBS_UP"
    FIST = "FIST"
    OPEN_PALM = "OPEN_PALM"
    ONE_FINGER = "ONE_FINGER"
    TWO_FINGERS = "TWO_FINGERS"
    NEUTRAL = "NEUTRAL"  # no hand in view
    UNKNOWN = "UNKNOWN"  # hand in view, no gesture recognised


# The canonical gesture -> intent mapping. Gestures never name a device or device action.
GESTURE_INTENTS: Mapping[Gesture, Intent] = MappingProxyType(
    {
        Gesture.THUMBS_UP: Intent.TURN_ON,
        Gesture.FIST: Intent.TURN_OFF,
        Gesture.OPEN_PALM: Intent.STOP,
        Gesture.ONE_FINGER: Intent.SELECT,
        Gesture.TWO_FINGERS: Intent.TOGGLE,
        Gesture.NEUTRAL: Intent.NONE,
        Gesture.UNKNOWN: Intent.NONE,
    }
)


class GestureCommand(BaseModel):
    """A recognised gesture aimed at a target device."""

    model_config = ConfigDict(frozen=True)

    gesture: Gesture
    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    target_device_id: str = Field(min_length=1, max_length=64)
    # Only for value intents (the future pinch adjustment sends one value, on release).
    value: int | None = Field(default=None, strict=True)


class GestureOutcome(StrEnum):
    EXECUTED = "executed"  # a device command ran successfully
    ACKNOWLEDGED = "acknowledged"  # valid targeting gesture (SELECT); no device command
    REJECTED = "rejected"  # refused before reaching the device (confidence, mismatch, policy...)
    FAILED = "failed"  # the device command itself failed


class GestureEvent(BaseModel):
    """History record of one gesture command, whatever its outcome."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    gesture: Gesture
    confidence: float
    intent: Intent
    target_device_id: str
    value: int | None = None
    action: str | None = None
    outcome: GestureOutcome
    detail: str | None = None
    device_event_id: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success(self) -> bool:
        return self.outcome in (GestureOutcome.EXECUTED, GestureOutcome.ACKNOWLEDGED)


@dataclass(frozen=True)
class GestureCommandResult:
    gesture_event: GestureEvent
    device_event: DeviceEvent | None
