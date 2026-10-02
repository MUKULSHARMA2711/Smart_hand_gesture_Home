from typing import Any

from app.devices.commands import CommandModel, TurnOff, TurnOn
from app.devices.specs.ac import AC_SPEC, TEMPERATURE_MAX_C, AcState, SetTemperature
from app.devices.virtual.base import VirtualDevice


class VirtualAC(VirtualDevice[AcState]):
    """1.5-ton inverter split AC; colder set points draw more power."""

    BASE_POWER_W = 700.0
    WATTS_PER_DEGREE = 70.0
    STANDBY_POWER_W = 2.0

    def __init__(self, device_id: str, name: str, room: str, **kwargs: Any) -> None:
        super().__init__(device_id, name, room, AC_SPEC, **kwargs)

    def apply(self, state: AcState, command: CommandModel) -> AcState:
        match command:
            case TurnOn():
                return state.model_copy(update={"is_on": True})
            case TurnOff():
                return state.model_copy(update={"is_on": False})
            case SetTemperature(value=temperature):
                # Like a real remote: the set point changes even while the unit is off.
                return state.model_copy(update={"target_temperature_c": temperature})
        raise NotImplementedError(command.action)

    @property
    def power_w(self) -> float:
        if not self.state.is_on:
            return self.STANDBY_POWER_W
        degrees_below_max = TEMPERATURE_MAX_C - self.state.target_temperature_c
        return round(self.BASE_POWER_W + self.WATTS_PER_DEGREE * degrees_below_max, 2)
