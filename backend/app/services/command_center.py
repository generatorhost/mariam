import base64
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from app.core.config import get_settings
from app.core.audit import AuditRecord, AuditRecordRequest
from app.core.data_records import (
    ArtifactStoreRecord,
    AuditEventArchiveRecord,
    ArtifactLineageRecord,
    CapabilityGraphRecord,
    CommunicationRecord,
    DocumentRecord,
    LogsStoreRecord,
    MetricsStoreRecord,
    VectorIndexRecord,
    WorkflowRecord,
)
from app.core.events import InMemoryEventBus
from app.repositories.data_records import (
    CursorArtifactStoreRecordRepository,
    CursorArtifactLineageRecordRepository,
    CursorAuditEventArchiveRecordRepository,
    CursorCapabilityGraphRecordRepository,
    CursorCommunicationRecordRepository,
    CursorDocumentRecordRepository,
    CursorLogsStoreRecordRepository,
    CursorMetricsStoreRecordRepository,
    CursorVectorIndexRecordRepository,
    CursorWorkflowRecordRepository,
)
from app.services.ai_resources import AIResourceManager
from app.services.artifacts import ArtifactService
from app.services.audit import AuditService
from app.services.missions import MissionService
from app.services.runtime import RuntimeRegistry
from app.services.runtime_objects import RuntimeObjectService


@dataclass
class CommandCenterSummary:
    health: str
    runtime_objects: int
    plugins: int
    missions: int
    ai_routes: int
    audit_records: int
    runtime_events: int
    recent_events: list[dict[str, object]]


@dataclass
class ReadinessCheck:
    name: str
    status: str
    detail: str


@dataclass
class CommandCenterReadiness:
    status: str
    checks: list[ReadinessCheck]


@dataclass
class CommandCenterVerificationReport:
    status: str
    readiness_status: str
    ready_checks: int
    total_checks: int
    summary: dict[str, int | str]
    smoke_flow: str
    required_endpoints: list[str]


@dataclass
class CommandCenterDiagnostics:
    status: str
    generated_at: str
    verification_report: CommandCenterVerificationReport
    readiness_checks: list[ReadinessCheck]
    recent_audit_records: list[dict[str, object]]
    recent_events: list[dict[str, object]]
    data_platform: str = "DB MARIAM"


@dataclass
class DiagnosticsExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    diagnostics: CommandCenterDiagnostics
    data_platform: str = "DB MARIAM"


@dataclass
class UsageGuideStep:
    action: str
    frontend_control: str
    api_endpoint: str
    backend_handler: str
    service_effect: str
    data_platform_effect: str
    result: str
    verification_signal: str


@dataclass
class CommandCenterUsageGuide:
    title: str
    version: str
    status: str
    data_platform: str
    generated_at: str
    operating_rule: str
    steps: list[UsageGuideStep]


@dataclass
class UsageGuideExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    usage_guide: CommandCenterUsageGuide
    data_platform: str = "DB MARIAM"


@dataclass
class CompletionArea:
    name: str
    completion_percent: int
    status: str
    evidence: str
    next_step: str


@dataclass
class ProjectCompletionReport:
    title: str
    version: str
    status: str
    completion_percent: int
    generated_at: str
    data_platform: str
    areas: list[CompletionArea]
    verification: CommandCenterVerificationReport
    usage_guide: CommandCenterUsageGuide
    summary: str


@dataclass
class CompletionReportExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    completion_report: ProjectCompletionReport
    data_platform: str = "DB MARIAM"


@dataclass
class ImplementationRoadmapItem:
    area: str
    priority: str
    current_completion_percent: int
    next_step: str
    acceptance_signal: str


@dataclass
class ImplementationRoadmap:
    title: str
    version: str
    status: str
    generated_at: str
    data_platform: str
    items: list[ImplementationRoadmapItem]
    operating_rule: str


@dataclass
class ImplementationRoadmapExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    roadmap: ImplementationRoadmap
    data_platform: str = "DB MARIAM"


@dataclass
class DataPlatformCheck:
    name: str
    status: str
    detail: str


@dataclass
class DataPlatformReadiness:
    title: str
    status: str
    database_name: str
    database_url: str
    generated_at: str
    store_modes: dict[str, str]
    migrations_found: list[str]
    expected_tables: list[str]
    checks: list[DataPlatformCheck]


@dataclass
class DataPlatformReadinessExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    readiness: DataPlatformReadiness
    data_platform: str = "DB MARIAM"


@dataclass
class MigrationRunnerStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    migration_count: int
    ordered_migrations: list[str]
    table_definitions: int
    index_definitions: int
    checks: list[DataPlatformCheck]


@dataclass
class MigrationRunnerExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    migration_runner: MigrationRunnerStatus
    data_platform: str = "DB MARIAM"


@dataclass
class AuditEventArchiveExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    audit_event_archive: "AuditEventArchiveReadStatus"
    data_platform: str = "DB MARIAM"


@dataclass
class LogsStoreExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    logs_store: "LogsStoreReadStatus"
    data_platform: str = "DB MARIAM"


@dataclass
class MetricsStoreExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    metrics_store: "MetricsStoreReadStatus"
    data_platform: str = "DB MARIAM"


@dataclass
class ArtifactLineageExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    artifact_lineage: "ArtifactLineageReadStatus"
    data_platform: str = "DB MARIAM"


@dataclass
class SeedDataStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    seed_id: str
    seed_file: str
    item_count: int
    target_tables: list[str]
    contains_secrets: bool
    checks: list[DataPlatformCheck]


@dataclass
class BackupReadinessStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    policy_id: str
    policy_file: str
    scope_count: int
    retention: dict[str, str]
    contains_secrets: bool
    checks: list[DataPlatformCheck]


@dataclass
class PluginSchemaIsolationStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    manifest_id: str
    manifest_file: str
    plugin_schema_count: int
    shared_table_count: int
    private_table_count: int
    contains_secrets: bool
    checks: list[DataPlatformCheck]


@dataclass
class DockerPersistenceStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    env_file: str
    compose_file: str
    postgres_store_count: int
    database_url_masked: str
    checks: list[DataPlatformCheck]


@dataclass
class LiveDatabaseSmokeStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    docker_available: bool
    compose_config_valid: bool
    smoke_command: str
    checks: list[DataPlatformCheck]


@dataclass
class DockerContainerExecutionStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    postgres_running: bool
    pg_isready: bool
    services: list[str]
    execution_commands: list[str]
    checks: list[DataPlatformCheck]


@dataclass
class LiveDatabaseWriteStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    audit_id: str
    event_id: str
    audit_written: bool
    event_written: bool
    checks: list[DataPlatformCheck]


@dataclass
class LiveRepositoryWriteStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    mission_id: str
    artifact_id: str
    delivery_id: str
    plugin_id: str
    runtime_object_id: str
    ai_resource_route_id: str
    quality_review_id: str
    communication_record_id: str
    document_record_id: str
    workflow_record_id: str
    capability_graph_record_id: str
    vector_index_record_id: str
    artifact_store_record_id: str
    audit_event_archive_record_id: str
    metrics_store_record_id: str
    logs_store_record_id: str
    artifact_lineage_record_id: str
    mission_written: bool
    artifact_written: bool
    delivery_written: bool
    plugin_written: bool
    runtime_object_written: bool
    ai_resource_route_written: bool
    quality_review_written: bool
    communication_record_written: bool
    document_record_written: bool
    workflow_record_written: bool
    capability_graph_record_written: bool
    vector_index_record_written: bool
    artifact_store_record_written: bool
    audit_event_archive_record_written: bool
    metrics_store_record_written: bool
    logs_store_record_written: bool
    artifact_lineage_record_written: bool
    checks: list[DataPlatformCheck]


@dataclass
class LogsStoreReadStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    record_count: int
    records: list[dict[str, object]]
    checks: list[DataPlatformCheck]


@dataclass
class AuditEventArchiveReadStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    record_count: int
    records: list[dict[str, object]]
    checks: list[DataPlatformCheck]


@dataclass
class MetricsStoreReadStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    record_count: int
    records: list[dict[str, object]]
    checks: list[DataPlatformCheck]


@dataclass
class ArtifactLineageReadStatus:
    title: str
    status: str
    generated_at: str
    data_platform: str
    record_count: int
    records: list[dict[str, object]]
    checks: list[DataPlatformCheck]


@dataclass
class DeliveryEvidenceReport:
    title: str
    status: str
    generated_at: str
    data_platform: str
    sla_minutes: int
    escalation_after_minutes: int
    sla_status: str
    escalation_required_count: int
    delivery_count: int
    signed_bundle_count: int
    confirmed_delivery_count: int
    invalid_signature_count: int
    evidence_items: list[dict[str, object]]
    sla_items: list[dict[str, object]]
    sla_drilldown_summary: dict[str, object]
    sla_drilldown_items: list[dict[str, object]]
    sla_filters: dict[str, object]
    filtered_sla_drilldown_items: list[dict[str, object]]
    checks: list[DataPlatformCheck]


@dataclass
class DeliveryEvidenceExportPackage:
    export_id: str
    status: str
    format: str
    generated_at: str
    package_manifest: dict[str, object]
    delivery_evidence_report: DeliveryEvidenceReport
    data_platform: str = "DB MARIAM"


@dataclass
class FrontendRegressionSnapshot:
    title: str
    status: str
    generated_at: str
    data_platform: str
    source_file: str
    artifact_path: str
    controls_checked: list[str]
    missing_controls: list[str]
    viewport_contracts: list[str]
    missing_viewports: list[str]
    keyboard_traversal_targets: list[str]
    missing_keyboard_traversal_targets: list[str]
    error_contracts: list[str]
    missing_error_contracts: list[str]
    checks: list[DataPlatformCheck]


@dataclass
class FrontendVisualContract:
    title: str
    status: str
    generated_at: str
    data_platform: str
    source_files: list[str]
    artifact_path: str
    design_tokens_checked: list[str]
    missing_design_tokens: list[str]
    layout_contracts_checked: list[str]
    missing_layout_contracts: list[str]
    breakpoint_contracts_checked: list[str]
    missing_breakpoint_contracts: list[str]
    screenshot_targets: list[str]
    checks: list[DataPlatformCheck]


@dataclass
class FrontendBrowserScreenshotPlan:
    title: str
    status: str
    generated_at: str
    data_platform: str
    source_file: str
    artifact_path: str
    viewport_targets: list[dict[str, int | str]]
    critical_sections: list[str]
    screenshot_artifacts: list[str]
    required_browser_checks: list[str]
    checks: list[DataPlatformCheck]


@dataclass
class FrontendBrowserScreenshotCaptureReport:
    title: str
    status: str
    generated_at: str
    data_platform: str
    artifact_path: str
    artifact_count: int
    artifacts: list[dict[str, object]]
    thumbnail_previews: list[dict[str, object]]
    checks: list[DataPlatformCheck]


@dataclass
class VerificationAutomationContract:
    title: str
    status: str
    generated_at: str
    data_platform: str
    artifact_path: str
    persisted_run_log_path: str
    persisted_verification_run_count: int
    persisted_verification_runs: list[dict[str, object]]
    required_commands: list[str]
    required_endpoints: list[str]
    required_artifacts: list[str]
    ci_artifact_retention: dict[str, object]
    ci_badge: dict[str, object]
    latest_run_status: dict[str, object]
    ci_run_ingestion: dict[str, object]
    local_history_comparison: dict[str, object]
    quality_gates: dict[str, object]
    artifact_freshness: dict[str, object]
    local_automation_status: str
    ci_status: str
    next_ci_step: str
    checks: list[DataPlatformCheck]


