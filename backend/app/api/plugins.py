from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.plugin_manifest import (
    PluginApprovalRequest,
    PluginApprovalReport,
    PluginChatRequest,
    PluginDNAImportRequest,
    PluginDNAPackage,
    PluginImpactRequest,
    PluginImpactReport,
    PluginManifest,
    PluginPatchRequest,
    PluginSettingsUpdateRequest,
    PluginStateChangeRequest,
    PluginValidationReport,
)
from app.core.missions import Mission, MissionRequest
from app.dependencies import get_mission_service, get_runtime_registry, require_permission
from app.services.missions import MissionService
from app.services.runtime import RuntimeRegistry

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class PluginTimelineAuditRecordResponse(BaseModel):
    audit_id: str
    actor_id: str
    action: str
    decision: str
    evidence: dict[str, Any]
    created_at: datetime


class PluginTimelineEventResponse(BaseModel):
    event_id: str
    name: str
    source: str
    payload: dict[str, Any]
    created_at: datetime


class PluginTimelineSummaryResponse(BaseModel):
    audit_records: int
    events: int
    rollback_points: int
    status: str
    version: str


class PluginTimelineResponse(BaseModel):
    plugin: PluginManifest
    audit_records: list[PluginTimelineAuditRecordResponse]
    events: list[PluginTimelineEventResponse]
    summary: PluginTimelineSummaryResponse


class PluginSettingsResponse(BaseModel):
    plugin_id: str
    settings_schema: dict[str, Any]
    settings_values: dict[str, Any]
    status: str
    data_platform: str


class PluginDashboardLifecycleResponse(BaseModel):
    validation_passed: bool
    impact_ready: bool
    approval_ready: bool
    rollback_points: int


class PluginDashboardResponse(BaseModel):
    plugin_id: str
    name: str
    version: str
    status: str
    dashboard_route: str
    api_prefix: str
    data_boundary: str
    chief_agent_role: str
    swarm_roles: list[str]
    workflows: list[str]
    permissions: list[str]
    settings_values: dict[str, Any]
    lifecycle: PluginDashboardLifecycleResponse
    activity: PluginTimelineSummaryResponse
    data_platform: str


class PluginChiefAgentResponse(BaseModel):
    role: str
    entrypoint: str
    responsibilities: list[str]


class PluginSwarmAgentResponse(BaseModel):
    role: str
    scope: str
    data_boundary: str


class PluginWorkspaceActionResponse(BaseModel):
    label: str
    api: str
    result: str


class PluginDataBoundaryResponse(BaseModel):
    platform: str
    boundary: str
    shared_tables: list[str]
    private_tables: list[str]


class PluginWorkspaceResponse(BaseModel):
    plugin_id: str
    title: str
    status: str
    dashboard: PluginDashboardResponse
    settings: PluginSettingsResponse
    chief_agent: PluginChiefAgentResponse
    swarm: list[PluginSwarmAgentResponse]
    workspace_actions: list[PluginWorkspaceActionResponse]
    data_boundary: PluginDataBoundaryResponse
    activity: PluginTimelineSummaryResponse
    data_platform: str


class PluginListResponse(BaseModel):
    plugins: list[PluginManifest]


class PluginMutationResponse(BaseModel):
    plugin: PluginManifest


class PluginChatSummaryResponse(BaseModel):
    plugin_id: str
    chief_agent_role: str
    mission_id: str
    status: str
    governance_gate: str
    data_platform: str


class PluginChatResponse(BaseModel):
    chat: PluginChatSummaryResponse
    mission: Mission


class PluginValidationResponse(BaseModel):
    validation_report: PluginValidationReport


class PluginImpactResponse(BaseModel):
    impact_report: PluginImpactReport


class PluginApprovalResponse(BaseModel):
    approval_report: PluginApprovalReport


class PluginDNAExportResponse(BaseModel):
    dna_package: PluginDNAPackage


@router.get("", response_model=PluginListResponse)
def list_plugins(registry: RuntimeRegistry = Depends(get_runtime_registry)) -> PluginListResponse:
    return {"plugins": registry.list_plugins()}


