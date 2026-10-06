"""ML APIs, events, AI integration, and the rule that ML never bypasses CommandService."""

import pytest
from fastapi.testclient import TestClient

from app.ai.agent import HomeAgent
from app.ai.history import InMemoryAgentHistory
from app.ai.tools import AgentTools
from app.ai.validation import PlanValidator
from app.config import Settings
from app.devices.factory import build_device
from app.devices.registry import DeviceRegistry
from app.domain.home_state import HomeState
from app.domain.intents import IntentResolver
from app.domain.policy import SecurityPolicy
from app.events.models import CommandSource
from app.events.store import InMemoryEventStore
from app.main import create_app
from app.ml.service import MLService, train_models
from app.sensors.simulated import SimulatedSensorProvider
from tests.ai_helpers import ScriptedProvider, SpyCommandService, action
from tests.conftest import SendCommand

FAN = "fan_living_room"
HOT = {"temperature_c": 30.4, "occupied": 1, "occupant_count": 2, "humidity_pct": 50, "hour": 15}


def ask(client: TestClient, message: str) -> dict:
    response = client.post("/api/v1/ai/command", json={"message": message})
    assert response.status_code == 200
    return response.json()


# --- Prediction API -----------------------------------------------------------------------


def test_ml_status_reports_models_metrics_and_simulated_data(client: TestClient) -> None:
    status = client.get("/api/v1/ml/status").json()

    assert status["enabled"] is True
    assert status["predictor"]["model"] == "random_forest_v1"
    assert status["detector"]["model"] == "isolation_forest_v1"
    assert status["predictor"]["metrics"]["accuracy"] > status["predictor"]["metrics"]["baseline_accuracy"]
    assert "simulated" in status["data_note"].lower()


def test_prediction_api_derives_features_from_home_state(client: TestClient) -> None:
    body = client.post("/api/v1/ml/predict", json={}).json()

    assert body["device_id"] == FAN
    assert 0 <= body["probability"] <= 1
    assert body["prediction"] in {"ON", "OFF"}
    assert body["model"] == "random_forest_v1"
    assert set(body["features"]) >= {"temperature_c", "occupied", "hour", "fan_on"}
    assert body["missing_features"] == []


def test_prediction_api_accepts_overrides_and_missing_values(client: TestClient) -> None:
    hot = client.post("/api/v1/ml/predict", json={"features": HOT}).json()
    missing = client.post("/api/v1/ml/predict", json={"features": {"temperature_c": None}}).json()

    assert hot["features"]["temperature_c"] == 30.4
    assert missing["missing_features"] == ["temperature_c"]


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"features": {"rain": 1}}, 422, "invalid_features"),
        ({"device_id": "light_living_room"}, 400, "prediction_not_supported"),
        ({"device_id": "fan_living_room", "extra": 1}, 422, "invalid_request"),
    ],
)
def test_prediction_api_rejects_bad_requests(client: TestClient, body, status, code) -> None:
    response = client.post("/api/v1/ml/predict", json=body)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


# --- Anomaly API and events ---------------------------------------------------------------------


def test_live_devices_are_normal_and_create_no_events(client: TestClient, send_command: SendCommand) -> None:
    send_command(FAN, "set_speed", value=60)

    report = client.get("/api/v1/ml/anomalies").json()

    assert report["active_count"] == 0
    assert all(not r["is_anomaly"] for r in report["live"])
    assert all(e["source"] != "ml" for e in client.get("/api/v1/events").json())


def test_normal_reading_is_not_an_anomaly(client: TestClient, send_command: SendCommand) -> None:
    send_command(FAN, "set_speed", value=60)

    result = client.post("/api/v1/ml/anomalies/check", json={"device_id": FAN, "power_w": 40.5}).json()

    assert result["is_anomaly"] is False
    assert result["event_id"] is None


def test_anomalous_reading_is_flagged_and_becomes_an_ml_event(client: TestClient, send_command: SendCommand) -> None:
    send_command(FAN, "set_speed", value=60)

    result = client.post("/api/v1/ml/anomalies/check", json={"device_id": FAN, "power_w": 170}).json()

    assert result["is_anomaly"] is True
    assert result["score"] < 0
    assert result["observed_power_watts"] == 170
    assert result["expected_range"]["max"] < 170
    assert "Isolation Forest" in result["explanation"]
    event = client.get("/api/v1/events").json()[0]
    assert (event["event_type"], event["source"], event["device_id"]) == ("energy_anomaly", "ml", FAN)
    assert event["event_id"] == result["event_id"]
    assert event["details"]["expected_range"] == result["expected_range"]
    assert event["previous_state"] == event["new_state"]  # an observation, not a command
    report = client.get("/api/v1/ml/anomalies").json()
    assert report["active_count"] == 1 and report["active"][0]["device_id"] == FAN


@pytest.mark.parametrize(
    ("body", "status"),
    [({"device_id": "toaster", "power_w": 10}, 404), ({"device_id": FAN, "power_w": -5}, 422), ({"device_id": FAN}, 422)],
)
def test_anomaly_check_validates_input(client: TestClient, body, status) -> None:
    assert client.post("/api/v1/ml/anomalies/check", json=body).status_code == status


def test_ml_cannot_issue_device_commands(send_command: SendCommand) -> None:
    response = send_command(FAN, "turn_on", source="ml")
    assert response.status_code == 422


