from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mqtt_simulator.cli import app
from mqtt_simulator.mqtt.fake_adapter import FakeBrokerAdapter


def _write_basic_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "brokers": [{"name": "main", "host": "localhost"}],
                "streams": [
                    {
                        "broker": "main",
                        "topic": "device/{id}",
                        "interval": 0.02,
                        "expand": {"kind": "range", "var": "id", "start": 1, "stop": 2},
                        "payload": {"kind": "text", "value": "hello-{id}"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_validate_command_prints_summary() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        config_path = Path("config.json")
        _write_basic_config(config_path)

        result = runner.invoke(app, ["validate", "-c", str(config_path)])

    assert result.exit_code == 0
    assert "Config valid:" in result.stdout
    assert "resolved_streams=2" in result.stdout


def test_validate_command_returns_nonzero_for_invalid_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        config_path = Path("bad.json")
        config_path.write_text('{"schema_version":1,"brokers":[],"streams":[]}', encoding="utf-8")

        result = runner.invoke(app, ["validate", "-c", str(config_path)])

    assert result.exit_code != 0
    assert "Config validation failed." in result.stderr


def test_run_command_uses_fake_adapter_and_log_mode(monkeypatch) -> None:
    runner = CliRunner()
    created_adapters: list[FakeBrokerAdapter] = []

    def fake_paho_adapter(_broker_config, *, logger):
        del logger
        adapter = FakeBrokerAdapter()
        created_adapters.append(adapter)
        return adapter

    monkeypatch.setattr("mqtt_simulator.cli.PahoBrokerAdapter", fake_paho_adapter)

    with runner.isolated_filesystem():
        config_path = Path("config.json")
        _write_basic_config(config_path)

        result = runner.invoke(
            app,
            ["run", "-c", str(config_path), "--output", "log", "--duration", "0.06"],
        )

        log_path = Path(".mqtt-sim/logs/mqtt-sim.log")
        log_exists = log_path.exists()

    assert result.exit_code == 0
    assert "Starting simulator:" in result.stdout
    assert "Finished (" in result.stdout
    assert created_adapters
    assert any(adapter.published for adapter in created_adapters)
    assert log_exists
