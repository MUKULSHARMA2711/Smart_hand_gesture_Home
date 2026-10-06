from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import ContainerDep
from app.devices.types import DeviceStatus

router = APIRouter(prefix="/iot", tags=["iot"])


class MQTTConnection(BaseModel):
    enabled: bool
    connected: bool
    broker: str | None = None
    client_id: str | None = None
    connected_since: datetime | None = None
    messages_received: int = 0
    messages_ignored: int = 0  # malformed, unknown topic, or for a device this backend does not manage


class DeviceConnectivity(BaseModel):
    device_id: str
    name: str
    driver: str
    status: DeviceStatus
    last_seen: datetime | None = None
    last_confirmed_at: datetime | None = None
    topics: dict[str, str] | None = None


class DeviceCounts(BaseModel):
    online: int
    offline: int
    unknown: int
    items: list[DeviceConnectivity]


class SensorStatus(BaseModel):
    source: Literal["simulated", "mqtt"]
    max_age_s: float
    board_online: bool | None = None
    readings: dict[str, dict[str, Any]] | None = None  # per sensor: status, age, sensor id (MQTT only)


class IoTStatus(BaseModel):
    mqtt: MQTTConnection
    devices: DeviceCounts
    sensors: SensorStatus


@router.get(
    "/status",
    response_model=IoTStatus,
    summary="MQTT connection, device connectivity and sensor freshness",
    description="Runtime values only: `connected` is the live MQTT connection state, and device "
    "status comes from the devices' own availability reports.",
)
async def iot_status(container: ContainerDep) -> IoTStatus:
    mqtt = container.mqtt
    items = []
    for device in container.home_state.devices.all():
        extra = mqtt.device_status(device) if mqtt is not None and device.driver == "esp32_mqtt" else {}
        items.append(
            DeviceConnectivity(
                device_id=device.id,
                name=device.name,
                driver=device.driver,
                status=device.status,
                last_confirmed_at=device.last_confirmed_at,
                **extra,
            )
        )
    count = lambda status: sum(item.status is status for item in items)  # noqa: E731

    sensors = mqtt.sensors if mqtt is not None else None
    return IoTStatus(
        mqtt=MQTTConnection(
            enabled=mqtt is not None,
            connected=mqtt.connected if mqtt else False,
            broker=mqtt.broker if mqtt else None,
            client_id=mqtt.client_id if mqtt else None,
            connected_since=mqtt.connected_since if mqtt else None,
            messages_received=mqtt.messages_received if mqtt else 0,
            messages_ignored=mqtt.messages_ignored if mqtt else 0,
        ),
        devices=DeviceCounts(
            online=count(DeviceStatus.ONLINE),
            offline=count(DeviceStatus.OFFLINE),
            unknown=count(DeviceStatus.UNKNOWN),
            items=items,
        ),
        sensors=SensorStatus(
            source=container.settings.sensor_source,
            max_age_s=container.settings.sensor_max_age_s,
            board_online=mqtt.sensors_board_online if sensors is not None else None,
            readings=sensors.status() if sensors is not None else None,
        ),
    )
