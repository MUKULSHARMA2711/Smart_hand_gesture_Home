"""API tests for device commands: happy paths and validation."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import SendCommand

LIGHT = "light_living_room"
FAN = "fan_living_room"
AC = "ac_bedroom"
DOOR = "door_main"


def device_state(client: TestClient, device_id: str) -> dict:
    response = client.get(f"/api/v1/devices/{device_id}")
    assert response.status_code == 200
    return response.json()["state"]


def test_lists_all_devices(client: TestClient) -> None:
    response = client.get("/api/v1/devices")

    assert response.status_code == 200
    devices = {device["id"]: device for device in response.json()}
    assert set(devices) == {LIGHT, FAN, AC, DOOR}
    assert devices[LIGHT]["device_type"] == "light"
    assert devices[LIGHT]["status"] == "online"
    assert {c["action"] for c in devices[DOOR]["supported_commands"]} == {"lock", "unlock"}


# --- Light -------------------------------------------------------------------------


def test_turn_light_on(client: TestClient, send_command: SendCommand) -> None:
    response = send_command(LIGHT, "turn_on")

    assert response.status_code == 200
    body = response.json()
    assert body["event"]["previous_state"]["is_on"] is False
    assert body["event"]["new_state"]["is_on"] is True
    assert body["device"]["state"]["is_on"] is True
    assert device_state(client, LIGHT)["is_on"] is True


def test_turn_light_off(client: TestClient, send_command: SendCommand) -> None:
    send_command(LIGHT, "turn_on")

    response = send_command(LIGHT, "turn_off")

    assert response.status_code == 200
    assert response.json()["event"]["previous_state"]["is_on"] is True
    assert device_state(client, LIGHT)["is_on"] is False


def test_set_brightness(client: TestClient, send_command: SendCommand) -> None:
    response = send_command(LIGHT, "set_brightness", value=70)

    assert response.status_code == 200
    assert device_state(client, LIGHT) == {"is_on": True, "brightness": 70}


@pytest.mark.parametrize("value", [-1, 101, 70.5, "70", True, None])
def test_rejects_invalid_brightness(client: TestClient, send_command: SendCommand, value: object) -> None:
    before = device_state(client, LIGHT)

    response = send_command(LIGHT, "set_brightness", value=value)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_command"
    assert device_state(client, LIGHT) == before


# --- Fan ---------------------------------------------------------------------------


def test_set_fan_speed(client: TestClient, send_command: SendCommand) -> None:
    response = send_command(FAN, "set_speed", value=40)

    assert response.status_code == 200
    assert device_state(client, FAN) == {"is_on": True, "speed": 40}


def test_fan_speed_zero_turns_fan_off(client: TestClient, send_command: SendCommand) -> None:
    send_command(FAN, "set_speed", value=80)

    send_command(FAN, "set_speed", value=0)

    assert device_state(client, FAN)["is_on"] is False


@pytest.mark.parametrize("value", [-5, 150])
def test_rejects_invalid_fan_speed(send_command: SendCommand, value: int) -> None:
    response = send_command(FAN, "set_speed", value=value)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_command"


# --- AC ----------------------------------------------------------------------------


def test_set_ac_temperature(client: TestClient, send_command: SendCommand) -> None:
    send_command(AC, "turn_on")

    response = send_command(AC, "set_temperature", value=22)

    assert response.status_code == 200
    assert device_state(client, AC) == {"is_on": True, "target_temperature_c": 22}


@pytest.mark.parametrize("value", [15, 31, 22.5])
def test_rejects_invalid_ac_temperature(send_command: SendCommand, value: float) -> None:
    response = send_command(AC, "set_temperature", value=value)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_command"


# --- Door --------------------------------------------------------------------------


def test_door_unlock_and_lock(client: TestClient, send_command: SendCommand) -> None:
    assert device_state(client, DOOR)["is_locked"] is True

    assert send_command(DOOR, "unlock").status_code == 200
    assert device_state(client, DOOR)["is_locked"] is False

    assert send_command(DOOR, "lock").status_code == 200
    assert device_state(client, DOOR)["is_locked"] is True


@pytest.mark.parametrize("action", ["turn_on", "open", "set_brightness"])
def test_rejects_invalid_door_commands(send_command: SendCommand, action: str) -> None:
    response = send_command(DOOR, action)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_command"


def test_rejects_value_for_command_without_one(send_command: SendCommand) -> None:
    response = send_command(DOOR, "lock", value=1)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_command"


# --- Unknown commands and devices ----------------------------------------------------


def test_rejects_unsupported_command(send_command: SendCommand) -> None:
    response = send_command(LIGHT, "self_destruct")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "unsupported_command"
    assert error["details"]["supported_actions"] == ["turn_on", "turn_off", "set_brightness"]


def test_rejects_unknown_device_command(send_command: SendCommand) -> None:
    response = send_command("toaster_kitchen", "turn_on")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "device_not_found"


def test_get_unknown_device_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/devices/toaster_kitchen")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "device_not_found"


@pytest.mark.parametrize(
    "body",
    [{}, {"action": ""}, {"action": "turn_on", "unexpected": 1}, {"action": "turn_on", "source": "hacker"}],
)
def test_rejects_malformed_request(client: TestClient, body: dict) -> None:
    response = client.post(f"/api/v1/devices/{LIGHT}/command", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
