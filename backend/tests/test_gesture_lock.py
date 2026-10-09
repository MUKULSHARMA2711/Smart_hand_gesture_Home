"""A fist on the selected Main Door locks it (FIST may carry LOCK_DOOR); everywhere else a fist
is still TURN_OFF. A fist can never unlock, and the double-pinch unlock is unchanged."""

import pytest
from fastapi.testclient import TestClient

from app.devices.commands import DeviceCommand
from app.events.models import CommandSource
from app.gestures.models import GESTURE_INTENTS, Gesture
from app.gestures.service import GestureService
from app.domain.intents import Intent

API = "/api/v1"
DOOR, FAN, AC, LIGHT = "door_main", "fan_living_room", "ac_bedroom", "light_living_room"


def gesture(client: TestClient, name: str, intent: str, target: str = DOOR, confidence: float = 0.95):
    return client.post(
        f"{API}/gestures/commands",
        json={"gesture": name, "intent": intent, "confidence": confidence, "target_device_id": target},
    )


def fist_on_door(client: TestClient):
    """What the Gesture page sends for a fist while the Main Door is selected."""
    return gesture(client, "FIST", "LOCK_DOOR")


def locked(client: TestClient) -> bool:
    return client.get(f"{API}/devices/{DOOR}").json()["state"]["is_locked"]


def unlock_directly(client: TestClient) -> None:
    assert client.post(f"{API}/devices/{DOOR}/command", json={"action": "unlock"}).status_code == 200


def door_events(client: TestClient) -> list[dict]:
    return [e for e in client.get(f"{API}/events").json() if e["device_id"] == DOOR]


def spy_on_commands(client: TestClient) -> list:
    """Record every CommandService call the gesture service makes (the real service still runs)."""
    service: GestureService = client.app.state.container.gesture_service
    calls = []
    real = service._commands.execute

    async def execute(device_id, command, source):
        calls.append((device_id, command, source))
        return await real(device_id, command, source)

    service._commands.execute = execute
    return calls


# --- Fist on the Main Door ---------------------------------------------------------------------


def test_fist_on_the_door_locks_it_through_command_service(client: TestClient) -> None:
    unlock_directly(client)
    calls = spy_on_commands(client)

    body = fist_on_door(client).json()

    assert calls == [(DOOR, DeviceCommand(action="lock"), CommandSource.GESTURE)]
    assert body["gesture_event"]["outcome"] == "executed"
    assert body["gesture_event"]["action"] == "lock"
    assert body["device"]["state"] == {"is_locked": True}  # the backend-confirmed state the 3D door renders
    event = door_events(client)[0]
    assert (event["action"], event["source"]) == ("lock", "gesture")
    assert (event["previous_state"], event["new_state"]) == ({"is_locked": False}, {"is_locked": True})
    assert locked(client) is True


def test_fist_on_an_already_locked_door_sends_no_repeated_command(client: TestClient) -> None:
    calls = spy_on_commands(client)
    before = len(door_events(client))

    body = fist_on_door(client).json()

    assert calls == []
    assert body["gesture_event"]["outcome"] == "acknowledged"
    assert body["gesture_event"]["detail"] == "Main Door is already locked."
    assert body["device_event"] is None
    assert len(door_events(client)) == before
    assert locked(client) is True


@pytest.mark.parametrize("intent", ["UNLOCK_DOOR", "TOGGLE", "TURN_ON", "STOP", "ADJUST"])
def test_a_fist_can_never_unlock(client: TestClient, intent: str) -> None:
    response = gesture(client, "FIST", intent)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "gesture_intent_mismatch"
    assert locked(client) is True


def test_fist_turn_off_on_the_door_is_still_not_applicable(client: TestClient) -> None:
    unlock_directly(client)

    response = gesture(client, "FIST", "TURN_OFF")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "intent_not_applicable"
    assert locked(client) is False


def test_low_confidence_fist_cannot_lock(client: TestClient) -> None:
    unlock_directly(client)

    response = gesture(client, "FIST", "LOCK_DOOR", confidence=0.5)

    assert response.json()["error"]["code"] == "confidence_below_threshold"
    assert locked(client) is False


# --- Fist on the fan, AC and light: unchanged -------------------------------------------------


@pytest.mark.parametrize(
    ("target", "on"), [(FAN, {"action": "turn_on"}), (AC, {"action": "turn_on"}), (LIGHT, {"action": "turn_on"})]
)
def test_fist_still_turns_off_fan_ac_and_light(client: TestClient, target: str, on: dict) -> None:
    client.post(f"{API}/devices/{target}/command", json=on)

    body = gesture(client, "FIST", "TURN_OFF", target).json()

    assert body["gesture_event"]["action"] == "turn_off"
    assert body["device"]["state"]["is_on"] is False


@pytest.mark.parametrize("target", [FAN, AC, LIGHT])
def test_lock_door_from_a_fist_never_applies_to_appliances(client: TestClient, target: str) -> None:
    client.post(f"{API}/devices/{target}/command", json={"action": "turn_on"})

    response = gesture(client, "FIST", "LOCK_DOOR", target)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "intent_not_applicable"  # appliances have no LOCK
    assert client.get(f"{API}/devices/{target}").json()["state"]["is_on"] is True


def test_global_gesture_mapping_is_unchanged(client: TestClient) -> None:
    assert GESTURE_INTENTS[Gesture.FIST] is Intent.TURN_OFF
    mapping = {m["gesture"]: m["intent"] for m in client.get(f"{API}/gestures/config").json()["gestures"]}
    assert mapping["FIST"] == "TURN_OFF"
    assert mapping["OPEN_PALM"] == "STOP"


# --- With the double-pinch unlock --------------------------------------------------------------


def test_double_pinch_still_unlocks_and_a_fist_locks_again(client: TestClient) -> None:
    first = gesture(client, "PINCH", "UNLOCK_DOOR").json()
    assert first["gesture_event"]["outcome"] == "awaiting_confirmation"
    assert locked(client) is True

    confirm = client.post(f"{API}/ai/confirmations/{first['confirmation']['confirmation_id']}", json={"decision": "confirm"})
    assert confirm.status_code == 200
    assert locked(client) is False

    assert fist_on_door(client).json()["gesture_event"]["outcome"] == "executed"
    assert locked(client) is True
    assert [e["action"] for e in door_events(client)[:2]] == ["lock", "unlock"]


def test_fist_while_an_unlock_is_pending_cancels_it_and_never_unlocks(client: TestClient) -> None:
    """The Gesture page answers a fist during a pending unlock with a cancel (and nothing else)."""
    first = gesture(client, "PINCH", "UNLOCK_DOOR").json()
    confirmation_id = first["confirmation"]["confirmation_id"]

    cancel = client.post(f"{API}/ai/confirmations/{confirmation_id}", json={"decision": "cancel"})
    assert cancel.json()["actions"][0]["status"] == "cancelled"
    assert locked(client) is True

    late = client.post(f"{API}/ai/confirmations/{confirmation_id}", json={"decision": "confirm"})
    assert late.status_code == 404  # the cancelled request can never be confirmed afterwards
    assert locked(client) is True
    assert all(e["action"] != "unlock" for e in door_events(client))

    # A separate, later fist may lock: here the door is already locked, so nothing is sent.
    assert fist_on_door(client).json()["gesture_event"]["outcome"] == "acknowledged"
