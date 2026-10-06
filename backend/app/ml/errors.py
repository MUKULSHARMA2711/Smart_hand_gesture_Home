from app.domain.errors import DomainError


class PredictionNotSupportedError(DomainError):
    code = "prediction_not_supported"

    def __init__(self, device_id: str, supported: list[str]) -> None:
        super().__init__(
            f"No prediction model exists for device '{device_id}'.",
            details={"device_id": device_id, "supported_devices": supported},
        )


class MLUnavailableError(DomainError):
    code = "ml_unavailable"

    def __init__(self, reason: str = "Machine-learning models are not available.") -> None:
        super().__init__(reason)


class InvalidFeatureError(DomainError):
    code = "invalid_features"

    def __init__(self, message: str, errors: list[dict] | None = None) -> None:
        super().__init__(message, details={"errors": errors} if errors else None)
