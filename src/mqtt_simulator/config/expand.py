"""Resolve stream templates into publish streams and client sessions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from itertools import product
from typing import Any

from ..errors import ConfigValidationError
from .duration import format_duration
from .models import (
    ClientConfig,
    LifecycleMessageConfig,
    PayloadConfig,
    SimulatorConfig,
    StreamConfig,
)

_TEMPLATE_RE = re.compile(r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(slots=True)
class ResolvedLifecycleMessageConfig:
    """A resolved lifecycle message ready for payload builder construction."""

    event: str
    topic: str
    qos: int
    retain: bool
    payload: PayloadConfig


@dataclass(slots=True)
class ResolvedClientConfig:
    """A fully resolved MQTT client session."""

    session_id: str
    client_name: str
    broker_name: str
    client_id: str
    clean_session: bool
    lifecycle: dict[str, ResolvedLifecycleMessageConfig]
    context: dict[str, Any]


@dataclass(slots=True)
class ResolvedStreamConfig:
    """A fully resolved publish stream ready for runtime construction."""

    stream_id: str
    name: str
    client_session_id: str
    client_name: str
    topic: str
    mode: str
    every: float
    jitter: float | None
    burst_count: int | None
    burst_spacing: float | None
    schedule_label: str
    qos: int
    retain: bool
    payload: PayloadConfig
    context: dict[str, Any]


@dataclass(slots=True)
class ResolvedSimulationConfig:
    """Resolved client sessions plus resolved publish streams."""

    clients: dict[str, ResolvedClientConfig]
    streams: list[ResolvedStreamConfig]


def resolve_simulation(config: SimulatorConfig) -> ResolvedSimulationConfig:
    """Expand all stream templates and resolve client sessions."""

    resolved_clients: dict[str, ResolvedClientConfig] = {}
    stream_items: list[ResolvedStreamConfig] = []
    session_by_signature: dict[str, str] = {}

    for stream_index, stream in enumerate(config.streams):
        client_template = config.clients[stream.client]
        for offset, context in enumerate(_iter_contexts(stream)):
            resolved_client = _resolve_client_session(
                client_template,
                context=context,
                session_by_signature=session_by_signature,
                resolved_clients=resolved_clients,
            )
            topic = _apply_templates(
                stream.topic,
                context=context,
                path=f"streams[{stream_index}].topic",
            )
            payload = _resolve_payload(
                stream.payload,
                context=context,
                path=f"streams[{stream_index}].payload",
            )
            stream_name = stream.name or topic
            unique_suffix = f"#{offset}" if stream.expand else ""
            stream_id = f"{stream_index}:{stream_name}{unique_suffix}"
            stream_items.append(
                ResolvedStreamConfig(
                    stream_id=stream_id,
                    name=stream_name,
                    client_session_id=resolved_client.session_id,
                    client_name=resolved_client.client_name,
                    topic=topic,
                    mode=stream.mode,
                    every=stream.every,
                    jitter=stream.jitter,
                    burst_count=stream.burst_count,
                    burst_spacing=stream.burst_spacing,
                    schedule_label=_format_schedule_label(stream),
                    qos=stream.qos,
                    retain=stream.retain,
                    payload=payload,
                    context=context,
                )
            )

    return ResolvedSimulationConfig(clients=resolved_clients, streams=stream_items)


def resolve_streams(config: SimulatorConfig) -> list[ResolvedStreamConfig]:
    """Compatibility helper that returns only the resolved streams."""

    return resolve_simulation(config).streams


def _resolve_client_session(
    client: ClientConfig,
    *,
    context: dict[str, Any],
    session_by_signature: dict[str, str],
    resolved_clients: dict[str, ResolvedClientConfig],
) -> ResolvedClientConfig:
    """Resolve one client session from a stream context."""

    resolved_client = _resolve_client_model(client, context=context)
    signature = json.dumps(
        resolved_client.model_dump(mode="python"), sort_keys=True, default=str
    )
    existing = session_by_signature.get(signature)
    if existing is not None:
        return resolved_clients[existing]

    session_id = f"{resolved_client.name}:{len(resolved_clients)}"
    lifecycle: dict[str, ResolvedLifecycleMessageConfig] = {}
    if resolved_client.lifecycle is not None:
        for event_name in ("online", "offline", "will"):
            message = getattr(resolved_client.lifecycle, event_name)
            if message is not None:
                lifecycle[event_name] = _resolve_lifecycle_message(
                    message,
                    context=context,
                    path=f"clients.{resolved_client.name}.lifecycle.{event_name}",
                    event_name=event_name,
                )

    session = ResolvedClientConfig(
        session_id=session_id,
        client_name=resolved_client.name,
        broker_name=resolved_client.broker,
        client_id=resolved_client.id,
        clean_session=resolved_client.clean_session,
        lifecycle=lifecycle,
        context=dict(context),
    )
    session_by_signature[signature] = session_id
    resolved_clients[session_id] = session
    return session


def _resolve_client_model(
    client: ClientConfig, *, context: dict[str, Any]
) -> ClientConfig:
    """Resolve client templates against one stream context."""

    data = client.model_dump(mode="python")
    templated = _apply_templates(data, context=context, path=f"clients.{client.name}")
    return ClientConfig.model_validate(templated)


def _resolve_lifecycle_message(
    message: LifecycleMessageConfig,
    *,
    context: dict[str, Any],
    path: str,
    event_name: str,
) -> ResolvedLifecycleMessageConfig:
    """Resolve one lifecycle message against one stream context."""

    topic = _apply_templates(message.topic, context=context, path=f"{path}.topic")
    payload = _resolve_payload(message.payload, context=context, path=f"{path}.payload")
    return ResolvedLifecycleMessageConfig(
        event=event_name,
        topic=topic,
        qos=message.qos,
        retain=message.retain,
        payload=payload,
    )


def _resolve_payload(
    payload: PayloadConfig,
    *,
    context: dict[str, Any],
    path: str,
) -> PayloadConfig:
    """Apply template substitution to a payload config."""

    payload_dict = payload.model_dump(mode="python")
    templated = _apply_templates(payload_dict, context=context, path=path)
    return PayloadConfig.model_validate(templated)


def _iter_contexts(stream: StreamConfig) -> list[dict[str, Any]]:
    """Return template contexts generated by a stream expansion map."""

    if not stream.expand:
        return [{}]

    names = list(stream.expand)
    values_by_name = [_expansion_values(stream.expand[name]) for name in names]
    contexts: list[dict[str, Any]] = []
    for combination in product(*values_by_name):
        contexts.append(dict(zip(names, combination, strict=True)))
    return contexts


def _expansion_values(spec) -> list[Any]:
    """Return the concrete values produced by one expansion spec."""

    if spec.list_values is not None:
        return list(spec.list_values)
    assert spec.range_values is not None
    if len(spec.range_values) == 2:
        start, stop = spec.range_values
        step = 1 if stop >= start else -1
    else:
        start, stop, step = spec.range_values

    values: list[int] = []
    current = start
    if step > 0:
        while current <= stop:
            values.append(current)
            current += step
    else:
        while current >= stop:
            values.append(current)
            current += step
    return values


def _apply_templates(value: Any, *, context: dict[str, Any], path: str) -> Any:
    """Recursively apply ``${name}`` template substitution to string values."""

    if isinstance(value, str):
        return _apply_string_template(value, context=context, path=path)
    if isinstance(value, list):
        return [
            _apply_templates(item, context=context, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        return {
            key: _apply_templates(item, context=context, path=f"{path}.{key}")
            for key, item in value.items()
        }
    return value


def _apply_string_template(value: str, *, context: dict[str, Any], path: str) -> str:
    """Expand ``${name}`` placeholders in one string."""

    def replace(match: re.Match[str]) -> str:
        name = match.group("name")
        if name not in context:
            raise ConfigValidationError(
                f"Missing template variable '{name}' while resolving {path}."
            )
        return str(context[name])

    return _TEMPLATE_RE.sub(replace, value)


def _format_schedule_label(stream: StreamConfig) -> str:
    """Return a compact schedule label."""

    base = stream.mode
    every = format_duration(stream.every)
    if stream.mode == "burst":
        assert stream.burst_count is not None and stream.burst_spacing is not None
        spacing = format_duration(stream.burst_spacing)
        return f"burst {stream.burst_count}x/{spacing} every {every}"
    if stream.jitter is not None:
        return f"{base} {every} +/- {format_duration(stream.jitter)}"
    return f"{base} {every}"
