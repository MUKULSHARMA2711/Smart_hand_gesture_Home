from app.domain.errors import DomainError

AI_UNAVAILABLE_MESSAGE = "AI service is currently unavailable."


class AIUnavailableError(DomainError):
    """The AI provider could not produce a plan (missing/invalid key, outage, timeout, bad output).

    Nothing was executed. Device control, gestures and the dashboard do not depend on it.
    """

    code = "ai_unavailable"

    def __init__(self, reason: str, *, interaction_id: str | None = None) -> None:
        super().__init__(AI_UNAVAILABLE_MESSAGE, details={"reason": reason, "interaction_id": interaction_id})


class ConfirmationNotFoundError(DomainError):
    code = "confirmation_not_found"

    def __init__(self, confirmation_id: str) -> None:
        super().__init__("There is no pending request with this id.", details={"confirmation_id": confirmation_id})


class ConfirmationExpiredError(DomainError):
    """The confirmation window passed; the held action was cancelled and never executed."""

    code = "confirmation_expired"

    def __init__(self, confirmation_id: str) -> None:
        super().__init__(
            "The confirmation expired, so nothing was unlocked. Ask again if you still want it.",
            details={"confirmation_id": confirmation_id},
        )
