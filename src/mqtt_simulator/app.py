"""Tie config, payload builders, and runtime inputs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .config import (
    ConfigSummary,
    ResolvedStreamConfig,
    format_summary,
    load_config,
    resolve_streams,
)
from .config.loaders import summarize_config
from .config.models import BrokerConfig
from .runtime.models import RuntimeStream
from .sim import build_payload_builder


@dataclass(slots=True)
class PreparedSimulation:
    """Resolved config and runtime stream objects for one simulator run."""

    brokers: dict[str, BrokerConfig]
    streams: list[RuntimeStream]
    config_path: Path
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
        config_path: Path to the JSON config file.
        seed: Optional base seed used to derive per-stream RNGs.
        logger: Parent logger used for preparation-time diagnostics.

    Returns:
        A prepared simulation object with broker configs and runtime stream specs.
    """

    config = load_config(config_path)
    resolved_streams = resolve_streams(config)
    brokers = {broker.name: broker for broker in config.brokers}
    config_dir = config_path.parent.resolve()
    runtime_streams: list[RuntimeStream] = []
    for stream in resolved_streams:
        builder = build_payload_builder(stream, config_dir=config_dir, seed=seed)
        runtime_streams.append(
            RuntimeStream(
                stream_id=stream.stream_id,
                broker_name=stream.broker,
                topic=stream.topic,
                interval=stream.interval,
                qos=stream.qos,
                retain=stream.retain,
                payload_builder=builder,
                payload_kind=stream.payload.kind,
            )
        )
    logger.info(
        "Prepared simulation with %d brokers and %d streams",
        len(brokers),
        len(runtime_streams),
    )
    return PreparedSimulation(
        brokers=brokers,
        streams=runtime_streams,
        config_path=config_path,
        resolved_streams=resolved_streams,
    )
