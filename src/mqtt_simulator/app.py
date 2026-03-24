"""Tie config, payload builders, and runtime inputs."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path

from .config import (
    ConfigSummary,
    ResolvedClientConfig,
    ResolvedStreamConfig,
    format_summary,
    load_config,
    resolve_simulation,
)
from .config.loaders import summarize_config
from .runtime.models import (
    RuntimeClient,
    RuntimeLifecycleMessage,
    RuntimeSchedule,
    RuntimeStream,
)
from .sim import build_payload_builder
from .sim.payloads import build_payload_builder as build_inline_payload_builder


@dataclass(slots=True)
class PreparedSimulation:
    """Resolved config and runtime stream objects for one simulator run."""

    clients: dict[str, RuntimeClient]
    streams: list[RuntimeStream]
    config_path: Path
    resolved_clients: dict[str, ResolvedClientConfig]
    resolved_streams: list[ResolvedStreamConfig]


def validate_config_file(config_path: Path) -> tuple[ConfigSummary, str]:
    """Validate a config and return a summary object plus formatted text."""

    config = load_config(config_path)
    summary = summarize_config(config)
    return summary, format_summary(summary)


def prepare_simulation(
    config_path: Path,
    *,
    seed: int | None,
    logger: logging.Logger,
) -> PreparedSimulation:
    """Load config, resolve streams, and build runtime payload builders.

    Args:
        config_path: Path to the TOML config file.
        seed: Optional base seed used to derive per-stream RNGs.
        logger: Parent logger used for preparation-time diagnostics.

    Returns:
        A prepared simulation object with resolved runtime client sessions and streams.
    """

    config = load_config(config_path)
    resolved = resolve_simulation(config)
    effective_seed = seed if seed is not None else config.seed
    config_dir = config_path.parent.resolve()
    runtime_clients: dict[str, RuntimeClient] = {}
    for client in resolved.clients.values():
        broker = config.brokers[client.broker_name]
        lifecycle: dict[str, RuntimeLifecycleMessage] = {}
        for event, message in client.lifecycle.items():
            payload_rng = _payload_rng(effective_seed, f"{client.session_id}:{event}")
            builder = build_inline_payload_builder(
                message.payload,
                config_dir=config_dir,
                rng=payload_rng,
            )
            lifecycle[event] = RuntimeLifecycleMessage(
                event=event,
                topic=message.topic,
                qos=message.qos,
                retain=message.retain,
                payload_builder=builder,
                payload_kind=message.payload.kind,
            )
        runtime_clients[client.session_id] = RuntimeClient(
            session_id=client.session_id,
            client_name=client.client_name,
            broker_name=client.broker_name,
            broker=broker,
            client_id=client.client_id,
            clean_session=client.clean_session,
            lifecycle=lifecycle,
        )

    runtime_streams: list[RuntimeStream] = []
    for stream in resolved.streams:
        builder = build_payload_builder(stream, config_dir=config_dir, seed=effective_seed)
        runtime_streams.append(
            RuntimeStream(
                stream_id=stream.stream_id,
                client_session_id=stream.client_session_id,
                topic=stream.topic,
                schedule=RuntimeSchedule(
                    mode=stream.mode,
                    every=stream.every,
                    jitter=stream.jitter,
                    burst_count=stream.burst_count,
                    burst_spacing=stream.burst_spacing,
                    label=stream.schedule_label,
                ),
                qos=stream.qos,
                retain=stream.retain,
                payload_builder=builder,
                payload_kind=stream.payload.kind,
            )
        )
    logger.info(
        "Prepared simulation with %d client sessions and %d streams",
        len(runtime_clients),
        len(runtime_streams),
    )
    return PreparedSimulation(
        clients=runtime_clients,
        streams=runtime_streams,
        config_path=config_path,
        resolved_clients=resolved.clients,
        resolved_streams=resolved.streams,
    )


def _payload_rng(seed: int | None, unique_id: str) -> random.Random:
    """Return a deterministic payload RNG when a base seed is configured."""

    if seed is None:
        return random.Random()
    return random.Random(hash((seed, unique_id)) & 0xFFFFFFFFFFFF)
