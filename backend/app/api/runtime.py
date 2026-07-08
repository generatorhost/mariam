from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_command_center_summary_service, get_event_bus, require_permission
from app.core.errors import api_error_contract, api_error_openapi_response_examples
from app.core.events import InMemoryEventBus
from app.services.command_center import CommandCenterSummaryService

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class VerificationSnapshotRequest(BaseModel):
    actor_id: str = Field(default="command-center-verifier", min_length=2)
    evidence: dict = Field(default_factory=dict)


class RuntimeCheckResponse(BaseModel):
    name: str
    status: str
    detail: str


class DataPlatformReadinessResponse(BaseModel):
    title: str
    status: str
    database_name: str
    database_url: str
    generated_at: str
    store_modes: dict[str, str]
    migrations_found: list[str]
    expected_tables: list[str]
    checks: list[RuntimeCheckResponse]


class DataPlatformReadinessExportResponse(BaseModel):
    export_package: dict[str, Any]


class MigrationRunnerStatusResponse(BaseModel):
    title: str
    status: str
    generated_at: str
    data_platform: str
    migration_count: int
    ordered_migrations: list[str]
    table_definitions: int
    index_definitions: int
    checks: list[RuntimeCheckResponse]


class MigrationRunnerExportResponse(BaseModel):
    export_package: dict[str, Any]


class SeedDataStatusResponse(BaseModel):
    title: str
    status: str
    generated_at: str
    data_platform: str
    seed_id: str
    seed_file: str
    item_count: int
    target_tables: list[str]
    contains_secrets: bool
    checks: list[RuntimeCheckResponse]


class BackupReadinessStatusResponse(BaseModel):
    title: str
    status: str
    generated_at: str
    data_platform: str
    policy_id: str
    policy_file: str
    scope_count: int
    retention: dict[str, str]
    contains_secrets: bool
    checks: list[RuntimeCheckResponse]


class PluginSchemaIsolationStatusResponse(BaseModel):
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
    checks: list[RuntimeCheckResponse]


class DockerPersistenceStatusResponse(BaseModel):
    title: str
    status: str
    generated_at: str
    data_platform: str
    env_file: str
    compose_file: str
    postgres_store_count: int
    database_url_masked: str
    checks: list[RuntimeCheckResponse]


class LiveDatabaseSmokeStatusResponse(BaseModel):
    title: str
    status: str
    generated_at: str
    data_platform: str
    docker_available: bool
    compose_config_valid: bool
    smoke_command: str
    checks: list[RuntimeCheckResponse]


class DockerContainerExecutionStatusResponse(BaseModel):
    title: str
    status: str
    generated_at: str
    data_platform: str
    postgres_running: bool
    pg_isready: bool
    services: list[str]
    execution_commands: list[str]
    checks: list[RuntimeCheckResponse]


class LiveDatabaseWriteStatusResponse(BaseModel):
    title: str
    status: str
    generated_at: str
    data_platform: str
    audit_id: str
    event_id: str
    audit_written: bool
    event_written: bool
    checks: list[RuntimeCheckResponse]


class LiveRepositoryWriteStatusResponse(BaseModel):
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
    checks: list[RuntimeCheckResponse]


class CompletionAreaResponse(BaseModel):
    name: str
    completion_percent: int
    status: str
    evidence: str
    next_step: str


class ProjectCompletionReportResponse(BaseModel):
    title: str
    version: str
    status: str
    completion_percent: int
    generated_at: str
    data_platform: str
    areas: list[CompletionAreaResponse]
    verification: dict[str, Any]
    usage_guide: dict[str, Any]
    summary: str


class CompletionReportExportResponse(BaseModel):
    export_package: dict[str, Any]


class ImplementationRoadmapItemResponse(BaseModel):
    area: str
    priority: str
    current_completion_percent: int
    next_step: str
    acceptance_signal: str


class ImplementationRoadmapResponse(BaseModel):
    title: str
    version: str
    status: str
    generated_at: str
    data_platform: str
    items: list[ImplementationRoadmapItemResponse]
    operating_rule: str