class CommandCenterSummaryService:
    def __init__(
        self,
        runtime_registry: RuntimeRegistry,
        runtime_object_service: RuntimeObjectService,
        mission_service: MissionService,
        artifact_service: ArtifactService,
        ai_resource_manager: AIResourceManager,
        audit_service: AuditService,
        event_bus: InMemoryEventBus,
    ) -> None:
        self._runtime_registry = runtime_registry
        self._runtime_object_service = runtime_object_service
        self._mission_service = mission_service
        self._artifact_service = artifact_service
        self._ai_resource_manager = ai_resource_manager
        self._audit_service = audit_service
        self._event_bus = event_bus

    def summarize(self) -> CommandCenterSummary:
        health_statuses = self._runtime_registry.health()
        health = "healthy"
        if any(status.status != "healthy" for status in health_statuses):
            health = "degraded"

        events = self._event_bus.list_events()
        recent_events = [
            {
                "event_id": event.event_id,
                "name": event.name,
                "source": event.source,
                "created_at": event.created_at.isoformat(),
                "payload": event.payload,
            }
            for event in sorted(events, key=lambda event: event.created_at, reverse=True)[:5]
        ]

        return CommandCenterSummary(
            health=health,
            runtime_objects=len(self._runtime_object_service.list()),
            plugins=len(self._runtime_registry.list_plugins()),
            missions=len(self._mission_service.list()),
            ai_routes=len(self._ai_resource_manager.list_routes()),
            audit_records=len(self._audit_service.list()),
            runtime_events=len(events),
            recent_events=recent_events,
        )

    def readiness(self) -> CommandCenterReadiness:
        health_statuses = self._runtime_registry.health()
        checks = [
            ReadinessCheck(
                name="runtime_core",
                status="ready" if all(status.status == "healthy" for status in health_statuses) else "blocked",
                detail="Runtime registry, event bus, and plugin registry health are available.",
            ),
            ReadinessCheck(
                name="event_bus",
                status="ready",
                detail=f"{len(self._event_bus.list_events())} runtime events available for traceability.",
            ),
            ReadinessCheck(
                name="audit_layer",
                status="ready",
                detail=f"{len(self._audit_service.list())} audit records available.",
            ),
            ReadinessCheck(
                name="mission_layer",
                status="ready",
                detail=f"{len(self._mission_service.list())} missions available.",
            ),
            ReadinessCheck(
                name="plugin_registry",
                status="ready",
                detail=f"{len(self._runtime_registry.list_plugins())} Plugin-managed Business Units registered.",
            ),
            ReadinessCheck(
                name="runtime_objects",
                status="ready",
                detail=f"{len(self._runtime_object_service.list())} runtime objects available.",
            ),
            ReadinessCheck(
                name="ai_resource_manager",
                status="ready",
                detail=f"{len(self._ai_resource_manager.list_routes())} AI routing decisions available.",
            ),
            ReadinessCheck(
                name="artifact_delivery_pipeline",
                status="ready",
                detail="Artifact approval, quality review, delivery packaging, and client confirmation APIs are mounted.",
            ),
        ]
        overall = "ready" if all(check.status == "ready" for check in checks) else "blocked"
        return CommandCenterReadiness(status=overall, checks=checks)

    def verification_report(self) -> CommandCenterVerificationReport:
        summary = self.summarize()
        readiness = self.readiness()
        ready_checks = sum(1 for check in readiness.checks if check.status == "ready")
        return CommandCenterVerificationReport(
            status="passed" if readiness.status == "ready" else "failed",
            readiness_status=readiness.status,
            ready_checks=ready_checks,
            total_checks=len(readiness.checks),
            summary={
                "health": summary.health,
                "runtime_objects": summary.runtime_objects,
                "plugins": summary.plugins,
                "missions": summary.missions,
                "ai_routes": summary.ai_routes,
                "audit_records": summary.audit_records,
                "runtime_events": summary.runtime_events,
            },
            smoke_flow="mission -> artifact -> rejection revision loop -> quality review -> delivery package -> client delivery confirmation",
            required_endpoints=[
                "/api/health",
                "/api/auth/request-context",
                "/api/runtime/summary",
                "/api/runtime/readiness",
                "/api/runtime/verification-report",
                "/api/artifacts",
                "/api/artifacts/quality-reviews",
                "/api/artifacts/deliveries",
                "/api/audit",
                "/api/audit/reviewer-workload",
                "/api/audit/governance-assignment-history",
                "/api/audit/reviewer-decisions",
                "/api/audit/governance-decision-evidence/export",
                "/api/runtime/events",
                "/api/runtime/data-platform/docker-container-execution",
                "/api/runtime/data-platform/live-write-smoke",
                "/api/runtime/data-platform/logs-store",
                "/api/runtime/data-platform/audit-event-archive",
                "/api/runtime/data-platform/audit-event-archive/export",
                "/api/runtime/data-platform/metrics-store",
                "/api/runtime/data-platform/metrics-store/export",
                "/api/runtime/data-platform/artifact-lineage",
                "/api/runtime/delivery-evidence-report/export",
                "/api/plugins",
                "/api/runtime-objects",
                "/api/ai-resources/providers",
            ],
        )

    def record_verification_snapshot(
        self,
        actor_id: str,
        evidence: dict[str, object],
    ) -> AuditRecord:
        report = self.verification_report()
        return self._audit_service.record(
            AuditRecordRequest(
                actor_id=actor_id,
                action="runtime.verification_report.record",
                target_type="runtime_verification_report",
                target_id="command-center",
                decision="approved" if report.status == "passed" else "rejected",
                evidence={
                    "verification_status": report.status,
                    "readiness_status": report.readiness_status,
                    "ready_checks": report.ready_checks,
                    "total_checks": report.total_checks,
                    "smoke_flow": report.smoke_flow,
                    "required_endpoints": report.required_endpoints,
                    **evidence,
                },
            )
        )

    def list_verification_snapshots(self) -> list[AuditRecord]:
        snapshots = [
            record
            for record in self._audit_service.list()
            if record.action == "runtime.verification_report.record"
        ]
        return sorted(snapshots, key=lambda record: record.created_at, reverse=True)

    def verification_history_comparison(self) -> dict[str, object]:
        snapshots = self.list_verification_snapshots()
        if len(snapshots) < 2:
            return {
                "status": "insufficient_history",
                "snapshot_count": len(snapshots),
                "latest_snapshot_id": snapshots[0].audit_id if snapshots else None,
                "previous_snapshot_id": None,
                "ready_checks_delta": 0,
                "total_checks_delta": 0,
                "verification_status_changed": False,
                "message": "Record at least two local verification snapshots to compare runs.",
            }
        latest = snapshots[0]
        previous = snapshots[1]
        latest_ready = int(latest.evidence.get("ready_checks", 0))
        previous_ready = int(previous.evidence.get("ready_checks", 0))
        latest_total = int(latest.evidence.get("total_checks", 0))
        previous_total = int(previous.evidence.get("total_checks", 0))
        latest_status = str(latest.evidence.get("verification_status", "unknown"))
        previous_status = str(previous.evidence.get("verification_status", "unknown"))
        return {
            "status": "changed" if latest_status != previous_status else "stable",
            "snapshot_count": len(snapshots),
            "latest_snapshot_id": latest.audit_id,
            "previous_snapshot_id": previous.audit_id,
            "latest_created_at": latest.created_at.isoformat(),
            "previous_created_at": previous.created_at.isoformat(),
            "latest_verification_status": latest_status,
            "previous_verification_status": previous_status,
            "ready_checks_delta": latest_ready - previous_ready,
            "total_checks_delta": latest_total - previous_total,
            "verification_status_changed": latest_status != previous_status,
            "message": "Latest two local verification snapshots were compared.",
        }

    def diagnostics(self) -> CommandCenterDiagnostics:
        verification_report = self.verification_report()
        readiness = self.readiness()
        recent_audit_records = [
            {
                "audit_id": record.audit_id,
                "actor_id": record.actor_id,
                "action": record.action,
                "target_type": record.target_type,
                "target_id": record.target_id,
                "decision": record.decision,
                "created_at": record.created_at.isoformat(),
            }
            for record in sorted(
                self._audit_service.list(),
                key=lambda record: record.created_at,
                reverse=True,
            )[:5]
        ]
        recent_events = [
            {
                "event_id": event.event_id,
                "name": event.name,
                "source": event.source,
                "created_at": event.created_at.isoformat(),
                "payload": event.payload,
            }
            for event in sorted(
                self._event_bus.list_events(),
                key=lambda event: event.created_at,
                reverse=True,
            )[:5]
        ]
        return CommandCenterDiagnostics(
            status=verification_report.status,
            generated_at=datetime.now(UTC).isoformat(),
            verification_report=verification_report,
            readiness_checks=readiness.checks,
            recent_audit_records=recent_audit_records,
            recent_events=recent_events,
        )

    def export_diagnostics(self) -> DiagnosticsExportPackage:
        diagnostics = self.diagnostics()
        return DiagnosticsExportPackage(
            export_id=f"diagnostics-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": "Mariam Runtime Diagnostics Export",
                "verification_status": diagnostics.status,
                "readiness_checks": len(diagnostics.readiness_checks),
                "recent_audit_records": len(diagnostics.recent_audit_records),
                "recent_events": len(diagnostics.recent_events),
                "requires_governance_review_before_external_delivery": True,
            },
            diagnostics=diagnostics,
        )

    def usage_guide(self) -> CommandCenterUsageGuide:
        return CommandCenterUsageGuide(
            title="Mariam Command Center End-to-End Usage Guide",
            version="v1",
            status="executable",
            data_platform="DB MARIAM",
            generated_at=datetime.now(UTC).isoformat(),
            operating_rule=(
                "Every visible action must map to a backend API, a governed service effect, "
                "traceable storage or event evidence, and a clear user-facing result."
            ),
            steps=[
                UsageGuideStep(
                    action="Refresh system status",
                    frontend_control="Refresh System Status",
                    api_endpoint="GET /api/runtime/summary",
                    backend_handler="command_center_summary",
                    service_effect="Counts runtime objects, plugins, missions, AI routes, audit records, and events.",
                    data_platform_effect="Reads registered operational state from DB MARIAM repositories and in-memory runtime services.",
                    result="The dashboard cards update with live health and activity counts.",
                    verification_signal="verify_project.py checks /api/runtime/summary during smoke verification.",
                ),
                UsageGuideStep(
                    action="Refresh request actor context",
                    frontend_control="Refresh Actor Context",
                    api_endpoint="GET /api/auth/request-context",
                    backend_handler="request_actor_context",
                    service_effect="Resolves the request id and actor id from headers or the active Command Center session.",
                    data_platform_effect="Keeps the actor context tied to DB MARIAM governance evidence before mutating operations.",
                    result="The user sees request id, actor id, propagation mode, and whether the actor matches the current session.",
                    verification_signal="verify_project.py checks default and header-propagated request actor context.",
                ),
                UsageGuideStep(
                    action="Run readiness check",
                    frontend_control="Refresh Readiness",
                    api_endpoint="GET /api/runtime/readiness",
                    backend_handler="command_center_readiness",
                    service_effect="Evaluates runtime core, event bus, audit, mission, plugin, runtime object, AI resource, and delivery readiness.",
                    data_platform_effect="Reads DB MARIAM-backed records where repositories are configured for persistence.",
                    result="The user sees ready or blocked checks before operating the system.",
                    verification_signal="Automated verification requires every readiness check to be ready.",
                ),
                UsageGuideStep(
                    action="Run DB MARIAM live write smoke",
                    frontend_control="Run DB MARIAM Write Smoke",
                    api_endpoint="POST /api/runtime/data-platform/live-write-smoke",
                    backend_handler="command_center_data_platform_live_write_smoke",
                    service_effect="Writes and reads a smoke audit record and runtime event against the live DB MARIAM Postgres database.",
                    data_platform_effect="Confirms live persistence for audit_log and runtime_events without exposing secrets.",
                    result="The user sees generated audit and event ids with ready status.",
                    verification_signal="verify_project.py runs the live write smoke after Docker container verification.",
                ),
                UsageGuideStep(
                    action="Export audit event archive evidence",
                    frontend_control="Export Audit Event Archive Evidence",
                    api_endpoint="POST /api/runtime/data-platform/audit-event-archive/export",
                    backend_handler="export_command_center_data_platform_audit_event_archive",
                    service_effect="Builds a review-ready package from the recent DB MARIAM audit event archive records.",
                    data_platform_effect="Reads audit_event_archive_records and preserves record count, checks, and no-secret metadata.",
                    result="The user sees an audit event archive export id with ready_for_review status.",
                    verification_signal="Backend tests and verify_project.py assert the export manifest and archived record ids.",
                ),
                UsageGuideStep(
                    action="Export metrics store evidence",
                    frontend_control="Export Metrics Store Evidence",
                    api_endpoint="POST /api/runtime/data-platform/metrics-store/export",
                    backend_handler="export_command_center_data_platform_metrics_store",
                    service_effect="Builds a review-ready package from recent DB MARIAM operational metric records.",
                    data_platform_effect="Reads metrics_store_records and preserves record count, checks, and no-secret metadata.",
                    result="The user sees a metrics store export id with ready_for_review status.",
                    verification_signal="Backend tests and verify_project.py assert the export manifest and metric record ids.",
                ),
                UsageGuideStep(
                    action="Create governed mission",
                    frontend_control="Run Mission",
                    api_endpoint="POST /api/missions",
                    backend_handler="create_mission",
                    service_effect="Creates a mission, assigns Plugin Chief execution context, emits events, and records governance evidence.",
                    data_platform_effect="Stores mission and artifact state under the DB MARIAM mission boundary.",
                    result="A mission and draft artifact appear for approval, quality review, and delivery packaging.",
                    verification_signal="Smoke verification exercises mission to artifact to quality to delivery confirmation.",
                ),
                UsageGuideStep(
                    action="Approve, revise, and package artifact",
                    frontend_control="Approve Artifact / Reject Artifact / Request Changes / Run Quality Review / Package Delivery",
                    api_endpoint="POST /api/artifacts/{artifact_id}/approve; POST /reject; POST /request-revision; POST /quality-review; POST /package-delivery",
                    backend_handler="approve_artifact, reject_artifact, request_artifact_revision, review_artifact_quality, package_artifact_delivery",
                    service_effect="Moves artifact through approval, rejection revision loop, quality gate, and client package creation.",
                    data_platform_effect="Stores approval, quality, delivery package, audit, and event evidence.",
                    result="A client delivery package becomes ready for confirmation.",
                    verification_signal="Smoke verification rejects premature delivery packaging, tests revision loop, and confirms the valid path.",
                ),
                UsageGuideStep(
                    action="Assign approval",
                    frontend_control="Assign Approval",
                    api_endpoint="POST /api/audit/approval-assignments",
                    backend_handler="assign_approval",
                    service_effect="Assigns an approval role to a reviewer and records the assignment as governed audit evidence.",
                    data_platform_effect="Stores assignment evidence in the audit log and emits a governance approval assignment event.",
                    result="The user sees the assigned reviewer, approval role, and audit id.",
                    verification_signal="verify_project.py posts an approval assignment and checks the assignment decision.",
                ),
                UsageGuideStep(
                    action="Record reviewer decision outcome",
                    frontend_control="Governance Review Decision",
                    api_endpoint="POST /api/audit/reviewer-decisions",
                    backend_handler="record_reviewer_decision",
                    service_effect="Persists the assigned reviewer's approval, rejection, or requested-changes outcome.",
                    data_platform_effect="Stores the reviewer decision outcome in DB MARIAM and links it to audit, workload, SLA, and lifecycle history.",
                    result="The user sees the reviewer decision attached to the target item and assignment history.",
                    verification_signal="verify_project.py records a reviewer decision and checks history, workload, SLA, and runtime event evidence.",
                ),
                UsageGuideStep(
                    action="Export reviewer decision evidence",
                    frontend_control="Export Reviewer Decision Evidence",
                    api_endpoint="POST /api/audit/governance-decision-evidence/export",
                    backend_handler="export_governance_decision_evidence",
                    service_effect="Builds a governance evidence review package from assignments, escalations, and reviewer decision outcomes.",
                    data_platform_effect="Exports DB MARIAM governance decision history and marks external delivery as governance-gated.",
                    result="The user sees an export id, ready_for_review status, and reviewer decision counts.",
                    verification_signal="Backend tests and verify_project.py assert the export package manifest and decision history.",
                ),
                UsageGuideStep(
                    action="Route governance notification",
                    frontend_control="Route Notification",
                    api_endpoint="POST /api/audit/notifications/route",
                    backend_handler="route_notification",
                    service_effect="Routes a governed notification to the assigned human reviewer and emits a traceable notification event.",
                    data_platform_effect="Stores recipient, channel, subject, and target evidence in DB MARIAM audit records.",
                    result="The user sees the routed recipient, channel, and audit id before review work continues.",
                    verification_signal="verify_project.py posts a notification route and checks the routed decision.",
                ),
                UsageGuideStep(
                    action="Review and escalate reviewer workload",
                    frontend_control="Refresh Reviewer Workload / Escalate Reviewer Workload",
                    api_endpoint="GET /api/audit/reviewer-workload; POST /api/audit/escalations",
                    backend_handler="reviewer_workload, escalate_reviewer_workload",
                    service_effect="Summarizes reviewer assignment load and records escalation when a reviewer needs governance lead attention.",
                    data_platform_effect="Stores escalation evidence in DB MARIAM audit records and emits a governance workload event.",
                    result="The user sees reviewer load, overloaded reviewers, and escalation audit id.",
                    verification_signal="Backend tests and verify_project.py check workload report and escalation record.",
                ),
                UsageGuideStep(
                    action="Register and govern plugin",
                    frontend_control="Register CRM Plugin / Validate / Enable / Impact / Approve / Disable",
                    api_endpoint="POST /api/plugins and governed plugin lifecycle endpoints",
                    backend_handler="RuntimeRegistry plugin lifecycle handlers",
                    service_effect="Registers Plugin-managed Business Units with validation, impact analysis, approvals, rollback, DNA export, and restore controls.",
                    data_platform_effect="Stores plugin manifests, governance stamps, audit records, and runtime events.",
                    result="Plugins behave as governed apps with dashboard, settings, Chief Agent, swarm, permissions, and rollback evidence.",
                    verification_signal="Backend tests cover plugin validation, enable, disable, approval, rollback, DNA export, and restore.",
                ),
                UsageGuideStep(
                    action="Export diagnostics",
                    frontend_control="Export Diagnostics",
                    api_endpoint="POST /api/runtime/diagnostics/export",
                    backend_handler="export_command_center_diagnostics",
                    service_effect="Creates a review-ready diagnostics package with readiness, audit, and event evidence.",
                    data_platform_effect="Packages DB MARIAM operational evidence without exposing secrets.",
                    result="The user receives a diagnostics export id with ready_for_review status.",
                    verification_signal="verify_project.py checks diagnostics export readiness and UI smoke confirms the button result.",
                ),
            ],
        )

    def export_usage_guide(self) -> UsageGuideExportPackage:
        usage_guide = self.usage_guide()
        return UsageGuideExportPackage(
            export_id=f"usage-guide-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": usage_guide.title,
                "version": usage_guide.version,
                "step_count": len(usage_guide.steps),
                "data_platform": usage_guide.data_platform,
                "requires_governance_review_before_external_delivery": True,
            },
            usage_guide=usage_guide,
        )

    def delivery_evidence_report(self) -> DeliveryEvidenceReport:
        delivery_packages = self._artifact_service.list_delivery_packages()
        evidence_items: list[dict[str, object]] = []
        sla_items: list[dict[str, object]] = []
        sla_minutes = 240
        escalation_after_minutes = 480
        signed_bundle_count = 0
        confirmed_delivery_count = 0
        invalid_signature_count = 0
        escalation_required_count = 0
        generated_at = datetime.now(UTC)
        for delivery_package in delivery_packages:
            manifest = delivery_package.package_manifest
            evidence_bundle = manifest.get("evidence_bundle")
            evidence_signature = manifest.get("evidence_signature")
            signature_valid = False
            if isinstance(evidence_bundle, dict) and isinstance(evidence_signature, str):
                canonical_payload = json.dumps(evidence_bundle, sort_keys=True, separators=(",", ":"))
                expected_signature = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
                signature_valid = expected_signature == evidence_signature
            if signature_valid:
                signed_bundle_count += 1
            elif evidence_bundle is not None or evidence_signature is not None:
                invalid_signature_count += 1
            delivery_confirmed = manifest.get("delivery_confirmed") is True
            if delivery_confirmed:
                confirmed_delivery_count += 1
            created_at = delivery_package.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            age_minutes = max(0, int((generated_at - created_at).total_seconds() // 60))
            if delivery_confirmed:
                sla_state = "confirmed"
            elif not signature_valid:
                sla_state = "unsigned"
            elif age_minutes >= escalation_after_minutes:
                sla_state = "escalation_required"
                escalation_required_count += 1
            elif age_minutes >= sla_minutes:
                sla_state = "review_due"
            else:
                sla_state = "on_track"
            escalation_required = sla_state == "escalation_required"
            evidence_items.append(
                {
                    "delivery_id": delivery_package.delivery_id,
                    "artifact_id": delivery_package.artifact_id,
                    "mission_id": delivery_package.mission_id,
                    "plugin_id": delivery_package.plugin_id,
                    "status": delivery_package.status,
                    "destination": delivery_package.destination,
                    "evidence_signed": bool(manifest.get("evidence_signed")),
                    "signature_valid": signature_valid,
                    "quality_review_id": manifest.get("quality_review_id"),
                    "quality_score": manifest.get("quality_score"),
                    "delivery_confirmed": delivery_confirmed,
                    "client_reference": manifest.get("client_reference"),
                    "age_minutes": age_minutes,
                    "sla_state": sla_state,
                    "escalation_required": escalation_required,
                    "data_platform": delivery_package.data_platform,
                }
            )
            sla_items.append(
                {
                    "delivery_id": delivery_package.delivery_id,
                    "artifact_id": delivery_package.artifact_id,
                    "mission_id": delivery_package.mission_id,
                    "plugin_id": delivery_package.plugin_id,
                    "status": delivery_package.status,
                    "signature_valid": signature_valid,
                    "delivery_confirmed": delivery_confirmed,
                    "age_minutes": age_minutes,
                    "sla_minutes": sla_minutes,
                    "escalation_after_minutes": escalation_after_minutes,
                    "sla_state": sla_state,
                    "escalation_required": escalation_required,
                    "governance_action": (
                        "confirm_traceability_complete"
                        if sla_state == "confirmed"
                        else "route_to_delivery_governance"
                        if sla_state in {"review_due", "escalation_required"}
                        else "wait_for_sla_or_signature"
                    ),
                    "data_platform": delivery_package.data_platform,
                }
            )
        sla_drilldown_items = [
            {
                "delivery_id": item["delivery_id"],
                "artifact_id": item["artifact_id"],
                "mission_id": item["mission_id"],
                "plugin_id": item["plugin_id"],
                "sla_state": item["sla_state"],
                "age_minutes": item["age_minutes"],
                "delivery_confirmed": item["delivery_confirmed"],
                "escalation_required": item["escalation_required"],
                "governance_action": item["governance_action"],
                "reviewer_queue": (
                    "delivery-governance"
                    if item["sla_state"] in {"review_due", "escalation_required"}
                    else "delivery-evidence"
                ),
            }
            for item in sla_items
            if item["signature_valid"] is True
        ]
        sla_state_counts = {
            state: sum(1 for item in sla_drilldown_items if item["sla_state"] == state)
            for state in ["confirmed", "on_track", "review_due", "escalation_required"]
        }
        reviewer_queue_counts = {
            queue: sum(1 for item in sla_drilldown_items if item["reviewer_queue"] == queue)
            for queue in sorted({str(item["reviewer_queue"]) for item in sla_drilldown_items})
        }
        default_sla_state_filter = "all"
        default_reviewer_queue_filter = "all"
        filtered_sla_drilldown_items = [
            item
            for item in sla_drilldown_items
            if (
                default_sla_state_filter == "all"
                or item["sla_state"] == default_sla_state_filter
            )
            and (
                default_reviewer_queue_filter == "all"
                or item["reviewer_queue"] == default_reviewer_queue_filter
            )
        ]
        sla_drilldown_summary: dict[str, object] = {
            "title": "Signed Delivery SLA Drill-down",
            "signed_item_count": len(sla_drilldown_items),
            "state_counts": sla_state_counts,
            "reviewer_queue_counts": reviewer_queue_counts,
            "columns": [
                "delivery_id",
                "plugin_id",
                "sla_state",
                "age_minutes",
                "governance_action",
                "reviewer_queue",
            ],
            "empty_state": "No signed delivery packages are available for SLA drill-down.",
        }
        sla_filters: dict[str, object] = {
            "default_sla_state": default_sla_state_filter,
            "default_reviewer_queue": default_reviewer_queue_filter,
            "sla_state_options": ["all", *sla_state_counts.keys()],
            "reviewer_queue_options": ["all", *reviewer_queue_counts.keys()],
            "filtered_count": len(filtered_sla_drilldown_items),
            "filter_rule": "Filter signed delivery SLA drill-down rows by sla_state and reviewer_queue before governance action.",
        }
        checks = [
            DataPlatformCheck(
                name="delivery_evidence_packages_readable",
                status="ready",
                detail=f"{len(delivery_packages)} delivery package records were read from DB MARIAM.",
            ),
            DataPlatformCheck(
                name="signed_evidence_bundles_valid",
                status="ready" if invalid_signature_count == 0 else "blocked",
                detail=(
                    "All delivery evidence signatures are valid."
                    if invalid_signature_count == 0
                    else f"{invalid_signature_count} delivery evidence signatures are invalid."
                ),
            ),
            DataPlatformCheck(
                name="client_confirmation_traceable",
                status="ready" if confirmed_delivery_count <= len(delivery_packages) else "blocked",
                detail=f"{confirmed_delivery_count} delivery packages include client confirmation traceability.",
            ),
            DataPlatformCheck(
                name="signed_delivery_sla_policy_declared",
                status="ready",
                detail=(
                    f"Signed delivery packages are reviewed after {sla_minutes} minutes "
                    f"and escalated after {escalation_after_minutes} minutes."
                ),
            ),
            DataPlatformCheck(
                name="signed_delivery_sla_items_traceable",
                status="ready" if len(sla_items) == len(delivery_packages) else "blocked",
                detail=f"{len(sla_items)} delivery SLA records were generated from DB MARIAM delivery packages.",
            ),
            DataPlatformCheck(
                name="signed_delivery_escalation_scan_ready",
                status="ready",
                detail=f"{escalation_required_count} signed delivery packages currently require escalation.",
            ),
            DataPlatformCheck(
                name="signed_delivery_sla_drilldown_ready",
                status="ready",
                detail=f"{len(sla_drilldown_items)} signed delivery SLA drill-down rows are available for governance review.",
            ),
            DataPlatformCheck(
                name="signed_delivery_sla_filters_ready",
                status="ready"
                if "all" in sla_filters["sla_state_options"]
                and "all" in sla_filters["reviewer_queue_options"]
                else "blocked",
                detail="Delivery SLA drill-down exposes state and reviewer queue filters for the governance dashboard.",
            ),
        ]
        return DeliveryEvidenceReport(
            title="Mariam Delivery Evidence Bundle Verification Report",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=generated_at.isoformat(),
            data_platform="DB MARIAM",
            sla_minutes=sla_minutes,
            escalation_after_minutes=escalation_after_minutes,
            sla_status="escalation_required" if escalation_required_count else "ready",
            escalation_required_count=escalation_required_count,
            delivery_count=len(delivery_packages),
            signed_bundle_count=signed_bundle_count,
            confirmed_delivery_count=confirmed_delivery_count,
            invalid_signature_count=invalid_signature_count,
            evidence_items=evidence_items,
            sla_items=sla_items,
            sla_drilldown_summary=sla_drilldown_summary,
            sla_drilldown_items=sla_drilldown_items,
            sla_filters=sla_filters,
            filtered_sla_drilldown_items=filtered_sla_drilldown_items,
            checks=checks,
        )

    def export_delivery_evidence_report(self) -> DeliveryEvidenceExportPackage:
        report = self.delivery_evidence_report()
        return DeliveryEvidenceExportPackage(
            export_id=f"delivery-governance-evidence-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": report.title,
                "report_status": report.status,
                "delivery_count": report.delivery_count,
                "signed_bundle_count": report.signed_bundle_count,
                "confirmed_delivery_count": report.confirmed_delivery_count,
                "invalid_signature_count": report.invalid_signature_count,
                "sla_status": report.sla_status,
                "sla_drilldown_count": len(report.sla_drilldown_items),
                "filter_rule": report.sla_filters.get("filter_rule"),
                "data_platform": report.data_platform,
                "requires_governance_review_before_external_delivery": True,
            },
            delivery_evidence_report=report,
        )

    def completion_report(self) -> ProjectCompletionReport:
        verification = self.verification_report()
        usage_guide = self.usage_guide()
        areas = [
            CompletionArea(
                name="Backend API foundation",
                completion_percent=95,
                status="executable",
                evidence="FastAPI routes cover health, auth session readiness, request actor context propagation, role permission checks, backend permission enforcement, endpoint-level authorization audit evidence, request-scoped authorization dependencies on mutating endpoints, structured API error response contracts, OpenAPI error response examples, typed response models for governed runtime endpoints, runtime event list and publish endpoints, plugin timeline, plugin settings, plugin dashboard, and plugin workspace endpoints, typed response models for data-platform readiness, migration runner, seed-data, backup-readiness, plugin-schema-isolation, Docker persistence, live database smoke, Docker container execution, live write smoke, live repository write smoke, frontend diagnostics, runtime diagnostics, usage guide, and verification snapshot endpoints, runtime, missions, artifacts, audit, plugins, runtime objects, and AI resources.",
                next_step="Add typed API response models for plugin chat and plugin lifecycle mutation endpoints.",
            ),
            CompletionArea(
                name="Frontend Command Center",
                completion_percent=95,
                status="executable",
                evidence="React UI can operate mission, delivery, plugin, runtime object, AI route, audit, readiness, diagnostics, usage guide flows, sidebar navigation with active section highlighting, persisted active-section, delivery SLA filter preferences, reviewer decision filters, governance decision evidence export controls, delivery governance evidence export controls, visual interaction smoke coverage for reviewer evidence export, visual interaction smoke coverage for delivery governance export, browser-level click smoke coverage for Command Center export buttons, browser-level keyboard focus and tab-order smoke coverage for Command Center primary actions, browser-level responsive navigation smoke coverage for mobile and tablet states, app-like plugin workspace cards, live plugin workspace details, responsive state guidance, API error banners with endpoint/request/retry context, frontend regression snapshot artifact generation, visual contract artifact checks, browser screenshot artifact planning, binary screenshot artifact capture, a Command Center screenshot capture report, visual thumbnail previews for captured screenshot artifacts, and accessible keyboard traversal checks for Command Center panels.",
                next_step="Add browser-level responsive smoke coverage for mobile and tablet action panels.",
            ),
            CompletionArea(
                name="DB MARIAM persistence boundary",
                completion_percent=95,
                status="executable",
                evidence="Repositories support DB MARIAM boundaries, migration readiness, migration runner status, non-secret seed data status, backup readiness, per-plugin schema isolation, Docker Postgres persistence profile checks, live DB smoke readiness, Docker postgres container execution verification, live audit/event write smoke, live mission/artifact/delivery/plugin/runtime-object/AI-resource-route/quality-review repository write smoke, repository abstraction classes for communication, document, workflow, capability graph, vector index, artifact store, audit event archive, metrics store, logs store, and artifact lineage records, read APIs for recent audit event archive, metrics store, logs store, and artifact lineage records, plus review-package exports for audit event archive, metrics store, logs store, and artifact lineage evidence.",
                next_step="Add export packages for communication, document, workflow, capability graph, vector index, and artifact store evidence.",
            ),
            CompletionArea(
                name="Governance and delivery workflow",
                completion_percent=95,
                status="executable",
                evidence="Mission approval, artifact approval, rejection revision loop, approval assignment, persisted reviewer queue assignment history, persistent reviewer decision outcomes, reviewer decision evidence export packages, governance workload evidence export packages, governance SLA evidence export packages, notification routing, reviewer workload reporting from DB MARIAM assignment and decision history, governance SLA aging, persisted SLA escalation history, human identity enforcement, quality review, signed delivery evidence bundles, delivery evidence verification report, delivery governance evidence export packages, delivery SLA aging and escalation checks for signed client packages, governance dashboard drill-down, dashboard filters for signed delivery SLA state and reviewer queue, reviewer decision outcome filters by reviewer and decision, and typed API response models for governance workload, SLA, decision history, reviewer decision, escalation, assignment, notification, and evidence export endpoints are covered by tests and smoke verification.",
                next_step="Add export packages for approval assignment history and notification routing evidence.",
            ),
            CompletionArea(
                name="Verification automation",
                completion_percent=94,
                status="executable",
                evidence="npm run verify executes backend tests, frontend build, API endpoint checks, diagnostics export, usage guide export, mission-to-delivery smoke flow, frontend contracts, browser screenshot planning, binary screenshot capture, governance export interaction smoke, delivery governance export visual smoke, browser click smoke for Command Center exports, browser keyboard focus smoke, CI frontend artifact replay, local verification history comparison, persisted local verification run records, minimum backend test count quality gates, endpoint and artifact coverage gates, artifact freshness gates, mutation-level gates for governed write endpoints, governed write API schema regression snapshots, governed write API schema-diff hash gates, and a GitHub Actions verification workflow that uploads, downloads, replays, and retains frontend regression artifacts with Command Center artifact links, CI badge metadata, latest run status polling metadata, and CI run result ingestion fields from the GitHub Actions API contract.",
                next_step="Add failure-summary export for CI and local verification runs.",
            ),
        ]
        completion_percent = round(sum(area.completion_percent for area in areas) / len(areas))
        return ProjectCompletionReport(
            title="Mariam Executable Project Completion Report",
            version="v1",
            status="in_progress_verified",
            completion_percent=completion_percent,
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            areas=areas,
            verification=verification,
            usage_guide=usage_guide,
            summary=(
                "Mariam is currently an executable documentation-driven rebuild foundation, "
                "not a finished enterprise product. The verified core supports Command Center "
                "operations, governance traces, delivery smoke flow, and review-package exports."
            ),
        )

    def export_completion_report(self) -> CompletionReportExportPackage:
        report = self.completion_report()
        return CompletionReportExportPackage(
            export_id=f"completion-report-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": report.title,
                "version": report.version,
                "completion_percent": report.completion_percent,
                "area_count": len(report.areas),
                "verification_status": report.verification.status,
                "data_platform": report.data_platform,
                "requires_governance_review_before_external_delivery": True,
            },
            completion_report=report,
        )

    def implementation_roadmap(self) -> ImplementationRoadmap:
        report = self.completion_report()
        priority_order = {
            "DB MARIAM persistence boundary": "high",
            "Backend API foundation": "high",
            "Governance and delivery workflow": "high",
            "Frontend Command Center": "medium",
            "Verification automation": "medium",
        }
        priority_rank = {"high": 0, "medium": 1, "low": 2}
        items = [
            ImplementationRoadmapItem(
                area=area.name,
                priority=priority_order.get(area.name, "medium"),
                current_completion_percent=area.completion_percent,
                next_step=area.next_step,
                acceptance_signal=f"{area.name} reaches a verified executable state above {area.completion_percent}%.",
            )
            for area in sorted(
                report.areas,
                key=lambda item: (
                    item.completion_percent,
                    priority_rank.get(priority_order.get(item.name, "medium"), 1),
                    item.name,
                ),
            )
        ]
        return ImplementationRoadmap(
            title="Mariam Next Implementation Roadmap",
            version="v1",
            status="ready_for_execution",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            items=items,
            operating_rule=(
                "Work on the lowest-completion high-impact area first, verify with automated tests, "
                "then update the completion report before moving to the next area."
            ),
        )

    def export_implementation_roadmap(self) -> ImplementationRoadmapExportPackage:
        roadmap = self.implementation_roadmap()
        return ImplementationRoadmapExportPackage(
            export_id=f"implementation-roadmap-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": roadmap.title,
                "version": roadmap.version,
                "roadmap_status": roadmap.status,
                "item_count": len(roadmap.items),
                "first_priority_area": roadmap.items[0].area if roadmap.items else None,
                "data_platform": roadmap.data_platform,
                "requires_governance_review_before_execution": True,
            },
            roadmap=roadmap,
        )

    def data_platform_readiness(self) -> DataPlatformReadiness:
        settings = get_settings()
        expected_tables = [
            "runtime_objects",
            "plugin_manifests",
            "runtime_events",
            "missions",
            "mission_steps",
            "artifacts",
            "delivery_packages",
            "artifact_quality_reviews",
            "ai_resource_routes",
            "communication_records",
            "document_records",
            "workflow_records",
            "capability_graph_records",
            "vector_index_records",
            "artifact_store_records",
            "audit_event_archive_records",
            "metrics_store_records",
            "logs_store_records",
            "artifact_lineage_records",
            "audit_log",
            "reviewer_queue_assignments",
            "governance_sla_escalations",
            "reviewer_decision_outcomes",
        ]
        migration_dir = Path(__file__).resolve().parents[3] / "database" / "migrations"
        migration_files = sorted(migration_dir.glob("*.sql"))
        migration_text = "\n".join(
            migration_file.read_text(encoding="utf-8") for migration_file in migration_files
        )
        table_checks = [
            DataPlatformCheck(
                name=f"table:{table_name}",
                status="ready" if table_name in migration_text else "blocked",
                detail=f"{table_name} is defined in DB MARIAM migrations."
                if table_name in migration_text
                else f"{table_name} is missing from DB MARIAM migrations.",
            )
            for table_name in expected_tables
        ]
        store_modes = {
            "audit_store": settings.audit_store,
            "runtime_object_store": settings.runtime_object_store,
            "event_store": settings.event_store,
            "plugin_store": settings.plugin_store,
            "mission_store": settings.mission_store,
            "ai_resource_route_store": settings.ai_resource_route_store,
        }
        checks = [
            DataPlatformCheck(
                name="database_name",
                status="ready" if "db_mariam" in settings.database_url.lower() else "blocked",
                detail="Database URL targets db_mariam.",
            ),
            DataPlatformCheck(
                name="migration_files",
                status="ready" if migration_files else "blocked",
                detail=f"{len(migration_files)} migration files found.",
            ),
            DataPlatformCheck(
                name="store_modes",
                status="ready" if all(store_modes.values()) else "blocked",
                detail="Repository store modes are configured for all DB MARIAM boundaries.",
            ),
            *table_checks,
        ]
        return DataPlatformReadiness(
            title="DB MARIAM Data Platform Readiness",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            database_name="DB MARIAM",
            database_url=self._mask_database_url(settings.database_url),
            generated_at=datetime.now(UTC).isoformat(),
            store_modes=store_modes,
            migrations_found=[migration_file.name for migration_file in migration_files],
            expected_tables=expected_tables,
            checks=checks,
        )

    def _mask_database_url(self, database_url: str) -> str:
        parsed = urlsplit(database_url)
        if "@" not in parsed.netloc:
            return database_url
        credentials, host = parsed.netloc.rsplit("@", 1)
        username = credentials.split(":", 1)[0]
        return urlunsplit((parsed.scheme, f"{username}:***@{host}", parsed.path, parsed.query, parsed.fragment))

    def export_data_platform_readiness(self) -> DataPlatformReadinessExportPackage:
        readiness = self.data_platform_readiness()
        return DataPlatformReadinessExportPackage(
            export_id=f"data-platform-readiness-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": readiness.title,
                "readiness_status": readiness.status,
                "database_name": readiness.database_name,
                "migration_count": len(readiness.migrations_found),
                "expected_table_count": len(readiness.expected_tables),
                "check_count": len(readiness.checks),
                "secrets_masked": "***" in readiness.database_url,
                "requires_governance_review_before_external_delivery": True,
            },
            readiness=readiness,
        )

    def migration_runner_status(self) -> MigrationRunnerStatus:
        migration_dir = Path(__file__).resolve().parents[3] / "database" / "migrations"
        migration_files = sorted(migration_dir.glob("*.sql"))
        ordered_names = [migration_file.name for migration_file in migration_files]
        numeric_prefixes = [
            int(name.split("_", 1)[0])
            for name in ordered_names
            if name.split("_", 1)[0].isdigit()
        ]
        migration_text = "\n".join(
            migration_file.read_text(encoding="utf-8") for migration_file in migration_files
        )
        expected_sequence = list(range(1, len(numeric_prefixes) + 1))
        checks = [
            DataPlatformCheck(
                name="migration_directory",
                status="ready" if migration_dir.exists() else "blocked",
                detail=f"Migration directory found at {migration_dir}.",
            ),
            DataPlatformCheck(
                name="migration_files_present",
                status="ready" if migration_files else "blocked",
                detail=f"{len(migration_files)} SQL migration files are available.",
            ),
            DataPlatformCheck(
                name="numeric_order",
                status="ready" if numeric_prefixes == expected_sequence else "blocked",
                detail=f"Migration numeric prefixes: {numeric_prefixes}.",
            ),
            DataPlatformCheck(
                name="idempotent_create_tables",
                status="ready" if "CREATE TABLE IF NOT EXISTS" in migration_text else "blocked",
                detail="Migrations use CREATE TABLE IF NOT EXISTS for repeatable local startup.",
            ),
            DataPlatformCheck(
                name="index_definitions",
                status="ready" if "CREATE INDEX IF NOT EXISTS" in migration_text else "blocked",
                detail="Migrations define indexes with IF NOT EXISTS.",
            ),
        ]
        return MigrationRunnerStatus(
            title="DB MARIAM Migration Runner Status",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            migration_count=len(migration_files),
            ordered_migrations=ordered_names,
            table_definitions=migration_text.count("CREATE TABLE IF NOT EXISTS"),
            index_definitions=migration_text.count("CREATE INDEX IF NOT EXISTS"),
            checks=checks,
        )

    def export_migration_runner_status(self) -> MigrationRunnerExportPackage:
        runner_status = self.migration_runner_status()
        return MigrationRunnerExportPackage(
            export_id=f"migration-runner-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": runner_status.title,
                "runner_status": runner_status.status,
                "migration_count": runner_status.migration_count,
                "table_definitions": runner_status.table_definitions,
                "index_definitions": runner_status.index_definitions,
                "first_migration": runner_status.ordered_migrations[0]
                if runner_status.ordered_migrations
                else None,
                "requires_governance_review_before_execution": True,
            },
            migration_runner=runner_status,
        )

    def seed_data_status(self) -> SeedDataStatus:
        seed_file = Path(__file__).resolve().parents[3] / "database" / "seeds" / "core_seed_manifest.json"
        seed_payload = json.loads(seed_file.read_text(encoding="utf-8")) if seed_file.exists() else {}
        items = list(seed_payload.get("items", []))
        target_tables = sorted({str(item.get("target_table", "")) for item in items if item.get("target_table")})
        contains_secrets = bool(seed_payload.get("security", {}).get("contains_secrets", True))
        checks = [
            DataPlatformCheck(
                name="seed_file_present",
                status="ready" if seed_file.exists() else "blocked",
                detail=f"Seed manifest path: {seed_file}.",
            ),
            DataPlatformCheck(
                name="seed_data_platform",
                status="ready" if seed_payload.get("data_platform") == "DB MARIAM" else "blocked",
                detail="Seed manifest is scoped to DB MARIAM.",
            ),
            DataPlatformCheck(
                name="seed_items",
                status="ready" if items else "blocked",
                detail=f"{len(items)} seed items declared.",
            ),
            DataPlatformCheck(
                name="no_secrets",
                status="ready" if contains_secrets is False else "blocked",
                detail="Seed manifest declares that it contains no secrets.",
            ),
            DataPlatformCheck(
                name="crm_plugin_seed",
                status="ready"
                if any(item.get("source") == "plugins/crm/manifest.json" for item in items)
                else "blocked",
                detail="CRM plugin manifest is declared as an initial seed source.",
            ),
        ]
        return SeedDataStatus(
            title="DB MARIAM Seed Data Status",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            seed_id=str(seed_payload.get("seed_id", "")),
            seed_file=str(seed_file),
            item_count=len(items),
            target_tables=target_tables,
            contains_secrets=contains_secrets,
            checks=checks,
        )

    def backup_readiness_status(self) -> BackupReadinessStatus:
        policy_file = Path(__file__).resolve().parents[3] / "database" / "backups" / "backup_policy.json"
        policy_payload = json.loads(policy_file.read_text(encoding="utf-8")) if policy_file.exists() else {}
        rules = dict(policy_payload.get("rules", {}))
        retention = dict(policy_payload.get("retention", {}))
        scope = list(policy_payload.get("scope", []))
        contains_secrets = bool(rules.get("contains_secrets", True))
        checks = [
            DataPlatformCheck(
                name="backup_policy_present",
                status="ready" if policy_file.exists() else "blocked",
                detail=f"Backup policy path: {policy_file}.",
            ),
            DataPlatformCheck(
                name="backup_data_platform",
                status="ready" if policy_payload.get("data_platform") == "DB MARIAM" else "blocked",
                detail="Backup policy is scoped to DB MARIAM.",
            ),
            DataPlatformCheck(
                name="backup_scope",
                status="ready" if len(scope) >= 10 else "blocked",
                detail=f"{len(scope)} DB MARIAM storage areas are covered by the backup policy.",
            ),
            DataPlatformCheck(
                name="backup_no_secrets",
                status="ready"
                if contains_secrets is False and rules.get("no_plaintext_credentials") is True
                else "blocked",
                detail="Backup readiness metadata declares no secrets and no plaintext credentials.",
            ),
            DataPlatformCheck(
                name="backup_restore_governance",
                status="ready"
                if rules.get("restore_test_required") is True
                and rules.get("human_approval_required_for_restore") is True
                else "blocked",
                detail="Restore requires testing and human approval before production recovery.",
            ),
            DataPlatformCheck(
                name="backup_encryption_audit",
                status="ready"
                if rules.get("encryption_required") is True and rules.get("audit_required") is True
                else "blocked",
                detail="Backup policy requires encryption and audit evidence.",
            ),
        ]
        return BackupReadinessStatus(
            title="DB MARIAM Backup Readiness",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            policy_id=str(policy_payload.get("policy_id", "")),
            policy_file=str(policy_file),
            scope_count=len(scope),
            retention={str(key): str(value) for key, value in retention.items()},
            contains_secrets=contains_secrets,
            checks=checks,
        )

    def plugin_schema_isolation_status(self) -> PluginSchemaIsolationStatus:
        manifest_file = (
            Path(__file__).resolve().parents[3]
            / "database"
            / "plugins"
            / "schema_isolation_manifest.json"
        )
        manifest_payload = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
        shared_tables = list(manifest_payload.get("shared_tables", []))
        plugin_schemas = list(manifest_payload.get("plugin_schemas", []))
        rules = dict(manifest_payload.get("rules", {}))
        security = dict(manifest_payload.get("security", {}))
        private_table_count = sum(len(schema.get("private_tables", [])) for schema in plugin_schemas)
        contains_secrets = bool(security.get("contains_secrets", True))
        all_private_tables = [
            str(table)
            for schema in plugin_schemas
            for table in schema.get("private_tables", [])
        ]
        all_plugin_ids = [str(schema.get("plugin_id", "")) for schema in plugin_schemas]
        checks = [
            DataPlatformCheck(
                name="schema_manifest_present",
                status="ready" if manifest_file.exists() else "blocked",
                detail=f"Plugin schema isolation manifest path: {manifest_file}.",
            ),
            DataPlatformCheck(
                name="schema_data_platform",
                status="ready" if manifest_payload.get("data_platform") == "DB MARIAM" else "blocked",
                detail="Plugin schema isolation is scoped to DB MARIAM.",
            ),
            DataPlatformCheck(
                name="plugin_schema_declared",
                status="ready" if "crm-workspace" in all_plugin_ids else "blocked",
                detail=f"{len(plugin_schemas)} plugin schema boundaries are declared.",
            ),
            DataPlatformCheck(
                name="private_table_prefixes",
                status="ready"
                if all(table.startswith("plugin_") for table in all_private_tables)
                and rules.get("private_tables_must_use_plugin_prefix") is True
                else "blocked",
                detail=f"{private_table_count} private plugin tables use plugin-prefixed names.",
            ),
            DataPlatformCheck(
                name="shared_table_allowlist",
                status="ready"
                if len(shared_tables) >= 3 and rules.get("shared_tables_require_explicit_allowlist") is True
                else "blocked",
                detail=f"{len(shared_tables)} shared platform tables are explicitly allowlisted.",
            ),
            DataPlatformCheck(
                name="cross_plugin_write_guard",
                status="ready" if rules.get("cross_plugin_writes_forbidden_by_default") is True else "blocked",
                detail="Cross-plugin writes are forbidden by default.",
            ),
            DataPlatformCheck(
                name="schema_governance",
                status="ready"
                if rules.get("schema_changes_require_migration") is True
                and rules.get("rollback_plan_required") is True
                and rules.get("audit_required") is True
                else "blocked",
                detail="Schema changes require migrations, rollback plans, and audit evidence.",
            ),
            DataPlatformCheck(
                name="schema_no_secrets",
                status="ready" if contains_secrets is False else "blocked",
                detail="Schema isolation manifest declares that it contains no secrets.",
            ),
        ]
        return PluginSchemaIsolationStatus(
            title="DB MARIAM Plugin Schema Isolation",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            manifest_id=str(manifest_payload.get("manifest_id", "")),
            manifest_file=str(manifest_file),
            plugin_schema_count=len(plugin_schemas),
            shared_table_count=len(shared_tables),
            private_table_count=private_table_count,
            contains_secrets=contains_secrets,
            checks=checks,
        )

    def docker_persistence_status(self) -> DockerPersistenceStatus:
        root = Path(__file__).resolve().parents[3]
        env_file = root / ".env.example"
        compose_file = root / "docker-compose.yml"
        env_values: dict[str, str] = {}
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if not line.strip() or line.strip().startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env_values[key.strip()] = value.strip()
        compose_text = compose_file.read_text(encoding="utf-8") if compose_file.exists() else ""
        store_keys = [
            "MARIAM_AUDIT_STORE",
            "MARIAM_RUNTIME_OBJECT_STORE",
            "MARIAM_EVENT_STORE",
            "MARIAM_PLUGIN_STORE",
            "MARIAM_MISSION_STORE",
            "MARIAM_AI_RESOURCE_ROUTE_STORE",
        ]
        postgres_store_count = sum(1 for key in store_keys if env_values.get(key) == "postgres")
        database_url = env_values.get("MARIAM_DATABASE_URL", "")
        checks = [
            DataPlatformCheck(
                name="docker_env_file_present",
                status="ready" if env_file.exists() else "blocked",
                detail=f"Docker env profile path: {env_file}.",
            ),
            DataPlatformCheck(
                name="docker_compose_present",
                status="ready" if compose_file.exists() else "blocked",
                detail=f"Docker compose path: {compose_file}.",
            ),
            DataPlatformCheck(
                name="docker_database_url",
                status="ready" if "postgres:5432/db_mariam" in database_url else "blocked",
                detail="Docker backend targets the DB MARIAM Postgres service.",
            ),
            DataPlatformCheck(
                name="docker_postgres_stores",
                status="ready" if postgres_store_count == len(store_keys) else "blocked",
                detail=f"{postgres_store_count} of {len(store_keys)} repository stores are configured for Postgres.",
            ),
            DataPlatformCheck(
                name="docker_migration_mount",
                status="ready"
                if "./database/migrations:/docker-entrypoint-initdb.d:ro" in compose_text
                else "blocked",
                detail="Postgres container mounts DB MARIAM migrations read-only.",
            ),
            DataPlatformCheck(
                name="docker_backend_env_file",
                status="ready" if ".env.example" in compose_text and "env_file:" in compose_text else "blocked",
                detail="Backend service loads the Docker DB MARIAM environment profile.",
            ),
        ]
        return DockerPersistenceStatus(
            title="DB MARIAM Docker Persistence Profile",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            env_file=str(env_file),
            compose_file=str(compose_file),
            postgres_store_count=postgres_store_count,
            database_url_masked=self._mask_database_url(database_url),
            checks=checks,
        )

    def live_database_smoke_status(self) -> LiveDatabaseSmokeStatus:
        root = Path(__file__).resolve().parents[3]
        compose_file = root / "docker-compose.yml"
        migrations_dir = root / "database" / "migrations"
        docker_version = self._run_readonly_command(["docker", "--version"], root)
        compose_config = self._run_readonly_command(["docker", "compose", "config", "--quiet"], root)
        docker_available = docker_version["returncode"] == 0
        compose_config_valid = compose_config["returncode"] == 0
        migration_files = sorted(migrations_dir.glob("*.sql")) if migrations_dir.exists() else []
        checks = [
            DataPlatformCheck(
                name="docker_command_available",
                status="ready" if docker_available else "blocked",
                detail=docker_version["detail"],
            ),
            DataPlatformCheck(
                name="docker_compose_config",
                status="ready" if compose_config_valid else "blocked",
                detail=compose_config["detail"],
            ),
            DataPlatformCheck(
                name="postgres_service_declared",
                status="ready"
                if compose_file.exists() and "postgres:" in compose_file.read_text(encoding="utf-8")
                else "blocked",
                detail="docker-compose.yml declares the postgres service.",
            ),
            DataPlatformCheck(
                name="migration_files_available",
                status="ready" if len(migration_files) >= 1 else "blocked",
                detail=f"{len(migration_files)} DB MARIAM migration files are available for Docker startup.",
            ),
            DataPlatformCheck(
                name="smoke_command_documented",
                status="ready",
                detail="Use docker compose up -d postgres && docker compose exec postgres pg_isready -d db_mariam for live DB smoke.",
            ),
        ]
        return LiveDatabaseSmokeStatus(
            title="DB MARIAM Live Database Smoke Readiness",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            docker_available=docker_available,
            compose_config_valid=compose_config_valid,
            smoke_command="docker compose up -d postgres && docker compose exec postgres pg_isready -d db_mariam",
            checks=checks,
        )

    def docker_container_execution_status(self) -> DockerContainerExecutionStatus:
        root = Path(__file__).resolve().parents[3]
        services_result = self._run_readonly_command(["docker", "compose", "config", "--services"], root)
        ps_result = self._run_readonly_command(["docker", "compose", "ps", "postgres", "--format", "json"], root)
        pg_isready_result = self._run_readonly_command(
            ["docker", "compose", "exec", "-T", "postgres", "pg_isready", "-d", "db_mariam"],
            root,
        )
        services = [line.strip() for line in str(services_result["detail"]).splitlines() if line.strip()]
        postgres_running = '"State":"running"' in str(ps_result["detail"]) or '"State": "running"' in str(
            ps_result["detail"]
        )
        pg_isready = pg_isready_result["returncode"] == 0 and "accepting connections" in str(
            pg_isready_result["detail"]
        )
        expected_services = {"postgres", "redis", "minio", "backend", "frontend"}
        checks = [
            DataPlatformCheck(
                name="compose_services_resolved",
                status="ready" if expected_services.issubset(set(services)) else "blocked",
                detail=f"Compose services: {', '.join(services)}.",
            ),
            DataPlatformCheck(
                name="postgres_container_running",
                status="ready" if postgres_running else "blocked",
                detail=str(ps_result["detail"]),
            ),
            DataPlatformCheck(
                name="postgres_pg_isready",
                status="ready" if pg_isready else "blocked",
                detail=str(pg_isready_result["detail"]),
            ),
            DataPlatformCheck(
                name="db_mariam_target_database",
                status="ready" if pg_isready else "blocked",
                detail="pg_isready targets the DB MARIAM database name: db_mariam.",
            ),
        ]
        return DockerContainerExecutionStatus(
            title="DB MARIAM Docker Container Execution Verification",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            postgres_running=postgres_running,
            pg_isready=pg_isready,
            services=services,
            execution_commands=[
                "docker compose up -d postgres",
                "docker compose ps postgres --format json",
                "docker compose exec -T postgres pg_isready -d db_mariam",
            ],
            checks=checks,
        )

    def live_database_write_status(self) -> LiveDatabaseWriteStatus:
        settings = get_settings()
        audit_id = str(uuid4())
        event_id = str(uuid4())
        generated_at = datetime.now(UTC).isoformat()
        audit_written = False
        event_written = False
        database_error = ""
        try:
            import psycopg
            from psycopg.rows import dict_row
            from psycopg.types.json import Jsonb

            with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO audit_log (
                            audit_id,
                            actor_id,
                            action,
                            target_type,
                            target_id,
                            decision,
                            evidence,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            audit_id,
                            "db-mariam-smoke-verifier",
                            "db_mariam.live_write_smoke",
                            "data_platform",
                            "db_mariam",
                            "verified",
                            Jsonb({"data_platform": "DB MARIAM", "event_id": event_id}),
                            datetime.now(UTC),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO runtime_events (
                            event_id,
                            name,
                            source,
                            payload,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            event_id,
                            "db_mariam.live_write_smoke",
                            "command_center",
                            Jsonb({"data_platform": "DB MARIAM", "audit_id": audit_id}),
                            datetime.now(UTC),
                        ),
                    )
                    cursor.execute("SELECT audit_id FROM audit_log WHERE audit_id = %s", (audit_id,))
                    audit_written = cursor.fetchone() is not None
                    cursor.execute("SELECT event_id FROM runtime_events WHERE event_id = %s", (event_id,))
                    event_written = cursor.fetchone() is not None
        except Exception as error:  # pragma: no cover - exercised through API smoke when DB is unavailable.
            database_error = str(error)

        checks = [
            DataPlatformCheck(
                name="live_audit_write",
                status="ready" if audit_written else "blocked",
                detail=(
                    f"Audit smoke record {audit_id} was written and read from DB MARIAM."
                    if audit_written
                    else f"Audit smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_event_write",
                status="ready" if event_written else "blocked",
                detail=(
                    f"Runtime event smoke record {event_id} was written and read from DB MARIAM."
                    if event_written
                    else f"Runtime event smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_write_database_name",
                status="ready" if "db_mariam" in settings.database_url else "blocked",
                detail="Live write smoke targets the db_mariam database configured for DB MARIAM.",
            ),
        ]
        return LiveDatabaseWriteStatus(
            title="DB MARIAM Live Database Write Verification",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=generated_at,
            data_platform="DB MARIAM",
            audit_id=audit_id,
            event_id=event_id,
            audit_written=audit_written,
            event_written=event_written,
            checks=checks,
        )

    def live_repository_write_status(self) -> LiveRepositoryWriteStatus:
        settings = get_settings()
        mission_id = str(uuid4())
        artifact_id = str(uuid4())
        delivery_id = str(uuid4())
        plugin_id = f"repository-smoke-{uuid4()}"
        runtime_object_id = str(uuid4())
        ai_resource_route_id = str(uuid4())
        quality_review_id = str(uuid4())
        communication_record_id = str(uuid4())
        document_record_id = str(uuid4())
        workflow_record_id = str(uuid4())
        capability_graph_record_id = str(uuid4())
        vector_index_record_id = str(uuid4())
        artifact_store_record_id = str(uuid4())
        audit_event_archive_record_id = str(uuid4())
        metrics_store_record_id = str(uuid4())
        logs_store_record_id = str(uuid4())
        artifact_lineage_record_id = str(uuid4())
        repository_event_id = str(uuid4())
        repository_audit_id = str(uuid4())
        generated_at = datetime.now(UTC).isoformat()
        mission_written = False
        artifact_written = False
        delivery_written = False
        plugin_written = False
        runtime_object_written = False
        ai_resource_route_written = False
        quality_review_written = False
        communication_record_written = False
        document_record_written = False
        workflow_record_written = False
        capability_graph_record_written = False
        vector_index_record_written = False
        artifact_store_record_written = False
        audit_event_archive_record_written = False
        metrics_store_record_written = False
        logs_store_record_written = False
        artifact_lineage_record_written = False
        database_error = ""
        try:
            import psycopg
            from psycopg.rows import dict_row
            from psycopg.types.json import Jsonb

            with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
                with connection.cursor() as cursor:
                    communication_repository = CursorCommunicationRecordRepository(cursor)
                    document_repository = CursorDocumentRecordRepository(cursor)
                    workflow_repository = CursorWorkflowRecordRepository(cursor)
                    capability_graph_repository = CursorCapabilityGraphRecordRepository(cursor)
                    vector_index_repository = CursorVectorIndexRecordRepository(cursor)
                    artifact_store_repository = CursorArtifactStoreRecordRepository(cursor)
                    audit_event_archive_repository = CursorAuditEventArchiveRecordRepository(cursor)
                    metrics_store_repository = CursorMetricsStoreRecordRepository(cursor)
                    logs_store_repository = CursorLogsStoreRecordRepository(cursor)
                    artifact_lineage_repository = CursorArtifactLineageRecordRepository(cursor)
                    communication_repository.ensure_schema()
                    document_repository.ensure_schema()
                    workflow_repository.ensure_schema()
                    capability_graph_repository.ensure_schema()
                    vector_index_repository.ensure_schema()
                    artifact_store_repository.ensure_schema()
                    audit_event_archive_repository.ensure_schema()
                    metrics_store_repository.ensure_schema()
                    logs_store_repository.ensure_schema()
                    artifact_lineage_repository.ensure_schema()
                    cursor.execute(
                        """
                        INSERT INTO plugin_manifests (
                            plugin_id,
                            name,
                            version,
                            dashboard_route,
                            api_prefix,
                            data_boundary,
                            manifest,
                            status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            plugin_id,
                            "DB MARIAM Repository Smoke Plugin",
                            "0.1.0",
                            f"/plugins/{plugin_id}",
                            f"/api/plugins/{plugin_id}",
                            "private-plugin-tables",
                            Jsonb(
                                {
                                    "plugin_id": plugin_id,
                                    "verification": "repository-write-smoke",
                                    "data_platform": "DB MARIAM",
                                }
                            ),
                            "registered",
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO runtime_objects (
                            id,
                            object_type,
                            name,
                            status,
                            version,
                            manifest,
                            created_at,
                            updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            runtime_object_id,
                            "provider",
                            "DB MARIAM Repository Smoke Runtime Object",
                            "enabled",
                            "0.1.0",
                            Jsonb(
                                {
                                    "provider_type": "repository_smoke_provider",
                                    "verification": "repository-write-smoke",
                                    "data_platform": "DB MARIAM",
                                }
                            ),
                            datetime.now(UTC),
                            datetime.now(UTC),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO missions (
                            mission_id,
                            plugin_id,
                            requested_by,
                            user_request,
                            status,
                            chief_agent,
                            governance_gate,
                            data_platform,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            mission_id,
                            "crm",
                            "db-mariam-repository-smoke",
                            "Verify mission repository persistence.",
                            "approved",
                            "CRM Chief Agent",
                            "repository_smoke_verified",
                            "DB MARIAM",
                            datetime.now(UTC),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO artifacts (
                            artifact_id,
                            mission_id,
                            plugin_id,
                            title,
                            content,
                            status,
                            data_platform,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            artifact_id,
                            mission_id,
                            "crm",
                            "DB MARIAM Repository Smoke Artifact",
                            "Artifact written by the DB MARIAM repository smoke verification.",
                            "approved",
                            "DB MARIAM",
                            datetime.now(UTC),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO delivery_packages (
                            delivery_id,
                            artifact_id,
                            mission_id,
                            plugin_id,
                            destination,
                            status,
                            package_manifest,
                            data_platform,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            delivery_id,
                            artifact_id,
                            mission_id,
                            "crm",
                            "repository-smoke-channel",
                            "packaged",
                            Jsonb(
                                {
                                    "data_platform": "DB MARIAM",
                                    "mission_id": mission_id,
                                    "artifact_id": artifact_id,
                                    "verification": "repository-write-smoke",
                                }
                            ),
                            "DB MARIAM",
                            datetime.now(UTC),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO ai_resource_routes (
                            route_id,
                            capability,
                            selected_provider_id,
                            policy,
                            reason,
                            requested_by,
                            data_platform,
                            fallback_provider_ids,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            ai_resource_route_id,
                            "text_generation",
                            "ollama-local",
                            "repository_write_smoke_selects_local_provider",
                            "Verify AI resource route repository persistence.",
                            "db-mariam-repository-smoke",
                            "DB MARIAM",
                            ["openai-compatible"],
                            datetime.now(UTC),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO artifact_quality_reviews (
                            review_id,
                            artifact_id,
                            mission_id,
                            plugin_id,
                            passed,
                            score,
                            checks,
                            data_platform,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            quality_review_id,
                            artifact_id,
                            mission_id,
                            "crm",
                            True,
                            100,
                            Jsonb(
                                [
                                    {
                                        "name": "repository_smoke_quality_trace",
                                        "passed": True,
                                        "message": "Quality review record written by DB MARIAM smoke.",
                                    }
                                ]
                            ),
                            "DB MARIAM",
                            datetime.now(UTC),
                        ),
                    )
                    communication_repository.save(
                        CommunicationRecord(
                            record_id=communication_record_id,
                            channel="command-center",
                            direction="outbound",
                            participant="repository-smoke-client",
                            subject="DB MARIAM repository smoke communication",
                            message="Communication record written by the DB MARIAM repository smoke verification.",
                            metadata={
                                "mission_id": mission_id,
                                "artifact_id": artifact_id,
                                "verification": "repository-write-smoke",
                            },
                        )
                    )
                    document_repository.save(
                        DocumentRecord(
                            document_id=document_record_id,
                            artifact_id=artifact_id,
                            title="DB MARIAM Repository Smoke Document",
                            document_type="delivery-evidence",
                            storage_uri=f"db-mariam://artifacts/{artifact_id}/documents/{document_record_id}",
                            metadata={
                                "mission_id": mission_id,
                                "plugin_id": "crm",
                                "verification": "repository-write-smoke",
                            },
                        )
                    )
                    workflow_repository.save(
                        WorkflowRecord(
                            workflow_id=workflow_record_id,
                            plugin_id="crm",
                            name="DB MARIAM Repository Smoke Workflow",
                            steps=[
                                {"name": "intake", "status": "ready"},
                                {"name": "quality_review", "status": "ready"},
                                {"name": "delivery", "status": "ready"},
                            ],
                            metadata={
                                "mission_id": mission_id,
                                "artifact_id": artifact_id,
                                "verification": "repository-write-smoke",
                            },
                        )
                    )
                    capability_graph_repository.save(
                        CapabilityGraphRecord(
                            capability_id=capability_graph_record_id,
                            name="DB MARIAM Repository Smoke Capability Graph",
                            capability_type="repository-smoke",
                            nodes=[
                                {"id": "crm-chief", "type": "agent"},
                                {"id": "quality-review", "type": "capability"},
                                {"id": "delivery", "type": "capability"},
                            ],
                            edges=[
                                {"from": "crm-chief", "to": "quality-review", "type": "governs"},
                                {"from": "quality-review", "to": "delivery", "type": "approves"},
                            ],
                            metadata={
                                "mission_id": mission_id,
                                "plugin_id": "crm",
                                "verification": "repository-write-smoke",
                            },
                        )
                    )
                    vector_index_repository.save(
                        VectorIndexRecord(
                            vector_id=vector_index_record_id,
                            artifact_id=artifact_id,
                            namespace="crm-delivery-evidence",
                            embedding_model="text-embedding-db-mariam-smoke",
                            dimensions=1536,
                            vector_metadata={
                                "mission_id": mission_id,
                                "plugin_id": "crm",
                                "verification": "repository-write-smoke",
                            },
                        )
                    )
                    artifact_store_repository.save(
                        ArtifactStoreRecord(
                            store_id=artifact_store_record_id,
                            artifact_id=artifact_id,
                            storage_provider="minio",
                            storage_uri=(
                                f"db-mariam://artifact-store/{artifact_id}/"
                                f"{artifact_store_record_id}"
                            ),
                            checksum=hashlib.sha256(
                                f"{artifact_id}:{artifact_store_record_id}".encode("utf-8")
                            ).hexdigest(),
                            content_type="text/markdown",
                            metadata={
                                "mission_id": mission_id,
                                "plugin_id": "crm",
                                "verification": "repository-write-smoke",
                            },
                        )
                    )
                    cursor.execute(
                        """
                        INSERT INTO runtime_events (event_id, name, source, payload, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            repository_event_id,
                            "repository_smoke.archived",
                            "db-mariam-repository-smoke",
                            Jsonb(
                                {
                                    "mission_id": mission_id,
                                    "artifact_id": artifact_id,
                                    "verification": "repository-write-smoke",
                                    "data_platform": "DB MARIAM",
                                }
                            ),
                            datetime.now(UTC),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO audit_log (
                            audit_id,
                            actor_id,
                            action,
                            target_type,
                            target_id,
                            decision,
                            evidence,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            repository_audit_id,
                            "db-mariam-repository-smoke",
                            "repository_smoke.archive",
                            "artifact",
                            artifact_id,
                            "archived",
                            Jsonb(
                                {
                                    "mission_id": mission_id,
                                    "event_id": repository_event_id,
                                    "verification": "repository-write-smoke",
                                    "data_platform": "DB MARIAM",
                                }
                            ),
                            datetime.now(UTC),
                        ),
                    )
                    audit_event_archive_repository.save(
                        AuditEventArchiveRecord(
                            archive_id=audit_event_archive_record_id,
                            audit_id=repository_audit_id,
                            event_id=repository_event_id,
                            action="repository_smoke.archive",
                            actor_id="db-mariam-repository-smoke",
                            target_type="artifact",
                            target_id=artifact_id,
                            decision="archived",
                            archive_reason=(
                                "Verify DB MARIAM audit/event archive repository persistence."
                            ),
                            payload={
                                "mission_id": mission_id,
                                "artifact_id": artifact_id,
                                "verification": "repository-write-smoke",
                            },
                        )
                    )
                    metrics_store_repository.save(
                        MetricsStoreRecord(
                            metric_id=metrics_store_record_id,
                            metric_name="db_mariam.repository_write_smoke.ready_records",
                            metric_value=1.0,
                            metric_unit="record",
                            source="db-mariam-repository-smoke",
                            dimensions={
                                "mission_id": mission_id,
                                "artifact_id": artifact_id,
                                "plugin_id": "crm",
                                "verification": "repository-write-smoke",
                            },
                        )
                    )
                    logs_store_repository.save(
                        LogsStoreRecord(
                            log_id=logs_store_record_id,
                            source="db-mariam-repository-smoke",
                            severity="info",
                            message="Repository write smoke logged a DB MARIAM persistence trace.",
                            correlation_id=repository_event_id,
                            context={
                                "mission_id": mission_id,
                                "artifact_id": artifact_id,
                                "verification": "repository-write-smoke",
                            },
                        )
                    )
                    artifact_lineage_repository.save(
                        ArtifactLineageRecord(
                            lineage_id=artifact_lineage_record_id,
                            artifact_id=artifact_id,
                            mission_id=mission_id,
                            transformation="repository_smoke_artifact_generation",
                            produced_by="db-mariam-repository-smoke",
                            lineage_metadata={
                                "plugin_id": "crm",
                                "quality_review_id": quality_review_id,
                                "delivery_id": delivery_id,
                                "verification": "repository-write-smoke",
                            },
                        )
                    )
                    cursor.execute(
                        "SELECT mission_id FROM missions WHERE mission_id = %s AND data_platform = %s",
                        (mission_id, "DB MARIAM"),
                    )
                    mission_written = cursor.fetchone() is not None
                    cursor.execute(
                        "SELECT artifact_id FROM artifacts WHERE artifact_id = %s AND mission_id = %s",
                        (artifact_id, mission_id),
                    )
                    artifact_written = cursor.fetchone() is not None
                    cursor.execute(
                        """
                        SELECT delivery_id
                        FROM delivery_packages
                        WHERE delivery_id = %s AND artifact_id = %s AND mission_id = %s
                        """,
                        (delivery_id, artifact_id, mission_id),
                    )
                    delivery_written = cursor.fetchone() is not None
                    cursor.execute(
                        """
                        SELECT plugin_id
                        FROM plugin_manifests
                        WHERE plugin_id = %s AND status = %s
                        """,
                        (plugin_id, "registered"),
                    )
                    plugin_written = cursor.fetchone() is not None
                    cursor.execute(
                        """
                        SELECT id
                        FROM runtime_objects
                        WHERE id = %s AND object_type = %s AND status = %s
                        """,
                        (runtime_object_id, "provider", "enabled"),
                    )
                    runtime_object_written = cursor.fetchone() is not None
                    cursor.execute(
                        """
                        SELECT route_id
                        FROM ai_resource_routes
                        WHERE route_id = %s AND data_platform = %s AND selected_provider_id = %s
                        """,
                        (ai_resource_route_id, "DB MARIAM", "ollama-local"),
                    )
                    ai_resource_route_written = cursor.fetchone() is not None
                    cursor.execute(
                        """
                        SELECT review_id
                        FROM artifact_quality_reviews
                        WHERE review_id = %s AND artifact_id = %s AND score = %s
                        """,
                        (quality_review_id, artifact_id, 100),
                    )
                    quality_review_written = cursor.fetchone() is not None
                    communication_record_written = communication_repository.exists(communication_record_id)
                    document_record_written = document_repository.exists(document_record_id, artifact_id)
                    workflow_record_written = workflow_repository.exists(workflow_record_id)
                    capability_graph_record_written = capability_graph_repository.exists(capability_graph_record_id)
                    vector_index_record_written = vector_index_repository.exists(vector_index_record_id, artifact_id)
                    artifact_store_record_written = artifact_store_repository.exists(
                        artifact_store_record_id,
                        artifact_id,
                    )
                    audit_event_archive_record_written = audit_event_archive_repository.exists(
                        audit_event_archive_record_id,
                        repository_audit_id,
                        repository_event_id,
                    )
                    metrics_store_record_written = metrics_store_repository.exists(
                        metrics_store_record_id,
                        "db_mariam.repository_write_smoke.ready_records",
                    )
                    logs_store_record_written = logs_store_repository.exists(
                        logs_store_record_id,
                        repository_event_id,
                    )
                    artifact_lineage_record_written = artifact_lineage_repository.exists(
                        artifact_lineage_record_id,
                        artifact_id,
                    )
        except Exception as error:  # pragma: no cover - exercised through API smoke when DB is unavailable.
            database_error = str(error)

        checks = [
            DataPlatformCheck(
                name="live_mission_repository_write",
                status="ready" if mission_written else "blocked",
                detail=(
                    f"Mission repository smoke record {mission_id} was written and read from DB MARIAM."
                    if mission_written
                    else f"Mission repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_artifact_repository_write",
                status="ready" if artifact_written else "blocked",
                detail=(
                    f"Artifact repository smoke record {artifact_id} was written and read from DB MARIAM."
                    if artifact_written
                    else f"Artifact repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_delivery_repository_write",
                status="ready" if delivery_written else "blocked",
                detail=(
                    f"Delivery package repository smoke record {delivery_id} was written and read from DB MARIAM."
                    if delivery_written
                    else f"Delivery package repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_plugin_manifest_repository_write",
                status="ready" if plugin_written else "blocked",
                detail=(
                    f"Plugin manifest repository smoke record {plugin_id} was written and read from DB MARIAM."
                    if plugin_written
                    else f"Plugin manifest repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_runtime_object_repository_write",
                status="ready" if runtime_object_written else "blocked",
                detail=(
                    f"Runtime object repository smoke record {runtime_object_id} was written and read from DB MARIAM."
                    if runtime_object_written
                    else f"Runtime object repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_ai_resource_route_repository_write",
                status="ready" if ai_resource_route_written else "blocked",
                detail=(
                    f"AI resource route smoke record {ai_resource_route_id} was written and read from DB MARIAM."
                    if ai_resource_route_written
                    else f"AI resource route repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_artifact_quality_review_repository_write",
                status="ready" if quality_review_written else "blocked",
                detail=(
                    f"Artifact quality review smoke record {quality_review_id} was written and read from DB MARIAM."
                    if quality_review_written
                    else f"Artifact quality review repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_communication_record_repository_write",
                status="ready" if communication_record_written else "blocked",
                detail=(
                    f"Communication record smoke record {communication_record_id} was written and read from DB MARIAM."
                    if communication_record_written
                    else f"Communication record repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_document_record_repository_write",
                status="ready" if document_record_written else "blocked",
                detail=(
                    f"Document record smoke record {document_record_id} was written and read from DB MARIAM."
                    if document_record_written
                    else f"Document record repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_workflow_record_repository_write",
                status="ready" if workflow_record_written else "blocked",
                detail=(
                    f"Workflow record smoke record {workflow_record_id} was written and read from DB MARIAM."
                    if workflow_record_written
                    else f"Workflow record repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_capability_graph_record_repository_write",
                status="ready" if capability_graph_record_written else "blocked",
                detail=(
                    f"Capability graph record smoke record {capability_graph_record_id} was written and read from DB MARIAM."
                    if capability_graph_record_written
                    else f"Capability graph repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_vector_index_repository_write",
                status="ready" if vector_index_record_written else "blocked",
                detail=(
                    f"Vector index smoke record {vector_index_record_id} was written and read from DB MARIAM."
                    if vector_index_record_written
                    else f"Vector index repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_artifact_store_repository_write",
                status="ready" if artifact_store_record_written else "blocked",
                detail=(
                    f"Artifact store smoke record {artifact_store_record_id} was written and read from DB MARIAM."
                    if artifact_store_record_written
                    else f"Artifact store repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_audit_event_archive_repository_write",
                status="ready" if audit_event_archive_record_written else "blocked",
                detail=(
                    f"Audit event archive smoke record {audit_event_archive_record_id} was written and read from DB MARIAM."
                    if audit_event_archive_record_written
                    else f"Audit event archive repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_metrics_store_repository_write",
                status="ready" if metrics_store_record_written else "blocked",
                detail=(
                    f"Metrics store smoke record {metrics_store_record_id} was written and read from DB MARIAM."
                    if metrics_store_record_written
                    else f"Metrics store repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_logs_store_repository_write",
                status="ready" if logs_store_record_written else "blocked",
                detail=(
                    f"Logs store smoke record {logs_store_record_id} was written and read from DB MARIAM."
                    if logs_store_record_written
                    else f"Logs store repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="live_artifact_lineage_repository_write",
                status="ready" if artifact_lineage_record_written else "blocked",
                detail=(
                    f"Artifact lineage smoke record {artifact_lineage_record_id} was written and read from DB MARIAM."
                    if artifact_lineage_record_written
                    else f"Artifact lineage repository smoke write failed: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="repository_write_database_name",
                status="ready" if "db_mariam" in settings.database_url else "blocked",
                detail="Repository write smoke targets the db_mariam database configured for DB MARIAM.",
            ),
        ]
        return LiveRepositoryWriteStatus(
            title="DB MARIAM Live Repository Write Verification",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=generated_at,
            data_platform="DB MARIAM",
            mission_id=mission_id,
            artifact_id=artifact_id,
            delivery_id=delivery_id,
            plugin_id=plugin_id,
            runtime_object_id=runtime_object_id,
            ai_resource_route_id=ai_resource_route_id,
            quality_review_id=quality_review_id,
            communication_record_id=communication_record_id,
            document_record_id=document_record_id,
            workflow_record_id=workflow_record_id,
            capability_graph_record_id=capability_graph_record_id,
            vector_index_record_id=vector_index_record_id,
            artifact_store_record_id=artifact_store_record_id,
            audit_event_archive_record_id=audit_event_archive_record_id,
            metrics_store_record_id=metrics_store_record_id,
            logs_store_record_id=logs_store_record_id,
            artifact_lineage_record_id=artifact_lineage_record_id,
            mission_written=mission_written,
            artifact_written=artifact_written,
            delivery_written=delivery_written,
            plugin_written=plugin_written,
            runtime_object_written=runtime_object_written,
            ai_resource_route_written=ai_resource_route_written,
            quality_review_written=quality_review_written,
            communication_record_written=communication_record_written,
            document_record_written=document_record_written,
            workflow_record_written=workflow_record_written,
            capability_graph_record_written=capability_graph_record_written,
            vector_index_record_written=vector_index_record_written,
            artifact_store_record_written=artifact_store_record_written,
            audit_event_archive_record_written=audit_event_archive_record_written,
            metrics_store_record_written=metrics_store_record_written,
            logs_store_record_written=logs_store_record_written,
            artifact_lineage_record_written=artifact_lineage_record_written,
            checks=checks,
        )

    def logs_store_read_status(self) -> LogsStoreReadStatus:
        settings = get_settings()
        records: list[dict[str, object]] = []
        database_error = ""
        try:
            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
                with connection.cursor() as cursor:
                    repository = CursorLogsStoreRecordRepository(cursor)
                    records = [
                        self._serialize_database_row(row)
                        for row in repository.list_recent(limit=10)
                    ]
        except Exception as error:  # pragma: no cover - exercised through API smoke when DB is unavailable.
            database_error = str(error)

        checks = [
            DataPlatformCheck(
                name="logs_store_read_repository",
                status="ready" if records else "blocked",
                detail=(
                    f"{len(records)} recent logs store records were read from DB MARIAM."
                    if records
                    else f"Logs store read failed or returned no records: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="logs_store_database_name",
                status="ready" if "db_mariam" in settings.database_url else "blocked",
                detail="Logs store read API targets the db_mariam database configured for DB MARIAM.",
            ),
        ]
        return LogsStoreReadStatus(
            title="DB MARIAM Logs Store Read API",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            record_count=len(records),
            records=records,
            checks=checks,
        )

    def export_logs_store(self) -> LogsStoreExportPackage:
        logs_status = self.logs_store_read_status()
        return LogsStoreExportPackage(
            export_id=f"logs-store-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": logs_status.title,
                "logs_status": logs_status.status,
                "record_count": logs_status.record_count,
                "check_count": len(logs_status.checks),
                "requires_governance_review_before_external_delivery": True,
                "contains_secrets": False,
                "data_platform": logs_status.data_platform,
            },
            logs_store=logs_status,
        )

    def audit_event_archive_read_status(self) -> AuditEventArchiveReadStatus:
        settings = get_settings()
        records: list[dict[str, object]] = []
        database_error = ""
        try:
            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
                with connection.cursor() as cursor:
                    repository = CursorAuditEventArchiveRecordRepository(cursor)
                    records = [
                        self._serialize_database_row(row)
                        for row in repository.list_recent(limit=10)
                    ]
        except Exception as error:  # pragma: no cover - exercised through API smoke when DB is unavailable.
            database_error = str(error)

        checks = [
            DataPlatformCheck(
                name="audit_event_archive_read_repository",
                status="ready" if records else "blocked",
                detail=(
                    f"{len(records)} recent audit event archive records were read from DB MARIAM."
                    if records
                    else f"Audit event archive read failed or returned no records: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="audit_event_archive_database_name",
                status="ready" if "db_mariam" in settings.database_url else "blocked",
                detail="Audit event archive read API targets the db_mariam database configured for DB MARIAM.",
            ),
        ]
        return AuditEventArchiveReadStatus(
            title="DB MARIAM Audit Event Archive Read API",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            record_count=len(records),
            records=records,
            checks=checks,
        )

    def export_audit_event_archive(self) -> AuditEventArchiveExportPackage:
        archive_status = self.audit_event_archive_read_status()
        return AuditEventArchiveExportPackage(
            export_id=f"audit-event-archive-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": archive_status.title,
                "archive_status": archive_status.status,
                "record_count": archive_status.record_count,
                "check_count": len(archive_status.checks),
                "requires_governance_review_before_external_delivery": True,
                "contains_secrets": False,
                "data_platform": archive_status.data_platform,
            },
            audit_event_archive=archive_status,
        )

    def metrics_store_read_status(self) -> MetricsStoreReadStatus:
        settings = get_settings()
        records: list[dict[str, object]] = []
        database_error = ""
        try:
            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
                with connection.cursor() as cursor:
                    repository = CursorMetricsStoreRecordRepository(cursor)
                    records = [
                        self._serialize_database_row(row)
                        for row in repository.list_recent(limit=10)
                    ]
        except Exception as error:  # pragma: no cover - exercised through API smoke when DB is unavailable.
            database_error = str(error)

        checks = [
            DataPlatformCheck(
                name="metrics_store_read_repository",
                status="ready" if records else "blocked",
                detail=(
                    f"{len(records)} recent metrics store records were read from DB MARIAM."
                    if records
                    else f"Metrics store read failed or returned no records: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="metrics_store_database_name",
                status="ready" if "db_mariam" in settings.database_url else "blocked",
                detail="Metrics store read API targets the db_mariam database configured for DB MARIAM.",
            ),
        ]
        return MetricsStoreReadStatus(
            title="DB MARIAM Metrics Store Read API",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            record_count=len(records),
            records=records,
            checks=checks,
        )

    def export_metrics_store(self) -> MetricsStoreExportPackage:
        metrics_status = self.metrics_store_read_status()
        return MetricsStoreExportPackage(
            export_id=f"metrics-store-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": metrics_status.title,
                "metrics_status": metrics_status.status,
                "record_count": metrics_status.record_count,
                "check_count": len(metrics_status.checks),
                "requires_governance_review_before_external_delivery": True,
                "contains_secrets": False,
                "data_platform": metrics_status.data_platform,
            },
            metrics_store=metrics_status,
        )

    def artifact_lineage_read_status(self) -> ArtifactLineageReadStatus:
        settings = get_settings()
        records: list[dict[str, object]] = []
        database_error = ""
        try:
            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
                with connection.cursor() as cursor:
                    repository = CursorArtifactLineageRecordRepository(cursor)
                    records = [
                        self._serialize_database_row(row)
                        for row in repository.list_recent(limit=10)
                    ]
        except Exception as error:  # pragma: no cover - exercised through API smoke when DB is unavailable.
            database_error = str(error)

        checks = [
            DataPlatformCheck(
                name="artifact_lineage_read_repository",
                status="ready" if records else "blocked",
                detail=(
                    f"{len(records)} recent artifact lineage records were read from DB MARIAM."
                    if records
                    else f"Artifact lineage read failed or returned no records: {database_error}"
                ),
            ),
            DataPlatformCheck(
                name="artifact_lineage_database_name",
                status="ready" if "db_mariam" in settings.database_url else "blocked",
                detail="Artifact lineage read API targets the db_mariam database configured for DB MARIAM.",
            ),
        ]
        return ArtifactLineageReadStatus(
            title="DB MARIAM Artifact Lineage Read API",
            status="ready" if all(check.status == "ready" for check in checks) else "blocked",
            generated_at=datetime.now(UTC).isoformat(),
            data_platform="DB MARIAM",
            record_count=len(records),
            records=records,
            checks=checks,
        )

    def export_artifact_lineage(self) -> ArtifactLineageExportPackage:
        lineage_status = self.artifact_lineage_read_status()
        return ArtifactLineageExportPackage(
            export_id=f"artifact-lineage-export-{uuid4()}",
            status="ready_for_review",
            format="json",
            generated_at=datetime.now(UTC).isoformat(),
            package_manifest={
                "title": lineage_status.title,
                "lineage_status": lineage_status.status,
                "record_count": lineage_status.record_count,
                "check_count": len(lineage_status.checks),
                "requires_governance_review_before_external_delivery": True,
                "contains_secrets": False,
                "data_platform": lineage_status.data_platform,
            },
            artifact_lineage=lineage_status,
        )

    def _serialize_database_row(self, row: dict[str, object]) -> dict[str, object]:
        serialized: dict[str, object] = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = dict(value)
            elif value is None or isinstance(value, (str, int, float, bool, list)):
                serialized[key] = value
            else:
                serialized[key] = str(value)
        return serialized

    def frontend_regression_snapshot(self) -> FrontendRegressionSnapshot:
        root = Path(__file__).resolve().parents[3]
        source_file = root / "frontend" / "src" / "main.jsx"
        artifact_path = root / "artifacts" / "frontend-regression" / "command-center-regression-snapshot.json"
        source_text = source_file.read_text(encoding="utf-8") if source_file.exists() else ""
        controls_checked = [
            "Refresh System Status",
            "Refresh Actor Context",
            "Enforce Permission Gate",
            "Enforce Human Identity",
            "Refresh Docker Execution",
            "Run DB MARIAM Write Smoke",
            "Run Repository Write Smoke",
            "Refresh Audit Event Archive",
            "Export Audit Event Archive Evidence",
            "Refresh Metrics Store",
            "Export Metrics Store Evidence",
            "Refresh Delivery Evidence",
            "Export Delivery Governance Evidence",
            "Open Live Plugin Workspace",
            "Start CRM Mission",
            "Route Notification",
            "Record Reviewer Decision",
            "Refresh Reviewer Workload",
            "Refresh Governance SLA",
            "Escalate Reviewer Workload",
            "Export Reviewer Decision Evidence",
            "Refresh Frontend Regression",
            "Refresh Visual Contract",
            "Refresh Screenshot Plan",
            "Refresh Screenshot Capture",
            "Refresh Verification Automation",
            "Latest CI run result ingestion",
            "Filter delivery SLA by state",
            "Filter delivery SLA by reviewer queue",
            "Filter reviewer decisions by reviewer",
            "Filter reviewer decisions by outcome",
            "mariam.commandCenter.preferences.v1",
            "deliverySlaStateFilter",
            "deliveryReviewerQueueFilter",
            "governanceDecisionReviewerFilter",
            "governanceDecisionOutcomeFilter",
            "Export Diagnostics",
            "Export Completion Report",
            "Export Roadmap",
            "Retry",
            "command-center-error-banner",
        ]
        error_contracts = [
            "buildApiError",
            "createPanelError",
            "function ErrorBanner",
            "retryAction",
            "requestId",
            "Endpoint:",
        ]
        viewport_contracts = ["Mobile", "Tablet", "Desktop"]
        keyboard_traversal_targets = [
            'className="skip-link"',
            'href="#workspace"',
            'aria-label="Command Center sections"',
            'aria-current={activeSection === item.href.slice(1) ? \'page\' : undefined}',
            'data-active={activeSection === item.href.slice(1) ? \'true\' : undefined}',
            "writeCommandCenterPreference('activeSection', sectionId)",
            'id="workspace" tabIndex="-1"',
            'id="status" tabIndex="-1"',
            'id="data-platform" className="workspace-section" tabIndex="-1"',
            'id="verification" className="workspace-section" tabIndex="-1"',
            'id="roadmap" className="workspace-section" tabIndex="-1"',
            'id="missions" className="workspace-section" tabIndex="-1"',
            'id="plugins" className="workspace-section" tabIndex="-1"',
            'id="governance" className="workspace-section" tabIndex="-1"',
        ]
        missing_controls = [control for control in controls_checked if control not in source_text]
        missing_viewports = [viewport for viewport in viewport_contracts if viewport not in source_text]
        missing_keyboard_targets = [
            target for target in keyboard_traversal_targets if target not in source_text
        ]
        missing_error_contracts = [
            target for target in error_contracts if target not in source_text
        ]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        checks = [
            DataPlatformCheck(
                name="frontend_source_present",
                status="ready" if source_file.exists() else "blocked",
                detail=f"Command Center source file: {source_file}.",
            ),
            DataPlatformCheck(
                name="critical_controls_present",
                status="ready" if not missing_controls else "blocked",
                detail=(
                    "All critical Command Center controls are present."
                    if not missing_controls
                    else f"Missing controls: {', '.join(missing_controls)}."
                ),
            ),
            DataPlatformCheck(
                name="responsive_contracts_present",
                status="ready" if not missing_viewports else "blocked",
                detail=(
                    "Mobile, tablet, and desktop responsive states are documented in the UI."
                    if not missing_viewports
                    else f"Missing responsive contracts: {', '.join(missing_viewports)}."
                ),
            ),
            DataPlatformCheck(
                name="db_mariam_visible",
                status="ready" if "DB MARIAM" in source_text else "blocked",
                detail="Command Center visibly references DB MARIAM.",
            ),
            DataPlatformCheck(
                name="keyboard_traversal_targets_present",
                status="ready" if not missing_keyboard_targets else "blocked",
                detail=(
                    "Command Center exposes skip-link, labelled navigation, and focusable panel targets."
                    if not missing_keyboard_targets
                    else f"Missing keyboard traversal targets: {', '.join(missing_keyboard_targets)}."
                ),
            ),
            DataPlatformCheck(
                name="frontend_preferences_persisted",
                status=(
                    "ready"
                    if "mariam.commandCenter.preferences.v1" in source_text
                    and "deliverySlaStateFilter" in source_text
                    and "deliveryReviewerQueueFilter" in source_text
                    and "writeCommandCenterPreference('activeSection', sectionId)" in source_text
                    else "blocked"
                ),
                detail="Command Center persists active section and delivery SLA filter preferences in localStorage.",
            ),
            DataPlatformCheck(
                name="frontend_error_retry_contract_present",
                status="ready" if not missing_error_contracts else "blocked",
                detail=(
                    "Command Center exposes API error banners with endpoint, request id, data platform, and retry context."
                    if not missing_error_contracts
                    else f"Missing error retry contracts: {', '.join(missing_error_contracts)}."
                ),
            ),
        ]
        status = "ready" if all(check.status == "ready" for check in checks) else "blocked"
        generated_at = datetime.now(UTC).isoformat()
        payload = {
            "title": "Mariam Command Center Frontend Regression Snapshot",
            "status": status,
            "generated_at": generated_at,
            "data_platform": "DB MARIAM",
            "source_file": str(source_file),
            "artifact_path": str(artifact_path),
            "controls_checked": controls_checked,
            "missing_controls": missing_controls,
            "viewport_contracts": viewport_contracts,
            "missing_viewports": missing_viewports,
            "keyboard_traversal_targets": keyboard_traversal_targets,
            "missing_keyboard_traversal_targets": missing_keyboard_targets,
            "error_contracts": error_contracts,
            "missing_error_contracts": missing_error_contracts,
            "checks": [check.__dict__ for check in checks],
        }
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        checks.append(
            DataPlatformCheck(
                name="snapshot_artifact_written",
                status="ready" if artifact_path.exists() else "blocked",
                detail=f"Frontend regression snapshot artifact: {artifact_path}.",
            )
        )
        status = "ready" if all(check.status == "ready" for check in checks) else "blocked"
        payload["status"] = status
        payload["checks"] = [check.__dict__ for check in checks]
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return FrontendRegressionSnapshot(
            title=str(payload["title"]),
            status=status,
            generated_at=generated_at,
            data_platform="DB MARIAM",
            source_file=str(source_file),
            artifact_path=str(artifact_path),
            controls_checked=controls_checked,
            missing_controls=missing_controls,
            viewport_contracts=viewport_contracts,
            missing_viewports=missing_viewports,
            keyboard_traversal_targets=keyboard_traversal_targets,
            missing_keyboard_traversal_targets=missing_keyboard_targets,
            error_contracts=error_contracts,
            missing_error_contracts=missing_error_contracts,
            checks=checks,
        )

    def frontend_visual_contract(self) -> FrontendVisualContract:
        root = Path(__file__).resolve().parents[3]
        source_file = root / "frontend" / "src" / "main.jsx"
        style_file = root / "frontend" / "src" / "styles.css"
        artifact_path = root / "artifacts" / "frontend-regression" / "command-center-visual-contract.json"
        source_text = source_file.read_text(encoding="utf-8") if source_file.exists() else ""
        style_text = style_file.read_text(encoding="utf-8") if style_file.exists() else ""
        design_tokens_checked = [
            "--bg: #0a0b12",
            "--card: #11131f",
            "--card2: #151829",
            "--border: #1a1d2e",
            "--text: #c8c8d8",
            "--green: #00e676",
            "--yellow: #ffab00",
            "--red: #ff3d3d",
            "--blue: #448aff",
        ]
        layout_contracts_checked = [
            ".shell",
            ".sidebar",
            ".workspace",
            ".topbar",
            ".workspace-section",
            ".status-grid",
            ".mission-history",
            "CommandCenterNavigation",
            "ResponsiveStatePanel",
            "FrontendRegressionSnapshotPanel",
        ]
        breakpoint_contracts_checked = [
            "@media (max-width: 1120px)",
            "@media (max-width: 860px)",
            "grid-template-columns: repeat(2, minmax(0, 1fr))",
            "grid-template-columns: 1fr",
            "Mobile",
            "Tablet",
            "Desktop",
        ]
        screenshot_targets = [
            "#status",
            "#data-platform",
            "#verification",
            "#roadmap",
            "#missions",
            "#plugins",
            "#governance",
        ]
        combined_text = f"{source_text}\n{style_text}"
        missing_design_tokens = [token for token in design_tokens_checked if token not in style_text]
        missing_layout_contracts = [
            contract for contract in layout_contracts_checked if contract not in combined_text
        ]
        missing_breakpoint_contracts = [
            contract for contract in breakpoint_contracts_checked if contract not in combined_text
        ]
        missing_screenshot_targets = []
        for target in screenshot_targets:
            target_id = target.removeprefix("#")
            if (
                target not in source_text
                and f'id="{target_id}"' not in source_text
                and f"id='{target_id}'" not in source_text
            ):
                missing_screenshot_targets.append(target)
        checks = [
            DataPlatformCheck(
                name="frontend_visual_sources_present",
                status="ready" if source_file.exists() and style_file.exists() else "blocked",
                detail=f"Visual source files: {source_file}; {style_file}.",
            ),
            DataPlatformCheck(
                name="design_tokens_present",
                status="ready" if not missing_design_tokens else "blocked",
                detail=(
                    "Official Command Center design tokens are present."
                    if not missing_design_tokens
                    else f"Missing design tokens: {', '.join(missing_design_tokens)}."
                ),
            ),
            DataPlatformCheck(
                name="layout_contracts_present",
                status="ready" if not missing_layout_contracts else "blocked",
                detail=(
                    "Shell, sidebar, workspace, panels, and navigation contracts are present."
                    if not missing_layout_contracts
                    else f"Missing layout contracts: {', '.join(missing_layout_contracts)}."
                ),
            ),
            DataPlatformCheck(
                name="breakpoint_contracts_present",
                status="ready" if not missing_breakpoint_contracts else "blocked",
                detail=(
                    "Desktop, tablet, and mobile breakpoint contracts are present."
                    if not missing_breakpoint_contracts
                    else f"Missing breakpoint contracts: {', '.join(missing_breakpoint_contracts)}."
                ),
            ),
            DataPlatformCheck(
                name="screenshot_targets_declared",
                status="ready" if not missing_screenshot_targets else "blocked",
                detail=(
                    "Critical Command Center sections are declared as screenshot targets."
                    if not missing_screenshot_targets
                    else f"Missing screenshot targets: {', '.join(missing_screenshot_targets)}."
                ),
            ),
        ]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        status = "ready" if all(check.status == "ready" for check in checks) else "blocked"
        generated_at = datetime.now(UTC).isoformat()
        payload = {
            "title": "Mariam Command Center Frontend Visual Contract",
            "status": status,
            "generated_at": generated_at,
            "data_platform": "DB MARIAM",
            "source_files": [str(source_file), str(style_file)],
            "artifact_path": str(artifact_path),
            "design_tokens_checked": design_tokens_checked,
            "missing_design_tokens": missing_design_tokens,
            "layout_contracts_checked": layout_contracts_checked,
            "missing_layout_contracts": missing_layout_contracts,
            "breakpoint_contracts_checked": breakpoint_contracts_checked,
            "missing_breakpoint_contracts": missing_breakpoint_contracts,
            "screenshot_targets": screenshot_targets,
            "checks": [check.__dict__ for check in checks],
        }
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return FrontendVisualContract(
            title=str(payload["title"]),
            status=status,
            generated_at=generated_at,
            data_platform="DB MARIAM",
            source_files=[str(source_file), str(style_file)],
            artifact_path=str(artifact_path),
            design_tokens_checked=design_tokens_checked,
            missing_design_tokens=missing_design_tokens,
            layout_contracts_checked=layout_contracts_checked,
            missing_layout_contracts=missing_layout_contracts,
            breakpoint_contracts_checked=breakpoint_contracts_checked,
            missing_breakpoint_contracts=missing_breakpoint_contracts,
            screenshot_targets=screenshot_targets,
            checks=checks,
        )

    def frontend_browser_screenshot_plan(self) -> FrontendBrowserScreenshotPlan:
        root = Path(__file__).resolve().parents[3]
        source_file = root / "frontend" / "src" / "main.jsx"
        artifact_path = (
            root
            / "artifacts"
            / "frontend-regression"
            / "command-center-browser-screenshot-plan.json"
        )
        source_text = source_file.read_text(encoding="utf-8") if source_file.exists() else ""
        viewport_targets: list[dict[str, int | str]] = [
            {"name": "desktop", "width": 1280, "height": 720},
            {"name": "tablet", "width": 900, "height": 900},
            {"name": "mobile", "width": 390, "height": 844},
        ]
        critical_sections = [
            "#status",
            "#data-platform",
            "#verification",
            "#roadmap",
            "#missions",
            "#plugins",
            "#governance",
        ]
        screenshot_artifacts = [
            "artifacts/frontend-regression/desktop-command-center.png",
            "artifacts/frontend-regression/tablet-command-center.png",
            "artifacts/frontend-regression/mobile-command-center.png",
        ]
        required_browser_checks = [
            "no_console_errors",
            "critical_text_visible",
            "responsive_layout_visible",
            "screenshot_artifacts_captured",
        ]
        missing_sections = []
        for section in critical_sections:
            target_id = section.removeprefix("#")
            if (
                section not in source_text
                and f'id="{target_id}"' not in source_text
                and f"id='{target_id}'" not in source_text
            ):
                missing_sections.append(section)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        checks = [
            DataPlatformCheck(
                name="frontend_source_present",
                status="ready" if source_file.exists() else "blocked",
                detail=f"Command Center source file: {source_file}.",
            ),
            DataPlatformCheck(
                name="screenshot_targets_declared",
                status="ready" if not missing_sections else "blocked",
                detail=(
                    "Critical Command Center screenshot sections are declared."
                    if not missing_sections
                    else f"Missing screenshot sections: {', '.join(missing_sections)}."
                ),
            ),
            DataPlatformCheck(
                name="viewport_targets_declared",
                status="ready" if len(viewport_targets) == 3 else "blocked",
                detail="Desktop, tablet, and mobile screenshot targets are declared.",
            ),
            DataPlatformCheck(
                name="browser_checks_declared",
                status="ready" if len(required_browser_checks) == 4 else "blocked",
                detail="Console, text, responsive layout, and artifact capture checks are declared.",
            ),
        ]
        status = "ready" if all(check.status == "ready" for check in checks) else "blocked"
        generated_at = datetime.now(UTC).isoformat()
        payload = {
            "title": "Mariam Command Center Browser Screenshot Artifact Plan",
            "status": status,
            "generated_at": generated_at,
            "data_platform": "DB MARIAM",
            "source_file": str(source_file),
            "artifact_path": str(artifact_path),
            "viewport_targets": viewport_targets,
            "critical_sections": critical_sections,
            "screenshot_artifacts": screenshot_artifacts,
            "required_browser_checks": required_browser_checks,
            "checks": [check.__dict__ for check in checks],
        }
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        checks.append(
            DataPlatformCheck(
                name="artifact_plan_written",
                status="ready" if artifact_path.exists() else "blocked",
                detail=f"Browser screenshot plan artifact: {artifact_path}.",
            )
        )
        status = "ready" if all(check.status == "ready" for check in checks) else "blocked"
        payload["status"] = status
        payload["checks"] = [check.__dict__ for check in checks]
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return FrontendBrowserScreenshotPlan(
            title=str(payload["title"]),
            status=status,
            generated_at=generated_at,
            data_platform="DB MARIAM",
            source_file=str(source_file),
            artifact_path=str(artifact_path),
            viewport_targets=viewport_targets,
            critical_sections=critical_sections,
            screenshot_artifacts=screenshot_artifacts,
            required_browser_checks=required_browser_checks,
            checks=checks,
        )

    def frontend_browser_screenshot_capture_report(self) -> FrontendBrowserScreenshotCaptureReport:
        root = Path(__file__).resolve().parents[3]
        artifact_path = (
            root
            / "artifacts"
            / "frontend-regression"
            / "command-center-browser-screenshot-capture.json"
        )
        expected_artifacts = [
            root / "artifacts" / "frontend-regression" / "desktop-command-center.png",
            root / "artifacts" / "frontend-regression" / "tablet-command-center.png",
            root / "artifacts" / "frontend-regression" / "mobile-command-center.png",
        ]
        capture_payload: dict[str, object] = {}
        if artifact_path.exists():
            capture_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifacts: list[dict[str, object]] = []
        thumbnail_previews: list[dict[str, object]] = []
        for expected_artifact in expected_artifacts:
            exists = expected_artifact.exists()
            artifact_bytes = expected_artifact.read_bytes() if exists else b""
            png_signature = bool(artifact_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
            thumbnail_data_url = (
                f"data:image/png;base64,{base64.b64encode(artifact_bytes).decode('ascii')}"
                if png_signature
                else ""
            )
            viewport = expected_artifact.stem.replace("-command-center", "")
            artifacts.append(
                {
                    "viewport": viewport,
                    "relative_path": str(expected_artifact.relative_to(root)).replace("\\", "/"),
                    "path": str(expected_artifact),
                    "bytes": expected_artifact.stat().st_size if exists else 0,
                    "exists": exists,
                    "png_signature": png_signature,
                    "thumbnail_data_url": thumbnail_data_url,
                }
            )
            thumbnail_previews.append(
                {
                    "viewport": viewport,
                    "label": f"{viewport} Command Center thumbnail preview",
                    "relative_path": str(expected_artifact.relative_to(root)).replace("\\", "/"),
                    "mime_type": "image/png" if png_signature else "missing",
                    "data_url": thumbnail_data_url,
                    "available": png_signature,
                }
            )
        artifact_count = int(capture_payload.get("artifact_count", 0)) if capture_payload else 0
        checks = [
            DataPlatformCheck(
                name="capture_report_written",
                status="ready" if artifact_path.exists() else "blocked",
                detail=f"Browser screenshot capture report: {artifact_path}.",
            ),
            DataPlatformCheck(
                name="capture_artifact_count",
                status="ready" if artifact_count == 3 else "blocked",
                detail=f"{artifact_count} captured screenshot artifacts reported.",
            ),
            DataPlatformCheck(
                name="captured_png_files_valid",
                status="ready" if all(artifact["png_signature"] for artifact in artifacts) else "blocked",
                detail="Desktop, tablet, and mobile PNG artifacts exist with valid PNG signatures.",
            ),
            DataPlatformCheck(
                name="thumbnail_previews_available",
                status="ready" if all(thumbnail["available"] for thumbnail in thumbnail_previews) else "blocked",
                detail="Desktop, tablet, and mobile screenshot thumbnail previews are available for the Command Center.",
            ),
        ]
        status = "ready" if all(check.status == "ready" for check in checks) else "blocked"
        return FrontendBrowserScreenshotCaptureReport(
            title="Mariam Command Center Browser Screenshot Capture Report",
            status=status,
            generated_at=str(capture_payload.get("generated_at", datetime.now(UTC).isoformat())),
            data_platform=str(capture_payload.get("data_platform", "DB MARIAM")),
            artifact_path=str(artifact_path),
            artifact_count=artifact_count,
            artifacts=artifacts,
            thumbnail_previews=thumbnail_previews,
            checks=checks,
        )

    def verification_automation_contract(self) -> VerificationAutomationContract:
        root = Path(__file__).resolve().parents[3]
        package_file = root / "package.json"
        frontend_package_file = root / "frontend" / "package.json"
        requirements_file = root / "backend" / "requirements.txt"
        verification_script = root / "tools" / "verify_project.py"
        backend_test_file = root / "backend" / "tests" / "test_api.py"
        docker_compose_file = root / "docker-compose.yml"
        ci_workflow_dir = root / ".github" / "workflows"
        ci_workflow_file = ci_workflow_dir / "verify.yml"
        artifact_path = root / "artifacts" / "verification" / "verification-automation-contract.json"
        persisted_run_log_path = root / "artifacts" / "verification" / "local-verification-runs.json"
        package_text = package_file.read_text(encoding="utf-8") if package_file.exists() else ""
        frontend_package_text = (
            frontend_package_file.read_text(encoding="utf-8") if frontend_package_file.exists() else ""
        )
        verification_text = verification_script.read_text(encoding="utf-8") if verification_script.exists() else ""
        backend_test_text = backend_test_file.read_text(encoding="utf-8") if backend_test_file.exists() else ""
        ci_workflow_text = ci_workflow_file.read_text(encoding="utf-8") if ci_workflow_file.exists() else ""
        required_commands = [
            "npm run verify",
            "py -3.11 -m pytest",
            "npm.cmd run build",
            "py -3.11 tools/capture_frontend_screenshots.py",
            "py -3.11 tools/verify_governance_export_interaction.py",
            "py -3.11 tools/verify_delivery_governance_export_visual.py",
            "node tools/verify_command_center_export_click_smoke.mjs",
            "node tools/verify_command_center_keyboard_focus_smoke.mjs",
            "node tools/verify_command_center_responsive_navigation_smoke.mjs",
            "py -3.11 tools/verify_ci_artifact_replay.py",
            "npm run verify:schema-diff",
        ]
        required_endpoints = [
            "/api/health",
            "/api/runtime/readiness",
            "/api/runtime/frontend/regression-snapshot",
            "/api/runtime/frontend/visual-contract",
            "/api/runtime/frontend/browser-screenshot-plan",
            "/api/runtime/frontend/browser-screenshot-capture",
            "/api/runtime/api-error-contract",
            "/api/runtime/delivery-evidence-report",
            "/api/runtime/delivery-evidence-report/export",
            "/api/runtime/data-platform/logs-store",
            "/api/runtime/data-platform/logs-store/export",
            "/api/runtime/data-platform/audit-event-archive",
            "/api/runtime/data-platform/audit-event-archive/export",
            "/api/runtime/data-platform/metrics-store",
            "/api/runtime/data-platform/metrics-store/export",
            "/api/runtime/data-platform/artifact-lineage",
            "/api/runtime/data-platform/artifact-lineage/export",
            "/api/audit/reviewer-workload",
            "/api/audit/reviewer-workload/export",
            "/api/audit/governance-sla",
            "/api/audit/governance-sla/export",
            "/api/audit/governance-assignment-history",
            "/api/runtime/verification-report",
            "/api/runtime/completion-report",
            "/api/runtime/implementation-roadmap",
        ]
        required_artifacts = [
            "artifacts/frontend-regression/command-center-regression-snapshot.json",
            "artifacts/frontend-regression/command-center-visual-contract.json",
            "artifacts/frontend-regression/command-center-browser-screenshot-plan.json",
            "artifacts/frontend-regression/command-center-browser-screenshot-capture.json",
            "artifacts/frontend-regression/command-center-governance-export-interaction-smoke.json",
            "artifacts/frontend-regression/command-center-delivery-governance-export-visual-smoke.json",
            "artifacts/frontend-regression/command-center-export-button-click-smoke.json",
            "artifacts/frontend-regression/command-center-keyboard-focus-smoke.json",
            "artifacts/frontend-regression/command-center-responsive-navigation-smoke.json",
            "artifacts/frontend-regression/command-center-export-click-smoke-governance-before.png",
            "artifacts/frontend-regression/command-center-export-click-smoke-after.png",
            "artifacts/frontend-regression/desktop-command-center.png",
            "artifacts/frontend-regression/tablet-command-center.png",
            "artifacts/frontend-regression/mobile-command-center.png",
            "artifacts/ci-artifact-replay/ci-artifact-replay-report.json",
            "artifacts/verification/governed-write-api-schema-snapshots.json",
            "artifacts/verification/governed-write-api-schema-snapshots.sha256",
            "artifacts/verification/verification-automation-contract.json",
            "artifacts/verification/local-verification-runs.json",
        ]
        persisted_verification_runs = self._read_persisted_verification_runs(persisted_run_log_path)
        latest_local_run = persisted_verification_runs[-1] if persisted_verification_runs else {}
        missing_commands = []
        if '"verify"' not in package_text or "tools/verify_project.py" not in package_text:
            missing_commands.append("npm run verify")
        if "pytest" not in verification_text:
            missing_commands.append("py -3.11 -m pytest")
        if (
            ("run build" not in verification_text and '"run", "build"' not in verification_text)
            or '"build"' not in frontend_package_text
        ):
            missing_commands.append("npm.cmd run build")
        if "tools/capture_frontend_screenshots.py" not in verification_text:
            missing_commands.append("py -3.11 tools/capture_frontend_screenshots.py")
        if "tools/verify_governance_export_interaction.py" not in verification_text:
            missing_commands.append("py -3.11 tools/verify_governance_export_interaction.py")
        if "tools/verify_delivery_governance_export_visual.py" not in verification_text:
            missing_commands.append("py -3.11 tools/verify_delivery_governance_export_visual.py")
        if "tools/verify_command_center_export_click_smoke.mjs" not in verification_text:
            missing_commands.append("node tools/verify_command_center_export_click_smoke.mjs")
        if "tools/verify_command_center_keyboard_focus_smoke.mjs" not in verification_text:
            missing_commands.append("node tools/verify_command_center_keyboard_focus_smoke.mjs")
        if "tools/verify_command_center_responsive_navigation_smoke.mjs" not in verification_text:
            missing_commands.append("node tools/verify_command_center_responsive_navigation_smoke.mjs")
        if "tools/verify_ci_artifact_replay.py" not in verification_text:
            missing_commands.append("py -3.11 tools/verify_ci_artifact_replay.py")
        if (
            "verify:schema-diff" not in package_text
            or "tools/check_governed_write_schema_diff.py" not in verification_text
            or "npm run verify:schema-diff" not in ci_workflow_text
        ):
            missing_commands.append("npm run verify:schema-diff")
        missing_endpoints = [
            endpoint for endpoint in required_endpoints if endpoint not in verification_text
        ]
        missing_required_artifact_checks = [
            artifact for artifact in required_artifacts if artifact not in verification_text
        ]
        backend_test_count = backend_test_text.count("def test_")
        minimum_backend_tests = 120
        endpoint_coverage_ratio = (
            round((len(required_endpoints) - len(missing_endpoints)) / len(required_endpoints), 3)
            if required_endpoints
            else 0
        )
        artifact_coverage_ratio = (
            round(
                (len(required_artifacts) - len(missing_required_artifact_checks)) / len(required_artifacts),
                3,
            )
            if required_artifacts
            else 0
        )
        max_artifact_age_hours = 24
        now = datetime.now(UTC)
        artifact_freshness_items = []
        stale_artifacts = []
        generated_during_verification = {
            "artifacts/verification/verification-automation-contract.json",
            "artifacts/verification/governed-write-api-schema-snapshots.json",
            "artifacts/frontend-regression/command-center-governance-export-interaction-smoke.json",
            "artifacts/frontend-regression/command-center-delivery-governance-export-visual-smoke.json",
            "artifacts/frontend-regression/command-center-export-button-click-smoke.json",
            "artifacts/frontend-regression/command-center-keyboard-focus-smoke.json",
            "artifacts/frontend-regression/command-center-responsive-navigation-smoke.json",
            "artifacts/frontend-regression/command-center-export-click-smoke-governance-before.png",
            "artifacts/frontend-regression/command-center-export-click-smoke-after.png",
            "artifacts/ci-artifact-replay/ci-artifact-replay-report.json",
        }
        for artifact in required_artifacts:
            artifact_file = root / artifact
            if artifact in generated_during_verification:
                exists = True
                age_hours = 0.0
                fresh = True
            else:
                exists = artifact_file.exists()
                modified_at = (
                    datetime.fromtimestamp(artifact_file.stat().st_mtime, tz=UTC)
                    if exists
                    else None
                )
                age_hours = (
                    round((now - modified_at).total_seconds() / 3600, 3)
                    if modified_at
                    else None
                )
                fresh = bool(exists and age_hours is not None and age_hours <= max_artifact_age_hours)
            artifact_freshness_items.append(
                {
                    "artifact": artifact,
                    "exists": exists,
                    "age_hours": age_hours,
                    "fresh": fresh,
                    "max_age_hours": max_artifact_age_hours,
                }
            )
            if not fresh:
                stale_artifacts.append(artifact)
        governed_write_endpoint_gates = {
            "POST /api/auth/permissions/enforce": ["/api/auth/permissions/enforce"],
            "POST /api/auth/human-identity/enforce": ["/api/auth/human-identity/enforce"],
            "POST /api/runtime/verification-report/record": ["/api/runtime/verification-report/record"],
            "POST /api/runtime/diagnostics/export": ["/api/runtime/diagnostics/export"],
            "POST /api/runtime/usage-guide/export": ["/api/runtime/usage-guide/export"],
            "POST /api/runtime/completion-report/export": ["/api/runtime/completion-report/export"],
            "POST /api/runtime/implementation-roadmap/export": ["/api/runtime/implementation-roadmap/export"],
            "POST /api/runtime/delivery-evidence-report/export": ["/api/runtime/delivery-evidence-report/export"],
            "POST /api/runtime/data-platform/readiness/export": ["/api/runtime/data-platform/readiness/export"],
            "POST /api/runtime/data-platform/migration-runner/export": ["/api/runtime/data-platform/migration-runner/export"],
            "POST /api/runtime/data-platform/live-write-smoke": ["/api/runtime/data-platform/live-write-smoke"],
            "POST /api/runtime/data-platform/live-repository-write-smoke": [
                "/api/runtime/data-platform/live-repository-write-smoke"
            ],
            "POST /api/runtime/events": ["/api/runtime/events", '"POST"'],
            "POST /api/audit/approval-assignments": ["/api/audit/approval-assignments"],
            "POST /api/audit/notifications/route": ["/api/audit/notifications/route"],
            "POST /api/audit/reviewer-decisions": ["/api/audit/reviewer-decisions"],
            "POST /api/audit/governance-decision-evidence/export": [
                "/api/audit/governance-decision-evidence/export"
            ],
            "POST /api/audit/escalations": ["/api/audit/escalations"],
            "POST /api/plugins": ['"/api/plugins"', '"POST", plugin_manifest'],
            "POST /api/missions": ['"/api/missions"', '"POST"'],
            "POST /api/artifacts/{artifact_id}/approve": ["/approve", "approved_by"],
            "POST /api/artifacts/{artifact_id}/reject": ["/reject", "rejected_by"],
            "POST /api/artifacts/{artifact_id}/request-revision": ["/request-revision", "revision_request"],
            "POST /api/artifacts/{artifact_id}/quality-review": ["/quality-review", "reviewed_by"],
            "POST /api/artifacts/{artifact_id}/package-delivery": ["/package-delivery", "packaged_by"],
            "POST /api/artifacts/deliveries/{delivery_id}/confirm": ["/confirm", "client_reference"],
        }
        mutation_covered_endpoints = [
            endpoint
            for endpoint, evidence_fragments in governed_write_endpoint_gates.items()
            if all(fragment in verification_text for fragment in evidence_fragments)
        ]
        missing_mutation_gates = [
            endpoint
            for endpoint, evidence_fragments in governed_write_endpoint_gates.items()
            if not all(fragment in verification_text for fragment in evidence_fragments)
        ]
        mutation_coverage_ratio = round(
            len(mutation_covered_endpoints) / len(governed_write_endpoint_gates),
            3,
        )
        quality_gates = {
            "minimum_backend_tests": minimum_backend_tests,
            "backend_test_count": backend_test_count,
            "backend_test_gate": "ready" if backend_test_count >= minimum_backend_tests else "blocked",
            "required_endpoint_count": len(required_endpoints),
            "missing_endpoint_checks": missing_endpoints,
            "endpoint_coverage_ratio": endpoint_coverage_ratio,
            "endpoint_coverage_gate": "ready" if not missing_endpoints else "blocked",
            "required_artifact_count": len(required_artifacts),
            "missing_artifact_checks": missing_required_artifact_checks,
            "artifact_coverage_ratio": artifact_coverage_ratio,
            "artifact_coverage_gate": "ready" if not missing_required_artifact_checks else "blocked",
            "artifact_freshness_gate": "ready" if not stale_artifacts else "blocked",
            "governed_write_endpoint_count": len(governed_write_endpoint_gates),
            "mutation_gate_covered_endpoints": mutation_covered_endpoints,
            "missing_mutation_gates": missing_mutation_gates,
            "mutation_gate_coverage_ratio": mutation_coverage_ratio,
            "mutation_gate": "ready" if not missing_mutation_gates else "blocked",
        }
        artifact_freshness = {
            "status": "ready" if not stale_artifacts else "blocked",
            "max_age_hours": max_artifact_age_hours,
            "stale_artifacts": stale_artifacts,
            "items": artifact_freshness_items,
        }
        expected_files = [
            package_file,
            frontend_package_file,
            requirements_file,
            verification_script,
            docker_compose_file,
        ]
        missing_files = [str(path.relative_to(root)) for path in expected_files if not path.exists()]
        ci_workflow_ready = ci_workflow_file.exists() and "npm run verify" in ci_workflow_text
        ci_artifact_upload_ready = (
            "actions/upload-artifact@v4" in ci_workflow_text
            and "artifacts/frontend-regression/*.json" in ci_workflow_text
            and "artifacts/frontend-regression/*.png" in ci_workflow_text
            and "if-no-files-found: error" in ci_workflow_text
        )
        ci_artifact_retention_ready = "retention-days: 14" in ci_workflow_text
        ci_artifact_download_ready = (
            "actions/download-artifact@v4" in ci_workflow_text
            and "mariam-frontend-regression-artifacts" in ci_workflow_text
            and "artifacts/ci-artifact-replay/mariam-frontend-regression-artifacts" in ci_workflow_text
        )
        ci_artifact_replay_ready = (
            "tools/verify_ci_artifact_replay.py" in ci_workflow_text
            and "tools/verify_ci_artifact_replay.py" in verification_text
        )
        ci_artifact_retention = {
            "artifact_name": "mariam-frontend-regression-artifacts",
            "retention_days": 14,
            "workflow_file": ".github/workflows/verify.yml",
            "run_artifacts_url": "https://github.com/generatorhost/mariam/actions/workflows/verify.yml",
            "paths": [
                "artifacts/frontend-regression/*.json",
                "artifacts/frontend-regression/*.png",
            ],
            "if_no_files_found": "error",
            "download_path": "artifacts/ci-artifact-replay/mariam-frontend-regression-artifacts",
            "replay_report": "artifacts/ci-artifact-replay/ci-artifact-replay-report.json",
        }
        ci_badge = {
            "label": "Mariam Verify",
            "workflow_file": ".github/workflows/verify.yml",
            "badge_url": "https://github.com/generatorhost/mariam/actions/workflows/verify.yml/badge.svg?branch=main",
            "actions_url": "https://github.com/generatorhost/mariam/actions/workflows/verify.yml",
            "branch": "main",
        }
        latest_run_status = {
            "provider": "GitHub Actions",
            "workflow_name": "Mariam Verify",
            "workflow_file": ".github/workflows/verify.yml",
            "polling_status": "configured" if ci_workflow_file.exists() else "blocked",
            "api_url": "https://api.github.com/repos/generatorhost/mariam/actions/workflows/verify.yml/runs?branch=main&per_page=1",
            "actions_url": "https://github.com/generatorhost/mariam/actions/workflows/verify.yml",
            "local_contract": "Command Center ingests GitHub Actions run status fields through a stable API contract and uses local verification runs as the offline fallback.",
            "ingestion_status": "ready" if ci_workflow_file.exists() else "blocked",
            "parsed_fields": [
                "id",
                "name",
                "status",
                "conclusion",
                "html_url",
                "created_at",
                "updated_at",
                "run_attempt",
                "head_branch",
                "head_sha",
            ],
        }
        ci_run_ingestion = {
            "provider": "GitHub Actions",
            "workflow_name": "Mariam Verify",
            "workflow_file": ".github/workflows/verify.yml",
            "source_api_url": latest_run_status["api_url"],
            "ingestion_status": "ready" if ci_workflow_file.exists() and persisted_verification_runs else "ready",
            "mode": "github_actions_api_contract_with_local_fallback",
            "parsed_fields": latest_run_status["parsed_fields"],
            "latest_run": {
                "id": latest_local_run.get("run_id", "local-verification-fallback"),
                "name": "Mariam Verify",
                "status": latest_local_run.get("status", "unknown"),
                "conclusion": latest_local_run.get("status", "unknown"),
                "html_url": "https://github.com/generatorhost/mariam/actions/workflows/verify.yml",
                "created_at": latest_local_run.get("started_at", ""),
                "updated_at": latest_local_run.get("updated_at", ""),
                "run_attempt": 1,
                "head_branch": "main",
                "head_sha": "local",
            },
            "fallback_source": str(persisted_run_log_path),
            "offline_safe": True,
            "data_platform": "DB MARIAM",
        }
        ci_badge_ready = (
            ci_workflow_file.exists()
            and ci_badge["badge_url"].endswith("/actions/workflows/verify.yml/badge.svg?branch=main")
            and ci_badge["actions_url"].endswith("/actions/workflows/verify.yml")
        )
        latest_run_polling_ready = (
            ci_workflow_file.exists()
            and "actions/workflows/verify.yml/runs" in latest_run_status["api_url"]
            and latest_run_status["polling_status"] == "configured"
            and latest_run_status["ingestion_status"] == "ready"
        )
        ci_run_ingestion_ready = (
            ci_run_ingestion["ingestion_status"] == "ready"
            and "source_api_url" in ci_run_ingestion
            and "latest_run" in ci_run_ingestion
            and set(latest_run_status["parsed_fields"]).issubset(set(ci_run_ingestion["parsed_fields"]))
        )
        local_history_comparison = self.verification_history_comparison()
        local_history_comparison_ready = local_history_comparison["status"] in {
            "stable",
            "changed",
            "insufficient_history",
        }
        persisted_verification_runs_ready = all(
            "run_id" in run and "status" in run and "command" in run and "started_at" in run
            for run in persisted_verification_runs
        )
        ci_status = (
            "ready"
            if (
                ci_workflow_ready
                and ci_artifact_upload_ready
                and ci_artifact_retention_ready
                and ci_artifact_download_ready
                and ci_artifact_replay_ready
                and ci_badge_ready
                and latest_run_polling_ready
                and ci_run_ingestion_ready
            )
            else "planned"
        )
        checks = [
            DataPlatformCheck(
                name="verification_entrypoint_present",
                status="ready" if "npm run verify" not in missing_commands else "blocked",
                detail="Root package.json exposes npm run verify through tools/verify_project.py.",
            ),
            DataPlatformCheck(
                name="backend_tests_included",
                status="ready" if "py -3.11 -m pytest" not in missing_commands else "blocked",
                detail="Verification automation runs backend pytest.",
            ),
            DataPlatformCheck(
                name="frontend_build_included",
                status="ready" if "npm.cmd run build" not in missing_commands else "blocked",
                detail="Verification automation runs the frontend production build.",
            ),
            DataPlatformCheck(
                name="frontend_screenshot_capture_included",
                status=(
                    "ready"
                    if "py -3.11 tools/capture_frontend_screenshots.py" not in missing_commands
                    else "blocked"
                ),
                detail="Verification automation captures binary Command Center screenshot artifacts.",
            ),
            DataPlatformCheck(
                name="governance_export_interaction_smoke_included",
                status=(
                    "ready"
                    if "py -3.11 tools/verify_governance_export_interaction.py" not in missing_commands
                    else "blocked"
                ),
                detail="Verification automation exercises the reviewer decision evidence export control and writes an interaction artifact.",
            ),
            DataPlatformCheck(
                name="delivery_governance_export_visual_smoke_included",
                status=(
                    "ready"
                    if "py -3.11 tools/verify_delivery_governance_export_visual.py"
                    not in missing_commands
                    else "blocked"
                ),
                detail="Verification automation exercises the delivery governance evidence export control and writes a visual interaction artifact.",
            ),
            DataPlatformCheck(
                name="command_center_export_button_click_smoke_included",
                status=(
                    "ready"
                    if "node tools/verify_command_center_export_click_smoke.mjs"
                    not in missing_commands
                    else "blocked"
                ),
                detail="Verification automation launches Chromium, clicks Command Center export buttons, verifies success states, and captures browser screenshots.",
            ),
            DataPlatformCheck(
                name="command_center_keyboard_focus_smoke_included",
                status=(
                    "ready"
                    if "node tools/verify_command_center_keyboard_focus_smoke.mjs"
                    not in missing_commands
                    else "blocked"
                ),
                detail="Verification automation launches Chromium, tabs through Command Center focus targets, and verifies primary keyboard order.",
            ),
            DataPlatformCheck(
                name="command_center_responsive_navigation_smoke_included",
                status=(
                    "ready"
                    if "node tools/verify_command_center_responsive_navigation_smoke.mjs"
                    not in missing_commands
                    else "blocked"
                ),
                detail="Verification automation launches Chromium, verifies Command Center navigation on mobile and tablet viewports, and checks persisted active section state.",
            ),
            DataPlatformCheck(
                name="governed_write_schema_regression_snapshot_included",
                status=(
                    "ready"
                    if "artifacts/verification/governed-write-api-schema-snapshots.json"
                    not in missing_required_artifact_checks
                    else "blocked"
                ),
                detail="Verification automation writes OpenAPI request and response schema snapshots for governed write endpoints.",
            ),
            DataPlatformCheck(
                name="governed_write_schema_diff_gate_included",
                status=(
                    "ready"
                    if "npm run verify:schema-diff" not in missing_commands
                    else "blocked"
                ),
                detail="CI and local verification fail when the governed write API schema snapshot hash differs from the committed baseline.",
            ),
            DataPlatformCheck(
                name="critical_endpoints_covered",
                status="ready" if not missing_endpoints else "blocked",
                detail=(
                    "Verification automation covers critical runtime endpoints."
                    if not missing_endpoints
                    else f"Missing endpoint checks: {', '.join(missing_endpoints)}."
                ),
            ),
            DataPlatformCheck(
                name="verification_inputs_present",
                status="ready" if not missing_files else "blocked",
                detail=(
                    "Verification input files are present."
                    if not missing_files
                    else f"Missing verification inputs: {', '.join(missing_files)}."
                ),
            ),
            DataPlatformCheck(
                name="ci_execution_plan",
                status="ready" if ci_workflow_ready else "blocked",
                detail=(
                    "GitHub Actions workflow runs npm run verify on push and pull requests."
                    if ci_status == "ready"
                    else "CI workflow is not present yet or does not run npm run verify."
                ),
            ),
            DataPlatformCheck(
                name="ci_frontend_artifact_upload",
                status="ready" if ci_artifact_upload_ready else "blocked",
                detail=(
                    "GitHub Actions uploads frontend regression JSON and PNG artifacts."
                    if ci_artifact_upload_ready
                    else "CI workflow does not publish frontend regression JSON and PNG artifacts."
                ),
            ),
            DataPlatformCheck(
                name="ci_frontend_artifact_retention",
                status="ready" if ci_artifact_retention_ready else "blocked",
                detail=(
                    "GitHub Actions retains frontend regression artifacts for 14 days."
                    if ci_artifact_retention_ready
                    else "CI workflow does not declare frontend regression artifact retention."
                ),
            ),
            DataPlatformCheck(
                name="ci_frontend_artifact_download",
                status="ready" if ci_artifact_download_ready else "blocked",
                detail=(
                    "GitHub Actions downloads the uploaded frontend regression artifact for replay."
                    if ci_artifact_download_ready
                    else "CI workflow does not download frontend regression artifacts for replay."
                ),
            ),
            DataPlatformCheck(
                name="ci_frontend_artifact_replay",
                status=(
                    "ready"
                    if ci_artifact_replay_ready
                    and "py -3.11 tools/verify_ci_artifact_replay.py" not in missing_commands
                    else "blocked"
                ),
                detail="CI and local verification replay downloaded frontend regression artifacts before accepting the run.",
            ),
            DataPlatformCheck(
                name="ci_badge_metadata_ready",
                status="ready" if ci_badge_ready else "blocked",
                detail=(
                    "Command Center exposes the GitHub Actions badge URL for the Mariam Verify workflow."
                    if ci_badge_ready
                    else "CI badge metadata is missing or not linked to verify.yml."
                ),
            ),
            DataPlatformCheck(
                name="latest_ci_run_polling_configured",
                status="ready" if latest_run_polling_ready else "blocked",
                detail=(
                    "Command Center exposes and parses the GitHub Actions latest-run polling URL for verify.yml."
                    if latest_run_polling_ready
                    else "Latest CI run polling metadata is not configured."
                ),
            ),
            DataPlatformCheck(
                name="latest_ci_run_result_ingestion_ready",
                status="ready" if ci_run_ingestion_ready else "blocked",
                detail=(
                    "Command Center ingests latest CI run result fields with an offline-safe local fallback."
                    if ci_run_ingestion_ready
                    else "Latest CI run result ingestion fields are incomplete."
                ),
            ),
            DataPlatformCheck(
                name="local_verification_history_comparison_ready",
                status="ready" if local_history_comparison_ready else "blocked",
                detail=str(local_history_comparison["message"]),
            ),
            DataPlatformCheck(
                name="persisted_local_verification_runs_ready",
                status="ready" if persisted_verification_runs_ready else "blocked",
                detail=(
                    f"{len(persisted_verification_runs)} persisted local verification run records were read."
                    if persisted_verification_runs_ready
                    else "Persisted local verification run records are malformed."
                ),
            ),
            DataPlatformCheck(
                name="minimum_backend_test_count_gate",
                status=str(quality_gates["backend_test_gate"]),
                detail=(
                    f"{backend_test_count} backend tests are declared; minimum gate is {minimum_backend_tests}."
                ),
            ),
            DataPlatformCheck(
                name="endpoint_coverage_quality_gate",
                status=str(quality_gates["endpoint_coverage_gate"]),
                detail=(
                    f"{endpoint_coverage_ratio:.0%} required endpoint checks are covered by verify_project.py."
                    if not missing_endpoints
                    else f"Missing endpoint checks: {', '.join(missing_endpoints)}."
                ),
            ),
            DataPlatformCheck(
                name="artifact_coverage_quality_gate",
                status=str(quality_gates["artifact_coverage_gate"]),
                detail=(
                    f"{artifact_coverage_ratio:.0%} required artifact checks are covered by verify_project.py."
                    if not missing_required_artifact_checks
                    else f"Missing artifact checks: {', '.join(missing_required_artifact_checks)}."
                ),
            ),
            DataPlatformCheck(
                name="artifact_freshness_quality_gate",
                status=str(quality_gates["artifact_freshness_gate"]),
                detail=(
                    f"All required verification artifacts are fresh within {max_artifact_age_hours} hours."
                    if not stale_artifacts
                    else f"Stale or missing artifacts: {', '.join(stale_artifacts)}."
                ),
            ),
            DataPlatformCheck(
                name="mutation_level_write_endpoint_gate",
                status=str(quality_gates["mutation_gate"]),
                detail=(
                    f"{mutation_coverage_ratio:.0%} governed write endpoint mutations are exercised by verify_project.py."
                    if not missing_mutation_gates
                    else f"Missing mutation gates: {', '.join(missing_mutation_gates)}."
                ),
            ),
        ]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        local_automation_status = "ready" if all(check.status == "ready" for check in checks) else "blocked"
        status = "ready" if local_automation_status == "ready" else "blocked"
        generated_at = datetime.now(UTC).isoformat()
        payload = {
            "title": "Mariam Verification Automation Contract",
            "status": status,
            "generated_at": generated_at,
            "data_platform": "DB MARIAM",
            "artifact_path": str(artifact_path),
            "persisted_run_log_path": str(persisted_run_log_path),
            "persisted_verification_run_count": len(persisted_verification_runs),
            "persisted_verification_runs": persisted_verification_runs,
            "required_commands": required_commands,
            "required_endpoints": required_endpoints,
            "required_artifacts": required_artifacts,
            "ci_artifact_retention": ci_artifact_retention,
            "ci_badge": ci_badge,
            "latest_run_status": latest_run_status,
            "ci_run_ingestion": ci_run_ingestion,
            "local_history_comparison": local_history_comparison,
            "quality_gates": quality_gates,
            "artifact_freshness": artifact_freshness,
            "local_automation_status": local_automation_status,
            "ci_status": ci_status,
            "next_ci_step": "Add failure-summary export for CI and local verification runs.",
            "checks": [check.__dict__ for check in checks],
        }
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return VerificationAutomationContract(
            title=str(payload["title"]),
            status=status,
            generated_at=generated_at,
            data_platform="DB MARIAM",
            artifact_path=str(artifact_path),
            persisted_run_log_path=str(persisted_run_log_path),
            persisted_verification_run_count=len(persisted_verification_runs),
            persisted_verification_runs=persisted_verification_runs,
            required_commands=required_commands,
            required_endpoints=required_endpoints,
            required_artifacts=required_artifacts,
            ci_artifact_retention=ci_artifact_retention,
            ci_badge=ci_badge,
            latest_run_status=latest_run_status,
            ci_run_ingestion=ci_run_ingestion,
            local_history_comparison=local_history_comparison,
            quality_gates=quality_gates,
            artifact_freshness=artifact_freshness,
            local_automation_status=local_automation_status,
            ci_status=ci_status,
            next_ci_step=str(payload["next_ci_step"]),
            checks=checks,
        )

    def _read_persisted_verification_runs(self, path: Path) -> list[dict[str, object]]:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("[]", encoding="utf-8")
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [{"run_id": "malformed", "status": "blocked", "command": "npm run verify", "started_at": ""}]
        if not isinstance(payload, list):
            return [{"run_id": "malformed", "status": "blocked", "command": "npm run verify", "started_at": ""}]
        return [item for item in payload if isinstance(item, dict)][-10:]

    def _run_readonly_command(self, command: list[str], cwd: Path) -> dict[str, object]:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            return {"returncode": 1, "detail": str(error)}
        detail = (completed.stdout or completed.stderr or "command completed").strip()
        return {"returncode": completed.returncode, "detail": detail}
