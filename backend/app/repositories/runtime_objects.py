from typing import Protocol

from app.core.runtime_objects import RuntimeObject


class RuntimeObjectRepository(Protocol):
    def save(self, runtime_object: RuntimeObject) -> RuntimeObject:
        pass

    def list(self) -> list[RuntimeObject]:
        pass


class InMemoryRuntimeObjectRepository:
    def __init__(self) -> None:
        self._objects: dict[str, RuntimeObject] = {}

    def save(self, runtime_object: RuntimeObject) -> RuntimeObject:
        self._objects[runtime_object.object_id] = runtime_object
        return runtime_object

    def list(self) -> list[RuntimeObject]:
        return list(self._objects.values())


class PostgresRuntimeObjectRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save(self, runtime_object: RuntimeObject) -> RuntimeObject:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO runtime_objects (
                        id,
                        object_type,
                        name,
                        status,
                        version,
                        manifest,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        runtime_object.object_id,
                        runtime_object.object_type,
                        runtime_object.name,
                        runtime_object.status,
                        runtime_object.version,
                        Jsonb(runtime_object.manifest),
                        runtime_object.created_at,
                        runtime_object.updated_at,
                    ),
                )
        return runtime_object

    def list(self) -> list[RuntimeObject]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, object_type, name, status, version, manifest, created_at, updated_at
                    FROM runtime_objects
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [
            RuntimeObject(
                object_id=str(row["id"]),
                object_type=row["object_type"],
                name=row["name"],
                status=row["status"],
                version=row["version"],
                manifest=dict(row["manifest"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
