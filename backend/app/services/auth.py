from app.core.auth import (
    PermissionCheckRequest,
    PermissionCheckResult,
    UserSession,
    default_command_center_session,
)


class AuthService:
    def current_session(self) -> UserSession:
        return default_command_center_session()

    def check_permission(self, request: PermissionCheckRequest) -> PermissionCheckResult:
        session = self.current_session()
        return PermissionCheckResult(
            actor_id=request.actor_id,
            permission=request.permission,
            allowed=request.permission in session.permissions,
            roles=session.roles,
        )
