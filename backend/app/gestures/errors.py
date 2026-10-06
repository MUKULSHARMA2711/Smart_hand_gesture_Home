from app.domain.errors import DomainError


class GestureRejectedError(DomainError):
    """A gesture command refused before any device command was attempted."""

    code = "gesture_rejected"


class GestureNotActionableError(GestureRejectedError):
    code = "gesture_not_actionable"

    def __init__(self, gesture: str) -> None:
        super().__init__(f"Gesture '{gesture}' does not map to an actionable intent.", details={"gesture": gesture})


class GestureIntentMismatchError(GestureRejectedError):
    code = "gesture_intent_mismatch"

    def __init__(self, gesture: str, intent: str, expected_intent: str) -> None:
        super().__init__(
            f"Gesture '{gesture}' maps to intent '{expected_intent}', not '{intent}'.",
            details={"gesture": gesture, "intent": intent, "expected_intent": expected_intent},
        )


class LowConfidenceError(GestureRejectedError):
    code = "confidence_below_threshold"

    def __init__(self, confidence: float, threshold: float) -> None:
        super().__init__(
            f"Gesture confidence {confidence:.2f} is below the threshold of {threshold:.2f}.",
            details={"confidence": confidence, "threshold": threshold},
        )


class GestureValueError(GestureRejectedError):
    code = "invalid_gesture_value"

    def __init__(self, intent: str, value: int | None) -> None:
        expected = "needs a value" if value is None else "does not take a value"
        super().__init__(f"Intent '{intent}' {expected}.", details={"intent": intent, "value": value})


class GestureActionBlockedError(GestureRejectedError):
    code = "action_blocked"

    def __init__(self, action: str, device_id: str) -> None:
        super().__init__(
            f"Action '{action}' on device '{device_id}' is not allowed by gesture.",
            details={"action": action, "device_id": device_id},
        )
