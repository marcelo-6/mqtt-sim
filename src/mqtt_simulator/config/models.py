"""Strict Pydantic models for the locked TOML configuration schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator

from .duration import parse_duration, parse_keepalive

_GENERATOR_KEYS = {
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
}


def _ensure_named_mapping(
    value: object,
    *,
    field_name: str,
) -> dict[str, dict[str, Any]]:
    """Validate a top-level named mapping and inject the key as ``name``."""

    if not isinstance(value, dict) or not value:
        raise ValueError(f"{field_name} must be a non-empty table of named entries")

    named: dict[str, dict[str, Any]] = {}
    for name, item in value.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{field_name} keys must be non-empty strings")
        if not isinstance(item, dict):
            raise ValueError(f"{field_name}.{name} must be a table")
        named[name] = {"name": name, **item}
    return named


def _validate_non_empty_name(name: object, *, field_name: str) -> str:
    """Validate a required string name-like field."""

    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return name


def _validate_json_object(value: object, *, path: str) -> dict[str, Any]:
    """Validate one JSON object subtree used by inline JSON payloads."""

    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a JSON object")
    output: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{path} keys must be non-empty strings")
        output[key] = _validate_json_value(item, path=f"{path}.{key}")
    return output


def _validate_json_value(value: object, *, path: str) -> Any:
    """Validate a JSON payload field value."""

    if isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list):
        return [
            _validate_json_constant(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        if len(value) == 1:
            key = next(iter(value))
            if key in _GENERATOR_KEYS:
                return _validate_generator(value, path=path)
        return _validate_json_object(value, path=path)
    raise ValueError(f"{path} must be a JSON constant, nested object, or generator expression")


def _validate_json_constant(value: object, *, path: str) -> Any:
    """Validate a constant-only JSON value."""

    if isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list):
        return [
            _validate_json_constant(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        if len(value) == 1 and next(iter(value)) in _GENERATOR_KEYS:
            raise ValueError(f"{path} arrays may not contain generator expressions")
        output: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"{path} object keys must be non-empty strings")
            output[key] = _validate_json_constant(item, path=f"{path}.{key}")
        return output
    raise ValueError(f"{path} must be a JSON constant")


def _validate_number_options(
    value: object,
    *,
    path: str,
    allow_precision: bool,
    allow_start: bool,
) -> dict[str, Any]:
    """Validate ``random`` or ``walk`` numeric generator options."""

    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a table")

    allowed = {"type", "min", "max"}
    if allow_precision:
        allowed.add("precision")
    if allow_start:
        allowed.add("start")
        allowed.add("step")
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        extras = ", ".join(unexpected)
        raise ValueError(f"{path} contains unsupported keys: {extras}")

    number_type = value.get("type")
    if number_type not in {"int", "float"}:
        raise ValueError(f"{path}.type must be 'int' or 'float'")

    minimum = value.get("min")
    maximum = value.get("max")
    if isinstance(minimum, bool) or not isinstance(minimum, int | float):
        raise ValueError(f"{path}.min must be a number")
    if isinstance(maximum, bool) or not isinstance(maximum, int | float):
        raise ValueError(f"{path}.max must be a number")
    if float(minimum) > float(maximum):
        raise ValueError(f"{path}.min must be <= {path}.max")

    validated: dict[str, Any] = {
        "type": number_type,
        "min": minimum,
        "max": maximum,
    }

    if allow_precision:
        precision = value.get("precision")
        if precision is not None:
            if isinstance(precision, bool) or not isinstance(precision, int) or precision < 0:
                raise ValueError(f"{path}.precision must be an integer >= 0")
            validated["precision"] = precision

    if allow_start:
        step = value.get("step")
        if isinstance(step, bool) or not isinstance(step, int | float) or float(step) <= 0:
            raise ValueError(f"{path}.step must be a number > 0")
        start = value.get("start", minimum)
        if isinstance(start, bool) or not isinstance(start, int | float):
            raise ValueError(f"{path}.start must be a number")
        if float(start) < float(minimum) or float(start) > float(maximum):
            raise ValueError(f"{path}.start must be within the configured min/max range")
        validated["step"] = step
        validated["start"] = start

    return validated


def _validate_counter_options(value: object, *, path: str) -> dict[str, Any]:
    """Validate ``counter`` generator options."""

    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a table")
    unexpected = sorted(set(value) - {"start", "step"})
    if unexpected:
        extras = ", ".join(unexpected)
        raise ValueError(f"{path} contains unsupported keys: {extras}")
    start = value.get("start", 0)
    step = value.get("step", 1)
    if isinstance(start, bool) or not isinstance(start, int | float):
        raise ValueError(f"{path}.start must be a number")
    if isinstance(step, bool) or not isinstance(step, int | float) or float(step) == 0:
        raise ValueError(f"{path}.step must be a non-zero number")
    return {"start": start, "step": step}


def _validate_generator(value: dict[str, Any], *, path: str) -> dict[str, Any]:
    """Validate one dynamic JSON field generator expression."""

    if len(value) != 1:
        raise ValueError(f"{path} generator expressions must contain exactly one operator")
    operator, raw = next(iter(value.items()))

    if operator == "toggle":
        if not isinstance(raw, bool):
            raise ValueError(f"{path}.toggle must be a boolean")
        return {"toggle": raw}
    if operator in {"pick", "seq"}:
        if not isinstance(raw, list) or not raw:
            raise ValueError(f"{path}.{operator} must be a non-empty list")
        values = [
            _validate_json_constant(item, path=f"{path}.{operator}[{index}]")
            for index, item in enumerate(raw)
        ]
        return {operator: values}
    if operator == "walk":
        return {
            "walk": _validate_number_options(
                raw,
                path=f"{path}.walk",
                allow_precision=False,
                allow_start=True,
            )
        }
    if operator == "random":
        return {
            "random": _validate_number_options(
                raw,
                path=f"{path}.random",
                allow_precision=True,
                allow_start=False,
            )
        }
    if operator == "expr":
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"{path}.expr must be a non-empty string")
        return {"expr": raw}
    if operator == "time":
        if raw not in {"iso", "unix"}:
            raise ValueError(f"{path}.time must be 'iso' or 'unix'")
        return {"time": raw}
    if operator == "uuid":
        if raw is not True:
            raise ValueError(f"{path}.uuid must be true")
        return {"uuid": True}
    if operator == "counter":
        return {"counter": _validate_counter_options(raw, path=f"{path}.counter")}
    if operator == "null":
        if raw is not True:
            raise ValueError(f"{path}.null must be true")
        return {"null": True}
    raise ValueError(f"{path} uses unsupported generator operator '{operator}'")


class BrokerAuthConfig(BaseModel):
    """Optional authentication settings for one broker."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1)
    password: str | None = None
    password_env: str | None = None

    @model_validator(mode="after")
    def _validate_password_source(self) -> BrokerAuthConfig:
        if self.password and self.password_env:
            raise ValueError("auth.password and auth.password_env are mutually exclusive")
        return self


