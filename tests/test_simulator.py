import json
import math
import random
import time
import pytest
from unittest.mock import MagicMock, patch

# Import the classes from your app (adjust the module paths as needed)
from app.classes.topic import (
    Topic,
    TopicConfig,
    ExpressionEvaluator,
    use_probability,
    TopicDataMathExpression,
    TopicData,
    TopicDataNumber,
    TopicDataBool,
    TopicDataRawValue,
)
from app.classes.data_classes import BrokerSettings, ClientSettings

# =====================
# Fixtures
# =====================


@pytest.fixture
def complex_config():
    """Fixture for the complex settings JSON as a Python dict."""
    return {
        "broker_url": "localhost",
        "broker_port": 1883,
        "topics": [
            {
                "topic_type": "multiple",
                "prefix": "lamp",
                "range_start": 1,
                "range_end": 2,
                "time_interval": 4,
                "data": [
                    {"name": "on", "data_type": "bool", "retain_probability": 0.85},
                    {
                        "name": "temperature",
                        "data_type": "int",
                        "initial_value": 2750,
                        "min_value": 2700,
                        "max_value": 6500,
                        "max_step": 250,
                        "retain_probability": 0.3,
                        "reset_probability": 0.1,
                        "increase_probability": 0.8,
                        "restart_on_boundaries": True,
                    },
                ],
            },
            {
                "topic_type": "single",
                "prefix": "air_quality",
                "time_interval": 6,
                "data": [
                    {
                        "name": "pollution_particles",
                        "data_type": "float",
                        "min_value": 0,
                        "max_value": 1,
                        "max_step": 0.15,
                        "retain_probability": 0.9,
                    },
                    {"name": "alert", "data_type": "bool", "retain_probability": 0.9},
                ],
            },
            {
                "topic_type": "list",
                "prefix": "temperature",
                "list": ["roof", "basement"],
                "time_interval": 8,
                "data": [
                    {
                        "name": "temperature",
                        "data_type": "float",
                        "min_value": 20,
                        "max_value": 55,
                        "max_step": 3,
                        "retain_probability": 0.5,
                        "increase_probability": 0.6,
                    }
                ],
            },
            {
                "topic_type": "single",
                "prefix": "freezer",
                "time_interval": 6,
                "data": [
                    {
                        "name": "temperature",
                        "data_type": "math_expression",
                        "retain_probability": 0.1,
                        "math_expression": "2*math.pow(x,2)+1",
                        "interval_start": 0,
                        "interval_end": 5,
                        "min_delta": 0.3,
                        "max_delta": 0.5,
                    }
                ],
            },
            {
                "topic_type": "single",
                "prefix": "location",
                "time_interval": 5,
                "payload_root": {"user_id": "abc123"},
                "data": [
                    {
                        "name": "position",
                        "data_type": "raw_values",
                        "restart_on_end": True,
                        "values": ["moving", "stopped"],
                    },
                    {
                        "name": "coordinate",
                        "data_type": "raw_values",
                        "value_default": {"alt": 0},
                        "restart_on_end": True,
                        "values": [
                            {"alt": 0.1, "lat": -121.883682, "long": 37.354635},
                            {"lat": -121.883352, "long": 37.354192},
                            {"alt": 0.15, "lat": -121.884284, "long": 37.353757},
                            {"alt": 0.22, "lat": -121.885227, "long": 37.353324},
                        ],
                    },
                ],
            },
        ],
    }


@pytest.fixture
def broker_settings(complex_config):
    """Fixture for BrokerSettings."""
    return BrokerSettings(
        url=complex_config["broker_url"],
        port=complex_config["broker_port"],
        protocol_version=4,  # Adjust if using MQTTv5
    )


@pytest.fixture
def client_settings():
    """Fixture for ClientSettings."""
    # Assume ClientSettings has a 'verbose' attribute for testing purposes.
    return ClientSettings(
        clean=True, retain=False, qos=1, time_interval=5, verbose=True
    )


@pytest.fixture
def topic_configs(complex_config):
    """Fixture that returns a list of TopicConfig objects from the complex config."""
    configs = []
    for topic_conf in complex_config["topics"]:
        configs.append(TopicConfig(**topic_conf))
    return configs


# =====================
# Tests for TopicData subclasses
# =====================


def test_topicdata_number_initial_and_next():
    """Test TopicDataNumber's initial and next value generation."""
    data = {
        "name": "temperature",
        "data_type": "float",
        "min_value": 10,
        "max_value": 30,
        "max_step": 2,
        "increase_probability": 0.8,
        "retain_probability": 0.0,  # force new value generation
        "reset_probability": 0.0,
    }
    td_num = TopicDataNumber(**data)
    init_val = td_num.generate_value()
    assert 10 <= init_val <= 30, f"Initial value {init_val} not in range 10-30"
    # Force next value generation by ensuring old_value is not retained
    next_val = td_num.generate_value()
    assert 10 <= next_val <= 30, f"Next value {next_val} not in range 10-30"


