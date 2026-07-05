from fastapi import APIRouter, Depends

from app.core.plugin_manifest import PluginManifest
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

