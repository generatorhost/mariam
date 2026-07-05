from dataclasses import dataclass

from app.core.events import InMemoryEventBus
from app.services.ai_resources import AIResourceManager
from app.services.audit import AuditService
from app.services.missions import MissionService
from app.services.runtime import RuntimeRegistry
from app.services.runtime_objects import RuntimeObjectService


@dataclass
class CommandCenterSummary:
    health: str
    runtime_objects: int
    plugins: int
    missions: int
    ai_routes: int
    audit_records: int
    runtime_events: int


class CommandCenterSummaryService:
    def __init__(
        self,
        runtime_registry: RuntimeRegistry,
        runtime_object_service: RuntimeObjectService,
        mission_service: MissionService,
        ai_resource_manager: AIResourceManager,
        audit_service: AuditService,
        event_bus: InMemoryEventBus,
    ) -> None:
        self._runtime_registry = runtime_registry
        self._runtime_object_service = runtime_object_service
        self._mission_service = mission_service
        self._ai_resource_manager = ai_resource_manager
        self._audit_service = audit_service
        self._event_bus = event_bus

    def summarize(self) -> CommandCenterSummary:
        health_statuses = self._runtime_registry.health()
        health = "healthy"
        if any(status.status != "healthy" for status in health_statuses):
            health = "degraded"

        return CommandCenterSummary(
            health=health,
            runtime_objects=len(self._runtime_object_service.list()),
            plugins=len(self._runtime_registry.list_plugins()),
            missions=len(self._mission_service.list()),
            ai_routes=len(self._ai_resource_manager.list_routes()),
            audit_records=len(self._audit_service.list()),
            runtime_events=len(self._event_bus.list_events()),
        )
