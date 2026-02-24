"""Asyncio runtime engine that schedules and publishes many streams."""

from __future__ import annotations

import asyncio
import heapq
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from ..config.models import BrokerConfig
from ..errors import BrokerPublishError
from ..mqtt.adapter import BrokerAdapter
from .clock import Clock, SystemClock
from .models import (
    Renderer,
    RuntimeResult,
    RuntimeSnapshot,
    RuntimeStream,
    StreamStatus,
)
from .status import build_snapshot

AdapterFactory = Callable[[BrokerConfig], BrokerAdapter]


@dataclass(slots=True)
class SimulationEngine:
    """Run a simulation by scheduling streams and publishing through broker adapters."""

    brokers: dict[str, BrokerConfig]
    streams: list[RuntimeStream]
    adapter_factory: AdapterFactory
    renderer: Renderer
    logger: logging.Logger
    fail_fast: bool = False
    duration: float | None = None
    clock: Clock = field(default_factory=SystemClock)

    async def run(self) -> RuntimeResult:
        """Execute the simulation and return the final runtime result."""

        started_mono = self.clock.monotonic()
        started_wall = self.clock.time()
        statuses = [
            StreamStatus(
                stream_id=stream.stream_id, topic=stream.topic, interval=stream.interval
            )
            for stream in self.streams
        ]
        status_by_id = {status.stream_id: status for status in statuses}
        total_publishes = 0
        total_errors = 0
        failed_fast = False
        adapters: dict[str, BrokerAdapter] = {}
        renderer_started = False
        fatal_exception: Exception | None = None

        async def emit_update() -> RuntimeSnapshot:
            nonlocal renderer_started
            snapshot = build_snapshot(
                started_at=started_wall,
                now=self.clock.time(),
                statuses=statuses,
                total_publishes=total_publishes,
                total_errors=total_errors,
            )
            if not renderer_started:
                self.renderer.start(snapshot)
                renderer_started = True
            else:
                self.renderer.update(snapshot)
            return snapshot

        try:
            for broker_name, broker in self.brokers.items():
                adapter = self.adapter_factory(broker)
                adapters[broker_name] = adapter
                self.logger.info(
                    "Connecting broker '%s' (%s:%s)",
                    broker.name,
                    broker.host,
                    broker.port,
                )
                await adapter.connect()
            await emit_update()

            due_heap: list[tuple[float, int]] = []
            now_mono = self.clock.monotonic()
            for index, _stream in enumerate(self.streams):
                heapq.heappush(due_heap, (now_mono, index))

            while due_heap:
                now_mono = self.clock.monotonic()
                if (
                    self.duration is not None
                    and (now_mono - started_mono) >= self.duration
                ):
                    break

                due_at, stream_index = heapq.heappop(due_heap)
                if due_at > now_mono:
                    remaining = due_at - now_mono
                    if self.duration is not None:
                        time_left = max(0.0, self.duration - (now_mono - started_mono))
                        remaining = min(remaining, time_left)
                    if remaining > 0:
                        await asyncio.sleep(remaining)
                    now_mono = self.clock.monotonic()
                    if (
                        self.duration is not None
                        and (now_mono - started_mono) >= self.duration
                    ):
                        break

                stream = self.streams[stream_index]
                status = status_by_id[stream.stream_id]
                status.state = "running"
                status.last_error = ""

                try:
                    build_result = stream.payload_builder.build()
                    adapter = adapters[stream.broker_name]
                    await adapter.publish(
                        stream.topic,
                        build_result.payload_bytes,
                        qos=stream.qos,
                        retain=stream.retain,
                    )
                    total_publishes += 1
                    status.publish_count += 1
                    status.last_publish_ts = self.clock.time()
                    status.last_payload_preview = build_result.preview
                    status.state = "ok"
                    self.logger.debug(
                        "Published stream_id=%s topic=%s bytes=%d",
                        stream.stream_id,
                        stream.topic,
                        len(build_result.payload_bytes),
                    )
                except BrokerPublishError as exc:
                    total_errors += 1
                    status.error_count += 1
                    status.state = "error"
                    status.last_error = str(exc)
                    self.logger.error("Publish error for %s: %s", stream.stream_id, exc)
                    if self.fail_fast:
                        failed_fast = True
                except Exception as exc:
                    total_errors += 1
                    status.error_count += 1
                    status.state = "error"
                    status.last_error = str(exc)
                    self.logger.exception(
                        "Unhandled stream error for %s", stream.stream_id
                    )
                    if self.fail_fast:
                        failed_fast = True

                if failed_fast:
                    await emit_update()
                    break

                next_due = self.clock.monotonic() + stream.interval
                heapq.heappush(due_heap, (next_due, stream_index))
                await emit_update()
        except Exception as exc:
            fatal_exception = exc
            raise

        finally:
            for status in statuses:
                if status.state not in {"error"}:
                    status.state = "stopped"

            for adapter in adapters.values():
                try:
                    await adapter.close()
                except Exception:  # pragma: no cover
                    self.logger.exception("Error closing broker adapter")

            snapshot = build_snapshot(
                started_at=started_wall,
                now=self.clock.time(),
                statuses=statuses,
                total_publishes=total_publishes,
                total_errors=total_errors,
            )
            result = RuntimeResult(
                exit_code=1 if (failed_fast or fatal_exception is not None) else 0,
                total_publishes=total_publishes,
                total_errors=total_errors,
                failed_fast=failed_fast,
                duration_seconds=max(0.0, self.clock.monotonic() - started_mono),
            )
            try:
                if fatal_exception is not None and not renderer_started:
                    pass
                elif renderer_started:
                    self.renderer.finish(snapshot, result)
                else:
                    self.renderer.start(snapshot)
                    self.renderer.finish(snapshot, result)
            finally:
                self.renderer.close()

        return result
