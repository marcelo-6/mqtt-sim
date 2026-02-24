"""Helpers for compact payload previews in terminal output."""

from __future__ import annotations

import json
from typing import Any


def truncate_preview(text: str, *, limit: int = 48) -> str:
    """Return a shortened preview string suitable for table cells."""

    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def preview_payload(payload: bytes | str | dict[str, Any], payload_kind: str) -> str:
    """Create a display-safe preview of a payload.

    Binary payloads are summarized as metadata rather than rendered directly.
    """

    if payload_kind == "pickle_file" and isinstance(payload, bytes):
        return f"<pickle {len(payload)}B>"
    if payload_kind in {"bytes", "file"} and isinstance(payload, bytes):
        return f"<bytes {len(payload)}B>"
    if isinstance(payload, bytes):
        return f"<bytes {len(payload)}B>"
    if isinstance(payload, str):
        return truncate_preview(payload)
    return truncate_preview(json.dumps(payload, separators=(",", ":"), default=str))
