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


class IntentNotApplicableError(DomainError):
    code = "intent_not_applicable"

    def __init__(self, intent: str, device_id: str) -> None:
        super().__init__(
            f"Intent '{intent}' cannot be applied to device '{device_id}'.",
            details={"intent": intent, "device_id": device_id},
        )


class DeviceUnavailableError(DomainError):
    code = "device_unavailable"

    def __init__(self, device_id: str, status: str, *, name: str | None = None, reason: str | None = None) -> None:
        label = name or f"Device '{device_id}'"
        message = f"{label} is {status}." if reason is None else f"{label} is {status}: {reason}"
        super().__init__(message, details={"device_id": device_id, "status": status, "reason": reason})


class DeviceTimeoutError(DomainError):
    """The device did not confirm a command in time. Its last confirmed state is kept."""

    code = "device_timeout"

    def __init__(self, device_id: str, name: str, timeout_s: float, command_id: str) -> None:
        super().__init__(
            f"{name} did not confirm the command within {timeout_s:g} s. Its last confirmed state is unchanged.",
            details={"device_id": device_id, "timeout_s": timeout_s, "command_id": command_id},
        )


class DeviceStateMismatchError(DomainError):
    """The device acknowledged a command with a state that does not reflect it."""

    code = "device_state_mismatch"

    def __init__(self, device_id: str, name: str, expected: dict, reported: dict, command_id: str) -> None:
        super().__init__(
            f"{name} acknowledged the command but reported a different state, so the command failed. "
            "The reported state is shown as the device's actual state.",
            details={"device_id": device_id, "expected": expected, "reported": reported, "command_id": command_id},
        )
