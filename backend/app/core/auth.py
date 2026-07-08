from pydantic import BaseModel, Field


class UserSession(BaseModel):
    session_id: str
    user_id: str
    display_name: str
    roles: list[str]
    permissions: list[str]
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
