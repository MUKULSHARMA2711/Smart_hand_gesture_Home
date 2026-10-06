import pytest
from fastapi.testclient import TestClient

from tests.conftest import SendCommand


def test_successful_command_is_logged_as_event(client: TestClient, send_command: SendCommand) -> None:
    send_command("light_living_room", "set_brightness", value=70)

    events = client.get("/api/v1/events").json()

    assert len(events) == 1
    event = events[0]
    assert set(event) >= {"event_id", "timestamp", "device_id", "action", "previous_state", "new_state", "source"}
    assert event["device_id"] == "light_living_room"
    assert event["action"] == "set_brightness"
    assert event["value"] == 70
    assert event["previous_state"] == {"is_on": False, "brightness": 100}
    assert event["new_state"] == {"is_on": True, "brightness": 70}
    assert event["source"] == "frontend"


@pytest.mark.parametrize("source", ["ai_agent", "gesture", "automation", "mqtt", "ml"])
def test_direct_commands_cannot_claim_another_source(
    client: TestClient, send_command: SendCommand, source: str
) -> None:
    # Regression: the device endpoint used to accept any source, so a client could unlock
    # the door and have the event log say the AI agent (or a gesture) did it.
    response = send_command("door_main", "unlock", source=source)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert client.get("/api/v1/devices/door_main").json()["state"]["is_locked"] is True
    assert client.get("/api/v1/events").json() == []


def test_direct_commands_are_recorded_as_frontend(client: TestClient, send_command: SendCommand) -> None:
    send_command("door_main", "unlock", source="frontend")

    assert client.get("/api/v1/events").json()[0]["source"] == "frontend"


def test_failed_commands_are_not_logged(client: TestClient, send_command: SendCommand) -> None:
    send_command("light_living_room", "set_brightness", value=500)
    send_command("light_living_room", "explode")
    send_command("missing_device", "turn_on")

    assert client.get("/api/v1/events").json() == []


def test_events_are_newest_first_and_filterable(client: TestClient, send_command: SendCommand) -> None:
    send_command("light_living_room", "turn_on")
    send_command("fan_living_room", "turn_on")
    send_command("door_main", "unlock")

    newest_two = client.get("/api/v1/events", params={"limit": 2}).json()
    fan_only = client.get("/api/v1/events", params={"device_id": "fan_living_room"}).json()

    assert [e["device_id"] for e in newest_two] == ["door_main", "fan_living_room"]
    assert [e["device_id"] for e in fan_only] == ["fan_living_room"]


def test_home_state_contains_devices_sensors_and_energy(client: TestClient) -> None:
    response = client.get("/api/v1/home/state")

    assert response.status_code == 200
    state = response.json()
    environment = state["environment"]
    assert 15 <= environment["temperature_c"] <= 35
    assert 20 <= environment["humidity_pct"] <= 95
    assert environment["ambient_light_lux"] >= 0
    assert environment["occupancy"]["occupied"] == (environment["occupancy"]["occupant_count"] > 0)
    assert len(state["devices"]) == 4
    energy = state["energy"]
    assert energy["total_power_w"] == round(sum(energy["per_device_w"].values()), 2)


def test_power_draw_follows_device_state(client: TestClient, send_command: SendCommand) -> None:
    idle_power = client.get("/api/v1/home/state").json()["energy"]["total_power_w"]

    send_command("ac_bedroom", "turn_on")

    active = client.get("/api/v1/home/state").json()["energy"]
    assert active["total_power_w"] > idle_power + 500
    assert active["per_device_w"]["ac_bedroom"] > 500


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_root_describes_the_service(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "IntelliHome",
        "description": "AI-powered smart home automation system",
        "status": "operational",
        "docs": "/docs",
        "api": "/api/v1",
    }
