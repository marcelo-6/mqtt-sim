"""Shared CLI error helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .errors import MqttSimError


@dataclass(slots=True)
class CliErrorResult:
    """The mapped CLI outcome for an exception."""

    exit_code: int
    message: str


def handle_cli_exception(exc: Exception, logger: logging.Logger) -> CliErrorResult:
    """Map an exception to a user-facing message and exit code.

    Expected application exceptions are logged at warning/error level without
    spamming console traces. Unexpected exceptions are logged with traceback and
    returned as a generic internal error.
    """

    if isinstance(exc, KeyboardInterrupt):
        logger.info("Interrupted by user")
        return CliErrorResult(exit_code=130, message="Interrupted.")

    if isinstance(exc, MqttSimError):
        if exc.exit_code >= 5:
            logger.error("%s", exc.message, extra={"error_details": exc.details})
        else:
            logger.warning("%s", exc.message, extra={"error_details": exc.details})
        return CliErrorResult(exit_code=exc.exit_code, message=exc.message)

    logger.exception("Unexpected error during CLI execution")
    return CliErrorResult(
        exit_code=1, message="Unexpected error. See log file for details."
    )
