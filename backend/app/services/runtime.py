from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.plugin_manifest import (
    PluginApprovalReport,
    PluginApprovalRequest,
    PluginImpactReport,
    PluginImpactRequest,
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
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        self._require_plugin_change_gates(plugin, "disable")
        return self._change_plugin_status(plugin_id, "disabled", "disable", request)

    def soft_delete_plugin(self, plugin_id: str, request: PluginStateChangeRequest) -> PluginManifest:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        self._require_plugin_change_gates(plugin, "delete")
        return self._change_plugin_status(plugin_id, "deleted", "soft_delete", request)

    def restore_plugin(self, plugin_id: str, request: PluginStateChangeRequest) -> PluginManifest:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        if plugin.status != "deleted":
            raise ValueError(f"Plugin {plugin_id} is not deleted.")
        return self._change_plugin_status(plugin_id, "disabled", "restore", request)

    def analyze_plugin_impact(
        self,
        plugin_id: str,
        request: PluginImpactRequest,
    ) -> PluginImpactReport:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        dependencies = [
            *plugin.provider_dependencies,
            *plugin.connector_dependencies,
            *plugin.runtime_dependencies,
        ]
        risk_level = "high" if plugin.status == "enabled" and (plugin.workflows or dependencies) else "medium"
        report = PluginImpactReport(
            impact_id=f"plugin-impact-{uuid4()}",
            plugin_id=plugin.plugin_id,
            intended_action=request.intended_action,
            risk_level=risk_level,
            affected_workflows=plugin.workflows,
            affected_permissions=plugin.permissions,
            affected_dependencies=dependencies,
            governance_notes=[
                "Plugin-managed Business Unit changes can affect dashboard, API routes, workflows, and private data.",
                "Disable must preserve plugin data as read-only until governance confirms rollback or replacement.",
            ],
            analyzed_at=datetime.now(UTC),
        )
        self._plugin_repository.update(
            plugin.model_copy(
                update={
                    "impact_analysis": {
                        "impact_id": report.impact_id,
                        "intended_action": report.intended_action,
                        "risk_level": report.risk_level,
                        "analyzed_at": report.analyzed_at.isoformat(),
                    }
                }
            )
        )
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="plugin.impact_analysis",
                target_type="plugin",
                target_id=plugin.plugin_id,
                decision="approved",
                evidence={
                    "name": plugin.name,
                    "version": plugin.version,
                    "reason": request.reason,
                    "impact_id": report.impact_id,
                    "intended_action": report.intended_action,
                    "risk_level": report.risk_level,
                    "affected_workflows": report.affected_workflows,
                    "affected_dependencies": report.affected_dependencies,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "plugin.impact_analysis",
            "runtime-registry",
            {
                "plugin_id": plugin.plugin_id,
                "impact_id": report.impact_id,
                "intended_action": report.intended_action,
                "risk_level": report.risk_level,
                "actor_id": request.actor_id,
            },
        )
        return report

    def approve_plugin_change(
        self,
        plugin_id: str,
        request: PluginApprovalRequest,
    ) -> PluginApprovalReport:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        impact_analysis = plugin.impact_analysis
        if impact_analysis.get("intended_action") != request.intended_action:
            raise ValueError(
                f"Plugin {plugin_id} requires impact analysis before approval for {request.intended_action}."
            )
        report = PluginApprovalReport(
            approval_id=f"plugin-approval-{uuid4()}",
            plugin_id=plugin.plugin_id,
            intended_action=request.intended_action,
            impact_id=impact_analysis["impact_id"],
            approved_at=datetime.now(UTC),
        )
        self._plugin_repository.update(
            plugin.model_copy(
                update={
                    "change_approval": {
                        "approval_id": report.approval_id,
                        "intended_action": report.intended_action,
                        "impact_id": report.impact_id,
                        "approved_at": report.approved_at.isoformat(),
                    }
                }
            )
        )
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="plugin.approve_change",
                target_type="plugin",
                target_id=plugin.plugin_id,
                decision="approved",
                evidence={
                    "name": plugin.name,
                    "version": plugin.version,
                    "reason": request.reason,
                    "approval_id": report.approval_id,
                    "impact_id": report.impact_id,
                    "intended_action": report.intended_action,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "plugin.approve_change",
            "runtime-registry",
            {
                "plugin_id": plugin.plugin_id,
                "approval_id": report.approval_id,
                "impact_id": report.impact_id,
                "intended_action": report.intended_action,
                "actor_id": request.actor_id,
            },
        )
        return report

    def rollback_plugin(self, plugin_id: str, request: PluginStateChangeRequest) -> PluginManifest:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        rollback_stack = list(plugin.rollback_stack)
        if not rollback_stack:
            raise ValueError(f"Plugin {plugin_id} has no rollback point.")
        rollback_point = rollback_stack.pop()
        restored = plugin.model_copy(
            update={
                "status": rollback_point["status"],
                "validation": rollback_point["validation"],
                "impact_analysis": rollback_point["impact_analysis"],
                "change_approval": rollback_point["change_approval"],
                "rollback_stack": rollback_stack,
            }
        )
        saved = self._plugin_repository.update(restored)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="plugin.rollback",
                target_type="plugin",
                target_id=saved.plugin_id,
                decision="approved",
                evidence={
                    "name": saved.name,
                    "version": saved.version,
                    "reason": request.reason,
                    "rollback_point": rollback_point,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "plugin.rollback",
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
        rollback_stack = [
            *plugin.rollback_stack,
            {
                "status": plugin.status,
                "validation": plugin.validation,
                "impact_analysis": plugin.impact_analysis,
                "change_approval": plugin.change_approval,
                "captured_at": datetime.now(UTC).isoformat(),
                "reason": request.reason,
            },
        ]
        saved = self._plugin_repository.update(
            plugin.model_copy(update={"status": status, "rollback_stack": rollback_stack})
        )
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

    def _require_plugin_change_gates(self, plugin: PluginManifest, intended_action: str) -> None:
        if plugin.impact_analysis.get("intended_action") != intended_action:
            raise ValueError(
                f"Plugin {plugin.plugin_id} requires impact analysis before {intended_action}."
            )
        if plugin.impact_analysis.get("risk_level") == "high":
            approval = plugin.change_approval
            if (
                approval.get("intended_action") != intended_action
                or approval.get("impact_id") != plugin.impact_analysis.get("impact_id")
            ):
                raise ValueError(
                    f"Plugin {plugin.plugin_id} requires approval before high-risk {intended_action}."
                )

    def health(self) -> list[RuntimeStatus]:
        return [
            RuntimeStatus("api", "healthy", datetime.now(UTC)),
            RuntimeStatus("event_bus", "healthy", datetime.now(UTC)),
            RuntimeStatus("plugin_registry", "healthy", datetime.now(UTC)),
        ]
