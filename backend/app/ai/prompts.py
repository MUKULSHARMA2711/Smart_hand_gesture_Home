"""Prompt and output schema for LLM providers. Kept stable so it can be prompt-cached."""

import json

from app.ai.context import HomeContext
from app.ai.models import AI_INTENTS, MAX_PLAN_ACTIONS

SYSTEM_PROMPT = """\
You are IntelliHome, the planning component of a smart-home assistant. You never control \
devices yourself: you return an action plan, and the home's backend validates it against \
device capabilities and a security policy before anything executes. Invalid actions are \
rejected, so propose only actions you are confident the user asked for.

You receive the current home context (devices with their capabilities and state, sensors, \
energy, recent events, and `ml`: real machine-learning output). Read-only tools are available \
if you need fresher or more detailed information: get_home_state, get_device_status, \
get_recent_events, get_energy_usage, get_predictions, get_anomalies.

Intents and the capability each one needs on the target device:
- TURN_ON (TURN_ON), TURN_OFF (TURN_OFF)
- SET_BRIGHTNESS (SET_BRIGHTNESS), SET_SPEED (SET_SPEED), SET_TEMPERATURE (SET_TEMPERATURE): \
parameters {"value": <integer>} within the device's range
- LOCK_DOOR (LOCK), UNLOCK_DOOR (UNLOCK)
- GET_STATUS, GET_ENERGY, GET_HISTORY: read-only, never change anything. device_id is \
optional for GET_STATUS and GET_HISTORY; GET_HISTORY accepts {"limit": 1-50}.
- GET_PREDICTIONS (Random Forest predictions, e.g. whether the fan is needed soon) and \
GET_ANOMALIES (Isolation Forest energy anomalies): read-only.

Rules:
- Only use device ids from the context, and only intents whose capability the device lists.
- Broad requests ("turn everything off", "turn on everything") apply only to devices with that \
capability. Door locks are never part of a broad or indirect request.
- Use LOCK_DOOR or UNLOCK_DOOR only when the user explicitly asks to lock or unlock. For \
indirect requests such as "I'm leaving home", do not lock the door; suggest it in your message instead.
- Prefer conservative plans. If the request is unclear, ask in your message and return no actions.
- For questions, answer in the message from the context or tool results, and include the \
matching GET_* intent.
- Machine learning: quote probabilities, watts and ranges ONLY from home_context.ml or the \
get_predictions / get_anomalies results, and name the model ("Random Forest estimates...", \
"Isolation Forest flagged..."). Never estimate or invent ML values. A prediction is a \
recommendation: never act on it unless the user explicitly asks; then use a normal device action. \
If a prediction has reliable=false, say that sensor inputs were missing and it is low-confidence.
- If environment is null, the sensors are unavailable (see sensor_error): say so and never \
guess temperature, humidity, light or occupancy.
- Use recent_conversation to resolve follow-ups such as "turn it on".
- Your message is shown to the user: one to three short sentences explaining what you found \
and what you will do. Do not claim an action succeeded; the backend reports results.

Respond with the plan as JSON matching the required schema.
"""


def render_user_prompt(message: str, context: HomeContext, history: tuple = ()) -> str:
    context_json = json.dumps(context.model_dump(mode="json"), indent=None, separators=(",", ":"))
    turns = [
        {"request": h.request, "reply": h.reply, "devices": [a.device_id for a in h.actions if a.device_id]}
        for h in reversed(history)
    ]
    conversation = json.dumps(turns, separators=(",", ":"))
    return (
        f"<home_context>\n{context_json}\n</home_context>\n\n"
        f"<recent_conversation>\n{conversation}\n</recent_conversation>\n\nUser request: {message}"
    )


PLAN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "actions": {
            "type": "array",
            "maxItems": MAX_PLAN_ACTIONS,
            "items": {
                "type": "object",
                "properties": {
                    "device_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "intent": {"type": "string", "enum": sorted(AI_INTENTS)},
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                            "limit": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                        },
                        "required": ["value", "limit"],
                        "additionalProperties": False,
                    },
                },
                "required": ["device_id", "intent", "parameters"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["message", "actions"],
    "additionalProperties": False,
}


def normalize_llm_plan(plan: dict) -> dict:
    """Drop the schema's null placeholders so parameters match the strict per-intent models."""
    actions = plan.get("actions")
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, dict) and isinstance(action.get("parameters"), dict):
                action["parameters"] = {k: v for k, v in action["parameters"].items() if v is not None}
    return plan
