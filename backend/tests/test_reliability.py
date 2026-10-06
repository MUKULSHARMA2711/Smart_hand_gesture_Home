"""Day 6 hardening: error contract, failure isolation, sensor validation, races, event integrity."""

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.ai.errors import AIUnavailableError
from app.config import Settings
from app.container import build_container
from app.devices.commands import DeviceCommand
from app.domain.home_state import HomeState
from app.events.models import CommandSource
from app.main import create_app
from app.sensors.base import SensorError, SensorProvider, SensorReadings
from app.sensors.simulated import SimulatedSensorProvider
from tests.ai_helpers import ScriptedProvider

API = "/api/v1"
FAN, LIGHT, DOOR = "fan_living_room", "light_living_room", "door_main"
VALID_READING = {
    "temperature_c": 24.0,
    "humidity_pct": 50.0,
    "occupancy": {"occupied": True, "occupant_count": 2},
    "ambient_light_lux": 300.0,
}


def device_states(client: TestClient) -> dict[str, dict]:
    return {d["id"]: d["state"] for d in client.get(f"{API}/devices").json()}


@pytest.fixture
def lenient_client() -> Iterator[TestClient]:
    """Returns 500 responses instead of re-raising, like a real server."""
    with TestClient(create_app(Settings(_env_file=None, sensor_seed=3)), raise_server_exceptions=False) as client:
        yield client


# --- Backend error contract ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "status", "code"),
    [("get", "/nope", 404, "not_found"), ("delete", "/devices", 405, "method_not_allowed")],
)
def test_framework_errors_use_the_error_envelope(
    client: TestClient, method: str, path: str, status: int, code: str
) -> None:
    # Regression: these returned FastAPI's {"detail": ...} instead of the error envelope.
    response = getattr(client, method)(API + path)

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert path in response.json()["error"]["message"]


def test_unexpected_errors_return_a_safe_500_envelope(
    lenient_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = lenient_client.app.state.container.home_state

    def explode():
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(home, "snapshot", explode)
    response = lenient_client.get(f"{API}/home/state")

    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "An unexpected server error occurred.", "details": None}}
    assert "secret" not in response.text
    # Unrelated endpoints keep working.
    assert lenient_client.post(f"{API}/devices/{LIGHT}/command", json={"action": "turn_on"}).status_code == 200


# --- Device command safety -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("device_id", "body", "status", "code"),
    [
        (LIGHT, {"action": "explode"}, 400, "unsupported_command"),  # invalid action
        (LIGHT, {"action": "set_brightness", "value": 150}, 422, "invalid_command"),  # out of range
        (LIGHT, {"action": "set_brightness", "value": True}, 422, "invalid_command"),  # bool is not a number
        (LIGHT, {"action": "set_brightness", "value": "70"}, 422, "invalid_command"),  # no string coercion
        ("toaster", {"action": "turn_on"}, 404, "device_not_found"),  # unknown device
        (DOOR, {"action": "turn_on"}, 400, "unsupported_command"),  # impossible capability
        (LIGHT, {"action": "turn_on", "extra": 1}, 422, "invalid_request"),  # malformed request
    ],
)
def test_failed_commands_never_mutate_state_or_log_events(
    client: TestClient, device_id: str, body: dict, status: int, code: str
) -> None:
    before = device_states(client)

    response = client.post(f"{API}/devices/{device_id}/command", json=body)

    assert (response.status_code, response.json()["error"]["code"]) == (status, code)
    assert device_states(client) == before
    assert client.get(f"{API}/events").json() == []


def test_repeated_identical_command_is_consistent(client: TestClient) -> None:
    for _ in range(2):
        assert client.post(f"{API}/devices/{FAN}/command", json={"action": "turn_on"}).status_code == 200

    second, first = client.get(f"{API}/events").json()
    assert first["previous_state"]["is_on"] is False and first["new_state"]["is_on"] is True
    assert second["previous_state"] == second["new_state"] == first["new_state"]  # a no-op, recorded honestly


@pytest.mark.anyio
async def test_concurrent_commands_on_one_device_are_serialised() -> None:
    container = build_container(Settings(_env_file=None, virtual_device_latency_ms=20))
    commands = container.command_service

    await asyncio.gather(
        *(commands.execute(FAN, DeviceCommand(action="set_speed", value=v), CommandSource.FRONTEND) for v in (30, 70, 50))
    )

    events = list(reversed(container.event_store.recent()))  # oldest first
    for earlier, later in zip(events, events[1:]):
        assert later.previous_state == earlier.new_state  # no interleaving
    assert container.home_state.devices.get(FAN).get_state() == events[-1].new_state


# --- AI failure handling -------------------------------------------------------------------------


class HangingProvider(ScriptedProvider):
    async def plan(self, request):
        await asyncio.sleep(10)


