import logging
from datetime import UTC, datetime

from pydantic import BaseModel, Field, ValidationError

from app.devices.base import DeviceSnapshot
from app.devices.registry import DeviceRegistry
from app.domain.energy import EnergyMeter
from app.sensors.base import SensorError, SensorProvider, SensorReadings

logger = logging.getLogger(__name__)


class EnergySnapshot(BaseModel):
    total_power_w: float
    energy_kwh: float = Field(description="Energy used by monitored devices since the backend started.")
    per_device_w: dict[str, float]


class HomeStateSnapshot(BaseModel):
    timestamp: datetime
    # None when the sensors are offline or reported implausible values; never guessed.
    environment: SensorReadings | None
    sensor_error: str | None = None
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
        self._sensor_error: str | None = None

    @property
    def devices(self) -> DeviceRegistry:
        return self._devices

    def total_power_w(self) -> float:
        return round(sum(device.power_w for device in self._devices.all()), 2)

    def record_energy(self) -> None:
        """Close the current metering interval at the present power draw."""
        self._energy_meter.accumulate(self.total_power_w())

    def read_environment(self) -> tuple[SensorReadings | None, str | None]:
        """Current readings, or ``(None, reason)`` if the sensors failed or reported garbage.

        A sensor fault must not take down the dashboard or device control, and implausible
        values must not reach the AI or ML layers as if they were real.
        """
        try:
            readings = self._sensors.read()
        except (SensorError, ValidationError) as exc:
            reason = _describe_sensor_error(exc)
        except Exception as exc:  # a broken provider is still only a sensor outage
            logger.exception("Sensor provider failed")
            reason = f"Sensor provider failed: {type(exc).__name__}"
        else:
            if self._sensor_error is not None:
                logger.info("Sensors recovered")
            self._sensor_error = None
            return readings, None

        if reason != self._sensor_error:  # log transitions, not every poll
            logger.warning("Sensor readings unavailable: %s", reason)
        self._sensor_error = reason
        return None, reason

    def snapshot(self) -> HomeStateSnapshot:
        self.record_energy()
        devices = [device.snapshot() for device in self._devices.all()]
        per_device_w = {device.id: device.power_w for device in devices}
        environment, sensor_error = self.read_environment()
        return HomeStateSnapshot(
            timestamp=datetime.now(UTC),
            environment=environment,
            sensor_error=sensor_error,
            energy=EnergySnapshot(
                total_power_w=round(sum(per_device_w.values()), 2),
                energy_kwh=round(self._energy_meter.energy_kwh, 6),
                per_device_w=per_device_w,
            ),
            devices=devices,
        )


def _describe_sensor_error(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        problems = "; ".join(
            f"{'.'.join(str(p) for p in error['loc']) or 'reading'}: {error['msg']}" for error in exc.errors()
        )
        return f"Implausible sensor reading rejected ({problems})."
    return str(exc) or "Sensors are unavailable."
