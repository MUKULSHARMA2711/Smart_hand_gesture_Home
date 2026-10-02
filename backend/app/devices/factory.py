"""Builds concrete devices from configuration."""

from collections.abc import Callable

from app.config import DeviceConfig
from app.devices.base import Device
from app.devices.types import DeviceDriver, DeviceType
from app.devices.virtual import VirtualAC, VirtualDoorLock, VirtualFan, VirtualLight

_VIRTUAL_DEVICES: dict[DeviceType, Callable[..., Device]] = {
    DeviceType.LIGHT: VirtualLight,
    DeviceType.FAN: VirtualFan,
    DeviceType.AC: VirtualAC,
    DeviceType.DOOR_LOCK: VirtualDoorLock,
}


def build_device(config: DeviceConfig, *, virtual_latency_s: float = 0.0) -> Device:
    """Instantiate the implementation selected by ``config.driver``.

    This is the only place that knows which concrete class backs a device. Real
    hardware is added by handling a new driver here, for example::

        if config.driver is DeviceDriver.ESP32_MQTT:
            return ESP32MQTTDevice(config.id, config.name, config.room,
                                   spec=SPECS_BY_TYPE[config.type], mqtt=mqtt_client)
    """
    if config.driver is DeviceDriver.VIRTUAL:
        device_cls = _VIRTUAL_DEVICES[config.type]
        return device_cls(config.id, config.name, config.room, latency_s=virtual_latency_s)
    raise ValueError(f"Unsupported driver '{config.driver}' for device '{config.id}'.")
