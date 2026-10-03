from collections import deque

from app.ai.models import AgentResponse


class InMemoryAgentHistory:
    """Bounded record of assistant interactions, newest first. A database later."""

    def __init__(self, max_size: int = 100) -> None:
        self._interactions: deque[AgentResponse] = deque(maxlen=max_size)

    def append(self, interaction: AgentResponse) -> None:
        self._interactions.append(interaction)

    def recent(self, *, limit: int = 20) -> list[AgentResponse]:
        return list(reversed(self._interactions))[:limit]
