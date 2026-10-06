"""MQTT configuration, topic contract and message schemas."""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.devices.types import DeviceDriver
from app.mqtt import topics
from app.mqtt.errors import MessageError
from app.mqtt.messages import (
    CommandMessage,
    EnergyMessage,
    SensorMessage,
    StateMessage,
    decode,
    decode_availability,
    encode,
)

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


# --- Configuration ----------------------------------------------------------------------------


def test_mqtt_is_off_by_default_and_every_device_is_virtual() -> None:
    settings = Settings(_env_file=None)
    assert settings.mqtt_enabled is False
    assert settings.sensor_source == "simulated"
    assert {d.driver for d in settings.devices} == {DeviceDriver.VIRTUAL}


def test_mqtt_settings_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {
        "SMARTHOME_MQTT_ENABLED": "true",
        "SMARTHOME_MQTT_HOST": "broker.lan",
        "SMARTHOME_MQTT_PORT": "8883",
        "SMARTHOME_MQTT_USERNAME": "hub",
        "SMARTHOME_MQTT_PASSWORD": "s3cret",
        "SMARTHOME_MQTT_CLIENT_ID": "hub-1",
        "SMARTHOME_MQTT_COMMAND_TIMEOUT_S": "2.5",
        "SMARTHOME_SENSOR_MAX_AGE_S": "45",
        "SMARTHOME_MQTT_DEVICES": '["fan_living_room"]',
        "SMARTHOME_SENSOR_SOURCE": "mqtt",
    }.items():
        monkeypatch.setenv(name, value)

    settings = Settings(_env_file=None)

    assert (settings.mqtt_host, settings.mqtt_port, settings.mqtt_client_id) == ("broker.lan", 8883, "hub-1")
    assert (settings.mqtt_command_timeout_s, settings.sensor_max_age_s) == (2.5, 45)
    drivers = {d.id: d.driver for d in settings.devices}
    assert drivers["fan_living_room"] is DeviceDriver.ESP32_MQTT
    assert drivers["light_living_room"] is DeviceDriver.VIRTUAL  # virtual and hardware side by side
    # The password is never shown, even in a repr or log line.
    assert "s3cret" not in repr(settings) and "s3cret" not in str(settings.model_dump())


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"mqtt_devices": ["fan_living_room"]}, "SMARTHOME_MQTT_ENABLED is false"),
        ({"sensor_source": "mqtt"}, "SMARTHOME_MQTT_ENABLED is false"),
        ({"mqtt_enabled": True, "mqtt_devices": ["toaster"]}, "unknown devices"),
        ({"mqtt_command_timeout_s": 120}, "less than or equal to 30"),  # no silently huge timeouts
    ],
)
def test_contradictory_or_unsafe_configuration_is_refused(overrides: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(_env_file=None, **overrides)


def test_device_ids_cannot_collide_with_reserved_topic_segments() -> None:
    with pytest.raises(ValidationError, match="reserved"):
        Settings(_env_file=None, devices=[{"id": "sensors", "name": "X", "type": "light", "room": "r"}])


# --- Topics -----------------------------------------------------------------------------------


def test_topic_contract() -> None:
    assert topics.device_set("light_living_room") == "home/light_living_room/set"
    assert topics.device_state("fan_living_room") == "home/fan_living_room/state"
    assert topics.device_availability("door_main") == "home/door_main/availability"
    assert [topics.sensor(k) for k in topics.SENSOR_KINDS] == [
        "home/sensors/temperature",
        "home/sensors/humidity",
        "home/sensors/occupancy",
        "home/sensors/ambient_light",
    ]
    assert topics.energy("fan_living_room") == "home/energy/fan_living_room"
    assert topics.backend_availability() == "home/backend/availability"


@pytest.mark.parametrize("bad", ["Fan", "fan/+", "fan#", "", "sensors", "energy", "backend"])
def test_topics_refuse_ids_that_would_break_the_contract(bad: str) -> None:
    with pytest.raises(ValueError):
        topics.device_set(bad)


@pytest.mark.parametrize(
    ("topic", "expected"),
    [
        ("home/fan_living_room/state", topics.Topic("state", "fan_living_room")),
        ("home/fan_living_room/availability", topics.Topic("availability", "fan_living_room")),
        ("home/sensors/humidity", topics.Topic("sensor", "humidity")),
        ("home/sensors/availability", topics.Topic("sensors_availability", "sensors")),
        ("home/energy/ac_bedroom", topics.Topic("energy", "ac_bedroom")),
        ("home/sensors/pressure", None),
        ("home/backend/availability", None),
        ("home/fan_living_room/state/extra", None),
        ("other/fan/state", None),
    ],
)
def test_topic_parsing(topic: str, expected: topics.Topic | None) -> None:
    assert topics.parse(topic) == expected


# --- Messages -----------------------------------------------------------------------------------


def test_command_serialisation_matches_the_contract() -> None:
    message = CommandMessage.create("fan_living_room", "set_speed", {"value": 70}, ttl_s=3, now=NOW)

    data = json.loads(encode(message))

    assert data == {
        "command_id": message.command_id,
        "device_id": "fan_living_room",
        "action": "set_speed",
        "parameters": {"value": 70},
        "issued_at": "2026-10-06T12:00:00Z",
        "expires_at": "2026-10-06T12:00:03Z",
    }
    UUID(data["command_id"])  # a real UUID


def test_command_ids_are_unique() -> None:
    ids = {CommandMessage.create("light_living_room", "turn_on", {}, ttl_s=3).command_id for _ in range(500)}
    assert len(ids) == 500


def test_state_acknowledgement_deserialisation() -> None:
    payload = json.dumps(
        {
            "device_id": "fan_living_room",
            "command_id": "6f1c3a52-0d5e-4b2f-9b8a-1f0e2d3c4b5a",
            "timestamp": "2026-10-06T12:00:00.250Z",
            "state": {"is_on": True, "speed": 70},
        }
    )
    message = decode(StateMessage, payload)
    assert message.state == {"is_on": True, "speed": 70}
    assert message.timestamp == NOW + timedelta(milliseconds=250)


@pytest.mark.parametrize(
    "payload",
    [
        b"{not json",
        b"\xff\xfe",
        b"[]",
        b'{"device_id": "fan_living_room", "timestamp": "2026-10-06T12:00:00Z"}',  # no state
        b'{"device_id": "fan_living_room", "timestamp": "2026-10-06T12:00:00", "state": {}}',  # no timezone
        b'{"device_id": "fan_living_room", "timestamp": "yesterday", "state": {}}',
        b'{"device_id": "fan_living_room", "command_id": "ABC", "timestamp": "2026-10-06T12:00:00Z", "state": {}}',
        b'{"device_id": "Fan!", "timestamp": "2026-10-06T12:00:00Z", "state": {}}',
        b'{"device_id": "fan_living_room", "timestamp": "2026-10-06T12:00:00Z", "state": {}, "extra": 1}',
    ],
)
def test_malformed_state_messages_raise_message_error(payload: bytes) -> None:
    with pytest.raises(MessageError):
        decode(StateMessage, payload)


@pytest.mark.parametrize("value", ["NaN", "Infinity", '"warm"'])
def test_sensor_values_must_be_finite_numbers(value: str) -> None:
    payload = f'{{"sensor_id": "dht22_1", "timestamp": "2026-10-06T12:00:00Z", "value": {value}}}'
    with pytest.raises(MessageError):
        decode(SensorMessage, payload)


def test_energy_and_availability_messages() -> None:
    assert decode(EnergyMessage, b'{"timestamp": "2026-10-06T12:00:00Z", "power_w": 41.2}').power_w == 41.2
    with pytest.raises(MessageError):
        decode(EnergyMessage, b'{"timestamp": "2026-10-06T12:00:00Z", "power_w": -1}')
    assert decode_availability(b" ONLINE\n") == "online"
    with pytest.raises(MessageError):
        decode_availability(b"maybe")
