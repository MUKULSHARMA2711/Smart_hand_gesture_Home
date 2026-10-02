"""Fan: on/off with variable speed (0-100 %)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.devices.commands import CommandModel, TurnOff, TurnOn
from app.devices.specs.base import DeviceSpec
from app.devices.types import DeviceType

SPEED_MIN = 0
SPEED_MAX = 100
DEFAULT_SPEED = 50


class FanState(BaseModel):
    is_on: bool = False
    speed: int = Field(default=DEFAULT_SPEED, ge=SPEED_MIN, le=SPEED_MAX)


class SetSpeed(CommandModel):
    action: Literal["set_speed"] = "set_speed"
    value: int = Field(ge=SPEED_MIN, le=SPEED_MAX, strict=True)


FAN_SPEC = DeviceSpec(DeviceType.FAN, FanState, [TurnOn, TurnOff, SetSpeed])
