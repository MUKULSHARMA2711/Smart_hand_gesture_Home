"""Fake ESP32 firmware: a software stand-in for the boards that will run real hardware.

Physical hardware is not required: each FakeESP32 behaves like minimal firmware for one
ESP32 controlling one device, over the same MQTT contract (app/mqtt/topics.py and
messages.py) the real firmware must implement:

  1. connect with a Last Will (home/{id}/availability = "offline", retained)
  2. publish availability "online" and its current state (retained)
  3. subscribe to home/{id}/set
  4. validate each command (shape, device id, expiry, action, parameters)
  5. drive the "hardware" (here: the same physics as the virtual device)
  6. publish the resulting state with the command_id (the acknowledgement)
  7. publish "offline" when stopped (a crash triggers the Last Will instead)

FakeSensorBoard plays an ESP32 with DHT22 / PIR / LDR sensors publishing on home/sensors/*.

Run it against a local broker (see README "MQTT Hardware Architecture"):

    python -m simulation.mqtt_esp32                     # devices in SMARTHOME_MQTT_DEVICES + sensors
    python -m simulation.mqtt_esp32 --devices fan_living_room --scenario delay --delay 2
"""

import argparse
import asyncio
import logging
import os
import random
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.devices.commands import DeviceCommand
from app.devices.power import POWER_MODELS
from app.devices.specs import SPECS_BY_TYPE
from app.devices.types import DeviceType
from app.devices.virtual import VirtualAC, VirtualDoorLock, VirtualFan, VirtualLight
from app.domain.errors import DomainError
from app.mqtt import topics
from app.mqtt.client import MQTTTransport, Will
from app.mqtt.errors import MessageError
from app.mqtt.messages import CommandMessage, EnergyMessage, SensorMessage, StateMessage, decode, encode
from app.sensors.base import SensorProvider
from app.sensors.simulated import SimulatedSensorProvider
from simulation.scenarios import Scenario, ScenarioRequest, SensorScenario, control_topic

logger = logging.getLogger("fake_esp32")

# Connects one board: (client_id, will) -> transport. Paho for a real broker, in-memory in tests.
TransportFactory = Callable[[str, Will], MQTTTransport]

_PHYSICS = {DeviceType.LIGHT: VirtualLight, DeviceType.FAN: VirtualFan, DeviceType.AC: VirtualAC, DeviceType.DOOR_LOCK: VirtualDoorLock}

# Valid JSON, but a state no real device can be in (rejected by the backend's spec check).
_IMPOSSIBLE_STATE = {
    DeviceType.LIGHT: {"is_on": True, "brightness": 250},
    DeviceType.FAN: {"is_on": True, "speed": 250},
    DeviceType.AC: {"is_on": True, "target_temperature_c": 99},
    DeviceType.DOOR_LOCK: {"is_locked": "maybe"},
}


def _now() -> datetime:
    return datetime.now(UTC)


