"""Asyncio runtime engine that schedules and publishes many streams."""

from __future__ import annotations

import asyncio
import heapq
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field

from ..errors import BrokerPublishError
from ..mqtt.adapter import BrokerAdapter
from .clock import Clock, SystemClock
from .models import (
    Renderer,
    RuntimeClient,
    RuntimeResult,
    RuntimeSnapshot,
    RuntimeStream,
    StreamStatus,
)
from .status import build_snapshot

AdapterFactory = Callable[[RuntimeClient], BrokerAdapter]


@dataclass(slots=True)
class _ScheduleState:
    """Mutable timing state for one runtime stream."""

    jitter_rng: random.Random = field(default_factory=random.Random)
    burst_emitted: int = 0
    cycle_anchor: float | None = None


@dataclass(slots=True)
class SimulationEngine:
    """Run a simulation by scheduling streams and publishing through client adapters."""

    clients: dict[str, RuntimeClient]
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
                stream_id=stream.stream_id,
                topic=stream.topic,
                schedule_label=stream.schedule.label,
            )
            for stream in self.streams
        ]
        status_by_id = {status.stream_id: status for status in statuses}
        total_publishes = 0
        total_errors = 0
        failed_fast = False
        adapters: dict[str, BrokerAdapter] = {}
        connected_clients: list[str] = []
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
            for session_id, client in self.clients.items():
                adapter = self.adapter_factory(client)
                adapters[session_id] = adapter
                self.logger.info(
                    "Connecting client '%s' to broker '%s' (%s:%s)",
                    client.client_id,
                    client.broker.name,
                    client.broker.host,
                    client.broker.port,
                )
                await adapter.connect()
                connected_clients.append(session_id)
                total_publishes, total_errors, failed_fast = await self._publish_lifecycle(
                    client=client,
                    event="online",
                    adapter=adapter,
                    total_publishes=total_publishes,
                    total_errors=total_errors,
                    failed_fast=failed_fast,
                )
                if failed_fast:
                    break

            await emit_update()

            if failed_fast:
                raise BrokerPublishError("Client lifecycle publish failed during startup.")

            due_heap: list[tuple[float, int]] = []
            schedule_states: list[_ScheduleState] = []
            now_mono = self.clock.monotonic()
            for index, stream in enumerate(self.streams):
                schedule_states.append(
                    _ScheduleState(
                        jitter_rng=random.Random(hash(stream.stream_id) & 0xFFFFFFFFFFFF)
                    )
                )
                heapq.heappush(due_heap, (now_mono, index))

            while due_heap:
                now_mono = self.clock.monotonic()
                if self.duration is not None and (now_mono - started_mono) >= self.duration:
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
                    if self.duration is not None and (now_mono - started_mono) >= self.duration:
                        break

                stream = self.streams[stream_index]
                status = status_by_id[stream.stream_id]
                status.state = "running"
                status.last_error = ""

                try:
                    build_result = stream.payload_builder.build()
                    adapter = adapters[stream.client_session_id]
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
                    self.logger.exception("Unhandled stream error for %s", stream.stream_id)
                    if self.fail_fast:
                        failed_fast = True

                if failed_fast:
                    await emit_update()
                    break

                next_due = _next_due(
                    stream=stream,
                    state=schedule_states[stream_index],
                    due_at=due_at,
                    now=self.clock.monotonic(),
                )
                heapq.heappush(due_heap, (next_due, stream_index))
                await emit_update()
        except Exception as exc:
            fatal_exception = exc
            raise
        finally:
            for status in statuses:
                if status.state not in {"error"}:
                    status.state = "stopped"

            for session_id in connected_clients:
                client = self.clients[session_id]
                adapter = adapters.get(session_id)
                if adapter is None:
                    continue
                try:
                    total_publishes, total_errors, _ = await self._publish_lifecycle(
                        client=client,
                        event="offline",
                        adapter=adapter,
                        total_publishes=total_publishes,
                        total_errors=total_errors,
                        failed_fast=False,
                    )
                except Exception:  # pragma: no cover - defensive cleanup
                    self.logger.exception(
                        "Error publishing offline lifecycle for client '%s'",
                        client.client_id,
                    )

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

    async def _publish_lifecycle(
        self,
        *,
        client: RuntimeClient,
        event: str,
        adapter: BrokerAdapter,
        total_publishes: int,
        total_errors: int,
        failed_fast: bool,
    ) -> tuple[int, int, bool]:
        """Publish one lifecycle message if the client defines it."""

        message = client.lifecycle.get(event)
        if message is None:
            return total_publishes, total_errors, failed_fast

        try:
            build_result = message.payload_builder.build()
            await adapter.publish(
                message.topic,
                build_result.payload_bytes,
                qos=message.qos,
                retain=message.retain,
            )
            total_publishes += 1
        except BrokerPublishError as exc:
            total_errors += 1
            self.logger.error(
                "Lifecycle publish error for client '%s' event=%s: %s",
                client.client_id,
                event,
                exc,
            )
            if self.fail_fast:
                failed_fast = True
        return total_publishes, total_errors, failed_fast


def _next_due(
    *,
    stream: RuntimeStream,
    state: _ScheduleState,
    due_at: float,
    now: float,
) -> float:
    """Return the next scheduled publish time for one stream."""

    schedule = stream.schedule
    if schedule.mode == "burst":
        count = schedule.burst_count or 1
        spacing = schedule.burst_spacing or 0.0
        if state.burst_emitted == 0:
            state.cycle_anchor = due_at
        state.burst_emitted += 1
        if state.burst_emitted < count:
            return now + spacing
        state.burst_emitted = 0
        anchor = state.cycle_anchor if state.cycle_anchor is not None else due_at
        state.cycle_anchor = None
        return anchor + schedule.every

    interval = max(0.0, schedule.every + _jitter_offset(schedule.jitter, state.jitter_rng))
    if schedule.mode == "fixed-rate":
        return due_at + interval
    return now + interval


def _jitter_offset(jitter: float | None, rng: random.Random) -> float:
    """Return one signed jitter offset for a schedule interval."""

    if jitter is None or jitter <= 0:
        return 0.0
    return rng.uniform(-jitter, jitter)
