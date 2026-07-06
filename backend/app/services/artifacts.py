from app.core.artifacts import (
    Artifact,
    ArtifactApprovalRequest,
    ArtifactRejectionRequest,
    ArtifactStatus,
    create_artifact_from_mission,
)
from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.repositories.artifacts import ArtifactRepository
from app.services.audit import AuditService
from app.services.missions import MissionService


class ArtifactService:
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        repository: ArtifactRepository,
        audit_service: AuditService,
        mission_service: MissionService,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository
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

    def list(self) -> list[Artifact]:
        return self._repository.list()

    def _get(self, artifact_id: str) -> Artifact:
        artifact = self._repository.get(artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact {artifact_id} was not found.")
        return artifact
