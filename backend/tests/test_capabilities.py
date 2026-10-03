"""Explicit device capabilities, intent resolution and the security policy."""

import pytest
from fastapi.testclient import TestClient

from app.devices.commands import CommandModel, DeviceCommand, TurnOn
from app.devices.specs.base import DeviceSpec
from app.devices.specs.light import LightState
from app.devices.types import Capability, DeviceType
from app.devices.virtual import VirtualAC, VirtualDoorLock, VirtualFan, VirtualLight
from app.domain.errors import IntentNotApplicableError
from app.domain.intents import Intent, IntentResolver, applicable_devices
from app.domain.policy import SecurityPolicy
from app.events.models import CommandSource

LIGHT = VirtualLight("light", "Light", "lab")
FAN = VirtualFan("fan", "Fan", "lab")
AC = VirtualAC("ac", "AC", "lab")
DOOR = VirtualDoorLock("door", "Door", "lab")
resolver = IntentResolver()


@pytest.mark.parametrize(
    ("device", "expected"),
    [
        (LIGHT, [Capability.TURN_ON, Capability.TURN_OFF, Capability.SET_BRIGHTNESS]),
        (FAN, [Capability.TURN_ON, Capability.TURN_OFF, Capability.SET_SPEED]),
        (AC, [Capability.TURN_ON, Capability.TURN_OFF, Capability.SET_TEMPERATURE]),
        (DOOR, [Capability.LOCK, Capability.UNLOCK]),
    ],
)
def test_each_device_declares_explicit_capabilities(device, expected) -> None:
    assert device.spec.capabilities == expected


def test_capabilities_are_queryable_through_the_api(client: TestClient) -> None:
    devices = {d["id"]: d for d in client.get("/api/v1/devices").json()}
    status = client.get("/api/v1/ai/status").json()

    assert devices["door_main"]["capabilities"] == ["LOCK", "UNLOCK"]
    assert devices["light_living_room"]["capabilities"] == ["TURN_ON", "TURN_OFF", "SET_BRIGHTNESS"]
    assert {d["device_id"]: d["capabilities"] for d in status["devices"]}["door_main"] == ["LOCK", "UNLOCK"]


def test_spec_rejects_two_commands_with_the_same_capability() -> None:
    class AlsoTurnOn(CommandModel):
        capability = Capability.TURN_ON
        action: str = "power_up"

    with pytest.raises(ValueError, match="twice"):
        DeviceSpec(DeviceType.LIGHT, LightState, [TurnOn, AlsoTurnOn])


@pytest.mark.parametrize("device", [LIGHT, FAN, AC])
def test_turn_on_is_valid_for_powered_devices(device) -> None:
    assert resolver.resolve(Intent.TURN_ON, device) == DeviceCommand(action="turn_on")


def test_turn_on_is_invalid_for_the_door() -> None:
    with pytest.raises(IntentNotApplicableError):
        resolver.resolve(Intent.TURN_ON, DOOR)


def test_turn_off_is_invalid_for_the_door() -> None:
    with pytest.raises(IntentNotApplicableError):
        resolver.resolve(Intent.TURN_OFF, DOOR)


def test_lock_door_is_valid_for_the_door() -> None:
    assert resolver.resolve(Intent.LOCK_DOOR, DOOR) == DeviceCommand(action="lock")


def test_unlock_door_is_valid_for_the_door() -> None:
    assert resolver.resolve(Intent.UNLOCK_DOOR, DOOR) == DeviceCommand(action="unlock")


@pytest.mark.parametrize("device", [LIGHT, FAN, AC])
def test_door_intents_are_invalid_for_appliances(device) -> None:
    with pytest.raises(IntentNotApplicableError):
        resolver.resolve(Intent.LOCK_DOOR, device)


def test_value_intents_carry_their_value() -> None:
    assert resolver.resolve(Intent.SET_SPEED, FAN, 70) == DeviceCommand(action="set_speed", value=70)
    with pytest.raises(IntentNotApplicableError):
        resolver.resolve(Intent.SET_SPEED, LIGHT, 70)


