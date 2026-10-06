"""Secure gesture unlock by double pinch: the first pinch on the Main Door only *requests* an
unlock; the second pinch confirms it through the existing POST /ai/confirmations/{id}."""

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


def first_pinch(client: TestClient, target: str = DOOR):
    """What the Gesture page sends for a pinch while the Main Door is selected."""
    return gesture(client, "PINCH", "UNLOCK_DOOR", target)


def second_pinch(client: TestClient, confirmation_id: str):
    """What the Gesture page sends for the confirming pinch (the existing confirmation API)."""
    return decide(client, confirmation_id, "confirm")


def decide(client: TestClient, confirmation_id: str, decision: str):
    return client.post(f"{API}/ai/confirmations/{confirmation_id}", json={"decision": decision})


def locked(client: TestClient) -> bool:
    return client.get(f"{API}/devices/{DOOR}").json()["state"]["is_locked"]


def device_events(client: TestClient) -> list[dict]:
    return client.get(f"{API}/events").json()


def pending(client: TestClient):
    return client.app.state.container.agent._confirmations.pending


def test_first_pinch_creates_a_pending_confirmation_and_does_not_unlock(client: TestClient) -> None:
    response = first_pinch(client)

    assert response.status_code == 200
    body = response.json()
    assert body["device_event"] is None  # nothing executed
    assert (body["gesture_event"]["gesture"], body["gesture_event"]["outcome"]) == ("PINCH", "awaiting_confirmation")
    confirmation = body["confirmation"]
    assert (confirmation["device_id"], confirmation["intent"], confirmation["source"]) == (DOOR, "UNLOCK_DOOR", "gesture")
    assert confirmation["prompt"] == "Unlock the Main Door? Pinch again to confirm, open palm to cancel."
    assert locked(client) and device_events(client) == []


def test_second_pinch_confirms_exactly_once_through_command_service(client: TestClient) -> None:
    confirmation_id = first_pinch(client).json()["confirmation"]["confirmation_id"]
    assert locked(client)  # still locked until the backend confirms

    body = second_pinch(client, confirmation_id).json()

    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("UNLOCK_DOOR", "executed")]
    assert not locked(client)
    [event] = device_events(client)
    assert (event["device_id"], event["action"], event["source"]) == (DOOR, "unlock", "gesture")
    # A repeated second pinch cannot execute twice.
    assert second_pinch(client, confirmation_id).status_code == 404
    assert len(device_events(client)) == 1


def test_repeated_first_pinches_never_unlock(client: TestClient) -> None:
    for _ in range(3):
        assert first_pinch(client).status_code == 200  # each only (re)creates the pending request
    assert locked(client) and device_events(client) == []


def test_confirming_without_a_pending_request_does_nothing(client: TestClient) -> None:
    response = second_pinch(client, "no-such-request")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "confirmation_not_found")
    assert locked(client) and device_events(client) == []


def test_cancel_keeps_the_door_locked(client: TestClient) -> None:
    confirmation_id = first_pinch(client).json()["confirmation"]["confirmation_id"]

    body = decide(client, confirmation_id, "cancel").json()  # open palm / other gesture / hand lost

    assert body["actions"][0]["status"] == "cancelled"
    assert locked(client) and device_events(client) == []
    assert second_pinch(client, confirmation_id).status_code == 404  # cancelled is final


def test_expired_confirmation_cannot_unlock(client: TestClient) -> None:
    confirmation_id = first_pinch(client).json()["confirmation"]["confirmation_id"]
    agent = client.app.state.container.agent
    later = agent._clock() + timedelta(seconds=31)
    agent._clock = lambda: later

    response = second_pinch(client, confirmation_id)

    assert (response.status_code, response.json()["error"]["code"]) == (410, "confirmation_expired")
    assert locked(client) and device_events(client) == []


@pytest.mark.parametrize("target", [FAN, AC, "light_living_room"])
def test_an_unlock_request_on_another_device_does_nothing(client: TestClient, target: str) -> None:
    before = client.get(f"{API}/devices/{target}").json()["state"]

    response = first_pinch(client, target)

    assert (response.status_code, response.json()["error"]["code"]) == (400, "intent_not_applicable")
    assert client.get(f"{API}/devices/{target}").json()["state"] == before
    assert device_events(client) == [] and pending(client) is None


@pytest.mark.parametrize("name", ["THUMBS_UP", "FIST", "OPEN_PALM", "ONE_FINGER", "TWO_FINGERS"])
def test_only_a_pinch_may_request_an_unlock(client: TestClient, name: str) -> None:
    response = gesture(client, name, "UNLOCK_DOOR")
    assert (response.status_code, response.json()["error"]["code"]) == (422, "gesture_intent_mismatch")
    assert locked(client) and pending(client) is None


def test_low_confidence_pinch_cannot_request_an_unlock(client: TestClient) -> None:
    assert gesture(client, "PINCH", "UNLOCK_DOOR", confidence=0.5).status_code == 422
    assert pending(client) is None


@pytest.mark.parametrize(
    ("name", "intent", "extra"),
    [
        ("THUMBS_UP", "TURN_ON", {}),
        ("FIST", "TURN_OFF", {}),
        ("OPEN_PALM", "STOP", {}),
        ("ONE_FINGER", "SELECT", {}),
        ("TWO_FINGERS", "TOGGLE", {}),
        ("PINCH", "ADJUST", {"value": 1}),
        ("PINCH", "UNLOCK_DOOR", {"value": 1}),
    ],
)
def test_generic_gestures_never_unlock(client: TestClient, name: str, intent: str, extra: dict) -> None:
    gesture(client, name, intent, **extra)
    assert locked(client)
    assert all(e["action"] != "unlock" for e in device_events(client))


def test_open_palm_still_stops_the_fan(client: TestClient) -> None:
    client.post(f"{API}/devices/{FAN}/command", json={"action": "turn_on"})

    response = gesture(client, "OPEN_PALM", "STOP", FAN)

    assert response.status_code == 200
    assert (response.json()["device_event"]["action"], response.json()["device"]["state"]["is_on"]) == ("turn_off", False)


@pytest.mark.parametrize(("target", "value", "field"), [(FAN, 70, "speed"), (AC, 22, "target_temperature_c")])
def test_pinch_still_adjusts_fan_and_ac(client: TestClient, target: str, value: int, field: str) -> None:
    response = gesture(client, "PINCH", "ADJUST", target, value=value)
    assert response.status_code == 200 and response.json()["confirmation"] is None
    assert client.get(f"{API}/devices/{target}").json()["state"][field] == value


def test_gesture_unlock_can_be_disabled() -> None:
    with TestClient(create_app(Settings(_env_file=None, gesture_door_unlock=False))) as client:
        response = first_pinch(client)
        assert (response.status_code, response.json()["error"]["code"]) == (403, "action_blocked")
        assert locked(client)


def test_gesture_unlock_stays_blocked_when_ai_unlock_is_disabled() -> None:
    with TestClient(create_app(Settings(_env_file=None, ai_allow_unlock=False))) as client:
        assert first_pinch(client).status_code == 403
        assert locked(client)
