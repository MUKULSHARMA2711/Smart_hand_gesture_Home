"""Locking the Main Door through the AI agent (text or "Hey Nova" voice, which sends the same text).

Flow under test: request → LOCK_DOOR → capability + policy → CommandService → device → confirmed
state. Locking needs no confirmation; questions and negated requests never change the door, and a
lock request never becomes an unlock.
"""

import pytest
from fastapi.testclient import TestClient

from app.ai.models import ActionStatus
from app.devices.commands import DeviceCommand
from app.devices.types import Capability
from app.domain.policy import asks_about_lock_state, explicitly_requests
from app.events.models import CommandSource
from tests.ai_helpers import action
from tests.test_ai_agent import Harness, plan

API = "/api/v1"
DOOR = "door_main"


def ask(client: TestClient, message: str) -> dict:
    response = client.post(f"{API}/ai/command", json={"message": message})
    assert response.status_code == 200
    return response.json()


def locked(client: TestClient) -> bool:
    return client.get(f"{API}/devices/{DOOR}").json()["state"]["is_locked"]


def unlock_directly(client: TestClient) -> None:
    """The dashboard's own control, to start from an unlocked door."""
    assert client.post(f"{API}/devices/{DOOR}/command", json={"action": "unlock"}).status_code == 200
    assert locked(client) is False


def door_events(client: TestClient) -> list[dict]:
    return [e for e in client.get(f"{API}/events").json() if e["device_id"] == DOOR]


# --- Explicit lock requests -------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "lock the main door",
        "Lock the main door.",
        "Hey Nova, lock the main door.",
        "lock the front door",
        "please lock the main door",
        "can you lock the main door?",
        "lock the door if it's unlocked",
    ],
)
def test_explicit_lock_request_locks_through_command_service(client: TestClient, message: str) -> None:
    unlock_directly(client)

    body = ask(client, message)

    assert [(a["device_id"], a["intent"], a["status"], a["device_action"]) for a in body["actions"]] == [
        (DOOR, "LOCK_DOOR", "executed", "lock")
    ]
    assert body["confirmation"] is None  # locking is not held for confirmation
    assert locked(client) is True  # backend-confirmed state, which the 3D door renders
    event = door_events(client)[0]
    assert (event["action"], event["source"]) == ("lock", "ai_agent")
    assert (event["previous_state"], event["new_state"]) == ({"is_locked": False}, {"is_locked": True})


def test_lock_request_never_produces_an_unlock(client: TestClient) -> None:
    unlock_directly(client)

    for message in ("lock the main door", "lock the door if it's unlocked", "Is the door locked? If not, lock it."):
        body = ask(client, message)
        assert "UNLOCK_DOOR" not in [a["intent"] for a in body["actions"]]
        assert body["confirmation"] is None
    assert all(e["action"] != "unlock" or e["source"] == "frontend" for e in door_events(client))
    assert locked(client) is True


@pytest.mark.anyio
async def test_agent_executes_lock_door_once_through_command_service() -> None:
    h = Harness(plan(action(DOOR, "LOCK_DOOR")))
    await h.devices.get(DOOR).execute_command(DeviceCommand(action="unlock"))

    response = await h.ask("lock the main door")

    assert h.commands.calls == [(DOOR, DeviceCommand(action="lock"), CommandSource.AI_AGENT)]
    assert response.actions[0].status is ActionStatus.EXECUTED
    assert response.confirmation is None
    assert h.state(DOOR) == {"is_locked": True}


# --- Negated requests and questions never change the door -------------------------------------


@pytest.mark.parametrize(
    "message", ["don't lock the door", "do not lock the main door", "never lock the door", "I don't want the door locked"]
)
def test_negated_lock_request_does_nothing(client: TestClient, message: str) -> None:
    unlock_directly(client)
    before = len(door_events(client))

    body = ask(client, message)

    assert all(a["status"] != "executed" for a in body["actions"])
    assert locked(client) is False
    assert len(door_events(client)) == before