class BuggyProvider(ScriptedProvider):
    async def plan(self, request):
        raise KeyError("unexpected")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("provider", "reason"),
    [(HangingProvider(), "did not respond within 0.05 s"), (BuggyProvider(), "failed unexpectedly (KeyError)")],
)
async def test_hung_or_buggy_providers_become_ai_unavailable(provider, reason: str) -> None:
    container = build_container(Settings(_env_file=None, ai_request_timeout_s=0.05), ai_provider=provider)

    with pytest.raises(AIUnavailableError) as raised:
        await container.agent.handle("turn on the fan")

    assert reason in raised.value.details["reason"]
    assert container.event_store.recent() == []


def test_ai_outage_leaves_the_rest_of_the_system_usable() -> None:
    app = create_app(Settings(_env_file=None), ai_provider=ScriptedProvider(error="provider down"))
    with TestClient(app) as client:
        assert client.post(f"{API}/ai/command", json={"message": "turn on the fan"}).status_code == 503

        assert client.get(f"{API}/home/state").status_code == 200
        assert client.post(f"{API}/devices/{FAN}/command", json={"action": "turn_on"}).status_code == 200
        gesture = {"gesture": "THUMBS_UP", "intent": "TURN_ON", "confidence": 0.95, "target_device_id": LIGHT}
        assert client.post(f"{API}/gestures/commands", json=gesture).status_code == 200
        assert [e["source"] for e in client.get(f"{API}/events").json()] == ["gesture", "frontend"]
        # The failed attempt is visible in the assistant history.
        assert client.get(f"{API}/ai/history").json()[0]["errors"] == ["provider down"]


@pytest.mark.anyio
async def test_partial_plan_reports_an_unexpected_device_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    plan = {
        "message": "On it.",
        "actions": [
            {"device_id": LIGHT, "intent": "TURN_ON", "parameters": {}},
            {"device_id": FAN, "intent": "TURN_ON", "parameters": {}},
        ],
    }
    container = build_container(Settings(_env_file=None), ai_provider=ScriptedProvider(plan))
    fan = container.home_state.devices.get(FAN)

    async def broken(command):
        raise ConnectionError("firmware did not answer")

    monkeypatch.setattr(fan, "execute_command", broken)
    response = await container.agent.handle("turn on the light and the fan")

    assert [(a.device_id, a.status, a.code) for a in response.actions] == [
        (LIGHT, "executed", None),
        (FAN, "failed", "internal_error"),
    ]
    assert [e.device_id for e in container.event_store.recent()] == [LIGHT]  # no fake success for the fan
    assert fan.get_state()["is_on"] is False


@pytest.mark.anyio
async def test_identical_ai_requests_in_quick_succession_stay_consistent() -> None:
    container = build_container(Settings(_env_file=None, virtual_device_latency_ms=20))

    first, second = await asyncio.gather(*(container.agent.handle("Turn on the fan.") for _ in range(2)))

    events = list(reversed(container.event_store.recent()))
    assert [(e.device_id, e.source) for e in events] == [(FAN, "ai_agent"), (FAN, "ai_agent")]
    assert events[1].previous_state == events[0].new_state
    # Exactly one request actually changed the fan; both report what really happened.
    assert sorted([first.changed_devices, second.changed_devices]) == [[], [FAN]]
    assert container.home_state.devices.get(FAN).get_state()["is_on"] is True


# --- Sensor validation ---------------------------------------------------------------------------


class FixedSensors(SensorProvider):
    """Parses a raw payload the way a hardware (MQTT) sensor provider would."""

    def __init__(self, payload: dict | Exception) -> None:
        self.payload = payload

    def read(self) -> SensorReadings:
        if isinstance(self.payload, Exception):
            raise self.payload
        return SensorReadings.model_validate(self.payload)


@pytest.mark.parametrize(
    "payload",
    [
        {**VALID_READING, "temperature_c": -1000},
        {**VALID_READING, "humidity_pct": 500},
        {**VALID_READING, "ambient_light_lux": -5},
        {**VALID_READING, "temperature_c": float("nan")},
        {**VALID_READING, "occupancy": {"occupied": "maybe", "occupant_count": 1}},
        {**VALID_READING, "occupancy": {"occupied": False, "occupant_count": 3}},  # contradictory
        SensorError("DHT22 offline"),
    ],
)
def test_implausible_or_missing_sensor_data_is_reported_not_used(client: TestClient, payload) -> None:
    client.app.state.container.home_state._sensors = FixedSensors(payload)

    state = client.get(f"{API}/home/state")
    prediction = client.post(f"{API}/ml/predict", json={}).json()
    answer = client.post(f"{API}/ai/command", json={"message": "what's happening in my house?"}).json()

    assert state.status_code == 200
    assert state.json()["environment"] is None and state.json()["sensor_error"]
    # ML still answers, but flags that sensor inputs were imputed instead of trusting them.
    assert prediction["reliable"] is False
    assert {"temperature_c", "humidity_pct", "occupied"} <= set(prediction["missing_features"])
    assert "Low confidence" in prediction["explanation"]
    assert "Sensor readings are unavailable" in answer["reply"]
    assert "humidity" not in answer["reply"] and "lux" not in answer["reply"]  # nothing invented
    assert client.post(f"{API}/devices/{LIGHT}/command", json={"action": "turn_on"}).status_code == 200


