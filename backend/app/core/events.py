from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Event:
    name: str
    source: str
    payload: dict[str, Any]
    event_id: str
    created_at: datetime


class InMemoryEventBus:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def publish(self, name: str, source: str, payload: dict[str, Any] | None = None) -> Event:
        event = Event(
            name=name,
            source=source,
            payload=payload or {},
            event_id=str(uuid4()),
            created_at=datetime.now(UTC),
        )
        self._events.append(event)
        return event

    def list_events(self) -> list[Event]:
        return list(self._events)

