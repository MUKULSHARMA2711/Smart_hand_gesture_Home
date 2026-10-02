from collections.abc import Iterable

from app.devices.base import Device
from app.domain.errors import DeviceNotFoundError


class DeviceRegistry:
    """Lookup of all devices in the home by id, in registration order."""

    def __init__(self, devices: Iterable[Device] = ()) -> None:
        self._devices: dict[str, Device] = {}
        for device in devices:
            self.register(device)

    def register(self, device: Device) -> None:
        if device.id in self._devices:
            raise ValueError(f"Duplicate device id '{device.id}'.")
        self._devices[device.id] = device

    def get(self, device_id: str) -> Device:
        try:
            return self._devices[device_id]
        except KeyError:
            raise DeviceNotFoundError(device_id) from None

    def all(self) -> list[Device]:
        return list(self._devices.values())

    def __contains__(self, device_id: object) -> bool:
        return device_id in self._devices

    def __len__(self) -> int:
        return len(self._devices)
