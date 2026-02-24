"""Application exception hierarchy for the MQTT simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MqttSimError(Exception):
    """Base class for expected application errors with a stable exit code."""

    message: str
    exit_code: int = 1
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return the user-facing error message."""
        return self.message


class ConfigLoadError(MqttSimError):
    """Raised when reading or parsing a config file fails."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message=message, exit_code=3, details=details)


class ConfigValidationError(MqttSimError):
    """Raised when a config file fails validation."""

    def __init__(
        self,
        message: str,
        *,
        errors: list[str] | None = None,
        **details: Any,
    ) -> None:
        payload = dict(details)
        if errors:
            payload["errors"] = errors
        super().__init__(message=message, exit_code=2, details=payload)


class PayloadBuildError(MqttSimError):
    """Raised when a payload cannot be generated or encoded."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message=message, exit_code=4, details=details)


class BrokerConnectionError(MqttSimError):
    """Raised when connecting to a broker fails."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message=message, exit_code=5, details=details)


class BrokerPublishError(MqttSimError):
    """Raised when a publish operation fails."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message=message, exit_code=5, details=details)


class RuntimeExecutionError(MqttSimError):
    """Raised when the runtime engine cannot continue."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message=message, exit_code=6, details=details)
