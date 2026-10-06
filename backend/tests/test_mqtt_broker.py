"""Against a real MQTT broker (paho over TCP). Skipped unless a broker is configured:

    SMARTHOME_TEST_MQTT_HOST=127.0.0.1 pytest tests/test_mqtt_broker.py -v

These use the real topic names (home/fan_living_room/...), so point them at a broker that
no running IntelliHome or Fake ESP32 is using, or they will interfere with each other.
"""

import asyncio
import os
import uuid

import pytest

from app.container import build_container
from app.devices.commands import DeviceCommand
from app.devices.types import DeviceStatus, DeviceType
from app.events.models import CommandSource
from app.mqtt.client import PahoTransport, Will
from simulation.mqtt_esp32 import FakeESP32
from tests.mqtt_helpers import FAN, hardware_settings

HOST = os.environ.get("SMARTHOME_TEST_MQTT_HOST")
PORT = int(os.environ.get("SMARTHOME_TEST_MQTT_PORT", "1883"))

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(not HOST, reason="set SMARTHOME_TEST_MQTT_HOST to run against a real broker"),
]


def paho(client_id: str, will: Will | None = None) -> PahoTransport:
    return PahoTransport(host=HOST or "", port=PORT, client_id=f"{client_id}-{uuid.uuid4().hex[:6]}", will=will, keepalive_s=5)


async def wait_for(condition, timeout: float = 5.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.02)


async def test_connect_disconnect_and_reconnect() -> None:
    transport = paho("probe")
    changes: list[bool] = []
    transport.on_connection_change = changes.append

    transport.start()
    await wait_for(lambda: transport.connected)
    transport.stop()
    assert transport.connected is False
    transport.start()  # reconnect after a stop
    await wait_for(lambda: transport.connected)
    transport.stop()

    assert changes == [True, False, True, False]


async def test_full_round_trip_last_will_and_recovery_over_a_real_broker() -> None:
    container = build_container(hardware_settings(mqtt_devices=[FAN], mqtt_command_timeout_s=3), mqtt_transport=paho("backend"))
    await container.mqtt.start()
    fake = FakeESP32(FAN, DeviceType.FAN, lambda client_id, will: paho(client_id, will))
    await fake.start()
    fan = container.home_state.devices.get(FAN)
    try:
        await wait_for(lambda: fan.status is DeviceStatus.ONLINE)

        event = await container.command_service.execute(FAN, DeviceCommand(action="set_speed", value=70), CommandSource.FRONTEND)
        assert event.new_state == {"is_on": True, "speed": 70} == fake.state.model_dump()
        assert event.details["ack_latency_ms"] < 3000

        fake.crash()  # unclean disconnect: the broker publishes the Last Will after the keepalive
        await wait_for(lambda: fan.status is DeviceStatus.OFFLINE, timeout=15)

        await fake.start()  # the board comes back
        await wait_for(lambda: fan.status is DeviceStatus.ONLINE)
        event = await container.command_service.execute(FAN, DeviceCommand(action="turn_off"), CommandSource.FRONTEND)
        assert event.new_state["is_on"] is False

        # A graceful stop must deliver its final "offline": a clean disconnect suppresses the
        # Last Will, so nothing else would tell the backend the device is gone.
        await fake.stop()
        await wait_for(lambda: fan.status is DeviceStatus.OFFLINE, timeout=3)
    finally:
        await fake.stop()
        await container.mqtt.stop()
