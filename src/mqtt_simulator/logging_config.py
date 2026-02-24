"""Logging configuration helpers for CLI commands and runtime execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_DIR = Path(".mqtt-sim/logs")
DEFAULT_LOG_FILE = "mqtt-sim.log"


@dataclass(slots=True)
class LoggingContext:
    """Metadata about the configured logging session."""

    log_path: Path
    logger: logging.Logger


def configure_logging(
    *,
    verbose: bool,
    output_mode: str,
    log_dir: Path | None = None,
) -> LoggingContext:
    """Configure logging without polluting table-mode console output.

    Args:
        verbose: If true, set the root level to ``DEBUG``; otherwise use ``INFO``.
        output_mode: The resolved output mode (`table` or `log`), recorded in the
            startup log entry for easier troubleshooting.
        log_dir: Optional log directory override (useful in tests).

    Returns:
        A ``LoggingContext`` containing the resolved log path and an application logger.
    """

    target_dir = (log_dir or DEFAULT_LOG_DIR).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / DEFAULT_LOG_FILE

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    handler = RotatingFileHandler(
        log_path,
        maxBytes=512 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(handler)

    logger = logging.getLogger("mqtt_simulator")
    logger.debug(
        "Logging configured", extra={"output_mode": output_mode, "verbose": verbose}
    )
    return LoggingContext(log_path=log_path, logger=logger)


def shutdown_logging() -> None:
    """Flush and close logging handlers."""

    logging.shutdown()
