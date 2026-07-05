from fastapi import APIRouter, Depends

from app.core.runtime_objects import RuntimeObjectRequest
from app.dependencies import get_runtime_object_service
from app.services.runtime_objects import RuntimeObjectService

router = APIRouter(prefix="/api/runtime-objects", tags=["runtime-objects"])


@router.get("")
def list_runtime_objects(service: RuntimeObjectService = Depends(get_runtime_object_service)) -> dict:
    return {"runtime_objects": [runtime_object.model_dump(mode="json") for runtime_object in service.list()]}


@router.post("")
def create_runtime_object(
    request: RuntimeObjectRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    runtime_object = service.create(request)
    return {"runtime_object": runtime_object.model_dump(mode="json")}
