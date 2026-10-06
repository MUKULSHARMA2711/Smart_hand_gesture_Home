"""ESP32MQTTDevice: acknowledgements, timeouts, availability and concurrency, over a real
CommandService and an in-memory broker. A Probe plays the firmware by hand."""

import asyncio
import time

import pytest

from app.devices.types import DeviceStatus
from app.domain.errors import DeviceStateMismatchError, DeviceTimeoutError, DeviceUnavailableError
from app.events.models import CommandSource
from app.mqtt import topics
from tests.mqtt_helpers import DOOR, FAN, LIGHT, Probe, Rig, settle

pytestmark = pytest.mark.anyio

FAN_OFF = {"is_on": False, "speed": 50}
FAN_70 = {"is_on": True, "speed": 70}


async def ready(state: dict = FAN_OFF, device_id: str = FAN, **overrides) -> tuple[Rig, Probe]:
    rig = await Rig(**overrides).start()
    probe = Probe(rig.broker, device_id)
    probe.online()
    probe.state(state)  # retained boot report
    await settle()
    return rig, probe


# --- Success path -------------------------------------------------------------------------------


async def test_command_succeeds_only_after_a_matching_acknowledgement() -> None:
    rig, probe = await ready()
    fan = rig.device(FAN)

    task = asyncio.create_task(rig.command(FAN, "set_speed", 70, source=CommandSource.GESTURE))
    command = await probe.next_command()

    # Published, but nothing is confirmed yet: no state change, no event.
    assert (command.device_id, command.action, command.parameters) == (FAN, "set_speed", {"value": 70})
    assert fan.get_state() == FAN_OFF
    assert rig.events("device_command") == []

    probe.state(FAN_70, command.command_id)
    event = await task

    assert fan.get_state() == FAN_70
    assert fan.last_confirmed_at is not None
    assert (event.source, event.previous_state, event.new_state) == ("gesture", FAN_OFF, FAN_70)  # real actor, not mqtt
    assert event.details["transport"] == "mqtt"
    assert event.details["command_id"] == command.command_id
    assert event.details["ack_latency_ms"] >= 0
    assert [e.event_id for e in rig.events("device_command")] == [event.event_id]


async def test_delayed_acknowledgement_within_the_timeout_succeeds() -> None:
    rig, probe = await ready(mqtt_command_timeout_s=0.5)

    task = asyncio.create_task(rig.command(FAN, "turn_on"))
    command = await probe.next_command()
    await asyncio.sleep(0.25)  # pending meanwhile
    assert not task.done() and rig.device(FAN).get_state() == FAN_OFF
    probe.state({"is_on": True, "speed": 50}, command.command_id)

    event = await task
    assert event.new_state["is_on"] is True
    assert event.details["ack_latency_ms"] >= 200  # the real wait, not 0 (Windows timers are coarse)


async def test_duplicate_acknowledgements_are_ignored() -> None:
    rig, probe = await ready()
    task = asyncio.create_task(rig.command(FAN, "set_speed", 70))
    command = await probe.next_command()

    for _ in range(3):
        probe.state(FAN_70, command.command_id)
    await task
    await settle()

    assert len(rig.events("device_command")) == 1
    assert rig.events("state_report") == []


# --- Failures never change confirmed state or create success events -------------------------------


async def expect_timeout(rig: Rig, respond) -> None:
    """Send turn_on, let `respond(command)` misbehave, and check nothing was faked."""
    fan = rig.device(FAN)
    task = asyncio.create_task(rig.command(FAN, "turn_on"))
    probe_command = await rig.probe.next_command()
    respond(probe_command)
    with pytest.raises(DeviceTimeoutError) as raised:
        await task
    assert raised.value.code == "device_timeout"
    assert "did not confirm" in raised.value.message
    assert fan.get_state() == FAN_OFF
    assert rig.events("device_command") == []
    assert fan._pending == {}  # cleaned up


async def test_no_acknowledgement_times_out() -> None:
    rig, rig.probe = await ready()
    await expect_timeout(rig, lambda command: None)
    assert rig.device(FAN).status is DeviceStatus.UNKNOWN  # not responding


async def test_wrong_command_id_is_ignored() -> None:
    rig, rig.probe = await ready()
    other = "9a8b7c6d-0000-4000-8000-000000000000"
    await expect_timeout(rig, lambda command: rig.probe.state({"is_on": True, "speed": 50}, other))


async def test_acknowledgement_for_another_device_is_ignored() -> None:
    rig, rig.probe = await ready()
    await expect_timeout(
        rig, lambda command: rig.probe.state({"is_on": True, "speed": 50}, command.command_id, device_id=LIGHT)
    )


@pytest.mark.parametrize("state", [{"is_on": True, "speed": 250}, {"is_on": "yes", "speed": 50}, {"speed": 50.5}])
async def test_impossible_state_is_ignored(state: dict) -> None:
    rig, rig.probe = await ready()
    await expect_timeout(rig, lambda command: rig.probe.state(state, command.command_id))


