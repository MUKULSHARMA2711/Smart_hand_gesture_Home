"""The HTTP API with ESP32 devices: dashboard, gesture and AI commands reach the Fake ESP32
through CommandService; failures surface as clear errors; virtual mode keeps working."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.devices.types import DeviceType
from app.main import create_app
from app.mqtt.memory import InMemoryBroker
from simulation.mqtt_esp32 import FakeESP32, FakeSensorBoard
from simulation.scenarios import Scenario
from tests.mqtt_helpers import FAN, LIGHT, hardware_settings

API = "/api/v1"


class Hardware:
    def __init__(self, client: TestClient, broker: InMemoryBroker) -> None:
        self.client, self.broker = client, broker
        connect = lambda client_id, will: broker.client(client_id, will=will)  # noqa: E731
        self.fan = FakeESP32(FAN, DeviceType.FAN, connect)
        self.light = FakeESP32(LIGHT, DeviceType.LIGHT, connect)
        self.sensors = FakeSensorBoard(connect, interval_s=3600)
        for board in (self.fan, self.light, self.sensors):
            client.portal.call(board.start)  # on the app's event loop, like a separate process would be

    def device(self, device_id: str) -> dict:
        return self.client.get(f"{API}/devices/{device_id}").json()


@pytest.fixture
def hardware() -> Iterator[Hardware]:
    broker = InMemoryBroker()
    app = create_app(hardware_settings(sensor_source="mqtt"), mqtt_transport=broker.client("backend"))
    with TestClient(app) as client:
        yield Hardware(client, broker)


def test_dashboard_command_goes_through_mqtt_and_waits_for_the_ack(hardware: Hardware) -> None:
    response = hardware.client.post(f"{API}/devices/{FAN}/command", json={"action": "set_speed", "value": 70})

    assert response.status_code == 200
    event = response.json()["event"]
    assert (event["source"], event["details"]["transport"]) == ("frontend", "mqtt")
    assert response.json()["device"]["state"] == {"is_on": True, "speed": 70} == hardware.fan.state.model_dump()
    assert response.json()["device"]["driver"] == "esp32_mqtt"
    assert response.json()["device"]["last_confirmed_at"] is not None


def test_gesture_reaches_the_hardware_through_command_service(hardware: Hardware) -> None:
    gesture = {"gesture": "THUMBS_UP", "intent": "TURN_ON", "confidence": 0.95, "target_device_id": LIGHT}

    body = hardware.client.post(f"{API}/gestures/commands", json=gesture).json()

    assert body["device_event"]["source"] == "gesture"
    assert body["device_event"]["details"]["transport"] == "mqtt"
    assert hardware.light.state.is_on is True


def test_ai_reaches_the_hardware_through_command_service(hardware: Hardware) -> None:
    body = hardware.client.post(f"{API}/ai/command", json={"message": "Turn on the fan and set it to 70"}).json()

    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("TURN_ON", "executed"), ("SET_SPEED", "executed")]
    assert hardware.fan.state.model_dump() == {"is_on": True, "speed": 70}
    assert {e["source"] for e in body["device_events"]} == {"ai_agent"}


def test_offline_device_fails_clearly_and_keeps_its_last_confirmed_state(hardware: Hardware) -> None:
    hardware.client.portal.call(lambda: hardware.fan.set_scenario(Scenario.OFFLINE))

    response = hardware.client.post(f"{API}/devices/{FAN}/command", json={"action": "turn_on"})
    gesture = hardware.client.post(
        f"{API}/gestures/commands",
        json={"gesture": "THUMBS_UP", "intent": "TURN_ON", "confidence": 0.95, "target_device_id": FAN},
    )
    ai = hardware.client.post(f"{API}/ai/command", json={"message": "turn on the fan"}).json()

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "device_unavailable",
        "message": "Living Room Fan is offline.",
        "details": {"device_id": FAN, "status": "offline", "reason": None},
    }
    assert gesture.status_code == 503
    assert [(a["status"], a["code"]) for a in ai["actions"]] == [("failed", "device_unavailable")]
    assert hardware.device(FAN)["status"] == "offline"
    assert hardware.device(FAN)["state"]["is_on"] is False  # no fake transition
    assert [e["source"] for e in hardware.client.get(f"{API}/events").json() if e["event_type"] == "device_command"] == []


def test_unacknowledged_command_returns_504_and_changes_nothing(hardware: Hardware) -> None:
    hardware.client.portal.call(lambda: hardware.fan.set_scenario(Scenario.NO_ACK))

    response = hardware.client.post(f"{API}/devices/{FAN}/command", json={"action": "turn_on"})

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "device_timeout"
    assert response.json()["error"]["message"].startswith("Living Room Fan did not confirm the command within 0.3 s.")
    assert hardware.device(FAN)["state"]["is_on"] is False


def test_iot_status_reports_real_runtime_values(hardware: Hardware) -> None:
    hardware.client.portal.call(lambda: hardware.fan.set_scenario(Scenario.OFFLINE))

    status = hardware.client.get(f"{API}/iot/status").json()

    assert status["mqtt"]["enabled"] is True and status["mqtt"]["connected"] is True
    assert status["mqtt"]["messages_received"] > 0
    assert (status["devices"]["online"], status["devices"]["offline"], status["devices"]["unknown"]) == (3, 1, 0)
    items = {item["device_id"]: item for item in status["devices"]["items"]}
    assert (items[FAN]["driver"], items[FAN]["status"]) == ("esp32_mqtt", "offline")
    assert items[FAN]["topics"]["set"] == "home/fan_living_room/set"
    assert (items["door_main"]["driver"], items["door_main"]["status"]) == ("virtual", "online")
    assert status["sensors"]["source"] == "mqtt" and status["sensors"]["board_online"] is True
    assert status["sensors"]["readings"]["temperature"]["status"] == "ok"


class UnreachableBroker:
    """A transport whose broker never answers (wrong host, broker down)."""

    on_message = on_connection_change = None
    connected = False

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def subscribe(self, topic_filter: str, qos: int = 1) -> None: ...

    def publish(self, *args, **kwargs) -> bool:
        return False


def test_unreachable_broker_never_blocks_virtual_devices_ai_or_gestures() -> None:
    app = create_app(hardware_settings(mqtt_devices=[FAN]), mqtt_transport=UnreachableBroker())
    with TestClient(app) as client:
        assert client.get(f"{API}/home/state").status_code == 200
        assert client.post(f"{API}/devices/{LIGHT}/command", json={"action": "turn_on"}).status_code == 200
        gesture = {"gesture": "FIST", "intent": "TURN_OFF", "confidence": 0.95, "target_device_id": LIGHT}
        assert client.post(f"{API}/gestures/commands", json=gesture).status_code == 200
        ai = client.post(f"{API}/ai/command", json={"message": "turn on the light"}).json()
        assert ai["actions"][0]["status"] == "executed"

        fan = client.post(f"{API}/devices/{FAN}/command", json={"action": "turn_on"})
        assert fan.status_code == 503
        assert fan.json()["error"]["message"] == "Living Room Fan is unreachable: the MQTT broker is not connected."
        status = client.get(f"{API}/iot/status").json()
        assert status["mqtt"]["connected"] is False
        assert {i["device_id"]: i["status"] for i in status["devices"]["items"]}[FAN] == "unknown"
