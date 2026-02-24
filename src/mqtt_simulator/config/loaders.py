"""JSON config file loading and summary helpers."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from ..errors import ConfigLoadError, ConfigValidationError
from .expand import resolve_streams
from .models import ConfigSummary, SimulatorConfig


def load_config(path: Path) -> SimulatorConfig:
    """Load and validate a simulator config from a JSON file."""

    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigLoadError(f"Config file not found: {path}") from exc
    except OSError as exc:
        raise ConfigLoadError(f"Unable to read config file: {path}") from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ConfigLoadError(
            f"Invalid JSON in config file {path} at line {exc.lineno}, column {exc.colno}"
        ) from exc

    try:
        return SimulatorConfig.model_validate(payload)
    except ValidationError as exc:
        errors = [_format_validation_error(item) for item in exc.errors()]
        message = "Config validation failed."
        if errors:
            message = f"{message} {errors[0]}"
        raise ConfigValidationError(message, errors=errors, path=str(path)) from exc


def summarize_config(config: SimulatorConfig) -> ConfigSummary:
    """Build a compact summary of a validated config."""

    resolved = resolve_streams(config)
    payload_kinds = sorted({stream.payload.kind for stream in config.streams})
    return ConfigSummary(
        broker_count=len(config.brokers),
        stream_template_count=len(config.streams),
        resolved_stream_count=len(resolved),
        payload_kinds=payload_kinds,
    )


def format_summary(summary: ConfigSummary) -> str:
    """Format a config summary for human-readable CLI output."""

    payloads = ", ".join(summary.payload_kinds) if summary.payload_kinds else "-"
    return (
        "Config valid: "
        f"brokers={summary.broker_count} "
        f"stream_templates={summary.stream_template_count} "
        f"resolved_streams={summary.resolved_stream_count} "
        f"payload_kinds=[{payloads}]"
    )


def _format_validation_error(item: dict[str, object]) -> str:
    """Format one pydantic error into a short, readable message."""

    loc = item.get("loc") or ()
    parts: list[str] = []
    for value in loc if isinstance(loc, tuple) else (loc,):
        if isinstance(value, int):
            if not parts:
                parts.append(f"[{value}]")
            else:
                parts[-1] = f"{parts[-1]}[{value}]"
        else:
            parts.append(str(value))
    field_path = ".".join(parts) if parts else "<root>"
    message = str(item.get("msg", "validation error"))
    return f"{field_path}: {message}"
