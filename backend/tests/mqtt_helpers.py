"""Test rigs for the MQTT layer: an in-memory broker, the real backend container, and a
hand-driven firmware probe for exact control over acknowledgements."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from app.config import Settings
from app.container import Container, build_container
from app.devices.commands import DeviceCommand
from app.events.models import CommandSource, DeviceEvent
from app.mqtt import topics
from app.mqtt.memory import InMemoryBroker, InMemoryTransport
from app.mqtt.messages import CommandMessage, StateMessage, decode, encode

FAN, LIGHT, DOOR = "fan_living_room", "light_living_room", "door_main"


def hardware_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "mqtt_enabled": True,
        "mqtt_devices": [FAN, LIGHT],
        "mqtt_command_timeout_s": 0.3,
        "sensor_seed": 1,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class Probe:
    """Plays the device side by hand: records commands, publishes exactly what a test says."""

    def __init__(self, broker: InMemoryBroker, device_id: str) -> None:
        self.device_id = device_id
        self.commands: list[CommandMessage] = []
        self._read = 0
        self.transport: InMemoryTransport = broker.client(f"probe-{device_id}")
        self.transport.on_message = lambda topic, payload: self.commands.append(decode(CommandMessage, payload))
        self.transport.subscribe(topics.device_set(device_id))
        self.transport.start()

    def online(self) -> None:
        self.transport.publish(topics.device_availability(self.device_id), topics.ONLINE, retain=True)

    def offline(self) -> None:
        self.transport.publish(topics.device_availability(self.device_id), topics.OFFLINE, retain=True)

    def state(self, state: dict[str, Any], command_id: str | None = None, *, device_id: str | None = None) -> None:
        message = StateMessage(
            device_id=device_id or self.device_id, command_id=command_id, timestamp=datetime.now(UTC), state=state
        )
        self.transport.publish(topics.device_state(self.device_id), encode(message), retain=True)

    def raw_state(self, payload: bytes) -> None:
        self.transport.publish(topics.device_state(self.device_id), payload)

    async def next_command(self, timeout: float = 1.0) -> CommandMessage:
        """The next command not yet returned (it may already have arrived)."""
        async with asyncio.timeout(timeout):
            while len(self.commands) <= self._read:
                await asyncio.sleep(0.005)
        self._read += 1
        return self.commands[self._read - 1]


class Rig:
    """The real container (CommandService, HomeState, events) on an in-memory broker."""

    def __init__(self, **overrides: Any) -> None:
        self.broker = InMemoryBroker()
        self.backend = self.broker.client("backend")
        self.container: Container = build_container(hardware_settings(**overrides), mqtt_transport=self.backend)

    async def start(self) -> "Rig":
        assert self.container.mqtt is not None
        await self.container.mqtt.start()
        await settle()
        return self

    def device(self, device_id: str):
        return self.container.home_state.devices.get(device_id)

    async def command(self, device_id: str, action: str, value: Any = None, source=CommandSource.FRONTEND) -> DeviceEvent:
        return await self.container.command_service.execute(device_id, DeviceCommand(action=action, value=value), source)

    def events(self, event_type: str | None = None) -> list[DeviceEvent]:
        events = list(reversed(self.container.event_store.recent(limit=500)))
        return [e for e in events if event_type is None or e.event_type == event_type]

    def commands_published(self, device_id: str) -> list[dict]:
        return [json.loads(p) for t, p, _ in self.broker.published if t == topics.device_set(device_id)]


async def settle(rounds: int = 3) -> None:
    """Let call_soon callbacks (message routing) run."""
    for _ in range(rounds):
        await asyncio.sleep(0)
