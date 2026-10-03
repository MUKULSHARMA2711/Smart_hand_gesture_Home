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
    # Queries (never change a device)
    GET_STATUS = "GET_STATUS"
    GET_ENERGY = "GET_ENERGY"
    GET_HISTORY = "GET_HISTORY"
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

VALUE_INTENTS = frozenset({Intent.SET_BRIGHTNESS, Intent.SET_SPEED, Intent.SET_TEMPERATURE})
QUERY_INTENTS = frozenset({Intent.GET_STATUS, Intent.GET_ENERGY, Intent.GET_HISTORY})
TARGETING_INTENTS = frozenset({Intent.SELECT})


def is_applicable(intent: Intent, device: Device) -> bool:
    """Whether ``device`` declares the capabilities ``intent`` needs."""
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

        if intent is Intent.TOGGLE:
            capability = Capability.TURN_OFF if device.get_state().get("is_on") else Capability.TURN_ON
        else:
            capability = INTENT_CAPABILITIES[intent]

        action = device.spec.action_for(capability)
        return DeviceCommand(action=action, value=value if intent in VALUE_INTENTS else None)

    @staticmethod
    def capability_for(intent: Intent, device: Device) -> Capability:
        """The capability a (resolvable) intent exercises on ``device``."""
        if intent is Intent.TOGGLE:
            return Capability.TURN_OFF if device.get_state().get("is_on") else Capability.TURN_ON
        return INTENT_CAPABILITIES[intent]
