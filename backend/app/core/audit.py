from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditRecordRequest(BaseModel):
    actor_id: str = Field(min_length=2)
    action: str = Field(min_length=2)
    target_type: str = Field(min_length=2)
    target_id: str = Field(min_length=2)
    decision: str = Field(min_length=2)
    evidence: dict = Field(default_factory=dict)


class AuditRecord(BaseModel):
    audit_id: str
    actor_id: str
    action: str
    target_type: str
    target_id: str
    decision: str
    evidence: dict
    data_platform: str = "DB MARIAM"
    created_at: datetime


def create_audit_record(request: AuditRecordRequest) -> AuditRecord:
    return AuditRecord(
        audit_id=str(uuid4()),
        actor_id=request.actor_id,
        action=request.action,
        target_type=request.target_type,
        target_id=request.target_id,
        decision=request.decision,
        evidence=request.evidence,
        created_at=datetime.now(UTC),
    )
