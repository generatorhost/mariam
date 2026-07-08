from fastapi import APIRouter, Depends

from app.core.ai_resources import ResourceRouteRequest
from app.dependencies import get_ai_resource_manager, require_permission
from app.services.ai_resources import AIResourceManager

router = APIRouter(prefix="/api/ai-resources", tags=["ai-resources"])


@router.get("/providers")
def list_providers(manager: AIResourceManager = Depends(get_ai_resource_manager)) -> dict:
    return {"providers": [provider.model_dump() for provider in manager.list_providers()]}


@router.get("/routes")
def list_routes(manager: AIResourceManager = Depends(get_ai_resource_manager)) -> dict:
    return {"routes": [route.model_dump(mode="json") for route in manager.list_routes()]}


@router.post("/route")
def route_resource(
    request: ResourceRouteRequest,
    authorization=Depends(require_permission("ai_resource.route", "ai_resource_route")),
    manager: AIResourceManager = Depends(get_ai_resource_manager),
) -> dict:
    decision = manager.route(request)
    return {"decision": decision.model_dump(mode="json")}
