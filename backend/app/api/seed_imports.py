from fastapi import APIRouter, Depends, HTTPException

from app.core.plugin_manifest import PluginManifest
from app.core.seed_imports import (
    ExternalSeedSourceListResponse,
    SeedImportListResponse,
    SeedImportRequest,
    SeedImportResponse,
    SeedPluginCandidateListResponse,
    SeedPluginPromotionRequest,
    SeedPluginPromotionResponse,
)
from app.dependencies import get_seed_import_service, require_permission
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
