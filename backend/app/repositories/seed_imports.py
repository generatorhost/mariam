from typing import Protocol

from app.core.seed_imports import SeedImportRecord


class SeedImportRepository(Protocol):
    def save(self, record: SeedImportRecord) -> SeedImportRecord:
        pass

    def get(self, source_id: str) -> SeedImportRecord | None:
        pass

    def list(self) -> list[SeedImportRecord]:
        pass


class InMemorySeedImportRepository:
    def __init__(self) -> None:
        self._records: dict[str, SeedImportRecord] = {}

    def save(self, record: SeedImportRecord) -> SeedImportRecord:
        self._records[record.source_id] = record
        return record

    def get(self, source_id: str) -> SeedImportRecord | None:
        return self._records.get(source_id)

    def list(self) -> list[SeedImportRecord]:
        return list(self._records.values())


class PostgresSeedImportRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save(self, record: SeedImportRecord) -> SeedImportRecord:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO seed_import_records (
                        source_id,
                        source_path,
                        source_name,
                        status,
                        record,
                        imported_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_id)
                    DO UPDATE SET
                        source_path = EXCLUDED.source_path,
                        source_name = EXCLUDED.source_name,
                        status = EXCLUDED.status,
                        record = EXCLUDED.record,
                        imported_at = EXCLUDED.imported_at
                    """,
                    (
                        record.source_id,
                        record.source_path,
                        record.source_name,
                        record.status,
                        Jsonb(record.model_dump(mode="json")),
                        record.imported_at,
                    ),
                )
        return record

    def get(self, source_id: str) -> SeedImportRecord | None:
        return next((record for record in self.list() if record.source_id == source_id), None)

    def list(self) -> list[SeedImportRecord]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT record
                    FROM seed_import_records
                    ORDER BY imported_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [SeedImportRecord.model_validate(row["record"]) for row in rows]
