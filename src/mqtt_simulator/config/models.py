"""Pydantic models for the simulator configuration schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class KindedSpec(BaseModel):
    """A generic kind spec."""

    model_config = ConfigDict(extra="allow")

    kind: str


class JsonFieldSpec(BaseModel):
    """A field entry for the ``json_fields`` payload kind."""

    name: str = Field(min_length=1)
    generator: KindedSpec


class PayloadSpec(KindedSpec):
    """A payload spec for a stream."""

    kind: str = Field(min_length=1)


class BrokerConfig(BaseModel):
    """MQTT broker connection settings."""

    name: str = Field(min_length=1)
    host: str = Field(min_length=1)
    port: int = Field(default=1883, ge=1, le=65535)
    keepalive: int = Field(default=60, ge=1)
    client_id: str | None = None
    username: str | None = None
    password: str | None = None


class RangeExpansion(BaseModel):
    """Expand one stream template into many streams using an integer range."""

    kind: Literal["range"]
    var: str = Field(min_length=1)
    start: int
    stop: int
    step: int = 1
    inclusive: bool = True

    @field_validator("step")
    @classmethod
    def _validate_step(cls, value: int) -> int:
        if value == 0:
            raise ValueError("step must not be 0")
        return value


class ListExpansion(BaseModel):
    """Expand one stream template into many streams using a value list."""

    kind: Literal["list"]
    var: str = Field(min_length=1)
    values: list[Any] = Field(min_length=1)


ExpansionSpec = Annotated[RangeExpansion | ListExpansion, Field(discriminator="kind")]


class StreamConfig(BaseModel):
    """A stream template that resolves to one or more MQTT publish streams."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    broker: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    interval: float = Field(gt=0)
    qos: int = Field(default=0, ge=0, le=2)
    retain: bool = False
    payload: PayloadSpec
    expand: ExpansionSpec | None = None


class SimulatorConfig(BaseModel):
    """Root config model."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    brokers: list[BrokerConfig] = Field(min_length=1)
    streams: list[StreamConfig] = Field(min_length=1)

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("schema_version must be 1")
        return value

    @model_validator(mode="after")
    def _validate_unique_brokers(self) -> SimulatorConfig:
        names = [broker.name for broker in self.brokers]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            dupes = ", ".join(sorted(duplicates))
            raise ValueError(f"duplicate broker names: {dupes}")
        return self


@dataclass(slots=True)
class ConfigSummary:
    """Small summary used by the ``validate`` command output."""

    broker_count: int
    stream_template_count: int
    resolved_stream_count: int
    payload_kinds: list[str]
