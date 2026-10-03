"""Deterministic, rule-based stand-in for an LLM.

Used for tests and for running IntelliHome without an API key. It reads the same
HomeContext a real model receives and returns the same raw plan shape, so its output
goes through exactly the same validation and security policy as an LLM's would.

It is intentionally simple keyword parsing, not a language model.
"""

import re
from typing import Any

from app.ai.context import DeviceContext, HomeContext
from app.ai.providers.base import AIProvider, PlanningRequest
from app.devices.types import Capability, DeviceType
from app.domain.intents import INTENT_CAPABILITIES, Intent

_TYPE_WORDS: dict[DeviceType, tuple[str, ...]] = {
    DeviceType.LIGHT: ("light", "lights", "lamp", "lamps"),
    DeviceType.FAN: ("fan", "fans"),
    DeviceType.AC: ("ac", "a/c", "air conditioner", "air conditioning", "aircon", "air con"),
    DeviceType.DOOR_LOCK: ("door", "doors", "front door", "main door", "entrance"),
}
_VALUE_INTENT_BY_TYPE = {
    DeviceType.LIGHT: Intent.SET_BRIGHTNESS,
    DeviceType.FAN: Intent.SET_SPEED,
    DeviceType.AC: Intent.SET_TEMPERATURE,
}
_VALUE_KEYWORDS = (
    (re.compile(r"\b(brightness|bright|dim)\b"), DeviceType.LIGHT),
    (re.compile(r"\bspeed\b"), DeviceType.FAN),
    (re.compile(r"\b(temperature|degrees?|celsius)\b|°"), DeviceType.AC),
)

_CLAUSE_SPLIT = re.compile(r"\s*(?:[,;.!]|\bthen\b|\band\b|\balso\b)\s*")
_ALL = re.compile(r"\b(everything|every device|all devices|all the devices|all appliances|all)\b")
_CONTROL = re.compile(
    r"\b(turn|switch|power on|power off|shut|set|dim|brighten|lock|unlock|start|stop|adjust|increase|decrease|raise|lower)\b"
)
_LEAVING = re.compile(r"\b(leaving|heading out|going out|leave (the )?(house|home)|i'?m off|goodbye|bye)\b")
_ENERGY = re.compile(r"\b(energy|power|electricity|consum\w*|usage|watts?|kwh|bill)\b")
_HISTORY = re.compile(r"\b(history|recent(ly)?|happened|events?|activity|log)\b")
_STATUS = re.compile(r"\b(status|happening|state|overview|summary|how is|how's|what's on|is the|are the|which)\b|\?")
_UNLOCK = re.compile(r"\bunlock")
_LOCK = re.compile(r"\block")
_OFF = re.compile(r"\b(off|shut|stop)\b")
_ON = re.compile(r"\b(on|start)\b")
_NUMBER = re.compile(r"-?\d+")
_SETTING = re.compile(r"\b(set|dim|brighten|change|make|adjust|put|increase|decrease|raise|lower|to)\b|%")

_HELP = (
    "I'm not sure what you'd like me to do. Try 'turn on the living room light', "
    "'set the fan to 70', 'lock the front door' or 'how much energy are we using?'."
)
_DOOR_NOTE = (
    "I've left the {names} as it is: door locks only change when you explicitly ask me to lock or unlock them."
)


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w/]){re.escape(phrase)}(?![\w/])")


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _format_power(watts: float) -> str:
    return f"{watts / 1000:.2f} kW" if watts >= 1000 else f"{watts:.1f} W"


def describe_state(device: DeviceContext) -> str:
    state = device.state
    match device.type:
        case DeviceType.LIGHT:
            return f"on at {state['brightness']}% brightness" if state["is_on"] else "off"
        case DeviceType.FAN:
            return f"on at {state['speed']}% speed" if state["is_on"] else "off"
        case DeviceType.AC:
            return f"{'on' if state['is_on'] else 'off'}, set to {state['target_temperature_c']} °C"
        case DeviceType.DOOR_LOCK:
            return "locked" if state["is_locked"] else "unlocked"
    return str(state)


