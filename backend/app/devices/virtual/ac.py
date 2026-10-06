from typing import Any

from app.devices.commands import CommandModel, TurnOff, TurnOn
from app.devices.power import ac_power
from app.devices.specs.ac import AC_SPEC, AcState, SetTemperature
from app.devices.virtual.base import VirtualDevice


class VirtualAC(VirtualDevice[AcState]):
    """1.5-ton inverter split AC; colder set points draw more power."""

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
        return ac_power(self.get_state())
