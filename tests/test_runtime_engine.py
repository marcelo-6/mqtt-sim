from __future__ import annotations

import asyncio

from mqtt_simulator.config.models import BrokerConfig
from mqtt_simulator.mqtt.fake_adapter import FakeBrokerAdapter
from mqtt_simulator.runtime.engine import SimulationEngine
from mqtt_simulator.runtime.models import RuntimeResult, RuntimeSnapshot, RuntimeStream
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


def _runtime_stream(topic: str, text: str, *, interval: float = 0.01) -> RuntimeStream:
    return RuntimeStream(
        stream_id=topic,
        broker_name="main",
        topic=topic,
        interval=interval,
        qos=0,
        retain=False,
        payload_builder=TextPayloadBuilder(text),
        payload_kind="text",
    )


def test_engine_keep_going_continues_after_stream_error() -> None:
    adapter = FakeBrokerAdapter(fail_topics={"bad/topic"})
    renderer = CollectingRenderer()
    engine = SimulationEngine(
        brokers={"main": BrokerConfig(name="main", host="localhost")},
        streams=[_runtime_stream("ok/topic", "1"), _runtime_stream("bad/topic", "2")],
        adapter_factory=lambda _broker: adapter,
        renderer=renderer,
        logger=__import__("logging").getLogger("test.engine.keep_going"),
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
        brokers={"main": BrokerConfig(name="main", host="localhost")},
        streams=[_runtime_stream("bad/topic", "x")],
        adapter_factory=lambda _broker: adapter,
        renderer=renderer,
        logger=__import__("logging").getLogger("test.engine.fail_fast"),
        fail_fast=True,
        duration=0.05,
    )

    result = asyncio.run(engine.run())

    assert result.exit_code == 1
    assert result.failed_fast is True
    assert result.total_errors >= 1
