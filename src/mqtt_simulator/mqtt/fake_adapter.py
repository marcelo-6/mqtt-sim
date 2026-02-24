"""In-memory fake MQTT adapter used by tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..errors import BrokerConnectionError, BrokerPublishError
from .adapter import PublishResult


@dataclass(slots=True)
class FakeBrokerAdapter:
    """A fake broker adapter that records publishes and can inject failures."""

    fail_connect: bool = False
    fail_topics: set[str] = field(default_factory=set)
    fail_after: int | None = None
    connected: bool = False
    published: list[tuple[str, bytes, int, bool]] = field(default_factory=list)

    async def connect(self) -> None:
        """Simulate connecting to a broker."""

        if self.fail_connect:
            raise BrokerConnectionError("Fake broker connect failed.")
        self.connected = True

    async def publish(
        self,
        topic: str,
        payload: bytes,
        *,
        qos: int = 0,
        retain: bool = False,
    ) -> PublishResult:
        """Record a publish or raise a simulated error."""

        if not self.connected:
            raise BrokerPublishError("Fake broker is not connected.")
        if topic in self.fail_topics:
            raise BrokerPublishError(f"Fake publish failure for topic '{topic}'.")
        if self.fail_after is not None and len(self.published) >= self.fail_after:
            raise BrokerPublishError("Fake publish failure after configured count.")
        self.published.append((topic, payload, qos, retain))
        return PublishResult(message_id=len(self.published))

    async def close(self) -> None:
        """Simulate closing the broker connection."""

        self.connected = False
