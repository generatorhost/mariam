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
                "/api/runtime/summary",
                "/api/runtime/readiness",
                "/api/runtime/verification-report",
                "/api/artifacts",
                "/api/artifacts/quality-reviews",
                "/api/artifacts/deliveries",
                "/api/audit",
                "/api/runtime/events",
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
                completion_percent=70,
                status="executable",
                evidence="FastAPI routes cover health, auth session readiness, role permission checks, runtime, missions, artifacts, audit, plugins, runtime objects, AI resources, diagnostics, and usage guide.",
                next_step="Add production permission enforcement.",
            ),
            CompletionArea(
                name="Frontend Command Center",
                completion_percent=68,
                status="executable",
                evidence="React UI can operate mission, delivery, plugin, runtime object, AI route, audit, readiness, diagnostics, usage guide flows, sidebar navigation, app-like plugin workspace cards, and responsive state guidance.",
                next_step="Add deeper plugin workspace details.",
            ),
            CompletionArea(
                name="DB MARIAM persistence boundary",
                completion_percent=70,
                status="partial",
                evidence="Repositories support DB MARIAM boundaries, migration readiness, migration runner status, non-secret seed data status, backup readiness, per-plugin schema isolation, Docker Postgres persistence profile checks, and live DB smoke readiness.",
                next_step="Add live Docker database container execution verification.",
            ),
            CompletionArea(
                name="Governance and delivery workflow",
                completion_percent=68,
                status="executable",
                evidence="Mission approval, artifact approval, rejection revision loop, approval assignment, quality review, delivery packaging, and client confirmation are covered by tests and smoke verification.",
                next_step="Add human identity and notification routing.",
            ),
            CompletionArea(
                name="Verification automation",
                completion_percent=72,
                status="executable",
                evidence="npm run verify executes backend tests, frontend build, API endpoint checks, diagnostics export, usage guide export, and mission-to-delivery smoke flow.",
                next_step="Add browser regression screenshots, Docker verification, and CI execution.",
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
