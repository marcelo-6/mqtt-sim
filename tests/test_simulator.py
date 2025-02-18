from unittest.mock import MagicMock, mock_open, patch
from pathlib import Path
from simulator import Simulator
from topic import (
    Topic,
    TopicConfig,
    TopicDataNumber,
    TopicDataBool,
    TopicDataMathExpression,
    TopicDataRawValue,
)
from data_classes import BrokerSettings, ClientSettings
import json


# Test to ensure that the Simulator loads topics correctly
def test_load_topics():
    # Mock the settings file path
    settings_file = Path("config/settings.json")

    # Mock the content of settings.json
    mock_settings = {
        "BROKER_URL": "localhost",
        "BROKER_PORT": 1883,
        "PROTOCOL_VERSION": 4,
        "TOPICS": [
            {
                "TYPE": "single",
                "PREFIX": "sensors/temperature",
                "DATA": [
                    {
                        "NAME": "temp_value",
                        "TYPE": "float",
                        "MIN_VALUE": 10,
                        "MAX_VALUE": 30,
                    }
                ],
                "PAYLOAD_ROOT": {"sensor": "temperature_sensor"},
                "CLEAN_SESSION": True,
                "RETAIN": False,
                "QOS": 1,
                "TIME_INTERVAL": 5,
            }
        ],
    }

    # Patch open() using mock_open, and return mock JSON content
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_settings))):
        # Initialize Simulator
        simulator = Simulator(settings_file=settings_file)

        # Assert that topics are loaded correctly
        assert len(simulator.topics) == 1
        assert simulator.topics[0].topic_url == "sensors/temperature"
        assert simulator.topics[0].topic_data[0].NAME == "temp_value"
        assert simulator.topics[0].topic_data[0].MIN_VALUE == 10
        assert simulator.topics[0].topic_data[0].MAX_VALUE == 30


# Test for the Topic class, checking connection and payload generation
def test_topic():
    mock_broker = BrokerSettings(url="localhost", port=1883, protocol_version=4)
    mock_client_settings = ClientSettings(
        clean=True, retain=False, qos=1, time_interval=5
    )

    # Create a mock topic configuration
    mock_topic_config = TopicConfig(
        TYPE="single",
        PREFIX="sensors/temperature",
        DATA=[
            {"NAME": "temp_value", "TYPE": "float", "MIN_VALUE": 10, "MAX_VALUE": 30}
        ],
        PAYLOAD_ROOT={"sensor": "temperature_sensor"},
        CLEAN_SESSION=True,
        RETAIN=False,
        QOS=1,
        TIME_INTERVAL=5,
    )

    # Initialize a Topic
    topic = Topic(
        mock_broker, "sensors/temperature", mock_topic_config, mock_client_settings
    )

    # Test the payload generation
    payload = topic.generate_payload()
    assert "sensor" in payload
    assert "temp_value" in payload

    # Test connecting to the broker
    topic.connect()
    # topic.client.connect.assert_called_with("localhost", 1883)


# Test to ensure that TopicDataNumber generates the correct value
def test_topic_data_number():
    data = {"NAME": "temp_value", "TYPE": "float", "MIN_VALUE": 10, "MAX_VALUE": 30}
    topic_data = TopicDataNumber(**data)

    value = topic_data.generate_value()

    # Ensure value is in the expected range and has the correct name
    assert "temp_value" in value
    assert 10 <= value["temp_value"] <= 30


# Test to ensure that TopicDataBool generates correct boolean value
def test_topic_data_bool():
    data = {"NAME": "status", "TYPE": "bool", "TRUE_PROBABILITY": 0.7}
    topic_data = TopicDataBool(**data)

    value = topic_data.generate_value()

    # Ensure the generated value is either True or False
    assert "status" in value
    assert value["status"] in [True, False]


# Test to ensure that TopicDataRawValue generates the correct value
def test_topic_data_raw_value():
    data = {"NAME": "status", "TYPE": "raw_values", "VALUE": 100}
    topic_data = TopicDataRawValue(**data)

    value = topic_data.generate_value()

    # Ensure the generated value is the raw value
    assert "status" in value
    assert value["status"] == 100


# Test to ensure that TopicDataMathExpression generates the correct value
def test_topic_data_math_expression():
    data = {
        "NAME": "calculated_value",
        "TYPE": "math_expression",
        "EXPRESSION": "2 * 5 + 10",
    }
    topic_data = TopicDataMathExpression(**data)

    value = topic_data.generate_value()

    # Ensure the generated value is the result of the expression
    assert "calculated_value" in value
    assert value["calculated_value"] == 20
