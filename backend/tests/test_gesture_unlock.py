"""Secure gesture unlock: FOUR_FINGERS only *requests* an unlock; it executes only after an
explicit confirmation through the existing POST /ai/confirmations/{id} (pinch in the UI)."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

API = "/api/v1"
DOOR, FAN, AC = "door_main", "fan_living_room", "ac_bedroom"


def gesture(client: TestClient, name: str, intent: str, target: str = DOOR, confidence: float = 0.95, **extra):
    return client.post(
        f"{API}/gestures/commands",
        json={"gesture": name, "intent": intent, "confidence": confidence, "target_device_id": target, **extra},
    )


def four_fingers(client: TestClient, target: str = DOOR):
    return gesture(client, "FOUR_FINGERS", "UNLOCK_DOOR", target)


def decide(client: TestClient, confirmation_id: str, decision: str):
    return client.post(f"{API}/ai/confirmations/{confirmation_id}", json={"decision": decision})


def locked(client: TestClient) -> bool:
    return client.get(f"{API}/devices/{DOOR}").json()["state"]["is_locked"]


def device_events(client: TestClient) -> list[dict]:
    return client.get(f"{API}/events").json()


def test_four_fingers_creates_a_pending_confirmation_and_never_unlocks(client: TestClient) -> None:
    response = four_fingers(client)

    assert response.status_code == 200
    body = response.json()
    assert body["device_event"] is None  # nothing executed
    assert body["gesture_event"]["outcome"] == "awaiting_confirmation"
    confirmation = body["confirmation"]
    assert (confirmation["device_id"], confirmation["intent"], confirmation["source"]) == (DOOR, "UNLOCK_DOOR", "gesture")
    assert confirmation["prompt"] == "Unlock the Main Door? Pinch to confirm, open palm to cancel."
    assert locked(client) and device_events(client) == []


def test_confirmation_unlocks_once_through_command_service_as_a_gesture(client: TestClient) -> None:
    confirmation_id = four_fingers(client).json()["confirmation"]["confirmation_id"]
    assert locked(client)  # still locked until the backend confirms

    body = decide(client, confirmation_id, "confirm").json()

    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("UNLOCK_DOOR", "executed")]
    assert not locked(client)
    [event] = device_events(client)
    assert (event["device_id"], event["action"], event["source"]) == (DOOR, "unlock", "gesture")
    # A second confirmation (or a repeated pinch) cannot unlock again.
    assert decide(client, confirmation_id, "confirm").status_code == 404
    assert len(device_events(client)) == 1


def test_confirming_without_a_pending_request_does_nothing(client: TestClient) -> None:
    response = decide(client, "no-such-request", "confirm")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "confirmation_not_found")
    assert locked(client) and device_events(client) == []


def test_cancel_keeps_the_door_locked(client: TestClient) -> None:
    confirmation_id = four_fingers(client).json()["confirmation"]["confirmation_id"]

    body = decide(client, confirmation_id, "cancel").json()

    assert body["actions"][0]["status"] == "cancelled"
    assert locked(client) and device_events(client) == []
    assert decide(client, confirmation_id, "confirm").status_code == 404  # cancelled is final


def test_expired_confirmation_cannot_unlock(client: TestClient) -> None:
    confirmation_id = four_fingers(client).json()["confirmation"]["confirmation_id"]
    agent = client.app.state.container.agent
    later = agent._clock() + timedelta(seconds=31)
    agent._clock = lambda: later

    response = decide(client, confirmation_id, "confirm")

    assert (response.status_code, response.json()["error"]["code"]) == (410, "confirmation_expired")
    assert locked(client) and device_events(client) == []


@pytest.mark.parametrize("target", [FAN, AC, "light_living_room"])
def test_four_fingers_does_nothing_to_other_devices(client: TestClient, target: str) -> None:
    before = client.get(f"{API}/devices/{target}").json()["state"]

    response = four_fingers(client, target)

    assert (response.status_code, response.json()["error"]["code"]) == (400, "intent_not_applicable")
    assert client.get(f"{API}/devices/{target}").json()["state"] == before
    assert device_events(client) == []
    assert client.app.state.container.agent._confirmations.pending is None


def test_low_confidence_four_fingers_is_rejected(client: TestClient) -> None:
    response = gesture(client, "FOUR_FINGERS", "UNLOCK_DOOR", confidence=0.5)
    assert response.status_code == 422
    assert client.app.state.container.agent._confirmations.pending is None


@pytest.mark.parametrize(
    ("name", "intent", "extra"),
    [
        ("THUMBS_UP", "TURN_ON", {}),
        ("FIST", "TURN_OFF", {}),
        ("OPEN_PALM", "STOP", {}),
        ("ONE_FINGER", "SELECT", {}),
        ("TWO_FINGERS", "TOGGLE", {}),
        ("PINCH", "ADJUST", {"value": 1}),
        ("FOUR_FINGERS", "TURN_ON", {}),  # four fingers only maps to the confirmed request
    ],
)
def test_generic_gestures_never_unlock(client: TestClient, name: str, intent: str, extra: dict) -> None:
    gesture(client, name, intent, **extra)
    assert locked(client)
    assert all(e["action"] != "unlock" for e in device_events(client))


@pytest.mark.parametrize(("target", "value", "field"), [(FAN, 70, "speed"), (AC, 22, "target_temperature_c")])
def test_pinch_still_adjusts_fan_and_ac(client: TestClient, target: str, value: int, field: str) -> None:
    response = gesture(client, "PINCH", "ADJUST", target, value=value)
    assert response.status_code == 200 and response.json()["confirmation"] is None
    assert client.get(f"{API}/devices/{target}").json()["state"][field] == value


def test_gesture_unlock_can_be_disabled() -> None:
    with TestClient(create_app(Settings(_env_file=None, gesture_door_unlock=False))) as client:
        response = four_fingers(client)
        assert (response.status_code, response.json()["error"]["code"]) == (403, "action_blocked")
        assert locked(client)


def test_gesture_unlock_respects_the_unlock_policy() -> None:
    with TestClient(create_app(Settings(_env_file=None, ai_allow_unlock=False))) as client:
        assert four_fingers(client).status_code == 403
        assert locked(client)
