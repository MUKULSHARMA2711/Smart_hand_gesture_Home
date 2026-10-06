"""End-to-end AI agent behaviour through POST /api/v1/ai/command with the mock provider."""

import pytest
from fastapi.testclient import TestClient

from app.ai.providers import MockAIProvider, PlanningRequest
from app.ai.tools import AgentTools
from app.config import Settings
from app.container import build_container
from tests.conftest import SendCommand

DOOR = "door_main"


def ask(client: TestClient, message: str) -> dict:
    response = client.post("/api/v1/ai/command", json={"message": message})
    assert response.status_code == 200
    return response.json()


def states(client: TestClient) -> dict[str, dict]:
    return {d["id"]: d["state"] for d in client.get("/api/v1/devices").json()}


def planned(body: dict) -> list[tuple]:
    return [(a["device_id"], a["intent"], a["parameters"]) for a in body["actions"]]


# --- Examples A-G ---------------------------------------------------------------------------


def test_example_a_turn_on_living_room_light(client: TestClient) -> None:
    body = ask(client, "Turn on the living room light.")

    assert planned(body) == [("light_living_room", "TURN_ON", {})]
    assert body["actions"][0]["status"] == "executed"
    assert body["changed_devices"] == ["light_living_room"]
    assert states(client)["light_living_room"]["is_on"] is True


def test_example_b_turn_off_everything_leaves_door_unchanged(client: TestClient, send_command: SendCommand) -> None:
    for device_id in ("light_living_room", "fan_living_room", "ac_bedroom"):
        send_command(device_id, "turn_on")
    send_command(DOOR, "unlock")

    body = ask(client, "Turn off everything.")

    assert {a["device_id"] for a in body["actions"]} == {"light_living_room", "fan_living_room", "ac_bedroom"}
    after = states(client)
    assert not any(after[d]["is_on"] for d in ("light_living_room", "fan_living_room", "ac_bedroom"))
    assert after[DOOR]["is_locked"] is False  # untouched, still unlocked
    assert all(e["device_id"] != DOOR for e in body["device_events"])


def test_turn_on_everything_never_modifies_door(client: TestClient) -> None:
    door_before = states(client)[DOOR]

    body = ask(client, "Turn on everything")

    assert DOOR not in {a["device_id"] for a in body["actions"]}
    assert states(client)[DOOR] == door_before
    assert all(e["device_id"] != DOOR for e in client.get("/api/v1/events").json())


def test_example_c_leaving_home_turns_off_active_devices_but_not_the_door(
    client: TestClient, send_command: SendCommand
) -> None:
    send_command("fan_living_room", "turn_on")
    send_command(DOOR, "unlock")

    body = ask(client, "I'm leaving home.")

    assert planned(body) == [("fan_living_room", "TURN_OFF", {})]
    assert states(client)[DOOR]["is_locked"] is False
    assert "lock the front door" in body["reply"]


def test_example_d_lock_the_front_door(client: TestClient, send_command: SendCommand) -> None:
    send_command(DOOR, "unlock")

    body = ask(client, "Lock the front door.")

    assert planned(body) == [(DOOR, "LOCK_DOOR", {})]
    assert body["actions"][0]["status"] == "executed"
    assert states(client)[DOOR]["is_locked"] is True


def test_example_e_unlock_the_front_door(client: TestClient) -> None:
    body = ask(client, "Unlock the front door.")

    assert planned(body) == [(DOOR, "UNLOCK_DOOR", {})]
    assert states(client)[DOOR]["is_locked"] is False


def test_example_f_status_query_does_not_modify_devices(client: TestClient) -> None:
    before = states(client)

    body = ask(client, "What's happening in my house?")

    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("GET_STATUS", "answered")]
    assert "Main Door is locked" in body["reply"]
    assert states(client) == before
    assert body["device_events"] == []
    assert client.get("/api/v1/events").json() == []


def test_example_g_energy_query_does_not_modify_devices(client: TestClient) -> None:
    before = states(client)

    body = ask(client, "How much energy are we using?")

    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("GET_ENERGY", "answered")]
    assert body["actions"][0]["data"]["total_power_w"] > 0
    assert states(client) == before
    assert client.get("/api/v1/events").json() == []


def test_fan_on_and_speed_seventy(client: TestClient) -> None:
    body = ask(client, "Turn on the fan and set it to 70.")

    assert planned(body) == [("fan_living_room", "TURN_ON", {}), ("fan_living_room", "SET_SPEED", {"value": 70})]
    assert body["reply"] == "The Living Room Fan is currently off. I'll turn it on and set its speed to 70%."
    assert states(client)["fan_living_room"] == {"is_on": True, "speed": 70}


def test_explicitly_targeted_unsupported_action_is_rejected(client: TestClient) -> None:
    body = ask(client, "turn on the front door")

    assert body["actions"][0]["status"] == "rejected"
    assert body["actions"][0]["code"] == "unsupported_capability"
    assert body["any_rejected"] is True
    assert body["outcome"] == "1 rejected."
    assert states(client)[DOOR]["is_locked"] is True


