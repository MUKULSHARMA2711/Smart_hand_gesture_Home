"""Base class for devices simulated entirely in memory."""

import asyncio
from abc import abstractmethod
from typing import Any, Generic

from app.devices.base import Device
from app.devices.commands import CommandModel
from app.devices.specs.base import DeviceSpec, StateT
from app.devices.types import DeviceStatus


class VirtualDevice(Device, Generic[StateT]):
    """A software stand-in for a physical device.

    Subclasses implement :meth:`apply`, a pure function that mimics how the device
    firmware reacts to a command, and :attr:`power_w`, an estimate of the power draw.
    """

    def __init__(
        self,
        device_id: str,
        name: str,
        room: str,
        spec: DeviceSpec[StateT],
        *,
        initial_state: StateT | None = None,
        latency_s: float = 0.0,
    ) -> None:
        super().__init__(device_id, name, room, spec)
        self._state: StateT = initial_state if initial_state is not None else spec.state_model()
        self._latency_s = latency_s

    @property
    def status(self) -> DeviceStatus:
        return DeviceStatus.ONLINE

    @property
    def state(self) -> StateT:
        return self._state

    def get_state(self) -> dict[str, Any]:
        return self._state.model_dump()

    async def _perform(self, command: CommandModel) -> None:
        if self._latency_s > 0:
            await asyncio.sleep(self._latency_s)  # mimic the network/firmware round trip
        self._state = self.apply(self._state, command)

    @abstractmethod
    def apply(self, state: StateT, command: CommandModel) -> StateT:
        """Return the state that results from applying ``command`` to ``state``."""
