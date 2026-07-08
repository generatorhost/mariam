from fastapi import APIRouter, Depends

from app.dependencies import get_command_center_summary_service, get_event_bus
from app.core.events import InMemoryEventBus
from app.services.command_center import CommandCenterSummaryService

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


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
