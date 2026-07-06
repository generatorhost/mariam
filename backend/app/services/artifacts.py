from __future__ import annotations

from app.core.artifacts import (
    Artifact,
    ArtifactApprovalRequest,
    ArtifactDeliveryRequest,
    ArtifactRejectionRequest,
    ArtifactStatus,
    DeliveryPackage,
    create_delivery_package,
    create_artifact_from_mission,
)
from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.repositories.artifacts import ArtifactRepository, DeliveryPackageRepository
from app.services.audit import AuditService
from app.services.missions import MissionService


class ArtifactService:
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        repository: ArtifactRepository,
        delivery_repository: DeliveryPackageRepository,
        audit_service: AuditService,
        mission_service: MissionService,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository
        self._delivery_repository = delivery_repository
        self._audit_service = audit_service
        self._mission_service = mission_service

    def generate_from_mission(self, mission_id: str) -> Artifact:
        mission = next(
            (candidate for candidate in self._mission_service.list() if candidate.mission_id == mission_id),
            None,
        )
        if mission is None:
            raise ValueError(f"Mission {mission_id} was not found.")
        artifact = create_artifact_from_mission(
            mission_id=mission.mission_id,
            plugin_id=mission.plugin_id,
            user_request=mission.user_request,
        )
        saved = self._repository.save(artifact)
        self._event_bus.publish(
            "artifact.generated",
            "artifact-service",
            {
                "artifact_id": saved.artifact_id,
                "mission_id": saved.mission_id,
                "plugin_id": saved.plugin_id,
                "status": saved.status,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def approve(self, artifact_id: str, request: ArtifactApprovalRequest) -> Artifact:
        artifact = self._get(artifact_id)
        approved = artifact.model_copy(update={"status": ArtifactStatus.approved})
        saved = self._repository.update(approved)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.approved_by,
                action="artifact.approve",
                target_type="artifact",
                target_id=artifact_id,
                decision="approved",
                evidence={
                    "mission_id": saved.mission_id,
                    "plugin_id": saved.plugin_id,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "artifact.approved",
            "artifact-service",
            {
                "artifact_id": saved.artifact_id,
                "mission_id": saved.mission_id,
                "plugin_id": saved.plugin_id,
                "approved_by": request.approved_by,
                "status": saved.status,
            },
        )
        return saved

    def reject(self, artifact_id: str, request: ArtifactRejectionRequest) -> Artifact:
        artifact = self._get(artifact_id)
        rejected = artifact.model_copy(update={"status": ArtifactStatus.rejected})
        saved = self._repository.update(rejected)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.rejected_by,
                action="artifact.reject",
                target_type="artifact",
                target_id=artifact_id,
                decision="rejected",
                evidence={
                    "mission_id": saved.mission_id,
                    "plugin_id": saved.plugin_id,
                    "rejection_reason": request.reason,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "artifact.rejected",
            "artifact-service",
            {
                "artifact_id": saved.artifact_id,
                "mission_id": saved.mission_id,
                "plugin_id": saved.plugin_id,
                "rejected_by": request.rejected_by,
                "status": saved.status,
            },
        )
        return saved

    def package_for_delivery(self, artifact_id: str, request: ArtifactDeliveryRequest) -> DeliveryPackage:
        artifact = self._get(artifact_id)
        if artifact.status != ArtifactStatus.approved:
            raise ValueError(f"Artifact {artifact_id} must be approved before delivery packaging.")
        delivery_package = create_delivery_package(artifact, request.destination)
        saved_delivery = self._delivery_repository.save(delivery_package)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.packaged_by,
                action="artifact.package_delivery",
                target_type="artifact",
                target_id=artifact_id,
                decision="approved",
                evidence={
                    "delivery_id": saved_delivery.delivery_id,
                    "mission_id": saved_delivery.mission_id,
                    "plugin_id": saved_delivery.plugin_id,
                    "destination": saved_delivery.destination,
                    "data_platform": saved_delivery.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "artifact.delivery_packaged",
            "artifact-service",
            {
                "delivery_id": saved_delivery.delivery_id,
                "artifact_id": saved_delivery.artifact_id,
                "mission_id": saved_delivery.mission_id,
                "plugin_id": saved_delivery.plugin_id,
                "destination": saved_delivery.destination,
                "status": saved_delivery.status,
            },
        )
        return saved_delivery

    def list(self) -> list[Artifact]:
        return self._repository.list()

    def list_delivery_packages(self) -> list[DeliveryPackage]:
        return self._delivery_repository.list()

    def _get(self, artifact_id: str) -> Artifact:
        artifact = self._repository.get(artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact {artifact_id} was not found.")
        return artifact
