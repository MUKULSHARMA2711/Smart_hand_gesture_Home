from abc import ABC, abstractmethod
from collections import deque

from app.gestures.models import GestureEvent


class GestureHistory(ABC):
    """Storage for gesture events. In-memory today; a database later."""

    @abstractmethod
    def append(self, event: GestureEvent) -> None: ...

    @abstractmethod
    def recent(self, *, limit: int = 50) -> list[GestureEvent]:
        """Return up to ``limit`` events, newest first."""


class InMemoryGestureHistory(GestureHistory):
    """Bounded ring buffer: the oldest events are dropped once ``max_size`` is reached."""

    def __init__(self, max_size: int = 500) -> None:
        self._events: deque[GestureEvent] = deque(maxlen=max_size)

    def append(self, event: GestureEvent) -> None:
        self._events.append(event)

    def recent(self, *, limit: int = 50) -> list[GestureEvent]:
        return list(reversed(self._events))[:limit]