def test_topicdata_bool_flip_and_retain(monkeypatch):
    """Test TopicDataBool for initial generation and next value (flip/retain)."""
    data = {"name": "status", "data_type": "bool", "retain_probability": 0.5}
    td_bool = TopicDataBool(**data)
    # Force initial value
    init_val = td_bool.generate_value()
    assert init_val in [True, False]

    # Test retention branch by patching use_probability to always return True
    monkeypatch.setattr("app.classes.topic.use_probability", lambda prob: True)
    retained_val = td_bool.generate_value()
    assert retained_val == td_bool.old_value, "Expected to retain old value"

    # Test flip branch by patching use_probability to return False
    monkeypatch.setattr("app.classes.topic.use_probability", lambda prob: False)
    previous = td_bool.old_value  # store the current (old) value
    flipped_val = td_bool.generate_value()
    assert flipped_val == (not previous), "Expected value to flip"


def test_topicdata_raw_value_restart_and_deactivate():
    """Test TopicDataRawValue's initial, next, restart, and deactivation behavior."""
    data = {
        "name": "position",
        "data_type": "raw_values",
        "values": ["moving", "stopped"],
        "index_start": 0,
        "index_end": 1,
        "restart_on_end": True,
    }
    td_raw = TopicDataRawValue(**data)
    init_val = td_raw.generate_value()
    assert init_val == "moving", f"Expected 'moving', got {init_val}"
    next_val = td_raw.generate_value()
    assert next_val == "stopped", f"Expected 'stopped', got {next_val}"
    # Should restart because restart_on_end is True
    restart_val = td_raw.generate_value()
    assert restart_val == "moving", f"Expected restart to 'moving', got {restart_val}"


def test_topicdata_math_expression(monkeypatch):
    """Test TopicDataMathExpression initial and next value generation."""
    data = {
        "name": "calculated_value",
        "data_type": "math_expression",
        "math_expression": "2*math.pow(x,2)+1",
        "interval_start": 0,
        "interval_end": 5,
        "min_delta": 0.3,
        "max_delta": 0.3,  # fixed step for predictability
        "retain_probability": 0.0,
    }
    td_math = TopicDataMathExpression(**data)
    init_val = td_math.generate_value()
    # At x=0, expression should be 1
    assert math.isclose(init_val, 1.0), f"Expected initial value 1.0, got {init_val}"

    next_val = td_math.generate_value()
    # With a fixed step of 0.3, x becomes 0.3, so value = 2*0.3^2+1 = 2*0.09+1 = 1.18
    assert math.isclose(
        next_val, 1.18, rel_tol=1e-2
    ), f"Expected next value ~1.18, got {next_val}"


def test_expression_evaluator_reset():
    """Test ExpressionEvaluator's reset behavior."""
    evaluator = ExpressionEvaluator("2*math.pow(x,2)+1", 0, 5, 0.3, 0.3)
    # Advance x past interval_end
    evaluator._x = 6
    val_after_reset = evaluator.get_next_expression_value()
    # After reset, x should be set to interval_start=0, value = 1
    assert math.isclose(
        val_after_reset, 1.0
    ), f"Expected reset value 1.0, got {val_after_reset}"


# =====================
# Tests for TopicConfig and Topic integration
# =====================


def test_topic_config_load(topic_configs):
    """Test that TopicConfig.load_topic_data creates TopicData instances correctly."""
    for config in topic_configs:
        td_list = config.load_topic_data()
        assert isinstance(td_list, list)
        for td in td_list:
            assert isinstance(td, TopicData)


def test_topic_generate_payload(broker_settings, client_settings, topic_configs):
    """Test that Topic.generate_payload produces payload with expected keys."""
    for config in topic_configs:
        topic = Topic(broker_settings, config.prefix, config, client_settings)
        # Patch the MQTT client to avoid network calls
        topic.client = MagicMock()
        payload = topic.generate_payload()
        # Verify payload includes keys from payload_root (if any)
        if config.payload_root:
            for key in config.payload_root:
                assert key in payload
        # Verify that for each TopicData, its name appears in the payload
        td_list = config.load_topic_data()
        for td in td_list:
            assert td.name in payload


def test_topic_run_iteration(broker_settings, client_settings, topic_configs):
    """Integration test: simulate one publish iteration of a Topic."""
    # Choose one topic configuration for testing
    config = topic_configs[0]
    topic = Topic(broker_settings, config.prefix, config, client_settings)

    # Patch MQTT client methods so no real connection occurs
    topic.client = MagicMock()
    topic.client.publish = MagicMock()
    topic.loop = True

    # Simulate one publish iteration
    payload = topic.generate_payload()
    topic.client.publish(
        topic=topic.topic_url,
        payload=json.dumps(payload),
        qos=client_settings.qos,
        retain=client_settings.retain,
    )
    topic.client.publish.assert_called_once()

    # Simulate disconnect and check loop is set to False
    topic.disconnect()
    assert topic.loop is False
