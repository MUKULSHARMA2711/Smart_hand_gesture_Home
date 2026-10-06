"""Application configuration.

Every setting can be overridden with an environment variable prefixed ``SMARTHOME_``
(or in ``backend/.env``), e.g. ``SMARTHOME_VIRTUAL_DEVICE_LATENCY_MS=150``.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, SecretStr
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
    model_config = SettingsConfigDict(
        env_prefix="SMARTHOME_", env_file=".env", extra="ignore", populate_by_name=True
    )

    app_name: str = "IntelliHome"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    event_log_max_size: int = Field(default=1000, ge=1)
    virtual_device_latency_ms: int = Field(default=0, ge=0)
    sensor_seed: int | None = None
    devices: list[DeviceConfig] = Field(default_factory=lambda: list(DEFAULT_DEVICES))

    # Gesture control
    gesture_confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    # Device actions gesture control may not trigger. No gesture maps to a door intent, and
    # "unlock" is blocked here as well (defence in depth against a misread hand pose).
    gesture_blocked_actions: list[str] = ["unlock"]
    gesture_history_max_size: int = Field(default=500, ge=1)

    # AI agent. Provider, model and key also accept the unprefixed AI_PROVIDER / AI_MODEL / AI_API_KEY.
    ai_provider: Literal["mock", "anthropic"] = Field(
        default="mock", validation_alias=AliasChoices("SMARTHOME_AI_PROVIDER", "AI_PROVIDER", "ai_provider")
    )
    ai_model: str = Field(
        default="claude-opus-5-5", validation_alias=AliasChoices("SMARTHOME_AI_MODEL", "AI_MODEL", "ai_model")
    )
    # Optional: without it the Anthropic SDK uses ANTHROPIC_API_KEY or an `ant auth login` profile.
    ai_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("SMARTHOME_AI_API_KEY", "AI_API_KEY", "ai_api_key")
    )
    ai_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    ai_max_tool_rounds: int = Field(default=4, ge=0, le=10)
    ai_timeout_s: float = Field(default=60.0, gt=0)
    # Explicit "unlock the front door" requests are allowed for the AI agent; set False to forbid.
    ai_allow_unlock: bool = True
    ai_history_max_size: int = Field(default=100, ge=1)

    # Machine learning (trained at startup on deterministic simulated data)
    ml_enabled: bool = True
    ml_seed: int = 7
    ml_dataset_days: int = Field(default=60, ge=7, le=365)
    ml_prediction_threshold: float = Field(default=0.5, gt=0, lt=1)
    ml_anomaly_active_minutes: int = Field(default=15, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