class BrokerTlsConfig(BaseModel):
    """Optional TLS settings for one broker."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    ca_file: str | None = None
    cert_file: str | None = None
    key_file: str | None = None
    insecure: bool = False


class BrokerConfig(BaseModel):
    """MQTT broker connection settings."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    host: str = Field(min_length=1)
    port: int = Field(default=1883, ge=1, le=65535)
    keepalive: int = 60
    protocol: Literal["3.1.1", "5.0"] = "3.1.1"
    transport: Literal["tcp", "websockets"] = "tcp"
    auth: BrokerAuthConfig | None = None
    tls: BrokerTlsConfig | None = None

    @field_validator("keepalive", mode="before")
    @classmethod
    def _parse_keepalive(cls, value: object) -> int:
        return parse_keepalive(value)


class TextPayloadConfig(BaseModel):
    """Inline UTF-8 text payload."""

    model_config = ConfigDict(extra="forbid")

    value: str


class BytesPayloadConfig(BaseModel):
    """Inline raw bytes payload."""

    model_config = ConfigDict(extra="forbid")

    utf8: str | None = None
    hex: str | None = None
    base64: str | None = None

    @model_validator(mode="after")
    def _validate_source(self) -> BytesPayloadConfig:
        selected = [name for name in ("utf8", "hex", "base64") if getattr(self, name) is not None]
        if len(selected) != 1:
            raise ValueError("bytes payload must define exactly one of utf8, hex, or base64")
        return self


