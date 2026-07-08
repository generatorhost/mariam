from typing import Protocol

from app.core.data_records import (
    CapabilityGraphRecord,
    CommunicationRecord,
    DocumentRecord,
    WorkflowRecord,
)


class CommunicationRecordRepository(Protocol):
    def ensure_schema(self) -> None:
        pass

    def save(self, record: CommunicationRecord) -> CommunicationRecord:
        pass

    def exists(self, record_id: str, status: str = "recorded") -> bool:
        pass


class DocumentRecordRepository(Protocol):
    def ensure_schema(self) -> None:
        pass

    def save(self, record: DocumentRecord) -> DocumentRecord:
        pass

    def exists(self, document_id: str, artifact_id: str) -> bool:
        pass


class WorkflowRecordRepository(Protocol):
    def ensure_schema(self) -> None:
        pass

    def save(self, record: WorkflowRecord) -> WorkflowRecord:
        pass

    def exists(self, workflow_id: str, status: str = "active") -> bool:
        pass


class CapabilityGraphRecordRepository(Protocol):
    def ensure_schema(self) -> None:
        pass

    def save(self, record: CapabilityGraphRecord) -> CapabilityGraphRecord:
        pass

    def exists(self, capability_id: str, status: str = "available") -> bool:
        pass


class CursorCommunicationRecordRepository:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def ensure_schema(self) -> None:
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS communication_records (
                record_id UUID PRIMARY KEY,
                channel TEXT NOT NULL,
                direction TEXT NOT NULL,
                participant TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    def save(self, record: CommunicationRecord) -> CommunicationRecord:
        from psycopg.types.json import Jsonb

        self._cursor.execute(
            """
            INSERT INTO communication_records (
                record_id,
                channel,
                direction,
                participant,
                subject,
                message,
                status,
                data_platform,
                metadata,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.record_id,
                record.channel,
                record.direction,
                record.participant,
                record.subject,
                record.message,
                record.status,
                record.data_platform,
                Jsonb(record.metadata),
                record.created_at,
            ),
        )
        return record

    def exists(self, record_id: str, status: str = "recorded") -> bool:
        self._cursor.execute(
            """
            SELECT record_id
            FROM communication_records
            WHERE record_id = %s AND data_platform = %s AND status = %s
            """,
            (record_id, "DB MARIAM", status),
        )
        return self._cursor.fetchone() is not None


class CursorDocumentRecordRepository:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def ensure_schema(self) -> None:
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS document_records (
                document_id UUID PRIMARY KEY,
                artifact_id UUID REFERENCES artifacts (artifact_id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                document_type TEXT NOT NULL,
                storage_uri TEXT NOT NULL,
                status TEXT NOT NULL,
                data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    def save(self, record: DocumentRecord) -> DocumentRecord:
        from psycopg.types.json import Jsonb

        self._cursor.execute(
            """
            INSERT INTO document_records (
                document_id,
                artifact_id,
                title,
                document_type,
                storage_uri,
                status,
                data_platform,
                metadata,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.document_id,
                record.artifact_id,
                record.title,
                record.document_type,
                record.storage_uri,
                record.status,
                record.data_platform,
                Jsonb(record.metadata),
                record.created_at,
            ),
        )
        return record

    def exists(self, document_id: str, artifact_id: str) -> bool:
        self._cursor.execute(
            """
            SELECT document_id
            FROM document_records
            WHERE document_id = %s AND artifact_id = %s AND data_platform = %s
            """,
            (document_id, artifact_id, "DB MARIAM"),
        )
        return self._cursor.fetchone() is not None


class CursorWorkflowRecordRepository:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def ensure_schema(self) -> None:
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_records (
                workflow_id UUID PRIMARY KEY,
                plugin_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                steps JSONB NOT NULL DEFAULT '[]'::jsonb,
                data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    def save(self, record: WorkflowRecord) -> WorkflowRecord:
        from psycopg.types.json import Jsonb

        self._cursor.execute(
            """
            INSERT INTO workflow_records (
                workflow_id,
                plugin_id,
                name,
                status,
                steps,
                data_platform,
                metadata,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.workflow_id,
                record.plugin_id,
                record.name,
                record.status,
                Jsonb(record.steps),
                record.data_platform,
                Jsonb(record.metadata),
                record.created_at,
            ),
        )
        return record

    def exists(self, workflow_id: str, status: str = "active") -> bool:
        self._cursor.execute(
            """
            SELECT workflow_id
            FROM workflow_records
            WHERE workflow_id = %s AND data_platform = %s AND status = %s
            """,
            (workflow_id, "DB MARIAM", status),
        )
        return self._cursor.fetchone() is not None


class CursorCapabilityGraphRecordRepository:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def ensure_schema(self) -> None:
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS capability_graph_records (
                capability_id UUID PRIMARY KEY,
                name TEXT NOT NULL,
                capability_type TEXT NOT NULL,
                status TEXT NOT NULL,
                nodes JSONB NOT NULL DEFAULT '[]'::jsonb,
                edges JSONB NOT NULL DEFAULT '[]'::jsonb,
                data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    def save(self, record: CapabilityGraphRecord) -> CapabilityGraphRecord:
        from psycopg.types.json import Jsonb

        self._cursor.execute(
            """
            INSERT INTO capability_graph_records (
                capability_id,
                name,
                capability_type,
                status,
                nodes,
                edges,
                data_platform,
                metadata,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.capability_id,
                record.name,
                record.capability_type,
                record.status,
                Jsonb(record.nodes),
                Jsonb(record.edges),
                record.data_platform,
                Jsonb(record.metadata),
                record.created_at,
            ),
        )
        return record

    def exists(self, capability_id: str, status: str = "available") -> bool:
        self._cursor.execute(
            """
            SELECT capability_id
            FROM capability_graph_records
            WHERE capability_id = %s AND data_platform = %s AND status = %s
            """,
            (capability_id, "DB MARIAM", status),
        )
        return self._cursor.fetchone() is not None