def test_sensors_recover_after_a_fault() -> None:
    sensors = FixedSensors(SensorError("offline"))
    home = HomeState(build_container(Settings(_env_file=None)).home_state.devices, sensors)

    assert home.snapshot().environment is None
    sensors.payload = VALID_READING
    snapshot = home.snapshot()
    assert snapshot.environment is not None and snapshot.sensor_error is None


def test_simulated_sensors_stay_within_validated_bounds() -> None:
    sensors = SimulatedSensorProvider(seed=0)
    for _ in range(500):
        sensors.read()  # raises if the simulator ever produced an implausible reading


# --- ML robustness -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "features",
    [
        {"temperature_c": -1000},
        {"humidity_pct": 500},
        {"ambient_light_lux": -1},
        {"occupied": 0.5},
        {"hour": 30},
    ],
)
def test_prediction_rejects_implausible_feature_values(client: TestClient, features: dict) -> None:
    # Regression: temperature_c=-1000 used to return a confident prediction.
    response = client.post(f"{API}/ml/predict", json={"features": features})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_features"
    assert error["details"]["errors"][0]["feature"] == next(iter(features))


def test_prediction_rejects_non_finite_values(client: TestClient) -> None:
    # Regression: Infinity reached scikit-learn and leaked its internal error message.
    response = client.post(
        f"{API}/ml/predict",
        content=b'{"features": {"temperature_c": Infinity}}',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["errors"] == [{"feature": "temperature_c", "message": "Must be a finite number."}]


def test_model_failure_at_runtime_is_isolated(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    models = client.app.state.container.ml_service._models

    def broken(*args, **kwargs):
        raise RuntimeError("model file corrupted")

    monkeypatch.setattr(models.predictor, "predict", broken)
    monkeypatch.setattr(models.detector, "assess", broken)

    for response in (client.post(f"{API}/ml/predict", json={}), client.get(f"{API}/ml/anomalies")):
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "ml_unavailable"
        assert "corrupted" not in response.text
    # The AI agent still handles ordinary commands, without ML context.
    body = client.post(f"{API}/ai/command", json={"message": "turn on the light"}).json()
    assert [(a["intent"], a["status"]) for a in body["actions"]] == [("TURN_ON", "executed")]
    assert client.get(f"{API}/home/state").status_code == 200


def test_ml_training_failure_does_not_take_down_the_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise MemoryError("training failed")

    monkeypatch.setattr("app.container.train_models", fail)
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get(f"{API}/ml/status").json()["error"]["code"] == "ml_unavailable"
        assert client.get(f"{API}/home/state").status_code == 200
        assert client.post(f"{API}/devices/{FAN}/command", json={"action": "turn_on"}).status_code == 200
        body = client.post(f"{API}/ai/command", json={"message": "Should I turn on the fan?"})
        assert body.status_code == 200
        assert "%" not in body.json()["reply"]  # no ML numbers without ML


# --- Event semantics ------------------------------------------------------------------------------


def test_each_source_produces_exactly_the_events_that_happened(client: TestClient) -> None:
    gesture = {"gesture": "THUMBS_UP", "intent": "TURN_ON", "target_device_id": LIGHT}
    # Rejected attempts: none of these may create a device event.
    assert client.post(f"{API}/gestures/commands", json={**gesture, "confidence": 0.3}).status_code == 422
    assert client.post(f"{API}/devices/{DOOR}/command", json={"action": "turn_on"}).status_code == 400
    client.post(f"{API}/ai/command", json={"message": "don't unlock the door"})
    assert client.get(f"{API}/events").json() == []

    # Successful ones: exactly one event each, attributed to the real source.
    client.post(f"{API}/devices/{FAN}/command", json={"action": "turn_on"})
    client.post(f"{API}/gestures/commands", json={**gesture, "confidence": 0.95})
    client.post(f"{API}/ai/command", json={"message": "unlock the front door"})
    client.post(f"{API}/ml/anomalies/check", json={"device_id": FAN, "power_w": 400})

    events = list(reversed(client.get(f"{API}/events").json()))
    assert [(e["source"], e["device_id"], e["event_type"]) for e in events] == [
        ("frontend", FAN, "device_command"),
        ("gesture", LIGHT, "device_command"),
        ("ai_agent", DOOR, "device_command"),
        ("ml", FAN, "energy_anomaly"),
    ]
    assert events[-1]["previous_state"] == events[-1]["new_state"]  # an observation, not a state change
