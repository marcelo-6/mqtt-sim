"""Payload builder factory functions."""

from __future__ import annotations

import random
from pathlib import Path

from ..config.expand import ResolvedStreamConfig
from ..errors import PayloadBuildError
from .payloads import (
    PayloadBuilder,
    build_bytes_builder,
    build_file_builder,
    build_json_fields_builder,
    build_sequence_builder,
    build_text_builder,
)


def build_payload_builder(
    stream: ResolvedStreamConfig,
    *,
    config_dir: Path,
    seed: int | None,
) -> PayloadBuilder:
    """Build the payload builder for one resolved stream."""

    kind = stream.payload.kind
    rng_seed = _derive_seed(seed, stream.stream_id)
    rng = random.Random(rng_seed) if rng_seed is not None else random.Random()

    if kind == "json_fields":
        return build_json_fields_builder(stream.payload, rng=rng)
    if kind == "text":
        return build_text_builder(stream.payload)
    if kind == "bytes":
        return build_bytes_builder(stream.payload)
    if kind == "file":
        return build_file_builder(stream.payload, config_dir=config_dir, kind="file")
    if kind == "pickle_file":
        return build_file_builder(
            stream.payload, config_dir=config_dir, kind="pickle_file"
        )
    if kind == "sequence":
        return build_sequence_builder(stream.payload)
    raise PayloadBuildError(
        f"Unsupported payload kind: {kind}", stream_id=stream.stream_id
    )


def _derive_seed(base_seed: int | None, stream_id: str) -> int | None:
    """Create a stable per-stream seed from a base seed."""

    if base_seed is None:
        return None
    return hash((base_seed, stream_id)) & 0xFFFFFFFFFFFF
