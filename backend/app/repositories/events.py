from typing import Protocol

from app.core.events import Event


class EventRepository(Protocol):
    def save(self, event: Event) -> Event:
        pass

    def list(self) -> list[Event]:
        pass


class InMemoryEventRepository:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def save(self, event: Event) -> Event:
        self._events.append(event)
        return event

    def list(self) -> list[Event]:
        return list(self._events)


class PostgresEventRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save(self, event: Event) -> Event:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
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
                        event.event_id,
                        event.name,
                        event.source,
                        Jsonb(event.payload),
                        event.created_at,
                    ),
                )
        return event

    def list(self) -> list[Event]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT event_id, name, source, payload, created_at
                    FROM runtime_events
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [
            Event(
                name=row["name"],
                source=row["source"],
                payload=dict(row["payload"]),
                event_id=str(row["event_id"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
