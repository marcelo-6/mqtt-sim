"""Small clock abstraction used by the runtime engine and tests."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    """Clock protocol for monotonic and wall time access."""

    def monotonic(self) -> float:
        """Return monotonic time in seconds."""

    def time(self) -> float:
        """Return wall time in seconds since epoch."""


class SystemClock:
    """Default clock implementation backed by the Python standard library."""

    def monotonic(self) -> float:
        """Return system monotonic time."""

        return time.monotonic()

    def time(self) -> float:
        """Return system wall-clock time."""

        return time.time()
