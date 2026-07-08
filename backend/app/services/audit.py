from app.core.audit import ApprovalAssignmentRequest, AuditRecord, AuditRecordRequest, create_audit_record
from app.core.events import InMemoryEventBus
from app.repositories.audit import AuditRepository


class AuditService:
    def __init__(self, event_bus: InMemoryEventBus, repository: AuditRepository) -> None:
        self._event_bus = event_bus
        self._repository = repository

    def record(self, request: AuditRecordRequest) -> AuditRecord:
        record = create_audit_record(request)
        saved = self._repository.save(record)
        self._event_bus.publish(
            "audit.recorded",
            "audit-service",
            {
                "audit_id": saved.audit_id,
                "actor_id": saved.actor_id,
                "action": saved.action,
                "target_type": saved.target_type,
                "target_id": saved.target_id,
                "decision": saved.decision,
            },
        )
        return saved

    def assign_approval(self, request: ApprovalAssignmentRequest) -> AuditRecord:
        record = self.record(
            AuditRecordRequest(
                actor_id=request.assigned_by,
                action="governance.assign_approval",
                target_type=request.target_type,
                target_id=request.target_id,
                decision="assigned",
                evidence={
                    "assignee_id": request.assignee_id,
                    "approval_role": request.approval_role,
                    "reason": request.reason,
                    "data_platform": "DB MARIAM",
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "governance.approval_assigned",
            "audit-service",
            {
                "audit_id": record.audit_id,
                "target_type": request.target_type,
                "target_id": request.target_id,
                "assigned_by": request.assigned_by,
                "assignee_id": request.assignee_id,
                "approval_role": request.approval_role,
            },
        )
        return record

    def list(self) -> list[AuditRecord]:
        return self._repository.list()
