from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4


@dataclass(frozen=True)
class Event:
    name: str
    source: str
    payload: dict[str, Any]
    event_id: str
    created_at: datetime


class EventStore(Protocol):
    def save(self, event: Event) -> Event:
        pass

    def list(self) -> list[Event]:
        pass


class InMemoryEventBus:
    def __init__(self, store: EventStore) -> None:
        self._store = store

    def publish(self, name: str, source: str, payload: dict[str, Any] | None = None) -> Event:
        event = Event(
            name=name,
            source=source,
            payload=payload or {},
            event_id=str(uuid4()),
            created_at=datetime.now(UTC),
        )
        return self._store.save(event)

    def list_events(self) -> list[Event]:
        return self._store.list()
