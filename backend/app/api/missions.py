from fastapi import APIRouter, Depends

from app.core.missions import MissionRequest
from app.dependencies import get_mission_service
from app.services.missions import MissionService

router = APIRouter(prefix="/api/missions", tags=["missions"])


@router.get("")
def list_missions(service: MissionService = Depends(get_mission_service)) -> dict:
    return {"missions": [mission.model_dump(mode="json") for mission in service.list()]}


@router.post("")
def create_mission(
    request: MissionRequest,
    service: MissionService = Depends(get_mission_service),
) -> dict:
    mission = service.create(request)
    return {"mission": mission.model_dump(mode="json")}
