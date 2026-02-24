"""Payload builders that encode simulator values into MQTT publish bytes."""

from __future__ import annotations

import base64
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ..config.models import JsonFieldSpec, PayloadSpec
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
class JsonFieldRuntime:
    """A configured JSON field generator bound to its field name."""

    name: str
    generator: ValueGenerator


@dataclass(slots=True)
class JsonFieldsPayloadBuilder:
    """Publish a JSON object assembled from multiple field generators."""

    fields: list[JsonFieldRuntime]

    def build(self) -> PayloadBuildResult:
        """Generate a JSON object and encode it as UTF-8 bytes."""

        payload = {field.name: field.generator.next_value() for field in self.fields}
        encoded = json.dumps(payload, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
        return PayloadBuildResult(encoded, preview_payload(payload, "json_fields"))


def build_text_builder(payload_spec: PayloadSpec) -> TextPayloadBuilder:
    """Build a text payload builder from a generic payload spec."""

    value = payload_spec.model_dump(mode="python").get("value")
    if not isinstance(value, str):
        raise PayloadBuildError("text payload requires a string 'value'")
    return TextPayloadBuilder(value=value)


def build_bytes_builder(payload_spec: PayloadSpec) -> BytesPayloadBuilder:
    """Build a raw-bytes payload builder from inline text/hex/base64 content."""

    data = payload_spec.model_dump(mode="python")
    value = data.get("value")
    encoding = str(data.get("encoding", "utf8"))
    if not isinstance(value, str):
        raise PayloadBuildError("bytes payload requires a string 'value'")
    try:
        if encoding == "utf8":
            payload = value.encode("utf-8")
        elif encoding == "hex":
            payload = bytes.fromhex(value)
        elif encoding == "base64":
            payload = base64.b64decode(value)
        else:
            raise PayloadBuildError(
                "bytes payload encoding must be utf8, hex, or base64"
            )
    except ValueError as exc:
        raise PayloadBuildError(f"bytes payload decoding failed: {exc}") from exc
    return BytesPayloadBuilder(payload=payload)


def build_file_builder(
    payload_spec: PayloadSpec, *, config_dir: Path, kind: str
) -> FilePayloadBuilder:
    """Build a file-backed payload builder.

    Args:
        payload_spec: The generic payload spec that contains a ``path`` field.
        config_dir: Base directory used for resolving relative file paths.
        kind: Either ``file`` or ``pickle_file``.
    """

    data = payload_spec.model_dump(mode="python")
    raw_path = data.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise PayloadBuildError(f"{kind} payload requires a non-empty 'path'")
    if Path(raw_path).is_absolute():
        path = Path(raw_path)
    else:
        path = (config_dir / raw_path).resolve()
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise PayloadBuildError(f"Unable to read payload file: {path}") from exc
    return FilePayloadBuilder(payload=payload, kind=kind)


def build_sequence_builder(payload_spec: PayloadSpec) -> SequencePayloadBuilder:
    """Build a sequence payload builder."""

    data = payload_spec.model_dump(mode="python")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise PayloadBuildError("sequence payload requires a non-empty 'items' list")
    encoding = str(data.get("encoding", "text"))
    if encoding not in {"text", "json"}:
        raise PayloadBuildError("sequence payload encoding must be 'text' or 'json'")
    return SequencePayloadBuilder(
        items=list(items),
        loop=bool(data.get("loop", True)),
        encoding=encoding,
    )


def build_json_fields_builder(
    payload_spec: PayloadSpec, *, rng: random.Random
) -> JsonFieldsPayloadBuilder:
    """Build a JSON-fields payload builder with stateful generators."""

    data = payload_spec.model_dump(mode="python")
    raw_fields = data.get("fields")
    if not isinstance(raw_fields, list) or not raw_fields:
        raise PayloadBuildError(
            "json_fields payload requires a non-empty 'fields' list"
        )
    fields: list[JsonFieldRuntime] = []
    for raw_field in raw_fields:
        try:
            field_spec = JsonFieldSpec.model_validate(raw_field)
        except Exception as exc:
            raise PayloadBuildError(f"Invalid json_fields field spec: {exc}") from exc
        field_rng = random.Random(rng.random())
        generator = build_value_generator(field_spec.generator, rng=field_rng)
        fields.append(JsonFieldRuntime(name=field_spec.name, generator=generator))
    return JsonFieldsPayloadBuilder(fields=fields)
