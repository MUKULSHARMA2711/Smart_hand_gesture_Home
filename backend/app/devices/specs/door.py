"""Door lock: locked/unlocked."""

from typing import Literal

from pydantic import BaseModel

from app.devices.commands import CommandModel
from app.devices.specs.base import DeviceSpec
from app.devices.types import Capability, DeviceType


class DoorLockState(BaseModel):
    is_locked: bool = True


class Lock(CommandModel):
    capability = Capability.LOCK
    action: Literal["lock"] = "lock"

    def effect(self) -> dict:
        return {"is_locked": True}


class Unlock(CommandModel):
    capability = Capability.UNLOCK
    action: Literal["unlock"] = "unlock"

    def effect(self) -> dict:
        return {"is_locked": False}


DOOR_LOCK_SPEC = DeviceSpec(DeviceType.DOOR_LOCK, DoorLockState, [Lock, Unlock])
