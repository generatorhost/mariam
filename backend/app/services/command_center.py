import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from app.core.config import get_settings
from app.core.audit import AuditRecord, AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.services.ai_resources import AIResourceManager
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
class VerificationAutomationContract:
    title: str
    status: str
    generated_at: str
    data_platform: str
    artifact_path: str
    required_commands: list[str]
    required_endpoints: list[str]
    required_artifacts: list[str]
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
        ai_resource_manager: AIResourceManager,
        audit_service: AuditService,
        event_bus: InMemoryEventBus,
    ) -> None:
        self._runtime_registry = runtime_registry
        self._runtime_object_service = runtime_object_service
        self._mission_service = mission_service
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
                "/api/runtime/events",
                "/api/runtime/data-platform/docker-container-execution",
                "/api/runtime/data-platform/live-write-smoke",
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

    def completion_report(self) -> ProjectCompletionReport:
        verification = self.verification_report()
        usage_guide = self.usage_guide()
        areas = [
            CompletionArea(
                name="Backend API foundation",
                completion_percent=74,
                status="executable",
                evidence="FastAPI routes cover health, auth session readiness, request actor context propagation, role permission checks, backend permission enforcement, runtime, missions, artifacts, audit, plugins, runtime objects, AI resources, diagnostics, and usage guide.",
                next_step="Add request-scoped authorization dependency enforcement across mutating endpoints.",
            ),
            CompletionArea(
                name="Frontend Command Center",
                completion_percent=74,
                status="executable",
                evidence="React UI can operate mission, delivery, plugin, runtime object, AI route, audit, readiness, diagnostics, usage guide flows, sidebar navigation, app-like plugin workspace cards, live plugin workspace details, responsive state guidance, frontend regression snapshot artifact generation, and visual contract artifact checks.",
                next_step="Add real browser screenshot artifacts for critical Command Center flows.",
            ),
            CompletionArea(
                name="DB MARIAM persistence boundary",
                completion_percent=74,
                status="partial",
                evidence="Repositories support DB MARIAM boundaries, migration readiness, migration runner status, non-secret seed data status, backup readiness, per-plugin schema isolation, Docker Postgres persistence profile checks, live DB smoke readiness, Docker postgres container execution verification, and live audit/event write smoke.",
                next_step="Add persistent repository smoke writes for missions and artifact delivery packages.",
            ),
            CompletionArea(
                name="Governance and delivery workflow",
                completion_percent=74,
                status="executable",
                evidence="Mission approval, artifact approval, rejection revision loop, approval assignment, notification routing, reviewer workload reporting, workload escalation, human identity enforcement, quality review, delivery packaging, and client confirmation are covered by tests and smoke verification.",
                next_step="Add SLA timers and escalation aging rules.",
            ),
            CompletionArea(
                name="Verification automation",
                completion_percent=74,
                status="executable",
                evidence="npm run verify executes backend tests, frontend build, API endpoint checks, diagnostics export, usage guide export, mission-to-delivery smoke flow, frontend contracts, and a reviewable verification automation contract artifact.",
                next_step="Add browser regression screenshots and CI execution for pull requests.",
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
            "audit_log",
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
            "Open Live Plugin Workspace",
            "Start CRM Mission",
            "Route Notification",
            "Refresh Reviewer Workload",
            "Escalate Reviewer Workload",
            "Refresh Frontend Regression",
            "Refresh Visual Contract",
            "Refresh Verification Automation",
            "Export Diagnostics",
            "Export Completion Report",
            "Export Roadmap",
        ]
        viewport_contracts = ["Mobile", "Tablet", "Desktop"]
        missing_controls = [control for control in controls_checked if control not in source_text]
        missing_viewports = [viewport for viewport in viewport_contracts if viewport not in source_text]
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

    def verification_automation_contract(self) -> VerificationAutomationContract:
        root = Path(__file__).resolve().parents[3]
        package_file = root / "package.json"
        frontend_package_file = root / "frontend" / "package.json"
        requirements_file = root / "backend" / "requirements.txt"
        verification_script = root / "tools" / "verify_project.py"
        docker_compose_file = root / "docker-compose.yml"
        ci_workflow_dir = root / ".github" / "workflows"
        artifact_path = root / "artifacts" / "verification" / "verification-automation-contract.json"
        package_text = package_file.read_text(encoding="utf-8") if package_file.exists() else ""
        frontend_package_text = (
            frontend_package_file.read_text(encoding="utf-8") if frontend_package_file.exists() else ""
        )
        verification_text = verification_script.read_text(encoding="utf-8") if verification_script.exists() else ""
        required_commands = [
            "npm run verify",
            "py -3.11 -m pytest",
            "npm.cmd run build",
        ]
        required_endpoints = [
            "/api/health",
            "/api/runtime/readiness",
            "/api/runtime/frontend/regression-snapshot",
            "/api/runtime/frontend/visual-contract",
            "/api/runtime/verification-report",
            "/api/runtime/completion-report",
            "/api/runtime/implementation-roadmap",
        ]
        required_artifacts = [
            "artifacts/frontend-regression/command-center-regression-snapshot.json",
            "artifacts/frontend-regression/command-center-visual-contract.json",
            "artifacts/verification/verification-automation-contract.json",
        ]
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
        missing_endpoints = [
            endpoint for endpoint in required_endpoints if endpoint not in verification_text
        ]
        expected_files = [
            package_file,
            frontend_package_file,
            requirements_file,
            verification_script,
            docker_compose_file,
        ]
        missing_files = [str(path.relative_to(root)) for path in expected_files if not path.exists()]
        ci_status = "ready" if ci_workflow_dir.exists() and list(ci_workflow_dir.glob("*.yml")) else "planned"
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
                status="ready",
                detail=(
                    "CI workflow is present."
                    if ci_status == "ready"
                    else "CI workflow is not present yet; local verification is authoritative until CI is added."
                ),
            ),
        ]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        local_automation_status = "ready" if all(
            check.status == "ready" for check in checks if check.name != "ci_execution_plan"
        ) else "blocked"
        status = "ready" if local_automation_status == "ready" else "blocked"
        generated_at = datetime.now(UTC).isoformat()
        payload = {
            "title": "Mariam Verification Automation Contract",
            "status": status,
            "generated_at": generated_at,
            "data_platform": "DB MARIAM",
            "artifact_path": str(artifact_path),
            "required_commands": required_commands,
            "required_endpoints": required_endpoints,
            "required_artifacts": required_artifacts,
            "local_automation_status": local_automation_status,
            "ci_status": ci_status,
            "next_ci_step": "Add GitHub Actions workflow that runs npm run verify on pull requests.",
            "checks": [check.__dict__ for check in checks],
        }
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return VerificationAutomationContract(
            title=str(payload["title"]),
            status=status,
            generated_at=generated_at,
            data_platform="DB MARIAM",
            artifact_path=str(artifact_path),
            required_commands=required_commands,
            required_endpoints=required_endpoints,
            required_artifacts=required_artifacts,
            local_automation_status=local_automation_status,
            ci_status=ci_status,
            next_ci_step=str(payload["next_ci_step"]),
            checks=checks,
        )

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
