from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.devices.base import DeviceSnapshot
from app.devices.registry import DeviceRegistry
from app.domain.energy import EnergyMeter
from app.sensors.base import SensorProvider, SensorReadings


class EnergySnapshot(BaseModel):
    total_power_w: float
    energy_kwh: float = Field(description="Energy used by monitored devices since the backend started.")
    per_device_w: dict[str, float]


class HomeStateSnapshot(BaseModel):
    timestamp: datetime
    environment: SensorReadings
    energy: EnergySnapshot
    devices: list[DeviceSnapshot]


class HomeState:
    """In-memory aggregate of everything known about the home: devices, sensors, energy."""

    def __init__(
        self,
        devices: DeviceRegistry,
        sensors: SensorProvider,
        energy_meter: EnergyMeter | None = None,
    ) -> None:
        self._devices = devices
        self._sensors = sensors
        self._energy_meter = energy_meter or EnergyMeter()

    @property
    def devices(self) -> DeviceRegistry:
        return self._devices

    def total_power_w(self) -> float:
        return round(sum(device.power_w for device in self._devices.all()), 2)

    def record_energy(self) -> None:
        """Close the current metering interval at the present power draw."""
        self._energy_meter.accumulate(self.total_power_w())

    def snapshot(self) -> HomeStateSnapshot:
        self.record_energy()
        devices = [device.snapshot() for device in self._devices.all()]
        per_device_w = {device.id: device.power_w for device in devices}
        return HomeStateSnapshot(
            timestamp=datetime.now(UTC),
            environment=self._sensors.read(),
            energy=EnergySnapshot(
                total_power_w=round(sum(per_device_w.values()), 2),
                energy_kwh=round(self._energy_meter.energy_kwh, 6),
                per_device_w=per_device_w,
            ),
            devices=devices,
        )
