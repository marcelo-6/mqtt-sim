import time
import json
import threading
import paho.mqtt.client as mqtt
from typing import List, Union
from pydantic import BaseModel, Field
from data_classes import BrokerSettings, ClientSettings
from paho.mqtt.client import CallbackAPIVersion
import random


# Define the base class for the topic data
class TopicData(BaseModel):
    NAME: str
    is_active: bool = True

    def generate_value(self) -> dict:
        raise NotImplementedError(
            "Each TopicData subclass must implement generate_value()"
        )


# TopicData for numbers (int or float)
class TopicDataNumber(TopicData):
    MIN_VALUE: float = Field(..., ge=0)  # ge=0 ensures min_value >= 0
    MAX_VALUE: float = Field(..., ge=0)

    def generate_value(self) -> dict:
        # Example: Generate a midpoint value or any logic you want
        value = (self.MAX_VALUE - self.MIN_VALUE) / 2 + self.MIN_VALUE
        return {self.NAME: value}


# TopicData for booleans
class TopicDataBool(TopicData):
    TRUE_PROBABILITY: float = Field(..., ge=0, le=1)  # Probability between 0 and 1

    def generate_value(self) -> dict:
        value = True if random.random() < self.TRUE_PROBABILITY else False
        return {self.NAME: value}


# TopicData for raw values (custom or specific data)
class TopicDataRawValue(TopicData):
    VALUE: Union[int, float]

    def generate_value(self) -> dict:
        return {self.NAME: self.VALUE}


# TopicData for math expressions (e.g., "2 * x + 5")
class TopicDataMathExpression(TopicData):
    EXPRESSION: str  # Math expression as a string

    def generate_value(self) -> dict:
        # Safely evaluate the math expression
        try:
            value = eval(
                self.EXPRESSION
            )  # In a real application, use a safer eval approach
        except Exception as e:
            value = str(e)  # Return the error message if the eval fails
        return {self.NAME: value}


# Pydantic model to hold Topic configuration
class TopicConfig(BaseModel):
    TYPE: str
    PREFIX: str
    DATA: List[dict]
    PAYLOAD_ROOT: dict = {}
    CLEAN_SESSION: bool = True
    RETAIN: bool = False
    QOS: int = 1
    TIME_INTERVAL: int = 10

    def load_topic_data(self):
        topic_data = []
        for data in self.DATA:
            data_type = data["TYPE"]
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
        self.topic_payload_root = topic_config.PAYLOAD_ROOT
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
        print(f"[{time.strftime('%H:%M:%S')}] Data published on: {self.topic_url}")

    def generate_payload(self) -> dict:
        payload = {}
        payload.update(self.topic_payload_root)
        has_data_active = False
        for data in self.topic_data:
            if data.is_active:
                has_data_active = True
                payload.update(data.generate_value())
        if not has_data_active:
            self.disconnect()
            return {}
        return payload
