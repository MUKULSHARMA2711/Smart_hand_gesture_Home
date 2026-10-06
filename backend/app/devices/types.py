"""Enumerations shared across the device layer."""

from enum import StrEnum


class DeviceType(StrEnum):
    LIGHT = "light"
    FAN = "fan"
    AC = "ac"
    DOOR_LOCK = "door_lock"


class DeviceStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"  # no availability report yet, broker unreachable, or not responding
    ERROR = "error"


class Capability(StrEnum):
    """An explicit thing a device can do. Each device command declares exactly one.

    Capabilities are deliberately unambiguous: a door lock has LOCK and UNLOCK only,
    so a generic intent such as "turn on" can never reach it.
    """

    TURN_ON = "TURN_ON"
    TURN_OFF = "TURN_OFF"
    SET_BRIGHTNESS = "SET_BRIGHTNESS"
    SET_SPEED = "SET_SPEED"
    SET_TEMPERATURE = "SET_TEMPERATURE"
    LOCK = "LOCK"
    UNLOCK = "UNLOCK"


class DeviceDriver(StrEnum):
    """Which implementation backs a configured device.

    Both kinds can run side by side, so devices can move to hardware one at a time.
    """

    VIRTUAL = "virtual"
    ESP32_MQTT = "esp32_mqtt"