# --- Events and history -------------------------------------------------------------------------


def test_ai_events_use_ai_agent_source(client: TestClient) -> None:
    ask(client, "Turn on the light and fan")

    events = client.get("/api/v1/events").json()
    assert len(events) == 2
    assert {e["source"] for e in events} == {"ai_agent"}


def test_ai_history_records_interactions(client: TestClient) -> None:
    ask(client, "Turn on the living room light")
    ask(client, "How much energy are we using?")

    history = client.get("/api/v1/ai/history").json()

    assert [h["request"] for h in history] == ["How much energy are we using?", "Turn on the living room light"]
    assert history[1]["actions"][0]["status"] == "executed"


def test_ai_status_reports_provider_and_policy(client: TestClient) -> None:
    status = client.get("/api/v1/ai/status").json()

    assert (status["provider"], status["mock"]) == ("mock", True)
    assert "LOCK_DOOR" in status["intents"] and "TOGGLE" not in status["intents"]
    assert status["security_policy"]["security_sensitive_capabilities"] == ["LOCK", "UNLOCK"]


@pytest.mark.parametrize("body", [{}, {"message": ""}, {"message": "   "}, {"message": "hi", "model": "x"}])
def test_rejects_malformed_requests(client: TestClient, body: dict) -> None:
    response = client.post("/api/v1/ai/command", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


# --- Mock provider determinism ------------------------------------------------------------------


@pytest.mark.anyio
async def test_mock_provider_is_deterministic() -> None:
    container = build_container(Settings(_env_file=None, sensor_seed=5))
    tools = AgentTools(container.home_state, container.event_store, container.command_service)
    context = tools.home_context()
    provider = MockAIProvider()

    for message in ["Turn off everything", "Turn on the fan and set it to 70", "Lock the front door", "make tea"]:
        first = await provider.plan(PlanningRequest(message, context, tools))
        second = await provider.plan(PlanningRequest(message, context, tools))
        assert first == second


@pytest.mark.anyio
@pytest.mark.parametrize("message", ["Turn on everything", "turn everything off", "switch off all devices", "I'm leaving"])
async def test_mock_provider_never_plans_door_actions_for_broad_requests(message: str) -> None:
    container = build_container(Settings(_env_file=None, sensor_seed=5))
    tools = AgentTools(container.home_state, container.event_store, container.command_service)

    plan = await MockAIProvider().plan(PlanningRequest(message, tools.home_context(), tools))

    assert all(a["device_id"] != DOOR for a in plan["actions"])


def test_unavailable_provider_reports_error_and_device_control_still_works() -> None:
    from app.ai.providers import UnavailableAIProvider
    from app.main import create_app

    app = create_app(Settings(_env_file=None), ai_provider=UnavailableAIProvider("anthropic", "claude-opus-5-5", "no key"))
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/command", json={"message": "turn on the light"})

        assert response.status_code == 503
        error = response.json()["error"]
        assert (error["code"], error["message"]) == ("ai_unavailable", "AI service is currently unavailable.")
        assert error["details"]["reason"] == "no key"
        assert client.get("/api/v1/events").json() == []
        assert client.post("/api/v1/devices/light_living_room/command", json={"action": "turn_on"}).status_code == 200


@pytest.mark.parametrize(
    "message",
    ["don't unlock the door", "do not unlock the door", "never unlock the door", "I don't want the door unlocked"],
)
def test_negated_unlock_requests_do_not_unlock_the_door(client: TestClient, message: str) -> None:
    body = ask(client, message)

    assert all(a["status"] != "executed" for a in body["actions"])
    assert states(client)[DOOR]["is_locked"] is True
    assert client.get("/api/v1/events").json() == []


def test_explicit_unlock_still_works(client: TestClient) -> None:
    body = ask(client, "unlock the front door")

    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("UNLOCK_DOOR", "executed")]
    assert states(client)[DOOR]["is_locked"] is False


@pytest.mark.parametrize(
    ("message", "reply"),
    [
        ("don't unlock the door", "Understood, I won't unlock the Main Door. It stays locked."),
        ("never lock the front door", "Understood, I won't lock the Main Door."),
    ],
)
def test_mock_planner_does_not_propose_negated_door_actions(client: TestClient, message: str, reply: str) -> None:
    # Regression: the planner replied "I'll unlock it" (the policy then rejected the action),
    # so the user saw a reply that contradicted their request.
    body = ask(client, message)

    assert body["reply"].startswith(reply)
    assert body["actions"] == []
    assert client.get("/api/v1/events").json() == []


def test_negated_door_clause_does_not_swallow_the_rest_of_the_request(client: TestClient) -> None:
    body = ask(client, "turn on the light but don't unlock the door")

    assert [(a["device_id"], a["intent"], a["status"]) for a in body["actions"]] == [
        ("light_living_room", "TURN_ON", "executed")
    ]
    assert states(client)[DOOR]["is_locked"] is True