class FakeESP32:
    """One simulated ESP32 board controlling one device, on its own MQTT connection."""

    def __init__(
        self,
        device_id: str,
        device_type: DeviceType,
        connect: TransportFactory,
        *,
        initial_state: dict[str, Any] | None = None,
        scenario: Scenario = Scenario.NORMAL,
        delay_s: float = 2.0,
        reconnect_after_s: float = 3.0,
        energy_interval_s: float | None = None,
    ) -> None:
        self.device_id = device_id
        self.device_type = device_type
        self._connect = connect
        self._spec = SPECS_BY_TYPE[device_type]
        self._physics = _PHYSICS[device_type](device_id, device_id, "simulation")
        self.state = self._spec.state_model(**(initial_state or {}))
        self.scenario = scenario
        self.delay_s = delay_s
        self.reconnect_after_s = reconnect_after_s
        self.energy_interval_s = energy_interval_s
        self.commands_received: list[CommandMessage] = []
        self._transport: MQTTTransport | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tasks: set[asyncio.Task] = set()

    @property
    def connected(self) -> bool:
        return self._transport is not None and self._transport.connected

    # --- Lifecycle ----------------------------------------------------------------------

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        will = Will(topics.device_availability(self.device_id), topics.OFFLINE)
        transport = self._connect(f"fake-esp32-{self.device_id}", will)
        transport.on_message = self._on_message
        transport.on_connection_change = self._on_connection_change
        transport.subscribe(topics.device_set(self.device_id))
        transport.subscribe(control_topic(self.device_id))
        self._transport = transport
        transport.start()
        if self.energy_interval_s:
            self._spawn(self._energy_loop())

    async def stop(self) -> None:
        """Graceful shutdown: announce offline, then disconnect (no Last Will)."""
        current = asyncio.current_task()
        for task in list(self._tasks):
            if task is not current:  # a reconnect stops and restarts the board from its own task
                task.cancel()
        if self._transport is not None:
            self._publish(topics.device_availability(self.device_id), topics.OFFLINE, retain=True)
            self._transport.stop()

    def crash(self) -> None:
        """Simulate a power cut: drop the connection so the broker publishes the Last Will."""
        if self._transport is not None:
            self._transport.abort()

    # --- Scenarios ------------------------------------------------------------------------

    def set_scenario(self, scenario: Scenario, *, delay_s: float | None = None, reconnect_after_s: float | None = None) -> None:
        previous, self.scenario = self.scenario, scenario
        if delay_s is not None:
            self.delay_s = delay_s
        if reconnect_after_s is not None:
            self.reconnect_after_s = reconnect_after_s
        logger.info("%s scenario: %s -> %s", self.device_id, previous, scenario)
        if scenario is Scenario.OFFLINE:
            self._publish(topics.device_availability(self.device_id), topics.OFFLINE, retain=True)
        elif previous is Scenario.OFFLINE:
            self._announce()
        if scenario is Scenario.RECONNECT:
            self._spawn(self._reconnect())

    async def _reconnect(self) -> None:
        await self.stop()
        await asyncio.sleep(self.reconnect_after_s)
        self.scenario = Scenario.NORMAL
        await self.start()

    # --- Transport callbacks (any thread) → event loop --------------------------------------

    def _on_message(self, topic: str, payload: bytes) -> None:
        if self._loop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._handle, topic, payload)

    def _on_connection_change(self, connected: bool) -> None:
        if connected and self._loop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._announce)

    def _announce(self) -> None:
        """On every (re)connect: availability and the current state, both retained."""
        if self.scenario is Scenario.OFFLINE:
            self._publish(topics.device_availability(self.device_id), topics.OFFLINE, retain=True)
            return
        self._publish(topics.device_availability(self.device_id), topics.ONLINE, retain=True)
        self._publish_state(None)

    def _handle(self, topic: str, payload: bytes) -> None:
        if topic == control_topic(self.device_id):
            try:
                request = ScenarioRequest.decode(payload)
                self.set_scenario(Scenario(request.scenario), delay_s=request.delay_s, reconnect_after_s=request.reconnect_after_s)
            except (ValueError, KeyError) as exc:
                logger.warning("%s: bad scenario request: %s", self.device_id, exc)
            return
        self._command(payload)

    # --- Firmware command handling ---------------------------------------------------------

    def _command(self, payload: bytes) -> None:
        if self.scenario in (Scenario.OFFLINE, Scenario.NO_ACK, Scenario.RECONNECT):
            logger.info("%s: ignoring command (%s)", self.device_id, self.scenario)
            return
        try:
            message = decode(CommandMessage, payload)
        except MessageError as exc:
            logger.warning("%s: dropped malformed command: %s", self.device_id, exc)
            return
        if message.device_id != self.device_id:
            logger.warning("%s: dropped command for %s", self.device_id, message.device_id)
            return
        if _now() > message.expires_at:
            logger.warning("%s: dropped expired command %s", self.device_id, message.command_id)
            return
        try:
            command = self._spec.parse_command(
                self.device_id, DeviceCommand(action=message.action, value=message.parameters.get("value"))
            )
        except DomainError as exc:
            logger.warning("%s: rejected command: %s", self.device_id, exc.message)
            return
        self.commands_received.append(message)
        new_state = self._physics.apply(self.state, command)
        logger.info("%s: %s %s -> %s", self.device_id, message.action, message.parameters, new_state.model_dump())

        match self.scenario:
            case Scenario.WRONG_STATE:
                self._publish_ack(message.command_id, _IMPOSSIBLE_STATE[self.device_type])
            case Scenario.MALFORMED_ACK:
                self._publish(topics.device_state(self.device_id), b'{"device_id": "' + self.device_id.encode() + b'", "state": {', retain=False)
            case Scenario.WRONG_COMMAND_ID:
                self.state = new_state
                self._publish_state(str(uuid4()))
            case Scenario.DELAY:
                self.state = new_state
                assert self._loop is not None
                self._loop.call_later(self.delay_s, self._publish_state, message.command_id)
            case Scenario.DUPLICATE_ACK:
                self.state = new_state
                for _ in range(3):
                    self._publish_state(message.command_id)
            case _:
                self.state = new_state
                self._publish_state(message.command_id)

    def _publish_state(self, command_id: str | None) -> None:
        self._publish_ack(command_id, self.state.model_dump())
        if self.energy_interval_s:
            self._publish_energy()  # a real meter reflects the change at once

    def _publish_energy(self) -> None:
        """A power meter (e.g. INA219 / PZEM): the modelled draw with ±2 % measurement noise."""
        watts = max(0.0, POWER_MODELS[self.device_type](self.state.model_dump()) * random.uniform(0.98, 1.02))
        self._publish(topics.energy(self.device_id), encode(EnergyMessage(timestamp=_now(), power_w=round(watts, 2))))

    def _publish_ack(self, command_id: str | None, state: dict[str, Any]) -> None:
        message = StateMessage(device_id=self.device_id, command_id=command_id, timestamp=_now(), state=state)
        self._publish(topics.device_state(self.device_id), encode(message), retain=True)

    async def _energy_loop(self) -> None:
        while True:
            await asyncio.sleep(self.energy_interval_s or 10)
            if self.scenario not in (Scenario.OFFLINE, Scenario.NO_ACK):
                self._publish_energy()

    def _publish(self, topic: str, payload: bytes | str, *, retain: bool = False) -> None:
        if self._transport is not None:
            self._transport.publish(topic, payload, qos=1, retain=retain)

    def _spawn(self, coro) -> None:
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


