from app.core.ai_resources import (
    PROVIDERS,
    ModelProvider,
    ResourceRouteDecision,
    ResourceRouteRequest,
)
from app.core.events import InMemoryEventBus


class AIResourceManager:
    def __init__(self, event_bus: InMemoryEventBus) -> None:
        self._event_bus = event_bus

    def list_providers(self) -> list[ModelProvider]:
        return PROVIDERS

    def route(self, request: ResourceRouteRequest) -> ResourceRouteDecision:
        candidates = [
            provider
            for provider in PROVIDERS
            if request.capability in provider.capabilities and provider.status == "available"
        ]
        if not candidates:
            candidates = [provider for provider in PROVIDERS if provider.status == "available"]
        selected = self._select_provider(candidates, request)
        fallback_ids = [provider.provider_id for provider in candidates if provider.provider_id != selected.provider_id]
        decision = ResourceRouteDecision(
            capability=request.capability,
            selected_provider=selected,
            reason=self._reason(selected, request),
            policy="chief_requests_capability_ai_resource_manager_selects_provider",
            fallback_provider_ids=fallback_ids,
        )
        self._event_bus.publish(
            "ai_resource.route.selected",
            "ai-resource-manager",
            {
                "capability": decision.capability,
                "provider_id": selected.provider_id,
                "requested_by": request.requested_by,
                "policy": decision.policy,
            },
        )
        return decision

    def _select_provider(
        self,
        candidates: list[ModelProvider],
        request: ResourceRouteRequest,
    ) -> ModelProvider:
        if request.privacy_preference == "local_first":
            local = [provider for provider in candidates if provider.local]
            if local:
                return local[0]
        return candidates[0]

    def _reason(self, provider: ModelProvider, request: ResourceRouteRequest) -> str:
        if provider.local and request.privacy_preference == "local_first":
            return "Selected local provider to satisfy privacy/local-first routing."
        return "Selected first available provider matching the requested capability."