class ImplementationRoadmapExportResponse(BaseModel):
    export_package: dict[str, Any]


class VerificationAutomationResponse(BaseModel):
    title: str
    status: str
    generated_at: str
    data_platform: str
    artifact_path: str
    persisted_run_log_path: str
    persisted_verification_run_count: int
    persisted_verification_runs: list[dict[str, Any]]
    required_commands: list[str]
    required_endpoints: list[str]
    required_artifacts: list[str]
    ci_artifact_retention: dict[str, Any]
    ci_badge: dict[str, Any]
    latest_run_status: dict[str, Any]
    ci_run_ingestion: dict[str, Any]
    local_history_comparison: dict[str, Any]
    quality_gates: dict[str, Any]
    artifact_freshness: dict[str, Any]
    local_automation_status: str
    ci_status: str
    next_ci_step: str
    checks: list[RuntimeCheckResponse]


class DeliveryEvidenceReportResponse(BaseModel):
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
    evidence_items: list[dict[str, Any]]
    sla_items: list[dict[str, Any]]
    sla_drilldown_summary: dict[str, Any]
    sla_drilldown_items: list[dict[str, Any]]
    sla_filters: dict[str, Any]
    filtered_sla_drilldown_items: list[dict[str, Any]]
    checks: list[RuntimeCheckResponse]


class FrontendRegressionSnapshotResponse(BaseModel):
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
    checks: list[RuntimeCheckResponse]


class FrontendVisualContractResponse(BaseModel):
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
    checks: list[RuntimeCheckResponse]


class FrontendBrowserScreenshotPlanResponse(BaseModel):
    title: str
    status: str
    generated_at: str
    data_platform: str
    source_file: str
    artifact_path: str
    viewport_targets: list[dict[str, Any]]
    critical_sections: list[str]
    screenshot_artifacts: list[str]
    required_browser_checks: list[str]
    checks: list[RuntimeCheckResponse]


class FrontendBrowserScreenshotCaptureResponse(BaseModel):
    title: str
    status: str
    generated_at: str
    data_platform: str
    artifact_path: str
    artifact_count: int
    artifacts: list[dict[str, Any]]
    thumbnail_previews: list[dict[str, Any]]
    checks: list[RuntimeCheckResponse]


class VerificationReportResponse(BaseModel):
    status: str
    readiness_status: str
    ready_checks: int
    total_checks: int
    summary: dict[str, Any]
    smoke_flow: str
    required_endpoints: list[str]


class VerificationSnapshotRecordResponse(BaseModel):
    audit_record: dict[str, Any]


class VerificationSnapshotsResponse(BaseModel):
    snapshots: list[dict[str, Any]]


class DiagnosticsResponse(BaseModel):
    status: str
    generated_at: str
    data_platform: str
    verification_report: VerificationReportResponse
    readiness_checks: list[RuntimeCheckResponse]
    recent_audit_records: list[dict[str, Any]]
    recent_events: list[dict[str, Any]]


class DiagnosticsExportResponse(BaseModel):
    export_package: dict[str, Any]


class UsageGuideStepResponse(BaseModel):
    action: str
    frontend_control: str
    api_endpoint: str
    backend_handler: str
    service_effect: str
    data_platform_effect: str
    result: str
    verification_signal: str


class UsageGuideResponse(BaseModel):
    title: str
    version: str
    status: str
    data_platform: str
    generated_at: str
    operating_rule: str
    steps: list[UsageGuideStepResponse]


class UsageGuideExportResponse(BaseModel):
    export_package: dict[str, Any]


