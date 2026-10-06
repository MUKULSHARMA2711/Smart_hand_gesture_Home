"""The device abstraction that all business logic depends on."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.devices.commands import CommandModel, DeviceCommand
from app.devices.specs.base import CommandDescriptor, DeviceSpec
from app.devices.types import Capability, DeviceStatus, DeviceType
from app.domain.errors import DeviceUnavailableError


class DeviceSnapshot(BaseModel):
    """Serializable view of a device at a point in time."""

    id: str
    name: str
    device_type: DeviceType
    room: str
    status: DeviceStatus
    state: dict[str, Any]
    power_w: float
    capabilities: list[Capability]
    supported_commands: list[CommandDescriptor]
    driver: str = "virtual"
    # When the hardware last confirmed this state (None for virtual devices or before any report).
    last_confirmed_at: datetime | None = None


@dataclass(frozen=True)
class CommandResult:
    command: CommandModel
    previous_state: dict[str, Any]
    new_state: dict[str, Any]
    metadata: dict[str, Any] | None = None  # e.g. command_id, transport, acknowledgement latency


class Device(ABC):
    """Base class for every device, however it is connected.

    Implementations (``VirtualDevice`` today, ``ESP32MQTTDevice`` later) only decide
    *how* a validated command is carried out and how state and power are obtained.
    Validation lives in the shared :class:`DeviceSpec`, so callers see identical
    behaviour whichever implementation is wired in.
    """

    def __init__(self, device_id: str, name: str, room: str, spec: DeviceSpec[Any]) -> None:
        self._id = device_id
        self._name = name
        self._room = room
        self._spec = spec

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def room(self) -> str:
        return self._room

    @property
    def spec(self) -> DeviceSpec[Any]:
        return self._spec

    @property
    def device_type(self) -> DeviceType:
        return self._spec.device_type

    @property
    def driver(self) -> str:
        """How the device is connected (``virtual``, ``esp32_mqtt``); informational only."""
        return "virtual"

    @property
    def last_confirmed_at(self) -> datetime | None:
        return None

    @property
    def accepts_commands(self) -> bool:
        """Whether a command may be attempted now. Hardware may accept attempts while UNKNOWN."""
        return self.status is DeviceStatus.ONLINE

    @property
    @abstractmethod
    def status(self) -> DeviceStatus:
        """Connectivity/health of the device."""

    @property
    @abstractmethod
    def power_w(self) -> float:
        """Current power draw in watts, measured by hardware or estimated."""

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """Return the last known device state."""

    async def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Validate ``command`` against the device spec and carry it out."""
        validated = self._spec.parse_command(self._id, command)
        if not self.accepts_commands:
            raise DeviceUnavailableError(self._id, self.status, name=self._name)

        previous_state = self.get_state()
        metadata = await self._perform(validated)
        return CommandResult(
            command=validated, previous_state=previous_state, new_state=self.get_state(), metadata=metadata
        )

    @abstractmethod
    async def _perform(self, command: CommandModel) -> dict[str, Any] | None:
        """Carry out an already-validated command and update the known state.

        Must raise (and leave the known state unchanged) if the command did not take effect.
        May return metadata to attach to the command's event.
        """

    def snapshot(self) -> DeviceSnapshot:
        return DeviceSnapshot(
            id=self._id,
            name=self._name,
            device_type=self.device_type,
            room=self._room,
            status=self.status,
            state=self.get_state(),
            power_w=self.power_w,
            capabilities=self._spec.capabilities,
            supported_commands=self._spec.describe_commands(),
            driver=self.driver,
            last_confirmed_at=self.last_confirmed_at,
        )
