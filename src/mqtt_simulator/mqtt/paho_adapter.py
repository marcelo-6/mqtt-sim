"""Paho MQTT adapter used for real broker connectivity."""

from __future__ import annotations

import asyncio
import logging
import os
import threading

import paho.mqtt.client as mqtt

from ..errors import BrokerConnectionError, BrokerPublishError
from ..runtime.models import RuntimeClient
from .adapter import PublishResult


class PahoBrokerAdapter:
    """Async wrapper around a single Paho MQTT client instance.
      it connects once, uses Paho's network loop thread, and wraps blocking waits
    with ``asyncio.to_thread``.
    """

    def __init__(self, client: RuntimeClient, *, logger: logging.Logger) -> None:
        """Initialize the adapter for one resolved client session."""

        self._runtime_client = client
        self._broker = client.broker
        self._logger = logger.getChild(f"mqtt.{client.client_id}")
        self._client: mqtt.Client | None = None
        self._connected_event = threading.Event()
        self._connect_rc: int | None = None

    async def connect(self) -> None:
        """Connect to the broker and wait for the connect callback."""

        await asyncio.to_thread(self._connect_blocking)

    def _connect_blocking(self) -> None:
        protocol = mqtt.MQTTv5 if self._broker.protocol == "5.0" else mqtt.MQTTv311
        client_kwargs = {
            "callback_api_version": mqtt.CallbackAPIVersion.VERSION2,
            "client_id": self._runtime_client.client_id,
            "protocol": protocol,
            "transport": self._broker.transport,
        }
        if protocol != mqtt.MQTTv5:
            client_kwargs["clean_session"] = self._runtime_client.clean_session
        client = mqtt.Client(
            **client_kwargs,
        )
        if self._broker.auth is not None:
            password = self._broker.auth.password
            if password is None and self._broker.auth.password_env:
                password = os.getenv(self._broker.auth.password_env)
                if password is None:
                    raise BrokerConnectionError(
                        "Missing broker password from environment variable "
                        f"'{self._broker.auth.password_env}' for broker '{self._broker.name}'."
                    )
            client.username_pw_set(self._broker.auth.username, password)
        if self._broker.tls is not None and self._broker.tls.enabled:
            client.tls_set(
                ca_certs=self._broker.tls.ca_file,
                certfile=self._broker.tls.cert_file,
                keyfile=self._broker.tls.key_file,
            )
            if self._broker.tls.insecure:
                client.tls_insecure_set(True)
        will_message = self._runtime_client.lifecycle.get("will")
        if will_message is not None:
            build_result = will_message.payload_builder.build()
            client.will_set(
                will_message.topic,
                payload=build_result.payload_bytes,
                qos=will_message.qos,
                retain=will_message.retain,
            )
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        self._client = client

        try:
            if protocol == mqtt.MQTTv5:
                client.connect(
                    self._broker.host,
                    self._broker.port,
                    self._broker.keepalive,
                    clean_start=self._runtime_client.clean_session,
                )
            else:
                client.connect(self._broker.host, self._broker.port, self._broker.keepalive)
        except Exception as exc:  # pragma: no cover - network-dependent
            raise BrokerConnectionError(
                "Failed to connect client "
                f"'{self._runtime_client.client_id}' to broker '{self._broker.name}' "
                f"({self._broker.host}:{self._broker.port}): {exc}"
            ) from exc

        self._connected_event.clear()
        client.loop_start()
        if not self._connected_event.wait(
            timeout=10
        ):  # pragma: no cover - network-dependent
            raise BrokerConnectionError(
                f"Timed out connecting to broker '{self._broker.name}'."
            )
        if self._connect_rc not in {0, None}:  # pragma: no cover - network-dependent
            raise BrokerConnectionError(
                f"Broker '{self._broker.name}' rejected connect (rc={self._connect_rc})."
            )

    async def publish(
        self,
        topic: str,
        payload: bytes,
        *,
        qos: int = 0,
        retain: bool = False,
    ) -> PublishResult:
        """Publish one message and wait for the client library to finish."""

        if self._client is None:
            raise BrokerPublishError(f"Broker '{self._broker.name}' is not connected.")
        info = self._client.publish(topic, payload=payload, qos=qos, retain=retain)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise BrokerPublishError(
                "Publish failed for topic "
                f"'{topic}' on broker '{self._broker.name}' "
                f"(rc={info.rc})."
            )
        await asyncio.to_thread(info.wait_for_publish)
        return PublishResult(message_id=info.mid)

    async def close(self) -> None:
        """Disconnect and stop the Paho network loop."""

        if self._client is None:
            return
        client = self._client
        self._client = None
        await asyncio.to_thread(self._close_blocking, client)

    def _close_blocking(self, client: mqtt.Client) -> None:
        try:
            client.disconnect()
        finally:
            client.loop_stop()

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object | None,
        flags: object,
        reason_code: object,
        properties: object | None,
    ) -> None:
        """Record the connect callback result."""

        del client, userdata, flags, properties
        self._connect_rc = _reason_code_value(reason_code)
        self._connected_event.set()

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object | None,
        disconnect_flags: object,
        reason_code: object,
        properties: object | None,
    ) -> None:
        """Log broker disconnects for troubleshooting."""

        del client, userdata, disconnect_flags, properties
        self._logger.debug("Broker disconnected rc=%s", _reason_code_value(reason_code))


def _reason_code_value(reason_code: object) -> int:
    """Return a stable integer-like code from Paho callback reason codes.

    Paho callback API v2 passes ``ReasonCode`` instances (not plain ints), and
    they do not implement ``__int__``. This helper normalizes both old and new
    callback styles.
    # TODO do we need this?
    """

    if isinstance(reason_code, int):
        return reason_code

    value = getattr(reason_code, "value", None)
    if isinstance(value, int):
        return value

    try:
        return int(str(reason_code))
    except (TypeError, ValueError):
        return -1
