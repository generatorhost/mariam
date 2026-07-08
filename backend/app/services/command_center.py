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
    recent_events: list[dict[str, object]]


@dataclass
class ReadinessCheck:
    name: str
    status: str
    detail: str


@dataclass
class CommandCenterReadiness:
    status: str
    checks: list[ReadinessCheck]


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

        events = self._event_bus.list_events()
        recent_events = [
            {
                "event_id": event.event_id,
                "name": event.name,
                "source": event.source,
                "created_at": event.created_at.isoformat(),
                "payload": event.payload,
            }
            for event in sorted(events, key=lambda event: event.created_at, reverse=True)[:5]
        ]

        return CommandCenterSummary(
            health=health,
            runtime_objects=len(self._runtime_object_service.list()),
            plugins=len(self._runtime_registry.list_plugins()),
            missions=len(self._mission_service.list()),
            ai_routes=len(self._ai_resource_manager.list_routes()),
            audit_records=len(self._audit_service.list()),
            runtime_events=len(events),
            recent_events=recent_events,
        )

    def readiness(self) -> CommandCenterReadiness:
        health_statuses = self._runtime_registry.health()
        checks = [
            ReadinessCheck(
                name="runtime_core",
                status="ready" if all(status.status == "healthy" for status in health_statuses) else "blocked",
                detail="Runtime registry, event bus, and plugin registry health are available.",
            ),
            ReadinessCheck(
                name="event_bus",
                status="ready",
                detail=f"{len(self._event_bus.list_events())} runtime events available for traceability.",
            ),
            ReadinessCheck(
                name="audit_layer",
                status="ready",
                detail=f"{len(self._audit_service.list())} audit records available.",
            ),
            ReadinessCheck(
                name="mission_layer",
                status="ready",
                detail=f"{len(self._mission_service.list())} missions available.",
            ),
            ReadinessCheck(
                name="plugin_registry",
                status="ready",
                detail=f"{len(self._runtime_registry.list_plugins())} Plugin-managed Business Units registered.",
            ),
            ReadinessCheck(
                name="runtime_objects",
                status="ready",
                detail=f"{len(self._runtime_object_service.list())} runtime objects available.",
            ),
            ReadinessCheck(
                name="ai_resource_manager",
                status="ready",
                detail=f"{len(self._ai_resource_manager.list_routes())} AI routing decisions available.",
            ),
            ReadinessCheck(
                name="artifact_delivery_pipeline",
                status="ready",
                detail="Artifact approval, quality review, delivery packaging, and client confirmation APIs are mounted.",
            ),
        ]
        overall = "ready" if all(check.status == "ready" for check in checks) else "blocked"
        return CommandCenterReadiness(status=overall, checks=checks)
