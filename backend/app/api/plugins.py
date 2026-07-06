from fastapi import APIRouter, Depends, HTTPException

from app.core.plugin_manifest import PluginManifest, PluginStateChangeRequest
from app.dependencies import get_runtime_registry
from app.services.runtime import RuntimeRegistry

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("")
def list_plugins(registry: RuntimeRegistry = Depends(get_runtime_registry)) -> dict:
    return {"plugins": [plugin.model_dump() for plugin in registry.list_plugins()]}


@router.post("")
def register_plugin(
    manifest: PluginManifest,
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    plugin = registry.register_plugin(manifest)
    return {"plugin": plugin.model_dump()}


@router.post("/{plugin_id}/enable")
def enable_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        plugin = registry.enable_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"plugin": plugin.model_dump()}


@router.post("/{plugin_id}/validate")
def validate_plugin(
    plugin_id: str,
    request: PluginStateChangeRequest,
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
    registry: RuntimeRegistry = Depends(get_runtime_registry),
) -> dict:
    try:
        plugin = registry.disable_plugin(plugin_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"plugin": plugin.model_dump()}
