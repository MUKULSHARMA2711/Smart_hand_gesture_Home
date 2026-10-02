from typing import Any

from app.devices.commands import CommandModel, TurnOff, TurnOn
from app.devices.specs.light import BRIGHTNESS_MAX, LIGHT_SPEC, LightState, SetBrightness
from app.devices.virtual.base import VirtualDevice


class VirtualLight(VirtualDevice[LightState]):
    """Dimmable smart LED bulb (~9 W at full brightness)."""

    MAX_POWER_W = 9.0
    STANDBY_POWER_W = 0.3

    def __init__(self, device_id: str, name: str, room: str, **kwargs: Any) -> None:
        super().__init__(device_id, name, room, LIGHT_SPEC, **kwargs)

    def apply(self, state: LightState, command: CommandModel) -> LightState:
        match command:
            case TurnOn():
                # Resume the previous brightness; a light dimmed to 0 comes back at full.
                return state.model_copy(update={"is_on": True, "brightness": state.brightness or BRIGHTNESS_MAX})
            case TurnOff():
                return state.model_copy(update={"is_on": False})
            case SetBrightness(value=level):
                return state.model_copy(update={"is_on": level > 0, "brightness": level})
        raise NotImplementedError(command.action)

    @property
    def power_w(self) -> float:
        if not self.state.is_on:
            return self.STANDBY_POWER_W
        return round(self.STANDBY_POWER_W + self.MAX_POWER_W * self.state.brightness / BRIGHTNESS_MAX, 2)