class FilePayloadConfig(BaseModel):
    """Payload loaded from a file path."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)


class PicklePayloadConfig(BaseModel):
    """Payload loaded from a pickle file without unpickling."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)


class JsonPayloadConfig(RootModel[dict[str, Any]]):
    """Inline JSON payload tree."""

    @model_validator(mode="before")
    @classmethod
    def _validate_root(cls, value: object) -> dict[str, Any]:
        return _validate_json_object(value, path="payload.json")


class SequencePayloadConfig(BaseModel):
    """Sequence payload that emits text or JSON items in order."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["text", "json"] = "text"
    loop: bool = True
    items: list[Any] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_items(self) -> SequencePayloadConfig:
        validated: list[Any] = []
        for index, item in enumerate(self.items):
            if self.format == "json":
                validated.append(_validate_json_constant(item, path=f"sequence.items[{index}]"))
            else:
                if isinstance(item, bool | int | float | str):
                    validated.append(item)
                else:
                    raise ValueError(
                        f"sequence.items[{index}] must be a scalar when format='text'"
                    )
        self.items = validated
        return self


class PayloadConfig(BaseModel):
    """One inline payload block with exactly one concrete type."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    text_payload: TextPayloadConfig | None = Field(default=None, alias="text")
    json_payload: JsonPayloadConfig | None = Field(default=None, alias="json")
    sequence_payload: SequencePayloadConfig | None = Field(default=None, alias="sequence")
    bytes_payload: BytesPayloadConfig | None = Field(default=None, alias="bytes")
    file_payload: FilePayloadConfig | None = Field(default=None, alias="file")
    pickle_payload: PicklePayloadConfig | None = Field(default=None, alias="pickle")

    @model_validator(mode="after")
    def _validate_one_of(self) -> PayloadConfig:
        selected = [
            name
            for name in (
                "text_payload",
                "json_payload",
                "sequence_payload",
                "bytes_payload",
                "file_payload",
                "pickle_payload",
            )
            if getattr(self, name) is not None
        ]
        if len(selected) != 1:
            raise ValueError(
                "payload must define exactly one of text, json, sequence, bytes, file, or pickle"
            )
        return self

    @property
    def kind(self) -> str:
        """Return the configured payload type name."""

        for name in (
            "text_payload",
            "json_payload",
            "sequence_payload",
            "bytes_payload",
            "file_payload",
            "pickle_payload",
        ):
            if getattr(self, name) is not None:
                return name.removesuffix("_payload")
        raise RuntimeError("PayloadConfig.kind accessed before validation")

    @property
    def spec(self) -> BaseModel | JsonPayloadConfig:
        """Return the concrete payload config model."""

        payload = getattr(self, f"{self.kind}_payload")
        assert payload is not None
        return payload


class LifecycleMessageConfig(BaseModel):
    """One client lifecycle message definition."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    qos: int = Field(default=0, ge=0, le=2)
    retain: bool = False
    payload: PayloadConfig


class LifecycleConfig(BaseModel):
    """Optional online/offline/will payloads for one client."""

    model_config = ConfigDict(extra="forbid")

    online: LifecycleMessageConfig | None = None
    offline: LifecycleMessageConfig | None = None
    will: LifecycleMessageConfig | None = None


class ClientConfig(BaseModel):
    """One named MQTT client/session definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    broker: str = Field(min_length=1)
    id: str = Field(min_length=1)
    clean_session: bool = True
    lifecycle: LifecycleConfig | None = None


