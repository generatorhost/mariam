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


class ApprovalAssignmentRequest(BaseModel):
    assigned_by: str = Field(default="governance-lead", min_length=2)
    assignee_id: str = Field(min_length=2)
    target_type: str = Field(min_length=2)
    target_id: str = Field(min_length=2)
    approval_role: str = Field(default="governance-reviewer", min_length=2)
    reason: str = Field(min_length=3)
    evidence: dict = Field(default_factory=dict)


class NotificationRoutingRequest(BaseModel):
    routed_by: str = Field(default="governance-router", min_length=2)
    recipient_id: str = Field(min_length=2)
    channel: str = Field(default="command-center", min_length=2)
    subject: str = Field(min_length=3)
    message: str = Field(min_length=3)
    target_type: str = Field(min_length=2)
    target_id: str = Field(min_length=2)
    evidence: dict = Field(default_factory=dict)


class EscalationRequest(BaseModel):
    escalated_by: str = Field(default="governance-lead", min_length=2)
    reviewer_id: str = Field(min_length=2)
    target_type: str = Field(min_length=2)
    target_id: str = Field(min_length=2)
    reason: str = Field(min_length=3)
    escalation_level: str = Field(default="governance-lead-review", min_length=2)
    evidence: dict = Field(default_factory=dict)


class ReviewerDecisionRequest(BaseModel):
    decided_by: str = Field(default="governance-reviewer", min_length=2)
    reviewer_id: str = Field(min_length=2)
    target_type: str = Field(min_length=2)
    target_id: str = Field(min_length=2)
    assignment_id: str | None = None
    decision: str = Field(pattern="^(approved|rejected|changes_requested)$")
    reason: str = Field(min_length=3)
    evidence: dict = Field(default_factory=dict)


class ReviewerWorkloadItem(BaseModel):
    reviewer_id: str
    assigned_count: int
    decision_count: int = 0
    routed_notifications: int
    escalation_count: int
    target_ids: list[str]
    status: str
    data_platform: str = "DB MARIAM"


class ReviewerWorkloadReport(BaseModel):
    title: str
    status: str
    reviewer_count: int
    overloaded_reviewers: list[str]
    items: list[ReviewerWorkloadItem]
    data_platform: str = "DB MARIAM"


class GovernanceSLAItem(BaseModel):
    target_type: str
    target_id: str
    reviewer_id: str
    approval_role: str
    age_minutes: int
    sla_minutes: int
    escalation_after_minutes: int
    status: str
    escalation_required: bool
    data_platform: str = "DB MARIAM"


class GovernanceSLAReport(BaseModel):
    title: str
    status: str
    generated_at: datetime
    sla_minutes: int
    escalation_after_minutes: int
    due_soon_count: int
    overdue_count: int
    escalation_required_count: int
    items: list[GovernanceSLAItem]
    data_platform: str = "DB MARIAM"


class ReviewerQueueAssignmentRecord(BaseModel):
    assignment_id: str
    audit_id: str
    assigned_by: str
    reviewer_id: str
    target_type: str
    target_id: str
    approval_role: str
    reviewer_queue: str
    status: str = "assigned"
    reason: str
    data_platform: str = "DB MARIAM"
    created_at: datetime


class GovernanceSLAEscalationRecord(BaseModel):
    escalation_id: str
    audit_id: str
    escalated_by: str
    reviewer_id: str
    target_type: str
    target_id: str
    escalation_level: str
    status: str = "escalated"
    reason: str
    data_platform: str = "DB MARIAM"
    created_at: datetime


class ReviewerDecisionOutcomeRecord(BaseModel):
    decision_id: str
    audit_id: str
    assignment_id: str | None = None
    decided_by: str
    reviewer_id: str
    target_type: str
    target_id: str
    decision: str
    reason: str
    evidence: dict = Field(default_factory=dict)
    data_platform: str = "DB MARIAM"
    created_at: datetime


class GovernanceAssignmentHistoryReport(BaseModel):
    title: str
    status: str
    generated_at: datetime
    assignment_count: int
    escalation_count: int
    decision_count: int
    assignments: list[ReviewerQueueAssignmentRecord]
    escalations: list[GovernanceSLAEscalationRecord]
    decisions: list[ReviewerDecisionOutcomeRecord]
    data_platform: str = "DB MARIAM"


class GovernanceDecisionEvidenceExportPackage(BaseModel):
    export_id: str
    title: str
    status: str
    format: str
    generated_at: datetime
    data_platform: str = "DB MARIAM"
    package_manifest: dict[str, object]
    history_report: GovernanceAssignmentHistoryReport


class GovernanceWorkloadEvidenceExportPackage(BaseModel):
    export_id: str
    title: str
    status: str
    format: str
    generated_at: datetime
    data_platform: str = "DB MARIAM"
    package_manifest: dict[str, object]
    workload_report: ReviewerWorkloadReport


class GovernanceSLAEvidenceExportPackage(BaseModel):
    export_id: str
    title: str
    status: str
    format: str
    generated_at: datetime
    data_platform: str = "DB MARIAM"
    package_manifest: dict[str, object]
    sla_report: GovernanceSLAReport


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
