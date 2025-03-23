import math
import time
import json
import threading
import paho.mqtt.client as mqtt
from abc import ABC, abstractmethod
from typing import Any, List, Union, Optional, Dict
from pydantic import BaseModel, Field
from .data_classes import BrokerSettings, ClientSettings
from paho.mqtt.client import CallbackAPIVersion
import random


# Utility function to simulate probability-based behavior
def use_probability(probability: float) -> bool:
    """Returns True with the given probability."""
    return random.random() < probability


class TopicData(BaseModel, ABC):
    """Base class for all topic data types.

    This class provides the structure and behavior common to all topic data types,
    including the ability to generate initial and next values based on probabilities.
    """

    name: str
    data_type: str
    is_active: bool = True  # Indicates whether the data is active
    old_value: Optional[
        float
    ] = None  # Stores the previous value (used for retaining or resetting)
    retain_probability: float = Field(
        0, ge=0, le=1, description="Probability to retain the old value"
    )
    reset_probability: float = Field(
        0, ge=0, le=1, description="Probability to reset to an initial value"
    )
    initial_value: Optional[float] = None  # Optionally provided initial value

    def generate_value(self) -> float:
        """Generates the next value based on the previous value and probabilities."""

        new_value: Optional[float] = None

        if self.old_value is None:
            # Generate the initial value (if not provided, use generate_initial_value())
            new_value = (
                self.initial_value
                if self.initial_value is not None
                else self.generate_initial_value()
            )
        else:
            # Generate the next value based on retain or reset probabilities
            if use_probability(self.retain_probability):
                new_value = self.old_value  # Retain the old value
            elif use_probability(self.reset_probability):
                new_value = self.generate_initial_value()  # Reset to an initial value
            else:
                new_value = (
                    self.generate_next_value()
                )  # Generate the next value normally

        self.old_value = new_value  # Store the newly generated value
        return new_value

    @abstractmethod
    def generate_initial_value(self) -> float:
        """Abstract method to generate the initial value for this data type."""
        pass

    @abstractmethod
    def generate_next_value(self) -> float:
        """Abstract method to generate the next value based on the current value."""
        pass


class TopicDataNumber(TopicData):
    """TopicData subclass for numeric values (integers or floats).

    This class handles generating initial values, next values, and logic for stepping within
    specified ranges, including the option to reset or bound the values.
    """

    # Define the expected data fields for TopicDataNumber
    min_value: Union[int, float] = Field(..., description="Minimum value for the range")
    max_value: Union[int, float] = Field(..., description="Maximum value for the range")
    max_step: Union[int, float] = Field(
        ..., description="Maximum step for incrementing/decrementing the value"
    )
    increase_probability: float = Field(
        0.5, ge=0, le=1, description="Probability of increasing the value"
    )
    restart_on_boundaries: bool = Field(
        False,
        description="Whether to restart the value generation when reaching boundaries",
    )

    is_int: bool = False  # Determines if the number is an integer or float

    def generate_initial_value(self) -> Union[int, float]:
        """Generates the initial value within the defined range.

        If the type is integer, it generates an integer between the min and max values.
        Otherwise, it generates a floating-point value.
        """
        self.is_int = self.data_type == "int"
        if self.is_int:
            return random.randint(self.min_value, self.max_value)
        return random.uniform(self.min_value, self.max_value)

    def generate_next_value(self) -> Union[int, float]:
        """Generates the next value based on the current value and conditions.

        If `restart_on_boundaries` is enabled and the current value is at the boundary,
        it resets the value. Otherwise, it steps within the range and adjusts the value
        based on the increase probability.
        """
        if self.restart_on_boundaries and (
            self.old_value == self.min_value or self.old_value == self.max_value
        ):
            return self.generate_initial_value()  # Restart when hitting boundaries

        # Generate the step value and adjust its direction based on probability
        step = random.uniform(0, self.max_step)
        step = round(step) if self.is_int else step  # Round for integer values

        # Determine whether to increase or decrease the step
        if use_probability(1 - self.increase_probability):
            step *= -1  # Flip the step direction

        # Ensure the new value stays within the boundaries
        if step < 0:
            return max(self.old_value + step, self.min_value)
        return min(self.old_value + step, self.max_value)


