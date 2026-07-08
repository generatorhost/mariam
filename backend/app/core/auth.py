from pydantic import BaseModel, Field


class UserSession(BaseModel):
    session_id: str
    user_id: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    data_platform: str = "DB MARIAM"


class RequestActorContext(BaseModel):
    request_id: str
    actor_id: str
    session_id: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    actor_matches_session: bool
    propagation_mode: str
    headers_used: list[str]
    data_platform: str = "DB MARIAM"


class PermissionCheckRequest(BaseModel):
    permission: str = Field(min_length=3)
    actor_id: str = Field(default="command-center-operator", min_length=2)


class PermissionCheckResult(BaseModel):
    actor_id: str
    permission: str
    allowed: bool
    roles: list[str]
    data_platform: str = "DB MARIAM"


class PermissionEnforcementRequest(PermissionCheckRequest):
    target_type: str = Field(default="runtime-action", min_length=2)
    target_id: str = Field(default="command-center", min_length=2)
    reason: str = Field(default="Enforce governed backend permission.", min_length=3)
    evidence: dict = Field(default_factory=dict)


class PermissionEnforcementResult(PermissionCheckResult):
    target_type: str
    target_id: str
    enforcement: str = "granted"
    reason: str
    evidence: dict = Field(default_factory=dict)


class HumanIdentityEnforcementRequest(BaseModel):
    actor_id: str = Field(default="command-center-operator", min_length=2)
    claimed_user_id: str = Field(default="command-center-operator", min_length=2)
    target_type: str = Field(default="governance-action", min_length=2)
    target_id: str = Field(default="command-center", min_length=2)
    reason: str = Field(default="Enforce human identity before governed action.", min_length=3)
    evidence: dict = Field(default_factory=dict)


class HumanIdentityEnforcementResult(BaseModel):
    actor_id: str
    claimed_user_id: str
    display_name: str
    roles: list[str]
    target_type: str
    target_id: str
    verified: bool
    enforcement: str = "verified"
    reason: str
    data_platform: str = "DB MARIAM"
    evidence: dict = Field(default_factory=dict)


def default_command_center_session() -> UserSession:
    return UserSession(
        session_id="command-center-session-local",
        user_id="command-center-operator",
        display_name="Command Center Operator",
        roles=["operator", "governance-reviewer", "quality-reviewer"],
        permissions=[
            "runtime.read",
            "mission.create",
            "artifact.approve",
            "artifact.request_revision",
            "governance.assign_approval",
            "plugin.register",
            "runtime_object.register",
            "diagnostics.export",
        ],
    )