class _Planner:
    def __init__(self, context: HomeContext) -> None:
        self.context = context
        self.devices = context.devices
        self.rooms = sorted({device.room for device in self.devices})

    # --- Entry point -------------------------------------------------------------------

    def plan(self, message: str) -> dict[str, Any]:
        text = message.lower().strip()
        has_control = bool(_CONTROL.search(text))
        leaving = bool(_LEAVING.search(text))

        if not has_control and not leaving:
            query = self._query(text)
            if query is not None:
                return query

        notes: list[str] = []
        planned = (self._leaving_actions() if leaving else []) + self._clause_actions(text, notes)
        actions: list[dict[str, Any]] = []
        for action in planned:  # drop duplicates, e.g. "I'm leaving, turn off the lights"
            if action not in actions:
                actions.append(action)
        if leaving and not any(a["intent"] in (Intent.LOCK_DOOR, Intent.UNLOCK_DOOR) for a in actions):
            notes.append(self._leaving_door_note())

        if not actions:
            if leaving:
                return {"message": " ".join(["Everything is already off.", *notes]).strip(), "actions": []}
            return {"message": _HELP, "actions": []}

        return {"message": " ".join([self._describe(actions, leaving), *notes]).strip(), "actions": actions}

    # --- Queries ---------------------------------------------------------------------------

    def _query(self, text: str) -> dict[str, Any] | None:
        if _ENERGY.search(text):
            return {"message": self._energy_summary(), "actions": [{"intent": Intent.GET_ENERGY, "parameters": {}}]}
        if _HISTORY.search(text):
            return {
                "message": self._history_summary(),
                "actions": [{"intent": Intent.GET_HISTORY, "parameters": {"limit": 5}}],
            }
        if _STATUS.search(text):
            targets = self._explicit_targets(text)
            if targets and len(targets) == 1:
                device = targets[0]
                return {
                    "message": f"The {device.name} is {describe_state(device)}, drawing {_format_power(device.power_w)}.",
                    "actions": [{"device_id": device.id, "intent": Intent.GET_STATUS, "parameters": {}}],
                }
            return {"message": self._status_summary(), "actions": [{"intent": Intent.GET_STATUS, "parameters": {}}]}
        return None

    def _status_summary(self) -> str:
        env = self.context.environment
        people = env.occupancy.occupant_count
        occupancy = f"{people} {'person is' if people == 1 else 'people are'} home" if people else "nobody is home"
        devices = _join([f"the {d.name} is {describe_state(d)}" for d in self.devices])
        return (
            f"Here's your home right now: {env.temperature_c} °C with {env.humidity_pct}% humidity, {occupancy}, "
            f"and ambient light is {env.ambient_light_lux:.0f} lux. {devices[0].upper()}{devices[1:]}. "
            f"Total power draw is {_format_power(self.context.energy.total_power_w)}."
        )

    def _energy_summary(self) -> str:
        energy = self.context.energy
        top = max(self.devices, key=lambda d: d.power_w)
        share = 100 * top.power_w / energy.total_power_w if energy.total_power_w else 0
        return (
            f"The home is drawing {_format_power(energy.total_power_w)} right now. The biggest consumer is the "
            f"{top.name} at {_format_power(top.power_w)} ({share:.0f}%). Monitored devices have used "
            f"{energy.energy_kwh * 1000:.1f} Wh since the system started."
        )

    def _history_summary(self) -> str:
        if not self.context.recent_events:
            return "There hasn't been any device activity yet."
        names = {d.id: d.name for d in self.devices}
        entries = [
            f"{e.timestamp:%H:%M:%S} {names.get(e.device_id, e.device_id)} {e.action.replace('_', ' ')} (via {e.source})"
            for e in self.context.recent_events
        ]
        return "Recent activity, newest first: " + "; ".join(entries) + "."

    # --- Control -----------------------------------------------------------------------------

    def _leaving_actions(self) -> list[dict[str, Any]]:
        return [
            {"device_id": d.id, "intent": Intent.TURN_OFF, "parameters": {}}
            for d in self.devices
            if Capability.TURN_OFF in d.capabilities and d.state.get("is_on")
        ]

    def _leaving_door_note(self) -> str:
        doors = [d.name for d in self.devices if Capability.LOCK in d.capabilities]
        if not doors:
            return ""
        return f"I haven't touched the {_join(doors)}. Say 'lock the front door' if you'd like it locked."

    def _clause_actions(self, text: str, notes: list[str]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        last_targets: list[DeviceContext] | None = None
        last_intent: Intent | None = None
        skipped_doors: list[str] = []

        for clause in filter(None, _CLAUSE_SPLIT.split(text)):
            explicit = self._explicit_targets(clause)
            broad = self._broad_targets(clause) if explicit is None else None
            intent, value = self._clause_intent(clause)
            if intent is None and explicit is not None and last_intent is not None and last_intent != "SET":
                intent = last_intent  # "turn on the light and [the] fan"
            if intent is None:
                continue

            if intent == "SET":
                targets = explicit or broad or last_targets or self._keyword_targets(clause)
                for device in targets or []:
                    value_intent = _VALUE_INTENT_BY_TYPE.get(device.type)
                    if value_intent is not None:
                        actions.append({"device_id": device.id, "intent": value_intent, "parameters": {"value": value}})
            else:
                if explicit is not None:
                    targets = explicit  # explicitly named: let the backend judge applicability
                else:
                    candidates = broad or last_targets
                    if candidates is None and intent in (Intent.LOCK_DOOR, Intent.UNLOCK_DOOR):
                        candidates = self.devices
                    capability = INTENT_CAPABILITIES[intent]
                    targets = [d for d in candidates or [] if capability in d.capabilities]
                    skipped_doors += [
                        d.name for d in candidates or [] if d.type is DeviceType.DOOR_LOCK and d not in targets
                    ]
                for device in targets:
                    actions.append({"device_id": device.id, "intent": intent, "parameters": {}})

            last_targets = explicit or broad or last_targets
            last_intent = intent

        if skipped_doors:
            notes.append(_DOOR_NOTE.format(names=_join(sorted(set(skipped_doors)))))
        return actions

    def _clause_intent(self, clause: str) -> tuple[Intent | str | None, int | None]:
        if _UNLOCK.search(clause):
            return Intent.UNLOCK_DOOR, None
        if _LOCK.search(clause):
            return Intent.LOCK_DOOR, None
        number = _NUMBER.search(clause)
        if number and (_SETTING.search(clause) or any(p.search(clause) for p, _ in _VALUE_KEYWORDS)):
            return "SET", int(number.group())
        if _OFF.search(clause):
            return Intent.TURN_OFF, None
        if _ON.search(clause):
            return Intent.TURN_ON, None
        return None, None

    def _explicit_targets(self, clause: str) -> list[DeviceContext] | None:
        """Devices named by type (optionally narrowed by room), or None if no type is named."""
        types = {t for t, words in _TYPE_WORDS.items() if any(_phrase_pattern(w).search(clause) for w in words)}
        if not types:
            return None
        rooms = self._rooms_in(clause)
        return [d for d in self.devices if d.type in types and (not rooms or d.room in rooms)]

    def _broad_targets(self, clause: str) -> list[DeviceContext] | None:
        """'everything' or a whole room. These are filtered by capability, never by guesswork."""
        rooms = self._rooms_in(clause)
        if rooms:
            return [d for d in self.devices if d.room in rooms]
        if _ALL.search(clause):
            return list(self.devices)
        return None

    def _keyword_targets(self, clause: str) -> list[DeviceContext] | None:
        for pattern, device_type in _VALUE_KEYWORDS:
            if pattern.search(clause):
                return [d for d in self.devices if d.type is device_type]
        return None

    def _rooms_in(self, clause: str) -> set[str]:
        return {room for room in self.rooms if _phrase_pattern(room.replace("_", " ")).search(clause)}

    # --- Explanations --------------------------------------------------------------------------

    def _describe(self, actions: list[dict[str, Any]], leaving: bool) -> str:
        devices = {d.id: d for d in self.devices}
        device_ids = list(dict.fromkeys(a["device_id"] for a in actions))
        prefix = "You're heading out, so " if leaving else ""

        if len(device_ids) == 1 and not leaving:
            device = devices[device_ids[0]]
            phrases = _join([_phrase(a["intent"], a["parameters"], None) for a in actions])
            return f"The {device.name} is currently {describe_state(device)}. I'll {phrases}."

        groups: dict[tuple, list[str]] = {}
        for action in actions:
            key = (action["intent"], tuple(sorted(action["parameters"].items())))
            groups.setdefault(key, []).append(devices[action["device_id"]].name)
        clauses = [_phrase(intent, dict(params), _join(names)) for (intent, params), names in groups.items()]
        return f"{prefix}I'll {_join(clauses)}."


def _phrase(intent: Intent, parameters: dict[str, Any], subject: str | None) -> str:
    """Verb phrase for an action. ``subject=None`` refers to an already-named device ("it")."""
    the = f"the {subject}" if subject else "it"
    owner = f"the {subject}'s" if subject else "its"
    value = parameters.get("value")
    match intent:
        case Intent.TURN_ON:
            return f"turn on {the}" if subject else "turn it on"
        case Intent.TURN_OFF:
            return f"turn off {the}" if subject else "turn it off"
        case Intent.SET_BRIGHTNESS:
            return f"set {owner} brightness to {value}%"
        case Intent.SET_SPEED:
            return f"set {owner} speed to {value}%"
        case Intent.SET_TEMPERATURE:
            return f"set {the} to {value} °C"
        case Intent.LOCK_DOOR:
            return f"lock {the}"
        case Intent.UNLOCK_DOOR:
            return f"unlock {the}"
    return f"apply {intent} to {the}"


class MockAIProvider(AIProvider):
    name = "mock"
    model = "rule-based"

    async def plan(self, request: PlanningRequest) -> dict[str, Any]:
        plan = _Planner(request.context).plan(request.message)
        # Serialise enums exactly as an LLM would emit them (plain JSON strings).
        plan["actions"] = [{**a, "intent": str(a["intent"])} for a in plan["actions"]]
        return plan
