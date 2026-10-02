"""Device specifications: the hardware-independent contract of each device type."""

from collections.abc import Iterable
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.devices.commands import CommandModel, DeviceCommand
from app.devices.types import DeviceType
from app.domain.errors import InvalidCommandError, UnsupportedCommandError

StateT = TypeVar("StateT", bound=BaseModel)

_VALUE_SCHEMA_KEYS = ("type", "minimum", "maximum")


class CommandDescriptor(BaseModel):
    """Machine-readable description of a supported command.

    Lets clients (the dashboard today, the AI agent later) discover what a device
    accepts and the valid value range, instead of hard-coding it.
    """

    action: str
    value: dict[str, Any] | None = None


class DeviceSpec(Generic[StateT]):
    """What a device type *is*: its state shape and the commands it accepts.

    A spec is shared by every implementation of a device type, so a virtual light
    and an ESP32 light validate commands identically.
    """

    def __init__(
        self,
        device_type: DeviceType,
        state_model: type[StateT],
        commands: Iterable[type[CommandModel]],
    ) -> None:
        self.device_type = device_type
        self.state_model = state_model
        self._commands: dict[str, type[CommandModel]] = {
            command.model_fields["action"].default: command for command in commands
        }
        self._descriptors = [_describe(action, model) for action, model in self._commands.items()]

    @property
    def supported_actions(self) -> list[str]:
        return list(self._commands)

    def describe_commands(self) -> list[CommandDescriptor]:
        return list(self._descriptors)

    def parse_command(self, device_id: str, command: DeviceCommand) -> CommandModel:
        """Turn a raw command into a typed one, or raise a domain error."""
        model = self._commands.get(command.action)
        if model is None:
            raise UnsupportedCommandError(device_id, command.action, self.supported_actions)

        payload: dict[str, Any] = {"action": command.action}
        if command.value is not None:
            payload["value"] = command.value
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            errors = [
                {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
                for error in exc.errors()
            ]
            raise InvalidCommandError(device_id, command.action, errors) from exc


def _describe(action: str, model: type[CommandModel]) -> CommandDescriptor:
    value_schema = model.model_json_schema().get("properties", {}).get("value")
    if value_schema is None:
        return CommandDescriptor(action=action)
    return CommandDescriptor(
        action=action,
        value={key: value_schema[key] for key in _VALUE_SCHEMA_KEYS if key in value_schema},
    )
