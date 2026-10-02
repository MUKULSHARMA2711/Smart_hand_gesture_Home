"""Simulated environmental sensors producing realistic, slowly varying readings."""

import math
import random
from collections.abc import Callable
from datetime import datetime

from app.sensors.base import Occupancy, SensorProvider, SensorReadings


class SimulatedSensorProvider(SensorProvider):
    """Indoor readings that follow a daily cycle plus mean-reverting noise.

    * temperature peaks mid-afternoon (~30 °C) and bottoms out before dawn (~22 °C)
    * humidity moves inversely to temperature
    * ambient light follows daylight hours (6:00-18:00)
    * occupancy occasionally changes by one person
    """

    BASE_TEMPERATURE_C = 26.0
    TEMPERATURE_SWING_C = 4.0
    BASE_HUMIDITY_PCT = 58.0
    HUMIDITY_SWING_PCT = 12.0
    PEAK_DAYLIGHT_LUX = 650.0
    NIGHT_LUX = 3.0
    MAX_OCCUPANTS = 4
    OCCUPANCY_CHANGE_PROBABILITY = 0.1

    def __init__(self, *, seed: int | None = None, clock: Callable[[], datetime] = datetime.now) -> None:
        self._rng = random.Random(seed)
        self._clock = clock
        self._temperature_noise = 0.0
        self._humidity_noise = 0.0
        self._occupants = 2

    def read(self) -> SensorReadings:
        now = self._clock()
        hour = now.hour + now.minute / 60
        daily_cycle = math.sin(2 * math.pi * (hour - 9) / 24)  # +1 at 15:00, -1 at 03:00

        self._temperature_noise = 0.8 * self._temperature_noise + self._rng.gauss(0, 0.15)
        self._humidity_noise = 0.8 * self._humidity_noise + self._rng.gauss(0, 0.6)
        if self._rng.random() < self.OCCUPANCY_CHANGE_PROBABILITY:
            change = self._rng.choice((-1, 1))
            self._occupants = min(self.MAX_OCCUPANTS, max(0, self._occupants + change))

        temperature = self.BASE_TEMPERATURE_C + self.TEMPERATURE_SWING_C * daily_cycle + self._temperature_noise
        humidity = self.BASE_HUMIDITY_PCT - self.HUMIDITY_SWING_PCT * daily_cycle + self._humidity_noise
        return SensorReadings(
            temperature_c=round(temperature, 1),
            humidity_pct=round(min(95.0, max(20.0, humidity)), 1),
            occupancy=Occupancy(occupied=self._occupants > 0, occupant_count=self._occupants),
            ambient_light_lux=round(self._ambient_light(hour), 1),
        )

    def _ambient_light(self, hour: float) -> float:
        if 6 <= hour <= 18:
            daylight = math.sin(math.pi * (hour - 6) / 12)
            return max(self.NIGHT_LUX, self.PEAK_DAYLIGHT_LUX * daylight * self._rng.uniform(0.9, 1.1))
        return self.NIGHT_LUX * self._rng.uniform(0.8, 1.2)
