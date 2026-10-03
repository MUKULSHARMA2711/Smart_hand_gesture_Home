"""Security policy for device actions requested on someone's behalf.

Security-sensitive capabilities (door LOCK / UNLOCK) are treated differently from
ordinary appliance control. For the AI agent, a door action is only allowed when the
user's *own words* explicitly ask for it — checked here in code, independently of the
LLM, so an indirect request ("I'm leaving home") or a mistaken/manipulated plan can
never lock or unlock the door.

The decision object leaves room for authentication / confirmation in a later phase.
"""

import re
from dataclasses import dataclass

from app.devices.types import Capability
from app.events.models import CommandSource

SECURITY_SENSITIVE_CAPABILITIES = frozenset({Capability.LOCK, Capability.UNLOCK})

_EXPLICIT_WORDING = {
    Capability.LOCK: re.compile(r"\block(?:ed|ing)?\b", re.IGNORECASE),
    Capability.UNLOCK: re.compile(r"\bunlock(?:ed|ing)?\b", re.IGNORECASE),
}

# A negation before the verb in the same clause cancels the request:
# "don't unlock the door", "I don't want the door unlocked", "never unlock it".
_NEGATION = re.compile(
    r"\b(?:don'?t|do not|does not|doesn'?t|did not|didn'?t|never|not|no|shouldn'?t|should not|"
    r"mustn'?t|must not|won'?t|will not|can'?t|cannot|without|avoid|stop)\b"
)
_CLAUSE_BREAK = re.compile(r"[.,;:!?]|\b(?:and|but|then|so|also)\b")


def explicitly_requests(utterance: str, capability: Capability) -> bool:
    """True if the utterance contains a non-negated request for ``capability``."""
    text = utterance.lower().replace("’", "'")
    for match in _EXPLICIT_WORDING[capability].finditer(text):
        clause_start = max((m.end() for m in _CLAUSE_BREAK.finditer(text, 0, match.start())), default=0)
        if not _NEGATION.search(text, clause_start, match.start()):
            return True
    return False


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    code: str | None = None
    reason: str | None = None
    # Reserved for a later phase (e.g. "confirm unlocking the front door?").
    requires_confirmation: bool = False


ALLOW = PolicyDecision(allowed=True)


class SecurityPolicy:
    def __init__(self, *, allow_ai_unlock: bool = True) -> None:
        self._allow_ai_unlock = allow_ai_unlock

    def evaluate(
        self,
        *,
        capability: Capability,
        device_id: str,
        source: CommandSource,
        utterance: str | None = None,
    ) -> PolicyDecision:
        if capability not in SECURITY_SENSITIVE_CAPABILITIES or source is not CommandSource.AI_AGENT:
            return ALLOW

        if capability is Capability.UNLOCK and not self._allow_ai_unlock:
            return PolicyDecision(
                allowed=False,
                code="unlock_disabled",
                reason=f"Unlocking '{device_id}' through the AI assistant is disabled by policy.",
            )
        if not utterance or not explicitly_requests(utterance, capability):
            verb = "unlock" if capability is Capability.UNLOCK else "lock"
            return PolicyDecision(
                allowed=False,
                code="not_explicitly_requested",
                reason=(
                    f"Door actions need an explicit request. Ask me to '{verb} the front door' "
                    f"if you want '{device_id}' {verb}ed."
                ),
            )
        return ALLOW