class TopicDataBool(TopicData):
    """TopicData subclass for boolean values.

    This class handles generating initial boolean values (True/False) and flipping the
    value based on `RETAIN_PROBABILITY`. The value can be reset or retained based on the
    probability provided.
    """

    # Define the expected fields for TopicDataBool
    retain_probability: float = Field(
        0.5,
        ge=0,
        le=1,
        description="Probability of retaining the previous value (True/False)",
    )

    def generate_initial_value(self) -> bool:
        """Generates the initial boolean value (True or False)."""

        return random.choice([True, False])

    def generate_next_value(self) -> bool:
        """Generates the next boolean value based on the previous value.

        If the `RETAIN_PROBABILITY` allows, the previous value is retained (flipped).
        Otherwise, the value is flipped to the opposite.
        """
        # If should retain the current value based on probability
        if use_probability(self.retain_probability):
            return self.old_value  # Retain the old value (True or False)

        # Flip the value
        return not self.old_value  # Flip the current boolean value


class TopicDataRawValue(TopicData):
    """TopicData subclass for raw values.

    This class handles the generation of raw values from a list of predefined values.
    It includes the ability to start at a specific index, increment through values,
    and restart or deactivate when reaching the end of the list.
    """

    # Define the expected fields for TopicDataRawValue
    values: List[Any] = Field(..., description="List of raw values")
    index_start: Optional[int] = Field(0, description="Starting index for raw values")
    index_end: Optional[int] = Field(None, description="Ending index for raw values")
    restart_on_end: bool = Field(
        False, description="Whether to restart the values when reaching the end"
    )
    value_default: Optional[Dict] = Field(
        None, description="Default values to be added to the raw value"
    )

    raw_values_index: int = 0  # Tracks the current index in the values list

    def generate_initial_value(self) -> Any:
        """Generates the initial value based on the starting index."""
        self.raw_values_index = self.index_start
        return self.get_current_value()

    def generate_next_value(self) -> Any:
        """Generates the next raw value based on the current index."""
        end_index = (
            self.index_end or len(self.values) - 1
        )  # Default to the last index if index_end is not provided
        self.raw_values_index += 1

        if self.raw_values_index <= end_index:
            return self.get_current_value()
        elif self.raw_values_index > end_index and self.restart_on_end:
            return self.generate_initial_value()  # Restart the value generation
        else:
            # If all values are processed and restart_on_end is False, deactivate the topic
            self.is_active = False

    def get_current_value(self) -> Any:
        """Gets the current value based on the current index and applies default values if needed."""
        current_value = self.values[self.raw_values_index]

        if self.value_default:
            # Add default values to the current raw value
            value = (
                self.value_default.copy()
            )  # Create a copy to avoid modifying the original default
            value.update(current_value)  # Merge current raw value with defaults
            return value
        return current_value


class TopicDataMathExpression(TopicData):
    math_expression: str = Field(..., description="List of raw values")
    interval_start: Optional[int] = Field(
        0, description="Starting index for raw values"
    )
    interval_end: Optional[int] = Field(None, description="Ending index for raw values")
    min_delta: float = Field(
        False, description="Whether to restart the values when reaching the end"
    )
    max_delta: float = Field(
        None, description="Default values to be added to the raw value"
    )
    expression_evaluator: object = None

    def generate_initial_value(self):
        self.expression_evaluator = ExpressionEvaluator(
            self.math_expression,
            self.interval_start,
            self.interval_end,
            self.min_delta,
            self.max_delta,
        )
        return self.expression_evaluator.get_current_expression_value()

    def generate_next_value(self):
        return self.expression_evaluator.get_next_expression_value()


