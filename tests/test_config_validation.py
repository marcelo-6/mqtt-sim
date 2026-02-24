from __future__ import annotations

import json

import pytest

from mqtt_simulator.app import validate_config_file
from mqtt_simulator.config import load_config, resolve_streams
from mqtt_simulator.errors import ConfigLoadError, ConfigValidationError


def test_validate_config_file_returns_summary_for_valid_config(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "brokers": [{"name": "main", "host": "localhost"}],
                "streams": [
                    {
                        "broker": "main",
                        "topic": "sensor/{id}",
                        "interval": 0.1,
                        "expand": {"kind": "range", "var": "id", "start": 1, "stop": 3},
                        "payload": {
                            "kind": "json_fields",
                            "fields": [
                                {"name": "temp", "generator": {"kind": "const", "value": 21}}
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    summary, text = validate_config_file(config_path)

    assert summary.broker_count == 1
    assert summary.stream_template_count == 1
    assert summary.resolved_stream_count == 3
    assert "payload_kinds=[json_fields]" in text


def test_load_config_raises_on_missing_file(tmp_path) -> None:
    with pytest.raises(ConfigLoadError):
        load_config(tmp_path / "missing.json")


def test_load_config_raises_on_validation_error(tmp_path) -> None:
    config_path = tmp_path / "bad.json"
    config_path.write_text(
        json.dumps({"schema_version": 99, "brokers": [], "streams": []}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_config(config_path)

    assert "Config validation failed." in str(exc_info.value)


def test_resolve_streams_applies_list_expansion_to_topic_and_payload(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "brokers": [{"name": "main", "host": "localhost"}],
                "streams": [
                    {
                        "name": "demo",
                        "broker": "main",
                        "topic": "site/{name}",
                        "interval": 1,
                        "expand": {"kind": "list", "var": "name", "values": ["a", "b"]},
                        "payload": {"kind": "text", "value": "hello-{name}"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)
    resolved = resolve_streams(config)

    assert [item.topic for item in resolved] == ["site/a", "site/b"]
    assert [item.payload.model_dump()["value"] for item in resolved] == ["hello-a", "hello-b"]
