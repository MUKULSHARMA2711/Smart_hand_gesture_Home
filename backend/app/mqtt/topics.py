"""The MQTT topic contract. Every topic string is built and parsed here, nowhere else.

    home/{device_id}/set            backend → device   command (JSON)
    home/{device_id}/state          device → backend   confirmed state / acknowledgement (JSON, retained)
    home/{device_id}/availability   device → backend   "online" | "offline" (retained, Last Will)
    home/sensors/{kind}             sensor → backend   reading (JSON)
    home/sensors/availability       sensor board       "online" | "offline" (retained, Last Will)
    home/energy/{device_id}         device → backend   measured power (JSON)
    home/backend/availability       backend            "online" | "offline" (retained, Last Will)
"""

import re
from dataclasses import dataclass
from typing import Literal

ROOT = "home"
SENSOR_KINDS: tuple[str, ...] = ("temperature", "humidity", "occupancy", "ambient_light")
SENSORS_SEGMENT = "sensors"
ENERGY_SEGMENT = "energy"
BACKEND_SEGMENT = "backend"
# Second-level segments with a fixed meaning; device ids must not collide with them.
RESERVED_IDS = frozenset({SENSORS_SEGMENT, ENERGY_SEGMENT, BACKEND_SEGMENT})

ONLINE = "online"
OFFLINE = "offline"

_ID = re.compile(r"^[a-z0-9_]+$")  # never contains MQTT separators or wildcards

# Subscriptions the backend makes on one shared connection.
DEVICE_STATE_FILTER = f"{ROOT}/+/state"
DEVICE_AVAILABILITY_FILTER = f"{ROOT}/+/availability"
SENSOR_FILTER = f"{ROOT}/{SENSORS_SEGMENT}/+"
ENERGY_FILTER = f"{ROOT}/{ENERGY_SEGMENT}/+"
BACKEND_SUBSCRIPTIONS = (DEVICE_STATE_FILTER, DEVICE_AVAILABILITY_FILTER, SENSOR_FILTER, ENERGY_FILTER)


def _device(device_id: str) -> str:
    if not _ID.match(device_id) or device_id in RESERVED_IDS:
        raise ValueError(f"Invalid device id for MQTT topics: {device_id!r}")
    return device_id


def device_set(device_id: str) -> str:
    return f"{ROOT}/{_device(device_id)}/set"


def device_state(device_id: str) -> str:
    return f"{ROOT}/{_device(device_id)}/state"


def device_availability(device_id: str) -> str:
    return f"{ROOT}/{_device(device_id)}/availability"


def sensor(kind: str) -> str:
    if kind not in SENSOR_KINDS:
        raise ValueError(f"Unknown sensor kind {kind!r}; expected one of {SENSOR_KINDS}")
    return f"{ROOT}/{SENSORS_SEGMENT}/{kind}"


def sensors_availability() -> str:
    return f"{ROOT}/{SENSORS_SEGMENT}/availability"


def backend_availability() -> str:
    """The backend's own presence (its Last Will), so firmware can tell when the hub is gone."""
    return f"{ROOT}/{BACKEND_SEGMENT}/availability"


def energy(device_id: str) -> str:
    return f"{ROOT}/{ENERGY_SEGMENT}/{_device(device_id)}"


TopicKind = Literal["set", "state", "availability", "sensor", "sensors_availability", "energy"]


@dataclass(frozen=True)
class Topic:
    kind: TopicKind
    key: str  # device id or sensor kind


def parse(topic: str) -> Topic | None:
    """Classify an incoming topic, or None if it is not part of the contract."""
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != ROOT:
        return None
    _, second, third = parts
    if second == SENSORS_SEGMENT:
        if third in SENSOR_KINDS:
            return Topic("sensor", third)
        return Topic("sensors_availability", SENSORS_SEGMENT) if third == "availability" else None
    if second == BACKEND_SEGMENT:
        return None
    if second == ENERGY_SEGMENT:
        return Topic("energy", third) if _ID.match(third) else None
    if not _ID.match(second) or third not in ("set", "state", "availability"):
        return None
    return Topic(third, second)  # type: ignore[arg-type]
