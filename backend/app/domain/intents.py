"""Device-agnostic intents and their resolution to concrete device commands.

An intent says *what* the user wants ("turn it on") without naming a device action.
Gesture control emits intents today; voice control or the AI agent can emit the same
intents later. Resolution is capability-based: it looks at the actions the target
device's spec supports and at its current state, never at the concrete device class.
"""

from enum import StrEnum
from typing import Any

from app.devices.base import Device
from app.devices.commands import DeviceCommand
from app.domain.errors import IntentNotApplicableError


class Intent(StrEnum):
    TURN_ON = "TURN_ON"
    TURN_OFF = "TURN_OFF"
    STOP = "STOP"
    SELECT = "SELECT"
    TOGGLE = "TOGGLE"
    NONE = "NONE"


# Intents that choose a target rather than change a device.
TARGETING_INTENTS = frozenset({Intent.SELECT})

# For each intent, the device actions that fulfil it, in order of preference.
_ACTION_CANDIDATES: dict[Intent, tuple[str, ...]] = {
    Intent.TURN_ON: ("turn_on", "lock"),
    Intent.TURN_OFF: ("turn_off", "unlock"),
    # STOP brings a device to its safe resting state: powered devices off, locks locked.
    Intent.STOP: ("turn_off", "lock"),
}

# Binary state fields TOGGLE can flip: (field, action when True, action when False).
_TOGGLES: tuple[tuple[str, str, str], ...] = (
    ("is_on", "turn_off", "turn_on"),
    ("is_locked", "unlock", "lock"),
)


class IntentResolver:
    """Translates an intent into the command that fulfils it on a given device."""

    def resolve(self, intent: Intent, device: Device) -> DeviceCommand | None:
        """Return the command for ``intent`` on ``device``, or ``None`` for targeting intents."""
        if intent in TARGETING_INTENTS:
            return None

        supported = set(device.spec.supported_actions)
        if intent is Intent.TOGGLE:
            action = _toggle_action(device.get_state(), supported)
        else:
            action = next((a for a in _ACTION_CANDIDATES.get(intent, ()) if a in supported), None)

        if action is None:
            raise IntentNotApplicableError(intent, device.id)
        return DeviceCommand(action=action)


def _toggle_action(state: dict[str, Any], supported: set[str]) -> str | None:
    for field, when_true, when_false in _TOGGLES:
        if field in state:
            action = when_true if state[field] else when_false
            if action in supported:
                return action
    return None
