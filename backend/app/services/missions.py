from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.missions import (
    Mission,
    MissionApprovalRequest,
    MissionRejectionRequest,
    MissionRequest,
    MissionStatus,
    create_mission_plan,
)
from app.repositories.missions import MissionRepository
from app.services.audit import AuditService


class MissionService:
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        repository: MissionRepository,
        audit_service: AuditService,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository
        self._audit_service = audit_service

    def create(self, request: MissionRequest) -> Mission:
        mission = create_mission_plan(request)
        saved = self._repository.save(mission)
        self._event_bus.publish(
            "mission.created",
            "mission-service",
            {
                "mission_id": mission.mission_id,
                "plugin_id": mission.plugin_id,
                "status": mission.status,
                "data_platform": mission.data_platform,
            },
        )
        return saved

    def approve(self, mission_id: str, request: MissionApprovalRequest) -> Mission:
        mission = self._repository.get(mission_id)
        if mission is None:
            raise ValueError(f"Mission {mission_id} was not found.")
        approved = mission.model_copy(update={"status": MissionStatus.approved})
        saved = self._repository.update(approved)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.approved_by,
                action="mission.approve",
                target_type="mission",
                target_id=mission_id,
                decision="approved",
                evidence={
                    "data_platform": saved.data_platform,
                    "governance_gate": saved.governance_gate,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "mission.approved",
            "mission-service",
            {
                "mission_id": saved.mission_id,
                "plugin_id": saved.plugin_id,
                "status": saved.status,
                "approved_by": request.approved_by,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def reject(self, mission_id: str, request: MissionRejectionRequest) -> Mission:
        mission = self._repository.get(mission_id)
        if mission is None:
            raise ValueError(f"Mission {mission_id} was not found.")
        rejected = mission.model_copy(update={"status": MissionStatus.rejected})
        saved = self._repository.update(rejected)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.rejected_by,
                action="mission.reject",
                target_type="mission",
                target_id=mission_id,
                decision="rejected",
                evidence={
                    "data_platform": saved.data_platform,
                    "governance_gate": saved.governance_gate,
                    "rejection_reason": request.reason,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "mission.rejected",
            "mission-service",
            {
                "mission_id": saved.mission_id,
                "plugin_id": saved.plugin_id,
                "status": saved.status,
                "rejected_by": request.rejected_by,
                "reason": request.reason,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def list(self) -> list[Mission]:
        return self._repository.list()
