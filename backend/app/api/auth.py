from fastapi import APIRouter, Depends

from app.core.auth import PermissionCheckRequest
from app.dependencies import get_auth_service
from app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/session")
def current_session(service: AuthService = Depends(get_auth_service)) -> dict:
    return {"session": service.current_session().model_dump(mode="json")}


@router.post("/permissions/check")
def check_permission(
    request: PermissionCheckRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    return {"permission_check": service.check_permission(request).model_dump(mode="json")}
