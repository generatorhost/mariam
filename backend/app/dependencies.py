from functools import lru_cache

from app.core.config import get_settings
from app.core.events import InMemoryEventBus
from app.repositories.audit import AuditRepository, InMemoryAuditRepository, PostgresAuditRepository
from app.repositories.ai_resource_routes import (
    AIResourceRouteRepository,
    InMemoryAIResourceRouteRepository,
    PostgresAIResourceRouteRepository,
)
from app.repositories.events import (
    EventRepository,
    InMemoryEventRepository,
    PostgresEventRepository,
)
from app.repositories.missions import (
    InMemoryMissionRepository,
    MissionRepository,
    PostgresMissionRepository,
)
from app.repositories.plugins import (
    InMemoryPluginRepository,
    PluginRepository,
    PostgresPluginRepository,
)
from app.repositories.runtime_objects import (
    InMemoryRuntimeObjectRepository,
    PostgresRuntimeObjectRepository,
    RuntimeObjectRepository,
)
from app.services.ai_resources import AIResourceManager
from app.services.audit import AuditService
from app.services.command_center import CommandCenterSummaryService
from app.services.missions import MissionService
from app.services.runtime import RuntimeRegistry
from app.services.runtime_objects import RuntimeObjectService


@lru_cache
def get_event_bus() -> InMemoryEventBus:
    return InMemoryEventBus(get_event_repository())


@lru_cache
def get_event_repository() -> EventRepository:
    settings = get_settings()
    if settings.event_store == "postgres":
        return PostgresEventRepository(settings.database_url)
    return InMemoryEventRepository()


@lru_cache
def get_runtime_registry() -> RuntimeRegistry:
    return RuntimeRegistry(get_event_bus(), get_plugin_repository())


@lru_cache
def get_audit_service() -> AuditService:
    return AuditService(get_event_bus(), get_audit_repository())


@lru_cache
def get_audit_repository() -> AuditRepository:
    settings = get_settings()
    if settings.audit_store == "postgres":
        return PostgresAuditRepository(settings.database_url)
    return InMemoryAuditRepository()


@lru_cache
def get_runtime_object_service() -> RuntimeObjectService:
    return RuntimeObjectService(
        get_event_bus(),
        get_runtime_object_repository(),
        get_audit_service(),
    )


@lru_cache
def get_runtime_object_repository() -> RuntimeObjectRepository:
    settings = get_settings()
    if settings.runtime_object_store == "postgres":
        return PostgresRuntimeObjectRepository(settings.database_url)
    return InMemoryRuntimeObjectRepository()


@lru_cache
def get_plugin_repository() -> PluginRepository:
    settings = get_settings()
    if settings.plugin_store == "postgres":
        return PostgresPluginRepository(settings.database_url)
    return InMemoryPluginRepository()


@lru_cache
def get_mission_service() -> MissionService:
    return MissionService(get_event_bus(), get_mission_repository(), get_audit_service())


@lru_cache
def get_mission_repository() -> MissionRepository:
    settings = get_settings()
    if settings.mission_store == "postgres":
        return PostgresMissionRepository(settings.database_url)
    return InMemoryMissionRepository()


@lru_cache
def get_ai_resource_route_repository() -> AIResourceRouteRepository:
    settings = get_settings()
    if settings.ai_resource_route_store == "postgres":
        return PostgresAIResourceRouteRepository(settings.database_url)
    return InMemoryAIResourceRouteRepository()


@lru_cache
def get_ai_resource_manager() -> AIResourceManager:
    return AIResourceManager(get_event_bus(), get_ai_resource_route_repository())


@lru_cache
def get_command_center_summary_service() -> CommandCenterSummaryService:
    return CommandCenterSummaryService(
        get_runtime_registry(),
        get_runtime_object_service(),
        get_mission_service(),
        get_ai_resource_manager(),
        get_audit_service(),
        get_event_bus(),
    )