@router.post("", response_model=PluginMutationResponse)
def register_plugin(
    manifest: PluginManifest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginMutationResponse:
    plugin = registry.register_plugin(manifest)
    return {"plugin": plugin}


@router.get("/{plugin_id}/timeline", response_model=PluginTimelineResponse)
def get_plugin_timeline(
    plugin_id: str,
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginTimelineResponse:
    try:
        return registry.plugin_timeline(plugin_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{plugin_id}/settings", response_model=PluginSettingsResponse)
def get_plugin_settings(
    plugin_id: str,
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginSettingsResponse:
    try:
        return registry.get_plugin_settings(plugin_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{plugin_id}/dashboard", response_model=PluginDashboardResponse)
def get_plugin_dashboard(
    plugin_id: str,
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginDashboardResponse:
    try:
        return registry.plugin_dashboard(plugin_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{plugin_id}/workspace", response_model=PluginWorkspaceResponse)
def get_plugin_workspace(
    plugin_id: str,
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginWorkspaceResponse:
    try:
        return registry.plugin_workspace(plugin_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{plugin_id}/chat", response_model=PluginChatResponse)
def send_plugin_chat_request(
    plugin_id: str,
    request: PluginChatRequest,
    authorization=Depends(require_permission("mission.create", "plugin_chat")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
    mission_service: MissionService = Depends(get_mission_service),
) -> PluginChatResponse:
    try:
        dashboard = registry.plugin_dashboard(plugin_id)
        if dashboard["status"] == "deleted":
            raise ValueError(f"Plugin {plugin_id} must be restored before chat execution.")
        mission = mission_service.create(
            MissionRequest(
                plugin_id=plugin_id,
                user_request=request.user_request,
                requested_by=request.requested_by,
            )
        )
        registry.record_plugin_chat_request(
            plugin_id=plugin_id,
            mission_id=mission.mission_id,
            requested_by=request.requested_by,
            user_request=request.user_request,
            evidence=request.evidence,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "chat": {
            "plugin_id": plugin_id,
            "chief_agent_role": dashboard["chief_agent_role"],
            "mission_id": mission.mission_id,
            "status": mission.status,
            "governance_gate": mission.governance_gate,
            "data_platform": mission.data_platform,
        },
        "mission": mission,
    }


@router.patch("/{plugin_id}/settings", response_model=PluginSettingsResponse)
def update_plugin_settings(
    plugin_id: str,
    request: PluginSettingsUpdateRequest,
    authorization=Depends(require_permission("plugin.register", "plugin_settings")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginSettingsResponse:
    try:
        return registry.update_plugin_settings(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/{plugin_id}/enable", response_model=PluginMutationResponse)
def enable_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginMutationResponse:
    try:
        plugin = registry.enable_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin}


@router.patch("/{plugin_id}", response_model=PluginMutationResponse)
def patch_plugin(
    plugin_id: str,
    request: PluginPatchRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginMutationResponse:
    try:
        plugin = registry.patch_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin}


@router.post("/{plugin_id}/validate", response_model=PluginValidationResponse)
def validate_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginValidationResponse:
    try:
        report = registry.validate_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"validation_report": report}


@router.post("/{plugin_id}/disable", response_model=PluginMutationResponse)
def disable_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginMutationResponse:
    try:
        plugin = registry.disable_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin}


@router.post("/{plugin_id}/delete", response_model=PluginMutationResponse)
def soft_delete_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginMutationResponse:
    try:
        plugin = registry.soft_delete_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin}


@router.post("/{plugin_id}/restore", response_model=PluginMutationResponse)
def restore_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginMutationResponse:
    try:
        plugin = registry.restore_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin}


@router.post("/{plugin_id}/impact-analysis", response_model=PluginImpactResponse)
def analyze_plugin_impact(
    plugin_id: str,
    request: PluginImpactRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginImpactResponse:
    try:
        report = registry.analyze_plugin_impact(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"impact_report": report}


@router.post("/{plugin_id}/approve-change", response_model=PluginApprovalResponse)
def approve_plugin_change(
    plugin_id: str,
    request: PluginApprovalRequest,
    authorization=Depends(require_permission("governance.assign_approval", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginApprovalResponse:
    try:
        report = registry.approve_plugin_change(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"approval_report": report}


@router.post("/{plugin_id}/rollback", response_model=PluginMutationResponse)
def rollback_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginMutationResponse:
    try:
        plugin = registry.rollback_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin}


@router.post("/{plugin_id}/export-dna", response_model=PluginDNAExportResponse)
def export_plugin_dna(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginDNAExportResponse:
    try:
        dna_package = registry.export_plugin_dna(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"dna_package": dna_package}


@router.post("/import-dna", response_model=PluginMutationResponse)
def import_plugin_dna(
    request: PluginDNAImportRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginMutationResponse:
    try:
        plugin = registry.import_plugin_dna(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin}
