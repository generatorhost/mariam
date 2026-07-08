from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.audit import (
    ApprovalAssignmentRequest,
    AuditRecord,
    AuditRecordRequest,
    EscalationRequest,
    GovernanceAssignmentHistoryReport,
    GovernanceDecisionEvidenceExportPackage,
    GovernanceSLAEvidenceExportPackage,
    GovernanceSLAReport,
    GovernanceWorkloadEvidenceExportPackage,
    NotificationRoutingRequest,
    ReviewerDecisionRequest,
    ReviewerWorkloadReport,
)
from app.dependencies import get_audit_service, require_permission
from app.services.audit import AuditService

router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditRecordsResponse(BaseModel):
    audit_records: list[AuditRecord]


class AuditRecordResponse(BaseModel):
    audit_record: AuditRecord


class ReviewerWorkloadResponse(BaseModel):
    workload_report: ReviewerWorkloadReport


class GovernanceWorkloadEvidenceExportResponse(BaseModel):
    export_package: GovernanceWorkloadEvidenceExportPackage


class GovernanceAssignmentHistoryResponse(BaseModel):
    history_report: GovernanceAssignmentHistoryReport


class GovernanceDecisionEvidenceExportResponse(BaseModel):
    export_package: GovernanceDecisionEvidenceExportPackage


class GovernanceSLAResponse(BaseModel):
    sla_report: GovernanceSLAReport


class GovernanceSLAEvidenceExportResponse(BaseModel):
    export_package: GovernanceSLAEvidenceExportPackage


@router.get("", response_model=AuditRecordsResponse)
def list_audit_records(service: AuditService = Depends(get_audit_service)) -> AuditRecordsResponse:
    return {"audit_records": [record.model_dump(mode="json") for record in service.list()]}


@router.post("", response_model=AuditRecordResponse)
def create_audit_record(
    request: AuditRecordRequest,
    authorization=Depends(require_permission("audit.record", "audit_record")),
    service: AuditService = Depends(get_audit_service),
) -> AuditRecordResponse:
    record = service.record(request)
    return {"audit_record": record.model_dump(mode="json")}


@router.post("/approval-assignments", response_model=AuditRecordResponse)
def assign_approval(
    request: ApprovalAssignmentRequest,
    authorization=Depends(require_permission("governance.assign_approval", "approval_assignment")),
    service: AuditService = Depends(get_audit_service),
) -> AuditRecordResponse:
    record = service.assign_approval(request)
    return {"audit_record": record.model_dump(mode="json")}


@router.post("/notifications/route", response_model=AuditRecordResponse)
def route_notification(
    request: NotificationRoutingRequest,
    authorization=Depends(require_permission("governance.assign_approval", "notification_route")),
    service: AuditService = Depends(get_audit_service),
) -> AuditRecordResponse:
    record = service.route_notification(request)
    return {"audit_record": record.model_dump(mode="json")}


@router.get("/reviewer-workload", response_model=ReviewerWorkloadResponse)
def reviewer_workload(service: AuditService = Depends(get_audit_service)) -> ReviewerWorkloadResponse:
    return {"workload_report": service.reviewer_workload().model_dump(mode="json")}


@router.post("/reviewer-workload/export", response_model=GovernanceWorkloadEvidenceExportResponse)
def export_reviewer_workload(
    authorization=Depends(require_permission("governance.assign_approval", "governance_workload_export")),
    service: AuditService = Depends(get_audit_service),
) -> GovernanceWorkloadEvidenceExportResponse:
    return {"export_package": service.export_governance_workload_evidence().model_dump(mode="json")}


@router.get("/governance-assignment-history", response_model=GovernanceAssignmentHistoryResponse)
def governance_assignment_history(
    service: AuditService = Depends(get_audit_service),
) -> GovernanceAssignmentHistoryResponse:
    return {"history_report": service.governance_assignment_history().model_dump(mode="json")}


@router.post("/governance-decision-evidence/export", response_model=GovernanceDecisionEvidenceExportResponse)
def export_governance_decision_evidence(
    authorization=Depends(require_permission("governance.assign_approval", "governance_decision_export")),
    service: AuditService = Depends(get_audit_service),
) -> GovernanceDecisionEvidenceExportResponse:
    return {"export_package": service.export_governance_decision_evidence().model_dump(mode="json")}


@router.post("/reviewer-decisions", response_model=AuditRecordResponse)
def record_reviewer_decision(
    request: ReviewerDecisionRequest,
    authorization=Depends(require_permission("governance.assign_approval", "reviewer_decision")),
    service: AuditService = Depends(get_audit_service),
) -> AuditRecordResponse:
    record = service.record_reviewer_decision(request)
    return {"audit_record": record.model_dump(mode="json")}


@router.get("/governance-sla", response_model=GovernanceSLAResponse)
def governance_sla(service: AuditService = Depends(get_audit_service)) -> GovernanceSLAResponse:
    return {"sla_report": service.governance_sla_report().model_dump(mode="json")}


@router.post("/governance-sla/export", response_model=GovernanceSLAEvidenceExportResponse)
def export_governance_sla(
    authorization=Depends(require_permission("governance.assign_approval", "governance_sla_export")),
    service: AuditService = Depends(get_audit_service),
) -> GovernanceSLAEvidenceExportResponse:
    return {"export_package": service.export_governance_sla_evidence().model_dump(mode="json")}


@router.post("/escalations", response_model=AuditRecordResponse)
def escalate_reviewer_workload(
    request: EscalationRequest,
    authorization=Depends(require_permission("governance.assign_approval", "reviewer_workload")),
    service: AuditService = Depends(get_audit_service),
) -> AuditRecordResponse:
    record = service.escalate_reviewer_workload(request)
    return {"audit_record": record.model_dump(mode="json")}
