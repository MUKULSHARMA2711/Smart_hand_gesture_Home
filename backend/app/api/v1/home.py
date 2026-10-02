from fastapi import APIRouter

from app.api.deps import HomeStateDep
from app.domain.home_state import HomeStateSnapshot

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/state", response_model=HomeStateSnapshot, summary="Full home snapshot")
async def get_home_state(home: HomeStateDep) -> HomeStateSnapshot:
    return home.snapshot()
