"""API tests for gesture commands: validation, confidence gate, execution and logging."""

from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import SendCommand

LIGHT = "light_living_room"
FAN = "fan_living_room"
DOOR = "door_main"

SendGesture = Callable[..., httpx.Response]


@pytest.fixture
def send_gesture(client: TestClient) -> SendGesture:
    return make_sender(client)


def make_sender(client: TestClient) -> SendGesture:
    def send(gesture: str, intent: str, *, confidence: float = 0.95, target: str = LIGHT, **extra: object):
        body = {"gesture": gesture, "intent": intent, "confidence": confidence, "target_device_id": target, **extra}
        return client.post("/api/v1/gestures/commands", json=body)

    return send


def device_state(client: TestClient, device_id: str) -> dict:
    return client.get(f"/api/v1/devices/{device_id}").json()["state"]


def gesture_events(client: TestClient) -> list[dict]:
    return client.get("/api/v1/gestures/events").json()


def device_events(client: TestClient) -> list[dict]:
    return client.get("/api/v1/events").json()


# --- The five actionable gestures ---------------------------------------------------


def test_thumbs_up_turns_target_on(client: TestClient, send_gesture: SendGesture) -> None:
    response = send_gesture("THUMBS_UP", "TURN_ON")

    assert response.status_code == 200
    body = response.json()
    assert body["gesture_event"]["outcome"] == "executed"
    assert body["gesture_event"]["action"] == "turn_on"
    assert body["gesture_event"]["success"] is True
    assert body["device_event"]["source"] == "gesture"
    assert body["device"]["state"]["is_on"] is True
    assert device_state(client, LIGHT)["is_on"] is True


def test_fist_turns_target_off(client: TestClient, send_gesture: SendGesture) -> None:
    send_gesture("THUMBS_UP", "TURN_ON")

    response = send_gesture("FIST", "TURN_OFF")

    assert response.status_code == 200
    assert response.json()["gesture_event"]["action"] == "turn_off"
    assert device_state(client, LIGHT)["is_on"] is False


def test_open_palm_stops_powered_device(client: TestClient, send_gesture: SendGesture) -> None:
    send_gesture("THUMBS_UP", "TURN_ON", target=FAN)

    response = send_gesture("OPEN_PALM", "STOP", target=FAN)

    assert response.status_code == 200
    assert response.json()["gesture_event"]["action"] == "turn_off"
    assert device_state(client, FAN)["is_on"] is False


def test_open_palm_brings_door_to_safe_state(
    client: TestClient, send_gesture: SendGesture, send_command: SendCommand
) -> None:
    send_command(DOOR, "unlock")

    response = send_gesture("OPEN_PALM", "STOP", target=DOOR)

    assert response.status_code == 200
    assert response.json()["gesture_event"]["action"] == "lock"
    assert device_state(client, DOOR)["is_locked"] is True


def test_one_finger_selects_without_changing_the_device(client: TestClient, send_gesture: SendGesture) -> None:
    before = device_state(client, FAN)

    response = send_gesture("ONE_FINGER", "SELECT", target=FAN)

    assert response.status_code == 200
    body = response.json()
    assert body["gesture_event"]["outcome"] == "acknowledged"
    assert body["gesture_event"]["action"] == "select"
    assert body["gesture_event"]["success"] is True
    assert body["device_event"] is None
    assert body["device"]["id"] == FAN
    assert device_state(client, FAN) == before
    assert device_events(client) == []


def test_two_fingers_toggles_target(client: TestClient, send_gesture: SendGesture) -> None:
    first = send_gesture("TWO_FINGERS", "TOGGLE")
    assert first.json()["gesture_event"]["action"] == "turn_on"
    assert device_state(client, LIGHT)["is_on"] is True

    second = send_gesture("TWO_FINGERS", "TOGGLE")
    assert second.json()["gesture_event"]["action"] == "turn_off"
    assert device_state(client, LIGHT)["is_on"] is False


def test_thumbs_up_on_door_locks_it(client: TestClient, send_gesture: SendGesture, send_command: SendCommand) -> None:
    send_command(DOOR, "unlock")

    response = send_gesture("THUMBS_UP", "TURN_ON", target=DOOR)

    assert response.status_code == 200
    assert response.json()["gesture_event"]["action"] == "lock"


# --- Validation -----------------------------------------------------------------------


def test_rejects_unknown_gesture(send_gesture: SendGesture) -> None:
    response = send_gesture("PEACE_SIGN", "TOGGLE")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_rejects_unknown_intent(send_gesture: SendGesture) -> None:
    response = send_gesture("THUMBS_UP", "EXPLODE")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_rejects_intent_that_does_not_match_gesture(client: TestClient, send_gesture: SendGesture) -> None:
    response = send_gesture("THUMBS_UP", "TURN_OFF")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "gesture_intent_mismatch"
    assert error["details"]["expected_intent"] == "TURN_ON"
    assert device_events(client) == []


@pytest.mark.parametrize("gesture", ["NEUTRAL", "UNKNOWN"])
def test_rejects_non_actionable_gestures(send_gesture: SendGesture, gesture: str) -> None:
    response = send_gesture(gesture, "NONE")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "gesture_not_actionable"


