"""Command models shared by every device implementation."""

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.devices.types import Capability


class DeviceCommand(BaseModel):
    """An unvalidated command addressed to a device.

    This is the transport-agnostic shape every caller uses: the REST API today, and
    automations, the gesture pipeline, the AI agent or an MQTT bridge later. It is
    validated against the target device's :class:`DeviceSpec` before execution.
    """

    model_config = ConfigDict(frozen=True)

    action: str = Field(min_length=1, max_length=64)
    value: Any = None


class CommandModel(BaseModel):
    """Base class for a validated, device-type specific command.

    Every concrete command declares the single ``capability`` it provides.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    capability: ClassVar[Capability]
    action: str

    @property
    def argument(self) -> Any:
        """The command's value, or ``None`` for commands that take none."""
        return getattr(self, "value", None)

    def effect(self) -> dict[str, Any]:
        """State fields this command must produce. A device acknowledgement is only accepted
        as success if its reported state matches (see ESP32MQTTDevice)."""
        raise NotImplementedError(self.action)


class TurnOn(CommandModel):
    capability = Capability.TURN_ON
    action: Literal["turn_on"] = "turn_on"

    def effect(self) -> dict[str, Any]:
        return {"is_on": True}


class TurnOff(CommandModel):
    capability = Capability.TURN_OFF
    action: Literal["turn_off"] = "turn_off"

    def effect(self) -> dict[str, Any]:
        return {"is_on": False}
