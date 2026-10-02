from typing import Any

from app.devices.commands import CommandModel
from app.devices.specs.door import DOOR_LOCK_SPEC, DoorLockState, Lock, Unlock
from app.devices.virtual.base import VirtualDevice


class VirtualDoorLock(VirtualDevice[DoorLockState]):
    """Motorised smart lock; only standby power is modelled."""

    STANDBY_POWER_W = 0.8

    def __init__(self, device_id: str, name: str, room: str, **kwargs: Any) -> None:
        super().__init__(device_id, name, room, DOOR_LOCK_SPEC, **kwargs)

    def apply(self, state: DoorLockState, command: CommandModel) -> DoorLockState:
        match command:
            case Lock():
                return state.model_copy(update={"is_locked": True})
            case Unlock():
                return state.model_copy(update={"is_locked": False})
        raise NotImplementedError(command.action)

    @property
    def power_w(self) -> float:
        return self.STANDBY_POWER_W