class ExpressionEvaluator:
    def __init__(
        self, math_expression, interval_start, interval_end, min_delta, max_delta
    ):
        self._math_expression = self.generate_compiled_expression(math_expression)
        self._interval_start = interval_start
        self._interval_end = interval_end
        self._min_delta = min_delta
        self._max_delta = max_delta
        self._x = interval_start

    def get_current_expression_value(self):
        return self._math_expression(self._x)

    def get_next_expression_value(self):
        if self._x > self._interval_end:
            self._x = self._interval_start
            return self.get_current_expression_value()
        step = random.uniform(self._min_delta, self._max_delta)
        self._x += step
        return self.get_current_expression_value()

    def generate_compiled_expression(self, expression):
        lambda_expression = "lambda x: " + expression
        code = compile(lambda_expression, "<string>", "eval")
        ALLOWED_FUNCTIONS = {
            function_name: func
            for function_name, func in math.__dict__.items()
            if not function_name.startswith("__")
        }
        for name in code.co_names:
            if name not in ALLOWED_FUNCTIONS:
                raise NameError(f"The use of '{name}' is not allowed")
        return eval(code, {"__builtins__": {}, "math": math}, ALLOWED_FUNCTIONS)


# Pydantic model to hold Topic configuration
class TopicConfig(BaseModel):
    topic_type: str
    prefix: str
    data: list[dict]
    payload_root: dict = {}
    clean_session: bool = True
    retain: bool = False
    qos: int = 1
    time_interval: int = 10

    def load_topic_data(self):
        topic_data = []
        for data in self.data:
            data_type = data["data_type"]
            if data_type == "int" or data_type == "float":
                topic_data.append(TopicDataNumber(**data))
            elif data_type == "bool":
                topic_data.append(TopicDataBool(**data))
            elif data_type == "raw_values":
                topic_data.append(TopicDataRawValue(**data))
            elif data_type == "math_expression":
                topic_data.append(TopicDataMathExpression(**data))
            else:
                raise ValueError(f"Unknown data type '{data_type}'")
        return topic_data


# Topic class for handling MQTT operations
class Topic(threading.Thread):
    def __init__(
        self,
        broker_settings: BrokerSettings,
        topic_url: str,
        topic_config: TopicConfig,
        client_settings: ClientSettings,
    ):
        threading.Thread.__init__(self)

        self.broker_settings = broker_settings
        self.topic_url = topic_url
        self.topic_data = topic_config.load_topic_data()
        self.topic_payload_root = topic_config.payload_root
        self.client_settings = client_settings
        self.callback_api_version = CallbackAPIVersion.VERSION2
        self.loop = False
        self.client = None
        self.payload = None

    def connect(self):
        self.loop = True
        clean_session = (
            None
            if self.broker_settings.protocol_version == mqtt.MQTTv5
            else self.client_settings.clean
        )
        self.client = mqtt.Client(
            client_id=self.topic_url,
            callback_api_version=self.callback_api_version,
            protocol=self.broker_settings.protocol_version,
            clean_session=clean_session,
        )
        self.client.on_publish = self.on_publish
        self.client.connect(self.broker_settings.url, self.broker_settings.port)
        self.client.loop_start()

    def disconnect(self):
        self.loop = False
        self.client.loop_stop()
        self.client.disconnect()

    def run(self):
        self.connect()
        while self.loop:
            self.payload = self.generate_payload()
            self.client.publish(
                topic=self.topic_url,
                payload=json.dumps(self.payload),
                qos=self.client_settings.qos,
                retain=self.client_settings.retain,
            )
            time.sleep(self.client_settings.time_interval)

    def on_publish(self, client, userdata, mid, result, oneMore):
        if self.client_settings.verbose:
            print(
                f"[{time.strftime('%H:%M:%S')}] Data published on: {self.topic_url} payload={self.payload}"
            )
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Data published on: {self.topic_url}")

    def generate_payload(self) -> dict:
        payload = {}
        payload.update(self.topic_payload_root)
        has_data_active = False
        for data in self.topic_data:
            if data.is_active:
                has_data_active = True
                payload[data.name] = data.generate_value()
        if not has_data_active:
            self.disconnect()
            return {}
        return payload
