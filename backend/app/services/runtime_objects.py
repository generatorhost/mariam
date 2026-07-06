from datetime import UTC, datetime
from uuid import uuid4

from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.runtime_objects import (
    RuntimeObject,
    RuntimeObjectDNAImportRequest,
    RuntimeObjectDNAPackage,
    RuntimeObjectPatchRequest,
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

    def patch(self, object_id: str, request: RuntimeObjectPatchRequest) -> RuntimeObject:
        runtime_object = self._repository.get(object_id)
        if runtime_object is None:
            raise ValueError(f"Runtime object {object_id} was not found.")

        rollback_stack = list(runtime_object.manifest.get("_rollback_stack", []))
        rollback_stack.append(
            {
                "name": runtime_object.name,
                "version": runtime_object.version,
                "manifest": {
                    key: value
                    for key, value in runtime_object.manifest.items()
                    if key != "_rollback_stack"
                },
                "captured_at": datetime.now(UTC).isoformat(),
                "reason": request.reason,
            }
        )
        manifest = {
            **{
                key: value
                for key, value in runtime_object.manifest.items()
                if key != "_rollback_stack"
            },
            **request.manifest_updates,
            "_rollback_stack": rollback_stack,
        }
        updated = runtime_object.model_copy(
            update={
                "name": request.name or runtime_object.name,
                "version": request.version or runtime_object.version,
                "manifest": manifest,
                "updated_at": datetime.now(UTC),
            }
        )
        saved = self._repository.update(updated)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="runtime_object.patch",
                target_type=saved.object_type,
                target_id=saved.object_id,
                decision="approved",
                evidence={
                    "name": saved.name,
                    "version": saved.version,
                    "reason": request.reason,
                    "manifest_updates": request.manifest_updates,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "runtime_object.patch",
            "runtime-object-service",
            {
                "object_id": saved.object_id,
                "object_type": saved.object_type,
                "name": saved.name,
                "status": saved.status,
                "version": saved.version,
                "actor_id": request.actor_id,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def rollback(self, object_id: str, request: RuntimeObjectStateChangeRequest) -> RuntimeObject:
        runtime_object = self._repository.get(object_id)
        if runtime_object is None:
            raise ValueError(f"Runtime object {object_id} was not found.")

        rollback_stack = list(runtime_object.manifest.get("_rollback_stack", []))
        if not rollback_stack:
            raise ValueError(f"Runtime object {object_id} has no rollback point.")

        rollback_point = rollback_stack.pop()
        manifest = {
            **rollback_point["manifest"],
            "_rollback_stack": rollback_stack,
        }
        updated = runtime_object.model_copy(
            update={
                "name": rollback_point["name"],
                "version": rollback_point["version"],
                "manifest": manifest,
                "updated_at": datetime.now(UTC),
            }
        )
        saved = self._repository.update(updated)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="runtime_object.rollback",
                target_type=saved.object_type,
                target_id=saved.object_id,
                decision="approved",
                evidence={
                    "name": saved.name,
                    "version": saved.version,
                    "reason": request.reason,
                    "rollback_point": rollback_point,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "runtime_object.rollback",
            "runtime-object-service",
            {
                "object_id": saved.object_id,
                "object_type": saved.object_type,
                "name": saved.name,
                "status": saved.status,
                "version": saved.version,
                "actor_id": request.actor_id,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def export_dna(self, object_id: str, request: RuntimeObjectStateChangeRequest) -> RuntimeObjectDNAPackage:
        runtime_object = self._repository.get(object_id)
        if runtime_object is None:
            raise ValueError(f"Runtime object {object_id} was not found.")

        exported_at = datetime.now(UTC)
        manifest = {
            key: value
            for key, value in runtime_object.manifest.items()
            if key != "_rollback_stack"
        }
        dna_package = RuntimeObjectDNAPackage(
            dna_package_id=f"dna-{uuid4()}",
            source_object_id=runtime_object.object_id,
            object_type=runtime_object.object_type,
            name=runtime_object.name,
            version=runtime_object.version,
            exported_at=exported_at,
            payload={
                "schema": "mariam.runtime_object.dna.v1",
                "object_type": runtime_object.object_type,
                "name": runtime_object.name,
                "status": runtime_object.status,
                "version": runtime_object.version,
                "manifest": manifest,
                "export_policy": {
                    "requires_governance_review_before_import": True,
                    "source_data_platform": runtime_object.data_platform,
                },
            },
        )
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="runtime_object.export_dna",
                target_type=runtime_object.object_type,
                target_id=runtime_object.object_id,
                decision="approved",
                evidence={
                    "name": runtime_object.name,
                    "version": runtime_object.version,
                    "reason": request.reason,
                    "dna_package_id": dna_package.dna_package_id,
                    "data_platform": runtime_object.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "runtime_object.export_dna",
            "runtime-object-service",
            {
                "object_id": runtime_object.object_id,
                "dna_package_id": dna_package.dna_package_id,
                "object_type": runtime_object.object_type,
                "name": runtime_object.name,
                "version": runtime_object.version,
                "actor_id": request.actor_id,
                "data_platform": runtime_object.data_platform,
            },
        )
        return dna_package

    def import_dna(self, request: RuntimeObjectDNAImportRequest) -> RuntimeObject:
        dna_package = request.dna_package
        payload = dna_package.payload
        if payload.get("schema") != "mariam.runtime_object.dna.v1":
            raise ValueError("Unsupported runtime object DNA schema.")

        now = datetime.now(UTC)
        imported = RuntimeObject(
            object_id=str(uuid4()),
            object_type=payload["object_type"],
            name=f"{payload['name']} Imported",
            status="disabled",
            version=payload["version"],
            manifest={
                **payload.get("manifest", {}),
                "dna_import": {
                    "source_dna_package_id": dna_package.dna_package_id,
                    "source_object_id": dna_package.source_object_id,
                    "imported_at": now.isoformat(),
                    "requires_governance_review_before_enable": True,
                },
            },
            created_at=now,
            updated_at=now,
        )
        saved = self._repository.save(imported)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="runtime_object.import_dna",
                target_type=saved.object_type,
                target_id=saved.object_id,
                decision="approved",
                evidence={
                    "name": saved.name,
                    "version": saved.version,
                    "reason": request.reason,
                    "source_dna_package_id": dna_package.dna_package_id,
                    "source_object_id": dna_package.source_object_id,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "runtime_object.import_dna",
            "runtime-object-service",
            {
                "object_id": saved.object_id,
                "source_dna_package_id": dna_package.dna_package_id,
                "object_type": saved.object_type,
                "name": saved.name,
                "status": saved.status,
                "version": saved.version,
                "actor_id": request.actor_id,
                "data_platform": saved.data_platform,
            },
        )
        return saved

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