class FakeSensorBoard:
    """An ESP32 with a DHT22 (temperature, humidity), a PIR (occupancy) and an LDR (light).

    Publishes every ``interval_s`` (not continuously), with the same realistic daily cycle
    as the built-in simulated sensors.
    """

    BOARD_ID = "sensors"

    def __init__(
        self,
        connect: TransportFactory,
        *,
        interval_s: float = 5.0,
        scenario: SensorScenario = SensorScenario.NORMAL,
        source: SensorProvider | None = None,
    ) -> None:
        self._connect = connect
        self.interval_s = interval_s
        self.scenario = scenario
        self._source = source or SimulatedSensorProvider()
        self._transport: MQTTTransport | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        transport = self._connect("fake-esp32-sensors", Will(topics.sensors_availability(), topics.OFFLINE))
        transport.on_message = self._on_message
        transport.on_connection_change = self._on_connection_change
        transport.subscribe(control_topic(self.BOARD_ID))
        self._transport = transport
        transport.start()
        self._task = asyncio.ensure_future(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
        if self._transport is not None:
            self._transport.publish(topics.sensors_availability(), topics.OFFLINE, retain=True)
            self._transport.stop()

    def crash(self) -> None:
        if self._task is not None:
            self._task.cancel()
        if self._transport is not None:
            self._transport.abort()

    def set_scenario(self, scenario: SensorScenario) -> None:
        logger.info("sensors scenario: %s -> %s", self.scenario, scenario)
        self.scenario = scenario
        if self._transport is not None:
            online = scenario is not SensorScenario.OFFLINE
            self._transport.publish(topics.sensors_availability(), topics.ONLINE if online else topics.OFFLINE, retain=True)

    def publish_once(self) -> None:
        if self._transport is None or self.scenario in (SensorScenario.STALE, SensorScenario.OFFLINE):
            return
        readings = self._source.read()
        now = _now()
        values = {
            "temperature": ("dht22_1", readings.temperature_c),
            "humidity": ("dht22_1", readings.humidity_pct),
            "occupancy": ("pir_1", float(readings.occupancy.occupant_count)),
            "ambient_light": ("ldr_1", readings.ambient_light_lux),
        }
        if self.scenario is SensorScenario.INVALID:
            values["temperature"] = ("dht22_1", -1000.0)
        for kind, (sensor_id, value) in values.items():
            message = SensorMessage(sensor_id=sensor_id, timestamp=now, value=value)
            self._transport.publish(topics.sensor(kind), encode(message), qos=1)

    async def _run(self) -> None:
        while True:
            self.publish_once()
            await asyncio.sleep(self.interval_s)

    def _on_message(self, topic: str, payload: bytes) -> None:
        if self._loop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._control, payload)

    def _control(self, payload: bytes) -> None:
        try:
            self.set_scenario(SensorScenario(ScenarioRequest.decode(payload).scenario))
        except (ValueError, KeyError) as exc:
            logger.warning("sensors: bad scenario request: %s", exc)

    def _on_connection_change(self, connected: bool) -> None:
        if connected and self._loop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self.set_scenario, self.scenario)  # announce availability


