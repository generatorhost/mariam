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


@router.get("/verification-report")
def command_center_verification_report(
    service: CommandCenterSummaryService = Depends(get_command_center_summary_service),
) -> dict:
    return service.verification_report().__dict__


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
