"""JSON message contract between the backend and ESP32 firmware (real or FakeESP32).

All timestamps are ISO 8601 with a timezone (the firmware syncs its clock over NTP).
Decoding is strict: anything that does not match is rejected with :class:`MessageError`
and never reaches device state.
"""

import json
import math
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.mqtt.errors import MessageError

_ID_PATTERN = r"^[a-z0-9_]+$"


class CommandMessage(BaseModel):
    """Published by the backend on ``home/{device_id}/set``.

    ``expires_at`` lets firmware drop a command that arrives after the backend has already
    reported it as timed out (e.g. delivered late after a reconnect), so a failed command
    never takes effect later by surprise.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    command_id: str
    device_id: str = Field(pattern=_ID_PATTERN)
    action: str = Field(min_length=1, max_length=64)
    parameters: dict[str, Any] = Field(default_factory=dict)
    issued_at: AwareDatetime
    expires_at: AwareDatetime

    @field_validator("command_id")
    @classmethod
    def uuid(cls, value: str) -> str:
        return _uuid(value)

    @classmethod
    def create(
        cls, device_id: str, action: str, parameters: dict[str, Any], *, ttl_s: float, now: datetime | None = None
    ) -> "CommandMessage":
        issued = now or datetime.now(UTC)
        return cls(
            command_id=str(uuid4()),
            device_id=device_id,
            action=action,
            parameters=parameters,
            issued_at=issued,
            expires_at=issued + timedelta(seconds=ttl_s),
        )


class StateMessage(BaseModel):
    """Published by the device on ``home/{device_id}/state`` (retained).

    ``command_id`` names the command this state acknowledges, or is null for a report the
    device makes on its own (boot, a physical button press).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    device_id: str = Field(pattern=_ID_PATTERN)
    command_id: str | None = None
    timestamp: AwareDatetime
    state: dict[str, Any]

    @field_validator("command_id")
    @classmethod
    def uuid(cls, value: str | None) -> str | None:
        return None if value is None else _uuid(value)


class SensorMessage(BaseModel):
    """Published on ``home/sensors/{kind}``. For occupancy, ``value`` is the occupant count
    (a simple PIR sensor publishes 0 or 1)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sensor_id: str = Field(min_length=1, max_length=64)
    timestamp: AwareDatetime
    value: float

    @field_validator("value")
    @classmethod
    def finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("must be a finite number")
        return value


class EnergyMessage(BaseModel):
    """Published on ``home/energy/{device_id}`` by a device with a power meter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    timestamp: AwareDatetime
    power_w: float = Field(ge=0, le=20_000, allow_inf_nan=False)


def _uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, AttributeError, TypeError):
        raise ValueError("must be a UUID") from None


def encode(message: BaseModel) -> bytes:
    return message.model_dump_json().encode()


def decode[M: BaseModel](model: type[M], payload: bytes | str) -> M:
    """Parse and validate a JSON payload, or raise MessageError (never a raw exception)."""
    try:
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MessageError(f"Not valid JSON: {exc}") from None
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(str(p) for p in e['loc']) or 'message'}: {e['msg']}" for e in exc.errors())
        raise MessageError(f"Invalid {model.__name__}: {problems}") from None


def decode_availability(payload: bytes | str) -> str:
    text = (payload.decode(errors="replace") if isinstance(payload, bytes) else payload).strip().lower()
    if text not in ("online", "offline"):
        raise MessageError(f"Availability must be 'online' or 'offline', not {text[:20]!r}")
    return text