@router.get("/summary")
def command_center_summary(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return service.summarize().__dict__


@router.get("/readiness")
def command_center_readiness(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    readiness = service.readiness()
    return {
        "status": readiness.status,
        "checks": [check.__dict__ for check in readiness.checks],
    }


@router.get("/api-error-contract", responses=api_error_openapi_response_examples())
def command_center_api_error_contract() -> dict:
    return api_error_contract()


@router.get("/data-platform/readiness", response_model=DataPlatformReadinessResponse)
def command_center_data_platform_readiness(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> DataPlatformReadinessResponse:
    return asdict(service.data_platform_readiness())


@router.post("/data-platform/readiness/export", response_model=DataPlatformReadinessExportResponse)
def export_command_center_data_platform_readiness(
    authorization=Depends(require_permission("diagnostics.export", "data_platform_readiness")),
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> DataPlatformReadinessExportResponse:
    return {"export_package": asdict(service.export_data_platform_readiness())}


@router.get("/data-platform/migration-runner", response_model=MigrationRunnerStatusResponse)
def command_center_data_platform_migration_runner(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> MigrationRunnerStatusResponse:
    return asdict(service.migration_runner_status())


@router.post("/data-platform/migration-runner/export", response_model=MigrationRunnerExportResponse)
def export_command_center_data_platform_migration_runner(
    authorization=Depends(require_permission("diagnostics.export", "migration_runner")),
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> MigrationRunnerExportResponse:
    return {"export_package": asdict(service.export_migration_runner_status())}


@router.get("/data-platform/seed-data", response_model=SeedDataStatusResponse)
def command_center_data_platform_seed_data(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> SeedDataStatusResponse:
    return asdict(service.seed_data_status())


@router.get("/data-platform/backup-readiness", response_model=BackupReadinessStatusResponse)
def command_center_data_platform_backup_readiness(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> BackupReadinessStatusResponse:
    return asdict(service.backup_readiness_status())


@router.get("/data-platform/plugin-schema-isolation", response_model=PluginSchemaIsolationStatusResponse)
def command_center_data_platform_plugin_schema_isolation(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> PluginSchemaIsolationStatusResponse:
    return asdict(service.plugin_schema_isolation_status())


@router.get("/data-platform/docker-persistence", response_model=DockerPersistenceStatusResponse)
def command_center_data_platform_docker_persistence(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> DockerPersistenceStatusResponse:
    return asdict(service.docker_persistence_status())


@router.get("/data-platform/live-db-smoke", response_model=LiveDatabaseSmokeStatusResponse)
def command_center_data_platform_live_db_smoke(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> LiveDatabaseSmokeStatusResponse:
    return asdict(service.live_database_smoke_status())


@router.get("/data-platform/docker-container-execution", response_model=DockerContainerExecutionStatusResponse)
def command_center_data_platform_docker_container_execution(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> DockerContainerExecutionStatusResponse:
    return asdict(service.docker_container_execution_status())


@router.post("/data-platform/live-write-smoke", response_model=LiveDatabaseWriteStatusResponse)
def command_center_data_platform_live_write_smoke(
    authorization=Depends(require_permission("data_platform.write", "data_platform_smoke")),
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> LiveDatabaseWriteStatusResponse:
    return asdict(service.live_database_write_status())


@router.post("/data-platform/live-repository-write-smoke", response_model=LiveRepositoryWriteStatusResponse)
def command_center_data_platform_live_repository_write_smoke(
    authorization=Depends(require_permission("data_platform.write", "repository_write_smoke")),
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> LiveRepositoryWriteStatusResponse:
    return asdict(service.live_repository_write_status())


@router.get("/frontend/regression-snapshot", response_model=FrontendRegressionSnapshotResponse)
def command_center_frontend_regression_snapshot(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> FrontendRegressionSnapshotResponse:
    return asdict(service.frontend_regression_snapshot())


@router.get("/frontend/visual-contract", response_model=FrontendVisualContractResponse)
def command_center_frontend_visual_contract(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> FrontendVisualContractResponse:
    return asdict(service.frontend_visual_contract())


@router.get("/frontend/browser-screenshot-plan", response_model=FrontendBrowserScreenshotPlanResponse)
def command_center_frontend_browser_screenshot_plan(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> FrontendBrowserScreenshotPlanResponse:
    return asdict(service.frontend_browser_screenshot_plan())


@router.get("/frontend/browser-screenshot-capture", response_model=FrontendBrowserScreenshotCaptureResponse)
def command_center_frontend_browser_screenshot_capture(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> FrontendBrowserScreenshotCaptureResponse:
    return asdict(service.frontend_browser_screenshot_capture_report())


@router.get("/verification-report", response_model=VerificationReportResponse)
def command_center_verification_report(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> VerificationReportResponse:
    return service.verification_report().__dict__


@router.get("/verification-automation", response_model=VerificationAutomationResponse)
def command_center_verification_automation(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> VerificationAutomationResponse:
    return asdict(service.verification_automation_contract())


@router.get("/delivery-evidence-report", response_model=DeliveryEvidenceReportResponse)
def command_center_delivery_evidence_report(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> DeliveryEvidenceReportResponse:
    return asdict(service.delivery_evidence_report())


@router.post("/verification-report/record", response_model=VerificationSnapshotRecordResponse)
def record_command_center_verification_report(
    request: VerificationSnapshotRequest,
    authorization=Depends(require_permission("diagnostics.export", "runtime_verification_report")),
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> VerificationSnapshotRecordResponse:
    audit_record = service.record_verification_snapshot(request.actor_id, request.evidence)
    return {"audit_record": audit_record.model_dump(mode="json")}


@router.get("/verification-report/snapshots", response_model=VerificationSnapshotsResponse)
def list_command_center_verification_snapshots(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> VerificationSnapshotsResponse:
    return {
        "snapshots": [
            snapshot.model_dump(mode="json")
            for snapshot in service.list_verification_snapshots()
        ]
    }


@router.get("/diagnostics", response_model=DiagnosticsResponse)
def command_center_diagnostics(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> DiagnosticsResponse:
    return asdict(service.diagnostics())


@router.get("/usage-guide", response_model=UsageGuideResponse)
def command_center_usage_guide(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> UsageGuideResponse:
    return asdict(service.usage_guide())


@router.get("/completion-report", response_model=ProjectCompletionReportResponse)
def command_center_completion_report(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> ProjectCompletionReportResponse:
    return asdict(service.completion_report())


@router.get("/implementation-roadmap", response_model=ImplementationRoadmapResponse)
def command_center_implementation_roadmap(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> ImplementationRoadmapResponse:
    return asdict(service.implementation_roadmap())


@router.post("/implementation-roadmap/export", response_model=ImplementationRoadmapExportResponse)
def export_command_center_implementation_roadmap(
    authorization=Depends(require_permission("diagnostics.export", "implementation_roadmap")),
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> ImplementationRoadmapExportResponse:
    return {"export_package": asdict(service.export_implementation_roadmap())}


@router.post("/completion-report/export", response_model=CompletionReportExportResponse)
def export_command_center_completion_report(
    authorization=Depends(require_permission("diagnostics.export", "completion_report")),
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> CompletionReportExportResponse:
    return {"export_package": asdict(service.export_completion_report())}


@router.post("/usage-guide/export", response_model=UsageGuideExportResponse)
def export_command_center_usage_guide(
    authorization=Depends(require_permission("diagnostics.export", "usage_guide")),
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> UsageGuideExportResponse:
    return {"export_package": asdict(service.export_usage_guide())}


@router.post("/diagnostics/export", response_model=DiagnosticsExportResponse)
def export_command_center_diagnostics(
    authorization=Depends(require_permission("diagnostics.export", "runtime_diagnostics")),
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> DiagnosticsExportResponse:
    return {"export_package": asdict(service.export_diagnostics())}


@router.get("/events")
def list_events(event_bus: InMemoryEventBus = Depends(get_event_bus)) -> dict:
    return {"events": [event.__dict__ for event in event_bus.list_events()]}


@router.post("/events")
def publish_event(
    payload: dict,
    authorization=Depends(require_permission("runtime.event.publish", "runtime_event")),
    event_bus: InMemoryEventBus = Depends(get_event_bus),
) -> dict:
    event = event_bus.publish(
        name=str(payload.get("name", "runtime.event")),
        source=str(payload.get("source", "api")),
        payload=dict(payload.get("payload", {})),
    )
    return {"event": event.__dict__}
