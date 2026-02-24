from __future__ import annotations

import logging

from mqtt_simulator.cli_errors import handle_cli_exception
from mqtt_simulator.errors import ConfigValidationError


def test_handle_cli_exception_maps_expected_errors() -> None:
    logger = logging.getLogger("test.errors.expected")

    result = handle_cli_exception(ConfigValidationError("Bad config."), logger)

    assert result.exit_code == 2
    assert result.message == "Bad config."


def test_handle_cli_exception_maps_unexpected_errors() -> None:
    logger = logging.getLogger("test.errors.unexpected")

    result = handle_cli_exception(RuntimeError("boom"), logger)

    assert result.exit_code == 1
    assert "See log file" in result.message
