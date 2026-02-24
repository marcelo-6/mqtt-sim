"""Helpers to snapshot runtime stream status for renderers."""

from __future__ import annotations

from dataclasses import replace

from .models import RuntimeSnapshot, StreamStatus


def build_snapshot(
    *,
    started_at: float,
    now: float,
    statuses: list[StreamStatus],
    total_publishes: int,
    total_errors: int,
) -> RuntimeSnapshot:
    """Return a snapshot for renderer consumption."""

    return RuntimeSnapshot(
        started_at=started_at,
        now=now,
        streams=[replace(status) for status in statuses],
        total_publishes=total_publishes,
        total_errors=total_errors,
    )
