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
    ERROR = "error"


class DeviceDriver(StrEnum):
    """Which implementation backs a configured device.

    Real hardware is added here later, e.g. ``ESP32_MQTT = "esp32_mqtt"``.
    """

    VIRTUAL = "virtual"