@pytest.mark.parametrize("intent", [Intent.TURN_ON, Intent.TURN_OFF, Intent.TOGGLE, Intent.STOP])
def test_broad_power_intents_never_include_the_door(intent: Intent) -> None:
    assert applicable_devices(intent, [LIGHT, FAN, AC, DOOR]) == [LIGHT, FAN, AC]


# --- Security policy -------------------------------------------------------------------------

policy = SecurityPolicy()


@pytest.mark.parametrize(
    ("capability", "utterance"),
    [
        (Capability.LOCK, "Lock the front door"),
        (Capability.LOCK, "please make sure the door is locked"),
        (Capability.UNLOCK, "Unlock the front door"),
    ],
)
def test_policy_allows_explicitly_requested_door_actions(capability, utterance) -> None:
    decision = policy.evaluate(capability=capability, device_id="door", source=CommandSource.AI_AGENT, utterance=utterance)
    assert decision.allowed


@pytest.mark.parametrize(
    ("capability", "utterance"),
    [
        (Capability.LOCK, "I'm leaving home"),
        (Capability.LOCK, "turn everything off"),
        (Capability.UNLOCK, "lock the door"),  # "lock" does not authorise UNLOCK
        (Capability.LOCK, "unlock the door"),  # and "unlock" does not authorise LOCK
        (Capability.UNLOCK, None),
    ],
)
def test_policy_rejects_door_actions_that_were_not_explicitly_requested(capability, utterance) -> None:
    decision = policy.evaluate(capability=capability, device_id="door", source=CommandSource.AI_AGENT, utterance=utterance)
    assert not decision.allowed
    assert decision.code == "not_explicitly_requested"


def test_policy_can_disable_ai_unlocking() -> None:
    decision = SecurityPolicy(allow_ai_unlock=False).evaluate(
        capability=Capability.UNLOCK, device_id="door", source=CommandSource.AI_AGENT, utterance="unlock the door"
    )
    assert (decision.allowed, decision.code) == (False, "unlock_disabled")


def test_policy_ignores_non_security_capabilities_and_other_sources() -> None:
    assert policy.evaluate(capability=Capability.TURN_ON, device_id="fan", source=CommandSource.AI_AGENT).allowed
    assert policy.evaluate(capability=Capability.UNLOCK, device_id="door", source=CommandSource.FRONTEND).allowed


# --- Negation-aware door policy --------------------------------------------------------------

NEGATED_UNLOCK_REQUESTS = [
    "don't unlock the door",
    "do not unlock the door",
    "never unlock the door",
    "I don't want the door unlocked",
    "Don’t unlock the front door",  # typographic apostrophe
    "please do NOT unlock it",
]


@pytest.mark.parametrize("utterance", NEGATED_UNLOCK_REQUESTS)
def test_policy_rejects_negated_unlock_requests(utterance: str) -> None:
    decision = policy.evaluate(capability=Capability.UNLOCK, device_id="door", source=CommandSource.AI_AGENT, utterance=utterance)
    assert (decision.allowed, decision.code) == (False, "not_explicitly_requested")


@pytest.mark.parametrize("utterance", ["don't lock the door", "never lock the front door", "I don't want it locked"])
def test_policy_rejects_negated_lock_requests(utterance: str) -> None:
    decision = policy.evaluate(capability=Capability.LOCK, device_id="door", source=CommandSource.AI_AGENT, utterance=utterance)
    assert not decision.allowed


@pytest.mark.parametrize(
    "utterance",
    [
        "unlock the front door",
        "Unlock the front door please",
        "don't turn on the lights and unlock the door",  # negation belongs to another clause
        "I'm not cold, unlock the door",
    ],
)
def test_policy_allows_non_negated_unlock_requests(utterance: str) -> None:
    decision = policy.evaluate(capability=Capability.UNLOCK, device_id="door", source=CommandSource.AI_AGENT, utterance=utterance)
    assert decision.allowed
