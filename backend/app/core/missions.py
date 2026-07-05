from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class MissionStatus(StrEnum):
    accepted = "accepted"
    planned = "planned"
    awaiting_approval = "awaiting_approval"
    approved = "approved"
    rejected = "rejected"


class MissionRequest(BaseModel):
    plugin_id: str = Field(min_length=2)
    user_request: str = Field(min_length=3)
    requested_by: str = Field(default="local-user", min_length=2)


class MissionApprovalRequest(BaseModel):
    approved_by: str = Field(default="governance-gate", min_length=2)
    evidence: dict[str, str] = Field(default_factory=dict)


class MissionRejectionRequest(BaseModel):
    rejected_by: str = Field(default="governance-gate", min_length=2)
    reason: str = Field(min_length=3)
    evidence: dict[str, str] = Field(default_factory=dict)


class MissionStep(BaseModel):
    name: str
    actor: str
    result: str


class Mission(BaseModel):
    mission_id: str
    plugin_id: str
    user_request: str
    requested_by: str
    status: MissionStatus
    chief_agent: str
    governance_gate: str
    data_platform: str
    steps: list[MissionStep]
    created_at: datetime


def create_mission_plan(request: MissionRequest) -> Mission:
    mission_id = str(uuid4())
    steps = [
        MissionStep(
            name="permission_check",
            actor="API Gateway",
            result="Request accepted for governed plugin execution.",
        ),
        MissionStep(
            name="chief_planning",
            actor="Plugin Chief Agent",
            result="User intent converted into a mission plan.",
        ),
        MissionStep(
            name="runtime_scheduling",
            actor="Mission Scheduler",
            result="Mission queued for runtime execution and audit.",
        ),
        MissionStep(
            name="approval_gate",
            actor="Governance Gate",
            result="Artifact delivery requires review before export.",
        ),
    ]
    return Mission(
        mission_id=mission_id,
        plugin_id=request.plugin_id,
        user_request=request.user_request,
        requested_by=request.requested_by,
        status=MissionStatus.awaiting_approval,
        chief_agent=f"{request.plugin_id.upper()} Chief Agent",
        governance_gate="human_approval_before_delivery",
        data_platform="DB MARIAM",
        steps=steps,
        created_at=datetime.now(UTC),
    )