class ExpansionSpec(BaseModel):
    """One named stream expansion operator."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    range_values: list[int] | None = Field(default=None, alias="range")
    list_values: list[str | int] | None = Field(default=None, alias="list")

    @model_validator(mode="after")
    def _validate_shape(self) -> ExpansionSpec:
        has_range = self.range_values is not None
        has_list = self.list_values is not None
        if has_range == has_list:
            raise ValueError("each expansion variable must define exactly one of range or list")
        if self.range_values is not None:
            if len(self.range_values) not in {2, 3}:
                raise ValueError("range expansion must be [start, stop] or [start, stop, step]")
            if len(self.range_values) == 3 and self.range_values[2] == 0:
                raise ValueError("range expansion step must not be 0")
        if self.list_values is not None and not self.list_values:
            raise ValueError("list expansion must not be empty")
        return self


class StreamConfig(BaseModel):
    """A stream template that resolves to one or more publish streams."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    client: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    every: float
    mode: Literal["fixed-delay", "fixed-rate", "burst"] = "fixed-delay"
    jitter: float | None = None
    burst_count: int | None = None
    burst_spacing: float | None = None
    qos: int = Field(default=0, ge=0, le=2)
    retain: bool = False
    expand: dict[str, ExpansionSpec] = Field(default_factory=dict)
    payload: PayloadConfig

    @field_validator("every", mode="before")
    @classmethod
    def _parse_every(cls, value: object) -> float:
        return parse_duration(value, field_name="every")

    @field_validator("jitter", mode="before")
    @classmethod
    def _parse_jitter(cls, value: object) -> float | None:
        if value is None:
            return None
        return parse_duration(value, field_name="jitter", allow_zero=True)

    @field_validator("burst_spacing", mode="before")
    @classmethod
    def _parse_burst_spacing(cls, value: object) -> float | None:
        if value is None:
            return None
        return parse_duration(value, field_name="burst_spacing")

    @field_validator("expand")
    @classmethod
    def _validate_expand_names(cls, value: dict[str, ExpansionSpec]) -> dict[str, ExpansionSpec]:
        for key in value:
            _validate_non_empty_name(key, field_name="expand variable")
        return value

    @model_validator(mode="after")
    def _validate_schedule_shape(self) -> StreamConfig:
        if self.mode == "burst":
            if self.jitter is not None:
                raise ValueError("burst schedules do not support jitter")
            if self.burst_count is None or self.burst_count < 1:
                raise ValueError("burst schedules require burst_count >= 1")
            if self.burst_spacing is None:
                raise ValueError("burst schedules require burst_spacing")
        else:
            if self.burst_count is not None or self.burst_spacing is not None:
                raise ValueError("burst_count and burst_spacing are only valid when mode='burst'")
        return self


class SimulatorConfig(BaseModel):
    """Root TOML configuration model."""

    model_config = ConfigDict(extra="forbid")

    config_version: int = 1
    name: str | None = None
    seed: int | None = None
    brokers: dict[str, BrokerConfig]
    clients: dict[str, ClientConfig]
    streams: list[StreamConfig] = Field(min_length=1)

    @field_validator("config_version")
    @classmethod
    def _validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("config_version must be 1")
        return value

    @field_validator("brokers", mode="before")
    @classmethod
    def _coerce_brokers(cls, value: object) -> dict[str, dict[str, Any]]:
        return _ensure_named_mapping(value, field_name="brokers")

    @field_validator("clients", mode="before")
    @classmethod
    def _coerce_clients(cls, value: object) -> dict[str, dict[str, Any]]:
        return _ensure_named_mapping(value, field_name="clients")

    @model_validator(mode="after")
    def _validate_references(self) -> SimulatorConfig:
        broker_names = set(self.brokers)
        client_names = set(self.clients)

        for client_name, client in self.clients.items():
            if client.broker not in broker_names:
                raise ValueError(
                    f"clients.{client_name}.broker references unknown broker '{client.broker}'"
                )

        for index, stream in enumerate(self.streams):
            if stream.client not in client_names:
                raise ValueError(
                    f"streams[{index}].client references unknown client '{stream.client}'"
                )
        return self


@dataclass(slots=True)
class ConfigSummary:
    """Compact config summary used by the ``validate`` command."""

    broker_count: int
    client_count: int
    client_session_count: int
    stream_template_count: int
    resolved_stream_count: int
    payload_kinds: list[str]
