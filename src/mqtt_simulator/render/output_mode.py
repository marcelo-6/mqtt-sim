"""Output mode resolution for CLI `run`."""

from __future__ import annotations

from enum import StrEnum

from ..errors import ConfigValidationError


class OutputMode(StrEnum):
    """Supported runtime output modes."""

    AUTO = "auto"
    TABLE = "table"
    LOG = "log"


def resolve_output_mode(requested: str, *, is_tty: bool) -> OutputMode:
    """Resolve ``auto`` to ``table`` or ``log`` based on terminal interactivity."""

    try:
        mode = OutputMode(requested)
    except ValueError as exc:
        raise ConfigValidationError(f"Unsupported output mode '{requested}'.") from exc
    if mode is OutputMode.AUTO:
        return OutputMode.TABLE if is_tty else OutputMode.LOG
    return mode
