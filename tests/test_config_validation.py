from __future__ import annotations

from pathlib import Path

import pytest

from mqtt_simulator.app import validate_config_file
from mqtt_simulator.config import load_config, resolve_streams
from mqtt_simulator.errors import ConfigLoadError, ConfigValidationError


def test_validate_config_file_returns_summary_for_valid_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
config_version = 1

[brokers.main]
host = "localhost"
port = 1883

[clients.main]
broker = "main"
id = "sim-${id}"

[[streams]]
client = "main"
topic = "sensor/${id}"
every = "100ms"

[streams.expand]
id = { range = [1, 3] }

[streams.payload.json]
temp = { random = { type = "int", min = 20, max = 22 } }
""".strip(),
        encoding="utf-8",
    )

    summary, text = validate_config_file(config_path)

    assert summary.broker_count == 1
    assert summary.client_count == 1
    assert summary.client_session_count == 3
    assert summary.stream_template_count == 1
    assert summary.resolved_stream_count == 3
    assert "payload_kinds=[json]" in text


def test_load_config_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigLoadError):
        load_config(tmp_path / "missing.toml")


def test_load_config_raises_on_validation_error(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.toml"
    config_path.write_text(
        """
config_version = 99

[brokers.main]
host = "localhost"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_config(config_path)

    assert "Config validation failed." in str(exc_info.value)


def test_resolve_streams_applies_list_expansion_to_topic_and_payload(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
config_version = 1

[brokers.main]
host = "localhost"

[clients.main]
broker = "main"
id = "client-${name}"

[[streams]]
name = "demo"
client = "main"
topic = "site/${name}"
every = "1s"

[streams.expand]
name = { list = ["a", "b"] }

[streams.payload.text]
value = "hello-${name}"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)
    resolved = resolve_streams(config)

    assert [item.topic for item in resolved] == ["site/a", "site/b"]
    assert [item.payload.kind for item in resolved] == ["text", "text"]
    assert [item.payload.spec.value for item in resolved] == ["hello-a", "hello-b"]
