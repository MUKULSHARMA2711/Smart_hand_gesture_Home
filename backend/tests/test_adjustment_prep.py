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
        {"gesture": "THUMBS_UP", "intent": "TURN_ON", "value": 70},  # current gestures take no value
        {"gesture": "THUMBS_UP", "intent": "ADJUST", "value": 70},  # no gesture maps to ADJUST yet
        {"gesture": "THUMBS_UP", "intent": "TURN_ON", "value": 70.5},
    ],
)
def test_gesture_values_are_rejected_until_a_gesture_needs_them(client: TestClient, body: dict) -> None:
    response = client.post(
        f"{API}/gestures/commands", json={**body, "confidence": 0.95, "target_device_id": "fan_living_room"}
    )
    assert response.status_code == 422
    assert client.get(f"{API}/devices/fan_living_room").json()["state"]["is_on"] is False
    assert client.get(f"{API}/events").json() == []
