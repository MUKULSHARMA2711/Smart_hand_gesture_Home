import logging
from collections.abc import Callable, Iterable
from typing import Any

from app.devices.types import DeviceStatus
from app.domain.command_service import CommandService
from app.domain.errors import DomainError, IntentNotApplicableError
from app.domain.home_state import HomeState
from app.domain.intents import VALUE_INTENTS, Intent, IntentResolver, is_applicable
from app.events.models import CommandSource
from app.gestures.errors import (
    GestureActionBlockedError,
    GestureIntentMismatchError,
    GestureNotActionableError,
    GestureRejectedError,
    GestureValueError,
    LowConfidenceError,
)
from app.gestures.history import GestureHistory
from app.gestures.models import (
    GESTURE_ALTERNATE_INTENTS,
    GESTURE_INTENTS,
    GestureCommand,
    GestureCommandResult,
    GestureEvent,
    GestureOutcome,
)

logger = logging.getLogger(__name__)


class GestureService:
    """Turns a recognised gesture into a device command.

    Pipeline: validate gesture/intent -> confidence gate -> resolve intent against the
    target device -> gesture policy -> existing :class:`CommandService` (source=gesture).
    Every attempt, successful or not, is recorded in the gesture history.
    """

    def __init__(
        self,
        home: HomeState,
        commands: CommandService,
        history: GestureHistory,
        *,
        resolver: IntentResolver | None = None,
        confidence_threshold: float = 0.75,
        blocked_actions: Iterable[str] = (),
    ) -> None:
        self._home = home
        self._commands = commands
        self._history = history
        self._resolver = resolver or IntentResolver()
        self._confidence_threshold = confidence_threshold
        self._blocked_actions = frozenset(blocked_actions)
        # Creates a pending unlock confirmation (HomeAgent.hold_gesture_unlock); None = disabled.
        self._request_unlock: Callable[[str], Any] | None = None

    def enable_unlock_confirmation(self, request_unlock: Callable[[str], Any]) -> None:
        """Let a pinch on the door *request* an unlock, confirmed later via the confirmation API."""
        self._request_unlock = request_unlock

    @property
    def confidence_threshold(self) -> float:
        return self._confidence_threshold

    @property
    def blocked_actions(self) -> frozenset[str]:
        return self._blocked_actions

    async def handle(self, command: GestureCommand) -> GestureCommandResult:
        action: str | None = None
        try:
            self._validate(command)
            device = self._home.devices.get(command.target_device_id)
            if command.intent is Intent.UNLOCK_DOOR:
                return self._request_door_unlock(command, device)
            device_command = self._resolver.resolve(command.intent, device, command.value)

            if device_command is None:  # targeting intent (SELECT): nothing to execute
                event = self._record(command, command.intent.lower(), GestureOutcome.ACKNOWLEDGED)
                return GestureCommandResult(gesture_event=event, device_event=None)

            action = device_command.action
            if action in self._blocked_actions:
                raise GestureActionBlockedError(action, device.id)
            if command.intent is Intent.LOCK_DOOR and _confirmed_locked(device):
                # A fist on a door the device itself reports as locked: no repeated command or event.
                event = self._record(command, action, GestureOutcome.ACKNOWLEDGED, detail=f"{device.name} is already locked.")
                return GestureCommandResult(gesture_event=event, device_event=None)

            device_event = await self._commands.execute(device.id, device_command, CommandSource.GESTURE)
        except (GestureRejectedError, IntentNotApplicableError) as exc:
            self._record(command, action, GestureOutcome.REJECTED, detail=exc.message)
            raise
        except DomainError as exc:
            self._record(command, action, GestureOutcome.FAILED, detail=exc.message)
            raise

        event = self._record(command, action, GestureOutcome.EXECUTED, device_event_id=device_event.event_id)
        return GestureCommandResult(gesture_event=event, device_event=device_event)

    def _request_door_unlock(self, command: GestureCommand, device: Any) -> GestureCommandResult:
        """Never unlocks: creates a pending confirmation the user must confirm (pinch / API)."""
        if not is_applicable(Intent.UNLOCK_DOOR, device):
            raise IntentNotApplicableError(command.intent, device.id)  # fan, AC, light: unchanged
        pending = self._request_unlock(device.id) if self._request_unlock is not None else None
        if pending is None:  # gesture unlock disabled, or refused by the unlock policy
            raise GestureActionBlockedError("unlock", device.id)
        event = self._record(command, "unlock", GestureOutcome.AWAITING_CONFIRMATION, detail=pending.prompt)
        return GestureCommandResult(gesture_event=event, device_event=None, confirmation=pending)

    def _validate(self, command: GestureCommand) -> None:
        expected_intent = GESTURE_INTENTS[command.gesture]
        if expected_intent is Intent.NONE:
            raise GestureNotActionableError(command.gesture)
        alternates = GESTURE_ALTERNATE_INTENTS.get(command.gesture, frozenset())
        if command.intent is not expected_intent and command.intent not in alternates:
            raise GestureIntentMismatchError(command.gesture, command.intent, expected_intent)
        if command.confidence < self._confidence_threshold:
            raise LowConfidenceError(command.confidence, self._confidence_threshold)
        if (command.value is not None) != (command.intent in VALUE_INTENTS):
            raise GestureValueError(command.intent, command.value)

    def _record(
        self,
        command: GestureCommand,
        action: str | None,
        outcome: GestureOutcome,
        *,
        detail: str | None = None,
        device_event_id: str | None = None,
    ) -> GestureEvent:
        event = GestureEvent(
            gesture=command.gesture,
            confidence=command.confidence,
            intent=command.intent,
            target_device_id=command.target_device_id,
            value=command.value,
            action=action,
            outcome=outcome,
            detail=detail,
            device_event_id=device_event_id,
        )
        self._history.append(event)
        logger.info(
            "gesture=%s intent=%s confidence=%.2f target=%s action=%s outcome=%s",
            event.gesture, event.intent, event.confidence, event.target_device_id, event.action, event.outcome,
        )
        return event


def _confirmed_locked(device: Any) -> bool:
    """Locked according to the device's own confirmed state. An unreachable or unknown device is
    never assumed locked, so the lock command is still sent (and fails or succeeds visibly)."""
    return device.status is DeviceStatus.ONLINE and device.get_state().get("is_locked") is True
