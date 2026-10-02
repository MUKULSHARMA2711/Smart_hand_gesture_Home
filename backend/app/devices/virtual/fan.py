from typing import Any

from app.devices.commands import CommandModel, TurnOff, TurnOn
from app.devices.specs.fan import DEFAULT_SPEED, FAN_SPEC, SPEED_MAX, FanState, SetSpeed
from app.devices.virtual.base import VirtualDevice


class VirtualFan(VirtualDevice[FanState]):
    """Ceiling fan drawing ~12 W at the lowest speed and ~60 W at full speed."""

    MIN_POWER_W = 12.0
    MAX_POWER_W = 60.0
    STANDBY_POWER_W = 0.5

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
        if not self.state.is_on:
            return self.STANDBY_POWER_W
        span = self.MAX_POWER_W - self.MIN_POWER_W
        return round(self.MIN_POWER_W + span * self.state.speed / SPEED_MAX, 2)
