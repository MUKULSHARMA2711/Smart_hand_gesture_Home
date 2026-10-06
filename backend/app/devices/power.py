"""Estimated power draw per device type, from device state.

Shared by virtual devices and by hardware devices that have no fresh measured reading,
so both report identical estimates for the same state.
"""

from collections.abc import Callable, Mapping
from typing import Any

from app.devices.specs.ac import TEMPERATURE_MAX_C
from app.devices.specs.fan import SPEED_MAX
from app.devices.specs.light import BRIGHTNESS_MAX
from app.devices.types import DeviceType

# Dimmable smart LED bulb (~9 W at full brightness).
LIGHT_MAX_POWER_W = 9.0
LIGHT_STANDBY_POWER_W = 0.3
# Ceiling fan: ~12 W at the lowest speed, ~60 W at full speed.
FAN_MIN_POWER_W = 12.0
FAN_MAX_POWER_W = 60.0
FAN_STANDBY_POWER_W = 0.5
# 1.5-ton inverter split AC; colder set points draw more power.
AC_BASE_POWER_W = 700.0
AC_WATTS_PER_DEGREE = 70.0
AC_STANDBY_POWER_W = 2.0
# Motorised smart lock: standby only.
DOOR_STANDBY_POWER_W = 0.8


def light_power(state: Mapping[str, Any]) -> float:
    if not state["is_on"]:
        return LIGHT_STANDBY_POWER_W
    return round(LIGHT_STANDBY_POWER_W + LIGHT_MAX_POWER_W * state["brightness"] / BRIGHTNESS_MAX, 2)


def fan_power(state: Mapping[str, Any]) -> float:
    if not state["is_on"]:
        return FAN_STANDBY_POWER_W
    return round(FAN_MIN_POWER_W + (FAN_MAX_POWER_W - FAN_MIN_POWER_W) * state["speed"] / SPEED_MAX, 2)


def ac_power(state: Mapping[str, Any]) -> float:
    if not state["is_on"]:
        return AC_STANDBY_POWER_W
    return round(AC_BASE_POWER_W + AC_WATTS_PER_DEGREE * (TEMPERATURE_MAX_C - state["target_temperature_c"]), 2)


def door_power(state: Mapping[str, Any]) -> float:
    return DOOR_STANDBY_POWER_W


POWER_MODELS: dict[DeviceType, Callable[[Mapping[str, Any]], float]] = {
    DeviceType.LIGHT: light_power,
    DeviceType.FAN: fan_power,
    DeviceType.AC: ac_power,
    DeviceType.DOOR_LOCK: door_power,
}
