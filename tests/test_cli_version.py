from __future__ import annotations

import importlib

from typer.testing import CliRunner

from mqtt_simulator.cli import app
from mqtt_simulator.version import get_version


def test_cli_module_is_import_safe() -> None:
    # Re-import should not parse argv or start runtime work.
    importlib.import_module("mqtt_simulator.cli")


def test_version_command_outputs_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert get_version() in result.stdout
