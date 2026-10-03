"""The Claude provider's tool loop, exercised with a fake client (no network, no API key)."""

import json
from types import SimpleNamespace

import pytest

from app.ai.providers import AIProviderError, PlanningRequest
from app.ai.providers.anthropic_provider import AnthropicProvider
from app.ai.tools import AgentTools
from app.config import Settings
from app.container import build_container

pytestmark = pytest.mark.anyio


def text_response(payload: object) -> SimpleNamespace:
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(payload))])


def tool_response(*calls: tuple[str, str, dict]) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[SimpleNamespace(type="tool_use", id=call_id, name=name, input=args) for call_id, name, args in calls],
    )


class FakeClient:
    def __init__(self, *responses: SimpleNamespace) -> None:
        self._responses = list(responses)
        self.requests: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.requests.append(kwargs)
        return self._responses.pop(0)


def make_request(message: str = "How much energy are we using?") -> PlanningRequest:
    container = build_container(Settings(_env_file=None, sensor_seed=2))
    tools = AgentTools(container.home_state, container.event_store, container.command_service)
    return PlanningRequest(message=message, context=tools.home_context(), tools=tools)


def provider(client: FakeClient) -> AnthropicProvider:
    return AnthropicProvider(model="claude-opus-5-5", client=client)


async def test_returns_structured_plan_and_strips_null_parameters() -> None:
    client = FakeClient(
        text_response(
            {
                "message": "Turning on the fan.",
                "actions": [{"device_id": "fan_living_room", "intent": "TURN_ON", "parameters": {"value": None, "limit": None}}],
            }
        )
    )

    plan = await provider(client).plan(make_request("turn on the fan"))

    assert plan["actions"] == [{"device_id": "fan_living_room", "intent": "TURN_ON", "parameters": {}}]
    request = client.requests[0]
    assert request["model"] == "claude-opus-5-5"
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert request["fallbacks"] == "default"
    assert {tool["name"] for tool in request["tools"]} == {
        "get_home_state", "get_device_status", "get_recent_events", "get_energy_usage"
    }
    assert all(tool["strict"] for tool in request["tools"])
    assert "fan_living_room" in request["messages"][0]["content"]  # home context is in the prompt


async def test_runs_read_only_tools_and_returns_results_to_the_model() -> None:
    client = FakeClient(
        tool_response(("call_1", "get_energy_usage", {})),
        text_response({"message": "You're using little power.", "actions": [{"device_id": None, "intent": "GET_ENERGY", "parameters": {"value": None, "limit": None}}]}),
    )

    plan = await provider(client).plan(make_request())

    assert plan["actions"][0]["intent"] == "GET_ENERGY"
    tool_results = client.requests[1]["messages"][-1]["content"]
    assert tool_results[0]["tool_use_id"] == "call_1"
    assert "total_power_w" in json.loads(tool_results[0]["content"])


async def test_model_cannot_call_a_device_control_tool() -> None:
    client = FakeClient(
        tool_response(("call_1", "control_device", {"device_id": "door_main", "command": "unlock"})),
        text_response({"message": "OK.", "actions": []}),
    )

    await provider(client).plan(make_request("unlock the door"))

    result = client.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True
    assert "Unknown tool" in result["content"]


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (SimpleNamespace(stop_reason="refusal", content=[], stop_details=SimpleNamespace(category="cyber")), "declined"),
        (SimpleNamespace(stop_reason="max_tokens", content=[]), "cut off"),
        (SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="not json")]), "valid JSON"),
    ],
)
async def test_unusable_responses_raise_provider_errors(response, message: str) -> None:
    with pytest.raises(AIProviderError, match=message):
        await provider(FakeClient(response)).plan(make_request())


async def test_tool_loop_is_bounded() -> None:
    client = FakeClient(*[tool_response((f"c{i}", "get_home_state", {})) for i in range(10)])

    with pytest.raises(AIProviderError, match="rounds"):
        await AnthropicProvider(model="claude-opus-5-5", client=client, max_tool_rounds=2).plan(make_request())
