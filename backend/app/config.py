"""Application configuration.

Every setting can be overridden with an environment variable prefixed ``SMARTHOME_``
(or in ``backend/.env``), e.g. ``SMARTHOME_VIRTUAL_DEVICE_LATENCY_MS=150``.
"""

from functools import lru_cache
from typing import Literal, Self

from pydantic import AliasChoices, BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.devices.types import DeviceDriver, DeviceType
from app.mqtt.topics import RESERVED_IDS


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

    @field_validator("id")
    @classmethod
    def not_reserved(cls, value: str) -> str:
        if value in RESERVED_IDS:
            raise ValueError(f"'{value}' is reserved by the MQTT topic contract.")
        return value


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
    # Browser origins allowed to call the API (the single source for the CORS middleware).
    # Vite serves on 5173 and moves to 5174 when that port is busy. Override with
    # SMARTHOME_CORS_ORIGINS='["https://home.example"]'.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]
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
    # A pinch on the door may *request* an unlock that must be confirmed by a second pinch.
    # "unlock" stays in gesture_blocked_actions: no gesture ever unlocks directly.
    gesture_door_unlock: bool = True

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
    ai_timeout_s: float = Field(default=60.0, gt=0)  # per provider HTTP call
    ai_request_timeout_s: float = Field(default=120.0, gt=0)  # whole plan, including tool rounds
    # Explicit "unlock the front door" requests are allowed for the AI agent; set False to forbid.
    ai_allow_unlock: bool = True
    # An explicit AI unlock is held until the user confirms ("yes, unlock it" or the button).
    ai_unlock_requires_confirmation: bool = True
    ai_confirmation_timeout_s: float = Field(default=30.0, gt=0, le=300)
    ai_history_max_size: int = Field(default=100, ge=1)

    # Machine learning (trained at startup on deterministic simulated data)
    ml_enabled: bool = True
    ml_seed: int = 7
    ml_dataset_days: int = Field(default=60, ge=7, le=365)
    ml_prediction_threshold: float = Field(default=0.5, gt=0, lt=1)
    ml_anomaly_active_minutes: int = Field(default=15, ge=1)

    # MQTT / ESP32 hardware (Phase 7). Off by default: virtual mode needs no broker.
    mqtt_enabled: bool = False
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    mqtt_username: str | None = None
    mqtt_password: SecretStr | None = None  # never logged
    mqtt_client_id: str = Field(default="intellihome-backend", min_length=1, max_length=64)
    mqtt_keepalive_s: int = Field(default=30, ge=5, le=600)
    # How long a device has to acknowledge a command. Deliberately capped: a slow device
    # must fail visibly rather than leave the UI waiting.
    mqtt_command_timeout_s: float = Field(default=3.0, gt=0, le=30)
    # Device ids to run on ESP32 hardware over MQTT; every other device stays virtual.
    mqtt_devices: list[str] = Field(default_factory=list)
    # "simulated" (default) or "mqtt" (readings from home/sensors/{kind}).
    sensor_source: Literal["simulated", "mqtt"] = "simulated"
    # Readings older than this are stale: reported as unavailable, never used as current.
    sensor_max_age_s: float = Field(default=30.0, gt=0, le=3600)

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins_only(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError("List the allowed origins explicitly; '*' is not permitted.")
        return [origin.rstrip("/") for origin in origins]  # browsers send origins without a trailing slash

    @model_validator(mode="after")
    def apply_hardware_drivers(self) -> Self:
        known = {device.id for device in self.devices}
        unknown = sorted(set(self.mqtt_devices) - known)
        if unknown:
            raise ValueError(f"SMARTHOME_MQTT_DEVICES lists unknown devices: {unknown}")
        self.devices = [
            device.model_copy(update={"driver": DeviceDriver.ESP32_MQTT}) if device.id in self.mqtt_devices else device
            for device in self.devices
        ]
        needs_mqtt = self.sensor_source == "mqtt" or any(d.driver is DeviceDriver.ESP32_MQTT for d in self.devices)
        if needs_mqtt and not self.mqtt_enabled:
            raise ValueError("ESP32 devices or MQTT sensors are configured, but SMARTHOME_MQTT_ENABLED is false.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
