class MQTTError(Exception):
    """Base class for transport-level MQTT problems."""


class MessageError(MQTTError):
    """A payload did not match the message contract (bad JSON, wrong schema, wrong values)."""
