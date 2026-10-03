"""The agent pipeline with scripted (possibly wrong or malicious) providers."""

import pytest

from app.ai.agent import HomeAgent
from app.ai.history import InMemoryAgentHistory
from app.ai.models import ActionStatus, AgentResponse
from app.ai.tools import AgentTools
from app.ai.validation import PlanValidator
from app.config import Settings
from app.devices.commands import DeviceCommand
from app.devices.factory import build_device
from app.devices.registry import DeviceRegistry
from app.domain.home_state import HomeState
from app.domain.intents import IntentResolver
from app.domain.policy import SecurityPolicy
from app.events.models import CommandSource
from app.events.store import InMemoryEventStore
from app.sensors.simulated import SimulatedSensorProvider
from tests.ai_helpers import ScriptedProvider, SpyCommandService, action

pytestmark = pytest.mark.anyio


class Harness:
    def __init__(self, plan=None, *, error: str | None = None, allow_unlock: bool = True) -> None:
        settings = Settings(_env_file=None)
        self.devices = DeviceRegistry(build_device(c) for c in settings.devices)
        self.home = HomeState(self.devices, SimulatedSensorProvider(seed=1))
        self.events = InMemoryEventStore()
        self.commands = SpyCommandService(self.home, self.events)
        self.provider = ScriptedProvider(plan, error=error)
        self.agent = HomeAgent(
            provider=self.provider,
            tools=AgentTools(self.home, self.events, self.commands),
            validator=PlanValidator(self.devices, IntentResolver(), SecurityPolicy(allow_ai_unlock=allow_unlock)),
            history=InMemoryAgentHistory(),
        )

    def state(self, device_id: str) -> dict:
        return self.devices.get(device_id).get_state()

    async def ask(self, message: str = "do it") -> AgentResponse:
        return await self.agent.handle(message)


def plan(*actions, message: str = "Plan.") -> dict:
    return {"message": message, "actions": list(actions)}


# --- Execution through CommandService ------------------------------------------------------------


async def test_valid_action_executes_through_command_service_with_ai_source() -> None:
    h = Harness(plan(action("light_living_room", "TURN_ON")))

    response = await h.ask("turn on the light")

    assert h.commands.calls == [("light_living_room", DeviceCommand(action="turn_on"), CommandSource.AI_AGENT)]
    assert response.actions[0].status is ActionStatus.EXECUTED
    assert response.device_events[0].source is CommandSource.AI_AGENT
    assert h.events.recent()[0].source is CommandSource.AI_AGENT
    assert response.changed_devices == ["light_living_room"]
    assert h.state("light_living_room")["is_on"] is True


async def test_set_value_intent_executes_with_parameters() -> None:
    h = Harness(plan(action("fan_living_room", "SET_SPEED", value=70)))

    response = await h.ask()

    assert response.actions[0].status is ActionStatus.EXECUTED
    assert h.state("fan_living_room") == {"is_on": True, "speed": 70}


# --- Rejections never execute ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("bad_action", "code"),
    [
        (action("toaster_kitchen", "TURN_ON"), "unknown_device"),
        (action("door_main", "TURN_ON"), "unsupported_capability"),
        (action("door_main", "TURN_OFF"), "unsupported_capability"),
        (action("light_living_room", "SET_SPEED", value=50), "unsupported_capability"),
        (action("light_living_room", "SET_BRIGHTNESS"), "invalid_parameters"),  # missing value
        (action("light_living_room", "SET_BRIGHTNESS", value=150), "invalid_parameters"),  # out of range
        (action("light_living_room", "SET_BRIGHTNESS", value="70"), "invalid_parameters"),  # wrong type
        (action("ac_bedroom", "SET_TEMPERATURE", value=10), "invalid_parameters"),
        (action("light_living_room", "TURN_ON", value=1), "invalid_parameters"),  # unexpected parameter
        (action(None, "TURN_ON"), "missing_device"),
        (action("light_living_room", "TOGGLE"), "intent_not_allowed"),  # gesture-only intent
        (action("light_living_room", "SELF_DESTRUCT"), "malformed_action"),
        ({"device_id": "light_living_room"}, "malformed_action"),  # no intent
        ({"device_id": "light_living_room", "intent": "TURN_ON", "parameters": {}, "code": "rm -rf /"}, "malformed_action"),
        ("turn everything on", "malformed_action"),  # not an object
    ],
)
async def test_invalid_actions_are_rejected_and_never_executed(bad_action, code: str) -> None:
    h = Harness(plan(bad_action))

    response = await h.ask()

    assert response.actions[0].status is ActionStatus.REJECTED
    assert response.actions[0].code == code
    assert response.any_rejected is True
    assert h.commands.calls == []
    assert h.events.recent() == []


