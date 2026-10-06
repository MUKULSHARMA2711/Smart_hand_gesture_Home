"""Secure door unlocking: an explicit request is held until an explicit confirmation, and only
then runs through the existing validation + CommandService path."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.ai.confirmation import Reply, classify_reply
from app.config import Settings
from app.container import build_container
from app.events.models import CommandSource
from app.main import create_app

API = "/api/v1"
DOOR = "door_main"


def ask(client: TestClient, message: str) -> dict:
    response = client.post(f"{API}/ai/command", json={"message": message})
    assert response.status_code == 200
    return response.json()


def locked(client: TestClient) -> bool:
    return client.get(f"{API}/devices/{DOOR}").json()["state"]["is_locked"]


def door_events(client: TestClient) -> list[dict]:
    return [e for e in client.get(f"{API}/events").json() if e["device_id"] == DOOR]


def test_explicit_unlock_request_is_held_for_confirmation(client: TestClient) -> None:
    body = ask(client, "Hey IntelliHome, unlock the main door")

    assert [(a["intent"], a["status"], a["code"]) for a in body["actions"]] == [
        ("UNLOCK_DOOR", "awaiting_confirmation", "confirmation_required")
    ]
    confirmation = body["confirmation"]
    assert confirmation["device_id"] == DOOR
    assert body["reply"] == confirmation["prompt"] == (
        "Are you sure you want to unlock the Main Door? Say 'yes, unlock it' to confirm, or 'cancel'."
    )
    expires = datetime.fromisoformat(confirmation["expires_at"]) - datetime.fromisoformat(confirmation["created_at"])
    assert expires == timedelta(seconds=30)
    assert locked(client) and door_events(client) == []  # nothing executed yet


@pytest.mark.parametrize("reply", ["Yes, unlock it.", "yes, unlock the door", "confirm"])
def test_explicit_spoken_confirmation_unlocks_through_command_service(client: TestClient, reply: str) -> None:
    ask(client, "unlock the main door")

    body = ask(client, reply)

    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("UNLOCK_DOOR", "executed")]
    assert body["reply"] == "Confirmed. The Main Door is unlocked."
    assert not locked(client)
    [event] = door_events(client)
    assert (event["action"], event["source"]) == ("unlock", "ai_agent")
    # A second "yes, unlock it" never re-executes the used confirmation: it is a new, held request.
    assert ask(client, "yes, unlock it")["actions"][0]["status"] == "awaiting_confirmation"
    assert len(door_events(client)) == 1


def test_bare_yes_is_not_enough(client: TestClient) -> None:
    ask(client, "unlock the main door")

    body = ask(client, "yes")

    assert body["actions"][0]["status"] == "awaiting_confirmation"
    assert "say 'yes, unlock it'" in body["reply"]
    assert locked(client)
    ask(client, "yes, unlock it")  # still pending, so an explicit answer works
    assert not locked(client)


@pytest.mark.parametrize("reply", ["no", "cancel", "don't unlock it", "no, keep it locked", "stop"])
def test_cancellation_keeps_the_door_locked(client: TestClient, reply: str) -> None:
    ask(client, "unlock the main door")

    body = ask(client, reply)

    assert [(a["status"], a["code"]) for a in body["actions"]] == [("cancelled", "cancelled_by_user")]
    assert body["reply"] == "Cancelled. The Main Door stays locked."
    assert locked(client) and door_events(client) == []
    ask(client, "yes, unlock it")  # cancelled is final: this only starts a new request
    assert locked(client)


def test_a_different_request_drops_the_pending_unlock(client: TestClient) -> None:
    ask(client, "unlock the main door")

    body = ask(client, "turn on the living room light")

    assert body["confirmation"] is None
    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("TURN_ON", "executed")]
    response = client.post(f"{API}/ai/confirmations/anything", json={"decision": "confirm"})
    assert response.status_code == 404
    assert locked(client)


def test_confirm_and_cancel_buttons(client: TestClient) -> None:
    confirmation_id = ask(client, "unlock the main door")["confirmation"]["confirmation_id"]

    body = client.post(f"{API}/ai/confirmations/{confirmation_id}", json={"decision": "confirm"}).json()
    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("UNLOCK_DOOR", "executed")]
    assert not locked(client)
    # Used once only.
    again = client.post(f"{API}/ai/confirmations/{confirmation_id}", json={"decision": "confirm"})
    assert (again.status_code, again.json()["error"]["code"]) == (404, "confirmation_not_found")

    client.post(f"{API}/devices/{DOOR}/command", json={"action": "lock"})
    confirmation_id = ask(client, "unlock the main door")["confirmation"]["confirmation_id"]
    body = client.post(f"{API}/ai/confirmations/{confirmation_id}", json={"decision": "cancel"}).json()
    assert body["actions"][0]["status"] == "cancelled"
    assert locked(client)


@pytest.mark.parametrize("body", [{"decision": "maybe"}, {}, {"decision": "confirm", "force": True}])
def test_confirmation_endpoint_validates_input(client: TestClient, body: dict) -> None:
    confirmation_id = ask(client, "unlock the main door")["confirmation"]["confirmation_id"]
    assert client.post(f"{API}/ai/confirmations/{confirmation_id}", json=body).status_code == 422
    assert locked(client)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.mark.anyio
async def test_expired_confirmation_cancels_the_unlock() -> None:
    container = build_container(Settings(_env_file=None, ai_confirmation_timeout_s=30))
    clock = Clock()
    container.agent._clock = clock
    door = container.home_state.devices.get(DOOR)

    await container.agent.handle("unlock the main door")
    clock.now += timedelta(seconds=31)
    body = await container.agent.handle("yes, unlock it")

    assert [(a.status, a.code) for a in body.actions] == [("cancelled", "confirmation_expired")]
    assert "expired" in body.reply
    assert door.get_state()["is_locked"] is True
    assert container.event_store.recent() == []


@pytest.mark.anyio
async def test_expired_confirmation_button_returns_410() -> None:
    container = build_container(Settings(_env_file=None))
    clock = Clock()
    container.agent._clock = clock
    pending = (await container.agent.handle("unlock the main door")).confirmation
    clock.now += timedelta(minutes=5)

    from app.ai.errors import ConfirmationExpiredError

    with pytest.raises(ConfirmationExpiredError):
        await container.agent.decide(pending.confirmation_id, confirm=True)
    assert container.home_state.devices.get(DOOR).get_state()["is_locked"] is True


# --- Denied: these never even create a confirmation ----------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "turn everything on",
        "start all devices",
        "activate the house",
        "don't unlock the door",
        "do not unlock the door",
        "never unlock the door",
        "I'm leaving home",
    ],
)
def test_broad_negated_or_indirect_requests_never_unlock(client: TestClient, message: str) -> None:
    body = ask(client, message)

    assert body["confirmation"] is None
    assert all(a["status"] != "executed" or a["device_id"] != DOOR for a in body["actions"])
    ask(client, "yes, unlock it")  # a "yes" without a pending request is just a new request
    assert locked(client)


def test_unlock_disabled_by_policy_is_denied_not_held() -> None:
    with TestClient(create_app(Settings(_env_file=None, ai_allow_unlock=False))) as client:
        body = ask(client, "unlock the main door")
        assert body["confirmation"] is None
        assert [(a["status"], a["code"]) for a in body["actions"]] == [("rejected", "unlock_disabled")]
        assert locked(client)


def test_locking_does_not_need_confirmation(client: TestClient) -> None:
    client.post(f"{API}/devices/{DOOR}/command", json={"action": "unlock"})
    body = ask(client, "lock the front door")
    assert body["actions"][0]["status"] == "executed" and locked(client)


def test_gestures_still_cannot_unlock(client: TestClient) -> None:
    gesture = {"gesture": "TWO_FINGERS", "intent": "TOGGLE", "confidence": 0.95, "target_device_id": DOOR}
    assert client.post(f"{API}/gestures/commands", json=gesture).status_code in (400, 403)
    assert locked(client)


@pytest.mark.anyio
async def test_confirmation_executes_once_through_command_service_with_ai_source() -> None:
    from tests.ai_helpers import SpyCommandService

    container = build_container(Settings(_env_file=None))
    spy = SpyCommandService(container.home_state, container.event_store)
    container.agent._tools._commands = spy

    await container.agent.handle("unlock the main door")
    assert spy.calls == []  # held: nothing sent to the device
    await container.agent.handle("yes, unlock it")

    assert [(device_id, command.action, source) for device_id, command, source in spy.calls] == [
        (DOOR, "unlock", CommandSource.AI_AGENT)
    ]


@pytest.mark.parametrize(
    ("text", "reply"),
    [
        ("Yes, unlock it.", Reply.CONFIRM),
        ("confirm", Reply.CONFIRM),
        ("yes", Reply.AFFIRM_ONLY),
        ("sure", Reply.AFFIRM_ONLY),
        ("no", Reply.CANCEL),
        ("yes, but don't unlock it", Reply.CANCEL),  # any negation wins
        ("what's the temperature?", Reply.OTHER),
    ],
)
def test_reply_classification(text: str, reply: Reply) -> None:
    assert classify_reply(text) is reply
