"""Explicit confirmation of security-sensitive AI actions (unlocking a door).

A held action executes only if the user's reply both affirms *and* repeats the request
("yes, unlock it", "confirm"). Any negation or cancel word cancels. A bare "yes" is not
enough: the user is told the exact phrase, and the request stays pending.
"""

import re
from enum import StrEnum
from typing import Any

from app.devices.types import Capability
from app.domain.policy import explicitly_requests

_AFFIRM = re.compile(r"\b(?:yes|yeah|yep|sure|ok(?:ay)?|confirm(?:ed)?|go ahead|do it|proceed)\b")
_CONFIRM_WORD = re.compile(r"\bconfirm(?:ed)?\b")
_CANCEL = re.compile(r"\b(?:no|nope|cancel(?:led)?|abort|stop|never|don'?t|do not|not|keep it locked|leave it)\b")


class Reply(StrEnum):
    CONFIRM = "confirm"
    CANCEL = "cancel"
    AFFIRM_ONLY = "affirm_only"  # "yes" without saying what: ask again
    OTHER = "other"  # a different request: the pending action is dropped


def classify_reply(text: str) -> Reply:
    t = text.lower().replace("’", "'")
    if _CANCEL.search(t):  # any negation wins: never unlock on an ambiguous answer
        return Reply.CANCEL
    if _AFFIRM.search(t):
        explicit = explicitly_requests(t, Capability.UNLOCK) or _CONFIRM_WORD.search(t) is not None
        return Reply.CONFIRM if explicit else Reply.AFFIRM_ONLY
    return Reply.OTHER


class ConfirmationStore:
    """At most one pending confirmation at a time (one household, one assistant)."""

    def __init__(self) -> None:
        self.pending: Any = None  # PendingConfirmation
        self.raw_action: Any = None  # the validated plan action, re-validated on confirmation

    def hold(self, pending: Any, raw_action: Any) -> None:
        self.pending, self.raw_action = pending, raw_action

    def clear(self) -> None:
        self.pending, self.raw_action = None, None
