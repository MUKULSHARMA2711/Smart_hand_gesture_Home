"""Environment readings reported by ESP32 sensors over MQTT (home/sensors/{kind}).

Every reading keeps its value, timestamp and sensor id. ``read()`` only returns readings
that are present, valid and fresh (younger than ``max_age_s``). Otherwise it raises
SensorError naming what is wrong, and HomeState reports the environment as unavailable,
so stale or implausible data never reaches the dashboard, AI or ML as current.
Missing values are never filled in.
"""

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.mqtt.errors import MessageError
from app.mqtt.messages import SensorMessage, decode
from app.mqtt.topics import SENSOR_KINDS
from app.sensors.base import (
    MAX_AMBIENT_LIGHT_LUX,
    MAX_OCCUPANTS,
    TEMPERATURE_RANGE_C,
    Occupancy,
    SensorError,
    SensorProvider,
    SensorReadings,
)

logger = logging.getLogger(__name__)

MAX_CLOCK_SKEW_S = 5.0  # a reading timestamped further in the future than this is rejected

_BOUNDS: dict[str, tuple[float, float]] = {
    "temperature": TEMPERATURE_RANGE_C,
    "humidity": (0.0, 100.0),
    "occupancy": (0.0, float(MAX_OCCUPANTS)),
    "ambient_light": (0.0, MAX_AMBIENT_LIGHT_LUX),
}


@dataclass(frozen=True)
class SensorReading:
    kind: str
    sensor_id: str
    value: float
    timestamp: datetime  # when the sensor measured it
    received_at: datetime


class MQTTSensorProvider(SensorProvider):
    def __init__(self, *, max_age_s: float = 30.0, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._max_age_s = max_age_s
        self._clock = clock
        self._readings: dict[str, SensorReading] = {}
        self._rejected: dict[str, str] = {}  # kind -> why its latest message was rejected
        self._board_online: bool | None = None  # from home/sensors/availability (Last Will)

    def set_board_online(self, online: bool) -> None:
        """An offline sensor board makes its readings unavailable at once, not after max_age_s."""
        self._board_online = online

    def handle(self, kind: str, payload: bytes) -> None:
        """Accept one message from home/sensors/{kind}. Never raises."""
        now = self._clock()
        try:
            message = decode(SensorMessage, payload)
        except MessageError as exc:
            self._reject(kind, f"malformed message ({exc})")
            return
        if (message.timestamp - now).total_seconds() > MAX_CLOCK_SKEW_S:
            self._reject(kind, f"timestamp {message.timestamp.isoformat()} is in the future")
            return
        problem = _value_problem(kind, message.value)
        if problem:
            self._reject(kind, problem)
            return
        self._readings[kind] = SensorReading(kind, message.sensor_id, message.value, message.timestamp, now)
        if self._rejected.pop(kind, None) is not None:
            logger.info("Sensor %s recovered", kind)

    def read(self) -> SensorReadings:
        if self._board_online is False:
            raise SensorError("Sensor data unavailable: the sensor board is offline.")
        problems = [problem for kind in SENSOR_KINDS if (problem := self._problem(kind))]
        if problems:
            raise SensorError("Sensor data unavailable: " + "; ".join(problems) + ".")
        r = self._readings
        people = int(r["occupancy"].value)
        return SensorReadings(
            temperature_c=round(r["temperature"].value, 1),
            humidity_pct=round(r["humidity"].value, 1),
            occupancy=Occupancy(occupied=people > 0, occupant_count=people),
            ambient_light_lux=round(r["ambient_light"].value, 1),
        )

    def status(self) -> dict[str, dict[str, Any]]:
        """Per-sensor freshness, for GET /iot/status."""
        result: dict[str, dict[str, Any]] = {}
        for kind in SENSOR_KINDS:
            reading = self._readings.get(kind)
            problem = self._problem(kind)
            result[kind] = {
                "status": "ok" if problem is None else ("invalid" if kind in self._rejected else "stale" if reading else "missing"),
                "problem": problem,
                "sensor_id": reading.sensor_id if reading else None,
                "value": reading.value if reading and problem is None else None,
                "timestamp": reading.timestamp if reading else None,
                "age_s": round(self._age(reading), 1) if reading else None,
            }
        return result

    def _problem(self, kind: str) -> str | None:
        if self._board_online is False:
            return f"{kind} unavailable (sensor board offline)"
        if kind in self._rejected:
            return f"{kind} rejected: {self._rejected[kind]}"
        reading = self._readings.get(kind)
        if reading is None:
            return f"{kind} has not reported"
        age = self._age(reading)
        if age > self._max_age_s:
            return f"{kind} is stale ({age:.0f} s old, limit {self._max_age_s:g} s)"
        return None

    def _age(self, reading: SensorReading) -> float:
        return max(0.0, (self._clock() - reading.timestamp).total_seconds())

    def _reject(self, kind: str, reason: str) -> None:
        if self._rejected.get(kind) != reason:
            logger.warning("Rejected %s reading: %s", kind, reason)
        self._rejected[kind] = reason


def _value_problem(kind: str, value: float) -> str | None:
    low, high = _BOUNDS[kind]
    if not math.isfinite(value) or not low <= value <= high:
        return f"{value:g} is outside the plausible range {low:g} to {high:g}"
    if kind == "occupancy" and value != int(value):
        return f"occupant count {value:g} is not a whole number"
    return None
