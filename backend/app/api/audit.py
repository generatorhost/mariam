from fastapi import APIRouter, Depends

from app.core.audit import (
    ApprovalAssignmentRequest,
    AuditRecordRequest,
    EscalationRequest,
    NotificationRoutingRequest,
)
from app.dependencies import get_audit_service, require_permission
from app.services.audit import AuditService

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit_records(service: AuditService = Depends(get_audit_service)) -> dict:
    return {"audit_records": [record.model_dump(mode="json") for record in service.list()]}


@router.post("")
def create_audit_record(
    request: AuditRecordRequest,
    authorization=Depends(require_permission("audit.record", "audit_record")),
    service: AuditService = Depends(get_audit_service),
) -> dict:
    record = service.record(request)
    return {"audit_record": record.model_dump(mode="json")}


@router.post("/approval-assignments")
def assign_approval(
    request: ApprovalAssignmentRequest,
    authorization=Depends(require_permission("governance.assign_approval", "approval_assignment")),
    service: AuditService = Depends(get_audit_service),
) -> dict:
    record = service.assign_approval(request)
    return {"audit_record": record.model_dump(mode="json")}


@router.post("/notifications/route")
def route_notification(
    request: NotificationRoutingRequest,
    authorization=Depends(require_permission("governance.assign_approval", "notification_route")),
    service: AuditService = Depends(get_audit_service),
) -> dict:
    record = service.route_notification(request)
    return {"audit_record": record.model_dump(mode="json")}


@router.get("/reviewer-workload")
def reviewer_workload(service: AuditService = Depends(get_audit_service)) -> dict:
    return {"workload_report": service.reviewer_workload().model_dump(mode="json")}


@router.get("/governance-assignment-history")
def governance_assignment_history(service: AuditService = Depends(get_audit_service)) -> dict:
    return {"history_report": service.governance_assignment_history().model_dump(mode="json")}


@router.get("/governance-sla")
def governance_sla(service: AuditService = Depends(get_audit_service)) -> dict:
    return {"sla_report": service.governance_sla_report().model_dump(mode="json")}


@router.post("/escalations")
def escalate_reviewer_workload(
    request: EscalationRequest,
    authorization=Depends(require_permission("governance.assign_approval", "reviewer_workload")),
    service: AuditService = Depends(get_audit_service),
) -> dict:
    record = service.escalate_reviewer_workload(request)
    return {"audit_record": record.model_dump(mode="json")}
