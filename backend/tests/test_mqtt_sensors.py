"""MQTT sensor readings: validation, freshness, and what HomeState / AI / ML do with them."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.mqtt import topics
from app.sensors.base import SensorError
from app.sensors.mqtt import MQTTSensorProvider
from tests.mqtt_helpers import Rig, settle

pytestmark = pytest.mark.anyio

T0 = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
GOOD = {"temperature": 29.4, "humidity": 61.0, "occupancy": 2, "ambient_light": 320.0}


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now


def message(value, *, at: datetime = T0, sensor_id: str = "dht22_1") -> bytes:
    return json.dumps({"sensor_id": sensor_id, "timestamp": at.isoformat(), "value": value}).encode()


def provider(**readings) -> tuple[MQTTSensorProvider, Clock]:
    clock = Clock()
    sensors = MQTTSensorProvider(max_age_s=30, clock=clock)
    for kind, value in {**GOOD, **readings}.items():
        sensors.handle(kind, message(value))
    return sensors, clock


def test_valid_readings_become_the_environment() -> None:
    sensors, _ = provider()
    readings = sensors.read()
    assert (readings.temperature_c, readings.humidity_pct, readings.ambient_light_lux) == (29.4, 61.0, 320.0)
    assert (readings.occupancy.occupied, readings.occupancy.occupant_count) == (True, 2)
    status = sensors.status()["temperature"]
    assert (status["status"], status["sensor_id"], status["value"]) == ("ok", "dht22_1", 29.4)


def test_stale_readings_are_unavailable_not_current() -> None:
    sensors, clock = provider()
    clock.now = T0 + timedelta(seconds=31)

    with pytest.raises(SensorError, match=r"temperature is stale \(31 s old, limit 30 s\)"):
        sensors.read()
    assert sensors.status()["humidity"]["status"] == "stale"
    assert sensors.status()["humidity"]["value"] is None  # the stale value is not offered as current


def test_one_stale_sensor_makes_the_environment_unavailable() -> None:
    sensors, clock = provider()
    clock.now = T0 + timedelta(seconds=20)
    for kind in ("temperature", "humidity", "ambient_light"):
        sensors.handle(kind, message(GOOD[kind], at=clock.now))
    clock.now = T0 + timedelta(seconds=40)  # occupancy (from T0) is now 40 s old

    with pytest.raises(SensorError, match="occupancy is stale"):
        sensors.read()


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("temperature", -1000),
        ("temperature", 85.1),
        ("humidity", 500),
        ("humidity", -1),
        ("ambient_light", -5),
        ("ambient_light", 250_000),
        ("occupancy", 1.5),
        ("occupancy", -1),
    ],
)
def test_implausible_values_are_rejected(kind: str, value: float) -> None:
    sensors, _ = provider(**{kind: value})

    with pytest.raises(SensorError, match=f"{kind} rejected"):
        sensors.read()
    assert sensors.status()[kind]["status"] == "invalid"


@pytest.mark.parametrize(
    "payload",
    [
        message(29.0, at=T0 + timedelta(minutes=5)),  # timestamp in the future
        b'{"sensor_id": "dht22_1", "timestamp": "2026-10-06T12:00:00", "value": 29}',  # no timezone
        b'{"sensor_id": "dht22_1", "timestamp": "noon", "value": 29}',
        b'{"sensor_id": "dht22_1", "value": 29}',  # no timestamp
        b'{"sensor_id": "dht22_1", "timestamp": "2026-10-06T12:00:00Z", "value": NaN}',
        b"not json",
    ],
)
def test_invalid_timestamps_and_malformed_messages_are_rejected(payload: bytes) -> None:
    sensors, _ = provider()
    sensors.handle("temperature", payload)

    with pytest.raises(SensorError, match="temperature rejected"):
        sensors.read()


def test_a_valid_reading_clears_a_rejection() -> None:
    sensors, _ = provider(temperature=-1000)
    sensors.handle("temperature", message(25.0))
    assert sensors.read().temperature_c == 25.0


def test_missing_sensors_and_an_offline_board_are_reported() -> None:
    sensors = MQTTSensorProvider(max_age_s=30, clock=Clock())
    with pytest.raises(SensorError, match="temperature has not reported"):
        sensors.read()

    sensors, _ = provider()
    sensors.set_board_online(False)  # the board's Last Will
    with pytest.raises(SensorError, match="sensor board is offline"):
        sensors.read()


# --- Through the backend: HomeState, AI and ML ------------------------------------------------------


def publish_all(rig: Rig, *, at: datetime, **overrides) -> None:
    probe = rig.broker.client("sensor-board")
    probe.start()
    for kind, value in {**GOOD, **overrides}.items():
        probe.publish(topics.sensor(kind), message(value, at=at))


async def test_mqtt_sensor_messages_reach_home_state_and_ml() -> None:
    rig = await Rig(sensor_source="mqtt", mqtt_devices=[]).start()
    publish_all(rig, at=datetime.now(UTC))
    await settle()

    snapshot = rig.container.home_state.snapshot()
    prediction = rig.container.ml_service.predict()

    assert snapshot.environment is not None and snapshot.environment.temperature_c == 29.4
    assert prediction.features["temperature_c"] == 29.4  # ML uses the MQTT reading
    assert prediction.reliable is True


async def test_stale_mqtt_sensors_are_not_used_by_ai_or_ml_as_current() -> None:
    rig = await Rig(sensor_source="mqtt", mqtt_devices=[], sensor_max_age_s=5).start()
    publish_all(rig, at=datetime.now(UTC) - timedelta(seconds=60))  # a minute old
    await settle()

    snapshot = rig.container.home_state.snapshot()
    prediction = rig.container.ml_service.predict()
    reply = (await rig.container.agent.handle("what's happening in my house?")).reply

    assert snapshot.environment is None
    assert "stale" in snapshot.sensor_error
    assert prediction.reliable is False and "temperature_c" in prediction.missing_features
    assert "Sensor readings are unavailable" in reply and "29.4" not in reply
