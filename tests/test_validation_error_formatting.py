from __future__ import annotations

from utils.exceptions.simulator_validation_error import SimulatorValidationError
from utils.print_validation_error import _format_location_string


def test_format_location_string_handles_nested_path() -> None:
    location = ("TOPICS", 0, "DATA", 2, "TYPE")
    assert _format_location_string(location) == "TOPICS[0].DATA[2].TYPE"


def test_simulator_validation_error_shapes_location_and_input() -> None:
    err = SimulatorValidationError(
        title="TopicSettingsFactory",
        message="Input should be a valid topic type",
        field="TYPE",
        value_received="bad_type",
    )

    errors = err.errors()

    assert errors == [
        {
            "msg": "Input should be a valid topic type",
            "loc": "TYPE",
            "input": "bad_type",
        }
    ]
