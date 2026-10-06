from typing import Any

from app.devices.commands import CommandModel, TurnOff, TurnOn
from app.devices.power import fan_power
from app.devices.specs.fan import DEFAULT_SPEED, FAN_SPEC, FanState, SetSpeed
from app.devices.virtual.base import VirtualDevice


class VirtualFan(VirtualDevice[FanState]):
    """Ceiling fan drawing ~12 W at the lowest speed and ~60 W at full speed."""

    def __init__(self, device_id: str, name: str, room: str, **kwargs: Any) -> None:
        super().__init__(device_id, name, room, FAN_SPEC, **kwargs)

    def apply(self, state: FanState, command: CommandModel) -> FanState:
        match command:
            case TurnOn():
                return state.model_copy(update={"is_on": True, "speed": state.speed or DEFAULT_SPEED})
            case TurnOff():
                return state.model_copy(update={"is_on": False})
            case SetSpeed(value=speed):
                return state.model_copy(update={"is_on": speed > 0, "speed": speed})
        raise NotImplementedError(command.action)

    @property
    def power_w(self) -> float:
        return fan_power(self.get_state())
