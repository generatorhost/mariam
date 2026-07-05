from functools import lru_cache

from app.core.config import get_settings
from app.core.events import InMemoryEventBus
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
from app.services.ai_resources import AIResourceManager
from app.services.missions import MissionService
from app.services.runtime import RuntimeRegistry


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
    return RuntimeRegistry(get_event_bus())


@lru_cache
def get_mission_service() -> MissionService:
    return MissionService(get_event_bus(), get_mission_repository())


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
