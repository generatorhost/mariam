from functools import lru_cache

from app.core.events import InMemoryEventBus
from app.services.runtime import RuntimeRegistry


@lru_cache
def get_event_bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@lru_cache
def get_runtime_registry() -> RuntimeRegistry:
    return RuntimeRegistry(get_event_bus())