@pytest.mark.parametrize("payload", [b"{not json", b'{"device_id": "fan_living_room"}', b"null"])
async def test_malformed_acknowledgement_is_ignored(payload: bytes) -> None:
    rig, rig.probe = await ready()
    await expect_timeout(rig, lambda command: rig.probe.raw_state(payload))


async def test_valid_but_wrong_acknowledged_state_fails_and_shows_the_real_state() -> None:
    rig, probe = await ready()
    task = asyncio.create_task(rig.command(FAN, "set_speed", 70))
    command = await probe.next_command()

    probe.state({"is_on": True, "speed": 40}, command.command_id)  # the device did something else

    with pytest.raises(DeviceStateMismatchError):
        await task
    assert rig.device(FAN).get_state() == {"is_on": True, "speed": 40}  # the device's truth
    assert rig.events("device_command") == []  # no success event
    [report] = rig.events("state_report")
    assert (report.source, report.details["reason"]) == ("mqtt", "mismatched_acknowledgement")


async def test_late_acknowledgement_after_a_timeout_is_recorded_as_a_state_report() -> None:
    rig, probe = await ready()
    task = asyncio.create_task(rig.command(FAN, "set_speed", 70))
    command = await probe.next_command()
    with pytest.raises(DeviceTimeoutError):
        await task

    probe.state(FAN_70, command.command_id)  # the device executed it after all
    await settle()

    assert rig.device(FAN).get_state() == FAN_70
    assert rig.device(FAN).status is DeviceStatus.ONLINE
    [report] = rig.events("state_report")
    assert report.details == {"transport": "mqtt", "reason": "late_acknowledgement", "command_id": command.command_id}
    assert rig.events("device_command") == []


# --- Reports the device makes on its own ------------------------------------------------------


async def test_unsolicited_state_report_is_recorded_with_mqtt_source() -> None:
    rig, probe = await ready()

    probe.state(FAN_70)  # someone pressed the fan's physical button
    await settle()

    [report] = rig.events("state_report")
    assert (report.source, report.previous_state, report.new_state) == ("mqtt", FAN_OFF, FAN_70)


async def test_retained_state_at_startup_is_adopted_without_an_event() -> None:
    rig = await Rig().start()
    probe = Probe(rig.broker, FAN)
    assert rig.device(FAN).last_confirmed_at is None  # defaults shown, but not confirmed

    probe.state(FAN_70, "11111111-2222-4333-8444-555555555555")  # last ack, retained across a backend restart
    await settle()
    assert rig.device(FAN).get_state() == FAN_70
    assert rig.events("state_report") == []

    probe.state(FAN_OFF, "66666666-2222-4333-8444-555555555555")  # unknown id once synced: ignored
    await settle()
    assert rig.device(FAN).get_state() == FAN_70


# --- Availability --------------------------------------------------------------------------------


async def test_availability_online_offline_and_reconnect() -> None:
    rig = await Rig().start()
    fan = rig.device(FAN)
    assert fan.status is DeviceStatus.UNKNOWN  # nothing reported yet

    probe = Probe(rig.broker, FAN)
    probe.online()
    probe.state(FAN_OFF)
    await settle()
    assert fan.status is DeviceStatus.ONLINE

    probe.offline()
    await settle()
    assert fan.status is DeviceStatus.OFFLINE
    started = time.monotonic()
    with pytest.raises(DeviceUnavailableError, match="^Living Room Fan is offline.$"):
        await rig.command(FAN, "turn_on")
    assert time.monotonic() - started < 0.1  # fails at once, no waiting for a timeout
    assert rig.commands_published(FAN) == []  # nothing was sent
    assert fan.get_state() == FAN_OFF  # last confirmed state is kept

    probe.online()  # reconnect
    await settle()
    task = asyncio.create_task(rig.command(FAN, "turn_on"))
    command = await probe.next_command()
    probe.state({"is_on": True, "speed": 50}, command.command_id)
    assert (await task).new_state["is_on"] is True

    statuses = [e.action for e in rig.events("availability")]
    assert statuses == ["online", "offline", "online"]


async def test_going_offline_fails_a_pending_command_immediately() -> None:
    rig, probe = await ready(mqtt_command_timeout_s=5)
    task = asyncio.create_task(rig.command(FAN, "turn_on"))
    await probe.next_command()

    started = time.monotonic()
    probe.offline()  # e.g. the broker publishes the Last Will
    with pytest.raises(DeviceUnavailableError, match="offline"):
        await task
    assert time.monotonic() - started < 1
    assert rig.device(FAN).get_state() == FAN_OFF


