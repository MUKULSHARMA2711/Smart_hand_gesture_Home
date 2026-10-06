"""Builds concrete devices from configuration."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from app.config import DeviceConfig
from app.devices.base import Device
from app.devices.power import POWER_MODELS
from app.devices.specs import SPECS_BY_TYPE
from app.devices.types import DeviceDriver, DeviceType
from app.devices.virtual import VirtualAC, VirtualDoorLock, VirtualFan, VirtualLight

if TYPE_CHECKING:
    from app.mqtt.manager import MQTTManager

_VIRTUAL_DEVICES: dict[DeviceType, Callable[..., Device]] = {
    DeviceType.LIGHT: VirtualLight,
    DeviceType.FAN: VirtualFan,
    DeviceType.AC: VirtualAC,
    DeviceType.DOOR_LOCK: VirtualDoorLock,
}


def build_device(
    config: DeviceConfig,
    *,
    virtual_latency_s: float = 0.0,
    mqtt: "MQTTManager | None" = None,
    command_timeout_s: float = 3.0,
    measurement_max_age_s: float = 30.0,
) -> Device:
    """Instantiate the implementation selected by ``config.driver``.

    This is the only place that knows which concrete class backs a device. Virtual and
    ESP32 devices can be mixed freely; everything above the Device interface (CommandService,
    gestures, the AI agent, the UI) is unaware of the difference.
    """
    if config.driver is DeviceDriver.VIRTUAL:
        device_cls = _VIRTUAL_DEVICES[config.type]
        return device_cls(config.id, config.name, config.room, latency_s=virtual_latency_s)
    if config.driver is DeviceDriver.ESP32_MQTT:
        if mqtt is None:
            raise ValueError(f"Device '{config.id}' uses the esp32_mqtt driver, but MQTT is not enabled.")
        from app.devices.esp32 import ESP32MQTTDevice

        device = ESP32MQTTDevice(
            config.id,
            config.name,
            config.room,
            SPECS_BY_TYPE[config.type],
            link=mqtt,
            power_model=POWER_MODELS[config.type],
            command_timeout_s=command_timeout_s,
            measurement_max_age_s=measurement_max_age_s,
        )
        mqtt.register_device(device)
        return device
    raise ValueError(f"Unsupported driver '{config.driver}' for device '{config.id}'.")
