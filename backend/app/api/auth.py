from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import (
    HumanIdentityEnforcementRequest,
    PermissionCheckRequest,
    PermissionEnforcementRequest,
)
from app.dependencies import get_auth_service
from app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/session")
def current_session(service: AuthService = Depends(get_auth_service)) -> dict:
    return {"session": service.current_session().model_dump(mode="json")}


@router.get("/request-context")
def request_actor_context(
    http_request: Request,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    context = service.request_actor_context(
        request_id=http_request.headers.get("x-mariam-request-id"),
        actor_id=http_request.headers.get("x-mariam-actor-id"),
    )
    return {"request_context": context.model_dump(mode="json")}


@router.post("/permissions/check")
def check_permission(
    request: PermissionCheckRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    return {"permission_check": service.check_permission(request).model_dump(mode="json")}


@router.post("/permissions/enforce")
def enforce_permission(
    request: PermissionEnforcementRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    try:
        return {"permission_enforcement": service.enforce_permission(request).model_dump(mode="json")}
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post("/human-identity/enforce")
def enforce_human_identity(
    request: HumanIdentityEnforcementRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    try:
        return {"human_identity": service.enforce_human_identity(request).model_dump(mode="json")}
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
