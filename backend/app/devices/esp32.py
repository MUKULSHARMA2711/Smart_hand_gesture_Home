"""A device behind an ESP32 that speaks the MQTT contract in app/mqtt.

It reuses everything hardware-independent: the device spec validates commands (in
``Device.execute_command``) and acknowledged states (``spec.state_model``), and
CommandService still serialises commands and records events. Only *how* a command is
carried out differs from a virtual device:

    publish command (unique command_id)
      → wait for home/{id}/state with the same command_id
      → validate the reported state against the spec, and check it reflects the command
      → only then commit it as the confirmed state

Publishing is never treated as success. On timeout, an offline report or a broker
disconnect the command fails and the confirmed state stays exactly as it was.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from app.devices.base import Device
from app.devices.commands import CommandModel
from app.devices.specs.base import DeviceSpec
from app.devices.types import DeviceStatus
from app.domain.errors import DeviceStateMismatchError, DeviceTimeoutError, DeviceUnavailableError
from app.mqtt import topics
from app.mqtt.errors import MessageError
from app.mqtt.messages import CommandMessage, EnergyMessage, StateMessage, decode, decode_availability, encode

logger = logging.getLogger(__name__)

_FINISHED_MEMORY = 64  # recently finished command ids, to recognise duplicate and late acknowledgements


class MQTTLink(Protocol):
    """What the device needs from the shared MQTT connection (implemented by MQTTManager)."""

    @property
    def connected(self) -> bool: ...

    def publish(self, topic: str, payload: bytes | str, *, qos: int = 1, retain: bool = False) -> bool: ...


class DeviceObserver(Protocol):
    """Receives changes the device reports on its own (implemented by MQTTManager)."""

    def before_state_change(self, device: "ESP32MQTTDevice") -> None: ...

    def state_reported(
        self, device: "ESP32MQTTDevice", previous: dict[str, Any], new: dict[str, Any], details: dict[str, Any]
    ) -> None: ...

    def availability_changed(self, device: "ESP32MQTTDevice", previous: DeviceStatus, new: DeviceStatus) -> None: ...


@dataclass
class _Pending:
    command: CommandModel
    future: asyncio.Future
    sent_at: float  # perf_counter (monotonic, high resolution)


class ESP32MQTTDevice(Device):
    def __init__(
        self,
        device_id: str,
        name: str,
        room: str,
        spec: DeviceSpec[Any],
        *,
        link: MQTTLink,
        power_model: Callable[[Mapping[str, Any]], float],
        command_timeout_s: float = 3.0,
        measurement_max_age_s: float = 30.0,
        observer: DeviceObserver | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        super().__init__(device_id, name, room, spec)
        self._link = link
        self._power_model = power_model
        self._timeout_s = command_timeout_s
        self._measurement_max_age_s = measurement_max_age_s
        self.observer = observer
        self._clock = clock

        self._confirmed: BaseModel | None = None
        self._confirmed_at: datetime | None = None  # backend clock: when the state was confirmed
        self._state_timestamp: datetime | None = None  # device clock: when the device reported it
        self._availability = DeviceStatus.UNKNOWN
        self._last_seen: datetime | None = None
        self._measured: EnergyMessage | None = None
        self._pending: dict[str, _Pending] = {}
        self._finished: OrderedDict[str, str] = OrderedDict()  # command_id -> "completed" | "expired"

    # --- Device interface -------------------------------------------------------------

    @property
    def driver(self) -> str:
        return "esp32_mqtt"

    @property
    def status(self) -> DeviceStatus:
        # Without the broker we cannot know; the last availability report may be stale.
        return self._availability if self._link.connected else DeviceStatus.UNKNOWN

    @property
    def accepts_commands(self) -> bool:
        # OFFLINE fails immediately. UNKNOWN may be attempted: the timeout bounds it.
        return self.status is not DeviceStatus.OFFLINE

    @property
    def last_confirmed_at(self) -> datetime | None:
        return self._confirmed_at

    @property
    def last_seen(self) -> datetime | None:
        return self._last_seen

    @property
    def has_confirmed_state(self) -> bool:
        return self._confirmed is not None

    def get_state(self) -> dict[str, Any]:
        # Until the device reports, the spec's defaults are shown with last_confirmed_at = None.
        return (self._confirmed or self._spec.state_model()).model_dump()

    @property
    def power_w(self) -> float:
        """Measured draw when a fresh reading taken after the last state change exists;
        otherwise the estimate for the confirmed state. A reading from before a change
        describes the old state (e.g. 0.3 W standby right after switching on) and would
        otherwise look like an energy anomaly. Both timestamps come from the device's clock,
        so clock skew between device and backend cannot reorder them."""
        measured = self._measured
        if (
            measured is not None
            and (self._clock() - measured.timestamp).total_seconds() <= self._measurement_max_age_s
            and (self._state_timestamp is None or measured.timestamp > self._state_timestamp)
        ):
            return round(measured.power_w, 2)
        return self._power_model(self.get_state())

    async def _perform(self, command: CommandModel) -> dict[str, Any]:
        if not self._link.connected:
            raise DeviceUnavailableError(self.id, "unreachable", name=self.name, reason="the MQTT broker is not connected.")

        message = CommandMessage.create(
            self.id, command.action, _parameters(command), ttl_s=self._timeout_s, now=self._clock()
        )
        command_id = message.command_id
        future = asyncio.get_running_loop().create_future()
        pending = _Pending(command, future, time.perf_counter())
        self._pending[command_id] = pending  # registered before publishing, so a fast ack is never missed
        try:
            if not self._link.publish(topics.device_set(self.id), encode(message), qos=1):
                raise DeviceUnavailableError(
                    self.id, "unreachable", name=self.name, reason="the command could not be published."
                )
            state, reported_at = await asyncio.wait_for(future, timeout=self._timeout_s)
        except TimeoutError:
            self._remember(command_id, "expired")
            if self._availability is DeviceStatus.ONLINE:
                self._set_availability(DeviceStatus.UNKNOWN)  # not responding; any later message restores ONLINE
            logger.warning("%s: no acknowledgement for %s within %.1f s", self.id, command_id, self._timeout_s)
            raise DeviceTimeoutError(self.id, self.name, self._timeout_s, command_id) from None
        finally:
            self._pending.pop(command_id, None)

        self._remember(command_id, "completed")
        self._commit(state, reported_at)
        latency_ms = round((time.perf_counter() - pending.sent_at) * 1000, 1)
        return {"transport": "mqtt", "command_id": command_id, "ack_latency_ms": latency_ms}

    # --- Incoming messages (called on the event loop by MQTTManager) --------------------

    def handle_state(self, payload: bytes) -> None:
        try:
            message = decode(StateMessage, payload)
        except MessageError as exc:
            logger.warning("%s: ignored malformed state message: %s", self.id, exc)
            return
        if message.device_id != self.id:
            logger.warning("%s: ignored state message addressed to %r", self.id, message.device_id)
            return
        try:
            state = self._spec.state_model.model_validate(message.state, strict=True)
        except ValidationError as exc:
            # An impossible state is never accepted; a pending command keeps waiting (and times out).
            logger.warning("%s: ignored impossible state %s (%s)", self.id, message.state, exc.errors()[0]["msg"])
            return

        self._seen()
        command_id = message.command_id
        pending = self._pending.get(command_id) if command_id else None
        at = message.timestamp
        if pending is not None:
            self._acknowledge(pending, command_id, state, at)
        elif command_id is None:
            self._report(state, at, reason="state_report")  # e.g. a physical button press or a reboot
        elif self._finished.get(command_id) == "completed":
            logger.debug("%s: ignored duplicate acknowledgement %s", self.id, command_id)
        elif self._finished.get(command_id) == "expired":
            # The device executed a command after we reported it as timed out: show the truth.
            self._remember(command_id, "completed")
            self._report(state, at, reason="late_acknowledgement", command_id=command_id)
        elif self._confirmed is None:
            self._report(state, at, reason="initial_sync", command_id=command_id)  # retained state at startup
        else:
            logger.warning("%s: ignored acknowledgement for unknown command %s", self.id, command_id)

    def handle_availability(self, payload: bytes) -> None:
        try:
            value = decode_availability(payload)
        except MessageError as exc:
            logger.warning("%s: ignored availability message: %s", self.id, exc)
            return
        if value == topics.ONLINE:
            self._seen()
            return
        self._set_availability(DeviceStatus.OFFLINE)
        self._fail_pending(DeviceUnavailableError(self.id, "offline", name=self.name))

    def handle_energy(self, payload: bytes) -> None:
        try:
            self._measured = decode(EnergyMessage, payload)
        except MessageError as exc:
            logger.warning("%s: ignored energy message: %s", self.id, exc)

    def connection_changed(self, connected: bool) -> None:
        if not connected:
            reason = "the connection to the MQTT broker was lost."
            self._fail_pending(DeviceUnavailableError(self.id, "unreachable", name=self.name, reason=reason))

    # --- Internals --------------------------------------------------------------------

    def _acknowledge(self, pending: _Pending, command_id: str, state: BaseModel, reported_at: datetime) -> None:
        if pending.future.done():
            return
        expected = pending.command.effect()
        reported = state.model_dump()
        if any(reported.get(field) != value for field, value in expected.items()):
            # Valid, but not what was asked: the command failed. The device's state is still the truth.
            pending.future.set_exception(DeviceStateMismatchError(self.id, self.name, expected, reported, command_id))
            self._remember(command_id, "completed")
            self._report(state, reported_at, reason="mismatched_acknowledgement", command_id=command_id)
            return
        pending.future.set_result((state, reported_at))

    def _commit(self, state: BaseModel, reported_at: datetime) -> None:
        self._confirmed = state
        self._confirmed_at = self._clock()
        self._state_timestamp = reported_at

    def _report(self, state: BaseModel, reported_at: datetime, *, reason: str, command_id: str | None = None) -> None:
        """Apply a state the device reported without a matching pending command."""
        if self.observer is not None:
            self.observer.before_state_change(self)
        previous = self.get_state()
        had_state = self._confirmed is not None
        self._commit(state, reported_at)
        if self.observer is not None and had_state and previous != self.get_state():
            details = {"transport": "mqtt", "reason": reason}
            if command_id:
                details["command_id"] = command_id
            self.observer.state_reported(self, previous, self.get_state(), details)

    def _seen(self) -> None:
        self._last_seen = self._clock()
        self._set_availability(DeviceStatus.ONLINE)  # any message from the device proves it is alive

    def _set_availability(self, status: DeviceStatus) -> None:
        if status is self._availability:
            return
        previous, self._availability = self._availability, status
        logger.info("%s availability: %s -> %s", self.id, previous, status)
        if self.observer is not None:
            self.observer.availability_changed(self, previous, status)

    def _fail_pending(self, error: Exception) -> None:
        for command_id, pending in list(self._pending.items()):
            if not pending.future.done():
                pending.future.set_exception(error)
                self._remember(command_id, "expired")

    def _remember(self, command_id: str, outcome: str) -> None:
        self._finished[command_id] = outcome
        self._finished.move_to_end(command_id)
        while len(self._finished) > _FINISHED_MEMORY:
            self._finished.popitem(last=False)


def _parameters(command: CommandModel) -> dict[str, Any]:
    return {} if command.argument is None else {"value": command.argument}
