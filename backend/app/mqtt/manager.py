"""The backend's single shared MQTT connection.

Subscribes once to the contract topics and routes every message to the hardware device
or sensor provider it belongs to. All routing happens on the asyncio event loop: messages
arrive on the transport's network thread and are handed over with call_soon_threadsafe,
so device state is only ever touched from one thread.

Changes a device reports on its own (a state report, availability) are recorded in the
existing event store with ``source=mqtt``. Commands keep their real source (frontend,
gesture, ai_agent): MQTT is the transport, not the actor.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.devices.types import DeviceStatus
from app.events.models import CommandSource, DeviceEvent
from app.events.store import EventStore
from app.mqtt import topics
from app.mqtt.client import MQTTTransport
from app.mqtt.errors import MessageError
from app.mqtt.messages import decode_availability

if TYPE_CHECKING:
    from app.devices.esp32 import ESP32MQTTDevice
    from app.domain.home_state import HomeState
    from app.sensors.mqtt import MQTTSensorProvider

logger = logging.getLogger(__name__)


class MQTTManager:
    def __init__(self, transport: MQTTTransport, events: EventStore, *, broker: str, client_id: str) -> None:
        self._transport = transport
        self._events = events
        self.broker = broker
        self.client_id = client_id
        self._devices: dict[str, "ESP32MQTTDevice"] = {}
        self._sensors: "MQTTSensorProvider | None" = None
        self._home: "HomeState | None" = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self.sensors_board_online: bool | None = None
        self.messages_received = 0
        self.messages_ignored = 0
        self.connected_since: datetime | None = None
        transport.on_message = self._on_message
        transport.on_connection_change = self._on_connection_change

    # --- Wiring ------------------------------------------------------------------------

    def register_device(self, device: "ESP32MQTTDevice") -> None:
        self._devices[device.id] = device
        device.observer = self

    def attach_sensors(self, provider: "MQTTSensorProvider") -> None:
        self._sensors = provider

    def attach_home(self, home: "HomeState") -> None:
        self._home = home

    @property
    def devices(self) -> list["ESP32MQTTDevice"]:
        return list(self._devices.values())

    @property
    def sensors(self) -> "MQTTSensorProvider | None":
        return self._sensors

    # --- Lifecycle (FastAPI lifespan) ----------------------------------------------------

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        for topic_filter in topics.BACKEND_SUBSCRIPTIONS:
            self._transport.subscribe(topic_filter, qos=1)
        self._transport.start()  # non-blocking: the backend runs (devices UNKNOWN) until it connects

    async def stop(self) -> None:
        self._transport.publish(topics.backend_availability(), topics.OFFLINE, retain=True)
        self._transport.stop()
        self._loop = None

    # --- MQTTLink (used by ESP32MQTTDevice) ---------------------------------------------

    @property
    def connected(self) -> bool:
        return self._transport.connected

    def publish(self, topic: str, payload: bytes | str, *, qos: int = 1, retain: bool = False) -> bool:
        return self._transport.publish(topic, payload, qos=qos, retain=retain)

    # --- Transport callbacks (network thread) ---------------------------------------------

    def _on_message(self, topic: str, payload: bytes) -> None:
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(self._dispatch, topic, payload)

    def _on_connection_change(self, connected: bool) -> None:
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(self._connection_changed, connected)

    # --- Event-loop side ------------------------------------------------------------------

    def _connection_changed(self, connected: bool) -> None:
        self.connected_since = datetime.now(UTC) if connected else None
        if connected:
            self._transport.publish(topics.backend_availability(), topics.ONLINE, retain=True)
        for device in self._devices.values():
            device.connection_changed(connected)

    def _dispatch(self, topic: str, payload: bytes) -> None:
        self.messages_received += 1
        try:
            if not self._route(topic, payload):
                self.messages_ignored += 1
        except Exception:  # a bad message must never break the connection's message loop
            self.messages_ignored += 1
            logger.exception("Error handling MQTT message on %s", topic)

    def _route(self, topic: str, payload: bytes) -> bool:
        parsed = topics.parse(topic)
        if parsed is None:
            return False
        if parsed.kind == "sensor":
            if self._sensors is None:
                return False
            self._sensors.handle(parsed.key, payload)
            return True
        if parsed.kind == "sensors_availability":
            return self._sensor_board_availability(payload)
        device = self._devices.get(parsed.key)
        if device is None:
            return False  # a virtual device, or one this backend does not manage
        match parsed.kind:
            case "state":
                device.handle_state(payload)
            case "availability":
                device.handle_availability(payload)
            case "energy":
                device.handle_energy(payload)
            case _:
                return False
        return True

    def _sensor_board_availability(self, payload: bytes) -> bool:
        try:
            online = decode_availability(payload) == topics.ONLINE
        except MessageError as exc:
            logger.warning("Ignored sensor availability message: %s", exc)
            return False
        if online != self.sensors_board_online:
            logger.info("Sensor board %s", "online" if online else "offline")
        self.sensors_board_online = online
        if self._sensors is not None:
            self._sensors.set_board_online(online)
        return True

    # --- DeviceObserver --------------------------------------------------------------------

    def before_state_change(self, device: "ESP32MQTTDevice") -> None:
        if self._home is not None:
            self._home.record_energy()  # close the energy interval at the old power draw

    def state_reported(
        self, device: "ESP32MQTTDevice", previous: dict[str, Any], new: dict[str, Any], details: dict[str, Any]
    ) -> None:
        self._events.append(
            DeviceEvent(
                device_id=device.id,
                action="state_report",
                previous_state=previous,
                new_state=new,
                source=CommandSource.MQTT,
                event_type="state_report",
                details=details,
            )
        )

    def availability_changed(self, device: "ESP32MQTTDevice", previous: DeviceStatus, new: DeviceStatus) -> None:
        state = device.get_state()
        self._events.append(
            DeviceEvent(
                device_id=device.id,
                action=str(new),
                previous_state=state,
                new_state=state,
                source=CommandSource.MQTT,
                event_type="availability",
                details={"transport": "mqtt", "previous": str(previous)},
            )
        )

    # --- Status (GET /iot/status) -------------------------------------------------------

    def device_status(self, device: "ESP32MQTTDevice") -> dict[str, Any]:
        return {
            "last_seen": device.last_seen,
            "topics": {
                "set": topics.device_set(device.id),
                "state": topics.device_state(device.id),
                "availability": topics.device_availability(device.id),
            },
        }
