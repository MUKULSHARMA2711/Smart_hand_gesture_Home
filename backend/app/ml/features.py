"""Feature extraction: HomeState snapshot → model inputs.

The same definitions are used to build the simulated training set and live inputs.
"""

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import math

from app.domain.home_state import HomeStateSnapshot
from app.events.models import DeviceEvent
from app.sensors.base import MAX_AMBIENT_LIGHT_LUX, MAX_OCCUPANTS, TEMPERATURE_RANGE_C

FAN_DEVICE_ID = "fan_living_room"
RECENT_WINDOW = timedelta(minutes=30)

FAN_FEATURES: tuple[str, ...] = (
    "hour",
    "day_of_week",
    "temperature_c",
    "humidity_pct",
    "occupied",
    "occupant_count",
    "ambient_light_lux",
    "fan_on",
    "fan_recently_on",
)

FEATURE_LABELS = {
    "hour": "Hour of day",
    "day_of_week": "Day of week",
    "temperature_c": "Temperature",
    "humidity_pct": "Humidity",
    "occupied": "Occupancy",
    "occupant_count": "People home",
    "ambient_light_lux": "Ambient light",
    "fan_on": "Fan currently on",
    "fan_recently_on": "Fan used in last 30 min",
}

POWER_FEATURES: tuple[str, ...] = ("setting_level", "power_w")

# Inputs that come from environmental sensors. If any is missing the prediction is still
# made (imputed with typical values) but flagged as unreliable.
SENSOR_FEATURES: tuple[str, ...] = ("temperature_c", "humidity_pct", "occupied", "occupant_count", "ambient_light_lux")

# Plausible range of every fan-model input; the same bounds the sensor layer enforces.
FEATURE_BOUNDS: dict[str, tuple[float, float]] = {
    "hour": (0.0, 24.0),
    "day_of_week": (0.0, 6.0),
    "temperature_c": TEMPERATURE_RANGE_C,
    "humidity_pct": (0.0, 100.0),
    "occupied": (0.0, 1.0),
    "occupant_count": (0.0, float(MAX_OCCUPANTS)),
    "ambient_light_lux": (0.0, MAX_AMBIENT_LIGHT_LUX),
    "fan_on": (0.0, 1.0),
    "fan_recently_on": (0.0, 1.0),
}
_BINARY_FEATURES = frozenset({"occupied", "fan_on", "fan_recently_on"})


def feature_errors(features: Mapping[str, float | None]) -> list[dict[str, Any]]:
    """Problems with caller-supplied features: unknown names, non-finite or implausible values."""
    errors: list[dict[str, Any]] = []
    for name, value in features.items():
        if name not in FEATURE_BOUNDS:
            errors.append({"feature": name, "message": f"Unknown feature. Expected one of: {', '.join(FAN_FEATURES)}."})
            continue
        if value is None:
            continue  # explicitly missing: imputed and reported
        low, high = FEATURE_BOUNDS[name]
        if not math.isfinite(value):
            errors.append({"feature": name, "message": "Must be a finite number."})
        elif not low <= value <= high:
            errors.append({"feature": name, "message": f"{value:g} is outside the plausible range {low:g} to {high:g}."})
        elif name in _BINARY_FEATURES and value not in (0, 1):
            errors.append({"feature": name, "message": "Must be 0 or 1."})
    return errors


def fan_features(
    snapshot: HomeStateSnapshot,
    now: datetime,
    recent_events: Iterable[DeviceEvent] = (),
    fan_id: str = FAN_DEVICE_ID,
) -> dict[str, float | None]:
    """Inputs for the fan-usage model. Values the snapshot lacks are returned as None."""
    env = snapshot.environment
    fan = next((device for device in snapshot.devices if device.id == fan_id), None)
    fan_on = float(bool(fan.state.get("is_on"))) if fan else None

    now_utc = now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
    recently = bool(fan_on) or any(
        event.device_id == fan_id
        and event.new_state.get("is_on")
        and now_utc - event.timestamp <= RECENT_WINDOW
        for event in recent_events
    )
    return {
        "hour": round(now.hour + now.minute / 60, 3),
        "day_of_week": float(now.weekday()),
        "temperature_c": env.temperature_c if env else None,
        "humidity_pct": env.humidity_pct if env else None,
        "occupied": float(env.occupancy.occupied) if env else None,
        "occupant_count": float(env.occupancy.occupant_count) if env else None,
        "ambient_light_lux": env.ambient_light_lux if env else None,
        "fan_on": fan_on,
        "fan_recently_on": float(recently) if fan is not None else None,
    }


def setting_level(device_type: str, state: Mapping[str, Any]) -> float:
    """Device setting the power draw depends on: 0 when off, 10-100 when on.

    "On" never maps to 0, so the detector can always tell standby from running.
    """
    if device_type in ("light", "fan"):
        if not state.get("is_on"):
            return 0.0
        value = float(state.get("brightness" if device_type == "light" else "speed", 0))
        return round(10 + 0.9 * value, 2)
    if device_type == "ac":
        if not state.get("is_on"):
            return 0.0
        # Colder set points work harder: 30 °C → 10, 16 °C → 100.
        return round(10 + 90 * (30 - float(state.get("target_temperature_c", 24))) / 14, 2)
    return 0.0  # door lock: standby only


def describe_setting(device_type: str, state: Mapping[str, Any]) -> str:
    if device_type == "light":
        return f"on at {state.get('brightness')}%" if state.get("is_on") else "off"
    if device_type == "fan":
        return f"on at speed {state.get('speed')}%" if state.get("is_on") else "off"
    if device_type == "ac":
        return f"on, set to {state.get('target_temperature_c')} °C" if state.get("is_on") else "off"
    if device_type == "door_lock":
        return "locked" if state.get("is_locked") else "unlocked"
    return "unknown"
