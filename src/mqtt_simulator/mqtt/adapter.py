"""MQTT broker adapter protocol used by the runtime engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class PublishResult:
    """Lightweight publish result metadata."""

    message_id: int | None = None


class BrokerAdapter(Protocol):
    """Async protocol implemented by broker publishing adapters."""

    async def connect(self) -> None:
        """Establish the broker connection."""

    async def publish(
        self,
        topic: str,
        payload: bytes,
        *,
        qos: int = 0,
        retain: bool = False,
    ) -> PublishResult:
        """Publish one MQTT message."""

    async def close(self) -> None:
        """Close the broker connection and release resources."""
