from abc import ABC, abstractmethod
from collections import deque

from app.events.models import DeviceEvent


class EventStore(ABC):
    """Persistence for device events. In-memory today; a database later."""

    @abstractmethod
    def append(self, event: DeviceEvent) -> None: ...

    @abstractmethod
    def recent(self, *, limit: int = 50, device_id: str | None = None) -> list[DeviceEvent]:
        """Return up to ``limit`` events, newest first."""


class InMemoryEventStore(EventStore):
    """Bounded ring buffer: the oldest events are dropped once ``max_size`` is reached."""

    def __init__(self, max_size: int = 1000) -> None:
        self._events: deque[DeviceEvent] = deque(maxlen=max_size)

    def append(self, event: DeviceEvent) -> None:
        self._events.append(event)

    def recent(self, *, limit: int = 50, device_id: str | None = None) -> list[DeviceEvent]:
        matches: list[DeviceEvent] = []
        for event in reversed(self._events):
            if device_id is None or event.device_id == device_id:
                matches.append(event)
                if len(matches) == limit:
                    break
        return matches
