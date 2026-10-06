"""MQTT transport: the only module that talks to the MQTT client library (paho-mqtt).

One transport is one MQTT connection. The backend uses a single shared connection for
all hardware devices and sensors (see MQTTManager); each FakeESP32 board uses its own,
as a real ESP32 would.

Callbacks (``on_message``, ``on_connection_change``) run on the transport's network
thread. Consumers must hand work over to their event loop (MQTTManager does).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)

MessageHandler = Callable[[str, bytes], None]
ConnectionHandler = Callable[[bool], None]


@dataclass(frozen=True)
class Will:
    """Last Will and Testament: published by the broker if the connection drops uncleanly."""

    topic: str
    payload: str
    retain: bool = True
    qos: int = 1


class MQTTTransport(Protocol):
    on_message: MessageHandler | None
    on_connection_change: ConnectionHandler | None

    @property
    def connected(self) -> bool: ...

    def start(self) -> None:
        """Begin connecting in the background (never blocks; retries until stopped)."""

    def stop(self) -> None:
        """Disconnect cleanly (no Last Will) and stop the network thread."""

    def subscribe(self, topic_filter: str, qos: int = 1) -> None:
        """Subscribe now and again after every reconnect."""

    def publish(self, topic: str, payload: bytes | str, *, qos: int = 1, retain: bool = False) -> bool:
        """Queue a message; False if not connected (nothing is buffered for later)."""


class PahoTransport:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        client_id: str,
        username: str | None = None,
        password: str | None = None,
        keepalive_s: int = 30,
        will: Will | None = None,
    ) -> None:
        import paho.mqtt.client as mqtt  # imported lazily: only needed when MQTT is enabled

        self._mqtt = mqtt
        self._host, self._port, self._keepalive = host, port, keepalive_s
        self._subscriptions: dict[str, int] = {}
        self._connected = False
        self._last_publish = None  # paho MQTTMessageInfo of the most recent publish
        self.on_message: MessageHandler | None = None
        self.on_connection_change: ConnectionHandler | None = None

        # Clean session: a command must never be queued by the broker and delivered later.
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=True)
        if username:
            self._client.username_pw_set(username, password)  # never logged
        if will is not None:
            self._client.will_set(will.topic, will.payload, qos=will.qos, retain=will.retain)
        self._client.reconnect_delay_set(min_delay=1, max_delay=15)
        self._client.on_connect = self._handle_connect
        self._client.on_disconnect = self._handle_disconnect
        self._client.on_message = self._handle_message
        self._label = f"{client_id}@{host}:{port}"

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        logger.info("MQTT connecting to %s", self._label)
        self._client.connect_async(self._host, self._port, keepalive=self._keepalive)
        self._client.loop_start()  # background thread; retries the first connection too

    def stop(self, flush_timeout_s: float = 2.0) -> None:
        # Deliver what is already queued (typically a final "offline") before disconnecting:
        # a clean DISCONNECT suppresses the Last Will, so a lost message would never be replaced.
        if self._connected and self._last_publish is not None:
            try:
                self._last_publish.wait_for_publish(timeout=flush_timeout_s)
            except (RuntimeError, ValueError):
                logger.warning("MQTT %s: could not flush pending messages before disconnecting", self._label)
        self._client.disconnect()
        self._client.loop_stop()
        self._set_connected(False)

    def abort(self) -> None:
        """Drop the connection without a DISCONNECT packet, so the broker publishes the Will.
        Used by FakeESP32 to simulate a power cut."""
        self._client.loop_stop()
        sock = self._client.socket()
        if sock is not None:
            sock.close()
        self._set_connected(False)

    def subscribe(self, topic_filter: str, qos: int = 1) -> None:
        self._subscriptions[topic_filter] = qos
        if self._connected:
            self._client.subscribe(topic_filter, qos)

    def publish(self, topic: str, payload: bytes | str, *, qos: int = 1, retain: bool = False) -> bool:
        if not self._connected:
            return False
        info = self._client.publish(topic, payload, qos=qos, retain=retain)
        self._last_publish = info  # messages leave in order: waiting for the last covers all
        return info.rc == self._mqtt.MQTT_ERR_SUCCESS

    # --- paho callbacks (network thread) ------------------------------------------------

    def _handle_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            logger.warning("MQTT connection to %s refused: %s", self._label, reason_code)
            return
        for topic_filter, qos in self._subscriptions.items():
            client.subscribe(topic_filter, qos)
        logger.info("MQTT connected to %s", self._label)
        self._set_connected(True)

    def _handle_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        if self._connected:
            logger.warning("MQTT disconnected from %s (%s); reconnecting", self._label, reason_code)
        self._set_connected(False)

    def _handle_message(self, client, userdata, message) -> None:
        if self.on_message is not None:
            self.on_message(message.topic, message.payload)

    def _set_connected(self, connected: bool) -> None:
        if connected != self._connected:
            self._connected = connected
            if self.on_connection_change is not None:
                self.on_connection_change(connected)