async def test_one_rejected_action_does_not_block_valid_ones() -> None:
    h = Harness(plan(action("door_main", "TURN_ON"), action("fan_living_room", "TURN_ON")))

    response = await h.ask("turn on everything")

    assert [r.status for r in response.actions] == [ActionStatus.REJECTED, ActionStatus.EXECUTED]
    assert [c[0] for c in h.commands.calls] == ["fan_living_room"]


async def test_duplicate_actions_are_rejected() -> None:
    h = Harness(plan(action("fan_living_room", "TURN_ON"), action("fan_living_room", "TURN_ON")))

    response = await h.ask()

    assert [r.status for r in response.actions] == [ActionStatus.EXECUTED, ActionStatus.REJECTED]
    assert response.actions[1].code == "duplicate_action"


# --- Malformed plans ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_plan",
    [
        None,
        "turn on the lights",
        {"actions": []},  # no message
        {"message": "", "actions": []},
        {"message": "hi", "actions": "TURN_ON"},
        {"message": "hi", "actions": [], "execute": "import os"},
        {"message": "hi", "actions": [action("fan_living_room", "TURN_ON")] * 13},  # too many
    ],
)
async def test_malformed_plans_execute_nothing(raw_plan) -> None:
    h = Harness(raw_plan)

    response = await h.ask()

    assert response.plan_valid is False
    assert response.errors
    assert response.actions == []
    assert h.commands.calls == []


async def test_provider_failure_executes_nothing() -> None:
    h = Harness(error="network down")

    response = await h.ask()

    assert response.plan_valid is False
    assert response.errors == ["network down"]
    assert h.commands.calls == []


# --- Door security ---------------------------------------------------------------------------------


async def test_door_lock_proposed_for_an_indirect_request_is_rejected() -> None:
    h = Harness(plan(action("light_living_room", "TURN_OFF"), action("door_main", "LOCK_DOOR")))
    h.devices.get("door_main")._state = h.devices.get("door_main").state.model_copy(update={"is_locked": False})

    response = await h.ask("I'm leaving home")

    assert [r.status for r in response.actions] == [ActionStatus.EXECUTED, ActionStatus.REJECTED]
    assert response.actions[1].code == "not_explicitly_requested"
    assert h.state("door_main")["is_locked"] is False


async def test_explicit_lock_and_unlock_are_executed() -> None:
    h = Harness(plan(action("door_main", "UNLOCK_DOOR")))
    assert (await h.ask("Unlock the front door")).actions[0].status is ActionStatus.EXECUTED
    assert h.state("door_main")["is_locked"] is False

    h.provider._plan = plan(action("door_main", "LOCK_DOOR"))
    assert (await h.ask("Lock the front door")).actions[0].status is ActionStatus.EXECUTED
    assert h.state("door_main")["is_locked"] is True


async def test_unlock_can_be_disabled_by_policy() -> None:
    h = Harness(plan(action("door_main", "UNLOCK_DOOR")), allow_unlock=False)

    response = await h.ask("Unlock the front door")

    assert response.actions[0].code == "unlock_disabled"
    assert h.state("door_main")["is_locked"] is True


# --- Queries --------------------------------------------------------------------------------------


@pytest.mark.parametrize("intent", ["GET_STATUS", "GET_ENERGY", "GET_HISTORY"])
async def test_queries_never_call_command_service(intent: str) -> None:
    h = Harness(plan(action(None, intent)))
    before = {d.id: d.get_state() for d in h.devices.all()}

    response = await h.ask("what's going on?")

    assert response.actions[0].status is ActionStatus.ANSWERED
    assert response.actions[0].data is not None
    assert h.commands.calls == []
    assert {d.id: d.get_state() for d in h.devices.all()} == before


async def test_provider_receives_home_context() -> None:
    h = Harness(plan())

    await h.ask("hello")

    context = h.provider.requests[0].context
    assert {d.id for d in context.devices} == {"light_living_room", "fan_living_room", "ac_bedroom", "door_main"}
    assert context.device("door_main").capabilities == ["LOCK", "UNLOCK"]
    assert context.environment.temperature_c


@pytest.mark.parametrize(
    "message",
    ["don't unlock the door", "do not unlock the door", "never unlock the door", "I don't want the door unlocked"],
)
async def test_negated_unlock_proposed_by_the_model_is_never_executed(message: str) -> None:
    h = Harness(plan(action("door_main", "UNLOCK_DOOR")))  # a model that misreads the negation

    response = await h.ask(message)

    assert response.actions[0].status is ActionStatus.REJECTED
    assert response.actions[0].code == "not_explicitly_requested"
    assert h.commands.calls == []
    assert h.state("door_main")["is_locked"] is True
