from typing import Protocol

from app.core.audit import AuditRecord


class AuditRepository(Protocol):
    def save(self, record: AuditRecord) -> AuditRecord:
        pass

    def list(self) -> list[AuditRecord]:
        pass


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def save(self, record: AuditRecord) -> AuditRecord:
        self._records.append(record)
        return record

    def list(self) -> list[AuditRecord]:
        return list(self._records)


class PostgresAuditRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save(self, record: AuditRecord) -> AuditRecord:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_log (
                        audit_id,
                        actor_id,
                        action,
                        target_type,
                        target_id,
                        decision,
                        evidence,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.audit_id,
                        record.actor_id,
                        record.action,
                        record.target_type,
                        record.target_id,
                        record.decision,
                        Jsonb(record.evidence),
                        record.created_at,
                    ),
                )
        return record

    def list(self) -> list[AuditRecord]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT audit_id, actor_id, action, target_type, target_id, decision, evidence, created_at
                    FROM audit_log
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [
            AuditRecord(
                audit_id=str(row["audit_id"]),
                actor_id=row["actor_id"],
                action=row["action"],
                target_type=row["target_type"],
                target_id=row["target_id"],
                decision=row["decision"],
                evidence=dict(row["evidence"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
