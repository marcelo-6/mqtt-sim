"""Payload builders that encode simulator values into MQTT publish bytes."""

from __future__ import annotations

import base64
import copy
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ..config.models import (
    BytesPayloadConfig,
    FilePayloadConfig,
    JsonPayloadConfig,
    PayloadConfig,
    PicklePayloadConfig,
    SequencePayloadConfig,
    TextPayloadConfig,
)
from ..errors import PayloadBuildError
from .generators import ValueGenerator, build_value_generator
from .preview import preview_payload


@dataclass(slots=True)
class PayloadBuildResult:
    """The encoded payload bytes plus a compact preview string."""

    payload_bytes: bytes
    preview: str


class PayloadBuilder(Protocol):
    """Protocol for stateful payload builders."""

    def build(self) -> PayloadBuildResult:
        """Build and encode the next payload."""


@dataclass(slots=True)
class TextPayloadBuilder:
    """Publish a constant text payload."""

    value: str

    def build(self) -> PayloadBuildResult:
        """Encode the text payload as UTF-8."""

        payload = self.value.encode("utf-8")
        return PayloadBuildResult(payload, preview_payload(self.value, "text"))


@dataclass(slots=True)
class BytesPayloadBuilder:
    """Publish raw bytes from an inline bytes spec."""

    payload: bytes

    def build(self) -> PayloadBuildResult:
        """Return the configured raw bytes payload."""

        return PayloadBuildResult(self.payload, preview_payload(self.payload, "bytes"))


@dataclass(slots=True)
class FilePayloadBuilder:
    """Publish bytes from a file loaded at builder creation time."""

    payload: bytes
    kind: str = "file"

    def build(self) -> PayloadBuildResult:
        """Return cached file bytes."""

        return PayloadBuildResult(
            self.payload, preview_payload(self.payload, self.kind)
        )


@dataclass(slots=True)
class SequencePayloadBuilder:
    """Publish a sequence of payload items encoded as text or JSON."""

    items: list[Any]
    loop: bool
    encoding: str
    index: int = 0

    def build(self) -> PayloadBuildResult:
        """Return the next sequence item encoded to bytes."""

        if self.index >= len(self.items):
            if self.loop:
                self.index = 0
            else:
                self.index = len(self.items) - 1
        item = self.items[self.index]
        self.index += 1
        if self.encoding == "json":
            encoded = json.dumps(item, separators=(",", ":"), default=str).encode(
                "utf-8"
            )
        else:
            encoded = str(item).encode("utf-8")
        preview_input = item if self.encoding == "json" else str(item)
        return PayloadBuildResult(encoded, preview_payload(preview_input, "sequence"))


@dataclass(slots=True)
class JsonNode(Protocol):
    """Protocol for one compiled JSON payload node."""

    def build_value(self) -> Any:
        """Return the next concrete JSON value for this node."""


@dataclass(slots=True)
class JsonConstantNode:
    """A constant JSON payload node."""

    value: Any

    def build_value(self) -> Any:
        """Return a deep-copied constant value."""

        return copy.deepcopy(self.value)


@dataclass(slots=True)
class JsonGeneratorNode:
    """A dynamic JSON payload node backed by a stateful generator."""

    generator: ValueGenerator

    def build_value(self) -> Any:
        """Return the next generated value."""

        return self.generator.next_value()


@dataclass(slots=True)
class JsonObjectNode:
    """A JSON object assembled from nested constant/generator nodes."""

    fields: dict[str, JsonNode]


    def build_value(self) -> dict[str, Any]:
        """Return the next concrete JSON object."""

        return {name: node.build_value() for name, node in self.fields.items()}


@dataclass(slots=True)
class JsonPayloadBuilder:
    """Publish a JSON object assembled from a nested payload tree."""

    root: JsonObjectNode

    def build(self) -> PayloadBuildResult:
        """Generate a JSON object and encode it as UTF-8 bytes."""

        payload = self.root.build_value()
        encoded = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        return PayloadBuildResult(encoded, preview_payload(payload, "json"))