@pytest.mark.parametrize("confidence", [-0.1, 1.5, "high", None])
def test_rejects_invalid_confidence(send_gesture: SendGesture, confidence: object) -> None:
    response = send_gesture("THUMBS_UP", "TURN_ON", confidence=confidence)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_rejects_unexpected_fields(send_gesture: SendGesture) -> None:
    response = send_gesture("THUMBS_UP", "TURN_ON", frame="<base64 jpeg>")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


# --- Confidence threshold -----------------------------------------------------------


def test_rejects_confidence_below_threshold(client: TestClient, send_gesture: SendGesture) -> None:
    response = send_gesture("THUMBS_UP", "TURN_ON", confidence=0.74)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "confidence_below_threshold"
    assert error["details"] == {"confidence": 0.74, "threshold": 0.75}
    assert device_state(client, LIGHT)["is_on"] is False
    assert device_events(client) == []
    assert gesture_events(client)[0]["outcome"] == "rejected"


def test_accepts_confidence_exactly_at_threshold(send_gesture: SendGesture) -> None:
    assert send_gesture("THUMBS_UP", "TURN_ON", confidence=0.75).status_code == 200


def test_confidence_threshold_is_configurable() -> None:
    settings = Settings(_env_file=None, sensor_seed=1, gesture_confidence_threshold=0.9)
    with TestClient(create_app(settings)) as client:
        send = make_sender(client)

        assert client.get("/api/v1/gestures/config").json()["confidence_threshold"] == 0.9
        assert send("THUMBS_UP", "TURN_ON", confidence=0.85).status_code == 422
        assert send("THUMBS_UP", "TURN_ON", confidence=0.92).status_code == 200


# --- Failures and policy --------------------------------------------------------------


def test_failed_gesture_command_for_unknown_device(client: TestClient, send_gesture: SendGesture) -> None:
    response = send_gesture("THUMBS_UP", "TURN_ON", target="toaster_kitchen")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "device_not_found"
    event = gesture_events(client)[0]
    assert event["outcome"] == "failed"
    assert event["success"] is False
    assert "toaster_kitchen" in event["detail"]


def test_unlocking_door_by_gesture_is_blocked_by_default(client: TestClient, send_gesture: SendGesture) -> None:
    response = send_gesture("TWO_FINGERS", "TOGGLE", target=DOOR)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "action_blocked"
    assert device_state(client, DOOR)["is_locked"] is True
    event = gesture_events(client)[0]
    assert (event["outcome"], event["action"]) == ("rejected", "unlock")


def test_blocked_actions_are_configurable() -> None:
    settings = Settings(_env_file=None, sensor_seed=1, gesture_blocked_actions=[])
    with TestClient(create_app(settings)) as client:
        response = make_sender(client)("TWO_FINGERS", "TOGGLE", target=DOOR)

        assert response.status_code == 200
        assert device_state(client, DOOR)["is_locked"] is False


# --- Event logging ----------------------------------------------------------------------


def test_gesture_history_records_every_field(client: TestClient, send_gesture: SendGesture) -> None:
    send_gesture("THUMBS_UP", "TURN_ON", confidence=0.96)

    [event] = gesture_events(client)

    assert set(event) >= {
        "event_id", "timestamp", "gesture", "confidence", "intent",
        "target_device_id", "action", "outcome", "success",
    }
    assert event["gesture"] == "THUMBS_UP"
    assert event["confidence"] == 0.96
    assert event["intent"] == "TURN_ON"
    assert event["target_device_id"] == LIGHT
    assert event["action"] == "turn_on"
    assert event["success"] is True


def test_successful_gesture_is_logged_as_device_event_with_gesture_source(
    client: TestClient, send_gesture: SendGesture
) -> None:
    gesture_event = send_gesture("THUMBS_UP", "TURN_ON").json()["gesture_event"]

    [device_event] = device_events(client)

    assert device_event["source"] == "gesture"
    assert device_event["device_id"] == LIGHT
    assert device_event["action"] == "turn_on"
    assert device_event["new_state"]["is_on"] is True
    assert gesture_event["device_event_id"] == device_event["event_id"]


def test_gesture_history_is_newest_first(client: TestClient, send_gesture: SendGesture) -> None:
    send_gesture("THUMBS_UP", "TURN_ON")
    send_gesture("ONE_FINGER", "SELECT", target=FAN)
    send_gesture("FIST", "TURN_OFF", confidence=0.2)

    events = gesture_events(client)

    assert [e["gesture"] for e in events] == ["FIST", "ONE_FINGER", "THUMBS_UP"]
    assert [e["success"] for e in events] == [False, True, True]


def test_gesture_config_exposes_mapping(client: TestClient) -> None:
    config = client.get("/api/v1/gestures/config").json()

    assert config["confidence_threshold"] == 0.75
    assert config["blocked_actions"] == ["unlock"]
    assert {m["gesture"]: m["intent"] for m in config["gestures"]} == {
        "THUMBS_UP": "TURN_ON",
        "FIST": "TURN_OFF",
        "OPEN_PALM": "STOP",
        "ONE_FINGER": "SELECT",
        "TWO_FINGERS": "TOGGLE",
        "NEUTRAL": "NONE",
        "UNKNOWN": "NONE",
    }
