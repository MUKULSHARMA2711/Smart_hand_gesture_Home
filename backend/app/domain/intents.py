"""Device-agnostic intents and their resolution to concrete device commands.

An intent says *what* the user wants ("turn it on") without naming a device action.
Gesture control, the AI agent and (later) voice control all emit these intents.

Resolution is capability-based and unambiguous: every device intent requires exactly
one explicit :class:`Capability`, and a device either declares it or the intent is not
applicable. In particular TURN_ON / TURN_OFF / STOP / TOGGLE require power
capabilities, so they can never lock or unlock a door — only LOCK_DOOR / UNLOCK_DOOR can.
"""

from collections.abc import Iterable
from enum import StrEnum
from typing import Any

from app.devices.base import Device
from app.devices.commands import DeviceCommand
from app.devices.types import Capability
from app.domain.errors import IntentNotApplicableError


class Intent(StrEnum):
    # Device control
    TURN_ON = "TURN_ON"
    TURN_OFF = "TURN_OFF"
    SET_BRIGHTNESS = "SET_BRIGHTNESS"
    SET_SPEED = "SET_SPEED"
    SET_TEMPERATURE = "SET_TEMPERATURE"
    LOCK_DOOR = "LOCK_DOOR"
    UNLOCK_DOOR = "UNLOCK_DOOR"
    TOGGLE = "TOGGLE"
    STOP = "STOP"
    # Set the target's adjustable value, whatever it is (fan speed, AC temperature, brightness).
    # Prepared for the pinch-and-move gesture; no gesture maps to it yet.
    ADJUST = "ADJUST"
    # Queries (never change a device)
    GET_STATUS = "GET_STATUS"
    GET_ENERGY = "GET_ENERGY"
    GET_HISTORY = "GET_HISTORY"
    GET_PREDICTIONS = "GET_PREDICTIONS"  # ML: predictive automation
    GET_ANOMALIES = "GET_ANOMALIES"  # ML: energy anomaly detection
    # Targeting / no-op
    SELECT = "SELECT"
    NONE = "NONE"


# Each device intent needs exactly one capability on the target device.
INTENT_CAPABILITIES: dict[Intent, Capability] = {
    Intent.TURN_ON: Capability.TURN_ON,
    Intent.TURN_OFF: Capability.TURN_OFF,
    Intent.STOP: Capability.TURN_OFF,  # gesture "stop": power off; not applicable to locks
    Intent.SET_BRIGHTNESS: Capability.SET_BRIGHTNESS,
    Intent.SET_SPEED: Capability.SET_SPEED,
    Intent.SET_TEMPERATURE: Capability.SET_TEMPERATURE,
    Intent.LOCK_DOOR: Capability.LOCK,
    Intent.UNLOCK_DOOR: Capability.UNLOCK,
}

# TOGGLE flips power, so it needs both power capabilities (never lock/unlock).
TOGGLE_CAPABILITIES = (Capability.TURN_ON, Capability.TURN_OFF)

# ADJUST resolves to the first of these the device has. Never a lock capability.
ADJUST_CAPABILITIES = (Capability.SET_SPEED, Capability.SET_TEMPERATURE, Capability.SET_BRIGHTNESS)

VALUE_INTENTS = frozenset({Intent.SET_BRIGHTNESS, Intent.SET_SPEED, Intent.SET_TEMPERATURE, Intent.ADJUST})
QUERY_INTENTS = frozenset(
    {Intent.GET_STATUS, Intent.GET_ENERGY, Intent.GET_HISTORY, Intent.GET_PREDICTIONS, Intent.GET_ANOMALIES}
)
TARGETING_INTENTS = frozenset({Intent.SELECT})


def adjust_capability(device: Device) -> Capability | None:
    """The value ADJUST sets on ``device`` (speed for a fan, temperature for an AC...)."""
    return next((c for c in ADJUST_CAPABILITIES if device.spec.supports(c)), None)


def is_applicable(intent: Intent, device: Device) -> bool:
    """Whether ``device`` declares the capabilities ``intent`` needs."""
    if intent is Intent.ADJUST:
        return adjust_capability(device) is not None
    if intent is Intent.TOGGLE:
        return all(device.spec.supports(capability) for capability in TOGGLE_CAPABILITIES)
    capability = INTENT_CAPABILITIES.get(intent)
    return capability is not None and device.spec.supports(capability)


def applicable_devices(intent: Intent, devices: Iterable[Device]) -> list[Device]:
    """The devices a broad request such as "turn on everything" may touch."""
    return [device for device in devices if is_applicable(intent, device)]


class IntentResolver:
    """Translates an intent into the command that fulfils it on a given device."""

    def resolve(self, intent: Intent, device: Device, value: Any = None) -> DeviceCommand | None:
        """Return the command for ``intent`` on ``device``, or ``None`` for targeting intents.

        Raises :class:`IntentNotApplicableError` when the device lacks the capability.
        Value range checks are left to the device spec.
        """
        if intent in TARGETING_INTENTS:
            return None
        if not is_applicable(intent, device):
            raise IntentNotApplicableError(intent, device.id)

        capability = self.capability_for(intent, device)
        action = device.spec.action_for(capability)
        return DeviceCommand(action=action, value=value if intent in VALUE_INTENTS else None)

    @staticmethod
    def capability_for(intent: Intent, device: Device) -> Capability:
        """The capability a (resolvable) intent exercises on ``device``."""
        if intent is Intent.TOGGLE:
            return Capability.TURN_OFF if device.get_state().get("is_on") else Capability.TURN_ON
        if intent is Intent.ADJUST:
            capability = adjust_capability(device)
            assert capability is not None  # callers check is_applicable first
            return capability
        return INTENT_CAPABILITIES[intent]
