"""Preparation for pinch-to-adjust: the ADJUST intent and gesture values. No gesture maps to
ADJUST yet, so the five existing gestures behave exactly as before."""

import pytest
from fastapi.testclient import TestClient

from app.ai.models import AI_INTENTS
from app.config import Settings
from app.container import build_container
from app.devices.types import Capability
from app.domain.errors import IntentNotApplicableError
from app.domain.intents import ADJUST_CAPABILITIES, Intent, IntentResolver, adjust_capability
from app.gestures.models import GESTURE_INTENTS, Gesture

API = "/api/v1"


@pytest.fixture
def devices():
    return build_container(Settings(_env_file=None)).home_state.devices


@pytest.mark.parametrize(
    ("device_id", "value", "action"),
    [("fan_living_room", 70, "set_speed"), ("ac_bedroom", 22, "set_temperature"), ("light_living_room", 40, "set_brightness")],
)
def test_adjust_resolves_to_each_devices_own_value_capability(devices, device_id: str, value: int, action: str) -> None:
    command = IntentResolver().resolve(Intent.ADJUST, devices.get(device_id), value)
    assert (command.action, command.value) == (action, value)


def test_adjust_can_never_reach_the_door(devices) -> None:
    door = devices.get("door_main")
    with pytest.raises(IntentNotApplicableError):
        IntentResolver().resolve(Intent.ADJUST, door, 1)
    assert adjust_capability(door) is None
    assert {Capability.LOCK, Capability.UNLOCK}.isdisjoint(ADJUST_CAPABILITIES)


def test_existing_gesture_mapping_is_unchanged_and_adjust_is_not_for_the_ai() -> None:
    assert dict(GESTURE_INTENTS) == {
        Gesture.THUMBS_UP: Intent.TURN_ON,
        Gesture.FIST: Intent.TURN_OFF,
        Gesture.OPEN_PALM: Intent.STOP,
        Gesture.ONE_FINGER: Intent.SELECT,
        Gesture.TWO_FINGERS: Intent.TOGGLE,
        Gesture.PINCH: Intent.ADJUST,  # added for fan/AC adjustment
        Gesture.NEUTRAL: Intent.NONE,
        Gesture.UNKNOWN: Intent.NONE,
    }
    assert Intent.ADJUST not in AI_INTENTS


def test_fan_and_ac_value_ranges_are_published_for_the_ui(client: TestClient) -> None:
    devices = {d["id"]: d for d in client.get(f"{API}/devices").json()}
    commands = lambda device_id: {c["action"]: c for c in devices[device_id]["supported_commands"]}  # noqa: E731

    assert commands("fan_living_room")["set_speed"]["capability"] == "SET_SPEED"
    assert commands("fan_living_room")["set_speed"]["value"] == {"type": "integer", "minimum": 0, "maximum": 100}
    assert commands("ac_bedroom")["set_temperature"]["capability"] == "SET_TEMPERATURE"
    assert commands("ac_bedroom")["set_temperature"]["value"] == {"type": "integer", "minimum": 16, "maximum": 30}


@pytest.mark.parametrize(
    "body",
    [
        {"gesture": "THUMBS_UP", "intent": "TURN_ON", "value": 70},  # the five gestures take no value
        {"gesture": "THUMBS_UP", "intent": "ADJUST", "value": 70},  # ADJUST belongs to PINCH only
        {"gesture": "THUMBS_UP", "intent": "TURN_ON", "value": 70.5},
        {"gesture": "PINCH", "intent": "ADJUST"},  # a pinch release must carry its value
        {"gesture": "PINCH", "intent": "ADJUST", "value": 70.5},
        {"gesture": "PINCH", "intent": "ADJUST", "value": 250},  # outside the published range
    ],
)
def test_invalid_gesture_values_are_rejected(client: TestClient, body: dict) -> None:
    response = client.post(
        f"{API}/gestures/commands", json={**body, "confidence": 0.95, "target_device_id": "fan_living_room"}
    )
    assert response.status_code == 422
    assert client.get(f"{API}/devices/fan_living_room").json()["state"]["is_on"] is False
    assert client.get(f"{API}/events").json() == []


# --- PINCH release: one ADJUST command through the existing gesture endpoint ----------------------


def pinch(client: TestClient, device_id: str, value: int, confidence: float = 0.9):
    return client.post(
        f"{API}/gestures/commands",
        json={"gesture": "PINCH", "intent": "ADJUST", "confidence": confidence, "target_device_id": device_id, "value": value},
    )


@pytest.mark.parametrize(
    ("device_id", "value", "action", "state"),
    [
        ("fan_living_room", 70, "set_speed", {"is_on": True, "speed": 70}),
        ("fan_living_room", 0, "set_speed", {"is_on": False, "speed": 0}),
        ("ac_bedroom", 22, "set_temperature", {"is_on": False, "target_temperature_c": 22}),
        ("ac_bedroom", 16, "set_temperature", {"is_on": False, "target_temperature_c": 16}),
    ],
)
def test_pinch_release_sets_fan_speed_or_ac_temperature(
    client: TestClient, device_id: str, value: int, action: str, state: dict
) -> None:
    response = pinch(client, device_id, value)

    assert response.status_code == 200
    body = response.json()
    assert (body["gesture_event"]["gesture"], body["gesture_event"]["value"]) == ("PINCH", value)
    assert (body["device_event"]["action"], body["device_event"]["value"], body["device_event"]["source"]) == (
        action,
        value,
        "gesture",
    )
    assert body["device"]["state"] == state
    assert len(client.get(f"{API}/events").json()) == 1  # exactly one command


@pytest.mark.parametrize(("device_id", "value"), [("ac_bedroom", 31), ("ac_bedroom", 15), ("fan_living_room", 101)])
def test_pinch_values_outside_the_device_range_are_refused(client: TestClient, device_id: str, value: int) -> None:
    response = pinch(client, device_id, value)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "invalid_command")
    assert client.get(f"{API}/events").json() == []


def test_door_never_receives_an_adjust_command(client: TestClient) -> None:
    response = pinch(client, "door_main", 1)

    assert (response.status_code, response.json()["error"]["code"]) == (400, "intent_not_applicable")
    assert client.get(f"{API}/devices/door_main").json()["state"]["is_locked"] is True
    assert client.get(f"{API}/events").json() == []
    assert client.get(f"{API}/gestures/events").json()[0]["outcome"] == "rejected"


def test_low_confidence_pinch_is_rejected(client: TestClient) -> None:
    assert pinch(client, "fan_living_room", 70, confidence=0.5).status_code == 422
    assert client.get(f"{API}/events").json() == []
