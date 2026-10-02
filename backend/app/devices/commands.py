"""Command models shared by every device implementation."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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
    """Base class for a validated, device-type specific command."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: str

    @property
    def argument(self) -> Any:
        """The command's value, or ``None`` for commands that take none."""
        return getattr(self, "value", None)


class TurnOn(CommandModel):
    action: Literal["turn_on"] = "turn_on"


class TurnOff(CommandModel):
    action: Literal["turn_off"] = "turn_off"
