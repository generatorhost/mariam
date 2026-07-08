from functools import lru_cache

from fastapi import Depends, HTTPException, Request

from app.core.audit import AuditRecordRequest
from app.core.auth import PermissionEnforcementRequest, PermissionEnforcementResult
from app.core.config import get_settings
from app.core.events import InMemoryEventBus
from app.repositories.audit import AuditRepository, InMemoryAuditRepository, PostgresAuditRepository
from app.repositories.artifacts import (
    ArtifactQualityReviewRepository,
    ArtifactRepository,
    DeliveryPackageRepository,
    InMemoryArtifactRepository,
    InMemoryArtifactQualityReviewRepository,
    InMemoryDeliveryPackageRepository,
    PostgresArtifactRepository,
    PostgresArtifactQualityReviewRepository,
    PostgresDeliveryPackageRepository,
)
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
from app.repositories.seed_imports import (
    InMemorySeedImportRepository,
    PostgresSeedImportRepository,
    SeedImportRepository,
)
from app.services.ai_resources import AIResourceManager
from app.services.artifacts import ArtifactService
from app.services.audit import AuditService
from app.services.auth import AuthService
from app.services.command_center import CommandCenterSummaryService
from app.services.missions import MissionService
from app.services.runtime import RuntimeRegistry
from app.services.runtime_objects import RuntimeObjectService
from app.services.seed_imports import SeedImportService


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
    return RuntimeRegistry(get_event_bus(), get_plugin_repository(), get_audit_service())


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
def get_seed_import_repository() -> SeedImportRepository:
    settings = get_settings()
    if settings.seed_import_store == "postgres":
        return PostgresSeedImportRepository(settings.database_url)
    return InMemorySeedImportRepository()


@lru_cache
def get_seed_import_service() -> SeedImportService:
    return SeedImportService(
        get_event_bus(),
        get_seed_import_repository(),
        get_runtime_registry(),
        get_audit_service(),
    )


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
def get_artifact_service() -> ArtifactService:
    return ArtifactService(
        get_event_bus(),
        get_artifact_repository(),
        get_delivery_package_repository(),
        get_artifact_quality_review_repository(),
        get_audit_service(),
        get_mission_service(),
    )


@lru_cache
def get_artifact_repository() -> ArtifactRepository:
    settings = get_settings()
    if settings.mission_store == "postgres":
        return PostgresArtifactRepository(settings.database_url)
    return InMemoryArtifactRepository()


@lru_cache
def get_delivery_package_repository() -> DeliveryPackageRepository:
    settings = get_settings()
    if settings.mission_store == "postgres":
        return PostgresDeliveryPackageRepository(settings.database_url)
    return InMemoryDeliveryPackageRepository()


@lru_cache
def get_artifact_quality_review_repository() -> ArtifactQualityReviewRepository:
    settings = get_settings()
    if settings.mission_store == "postgres":
        return PostgresArtifactQualityReviewRepository(settings.database_url)
    return InMemoryArtifactQualityReviewRepository()


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
def get_auth_service() -> AuthService:
    return AuthService()


def require_permission(permission: str, target_type: str):
    def dependency(
        http_request: Request,
        service: AuthService = Depends(get_auth_service),
        audit_service: AuditService = Depends(get_audit_service),
    ) -> PermissionEnforcementResult:
        target_id = next(iter(http_request.path_params.values()), http_request.url.path)
        actor_id = http_request.headers.get("x-mariam-actor-id", "command-center-operator")
        request_id = http_request.headers.get("x-mariam-request-id", "local-command-center-request")
        evidence = {
            "method": http_request.method,
            "path": http_request.url.path,
            "request_id": request_id,
            "permission": permission,
            "authorization_dependency": True,
            "data_platform": "DB MARIAM",
        }
        try:
            result = service.enforce_permission(
                PermissionEnforcementRequest(
                    permission=permission,
                    actor_id=actor_id,
                    target_type=target_type,
                    target_id=str(target_id),
                    reason=f"Authorize {http_request.method} {http_request.url.path}.",
                    evidence=evidence,
                )
            )
        except PermissionError as error:
            audit_service.record(
                AuditRecordRequest(
                    actor_id=actor_id,
                    action="authorization.permission_enforced",
                    target_type=target_type,
                    target_id=str(target_id),
                    decision="denied",
                    evidence={
                        **evidence,
                        "reason": f"Authorize {http_request.method} {http_request.url.path}.",
                        "error": str(error),
                    },
                )
            )
            raise HTTPException(status_code=403, detail=str(error)) from error
        audit_service.record(
            AuditRecordRequest(
                actor_id=result.actor_id,
                action="authorization.permission_enforced",
                target_type=result.target_type,
                target_id=result.target_id,
                decision="granted",
                evidence={**result.evidence, "reason": result.reason},
            )
        )
        return result

    return dependency


@lru_cache
def get_command_center_summary_service() -> CommandCenterSummaryService:
    return CommandCenterSummaryService(
        get_runtime_registry(),
        get_runtime_object_service(),
        get_mission_service(),
        get_artifact_service(),
        get_ai_resource_manager(),
        get_audit_service(),
        get_event_bus(),
    )
