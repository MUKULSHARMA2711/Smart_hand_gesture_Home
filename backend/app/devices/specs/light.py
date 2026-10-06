"""Light: on/off with dimmable brightness (0-100 %)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.devices.commands import CommandModel, TurnOff, TurnOn
from app.devices.specs.base import DeviceSpec
from app.devices.types import Capability, DeviceType

BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 100


class LightState(BaseModel):
    is_on: bool = False
    brightness: int = Field(default=BRIGHTNESS_MAX, ge=BRIGHTNESS_MIN, le=BRIGHTNESS_MAX)


class SetBrightness(CommandModel):
    capability = Capability.SET_BRIGHTNESS
    action: Literal["set_brightness"] = "set_brightness"
    value: int = Field(ge=BRIGHTNESS_MIN, le=BRIGHTNESS_MAX, strict=True)

    def effect(self) -> dict:
        return {"brightness": self.value}


LIGHT_SPEC = DeviceSpec(DeviceType.LIGHT, LightState, [TurnOn, TurnOff, SetBrightness])
