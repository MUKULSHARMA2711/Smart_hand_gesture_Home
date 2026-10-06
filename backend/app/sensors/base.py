"""Environmental sensor abstraction."""

from abc import ABC, abstractmethod
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Physically plausible bounds (DHT22: -40-80 °C; direct sunlight is ~100 000 lux). Readings
# outside them are rejected as sensor faults rather than passed on to the AI and ML layers.
TEMPERATURE_RANGE_C = (-40.0, 85.0)
MAX_AMBIENT_LIGHT_LUX = 200_000.0
MAX_OCCUPANTS = 100


class SensorError(Exception):
    """A sensor could not produce a valid reading (offline, faulty or implausible value)."""


class Occupancy(BaseModel):
    model_config = ConfigDict(strict=True)

    occupied: bool
    occupant_count: int = Field(ge=0, le=MAX_OCCUPANTS)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.occupied != (self.occupant_count > 0):
            raise ValueError(
                f"Inconsistent occupancy: occupied={self.occupied} with {self.occupant_count} occupant(s)."
            )
        return self


class SensorReadings(BaseModel):
    temperature_c: float = Field(ge=TEMPERATURE_RANGE_C[0], le=TEMPERATURE_RANGE_C[1], allow_inf_nan=False)
    humidity_pct: float = Field(ge=0, le=100, allow_inf_nan=False)
    occupancy: Occupancy
    ambient_light_lux: float = Field(ge=0, le=MAX_AMBIENT_LIGHT_LUX, allow_inf_nan=False)


class SensorProvider(ABC):
    """Source of environmental readings.

    ``SimulatedSensorProvider`` today; later an MQTT-backed provider that returns the
    latest values reported by ESP32 sensors (DHT22, PIR, LDR, ...). Implementations
    raise :class:`SensorError` (or a pydantic ``ValidationError``) instead of returning
    readings they cannot vouch for.
    """

    @abstractmethod
    def read(self) -> SensorReadings:
        """Return the most recent readings."""
