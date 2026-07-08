from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.plugin_manifest import (
    PluginApprovalRequest,
    PluginChatRequest,
    PluginDNAImportRequest,
    PluginImpactRequest,
    PluginManifest,
    PluginPatchRequest,
    PluginSettingsUpdateRequest,
    PluginStateChangeRequest,
)
from app.core.missions import MissionRequest
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


@router.get("")
def list_plugins(registry: RuntimeRegistry = Depends(get_runtime_registry)) -> dict:
    return {"plugins": [plugin.model_dump() for plugin in registry.list_plugins()]}


@router.post("")
def register_plugin(
    manifest: PluginManifest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    plugin = registry.register_plugin(manifest)
    return {"plugin": plugin.model_dump()}


@router.get("/{plugin_id}/timeline", response_model=PluginTimelineResponse)
def get_plugin_timeline(
    plugin_id: str,
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> PluginTimelineResponse:
    try:
        return registry.plugin_timeline(plugin_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{plugin_id}/settings")
def get_plugin_settings(
    plugin_id: str,
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        return registry.get_plugin_settings(plugin_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{plugin_id}/dashboard")
def get_plugin_dashboard(
    plugin_id: str,
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
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


@router.post("/{plugin_id}/chat")
def send_plugin_chat_request(
    plugin_id: str,
    request: PluginChatRequest,
    authorization=Depends(require_permission("mission.create", "plugin_chat")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
    mission_service: MissionService = Depends(get_mission_service),
) -> dict:
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
        "mission": mission.model_dump(mode="json"),
    }


@router.patch("/{plugin_id}/settings")
def update_plugin_settings(
    plugin_id: str,
    request: PluginSettingsUpdateRequest,
    authorization=Depends(require_permission("plugin.register", "plugin_settings")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        return registry.update_plugin_settings(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/{plugin_id}/enable")
def enable_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        plugin = registry.enable_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin.model_dump()}


@router.patch("/{plugin_id}")
def patch_plugin(
    plugin_id: str,
    request: PluginPatchRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        plugin = registry.patch_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin.model_dump()}


@router.post("/{plugin_id}/validate")
def validate_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        report = registry.validate_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"validation_report": report.model_dump()}


@router.post("/{plugin_id}/disable")
def disable_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        plugin = registry.disable_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin.model_dump()}


@router.post("/{plugin_id}/delete")
def soft_delete_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        plugin = registry.soft_delete_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin.model_dump()}


@router.post("/{plugin_id}/restore")
def restore_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        plugin = registry.restore_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin.model_dump()}


@router.post("/{plugin_id}/impact-analysis")
def analyze_plugin_impact(
    plugin_id: str,
    request: PluginImpactRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        report = registry.analyze_plugin_impact(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"impact_report": report.model_dump()}


@router.post("/{plugin_id}/approve-change")
def approve_plugin_change(
    plugin_id: str,
    request: PluginApprovalRequest,
    authorization=Depends(require_permission("governance.assign_approval", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        report = registry.approve_plugin_change(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"approval_report": report.model_dump()}


@router.post("/{plugin_id}/rollback")
def rollback_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        plugin = registry.rollback_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin.model_dump()}


@router.post("/{plugin_id}/export-dna")
def export_plugin_dna(
    plugin_id: str,
    request: PluginStateChangeRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        dna_package = registry.export_plugin_dna(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"dna_package": dna_package.model_dump(mode="json")}


@router.post("/import-dna")
def import_plugin_dna(
    request: PluginDNAImportRequest,
    authorization=Depends(require_permission("plugin.register", "plugin")),
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        plugin = registry.import_plugin_dna(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin.model_dump()}
