from app.core.audit import (
    ApprovalAssignmentRequest,
    AuditRecord,
    AuditRecordRequest,
    EscalationRequest,
    NotificationRoutingRequest,
    ReviewerWorkloadItem,
    ReviewerWorkloadReport,
    create_audit_record,
)
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

    def route_notification(self, request: NotificationRoutingRequest) -> AuditRecord:
        record = self.record(
            AuditRecordRequest(
                actor_id=request.routed_by,
                action="governance.route_notification",
                target_type=request.target_type,
                target_id=request.target_id,
                decision="routed",
                evidence={
                    "recipient_id": request.recipient_id,
                    "channel": request.channel,
                    "subject": request.subject,
                    "message": request.message,
                    "data_platform": "DB MARIAM",
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "governance.notification_routed",
            "audit-service",
            {
                "audit_id": record.audit_id,
                "target_type": request.target_type,
                "target_id": request.target_id,
                "routed_by": request.routed_by,
                "recipient_id": request.recipient_id,
                "channel": request.channel,
                "subject": request.subject,
            },
        )
        return record

    def reviewer_workload(self) -> ReviewerWorkloadReport:
        assignments: dict[str, dict[str, object]] = {}
        routed_notifications: dict[str, int] = {}
        escalations: dict[str, int] = {}
        for record in self.list():
            if record.action == "governance.assign_approval":
                reviewer_id = str(record.evidence.get("assignee_id", "unassigned"))
                reviewer_state = assignments.setdefault(
                    reviewer_id,
                    {"target_ids": set(), "assigned_count": 0},
                )
                reviewer_state["assigned_count"] = int(reviewer_state["assigned_count"]) + 1
                target_ids = reviewer_state["target_ids"]
                if isinstance(target_ids, set):
                    target_ids.add(record.target_id)
            if record.action == "governance.route_notification":
                reviewer_id = str(record.evidence.get("recipient_id", "unassigned"))
                routed_notifications[reviewer_id] = routed_notifications.get(reviewer_id, 0) + 1
            if record.action == "governance.escalate_reviewer_workload":
                reviewer_id = str(record.evidence.get("reviewer_id", "unassigned"))
                escalations[reviewer_id] = escalations.get(reviewer_id, 0) + 1

        reviewer_ids = sorted(set(assignments) | set(routed_notifications) | set(escalations))
        items = []
        for reviewer_id in reviewer_ids:
            reviewer_state = assignments.get(reviewer_id, {"target_ids": set(), "assigned_count": 0})
            assigned_count = int(reviewer_state["assigned_count"])
            target_ids_raw = reviewer_state["target_ids"]
            target_ids = sorted(target_ids_raw) if isinstance(target_ids_raw, set) else []
            routed_count = routed_notifications.get(reviewer_id, 0)
            escalation_count = escalations.get(reviewer_id, 0)
            status = "overloaded" if assigned_count >= 3 and routed_count < assigned_count else "ready"
            if escalation_count:
                status = "escalated"
            items.append(
                ReviewerWorkloadItem(
                    reviewer_id=reviewer_id,
                    assigned_count=assigned_count,
                    routed_notifications=routed_count,
                    escalation_count=escalation_count,
                    target_ids=target_ids,
                    status=status,
                )
            )
        overloaded_reviewers = [item.reviewer_id for item in items if item.status == "overloaded"]
        return ReviewerWorkloadReport(
            title="Governance Reviewer Workload Report",
            status="attention_required" if overloaded_reviewers else "ready",
            reviewer_count=len(items),
            overloaded_reviewers=overloaded_reviewers,
            items=items,
        )

    def escalate_reviewer_workload(self, request: EscalationRequest) -> AuditRecord:
        record = self.record(
            AuditRecordRequest(
                actor_id=request.escalated_by,
                action="governance.escalate_reviewer_workload",
                target_type=request.target_type,
                target_id=request.target_id,
                decision="escalated",
                evidence={
                    "reviewer_id": request.reviewer_id,
                    "reason": request.reason,
                    "escalation_level": request.escalation_level,
                    "data_platform": "DB MARIAM",
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "governance.reviewer_workload_escalated",
            "audit-service",
            {
                "audit_id": record.audit_id,
                "reviewer_id": request.reviewer_id,
                "target_type": request.target_type,
                "target_id": request.target_id,
                "escalated_by": request.escalated_by,
                "escalation_level": request.escalation_level,
            },
        )
        return record

    def list(self) -> list[AuditRecord]:
        return self._repository.list()
