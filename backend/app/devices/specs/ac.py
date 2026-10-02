"""Air conditioner: on/off with a target temperature (16-30 °C)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.devices.commands import CommandModel, TurnOff, TurnOn
from app.devices.specs.base import DeviceSpec
from app.devices.types import DeviceType

TEMPERATURE_MIN_C = 16
TEMPERATURE_MAX_C = 30
DEFAULT_TEMPERATURE_C = 24


class AcState(BaseModel):
    is_on: bool = False
    target_temperature_c: int = Field(
        default=DEFAULT_TEMPERATURE_C, ge=TEMPERATURE_MIN_C, le=TEMPERATURE_MAX_C
    )


class SetTemperature(CommandModel):
    action: Literal["set_temperature"] = "set_temperature"
    value: int = Field(ge=TEMPERATURE_MIN_C, le=TEMPERATURE_MAX_C, strict=True)


AC_SPEC = DeviceSpec(DeviceType.AC, AcState, [TurnOn, TurnOff, SetTemperature])
