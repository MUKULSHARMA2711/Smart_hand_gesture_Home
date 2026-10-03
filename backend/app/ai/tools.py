"""The agent's tools. Read-only tools may be called by the LLM; control_device may not.

The LLM can *propose* control_device actions in its plan, but only the backend
executor calls :meth:`AgentTools.control_device`, after validation and policy checks.
"""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai.context import HomeContext, build_home_context
from app.devices.commands import DeviceCommand
from app.domain.command_service import CommandService
from app.domain.errors import DeviceNotFoundError
from app.domain.home_state import HomeState
from app.events.models import CommandSource, DeviceEvent
from app.events.store import EventStore


class _NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _DeviceArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=1, max_length=64)


class _EventsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=10, ge=1, le=50)
    device_id: str | None = None


class ToolError(Exception):
    """A read-only tool call failed; reported back to the LLM as an error result."""


class AgentTools:
    def __init__(self, home: HomeState, events: EventStore, commands: CommandService) -> None:
        self._home = home
        self._events = events
        self._commands = commands

    # --- Read-only tools ---------------------------------------------------------------

    def home_context(self) -> HomeContext:
        return build_home_context(self._home, self._events)

    def get_home_state(self) -> dict[str, Any]:
        return self.home_context().model_dump(mode="json")

    def get_device_status(self, device_id: str) -> dict[str, Any]:
        device = self.home_context().device(device_id)
        if device is None:
            raise ToolError(f"Unknown device '{device_id}'.")
        return device.model_dump(mode="json")

    def get_recent_events(self, limit: int = 10, device_id: str | None = None) -> list[dict[str, Any]]:
        return [event.model_dump(mode="json") for event in self._events.recent(limit=limit, device_id=device_id)]

    def get_energy_usage(self) -> dict[str, Any]:
        context = self.home_context()
        total = context.energy.total_power_w
        per_device = sorted(
            (
                {
                    "device_id": device.id,
                    "name": device.name,
                    "power_w": device.power_w,
                    "share_pct": round(100 * device.power_w / total, 1) if total else 0.0,
                }
                for device in context.devices
            ),
            key=lambda entry: entry["power_w"],
            reverse=True,
        )
        return {
            "total_power_w": total,
            "energy_kwh_since_start": context.energy.energy_kwh,
            "per_device": per_device,
            "top_consumer": per_device[0]["device_id"] if per_device else None,
        }

    # --- Executor-only tool ----------------------------------------------------------

    async def control_device(self, device_id: str, command: DeviceCommand) -> DeviceEvent:
        """Execute an already-validated command. Never exposed to the LLM."""
        return await self._commands.execute(device_id, command, CommandSource.AI_AGENT)

    # --- LLM tool interface ----------------------------------------------------------

    def call_read_only(self, name: str, arguments: dict[str, Any]) -> Any:
        """Dispatch a read-only tool call requested by the LLM, validating its arguments."""
        handlers: dict[str, tuple[type[BaseModel], Callable[..., Any]]] = {
            "get_home_state": (_NoArgs, lambda a: self.get_home_state()),
            "get_device_status": (_DeviceArgs, lambda a: self.get_device_status(a.device_id)),
            "get_recent_events": (_EventsArgs, lambda a: self.get_recent_events(a.limit, a.device_id)),
            "get_energy_usage": (_NoArgs, lambda a: self.get_energy_usage()),
        }
        if name not in handlers:
            raise ToolError(f"Unknown tool '{name}'. Device changes must go in the action plan.")
        schema, handler = handlers[name]
        try:
            args = schema.model_validate(arguments or {})
        except ValidationError as exc:
            raise ToolError(f"Invalid arguments for {name}: {exc.errors(include_url=False)}") from exc
        try:
            return handler(args)
        except DeviceNotFoundError as exc:
            raise ToolError(exc.message) from exc


# JSON-schema definitions of the read-only tools, for LLM providers.
READ_ONLY_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "get_home_state",
        "description": "Full current home state: every device with its capabilities and state, "
        "environment sensors, energy and the most recent events.",
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "name": "get_device_status",
        "description": "Current state, capabilities and power draw of one device.",
        "input_schema": {
            "type": "object",
            "properties": {"device_id": {"type": "string", "description": "A device id from the home context."}},
            "required": ["device_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_recent_events",
        "description": "Recent device events (newest first), optionally for one device. "
        "Each event has its source: frontend, gesture, ai_agent, automation or mqtt.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "1-50 events."},
                "device_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            },
            "required": ["limit", "device_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_energy_usage",
        "description": "Current total power draw, energy used since the backend started, and per-device usage.",
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
]

