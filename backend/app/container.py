"""Composition root: the one place that wires concrete implementations together."""

import logging
from dataclasses import dataclass
from datetime import timedelta

from app.ai.agent import HomeAgent
from app.ai.history import InMemoryAgentHistory
from app.ai.providers import AIProvider, AIProviderError, MockAIProvider, UnavailableAIProvider
from app.ai.tools import AgentTools
from app.ai.validation import PlanValidator
from app.config import Settings
from app.devices.factory import build_device
from app.devices.registry import DeviceRegistry
from app.domain.command_service import CommandService
from app.domain.home_state import HomeState
from app.domain.intents import IntentResolver
from app.domain.policy import SecurityPolicy
from app.events.store import EventStore, InMemoryEventStore
from app.gestures.history import GestureHistory, InMemoryGestureHistory
from app.gestures.service import GestureService
from app.ml.service import MLService, train_models
from app.sensors.simulated import SimulatedSensorProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Container:
    settings: Settings
    home_state: HomeState
    event_store: EventStore
    command_service: CommandService
    gesture_history: GestureHistory
    gesture_service: GestureService
    agent: HomeAgent
    agent_history: InMemoryAgentHistory
    ml_service: MLService | None


def build_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "anthropic":
        try:
            # Imported lazily so the SDK is only needed when the real provider is selected.
            from app.ai.providers.anthropic_provider import AnthropicProvider

            return AnthropicProvider(
                model=settings.ai_model,
                api_key=settings.ai_api_key.get_secret_value() if settings.ai_api_key else None,
                effort=settings.ai_effort,
                max_tool_rounds=settings.ai_max_tool_rounds,
                timeout_s=settings.ai_timeout_s,
            )
        except AIProviderError as exc:
            # A misconfigured AI provider must not take down device control.
            logger.error("AI provider unavailable: %s", exc)
            return UnavailableAIProvider(settings.ai_provider, settings.ai_model, str(exc))
    return MockAIProvider()


def build_ml_service(settings: Settings, home_state: HomeState, event_store: EventStore) -> MLService | None:
    if not settings.ml_enabled:
        return None
    try:
        models = train_models(settings.ml_seed, settings.ml_dataset_days, settings.ml_prediction_threshold)
    except Exception:  # ML is an add-on: never let it take down device control
        logger.exception("ML models failed to train; ML features are disabled.")
        return None
    return MLService(
        home_state, event_store, models, active_window=timedelta(minutes=settings.ml_anomaly_active_minutes)
    )


def build_container(settings: Settings, *, ai_provider: AIProvider | None = None) -> Container:
    latency_s = settings.virtual_device_latency_ms / 1000
    registry = DeviceRegistry(build_device(config, virtual_latency_s=latency_s) for config in settings.devices)
    home_state = HomeState(registry, SimulatedSensorProvider(seed=settings.sensor_seed))
    event_store = InMemoryEventStore(max_size=settings.event_log_max_size)
    command_service = CommandService(home_state, event_store)
    resolver = IntentResolver()

    gesture_history = InMemoryGestureHistory(max_size=settings.gesture_history_max_size)
    gesture_service = GestureService(
        home_state,
        command_service,
        gesture_history,
        resolver=resolver,
        confidence_threshold=settings.gesture_confidence_threshold,
        blocked_actions=settings.gesture_blocked_actions,
    )

    ml_service = build_ml_service(settings, home_state, event_store)

    agent_history = InMemoryAgentHistory(max_size=settings.ai_history_max_size)
    agent = HomeAgent(
        provider=ai_provider or build_ai_provider(settings),
        tools=AgentTools(home_state, event_store, command_service, ml_service),
        validator=PlanValidator(registry, resolver, SecurityPolicy(allow_ai_unlock=settings.ai_allow_unlock)),
        history=agent_history,
        timeout_s=settings.ai_request_timeout_s,
    )

    return Container(
        settings=settings,
        home_state=home_state,
        event_store=event_store,
        command_service=command_service,
        gesture_history=gesture_history,
        gesture_service=gesture_service,
        agent=agent,
        agent_history=agent_history,
        ml_service=ml_service,
    )
