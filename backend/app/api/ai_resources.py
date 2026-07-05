from fastapi import APIRouter, Depends

from app.core.ai_resources import ResourceRouteRequest
from app.dependencies import get_ai_resource_manager
from app.services.ai_resources import AIResourceManager

router = APIRouter(prefix="/api/ai-resources", tags=["ai-resources"])


@router.get("/providers")
def list_providers(manager: AIResourceManager = Depends(get_ai_resource_manager)) -> dict:
    return {"providers": [provider.model_dump() for provider in manager.list_providers()]}


@router.post("/route")
def route_resource(
    request: ResourceRouteRequest,
    manager: AIResourceManager = Depends(get_ai_resource_manager),
) -> dict:
    decision = manager.route(request)
    return {"decision": decision.model_dump()}
