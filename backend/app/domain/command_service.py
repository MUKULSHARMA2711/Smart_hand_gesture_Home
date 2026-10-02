import asyncio
import logging
from collections import defaultdict

from app.devices.commands import DeviceCommand
from app.domain.home_state import HomeState
from app.events.models import CommandSource, DeviceEvent
from app.events.store import EventStore

logger = logging.getLogger(__name__)


class CommandService:
    """The single entry point for changing device state.

    The REST API uses it today. Automations, gesture control, the AI agent and the
    MQTT bridge will call the same method, passing a different ``source``.
    """

    def __init__(self, home: HomeState, events: EventStore) -> None:
        self._home = home
        self._events = events
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def execute(self, device_id: str, command: DeviceCommand, source: CommandSource) -> DeviceEvent:
        device = self._home.devices.get(device_id)

        # Serialise commands per device so each event's previous/new state is consistent.
        async with self._locks[device_id]:
            self._home.record_energy()
            result = await device.execute_command(command)
            event = DeviceEvent(
                device_id=device.id,
                action=result.command.action,
                value=result.command.argument,
                previous_state=result.previous_state,
                new_state=result.new_state,
                source=source,
            )
            self._events.append(event)

        logger.info(
            "device=%s action=%s value=%s source=%s", event.device_id, event.action, event.value, event.source
        )
        return event
