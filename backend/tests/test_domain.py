"""Unit tests for devices, sensors and energy metering, without HTTP."""

from datetime import datetime

import pytest

from app.devices.commands import DeviceCommand
from app.devices.registry import DeviceRegistry
from app.devices.virtual import VirtualAC, VirtualLight
from app.domain.command_service import CommandService
from app.domain.energy import EnergyMeter
from app.domain.errors import DeviceNotFoundError, InvalidCommandError, UnsupportedCommandError
from app.domain.home_state import HomeState
from app.events.models import CommandSource, DeviceEvent
from app.events.store import InMemoryEventStore
from app.sensors.simulated import SimulatedSensorProvider

pytestmark = pytest.mark.anyio


def make_light() -> VirtualLight:
    return VirtualLight("light_test", "Test Light", "lab")


async def test_brightness_zero_turns_light_off_and_turn_on_restores_full_brightness() -> None:
    light = make_light()

    await light.execute_command(DeviceCommand(action="set_brightness", value=0))
    assert light.get_state() == {"is_on": False, "brightness": 0}

    await light.execute_command(DeviceCommand(action="turn_on"))
    assert light.get_state() == {"is_on": True, "brightness": 100}


async def test_command_result_captures_previous_and_new_state() -> None:
    light = make_light()

    result = await light.execute_command(DeviceCommand(action="set_brightness", value=30))

    assert result.previous_state == {"is_on": False, "brightness": 100}
    assert result.new_state == {"is_on": True, "brightness": 30}


async def test_validation_errors_leave_state_untouched() -> None:
    light = make_light()

    with pytest.raises(InvalidCommandError):
        await light.execute_command(DeviceCommand(action="set_brightness", value=101))
    with pytest.raises(UnsupportedCommandError):
        await light.execute_command(DeviceCommand(action="lock"))

    assert light.get_state() == {"is_on": False, "brightness": 100}


async def test_ac_set_point_changes_while_off_without_turning_on() -> None:
    ac = VirtualAC("ac_test", "Test AC", "lab")

    await ac.execute_command(DeviceCommand(action="set_temperature", value=20))

    assert ac.get_state() == {"is_on": False, "target_temperature_c": 20}


async def test_colder_ac_set_point_draws_more_power() -> None:
    ac = VirtualAC("ac_test", "Test AC", "lab")
    await ac.execute_command(DeviceCommand(action="turn_on"))

    await ac.execute_command(DeviceCommand(action="set_temperature", value=26))
    warm_power = ac.power_w
    await ac.execute_command(DeviceCommand(action="set_temperature", value=18))

    assert ac.power_w > warm_power


async def test_command_service_logs_event_with_source() -> None:
    registry = DeviceRegistry([make_light()])
    events = InMemoryEventStore()
    service = CommandService(HomeState(registry, SimulatedSensorProvider(seed=1)), events)

    event = await service.execute("light_test", DeviceCommand(action="turn_on"), CommandSource.AUTOMATION)

    assert events.recent() == [event]
    assert event.source is CommandSource.AUTOMATION
    with pytest.raises(DeviceNotFoundError):
        await service.execute("nope", DeviceCommand(action="turn_on"), CommandSource.FRONTEND)


def test_registry_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        DeviceRegistry([make_light(), make_light()])


def test_event_store_drops_oldest_when_full() -> None:
    store = InMemoryEventStore(max_size=2)
    for action in ("a", "b", "c"):
        store.append(
            DeviceEvent(device_id="d", action=action, previous_state={}, new_state={}, source=CommandSource.FRONTEND)
        )

    assert [event.action for event in store.recent()] == ["c", "b"]


def test_energy_meter_integrates_power_over_time() -> None:
    now = [0.0]
    meter = EnergyMeter(clock=lambda: now[0])

    now[0] = 1800.0
    meter.accumulate(1000.0)  # 1 kW for half an hour
    now[0] = 3600.0
    meter.accumulate(500.0)  # 0.5 kW for half an hour

    assert meter.energy_kwh == pytest.approx(0.75)


@pytest.mark.parametrize("hour", range(24))
def test_simulated_sensors_stay_in_realistic_ranges(hour: int) -> None:
    sensors = SimulatedSensorProvider(seed=7, clock=lambda: datetime(2026, 6, 1, hour, 30))

    for _ in range(50):
        reading = sensors.read()
        assert 18 <= reading.temperature_c <= 34
        assert 20 <= reading.humidity_pct <= 95
        assert 0 <= reading.ambient_light_lux <= 800
        assert 0 <= reading.occupancy.occupant_count <= 4


def test_simulated_daylight_is_brighter_than_night() -> None:
    noon = SimulatedSensorProvider(seed=3, clock=lambda: datetime(2026, 6, 1, 12, 0)).read()
    midnight = SimulatedSensorProvider(seed=3, clock=lambda: datetime(2026, 6, 1, 0, 0)).read()

    assert noon.ambient_light_lux > 100 > midnight.ambient_light_lux
    assert noon.temperature_c > midnight.temperature_c
