"""Payload builder factory functions."""

from __future__ import annotations

import random
from pathlib import Path

from ..config.expand import ResolvedStreamConfig
from .payloads import PayloadBuilder
from .payloads import build_payload_builder as build_inline_payload_builder


def build_payload_builder(
    stream: ResolvedStreamConfig,
    *,
    config_dir: Path,
    seed: int | None,
) -> PayloadBuilder:
    """Build the payload builder for one resolved stream."""

    rng_seed = _derive_seed(seed, stream.stream_id)
    rng = random.Random(rng_seed) if rng_seed is not None else random.Random()
    return build_inline_payload_builder(stream.payload, config_dir=config_dir, rng=rng)


def _derive_seed(base_seed: int | None, stream_id: str) -> int | None:
    """Create a stable per-stream seed from a base seed."""

    if base_seed is None:
        return None
    return hash((base_seed, stream_id)) & 0xFFFFFFFFFFFF
