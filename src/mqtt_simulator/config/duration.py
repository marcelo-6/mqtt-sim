"""Duration parsing and formatting helpers for config and runtime models."""

from __future__ import annotations

import re

_DURATION_RE = re.compile(r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|s|m|h)\s*$")
_DURATION_MULTIPLIER = {
    "ms": 0.001,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
}


def parse_duration(
    value: object, *, field_name: str, allow_zero: bool = False
) -> float:
    """Return a duration in seconds from a numeric or string input."""

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a duration string or number")

    seconds: float
    if isinstance(value, int | float):
        seconds = float(value)
    elif isinstance(value, str):
        match = _DURATION_RE.match(value)
        if match is None:
            raise ValueError(
                f"{field_name} must be a number of seconds or a duration like 500ms, 1s, 5m"
            )
        amount = float(match.group("value"))
        unit = match.group("unit")
        seconds = amount * _DURATION_MULTIPLIER[unit]
    else:
        raise ValueError(f"{field_name} must be a duration string or number")

    if seconds < 0 or (seconds == 0 and not allow_zero):
        comparator = ">= 0" if allow_zero else "> 0"
        raise ValueError(f"{field_name} must be {comparator}")
    return seconds


def parse_keepalive(value: object) -> int:
    """Return a keepalive interval in whole seconds."""

    seconds = parse_duration(value, field_name="keepalive")
    if not float(seconds).is_integer():
        raise ValueError("keepalive must resolve to a whole number of seconds")
    return int(seconds)


def format_duration(seconds: float) -> str:
    """Format seconds into a compact duration string."""

    if seconds < 1:
        milliseconds = round(seconds * 1000)
        return f"{milliseconds}ms"
    if seconds < 60:
        whole = round(seconds)
        if abs(seconds - whole) < 1e-9:
            return f"{whole}s"
        return f"{seconds:.2f}".rstrip("0").rstrip(".") + "s"
    if seconds < 3600 and abs(seconds % 60) < 1e-9:
        return f"{int(seconds // 60)}m"
    if abs(seconds % 3600) < 1e-9:
        return f"{int(seconds // 3600)}h"
    return f"{seconds:.2f}".rstrip("0").rstrip(".") + "s"
