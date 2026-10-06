"""Deterministic *simulated* training data, pending real sensor history.

Both datasets reuse IntelliHome's own models so the correlations are realistic:
* the fan-usage history follows the same daily temperature/humidity/daylight cycle as
  SimulatedSensorProvider, an occupancy schedule, and a comfort-driven fan behaviour;
* power history uses the existing virtual device power estimates plus meter noise,
  with a small number of injected faults.

Every random draw comes from a seeded generator, so the data (and the models) are
reproducible.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from app.devices.specs.ac import AcState
from app.devices.specs.door import DoorLockState
from app.devices.specs.fan import FanState
from app.devices.specs.light import LightState
from app.devices.virtual import VirtualAC, VirtualDoorLock, VirtualFan, VirtualLight
from app.ml.features import FAN_FEATURES, POWER_FEATURES, setting_level

HORIZON_STEPS = 2  # "soon" = within the next two 15-minute steps (30 minutes)


@dataclass(frozen=True)
class Dataset:
    features: np.ndarray
    labels: np.ndarray
    feature_names: tuple[str, ...]
    metadata: dict = field(default_factory=dict)


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def generate_fan_dataset(*, days: int = 60, step_minutes: int = 15, seed: int = 7) -> Dataset:
    """Simulated living-room history labelled with FAN_ON_SOON (fan on within 30 min)."""
    rng = np.random.default_rng(seed)
    start = datetime(2026, 4, 1)
    steps = days * 24 * 60 // step_minutes
    day_weather = rng.normal(0, 1.6, size=days + 1)  # hotter / cooler days
    day_clouds = rng.uniform(0.55, 1.0, size=days + 1)

    rows: list[list[float]] = []
    fan_states: list[bool] = []
    fan_on = False
    occupied = True
    occupants = 2
    temp_noise = 0.0
    hum_noise = 0.0

    for i in range(steps):
        t = start + timedelta(minutes=i * step_minutes)
        day = (t - start).days
        hour = t.hour + t.minute / 60
        weekend = t.weekday() >= 5
        cycle = math.sin(2 * math.pi * (hour - 9) / 24)  # +1 at 15:00, as in the sensor simulator

        temp_noise = 0.8 * temp_noise + rng.normal(0, 0.2)
        hum_noise = 0.8 * hum_noise + rng.normal(0, 0.8)
        temperature = 26 + 4 * cycle + day_weather[day] + temp_noise
        humidity = float(np.clip(58 - 12 * cycle - 1.5 * day_weather[day] + hum_noise, 25, 95))
        daylight = math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 0.0
        ambient = max(3.0, 650 * daylight * day_clouds[day] * rng.uniform(0.9, 1.1)) if daylight else 3 * rng.uniform(0.8, 1.2)

        # Occupancy schedule with persistence: away on weekday working hours.
        home_probability = 0.85 if weekend else (0.12 if 8.5 <= hour < 17.5 else 0.93)
        if rng.random() > 0.75:
            occupied = rng.random() < home_probability
            occupants = int(rng.integers(1, 5)) if occupied else 0

        # Comfort-driven fan behaviour: hot, humid and occupied → fan wanted.
        pressure = 1.15 * (temperature - 27.5) + 0.05 * (humidity - 60) + (1.3 if occupied else -4.0)
        if 1 <= hour < 6:
            pressure -= 1.0  # people are asleep in the bedroom, not in the living room
        p_on = _sigmoid(pressure)
        if fan_on:
            fan_on = rng.random() < (0.9 if p_on > 0.35 else 0.3)
        else:
            fan_on = rng.random() < p_on * 0.6
        fan_states.append(fan_on)

        rows.append([hour, t.weekday(), temperature, humidity, float(occupied), float(occupants), ambient, 0.0, 0.0])

    features: list[list[float]] = []
    labels: list[int] = []
    for i in range(1, steps - HORIZON_STEPS):
        row = list(rows[i])
        row[7] = float(fan_states[i])  # fan_on
        row[8] = float(fan_states[i] or fan_states[i - 1])  # fan_recently_on (last 30 min)
        features.append(row)
        labels.append(int(any(fan_states[i + 1 : i + 1 + HORIZON_STEPS])))

    y = np.array(labels)
    return Dataset(
        features=np.array(features, dtype=float),
        labels=y,
        feature_names=FAN_FEATURES,
        metadata={
            "source": "simulated",
            "days": days,
            "step_minutes": step_minutes,
            "seed": seed,
            "samples": len(labels),
            "positive_rate": round(float(y.mean()), 3),
            "horizon_minutes": HORIZON_STEPS * step_minutes,
        },
    )


# --- Power history ---------------------------------------------------------------------

def _power_for(device_type: str, state) -> float:
    """Use the existing virtual device power estimate for a given state."""
    device = {
        "light": VirtualLight,
        "fan": VirtualFan,
        "ac": VirtualAC,
        "door_lock": VirtualDoorLock,
    }[device_type]("sim", "sim", "sim", initial_state=state)
    return device.power_w


def _random_state(device_type: str, rng: np.random.Generator):
    on = rng.random() < 0.6
    if device_type == "light":
        return LightState(is_on=on, brightness=int(rng.integers(1, 101)))
    if device_type == "fan":
        return FanState(is_on=on, speed=int(rng.integers(1, 101)))
    if device_type == "ac":
        return AcState(is_on=on, target_temperature_c=int(rng.integers(16, 31)))
    return DoorLockState(is_locked=bool(rng.random() < 0.7))


def generate_power_dataset(
    *, samples_per_device: int = 2500, anomaly_rate: float = 0.02, seed: int = 11
) -> dict[str, Dataset]:
    """Per device type: [setting_level, power_w] readings, label 1 = injected fault."""
    rng = np.random.default_rng(seed)
    datasets: dict[str, Dataset] = {}
    for device_type in ("light", "fan", "ac", "door_lock"):
        rows: list[list[float]] = []
        labels: list[int] = []
        for _ in range(samples_per_device):
            state = _random_state(device_type, rng)
            level = setting_level(device_type, state.model_dump())
            expected = _power_for(device_type, state)
            power = expected * (1 + rng.normal(0, 0.03)) + rng.normal(0, 0.05)
            injected = rng.random() < anomaly_rate
            if injected:
                fault = rng.choice(["surge", "phantom"]) if level == 0 else rng.choice(["surge", "stall"])
                if fault == "surge":
                    power = expected * rng.uniform(2.2, 4.0) + rng.uniform(5, 40)
                elif fault == "stall":
                    power = expected * rng.uniform(0.0, 0.25)
                else:  # drawing power while off
                    power = rng.uniform(15, 80) if device_type != "ac" else rng.uniform(150, 600)
            rows.append([level, max(0.0, power)])
            labels.append(int(injected))
        y = np.array(labels)
        datasets[device_type] = Dataset(
            features=np.array(rows, dtype=float),
            labels=y,
            feature_names=POWER_FEATURES,
            metadata={"source": "simulated", "samples": samples_per_device, "seed": seed, "injected": int(y.sum())},
        )
    return datasets
