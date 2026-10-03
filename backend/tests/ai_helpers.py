"""Test doubles for the AI layer."""

from typing import Any

from app.ai.providers.base import AIProvider, AIProviderError, PlanningRequest
from app.devices.commands import DeviceCommand
from app.domain.command_service import CommandService
from app.events.models import CommandSource, DeviceEvent


class ScriptedProvider(AIProvider):
    """Returns a fixed raw plan, standing in for an LLM that may be wrong or malicious."""

    name = "scripted"
    model = "test"

    def __init__(self, plan: Any = None, *, error: str | None = None) -> None:
        self._plan = plan
        self._error = error
        self.requests: list[PlanningRequest] = []

    async def plan(self, request: PlanningRequest) -> Any:
        self.requests.append(request)
        if self._error:
            raise AIProviderError(self._error)
        return self._plan


class SpyCommandService(CommandService):
    """Real CommandService that also records every call."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.calls: list[tuple[str, DeviceCommand, CommandSource]] = []

    async def execute(self, device_id: str, command: DeviceCommand, source: CommandSource) -> DeviceEvent:
        self.calls.append((device_id, command, source))
        return await super().execute(device_id, command, source)


def action(device_id: str | None, intent: str, **parameters: Any) -> dict[str, Any]:
    return {"device_id": device_id, "intent": intent, "parameters": parameters}