# --- Command line -----------------------------------------------------------------------------


def _paho_factory(host: str, port: int, username: str | None, password: str | None) -> TransportFactory:
    from app.mqtt.client import PahoTransport

    def connect(client_id: str, will: Will) -> MQTTTransport:
        return PahoTransport(host=host, port=port, client_id=client_id, username=username, password=password, will=will, keepalive_s=10)

    return connect


async def run(args: argparse.Namespace) -> None:
    from app.config import Settings

    types = {device.id: device.type for device in Settings(mqtt_enabled=True).devices}
    unknown = sorted(set(args.devices) - set(types))
    if unknown:
        raise SystemExit(f"Unknown device ids: {unknown}. Known: {sorted(types)}")

    connect = _paho_factory(args.host, args.port, os.environ.get("SMARTHOME_MQTT_USERNAME"), os.environ.get("SMARTHOME_MQTT_PASSWORD"))
    boards: list[FakeESP32 | FakeSensorBoard] = [
        FakeESP32(
            device_id,
            types[device_id],
            connect,
            scenario=Scenario(args.scenario),
            delay_s=args.delay,
            energy_interval_s=args.energy_interval or None,
        )
        for device_id in args.devices
    ]
    if args.sensors:
        boards.append(FakeSensorBoard(connect, interval_s=args.sensor_interval))
    for board in boards:
        await board.start()
    names = ", ".join(args.devices) + (" + sensor board" if args.sensors else "")
    print(f"Fake ESP32 running ({names}) on {args.host}:{args.port}. Ctrl+C to stop.", flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        for board in boards:
            await board.stop()
        await asyncio.sleep(0.3)  # let the offline messages go out


def main() -> None:
    default_devices = [d for d in os.environ.get("SMARTHOME_MQTT_DEVICES", "").strip("[] ").replace('"', "").split(",") if d.strip()]
    parser = argparse.ArgumentParser(description="Fake ESP32 boards speaking the IntelliHome MQTT contract.")
    parser.add_argument("--host", default=os.environ.get("SMARTHOME_MQTT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("SMARTHOME_MQTT_PORT", "1883")))
    parser.add_argument("--devices", type=lambda s: [d.strip() for d in s.split(",") if d.strip()],
                        default=[d.strip() for d in default_devices] or ["fan_living_room"],
                        help="comma-separated device ids (default: SMARTHOME_MQTT_DEVICES)")
    parser.add_argument("--scenario", choices=[s.value for s in Scenario], default=Scenario.NORMAL.value)
    parser.add_argument("--delay", type=float, default=2.0, help="acknowledgement delay for the 'delay' scenario")
    parser.add_argument("--energy-interval", type=float, default=10.0, help="seconds between power readings (0 = off)")
    parser.add_argument("--no-sensors", dest="sensors", action="store_false", help="do not run the sensor board")
    parser.add_argument("--sensor-interval", type=float, default=5.0)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
