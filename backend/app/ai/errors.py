from app.domain.errors import DomainError

AI_UNAVAILABLE_MESSAGE = "AI service is currently unavailable."


class AIUnavailableError(DomainError):
    """The AI provider could not produce a plan (missing/invalid key, outage, timeout, bad output).

    Nothing was executed. Device control, gestures and the dashboard do not depend on it.
    """

    code = "ai_unavailable"

    def __init__(self, reason: str, *, interaction_id: str | None = None) -> None:
        super().__init__(AI_UNAVAILABLE_MESSAGE, details={"reason": reason, "interaction_id": interaction_id})
