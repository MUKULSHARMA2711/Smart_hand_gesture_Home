"""FakeESP32 scenarios against the real backend stack (CommandService → ESP32MQTTDevice → MQTT)."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.devices.types import DeviceStatus, DeviceType
from app.domain.errors import DeviceTimeoutError, DeviceUnavailableError
from app.mqtt import topics
from app.mqtt.messages import CommandMessage, encode
from simulation.mqtt_esp32 import FakeESP32, FakeSensorBoard
from simulation.scenarios import Scenario, ScenarioRequest, SensorScenario, control_topic
from tests.mqtt_helpers import FAN, Rig, settle

pytestmark = pytest.mark.anyio


async def stack(scenario: Scenario = Scenario.NORMAL, *, timeout_s: float = 0.4, **fake_options) -> tuple[Rig, FakeESP32]:
    rig = await Rig(mqtt_devices=[FAN], mqtt_command_timeout_s=timeout_s).start()
    fake = FakeESP32(FAN, DeviceType.FAN, board_factory(rig), scenario=scenario, **fake_options)
    await fake.start()
    await settle()
    return rig, fake


def board_factory(rig: Rig):
    return lambda client_id, will: rig.broker.client(client_id, will=will)


async def test_normal_firmware_boots_and_acknowledges_commands() -> None:
    rig, fake = await stack()
    fan = rig.device(FAN)
    assert fan.status is DeviceStatus.ONLINE  # availability "online" on connect
    assert fan.last_confirmed_at is not None  # retained boot state adopted

    event = await rig.command(FAN, "set_speed", 70)

    assert event.new_state == {"is_on": True, "speed": 70} == fake.state.model_dump()  # backend == "hardware"
    assert event.details["transport"] == "mqtt"


async def test_delay_scenario_is_pending_then_succeeds() -> None:
    rig, fake = await stack(Scenario.DELAY, delay_s=0.2, timeout_s=0.6)

    task = asyncio.create_task(rig.command(FAN, "turn_on"))
    await asyncio.sleep(0.1)
    assert not task.done() and rig.device(FAN).get_state()["is_on"] is False
    event = await task
    assert event.new_state["is_on"] is True and event.details["ack_latency_ms"] >= 150  # ~200 ms; coarse timers


@pytest.mark.parametrize("scenario", [Scenario.NO_ACK, Scenario.WRONG_COMMAND_ID, Scenario.WRONG_STATE, Scenario.MALFORMED_ACK])
async def test_bad_acknowledgements_time_out_without_faking_state(scenario: Scenario) -> None:
    rig, fake = await stack(scenario)

    with pytest.raises(DeviceTimeoutError):
        await rig.command(FAN, "turn_on")

    assert rig.device(FAN).get_state()["is_on"] is False  # confirmed state untouched
    assert rig.events("device_command") == []


async def test_duplicate_acknowledgements_produce_one_event() -> None:
    rig, fake = await stack(Scenario.DUPLICATE_ACK)
    await rig.command(FAN, "turn_on")
    await settle()
    assert len(rig.events("device_command")) == 1 and rig.events("state_report") == []


async def test_offline_scenario_fails_fast_and_executes_nothing() -> None:
    rig, fake = await stack()
    fake.set_scenario(Scenario.OFFLINE)
    await settle()

    with pytest.raises(DeviceUnavailableError, match="Living Room Fan is offline."):
        await rig.command(FAN, "turn_on")
    assert rig.device(FAN).status is DeviceStatus.OFFLINE
    assert fake.commands_received == [] and fake.state.is_on is False


async def test_power_cut_triggers_the_last_will() -> None:
    rig, fake = await stack()
    fake.crash()
    await settle()
    assert rig.device(FAN).status is DeviceStatus.OFFLINE


async def test_reconnect_scenario_goes_offline_then_comes_back() -> None:
    rig, fake = await stack(reconnect_after_s=0.15)
    fake.set_scenario(Scenario.RECONNECT)
    await asyncio.sleep(0.05)
    assert rig.device(FAN).status is DeviceStatus.OFFLINE

    await asyncio.sleep(0.25)
    assert rig.device(FAN).status is DeviceStatus.ONLINE
    assert (await rig.command(FAN, "turn_on")).new_state["is_on"] is True


async def test_scenarios_can_be_switched_over_mqtt() -> None:
    rig, fake = await stack()
    controller = rig.broker.client("controller")
    controller.start()

    controller.publish(control_topic(FAN), ScenarioRequest("delay", delay_s=0.05).encode())
    await settle()
    assert (fake.scenario, fake.delay_s) == (Scenario.DELAY, 0.05)


async def test_firmware_drops_expired_and_foreign_commands() -> None:
    rig, fake = await stack()
    sender = rig.broker.client("sender")
    sender.start()
    expired = CommandMessage.create(FAN, "turn_on", {}, ttl_s=1, now=datetime.now(UTC) - timedelta(minutes=1))
    foreign = CommandMessage.create("light_living_room", "turn_on", {}, ttl_s=5)

    sender.publish(topics.device_set(FAN), encode(expired))
    sender.publish(topics.device_set(FAN), encode(foreign))
    sender.publish(topics.device_set(FAN), b'{"action": "explode"}')
    await settle()

    assert fake.commands_received == [] and fake.state.is_on is False


# --- Sensor board -----------------------------------------------------------------------------------


async def sensor_stack(**overrides) -> tuple[Rig, FakeSensorBoard]:
    rig = await Rig(mqtt_devices=[], sensor_source="mqtt", **overrides).start()
    board = FakeSensorBoard(board_factory(rig), interval_s=3600)
    await board.start()
    await settle()
    return rig, board


async def test_sensor_board_publishes_realistic_readings() -> None:
    rig, board = await sensor_stack()
    environment = rig.container.home_state.snapshot().environment
    assert environment is not None
    assert -40 <= environment.temperature_c <= 85 and 0 <= environment.humidity_pct <= 100


@pytest.mark.parametrize(
    ("scenario", "error"),
    [(SensorScenario.INVALID, "temperature rejected"), (SensorScenario.OFFLINE, "sensor board is offline")],
)
async def test_sensor_board_failures_make_the_environment_unavailable(scenario: SensorScenario, error: str) -> None:
    rig, board = await sensor_stack()
    board.set_scenario(scenario)
    board.publish_once()
    await settle()

    snapshot = rig.container.home_state.snapshot()
    assert snapshot.environment is None and error in snapshot.sensor_error


async def test_stale_sensor_board_ages_out() -> None:
    rig, board = await sensor_stack(sensor_max_age_s=0.2)
    board.set_scenario(SensorScenario.STALE)  # stops publishing
    await asyncio.sleep(0.3)

    snapshot = rig.container.home_state.snapshot()
    assert snapshot.environment is None and "stale" in snapshot.sensor_error
