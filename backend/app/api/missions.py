from fastapi import APIRouter, Depends, HTTPException

from app.core.missions import MissionApprovalRequest, MissionRequest
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


@router.post("/{mission_id}/approve")
def approve_mission(
    mission_id: str,
    request: MissionApprovalRequest,
    service: MissionService = Depends(get_mission_service),
) -> dict:
    try:
        mission = service.approve(mission_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"mission": mission.model_dump(mode="json")}
