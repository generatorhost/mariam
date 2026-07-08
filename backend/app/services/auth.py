from app.core.auth import (
    HumanIdentityEnforcementRequest,
    HumanIdentityEnforcementResult,
    PermissionCheckRequest,
    PermissionCheckResult,
    PermissionEnforcementRequest,
    PermissionEnforcementResult,
    RequestActorContext,
    UserSession,
    default_command_center_session,
)


class AuthService:
    def current_session(self) -> UserSession:
        return default_command_center_session()

    def request_actor_context(
        self,
        request_id: str | None = None,
        actor_id: str | None = None,
    ) -> RequestActorContext:
        session = self.current_session()
        propagated_actor = actor_id or session.user_id
        headers_used = []
        if request_id:
            headers_used.append("x-mariam-request-id")
        if actor_id:
            headers_used.append("x-mariam-actor-id")
        return RequestActorContext(
            request_id=request_id or "local-command-center-request",
            actor_id=propagated_actor,
            session_id=session.session_id,
            display_name=session.display_name,
            roles=session.roles,
            permissions=session.permissions,
            actor_matches_session=propagated_actor == session.user_id,
            propagation_mode="headers" if headers_used else "session-default",
            headers_used=headers_used,
        )

    def check_permission(self, request: PermissionCheckRequest) -> PermissionCheckResult:
        session = self.current_session()
        return PermissionCheckResult(
            actor_id=request.actor_id,
            permission=request.permission,
            allowed=request.permission in session.permissions,
            roles=session.roles,
        )

    def enforce_permission(self, request: PermissionEnforcementRequest) -> PermissionEnforcementResult:
        checked = self.check_permission(request)
        if not checked.allowed:
            raise PermissionError(
                f"Permission {request.permission} denied for {request.actor_id} on {request.target_type}:{request.target_id}."
            )
        return PermissionEnforcementResult(
            actor_id=checked.actor_id,
            permission=checked.permission,
            allowed=True,
            roles=checked.roles,
            target_type=request.target_type,
            target_id=request.target_id,
            reason=request.reason,
            evidence={"data_platform": "DB MARIAM", **request.evidence},
        )

    def enforce_human_identity(
        self,
        request: HumanIdentityEnforcementRequest,
    ) -> HumanIdentityEnforcementResult:
        session = self.current_session()
        if request.actor_id != session.user_id or request.claimed_user_id != session.user_id:
            raise PermissionError(
                f"Human identity {request.claimed_user_id} denied for actor {request.actor_id} on {request.target_type}:{request.target_id}."
            )
        return HumanIdentityEnforcementResult(
            actor_id=request.actor_id,
            claimed_user_id=request.claimed_user_id,
            display_name=session.display_name,
            roles=session.roles,
            target_type=request.target_type,
            target_id=request.target_id,
            verified=True,
            reason=request.reason,
            evidence={"data_platform": "DB MARIAM", **request.evidence},
        )
