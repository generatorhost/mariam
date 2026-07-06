from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.plugin_manifest import (
    PluginManifest,
    PluginStateChangeRequest,
    PluginValidationReport,
    validate_manifest,
)
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

    def validate_plugin(
        self,
        plugin_id: str,
        request: PluginStateChangeRequest,
    ) -> PluginValidationReport:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        checks = [
            {
                "name": "dashboard_route_declared",
                "passed": plugin.dashboard_route.startswith("/plugins/"),
                "details": plugin.dashboard_route,
            },
            {
                "name": "api_prefix_declared",
                "passed": plugin.api_prefix.startswith("/api/plugins/"),
                "details": plugin.api_prefix,
            },
            {
                "name": "permissions_declared",
                "passed": bool(plugin.permissions),
                "details": plugin.permissions,
            },
            {
                "name": "tests_declared",
                "passed": bool(plugin.tests),
                "details": plugin.tests,
            },
            {
                "name": "chief_agent_declared",
                "passed": bool(plugin.chief_agent_role.strip()),
                "details": plugin.chief_agent_role,
            },
            {
                "name": "data_boundary_declared",
                "passed": bool(plugin.data_boundary.strip()),
                "details": plugin.data_boundary,
            },
        ]
        passed = all(check["passed"] for check in checks)
        report = PluginValidationReport(
            validation_id=f"plugin-validation-{uuid4()}",
            plugin_id=plugin.plugin_id,
            status=plugin.status,
            passed=passed,
            checks=checks,
            validated_at=datetime.now(UTC),
        )
        self._plugin_repository.update(
            plugin.model_copy(
                update={
                    "validation": {
                        "validation_id": report.validation_id,
                        "passed": report.passed,
                        "validated_at": report.validated_at.isoformat(),
                        "checked_status": plugin.status,
                    }
                }
            )
        )
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="plugin.validate",
                target_type="plugin",
                target_id=plugin.plugin_id,
                decision="approved" if passed else "rejected",
                evidence={
                    "name": plugin.name,
                    "version": plugin.version,
                    "reason": request.reason,
                    "validation_id": report.validation_id,
                    "checks": checks,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "plugin.validate",
            "runtime-registry",
            {
                "plugin_id": plugin.plugin_id,
                "validation_id": report.validation_id,
                "passed": passed,
                "actor_id": request.actor_id,
            },
        )
        return report

    def enable_plugin(self, plugin_id: str, request: PluginStateChangeRequest) -> PluginManifest:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        if not plugin.validation.get("passed"):
            raise ValueError(f"Plugin {plugin_id} must pass validation before enable.")
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
