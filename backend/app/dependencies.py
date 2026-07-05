from functools import lru_cache

from app.core.events import InMemoryEventBus
from app.services.ai_resources import AIResourceManager
from app.services.missions import MissionService
from app.services.runtime import RuntimeRegistry


@lru_cache
def get_event_bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@lru_cache
def get_runtime_registry() -> RuntimeRegistry:
    return RuntimeRegistry(get_event_bus())


@lru_cache
def get_mission_service() -> MissionService:
    return MissionService(get_event_bus())


@lru_cache
def get_ai_resource_manager() -> AIResourceManager:
    return AIResourceManager(get_event_bus())
