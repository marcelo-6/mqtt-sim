from pydantic import BaseModel
from typing import List, Optional


class BrokerSettings(BaseModel):
    url: str
    port: int
    protocol_version: int


class ClientSettings(BaseModel):
    clean: bool
    retain: bool
    qos: int
    time_interval: int


class TopicConfig(BaseModel):
    TYPE: str
    PREFIX: str
    DATA: dict
    PAYLOAD_ROOT: Optional[dict]
    CLEAN_SESSION: bool
    RETAIN: bool
    QOS: int
    TIME_INTERVAL: int
