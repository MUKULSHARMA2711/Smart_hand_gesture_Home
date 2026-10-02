"""Per-device-type contracts, independent of how a device is connected."""

from app.devices.specs.ac import AC_SPEC, AcState, SetTemperature
from app.devices.specs.base import CommandDescriptor, DeviceSpec
from app.devices.specs.door import DOOR_LOCK_SPEC, DoorLockState, Lock, Unlock
from app.devices.specs.fan import FAN_SPEC, FanState, SetSpeed
from app.devices.specs.light import LIGHT_SPEC, LightState, SetBrightness
from app.devices.types import DeviceType

SPECS_BY_TYPE: dict[DeviceType, DeviceSpec] = {
    spec.device_type: spec for spec in (LIGHT_SPEC, FAN_SPEC, AC_SPEC, DOOR_LOCK_SPEC)
}

__all__ = [
    "AC_SPEC",
    "DOOR_LOCK_SPEC",
    "FAN_SPEC",
    "LIGHT_SPEC",
    "SPECS_BY_TYPE",
    "AcState",
    "CommandDescriptor",
    "DeviceSpec",
    "DoorLockState",
    "FanState",
    "LightState",
    "Lock",
    "SetBrightness",
    "SetSpeed",
    "SetTemperature",
    "Unlock",
]
