from datetime import UTC, datetime

from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.runtime_objects import (
    RuntimeObject,
    RuntimeObjectRequest,
    RuntimeObjectStateChangeRequest,
    create_runtime_object,
)
from app.repositories.runtime_objects import RuntimeObjectRepository
from app.services.audit import AuditService


class RuntimeObjectService:
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        repository: RuntimeObjectRepository,
        audit_service: AuditService,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository
        self._audit_service = audit_service

    def create(self, request: RuntimeObjectRequest) -> RuntimeObject:
        runtime_object = create_runtime_object(request)
        saved = self._repository.save(runtime_object)
        self._event_bus.publish(
            "runtime_object.registered",
            "runtime-object-service",
            {
                "object_id": saved.object_id,
                "object_type": saved.object_type,
                "name": saved.name,
                "status": saved.status,
                "data_platform": saved.data_platform,
            },
        )
        self._audit_service.record(
            AuditRecordRequest(
                actor_id="runtime-object-service",
                action="runtime_object.register",
                target_type=saved.object_type,
                target_id=saved.object_id,
                decision="approved",
                evidence={
                    "name": saved.name,
                    "version": saved.version,
                    "data_platform": saved.data_platform,
                },
            )
        )
        return saved

    def list(self) -> list[RuntimeObject]:
        return self._repository.list()

    def enable(self, object_id: str, request: RuntimeObjectStateChangeRequest) -> RuntimeObject:
        return self._change_status(object_id, "enabled", "enable", request)

    def disable(self, object_id: str, request: RuntimeObjectStateChangeRequest) -> RuntimeObject:
        return self._change_status(object_id, "disabled", "disable", request)

    def soft_delete(self, object_id: str, request: RuntimeObjectStateChangeRequest) -> RuntimeObject:
        return self._change_status(object_id, "deleted", "soft_delete", request)

    def restore(self, object_id: str, request: RuntimeObjectStateChangeRequest) -> RuntimeObject:
        return self._change_status(object_id, "disabled", "restore", request)

    def _change_status(
        self,
        object_id: str,
        status: str,
        action_verb: str,
        request: RuntimeObjectStateChangeRequest,
    ) -> RuntimeObject:
        runtime_object = self._repository.get(object_id)
        if runtime_object is None:
            raise ValueError(f"Runtime object {object_id} was not found.")

        updated = runtime_object.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(UTC),
            }
        )
        saved = self._repository.update(updated)
        action = f"runtime_object.{action_verb}"
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action=action,
                target_type=saved.object_type,
                target_id=saved.object_id,
                decision="approved",
                evidence={
                    "name": saved.name,
                    "version": saved.version,
                    "reason": request.reason,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            action,
            "runtime-object-service",
            {
                "object_id": saved.object_id,
                "object_type": saved.object_type,
                "name": saved.name,
                "status": saved.status,
                "actor_id": request.actor_id,
                "data_platform": saved.data_platform,
            },
        )
        return saved
