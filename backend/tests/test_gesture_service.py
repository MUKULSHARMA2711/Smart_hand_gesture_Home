"""Unit tests for intent resolution and the gesture service, without HTTP."""

import pytest

from app.devices.commands import DeviceCommand
from app.devices.registry import DeviceRegistry
from app.devices.virtual import VirtualAC, VirtualDoorLock, VirtualFan, VirtualLight
from app.domain.command_service import CommandService
from app.domain.errors import IntentNotApplicableError
from app.domain.home_state import HomeState
from app.domain.intents import Intent, IntentResolver
from app.events.models import CommandSource, DeviceEvent
from app.events.store import InMemoryEventStore
from app.gestures.errors import LowConfidenceError
from app.gestures.history import InMemoryGestureHistory
from app.gestures.models import Gesture, GestureCommand, GestureOutcome
from app.gestures.service import GestureService
from app.sensors.simulated import SimulatedSensorProvider

pytestmark = pytest.mark.anyio

LIGHT = VirtualLight("light", "Light", "lab")
FAN = VirtualFan("fan", "Fan", "lab")
AC = VirtualAC("ac", "AC", "lab")
DOOR = VirtualDoorLock("door", "Door", "lab")


@pytest.mark.parametrize(
    ("intent", "device", "expected_action"),
    [
        (Intent.TURN_ON, LIGHT, "turn_on"),
        (Intent.TURN_ON, FAN, "turn_on"),
        (Intent.TURN_ON, AC, "turn_on"),
        (Intent.TURN_OFF, AC, "turn_off"),
        (Intent.STOP, FAN, "turn_off"),
        (Intent.TOGGLE, LIGHT, "turn_on"),  # light starts off
        (Intent.LOCK_DOOR, DOOR, "lock"),
        (Intent.UNLOCK_DOOR, DOOR, "unlock"),
    ],
)
async def test_resolver_maps_intents_by_capability(intent: Intent, device, expected_action: str) -> None:
    assert IntentResolver().resolve(intent, device) == DeviceCommand(action=expected_action)


@pytest.mark.parametrize("intent", [Intent.TURN_ON, Intent.TURN_OFF, Intent.STOP, Intent.TOGGLE])
async def test_power_intents_never_resolve_for_the_door(intent: Intent) -> None:
    with pytest.raises(IntentNotApplicableError):
        IntentResolver().resolve(intent, DOOR)


async def test_resolver_returns_no_command_for_targeting_intent() -> None:
    assert IntentResolver().resolve(Intent.SELECT, LIGHT) is None


async def test_resolver_rejects_intent_without_matching_capability() -> None:
    with pytest.raises(IntentNotApplicableError):
        IntentResolver().resolve(Intent.NONE, LIGHT)


class SpyCommandService(CommandService):
    """Real CommandService that also records how it was called."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.calls: list[tuple[str, DeviceCommand, CommandSource]] = []

    async def execute(self, device_id: str, command: DeviceCommand, source: CommandSource) -> DeviceEvent:
        self.calls.append((device_id, command, source))
        return await super().execute(device_id, command, source)


def build_service() -> tuple[GestureService, SpyCommandService, InMemoryGestureHistory, VirtualLight]:
    light = VirtualLight("light", "Light", "lab")
    home = HomeState(DeviceRegistry([light]), SimulatedSensorProvider(seed=1))
    commands = SpyCommandService(home, InMemoryEventStore())
    history = InMemoryGestureHistory()
    return GestureService(home, commands, history, confidence_threshold=0.75), commands, history, light


async def test_gesture_service_executes_through_command_service() -> None:
    service, commands, history, light = build_service()

    result = await service.handle(
        GestureCommand(gesture=Gesture.THUMBS_UP, intent=Intent.TURN_ON, confidence=0.9, target_device_id="light")
    )

    assert commands.calls == [("light", DeviceCommand(action="turn_on"), CommandSource.GESTURE)]
    assert light.state.is_on is True
    assert result.device_event is not None and result.device_event.source is CommandSource.GESTURE
    assert history.recent() == [result.gesture_event]
    assert result.gesture_event.outcome is GestureOutcome.EXECUTED


async def test_low_confidence_never_reaches_command_service() -> None:
    service, commands, history, light = build_service()

    with pytest.raises(LowConfidenceError):
        await service.handle(
            GestureCommand(gesture=Gesture.THUMBS_UP, intent=Intent.TURN_ON, confidence=0.5, target_device_id="light")
        )

    assert commands.calls == []
    assert light.state.is_on is False
    assert history.recent()[0].outcome is GestureOutcome.REJECTED


async def test_select_never_reaches_command_service() -> None:
    service, commands, _, _ = build_service()

    result = await service.handle(
        GestureCommand(gesture=Gesture.ONE_FINGER, intent=Intent.SELECT, confidence=0.9, target_device_id="light")
    )

    assert commands.calls == []
    assert result.device_event is None
    assert result.gesture_event.outcome is GestureOutcome.ACKNOWLEDGED
