"""Environmental sensor abstraction."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class Occupancy(BaseModel):
    occupied: bool
    occupant_count: int = Field(ge=0)


class SensorReadings(BaseModel):
    temperature_c: float
    humidity_pct: float = Field(ge=0, le=100)
    occupancy: Occupancy
    ambient_light_lux: float = Field(ge=0)


class SensorProvider(ABC):
    """Source of environmental readings.

    ``SimulatedSensorProvider`` today; later an MQTT-backed provider that returns the
    latest values reported by ESP32 sensors (DHT22, PIR, LDR, ...).
    """

    @abstractmethod
    def read(self) -> SensorReadings:
        """Return the most recent readings."""
