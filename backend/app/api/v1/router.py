from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.api.v1 import devices, events, gestures, home

api_router = APIRouter()
api_router.include_router(home.router)
api_router.include_router(devices.router)
api_router.include_router(events.router)
api_router.include_router(gestures.router)


@api_router.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
