from app.core.audit import AuditRecord, AuditRecordRequest, create_audit_record
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

    def list(self) -> list[AuditRecord]:
        return self._repository.list()
