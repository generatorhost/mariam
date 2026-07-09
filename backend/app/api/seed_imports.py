from fastapi import APIRouter, Depends, HTTPException

from app.core.plugin_manifest import PluginManifest
from app.core.seed_imports import (
    ExternalSeedSourceListResponse,
    SeedImportListResponse,
    SeedImportRequest,
    SeedImportResponse,
    SeedPipelineRequest,
    SeedPipelineResponse,
    SeedPluginCandidateListResponse,
    SeedPluginPromotionRequest,
    SeedPluginPromotionResponse,
    SeedRuntimeLoadRequest,
    SeedRuntimeLoadResponse,
)
from app.dependencies import get_runtime_object_service, get_seed_import_service, require_permission
from app.services.runtime_objects import RuntimeObjectService
from app.services.seed_imports import SeedImportService

router = APIRouter(prefix="/api/seed-imports", tags=["seed-imports"])


@router.get("", response_model=SeedImportListResponse)
def list_seed_imports(service: SeedImportService = Depends(get_seed_import_service)) -> SeedImportListResponse:
    return {"imports": service.list_imports()}


@router.get("/external-sources", response_model=ExternalSeedSourceListResponse)
def list_external_seed_sources(
    service: SeedImportService = Depends(get_seed_import_service),
) -> ExternalSeedSourceListResponse:
    return {"external_sources": service.list_external_sources()}


@router.post("/external-sources/{source_key}/prepare", response_model=SeedImportResponse)
def prepare_external_seed_source(
    source_key: str,
    request: SeedImportRequest,
    authorization=Depends(require_permission("plugin.register", "external_seed_source")),
    service: SeedImportService = Depends(get_seed_import_service),
) -> SeedImportResponse:
    try:
        return {"seed_import": service.prepare_external_source(source_key, request)}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/inspect", response_model=SeedImportResponse)
def inspect_seed_source(
    request: SeedImportRequest,
    authorization=Depends(require_permission("plugin.register", "seed_source")),
    service: SeedImportService = Depends(get_seed_import_service),
) -> SeedImportResponse:
    try:
        return {"seed_import": service.inspect_source(request)}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/pipeline", response_model=SeedPipelineResponse)
def run_seed_pipeline(
    request: SeedPipelineRequest,
    authorization=Depends(require_permission("plugin.register", "seed_pipeline")),
    service: SeedImportService = Depends(get_seed_import_service),
    runtime_objects: RuntimeObjectService = Depends(get_runtime_object_service),
) -> SeedPipelineResponse:
    try:
        seed_import = service.inspect_source(request)
        runtime_load = None
        promoted_plugins = []
        if request.activation_mode in {"load_runtime", "full"}:
            runtime_requests = service.build_runtime_object_requests(seed_import.source_id)
            created = [runtime_objects.create(runtime_request) for runtime_request in runtime_requests]
            runtime_load = service.mark_runtime_loaded(
                seed_import.source_id,
                SeedRuntimeLoadRequest(
                    actor_id=request.actor_id,
                    reason=f"Pipeline runtime load for {request.source_path}.",
                    evidence={"activation_mode": request.activation_mode, **request.evidence},
                ),
                [item.object_id for item in created],
            )
            seed_import = service.get(seed_import.source_id)
        if request.activation_mode in {"promote_plugins", "full"}:
            candidate_ids = request.promote_plugin_ids or [candidate.plugin_id for candidate in seed_import.plugin_candidates]
            for candidate_id in candidate_ids:
                plugin = service.promote_plugin_candidate(
                    seed_import.source_id,
                    candidate_id,
                    SeedPluginPromotionRequest(
                        actor_id=request.actor_id,
                        reason=f"Pipeline plugin promotion for {candidate_id}.",
                        evidence={"activation_mode": request.activation_mode, **request.evidence},
                    ),
                )
                promoted_plugins.append(
                    {
                        "plugin_id": plugin.plugin_id,
                        "name": plugin.name,
                        "status": plugin.status,
                        "api_prefix": plugin.api_prefix,
                        "dashboard_route": plugin.dashboard_route,
                        "private_tables": [
                            f"{plugin.plugin_id}_settings",
                            f"{plugin.plugin_id}_workflows",
                            f"{plugin.plugin_id}_artifacts",
                        ],
                    }
                )
        return SeedPipelineResponse(
            activation_mode=request.activation_mode,
            seed_import=seed_import,
            runtime_load=runtime_load,
            promoted_plugins=promoted_plugins,
            notes=[
                "Pipeline executed according to the selected activation mode.",
                "Extracted DNA remains traceable to the source import record.",
                "Promoted plugins are disabled until validation and governance approval.",
            ],
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{source_id}", response_model=SeedImportResponse)
def get_seed_import(
    source_id: str,
    service: SeedImportService = Depends(get_seed_import_service),
) -> SeedImportResponse:
    try:
        return {"seed_import": service.get(source_id)}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{source_id}/plugin-candidates", response_model=SeedPluginCandidateListResponse)
def list_seed_plugin_candidates(
    source_id: str,
    service: SeedImportService = Depends(get_seed_import_service),
) -> SeedPluginCandidateListResponse:
    try:
        record = service.get(source_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"source_id": source_id, "plugin_candidates": record.plugin_candidates}


@router.post("/{source_id}/load-runtime-objects", response_model=SeedRuntimeLoadResponse)
def load_seed_runtime_objects(
    source_id: str,
    request: SeedRuntimeLoadRequest,
    authorization=Depends(require_permission("runtime_object.register", "seed_dna_runtime_load")),
    service: SeedImportService = Depends(get_seed_import_service),
    runtime_objects: RuntimeObjectService = Depends(get_runtime_object_service),
) -> SeedRuntimeLoadResponse:
    try:
        runtime_requests = service.build_runtime_object_requests(source_id)
        created = [runtime_objects.create(runtime_request) for runtime_request in runtime_requests]
        return service.mark_runtime_loaded(source_id, request, [item.object_id for item in created])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/{source_id}/plugin-candidates/{plugin_id}/promote", response_model=SeedPluginPromotionResponse)
def promote_seed_plugin_candidate(
    source_id: str,
    plugin_id: str,
    request: SeedPluginPromotionRequest,
    authorization=Depends(require_permission("plugin.register", "seed_plugin_candidate")),
    service: SeedImportService = Depends(get_seed_import_service),
) -> SeedPluginPromotionResponse:
    try:
        plugin: PluginManifest = service.promote_plugin_candidate(source_id, plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "source_id": source_id,
        "plugin_id": plugin.plugin_id,
        "status": plugin.status,
        "promotion_notes": [
            "Plugin was created disabled for governance review.",
            "Private DB tables must use the plugin id as prefix.",
            "Seed features remain traceable to the source import record.",
        ],
    }
