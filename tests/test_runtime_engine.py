from __future__ import annotations

import asyncio
import logging

from mqtt_simulator.config.models import BrokerConfig
from mqtt_simulator.mqtt.fake_adapter import FakeBrokerAdapter
from mqtt_simulator.runtime.engine import SimulationEngine
from mqtt_simulator.runtime.models import (
    RuntimeClient,
    RuntimeLifecycleMessage,
    RuntimeResult,
    RuntimeSchedule,
    RuntimeSnapshot,
    RuntimeStream,
)
from mqtt_simulator.sim.payloads import TextPayloadBuilder


class CollectingRenderer:
    """Minimal renderer used to inspect engine snapshots in tests."""

    def __init__(self) -> None:
        self.started = False
        self.finished = False
        self.snapshots: list[RuntimeSnapshot] = []
        self.result: RuntimeResult | None = None

    def start(self, snapshot: RuntimeSnapshot) -> None:
        self.started = True
        self.snapshots.append(snapshot)

    def update(self, snapshot: RuntimeSnapshot) -> None:
        self.snapshots.append(snapshot)

    def finish(self, snapshot: RuntimeSnapshot, result: RuntimeResult) -> None:
        self.finished = True
        self.snapshots.append(snapshot)
        self.result = result

    def close(self) -> None:
        return None


def _runtime_client() -> RuntimeClient:
    broker = BrokerConfig(name="main", host="localhost")
    return RuntimeClient(
        session_id="session-1",
        client_name="main",
        broker_name="main",
        broker=broker,
        client_id="demo-client",
        clean_session=True,
        lifecycle={},
    )


def _runtime_stream(topic: str, text: str, *, every: float = 0.01) -> RuntimeStream:
    return RuntimeStream(
        stream_id=topic,
        client_session_id="session-1",
        topic=topic,
        schedule=RuntimeSchedule(
            mode="fixed-delay",
            every=every,
            jitter=None,
            burst_count=None,
            burst_spacing=None,
            label=f"fixed-delay {every:.2f}s",
        ),
        qos=0,
        retain=False,
        payload_builder=TextPayloadBuilder(text),
        payload_kind="text",
    )


def test_engine_keep_going_continues_after_stream_error() -> None:
    adapter = FakeBrokerAdapter(fail_topics={"bad/topic"})
    renderer = CollectingRenderer()
    engine = SimulationEngine(
        clients={"session-1": _runtime_client()},
        streams=[_runtime_stream("ok/topic", "1"), _runtime_stream("bad/topic", "2")],
        adapter_factory=lambda _client: adapter,
        renderer=renderer,
        logger=logging.getLogger("test.engine.keep_going"),
        fail_fast=False,
        duration=0.05,
    )

    result = asyncio.run(engine.run())

    assert result.exit_code == 0
    assert result.total_errors >= 1
    assert any(item[0] == "ok/topic" for item in adapter.published)
    assert renderer.started and renderer.finished


def test_engine_fail_fast_returns_nonzero() -> None:
    adapter = FakeBrokerAdapter(fail_topics={"bad/topic"})
    renderer = CollectingRenderer()
    engine = SimulationEngine(
        clients={"session-1": _runtime_client()},
        streams=[_runtime_stream("bad/topic", "x")],
        adapter_factory=lambda _client: adapter,
        renderer=renderer,
        logger=logging.getLogger("test.engine.fail_fast"),
        fail_fast=True,
        duration=0.05,
    )

    result = asyncio.run(engine.run())

    assert result.exit_code == 1
    assert result.failed_fast is True
    assert result.total_errors >= 1


def test_engine_publishes_online_and_offline_lifecycle_messages() -> None:
    adapter = FakeBrokerAdapter()
    renderer = CollectingRenderer()
    client = _runtime_client()
    client.lifecycle = {
        "online": RuntimeLifecycleMessage(
            event="online",
            topic="demo/online",
            qos=1,
            retain=True,
            payload_builder=TextPayloadBuilder("up"),
            payload_kind="text",
        ),
        "offline": RuntimeLifecycleMessage(
            event="offline",
            topic="demo/offline",
            qos=1,
            retain=True,
            payload_builder=TextPayloadBuilder("down"),
            payload_kind="text",
        ),
    }
    engine = SimulationEngine(
        clients={"session-1": client},
        streams=[],
        adapter_factory=lambda _client: adapter,
        renderer=renderer,
        logger=logging.getLogger("test.engine.lifecycle"),
        duration=0.01,
    )

    result = asyncio.run(engine.run())

    assert result.exit_code == 0
    assert [topic for topic, *_ in adapter.published] == ["demo/online", "demo/offline"]
