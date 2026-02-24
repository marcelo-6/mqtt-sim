from __future__ import annotations

import pytest

from mqtt_simulator.errors import ConfigValidationError
from mqtt_simulator.render.output_mode import OutputMode, resolve_output_mode


def test_resolve_output_mode_auto_uses_table_for_tty() -> None:
    assert resolve_output_mode("auto", is_tty=True) is OutputMode.TABLE


def test_resolve_output_mode_auto_uses_log_for_non_tty() -> None:
    assert resolve_output_mode("auto", is_tty=False) is OutputMode.LOG


def test_resolve_output_mode_rejects_unknown_mode() -> None:
    with pytest.raises(ConfigValidationError):
        resolve_output_mode("jsonl", is_tty=True)
