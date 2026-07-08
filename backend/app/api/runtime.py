from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_command_center_summary_service, get_event_bus
from app.core.events import InMemoryEventBus
from app.services.command_center import CommandCenterSummaryService

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class VerificationSnapshotRequest(BaseModel):
    actor_id: str = Field(default="command-center-verifier", min_length=2)
    evidence: dict = Field(default_factory=dict)


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


@router.get("/data-platform/readiness")
def command_center_data_platform_readiness(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.data_platform_readiness())


@router.post("/data-platform/readiness/export")
def export_command_center_data_platform_readiness(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return {"export_package": asdict(service.export_data_platform_readiness())}


@router.get("/data-platform/migration-runner")
def command_center_data_platform_migration_runner(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.migration_runner_status())


@router.post("/data-platform/migration-runner/export")
def export_command_center_data_platform_migration_runner(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return {"export_package": asdict(service.export_migration_runner_status())}


@router.get("/data-platform/seed-data")
def command_center_data_platform_seed_data(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.seed_data_status())


@router.get("/data-platform/backup-readiness")
def command_center_data_platform_backup_readiness(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.backup_readiness_status())


@router.get("/data-platform/plugin-schema-isolation")
def command_center_data_platform_plugin_schema_isolation(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.plugin_schema_isolation_status())


@router.get("/data-platform/docker-persistence")
def command_center_data_platform_docker_persistence(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.docker_persistence_status())


@router.get("/data-platform/live-db-smoke")
def command_center_data_platform_live_db_smoke(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.live_database_smoke_status())


@router.get("/data-platform/docker-container-execution")
def command_center_data_platform_docker_container_execution(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.docker_container_execution_status())


@router.post("/data-platform/live-write-smoke")
def command_center_data_platform_live_write_smoke(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.live_database_write_status())


@router.get("/frontend/regression-snapshot")
def command_center_frontend_regression_snapshot(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.frontend_regression_snapshot())


@router.get("/frontend/visual-contract")
def command_center_frontend_visual_contract(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.frontend_visual_contract())


@router.get("/verification-report")
def command_center_verification_report(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return service.verification_report().__dict__


@router.get("/verification-automation")
def command_center_verification_automation(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.verification_automation_contract())


@router.post("/verification-report/record")
def record_command_center_verification_report(
    request: VerificationSnapshotRequest,
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    audit_record = service.record_verification_snapshot(request.actor_id, request.evidence)
    return {"audit_record": audit_record.model_dump(mode="json")}


@router.get("/verification-report/snapshots")
def list_command_center_verification_snapshots(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return {
        "snapshots": [
            snapshot.model_dump(mode="json")
            for snapshot in service.list_verification_snapshots()
        ]
    }


@router.get("/diagnostics")
def command_center_diagnostics(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.diagnostics())


@router.get("/usage-guide")
def command_center_usage_guide(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.usage_guide())


@router.get("/completion-report")
def command_center_completion_report(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.completion_report())


@router.get("/implementation-roadmap")
def command_center_implementation_roadmap(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return asdict(service.implementation_roadmap())


@router.post("/implementation-roadmap/export")
def export_command_center_implementation_roadmap(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return {"export_package": asdict(service.export_implementation_roadmap())}


@router.post("/completion-report/export")
def export_command_center_completion_report(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return {"export_package": asdict(service.export_completion_report())}


@router.post("/usage-guide/export")
def export_command_center_usage_guide(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return {"export_package": asdict(service.export_usage_guide())}


@router.post("/diagnostics/export")
def export_command_center_diagnostics(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return {"export_package": asdict(service.export_diagnostics())}


@router.get("/events")
def list_events(event_bus: InMemoryEventBus = Depends(get_event_bus)) -> dict:
    return {"events": [event.__dict__ for event in event_bus.list_events()]}


@router.post("/events")
def publish_event(payload: dict, event_bus: InMemoryEventBus = Depends(get_event_bus)) -> dict:
    event = event_bus.publish(
        name=str(payload.get("name", "runtime.event")),
        source=str(payload.get("source", "api")),
        payload=dict(payload.get("payload", {})),
    )
    return {"event": event.__dict__}