async def test_broker_disconnect_and_reconnect() -> None:
    rig, probe = await ready(mqtt_command_timeout_s=5)
    fan = rig.device(FAN)
    task = asyncio.create_task(rig.command(FAN, "turn_on"))
    await probe.next_command()

    rig.backend.abort()  # the backend loses the broker
    await settle()

    with pytest.raises(DeviceUnavailableError, match="connection to the MQTT broker was lost"):
        await task
    assert fan.status is DeviceStatus.UNKNOWN  # cannot know while disconnected
    with pytest.raises(DeviceUnavailableError, match="MQTT broker is not connected"):
        await rig.command(FAN, "turn_on")
    # Virtual devices are unaffected by the broker.
    assert (await rig.command(DOOR, "unlock")).new_state == {"is_locked": False}

    rig.backend.start()  # reconnect: retained availability and state come back
    await settle()
    assert fan.status is DeviceStatus.ONLINE
    assert fan.get_state() == FAN_OFF


# --- Measured power ------------------------------------------------------------------------------


async def test_measured_power_is_used_while_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    rig, probe = await ready()
    fan = rig.device(FAN)
    estimate = fan.power_w

    probe.transport.publish(topics.energy(FAN), b'{"timestamp": "2099-01-01T00:00:00Z", "power_w": 0.5}')
    await settle()
    await asyncio.sleep(0.05)  # measured clearly after the boot report (Windows clocks tick every ~15 ms)
    probe.transport.publish(topics.energy(FAN), '{"timestamp": "%s", "power_w": 7.25}' % _now_iso())
    await settle()
    assert fan.power_w == 7.25

    probe.transport.publish(topics.energy(FAN), b'{"timestamp": "2020-01-01T00:00:00Z", "power_w": 99}')
    await settle()
    assert fan.power_w == estimate  # stale reading: back to the estimate from confirmed state


async def test_a_reading_from_before_a_state_change_is_not_used_after_it() -> None:
    # Regression (found in the live MQTT run): the standby reading taken while the fan was
    # off was still used after it switched on, and Isolation Forest flagged an anomaly.
    rig, probe = await ready()
    fan = rig.device(FAN)
    probe.transport.publish(topics.energy(FAN), '{"timestamp": "%s", "power_w": 0.5}' % _now_iso())
    await settle()
    assert fan.power_w == 0.5

    task = asyncio.create_task(rig.command(FAN, "set_speed", 70))
    command = await probe.next_command()
    probe.state(FAN_70, command.command_id)
    await task

    assert fan.power_w == 45.6  # the estimate for speed 70, not the old 0.5 W reading
    anomalies = rig.container.ml_service.anomaly_report().live
    assert not next(r for r in anomalies if r.device_id == FAN).is_anomaly


# --- Concurrency ----------------------------------------------------------------------------------


async def test_commands_to_one_device_are_sent_one_at_a_time_in_order() -> None:
    rig, probe = await ready(mqtt_command_timeout_s=1)

    first = asyncio.create_task(rig.command(FAN, "set_speed", 30))
    second = asyncio.create_task(rig.command(FAN, "set_speed", 80))
    command = await probe.next_command()
    await asyncio.sleep(0.05)
    assert len(probe.commands) == 1  # the second waits for the first to be acknowledged

    probe.state({"is_on": True, "speed": 30}, command.command_id)
    command = await probe.next_command()
    assert command.parameters == {"value": 80}
    probe.state({"is_on": True, "speed": 80}, command.command_id)

    a, b = await first, await second
    assert b.previous_state == a.new_state  # consistent chain
    assert rig.device(FAN).get_state() == {"is_on": True, "speed": 80}


async def test_commands_to_different_devices_run_concurrently() -> None:
    rig, fan_probe = await ready(mqtt_command_timeout_s=1)
    light_probe = Probe(rig.broker, LIGHT)
    light_probe.online()
    light_probe.state({"is_on": False, "brightness": 100})
    await settle()

    fan_task = asyncio.create_task(rig.command(FAN, "turn_on"))
    light_task = asyncio.create_task(rig.command(LIGHT, "turn_on"))
    fan_command, light_command = await fan_probe.next_command(), await light_probe.next_command()

    # Both are in flight at the same time; acknowledge in reverse order.
    light_probe.state({"is_on": True, "brightness": 100}, light_command.command_id)
    fan_probe.state({"is_on": True, "speed": 50}, fan_command.command_id)
    await asyncio.gather(fan_task, light_task)
    assert {e.device_id for e in rig.events("device_command")} == {FAN, LIGHT}


async def test_a_timeout_leaves_the_device_ready_for_the_next_command() -> None:
    rig, probe = await ready()
    with pytest.raises(DeviceTimeoutError):
        await rig.command(FAN, "turn_on")
    assert rig.device(FAN)._pending == {}
    await probe.next_command()  # the timed-out one, never answered

    task = asyncio.create_task(rig.command(FAN, "turn_on"))
    command = await probe.next_command()
    probe.state({"is_on": True, "speed": 50}, command.command_id)
    assert (await task).new_state["is_on"] is True


def _now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
