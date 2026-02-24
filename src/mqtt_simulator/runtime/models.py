"""Dataclasses that describe runtime inputs, status snapshots, and outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..config.models import BrokerConfig
from ..mqtt.adapter import PublishResult
from ..sim.payloads import PayloadBuilder, PayloadBuildResult


class Renderer(Protocol):
    """Renderer protocol consumed by the runtime engine."""

    def start(self, snapshot: RuntimeSnapshot) -> None:
        """Initialize rendering for a simulation session."""

    def update(self, snapshot: RuntimeSnapshot) -> None:
        """Refresh the rendered view after state changes."""

    def finish(self, snapshot: RuntimeSnapshot, result: RuntimeResult) -> None:
        """Render final summary information."""

    def close(self) -> None:
        """Release any renderer resources."""


@dataclass(slots=True)
class RuntimeStream:
    """One publish stream bound to a broker and payload builder."""

    stream_id: str
    broker_name: str
    topic: str
    interval: float
    qos: int
    retain: bool
    payload_builder: PayloadBuilder
    payload_kind: str


@dataclass(slots=True)
class BrokerRuntime:
    """Broker config used by the runtime layer."""

    config: BrokerConfig


@dataclass(slots=True)
class StreamStatus:
    """Mutable status for one stream, copied into snapshots for renderers."""

    stream_id: str
    topic: str
    interval: float
    state: str = "pending"
    publish_count: int = 0
    last_publish_ts: float | None = None
    last_payload_preview: str = ""
    last_error: str = ""
    error_count: int = 0


@dataclass(slots=True)
class RuntimeSnapshot:
    """Read-only-ish snapshot of runtime state used by renderers."""

    started_at: float
    now: float
    streams: list[StreamStatus]
    total_publishes: int
    total_errors: int


@dataclass(slots=True)
class RuntimeResult:
    """Outcome summary returned by the runtime engine."""

    exit_code: int
    total_publishes: int
    total_errors: int
    failed_fast: bool = False
    interrupted: bool = False
    duration_seconds: float = 0.0


@dataclass(slots=True)
class PublishWork:
    """A single publish attempt produced by a stream payload builder."""

    build_result: PayloadBuildResult
    publish_result: PublishResult | None = None
