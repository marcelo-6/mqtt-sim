from __future__ import annotations

from settings_classes.data_settings_number import DataSettingsNumber


def test_int_number_generator_produces_int_initial_value() -> None:
    generator = DataSettingsNumber.model_validate(
        {
            "NAME": "temperature",
            "TYPE": "int",
            "MIN_VALUE": 1,
            "MAX_VALUE": 3,
            "MAX_STEP": 1,
        }
    )

    value = generator.generate_initial_value()

    assert isinstance(value, int)


def test_float_number_generator_produces_float_initial_value() -> None:
    generator = DataSettingsNumber.model_validate(
        {
            "NAME": "temperature",
            "TYPE": "float",
            "MIN_VALUE": 1,
            "MAX_VALUE": 3,
            "MAX_STEP": 1,
        }
    )

    value = generator.generate_initial_value()

    assert isinstance(value, float)
