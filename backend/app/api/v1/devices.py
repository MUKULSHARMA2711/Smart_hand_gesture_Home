from fastapi import APIRouter

from app.api.deps import CommandServiceDep, HomeStateDep
from app.api.schemas import CommandRequest, CommandResponse, ErrorResponse
from app.devices.base import DeviceSnapshot

router = APIRouter(prefix="/devices", tags=["devices"])

_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Unknown device"}}


@router.get("", response_model=list[DeviceSnapshot], summary="List all devices")
async def list_devices(home: HomeStateDep) -> list[DeviceSnapshot]:
    return [device.snapshot() for device in home.devices.all()]


@router.get("/{device_id}", response_model=DeviceSnapshot, responses=_NOT_FOUND, summary="Get one device")
async def get_device(device_id: str, home: HomeStateDep) -> DeviceSnapshot:
    return home.devices.get(device_id).snapshot()


@router.post(
    "/{device_id}/command",
    response_model=CommandResponse,
    summary="Execute a command on a device",
    responses={
        **_NOT_FOUND,
        400: {"model": ErrorResponse, "description": "Action not supported by this device"},
        422: {"model": ErrorResponse, "description": "Invalid command value or malformed request"},
    },
)
async def execute_command(
    device_id: str,
    request: CommandRequest,
    home: HomeStateDep,
    commands: CommandServiceDep,
) -> CommandResponse:
    event = await commands.execute(device_id, request.to_command(), source=request.source)
    return CommandResponse(event=event, device=home.devices.get(device_id).snapshot())
