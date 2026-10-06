"""The AI home agent: plan with a provider, validate everything, then execute.

    user message
      -> HomeContext (current devices, sensors, energy, recent events)
      -> AIProvider.plan()            untrusted JSON: {"message", "actions": [...]}
      -> ActionPlan / PlannedAction   strict Pydantic validation
      -> PlanValidator                capabilities, parameters, security policy
      -> AgentTools.control_device    -> existing CommandService (source=ai_agent)

All actions are validated before any of them executes.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import NoReturn

from pydantic import ValidationError

from app.ai.confirmation import ConfirmationStore, Reply, classify_reply
from app.ai.errors import AIUnavailableError, ConfirmationExpiredError, ConfirmationNotFoundError
from app.ai.history import InMemoryAgentHistory
from app.ai.models import ActionPlan, ActionResult, ActionStatus, AgentResponse, PendingConfirmation
from app.ai.providers.base import AIProvider, AIProviderError, PlanningRequest
from app.ai.tools import AgentTools, ToolSession
from app.ai.validation import PlanValidator, ValidatedAction
from app.domain.errors import DomainError
from app.domain.intents import Intent
from app.events.models import DeviceEvent

logger = logging.getLogger(__name__)


class HomeAgent:
    def __init__(
        self,
        provider: AIProvider,
        tools: AgentTools,
        validator: PlanValidator,
        history: InMemoryAgentHistory,
        *,
        timeout_s: float = 120.0,
        confirmation_timeout_s: float = 30.0,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._provider = provider
        self._tools = tools
        self._validator = validator
        self._history = history
        self._timeout_s = timeout_s
        self._confirmation_timeout = timedelta(seconds=confirmation_timeout_s)
        self._clock = clock
        self._confirmations = ConfirmationStore()

    @property
    def provider(self) -> AIProvider:
        return self._provider

    async def handle(self, message: str) -> AgentResponse:
        pending = self._confirmations.pending
        if pending is not None:
            reply = classify_reply(message)
            if pending.expires_at <= self._clock():
                self._confirmations.clear()
                if reply is Reply.CONFIRM:  # "yes, unlock it" too late: never execute it
                    return self._closed(pending, message, expired=True)
            elif reply is Reply.CONFIRM:
                return await self._confirm(pending, message)
            elif reply is Reply.CANCEL:
                return self._closed(pending, message, expired=False)
            elif reply is Reply.AFFIRM_ONLY:
                name = self._device_name(pending)
                return self._finish(
                    message,
                    reply=f"To unlock the {name}, say 'yes, unlock it'. Say 'cancel' to keep it locked.",
                    results=[self._held_result(pending, ActionStatus.AWAITING_CONFIRMATION)],
                    plan_valid=True,
                    confirmation=pending,
                )
            else:
                self._confirmations.clear()  # the user moved on: the unlock is dropped, not kept waiting
        return await self._plan_and_execute(message)

    async def decide(self, confirmation_id: str, confirm: bool) -> AgentResponse:
        """The confirm / cancel buttons: same checks and execution path as a spoken reply."""
        pending = self._confirmations.pending
        if pending is None or pending.confirmation_id != confirmation_id:
            raise ConfirmationNotFoundError(confirmation_id)
        name = self._device_name(pending)
        if pending.expires_at <= self._clock():
            self._closed(pending, f"Confirm unlock of the {name}", expired=True)
            raise ConfirmationExpiredError(confirmation_id)
        if confirm:
            return await self._confirm(pending, f"Confirmed: unlock the {name}")
        return self._closed(pending, f"Cancelled: unlock the {name}", expired=False)

    async def _plan_and_execute(self, message: str) -> AgentResponse:
        context = self._tools.home_context()
        session = self._tools.session(context)
        history = tuple(self._history.recent(limit=3))
        try:
            raw_plan = await asyncio.wait_for(
                self._provider.plan(PlanningRequest(message=message, context=context, tools=session, history=history)),
                timeout=self._timeout_s,
            )
        except AIProviderError as exc:
            self._unavailable(message, str(exc))
        except TimeoutError:
            self._unavailable(message, f"The AI provider did not respond within {self._timeout_s:g} s.")
        except Exception as exc:  # a provider bug must not surface as a raw server error
            logger.exception("AI provider raised an unexpected error")
            self._unavailable(message, f"The AI provider failed unexpectedly ({type(exc).__name__}).")

        try:
            plan = ActionPlan.model_validate(raw_plan)
        except ValidationError as exc:
            errors = [f"{'.'.join(str(p) for p in e['loc']) or 'plan'}: {e['msg']}" for e in exc.errors()]
            logger.warning("AI provider returned an invalid plan: %s", errors)
            return self._finish(
                message, reply="The AI produced an invalid plan, so nothing was changed.", errors=errors
            )

        # Validate everything first; nothing executes if it has not passed every check.
        validated = self._validator.validate_all(plan.actions, message)
        results: list[ActionResult] = []
        device_events: list[DeviceEvent] = []
        confirmation: PendingConfirmation | None = None
        for item in validated:
            if item.requires_confirmation and not item.rejected:
                confirmation = self._hold(item, message)
                results.append(self._held_result(confirmation, ActionStatus.AWAITING_CONFIRMATION))
                continue
            result, event = await self._execute(item, session)
            results.append(result)
            if event is not None:
                device_events.append(event)

        # The planner's text may say "I'll unlock it"; while the unlock is held, ask instead.
        reply = confirmation.prompt if confirmation else plan.message
        return self._finish(
            message, reply=reply, results=results, device_events=device_events, plan_valid=True, confirmation=confirmation
        )

    # --- Confirmation of security-sensitive actions ---------------------------------------

    def _hold(self, item: ValidatedAction, message: str) -> PendingConfirmation:
        assert item.action is not None and item.action.device_id is not None
        now = self._clock()
        name = self._tools.home.devices.get(item.action.device_id).name
        pending = PendingConfirmation(
            device_id=item.action.device_id,
            intent=str(item.action.intent),
            prompt=f"Are you sure you want to unlock the {name}? Say 'yes, unlock it' to confirm, or 'cancel'.",
            request=message,
            created_at=now,
            expires_at=now + self._confirmation_timeout,
        )
        self._confirmations.hold(pending, item.raw)
        logger.info("held %s on %s for confirmation until %s", pending.intent, pending.device_id, pending.expires_at)
        return pending

    async def _confirm(self, pending: PendingConfirmation, message: str) -> AgentResponse:
        raw_action = self._confirmations.raw_action
        self._confirmations.clear()  # one confirmation executes at most once
        # Re-validate now (device, capability, and the policy on the original explicit request);
        # only the confirmation step is satisfied. Execution is the normal CommandService path.
        item = self._validator.validate(0, raw_action, pending.request, confirmed=True)
        session = self._tools.session(self._tools.home_context())
        result, event = await self._execute(item, session)
        name = self._device_name(pending)
        if result.status is ActionStatus.EXECUTED:
            reply = f"Confirmed. The {name} is unlocked."
        else:
            reply = f"The {name} was not unlocked: {result.reason}"
        return self._finish(message, reply=reply, results=[result], device_events=[event] if event else [], plan_valid=True)

    def _closed(self, pending: PendingConfirmation, message: str, *, expired: bool) -> AgentResponse:
        self._confirmations.clear()
        name = self._device_name(pending)
        if expired:
            reply = f"The request to unlock the {name} expired, so it stays locked. Ask again if you still want it unlocked."
        else:
            reply = f"Cancelled. The {name} stays locked."
        result = self._held_result(pending, ActionStatus.CANCELLED)
        result.code = "confirmation_expired" if expired else "cancelled_by_user"
        return self._finish(message, reply=reply, results=[result], plan_valid=True)

    def _held_result(self, pending: PendingConfirmation, status: ActionStatus) -> ActionResult:
        awaiting = status is ActionStatus.AWAITING_CONFIRMATION
        return ActionResult(
            index=0,
            device_id=pending.device_id,
            intent=pending.intent,
            status=status,
            code="confirmation_required" if awaiting else None,
            reason=pending.prompt if awaiting else None,
        )

    def _device_name(self, pending: PendingConfirmation) -> str:
        devices = self._tools.home.devices
        return devices.get(pending.device_id).name if pending.device_id in devices else pending.device_id

    def _unavailable(self, message: str, reason: str) -> NoReturn:
        """Record the failed attempt (nothing executed), then report it as a structured error."""
        logger.warning("AI provider unavailable: %s", reason)
        response = self._finish(message, reply="The AI planner is unavailable, so nothing was changed.", errors=[reason])
        raise AIUnavailableError(reason, interaction_id=response.interaction_id)

    async def _execute(self, item: ValidatedAction, session: ToolSession) -> tuple[ActionResult, DeviceEvent | None]:
        action = item.action
        base = {
            "index": item.index,
            "device_id": action.device_id if action else _raw_field(item.raw, "device_id"),
            "intent": str(action.intent) if action else _raw_field(item.raw, "intent"),
            "parameters": item.parameters or (action.parameters if action else {}),
        }

        if item.rejected:
            return ActionResult(**base, status=ActionStatus.REJECTED, code=item.rejection_code, reason=item.rejection_reason), None

        if item.is_query:
            return ActionResult(**base, status=ActionStatus.ANSWERED, data=self._query(item, session)), None

        assert item.command is not None and action is not None and action.device_id is not None
        try:
            event = await self._tools.control_device(action.device_id, item.command)
        except DomainError as exc:
            return ActionResult(**base, status=ActionStatus.FAILED, code=exc.code, reason=exc.message), None
        except Exception:
            # Report this action as failed and keep the results of the others (a partial plan
            # must still say exactly what ran). CommandService logs no event for a failed command.
            logger.exception("AI action %s on %s failed unexpectedly", action.intent, action.device_id)
            reason = "The device command failed unexpectedly; the device state was not reported as changed."
            return ActionResult(**base, status=ActionStatus.FAILED, code="internal_error", reason=reason), None
        return (
            ActionResult(
                **base,
                status=ActionStatus.EXECUTED,
                device_action=event.action,
                device_event_id=event.event_id,
                previous_state=event.previous_state,
                new_state=event.new_state,
            ),
            event,
        )

    @staticmethod
    def _query(item: ValidatedAction, session: ToolSession):
        """Answer read-only intents from backend data (ML values come from this request's context)."""
        assert item.action is not None
        match item.action.intent:
            case Intent.GET_ENERGY:
                return session.get_energy_usage()
            case Intent.GET_HISTORY:
                return session.get_recent_events(item.parameters.get("limit", 10), item.action.device_id)
            case Intent.GET_PREDICTIONS:
                return session.get_predictions()
            case Intent.GET_ANOMALIES:
                return session.get_anomalies()
            case _:
                if item.action.device_id:
                    return session.get_device_status(item.action.device_id)
                return session.get_home_state()

    def _finish(
        self,
        message: str,
        *,
        reply: str,
        results: list[ActionResult] | None = None,
        device_events: list[DeviceEvent] | None = None,
        plan_valid: bool = False,
        errors: list[str] | None = None,
        confirmation: PendingConfirmation | None = None,
    ) -> AgentResponse:
        results = results or []
        device_events = device_events or []
        response = AgentResponse(
            request=message,
            reply=reply,
            outcome=_outcome(results, plan_valid),
            provider=f"{self._provider.name}:{self._provider.model}",
            plan_valid=plan_valid,
            actions=results,
            device_events=device_events,
            changed_devices=list(dict.fromkeys(e.device_id for e in device_events if e.previous_state != e.new_state)),
            any_rejected=any(r.status is ActionStatus.REJECTED for r in results) or not plan_valid,
            errors=errors or [],
            confirmation=confirmation,
        )
        self._history.append(response)
        logger.info(
            "ai request=%r actions=%s",
            message,
            [(r.device_id, r.intent, r.status) for r in results],
        )
        return response


def _outcome(results: list[ActionResult], plan_valid: bool) -> str:
    if not plan_valid:
        return "No actions were executed."
    if not results:
        return "No device actions were needed."
    counts = {status: sum(r.status is status for r in results) for status in ActionStatus}
    parts = [
        f"{counts[ActionStatus.EXECUTED]} executed" if counts[ActionStatus.EXECUTED] else "",
        f"{counts[ActionStatus.ANSWERED]} answered" if counts[ActionStatus.ANSWERED] else "",
        f"{counts[ActionStatus.REJECTED]} rejected" if counts[ActionStatus.REJECTED] else "",
        f"{counts[ActionStatus.FAILED]} failed" if counts[ActionStatus.FAILED] else "",
        f"{counts[ActionStatus.AWAITING_CONFIRMATION]} awaiting confirmation"
        if counts[ActionStatus.AWAITING_CONFIRMATION]
        else "",
        f"{counts[ActionStatus.CANCELLED]} cancelled" if counts[ActionStatus.CANCELLED] else "",
    ]
    return ", ".join(p for p in parts if p).capitalize() + "."


def _raw_field(raw: object, name: str) -> str | None:
    value = raw.get(name) if isinstance(raw, dict) else None
    return value if isinstance(value, str) else None
