from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.ai.context import HomeContext
from app.ai.tools import AgentTools


class AIProviderError(Exception):
    """The provider could not produce a plan (network, auth, refusal, unparseable output...)."""


@dataclass(frozen=True)
class PlanningRequest:
    message: str
    context: HomeContext
    tools: AgentTools  # providers may only call its read-only tools via call_read_only()
    # Recent assistant interactions, newest first (for follow-ups such as "turn it on").
    history: tuple[Any, ...] = ()


class AIProvider(ABC):
    """Turns a natural-language request into a *raw* plan: ``{"message": str, "actions": [...]}``.

    The return value is untrusted. The agent validates it with Pydantic, capability
    checks and the security policy before anything executes.
    """

    name: str = "provider"
    model: str = ""

    @abstractmethod
    async def plan(self, request: PlanningRequest) -> dict[str, Any]: ...


class UnavailableAIProvider(AIProvider):
    """Stands in for a provider that failed to initialise; every request reports why."""

    def __init__(self, name: str, model: str, reason: str) -> None:
        self.name = name
        self.model = model
        self._reason = reason

    async def plan(self, request: PlanningRequest) -> dict[str, Any]:
        raise AIProviderError(self._reason)