@pytest.mark.parametrize(
    "message",
    [
        "is the door locked?",
        "is the main door locked",
        "did you lock the door?",
        "did I lock the door",
        "check if the door is locked",
        "is the door lock on?",
        "did you unlock the door?",
        "has the door been unlocked?",
    ],
)
@pytest.mark.parametrize("start_locked", [True, False])
def test_status_question_answers_without_changing_the_door(client: TestClient, message: str, start_locked: bool) -> None:
    if not start_locked:
        unlock_directly(client)
    before = len(door_events(client))

    body = ask(client, message)

    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("GET_STATUS", "answered")]
    assert body["confirmation"] is None  # a question never starts an unlock confirmation
    assert locked(client) is start_locked
    assert len(door_events(client)) == before
    assert ("is locked" if start_locked else "is unlocked") in body["reply"]


@pytest.mark.anyio
async def test_policy_rejects_a_lock_an_llm_proposes_for_a_question() -> None:
    """Checked in code, independently of the planner: a question is not a lock request."""
    h = Harness(plan(action(DOOR, "LOCK_DOOR")))
    await h.devices.get(DOOR).execute_command(DeviceCommand(action="unlock"))

    response = await h.ask("is the door locked?")

    assert response.actions[0].status is ActionStatus.REJECTED
    assert response.actions[0].code == "not_explicitly_requested"
    assert h.commands.calls == []
    assert h.state(DOOR) == {"is_locked": False}


@pytest.mark.parametrize(
    ("utterance", "lock", "unlock", "question"),
    [
        ("lock the main door", True, False, False),
        ("can you lock the main door?", True, False, False),
        ("I want the door locked", True, False, False),
        ("lock the door if it's unlocked", True, False, False),
        ("is the door locked?", False, False, True),
        ("did you lock the door?", False, False, True),
        ("check whether the door is locked", False, False, True),
        ("has the door been unlocked?", False, False, True),
        ("Is the door locked? If not, lock it.", True, False, False),
        ("don't lock the door", False, False, False),
        ("unlock the main door", False, True, False),
        ("don't unlock the door", False, False, False),
        ("yes, unlock it", False, True, False),
    ],
)
def test_policy_wording(utterance: str, lock: bool, unlock: bool, question: bool) -> None:
    assert explicitly_requests(utterance, Capability.LOCK) is lock
    assert explicitly_requests(utterance, Capability.UNLOCK) is unlock
    assert asks_about_lock_state(utterance) is question


# --- Generic commands still never touch the door ----------------------------------------------


@pytest.mark.parametrize("message", ["turn off everything", "turn on everything", "I'm leaving home", "turn everything off"])
@pytest.mark.parametrize("start_locked", [True, False])
def test_generic_commands_never_lock_or_unlock(client: TestClient, message: str, start_locked: bool) -> None:
    if not start_locked:
        unlock_directly(client)
    before = len(door_events(client))

    body = ask(client, message)

    assert DOOR not in [a["device_id"] for a in body["actions"]]
    assert locked(client) is start_locked
    assert len(door_events(client)) == before


# --- Lock, then ask; unlock security unchanged ------------------------------------------------


def test_lock_then_status_check_reports_the_confirmed_state(client: TestClient) -> None:
    unlock_directly(client)

    ask(client, "lock the main door")
    body = ask(client, "is the main door locked?")

    assert body["actions"][0]["data"]["state"] == {"is_locked": True}
    assert "is locked" in body["reply"]
    assert locked(client) is True


def test_voice_unlock_still_needs_confirmation_and_lock_still_works_after(client: TestClient) -> None:
    held = ask(client, "unlock the main door")
    assert held["actions"][0]["status"] == "awaiting_confirmation"
    assert locked(client) is True

    confirmed = ask(client, "yes, unlock it")
    assert confirmed["actions"][0]["status"] == "executed"
    assert locked(client) is False

    ask(client, "Hey Nova, lock the main door")
    assert locked(client) is True


def test_double_pinch_unlock_unchanged_then_lock_by_voice(client: TestClient) -> None:
    first = client.post(
        f"{API}/gestures/commands",
        json={"gesture": "PINCH", "intent": "UNLOCK_DOOR", "confidence": 0.95, "target_device_id": DOOR},
    ).json()
    assert first["gesture_event"]["outcome"] == "awaiting_confirmation"
    assert locked(client) is True  # the first pinch never unlocks

    second = client.post(f"{API}/ai/confirmations/{first['confirmation']['confirmation_id']}", json={"decision": "confirm"})
    assert second.status_code == 200
    assert locked(client) is False
    assert door_events(client)[0]["source"] == "gesture"

    ask(client, "lock the main door")
    assert locked(client) is True
    assert door_events(client)[0]["source"] == "ai_agent"
