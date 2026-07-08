from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.plugin_manifest import (
    PluginApprovalReport,
    PluginApprovalRequest,
    PluginDNAImportRequest,
    PluginDNAPackage,
    PluginImpactReport,
    PluginImpactRequest,
    PluginManifest,
    PluginPatchRequest,
    PluginSettingsUpdateRequest,
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

    def plugin_timeline(self, plugin_id: str) -> dict:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        audit_records = [
            record
            for record in self._audit_service.list()
            if record.target_type == "plugin" and record.target_id == plugin_id
        ]
        events = [
            event
            for event in self._event_bus.list_events()
            if event.payload.get("plugin_id") == plugin_id
            or event.payload.get("source_plugin_id") == plugin_id
        ]
        return {
            "plugin": plugin.model_dump(),
            "audit_records": [
                {
                    "audit_id": record.audit_id,
                    "actor_id": record.actor_id,
                    "action": record.action,
                    "decision": record.decision,
                    "evidence": record.evidence,
                    "created_at": record.created_at,
                }
                for record in audit_records
            ],
            "events": [
                {
                    "event_id": event.event_id,
                    "name": event.name,
                    "source": event.source,
                    "payload": event.payload,
                    "created_at": event.created_at,
                }
                for event in events
            ],
            "summary": {
                "audit_records": len(audit_records),
                "events": len(events),
                "rollback_points": len(plugin.rollback_stack),
                "status": plugin.status,
                "version": plugin.version,
            },
        }

    def get_plugin_settings(self, plugin_id: str) -> dict:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        return {
            "plugin_id": plugin.plugin_id,
            "settings_schema": plugin.settings_schema,
            "settings_values": plugin.settings_values,
            "status": plugin.status,
            "data_platform": "DB MARIAM",
        }

    def plugin_dashboard(self, plugin_id: str) -> dict:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        timeline = self.plugin_timeline(plugin_id)
        return {
            "plugin_id": plugin.plugin_id,
            "name": plugin.name,
            "version": plugin.version,
            "status": plugin.status,
            "dashboard_route": plugin.dashboard_route,
            "api_prefix": plugin.api_prefix,
            "data_boundary": plugin.data_boundary,
            "chief_agent_role": plugin.chief_agent_role,
            "swarm_roles": plugin.swarm_roles,
            "workflows": plugin.workflows,
            "permissions": plugin.permissions,
            "settings_values": plugin.settings_values,
            "lifecycle": {
                "validation_passed": bool(plugin.validation.get("passed")),
                "impact_ready": bool(plugin.impact_analysis.get("impact_id")),
                "approval_ready": bool(plugin.change_approval.get("approval_id")),
                "rollback_points": len(plugin.rollback_stack),
            },
            "activity": timeline["summary"],
            "data_platform": "DB MARIAM",
        }

    def plugin_workspace(self, plugin_id: str) -> dict:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        dashboard = self.plugin_dashboard(plugin_id)
        settings = self.get_plugin_settings(plugin_id)
        timeline = self.plugin_timeline(plugin_id)
        workspace_title = plugin.name if plugin.name.lower().endswith("workspace") else f"{plugin.name} Workspace"
        return {
            "plugin_id": plugin.plugin_id,
            "title": workspace_title,
            "status": plugin.status,
            "dashboard": dashboard,
            "settings": settings,
            "chief_agent": {
                "role": plugin.chief_agent_role,
                "entrypoint": f"{plugin.dashboard_route}/chat",
                "responsibilities": [
                    "Understand user requests inside the plugin boundary.",
                    "Route work to plugin swarm roles.",
                    "Keep artifacts behind governance and approval gates.",
                ],
            },
            "swarm": [
                {
                    "role": role,
                    "scope": f"{plugin.name} execution support",
                    "data_boundary": plugin.data_boundary,
                }
                for role in plugin.swarm_roles
            ],
            "workspace_actions": [
                {
                    "label": "Open Dashboard",
                    "api": f"GET /api/plugins/{plugin.plugin_id}/dashboard",
                    "result": "Shows status, lifecycle, activity, workflows, and DB MARIAM evidence.",
                },
                {
                    "label": "Update Settings",
                    "api": f"PATCH /api/plugins/{plugin.plugin_id}/settings",
                    "result": "Updates plugin-owned settings after governance evidence is recorded.",
                },
                {
                    "label": "Send Plugin Chat Request",
                    "api": f"POST /api/plugins/{plugin.plugin_id}/chat",
                    "result": "Creates a governed mission owned by the plugin Chief Agent.",
                },
                {
                    "label": "Review Timeline",
                    "api": f"GET /api/plugins/{plugin.plugin_id}/timeline",
                    "result": "Shows audit records and runtime events linked to the plugin.",
                },
            ],
            "data_boundary": {
                "platform": "DB MARIAM",
                "boundary": plugin.data_boundary,
                "shared_tables": ["identity", "permissions", "audit", "events", "registry"],
                "private_tables": [
                    f"{plugin.plugin_id}_settings",
                    f"{plugin.plugin_id}_workflows",
                    f"{plugin.plugin_id}_artifacts",
                ],
            },
            "activity": timeline["summary"],
            "data_platform": "DB MARIAM",
        }

    def record_plugin_chat_request(
        self,
        plugin_id: str,
        mission_id: str,
        requested_by: str,
        user_request: str,
        evidence: dict,
    ) -> None:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        if plugin.status == "deleted":
            raise ValueError(f"Plugin {plugin_id} must be restored before chat execution.")
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=requested_by,
                action="plugin.chat_request",
                target_type="plugin",
                target_id=plugin.plugin_id,
                decision="approved",
                evidence={
                    "mission_id": mission_id,
                    "user_request": user_request,
                    "chief_agent_role": plugin.chief_agent_role,
                    "governance_gate": "mission_approval_before_delivery",
                    **evidence,
                },
            )
        )
        self._event_bus.publish(
            "plugin.chat_request",
            "runtime-registry",
            {
                "plugin_id": plugin.plugin_id,
                "mission_id": mission_id,
                "requested_by": requested_by,
                "chief_agent_role": plugin.chief_agent_role,
            },
        )

    def update_plugin_settings(
        self,
        plugin_id: str,
        request: PluginSettingsUpdateRequest,
    ) -> dict:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        if plugin.status == "deleted":
            raise ValueError(f"Plugin {plugin_id} must be restored before settings update.")
        allowed_keys = set(plugin.settings_schema.get("properties", {}).keys())
        if allowed_keys:
            unknown_keys = sorted(set(request.settings.keys()) - allowed_keys)
            if unknown_keys:
                raise ValueError(f"Plugin settings include unknown keys: {', '.join(unknown_keys)}")
        settings_values = {**plugin.settings_values, **request.settings}
        saved = self._plugin_repository.update(plugin.model_copy(update={"settings_values": settings_values}))
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="plugin.settings_update",
                target_type="plugin",
                target_id=saved.plugin_id,
                decision="approved",
                evidence={
                    "name": saved.name,
                    "version": saved.version,
                    "reason": request.reason,
                    "updated_settings": sorted(request.settings.keys()),
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "plugin.settings_update",
            "runtime-registry",
            {
                "plugin_id": saved.plugin_id,
                "name": saved.name,
                "version": saved.version,
                "updated_settings": sorted(request.settings.keys()),
                "actor_id": request.actor_id,
            },
        )
        return self.get_plugin_settings(saved.plugin_id)

    def patch_plugin(self, plugin_id: str, request: PluginPatchRequest) -> PluginManifest:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        if plugin.status == "deleted":
            raise ValueError(f"Plugin {plugin_id} must be restored before patch.")
        updates = request.model_dump(
            exclude={"actor_id", "reason", "evidence"},
            exclude_none=True,
        )
        if not updates:
            raise ValueError("Plugin patch requires at least one update.")
        rollback_stack = [
            *plugin.rollback_stack,
            {
                "status": plugin.status,
                "validation": plugin.validation,
                "impact_analysis": plugin.impact_analysis,
                "change_approval": plugin.change_approval,
                "manifest": plugin.model_dump(
                    exclude={"rollback_stack", "validation", "impact_analysis", "change_approval"}
                ),
                "captured_at": datetime.now(UTC).isoformat(),
                "reason": request.reason,
            },
        ]
        patched = validate_manifest(
            plugin.model_copy(
                update={
                    **updates,
                    "validation": {},
                    "impact_analysis": {},
                    "change_approval": {},
                    "rollback_stack": rollback_stack,
                }
            )
        )
        saved = self._plugin_repository.update(patched)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="plugin.patch",
                target_type="plugin",
                target_id=saved.plugin_id,
                decision="approved",
                evidence={
                    "name": saved.name,
                    "version": saved.version,
                    "reason": request.reason,
                    "updated_fields": sorted(updates.keys()),
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "plugin.patch",
            "runtime-registry",
            {
                "plugin_id": saved.plugin_id,
                "name": saved.name,
                "version": saved.version,
                "status": saved.status,
                "updated_fields": sorted(updates.keys()),
                "actor_id": request.actor_id,
            },
        )
        return saved

    def export_plugin_dna(self, plugin_id: str, request: PluginStateChangeRequest) -> PluginDNAPackage:
        plugin = self._plugin_repository.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} was not found.")
        manifest = plugin.model_dump(
            exclude={"rollback_stack", "validation", "impact_analysis", "change_approval"}
        )
        exported_at = datetime.now(UTC)
        dna_package = PluginDNAPackage(
            dna_package_id=f"plugin-dna-{uuid4()}",
            source_plugin_id=plugin.plugin_id,
            name=plugin.name,
            version=plugin.version,
            exported_at=exported_at,
            payload={
                "schema": "mariam.plugin.dna.v1",
                "plugin": manifest,
                "export_policy": {
                    "requires_governance_review_before_import": True,
                    "requires_validation_before_enable": True,
                    "source_data_platform": "DB MARIAM",
                },
            },
        )
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="plugin.export_dna",
                target_type="plugin",
                target_id=plugin.plugin_id,
                decision="approved",
                evidence={
                    "name": plugin.name,
                    "version": plugin.version,
                    "reason": request.reason,
                    "dna_package_id": dna_package.dna_package_id,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "plugin.export_dna",
            "runtime-registry",
            {
                "plugin_id": plugin.plugin_id,
                "dna_package_id": dna_package.dna_package_id,
                "name": plugin.name,
                "version": plugin.version,
                "actor_id": request.actor_id,
            },
        )
        return dna_package

    def import_plugin_dna(self, request: PluginDNAImportRequest) -> PluginManifest:
        dna_package = request.dna_package
        payload = dna_package.payload
        if payload.get("schema") != "mariam.plugin.dna.v1":
            raise ValueError("Unsupported plugin DNA schema.")
        source_plugin = payload["plugin"]
        imported_id = f"{source_plugin['plugin_id']}-imported"
        candidate = PluginManifest.model_validate(
            {
                **source_plugin,
                "plugin_id": imported_id,
                "name": f"{source_plugin['name']} Imported",
                "status": "disabled",
                "validation": {},
                "impact_analysis": {},
                "change_approval": {},
                "rollback_stack": [],
            }
        )
        saved = self._plugin_repository.save(validate_manifest(candidate))
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="plugin.import_dna",
                target_type="plugin",
                target_id=saved.plugin_id,
                decision="approved",
                evidence={
                    "name": saved.name,
                    "version": saved.version,
                    "reason": request.reason,
                    "source_dna_package_id": dna_package.dna_package_id,
                    "source_plugin_id": dna_package.source_plugin_id,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "plugin.import_dna",
            "runtime-registry",
            {
                "plugin_id": saved.plugin_id,
                "source_dna_package_id": dna_package.dna_package_id,
                "source_plugin_id": dna_package.source_plugin_id,
                "name": saved.name,
                "version": saved.version,
                "status": saved.status,
                "actor_id": request.actor_id,
            },
        )
        return saved

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
        manifest_snapshot = rollback_point.get("manifest", {})
        restored = plugin.model_copy(
            update={
                **manifest_snapshot,
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
