"""Application configuration.

Every setting can be overridden with an environment variable prefixed ``SMARTHOME_``
(or in ``backend/.env``), e.g. ``SMARTHOME_VIRTUAL_DEVICE_LATENCY_MS=150``.
"""

from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.devices.types import DeviceDriver, DeviceType


class DeviceConfig(BaseModel):
    """Declarative description of one device in the home.

    ``driver`` selects the implementation. Moving a device to real hardware means
    changing its driver here, not touching business logic.
    """

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    type: DeviceType
    room: str
    driver: DeviceDriver = DeviceDriver.VIRTUAL


DEFAULT_DEVICES = [
    DeviceConfig(id="light_living_room", name="Living Room Light", type=DeviceType.LIGHT, room="living_room"),
    DeviceConfig(id="fan_living_room", name="Living Room Fan", type=DeviceType.FAN, room="living_room"),
    DeviceConfig(id="ac_bedroom", name="Bedroom AC", type=DeviceType.AC, room="bedroom"),
    DeviceConfig(id="door_main", name="Main Door", type=DeviceType.DOOR_LOCK, room="entrance"),
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SMARTHOME_", env_file=".env", extra="ignore")

    app_name: str = "IntelliHome"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    event_log_max_size: int = Field(default=1000, ge=1)
    virtual_device_latency_ms: int = Field(default=0, ge=0)
    sensor_seed: int | None = None
    devices: list[DeviceConfig] = Field(default_factory=lambda: list(DEFAULT_DEVICES))


@lru_cache
def get_settings() -> Settings:
    return Settings()
