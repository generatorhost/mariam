from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.events import InMemoryEventBus
from app.core.plugin_manifest import PluginManifest, validate_manifest
from app.repositories.plugins import PluginRepository


@dataclass
class RuntimeStatus:
    name: str
    status: str
    checked_at: datetime


class RuntimeRegistry:
    def __init__(self, event_bus: InMemoryEventBus, plugin_repository: PluginRepository) -> None:
        self._event_bus = event_bus
        self._plugin_repository = plugin_repository

    def register_plugin(self, manifest: PluginManifest) -> PluginManifest:
        plugin = validate_manifest(manifest)
        saved = self._plugin_repository.save(plugin)
        self._event_bus.publish(
            "plugin.registered",
            "runtime-registry",
            {"plugin_id": plugin.plugin_id, "version": plugin.version},
        )
        return saved

    def list_plugins(self) -> list[PluginManifest]:
        return self._plugin_repository.list()

    def health(self) -> list[RuntimeStatus]:
        return [
            RuntimeStatus("api", "healthy", datetime.now(UTC)),
            RuntimeStatus("event_bus", "healthy", datetime.now(UTC)),
            RuntimeStatus("plugin_registry", "healthy", datetime.now(UTC)),
        ]
