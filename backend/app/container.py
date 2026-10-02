"""Composition root: the one place that wires concrete implementations together."""

from dataclasses import dataclass

from app.config import Settings
from app.devices.factory import build_device
from app.devices.registry import DeviceRegistry
from app.domain.command_service import CommandService
from app.domain.home_state import HomeState
from app.events.store import EventStore, InMemoryEventStore
from app.sensors.simulated import SimulatedSensorProvider


@dataclass(frozen=True)
class Container:
    settings: Settings
    home_state: HomeState
    event_store: EventStore
    command_service: CommandService


def build_container(settings: Settings) -> Container:
    latency_s = settings.virtual_device_latency_ms / 1000
    registry = DeviceRegistry(build_device(config, virtual_latency_s=latency_s) for config in settings.devices)
    home_state = HomeState(registry, SimulatedSensorProvider(seed=settings.sensor_seed))
    event_store = InMemoryEventStore(max_size=settings.event_log_max_size)
    return Container(
        settings=settings,
        home_state=home_state,
        event_store=event_store,
        command_service=CommandService(home_state, event_store),
    )
