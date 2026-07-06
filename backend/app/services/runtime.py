from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.plugin_manifest import PluginManifest, PluginStateChangeRequest, validate_manifest
from app.repositories.plugins import PluginRepository
from app.services.audit import AuditService


@dataclass
class RuntimeStatus:
    name: str
    status: str
    checked_at: datetime


class RuntimeRegistry:
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        plugin_repository: PluginRepository,
        audit_service: AuditService,
    ) -> None:
        self._event_bus = event_bus
        self._plugin_repository = plugin_repository
        self._audit_service = audit_service

    def register_plugin(self, manifest: PluginManifest) -> PluginManifest:
        plugin = validate_manifest(manifest)
        saved = self._plugin_repository.save(plugin)
        self._event_bus.publish(
            "plugin.registered",
            "runtime-registry",
            {"plugin_id": plugin.plugin_id, "version": plugin.version, "status": saved.status},
        )
        self._audit_service.record(
            AuditRecordRequest(
                actor_id="runtime-registry",
                action="plugin.register",
                target_type="plugin",
                target_id=saved.plugin_id,
                decision="approved",
                evidence={"name": saved.name, "version": saved.version, "status": saved.status},
            )
        )
        return saved

    def list_plugins(self) -> list[PluginManifest]:
        return self._plugin_repository.list()

    def enable_plugin(self, plugin_id: str, request: PluginStateChangeRequest) -> PluginManifest:
        return self._change_plugin_status(plugin_id, "enabled", "enable", request)

    def disable_plugin(self, plugin_id: str, request: PluginStateChangeRequest) -> PluginManifest:
        return self._change_plugin_status(plugin_id, "disabled", "disable", request)

    def _change_plugin_status(
        self,
        plugin_id: str,
        status: str,
        action_verb: str,
        request: PluginStateChangeRequest,
    ) -> PluginManifest:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        saved = self._plugin_repository.update(plugin.model_copy(update={"status": status}))
        action = f"plugin.{action_verb}"
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action=action,
                target_type="plugin",
                target_id=saved.plugin_id,
                decision="approved",
                evidence={
                    "name": saved.name,
                    "version": saved.version,
                    "status": saved.status,
                    "reason": request.reason,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            action,
            "runtime-registry",
            {
                "plugin_id": saved.plugin_id,
                "name": saved.name,
                "version": saved.version,
                "status": saved.status,
                "actor_id": request.actor_id,
            },
        )
        return saved

    def health(self) -> list[RuntimeStatus]:
        return [
            RuntimeStatus("api", "healthy", datetime.now(UTC)),
            RuntimeStatus("event_bus", "healthy", datetime.now(UTC)),
            RuntimeStatus("plugin_registry", "healthy", datetime.now(UTC)),
        ]