def build_text_builder(payload_spec: TextPayloadConfig) -> TextPayloadBuilder:
    """Build a text payload builder."""

    return TextPayloadBuilder(value=payload_spec.value)


def build_bytes_builder(payload_spec: BytesPayloadConfig) -> BytesPayloadBuilder:
    """Build a raw-bytes payload builder from one inline source."""

    try:
        if payload_spec.utf8 is not None:
            payload = payload_spec.utf8.encode("utf-8")
        elif payload_spec.hex is not None:
            payload = bytes.fromhex(payload_spec.hex)
        elif payload_spec.base64 is not None:
            payload = base64.b64decode(payload_spec.base64)
        else:  # pragma: no cover - guarded by config validation
            raise PayloadBuildError("bytes payload has no configured source")
    except ValueError as exc:
        raise PayloadBuildError(f"bytes payload decoding failed: {exc}") from exc
    return BytesPayloadBuilder(payload=payload)


def build_file_builder(
    payload_spec: FilePayloadConfig | PicklePayloadConfig,
    *,
    config_dir: Path,
    kind: str,
) -> FilePayloadBuilder:
    """Build a file-backed payload builder."""

    raw_path = payload_spec.path
    path = Path(raw_path) if Path(raw_path).is_absolute() else (config_dir / raw_path).resolve()
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise PayloadBuildError(f"Unable to read payload file: {path}") from exc
    return FilePayloadBuilder(payload=payload, kind=kind)


def build_sequence_builder(payload_spec: SequencePayloadConfig) -> SequencePayloadBuilder:
    """Build a sequence payload builder."""

    return SequencePayloadBuilder(
        items=list(payload_spec.items),
        loop=payload_spec.loop,
        encoding=payload_spec.format,
    )


def build_json_builder(
    payload_spec: JsonPayloadConfig,
    *,
    rng: random.Random,
) -> JsonPayloadBuilder:
    """Build a nested JSON payload builder with stateful generators."""

    root = _compile_json_object(payload_spec.root, rng=rng)
    return JsonPayloadBuilder(root=root)


def build_payload_builder(
    payload: PayloadConfig,
    *,
    config_dir: Path,
    rng: random.Random,
) -> PayloadBuilder:
    """Build the correct payload builder from an inline payload config."""

    kind = payload.kind
    spec = payload.spec

    if kind == "text":
        assert isinstance(spec, TextPayloadConfig)
        return build_text_builder(spec)
    if kind == "json":
        assert isinstance(spec, JsonPayloadConfig)
        return build_json_builder(spec, rng=rng)
    if kind == "sequence":
        assert isinstance(spec, SequencePayloadConfig)
        return build_sequence_builder(spec)
    if kind == "bytes":
        assert isinstance(spec, BytesPayloadConfig)
        return build_bytes_builder(spec)
    if kind == "file":
        assert isinstance(spec, FilePayloadConfig)
        return build_file_builder(spec, config_dir=config_dir, kind="file")
    if kind == "pickle":
        assert isinstance(spec, PicklePayloadConfig)
        return build_file_builder(spec, config_dir=config_dir, kind="pickle")
    raise PayloadBuildError(f"Unsupported payload kind: {kind}")


def _compile_json_object(value: dict[str, Any], *, rng: random.Random) -> JsonObjectNode:
    """Compile one JSON object mapping into nested runtime nodes."""

    return JsonObjectNode(
        fields={
            key: _compile_json_node(item, rng=random.Random(rng.random()))
            for key, item in value.items()
        }
    )


def _compile_json_node(value: Any, *, rng: random.Random) -> JsonNode:
    """Compile one validated JSON value into a runtime node."""

    if isinstance(value, dict):
        if len(value) == 1 and next(iter(value)) in {
            "toggle",
            "pick",
            "seq",
            "walk",
            "random",
            "expr",
            "time",
            "uuid",
            "counter",
            "null",
        }:
            return JsonGeneratorNode(generator=build_value_generator(value, rng=rng))
        return _compile_json_object(value, rng=rng)
    return JsonConstantNode(value=value)
