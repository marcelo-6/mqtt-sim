from pydantic import BaseModel


class BrokerSettings(BaseModel):
    url: str
    port: int
    protocol_version: int


class ClientSettings(BaseModel):
    clean: bool
    retain: bool
    qos: int
    time_interval: int
