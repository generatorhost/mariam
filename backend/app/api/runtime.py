from fastapi import APIRouter, Depends

from app.dependencies import get_event_bus
from app.core.events import InMemoryEventBus

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


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
