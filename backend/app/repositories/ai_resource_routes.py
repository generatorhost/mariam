from typing import Protocol

from app.core.ai_resources import ResourceRouteDecision


class AIResourceRouteRepository(Protocol):
    def save(self, decision: ResourceRouteDecision) -> ResourceRouteDecision:
        pass

    def list(self) -> list[ResourceRouteDecision]:
        pass


class InMemoryAIResourceRouteRepository:
    def __init__(self) -> None:
        self._routes: list[ResourceRouteDecision] = []

    def save(self, decision: ResourceRouteDecision) -> ResourceRouteDecision:
        self._routes.append(decision)
        return decision

    def list(self) -> list[ResourceRouteDecision]:
        return list(self._routes)
