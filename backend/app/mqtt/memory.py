"""An in-process MQTT broker with the semantics the system relies on: topic wildcards,
retained messages and Last Will on an unclean disconnect.

Used by the test suite (and usable for demos) so the full backend ↔ FakeESP32 protocol
runs without a broker process. It implements the same MQTTTransport interface as
PahoTransport, so nothing else knows the difference.
"""

from paho.mqtt.client import topic_matches_sub

from app.mqtt.client import ConnectionHandler, MessageHandler, Will


class InMemoryBroker:
    def __init__(self) -> None:
        self._clients: list["InMemoryTransport"] = []
        self.retained: dict[str, bytes] = {}
        self.published: list[tuple[str, bytes, bool]] = []  # every message, for assertions

    def client(self, client_id: str = "client", *, will: Will | None = None) -> "InMemoryTransport":
        return InMemoryTransport(self, client_id, will)

    def route(self, topic: str, payload: bytes, retain: bool) -> None:
        self.published.append((topic, payload, retain))
        if retain:
            if payload:
                self.retained[topic] = payload
            else:
                self.retained.pop(topic, None)  # an empty retained message clears the topic
        for client in list(self._clients):
            if any(topic_matches_sub(sub, topic) for sub in client.subscriptions):
                client.deliver(topic, payload)

    def attach(self, client: "InMemoryTransport") -> None:
        self._clients.append(client)

    def detach(self, client: "InMemoryTransport", *, clean: bool) -> None:
        if client in self._clients:
            self._clients.remove(client)
            if not clean and client.will is not None:
                will = client.will
                self.route(will.topic, will.payload.encode(), will.retain)


class InMemoryTransport:
    def __init__(self, broker: InMemoryBroker, client_id: str, will: Will | None) -> None:
        self.broker, self.client_id, self.will = broker, client_id, will
        self.subscriptions: dict[str, int] = {}
        self._connected = False
        self.on_message: MessageHandler | None = None
        self.on_connection_change: ConnectionHandler | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        if self._connected:
            return
        self.broker.attach(self)
        self._set_connected(True)
        for topic_filter in self.subscriptions:
            self._deliver_retained(topic_filter)

    def stop(self) -> None:
        self.broker.detach(self, clean=True)
        self._set_connected(False)

    def abort(self) -> None:
        """Unclean disconnect: the broker publishes the Will (simulated power cut / Wi-Fi loss)."""
        self.broker.detach(self, clean=False)
        self._set_connected(False)

    def subscribe(self, topic_filter: str, qos: int = 1) -> None:
        self.subscriptions[topic_filter] = qos
        if self._connected:
            self._deliver_retained(topic_filter)

    def publish(self, topic: str, payload: bytes | str, *, qos: int = 1, retain: bool = False) -> bool:
        if not self._connected:
            return False
        self.broker.route(topic, payload.encode() if isinstance(payload, str) else payload, retain)
        return True

    def deliver(self, topic: str, payload: bytes) -> None:
        if self.on_message is not None:
            self.on_message(topic, payload)

    def _deliver_retained(self, topic_filter: str) -> None:
        for topic, payload in list(self.broker.retained.items()):
            if topic_matches_sub(topic_filter, topic):
                self.deliver(topic, payload)

    def _set_connected(self, connected: bool) -> None:
        if connected != self._connected:
            self._connected = connected
            if self.on_connection_change is not None:
                self.on_connection_change(connected)