def test_ml_endpoints_report_unavailable_when_disabled() -> None:
    with TestClient(create_app(Settings(_env_file=None, ml_enabled=False))) as client:
        assert client.get("/api/v1/ml/status").status_code == 503
        assert client.get("/api/v1/devices").status_code == 200  # device control unaffected
        body = ask(client, "Should I turn on the fan?")
        assert "not available" in body["reply"]


# --- AI integration ------------------------------------------------------------------------------


def test_ai_answers_prediction_questions_with_the_actual_ml_result(client: TestClient) -> None:
    body = ask(client, "Should I turn on the fan?")

    [result] = body["actions"]
    assert (result["intent"], result["status"], result["device_id"]) == ("GET_PREDICTIONS", "answered", FAN)
    prediction = result["data"]["predictions"][0]
    assert f"{round(prediction['probability'] * 100)}%" in body["reply"]  # quoted, not invented
    assert "Random Forest" in body["reply"]
    assert body["device_events"] == []  # a recommendation, not an action


def test_ai_explains_anomalies_from_the_actual_ml_result(client: TestClient, send_command: SendCommand) -> None:
    send_command(FAN, "set_speed", value=60)
    client.post("/api/v1/ml/anomalies/check", json={"device_id": FAN, "power_w": 170})

    body = ask(client, "Is there abnormal energy usage?")

    [result] = body["actions"]
    assert result["intent"] == "GET_ANOMALIES"
    anomaly = result["data"]["active"][0]
    assert f"{anomaly['observed_power_watts']:.1f} W" in body["reply"]
    assert f"{anomaly['expected_range']['min']:.1f}" in body["reply"]
    assert "Isolation Forest" in body["reply"]


def test_ai_reports_nothing_unusual_when_no_anomaly(client: TestClient) -> None:
    body = ask(client, "Is anything unusual?")
    assert "Nothing unusual" in body["reply"]
    assert body["actions"][0]["data"]["active_count"] == 0


def test_user_confirmed_recommendation_executes_through_command_service(client: TestClient) -> None:
    ask(client, "Should I turn on the fan?")

    body = ask(client, "turn it on")

    assert [(a["intent"], a["device_id"], a["status"]) for a in body["actions"]] == [("TURN_ON", FAN, "executed")]
    [event] = client.get("/api/v1/events").json()
    assert (event["source"], event["action"]) == ("ai_agent", "turn_on")


# --- Agent-level guarantees (no HTTP) -----------------------------------------------------------


@pytest.fixture
def harness():
    settings = Settings(_env_file=None)
    devices = DeviceRegistry(build_device(c) for c in settings.devices)
    home = HomeState(devices, SimulatedSensorProvider(seed=4))
    events = InMemoryEventStore()
    commands = SpyCommandService(home, events)
    ml = MLService(home, events, train_models(7, 60, 0.5))
    tools = AgentTools(home, events, commands, ml)

    def agent_with(plan):
        provider = ScriptedProvider(plan)
        agent = HomeAgent(
            provider, tools, PlanValidator(devices, IntentResolver(), SecurityPolicy()), InMemoryAgentHistory()
        )
        return agent, provider

    return {"home": home, "events": events, "commands": commands, "ml": ml, "tools": tools, "agent_with": agent_with}


@pytest.mark.anyio
async def test_get_predictions_and_get_anomalies_tools_return_ml_output(harness) -> None:
    predictions = harness["tools"].call_read_only("get_predictions", {})
    anomalies = harness["tools"].call_read_only("get_anomalies", {})

    assert predictions["available"] is True
    assert predictions["predictions"][0]["model"] == "random_forest_v1"
    assert 0 <= predictions["predictions"][0]["probability"] <= 1
    assert anomalies["available"] is True and anomalies["model"] == "isolation_forest_v1"
    assert len(anomalies["live"]) == 4


@pytest.mark.anyio
async def test_planner_context_tools_and_response_share_the_same_ml_numbers(harness) -> None:
    fabricated = {"message": "The fan is 99.9% likely to be needed.", "actions": [action(FAN, "GET_PREDICTIONS")]}
    agent, provider = harness["agent_with"](fabricated)

    response = await agent.handle("should I turn on the fan?")

    request = provider.requests[0]
    context_probability = request.context.ml.predictions[0].probability
    tool_probability = request.tools.call_read_only("get_predictions", {})["predictions"][0]["probability"]
    data_probability = response.actions[0].data["predictions"][0]["probability"]
    # Whatever the planner writes, the structured answer carries the real model output.
    assert context_probability == tool_probability == data_probability
    assert data_probability != 0.999


@pytest.mark.anyio
async def test_ml_recommendation_alone_never_calls_command_service(harness) -> None:
    prediction = harness["ml"].predict(overrides=HOT)
    assert prediction.prediction == "ON"
    agent, _ = harness["agent_with"]({"message": "Recommended.", "actions": [action(FAN, "GET_PREDICTIONS")]})

    await agent.handle("should I turn on the fan?")
    harness["ml"].anomaly_report()

    assert harness["commands"].calls == []
    assert harness["home"].devices.get(FAN).get_state()["is_on"] is False


@pytest.mark.anyio
async def test_explicit_turn_on_after_recommendation_goes_through_command_service(harness) -> None:
    agent, _ = harness["agent_with"]({"message": "Turning it on.", "actions": [action(FAN, "TURN_ON")]})

    await agent.handle("turn it on")

    assert [(c[0], c[1].action, c[2]) for c in harness["commands"].calls] == [(FAN, "turn_on", CommandSource.AI_AGENT)]
