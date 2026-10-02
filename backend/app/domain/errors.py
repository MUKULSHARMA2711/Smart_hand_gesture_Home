"""Domain errors. The API layer maps these to HTTP responses."""

from typing import Any


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class DeviceNotFoundError(DomainError):
    code = "device_not_found"

    def __init__(self, device_id: str) -> None:
        super().__init__(f"Device '{device_id}' does not exist.", details={"device_id": device_id})


class UnsupportedCommandError(DomainError):
    code = "unsupported_command"

    def __init__(self, device_id: str, action: str, supported_actions: list[str]) -> None:
        super().__init__(
            f"Device '{device_id}' does not support action '{action}'.",
            details={"device_id": device_id, "action": action, "supported_actions": supported_actions},
        )


class InvalidCommandError(DomainError):
    code = "invalid_command"

    def __init__(self, device_id: str, action: str, errors: list[dict[str, str]]) -> None:
        summary = "; ".join(f"{error['field']}: {error['message']}" for error in errors)
        super().__init__(
            f"Invalid '{action}' command for device '{device_id}': {summary}",
            details={"device_id": device_id, "action": action, "errors": errors},
        )


class DeviceUnavailableError(DomainError):
    code = "device_unavailable"

    def __init__(self, device_id: str, status: str) -> None:
        super().__init__(
            f"Device '{device_id}' is {status} and cannot accept commands.",
            details={"device_id": device_id, "status": status},
        )
