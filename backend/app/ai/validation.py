"""Turns each AI-proposed action into either a safe, executable command or a rejection.

Every check runs before anything executes: schema -> allowed intent -> parameters ->
device exists -> device has the capability -> value range (device spec) -> security
policy -> duplicates.
"""

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.ai.models import AI_INTENTS, AI_QUERY_INTENTS, PARAMETER_MODELS, NoParameters, PlannedAction
from app.devices.commands import DeviceCommand
from app.devices.registry import DeviceRegistry
from app.devices.types import Capability
from app.domain.errors import DomainError, IntentNotApplicableError
from app.domain.intents import VALUE_INTENTS, IntentResolver
from app.domain.policy import SecurityPolicy
from app.events.models import CommandSource


@dataclass
class ValidatedAction:
    index: int
    raw: Any
    action: PlannedAction | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    command: DeviceCommand | None = None  # set for executable device actions
    capability: Capability | None = None
    rejection_code: str | None = None
    rejection_reason: str | None = None

    @property
    def rejected(self) -> bool:
        return self.rejection_code is not None

    @property
    def is_query(self) -> bool:
        return self.action is not None and self.action.intent in AI_QUERY_INTENTS


def _summarize(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in error['loc']) or 'action'}: {error['msg']}" for error in exc.errors()
    )


class PlanValidator:
    def __init__(self, devices: DeviceRegistry, resolver: IntentResolver, policy: SecurityPolicy) -> None:
        self._devices = devices
        self._resolver = resolver
        self._policy = policy

    def validate_all(self, raw_actions: list[Any], utterance: str) -> list[ValidatedAction]:
        validated: list[ValidatedAction] = []
        seen: set[tuple[str | None, str, tuple]] = set()
        for index, raw in enumerate(raw_actions):
            result = self.validate(index, raw, utterance)
            if not result.rejected and result.action is not None:
                key = (result.action.device_id, result.action.intent, tuple(sorted(result.parameters.items())))
                if key in seen:
                    result = self._reject(result, "duplicate_action", "This action already appears earlier in the plan.")
                seen.add(key)
            validated.append(result)
        return validated

    def validate(self, index: int, raw: Any, utterance: str) -> ValidatedAction:
        result = ValidatedAction(index=index, raw=raw)

        try:
            action = PlannedAction.model_validate(raw)
        except ValidationError as exc:
            return self._reject(result, "malformed_action", f"Malformed action: {_summarize(exc)}")
        result.action = action

        if action.intent not in AI_INTENTS:
            return self._reject(result, "intent_not_allowed", f"Intent '{action.intent}' is not available to the AI agent.")

        parameter_model = PARAMETER_MODELS.get(action.intent, NoParameters)
        try:
            result.parameters = parameter_model.model_validate(action.parameters).model_dump()
        except ValidationError as exc:
            return self._reject(result, "invalid_parameters", f"Invalid parameters: {_summarize(exc)}")

        if action.intent in AI_QUERY_INTENTS:
            if action.device_id is not None and action.device_id not in self._devices:
                return self._reject(result, "unknown_device", f"Device '{action.device_id}' does not exist.")
            return result

        # Device control
        if action.device_id is None:
            return self._reject(result, "missing_device", f"Intent '{action.intent}' needs a device_id.")
        if action.device_id not in self._devices:
            return self._reject(result, "unknown_device", f"Device '{action.device_id}' does not exist.")
        device = self._devices.get(action.device_id)

        try:
            value = result.parameters.get("value") if action.intent in VALUE_INTENTS else None
            command = self._resolver.resolve(action.intent, device, value)
        except IntentNotApplicableError:
            return self._reject(
                result,
                "unsupported_capability",
                f"{device.name} does not support '{action.intent}'. Its capabilities are: "
                f"{', '.join(device.spec.capabilities)}.",
            )
        assert command is not None  # AI intents are never targeting intents

        try:
            device.spec.parse_command(device.id, command)  # range/type check, no side effects
        except DomainError as exc:
            return self._reject(result, "invalid_parameters", exc.message)

        capability = self._resolver.capability_for(action.intent, device)
        decision = self._policy.evaluate(
            capability=capability, device_id=device.id, source=CommandSource.AI_AGENT, utterance=utterance
        )
        if not decision.allowed:
            return self._reject(result, decision.code or "policy_denied", decision.reason or "Denied by policy.")

        result.command = command
        result.capability = capability
        return result

    @staticmethod
    def _reject(result: ValidatedAction, code: str, reason: str) -> ValidatedAction:
        result.rejection_code = code
        result.rejection_reason = reason
        result.command = None
        return result
