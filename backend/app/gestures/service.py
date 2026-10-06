import logging
from collections.abc import Iterable

from app.domain.command_service import CommandService
from app.domain.errors import DomainError, IntentNotApplicableError
from app.domain.home_state import HomeState
from app.domain.intents import VALUE_INTENTS, Intent, IntentResolver
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
            device_command = self._resolver.resolve(command.intent, device, command.value)

            if device_command is None:  # targeting intent (SELECT): nothing to execute
                event = self._record(command, command.intent.lower(), GestureOutcome.ACKNOWLEDGED)
                return GestureCommandResult(gesture_event=event, device_event=None)

            action = device_command.action
            if action in self._blocked_actions:
                raise GestureActionBlockedError(action, device.id)

            device_event = await self._commands.execute(device.id, device_command, CommandSource.GESTURE)
        except (GestureRejectedError, IntentNotApplicableError) as exc:
            self._record(command, action, GestureOutcome.REJECTED, detail=exc.message)
            raise
        except DomainError as exc:
            self._record(command, action, GestureOutcome.FAILED, detail=exc.message)
            raise

        event = self._record(command, action, GestureOutcome.EXECUTED, device_event_id=device_event.event_id)
        return GestureCommandResult(gesture_event=event, device_event=device_event)

    def _validate(self, command: GestureCommand) -> None:
        expected_intent = GESTURE_INTENTS[command.gesture]
        if expected_intent is Intent.NONE:
            raise GestureNotActionableError(command.gesture)
        if command.intent is not expected_intent:
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
