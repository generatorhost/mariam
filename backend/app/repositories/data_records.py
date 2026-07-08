from typing import Protocol

from app.core.data_records import (
    ArtifactStoreRecord,
    AuditEventArchiveRecord,
    CapabilityGraphRecord,
    CommunicationRecord,
    DocumentRecord,
    MetricsStoreRecord,
    VectorIndexRecord,
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


class VectorIndexRecordRepository(Protocol):
    def ensure_schema(self) -> None:
        pass

    def save(self, record: VectorIndexRecord) -> VectorIndexRecord:
        pass

    def exists(self, vector_id: str, artifact_id: str) -> bool:
        pass


class ArtifactStoreRecordRepository(Protocol):
    def ensure_schema(self) -> None:
        pass

    def save(self, record: ArtifactStoreRecord) -> ArtifactStoreRecord:
        pass

    def exists(self, store_id: str, artifact_id: str, status: str = "stored") -> bool:
        pass


class AuditEventArchiveRecordRepository(Protocol):
    def ensure_schema(self) -> None:
        pass

    def save(self, record: AuditEventArchiveRecord) -> AuditEventArchiveRecord:
        pass

    def exists(self, archive_id: str, audit_id: str, event_id: str) -> bool:
        pass


class MetricsStoreRecordRepository(Protocol):
    def ensure_schema(self) -> None:
        pass

    def save(self, record: MetricsStoreRecord) -> MetricsStoreRecord:
        pass

    def exists(self, metric_id: str, metric_name: str, status: str = "recorded") -> bool:
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


class CursorVectorIndexRecordRepository:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def ensure_schema(self) -> None:
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vector_index_records (
                vector_id UUID PRIMARY KEY,
                artifact_id UUID REFERENCES artifacts (artifact_id) ON DELETE SET NULL,
                namespace TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                status TEXT NOT NULL,
                vector_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    def save(self, record: VectorIndexRecord) -> VectorIndexRecord:
        from psycopg.types.json import Jsonb

        self._cursor.execute(
            """
            INSERT INTO vector_index_records (
                vector_id,
                artifact_id,
                namespace,
                embedding_model,
                dimensions,
                status,
                vector_metadata,
                data_platform,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.vector_id,
                record.artifact_id,
                record.namespace,
                record.embedding_model,
                record.dimensions,
                record.status,
                Jsonb(record.vector_metadata),
                record.data_platform,
                record.created_at,
            ),
        )
        return record

    def exists(self, vector_id: str, artifact_id: str) -> bool:
        self._cursor.execute(
            """
            SELECT vector_id
            FROM vector_index_records
            WHERE vector_id = %s AND artifact_id = %s AND data_platform = %s
            """,
            (vector_id, artifact_id, "DB MARIAM"),
        )
        return self._cursor.fetchone() is not None


class CursorArtifactStoreRecordRepository:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def ensure_schema(self) -> None:
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS artifact_store_records (
                store_id UUID PRIMARY KEY,
                artifact_id UUID REFERENCES artifacts (artifact_id) ON DELETE SET NULL,
                storage_provider TEXT NOT NULL,
                storage_uri TEXT NOT NULL,
                checksum TEXT NOT NULL,
                content_type TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    def save(self, record: ArtifactStoreRecord) -> ArtifactStoreRecord:
        from psycopg.types.json import Jsonb

        self._cursor.execute(
            """
            INSERT INTO artifact_store_records (
                store_id,
                artifact_id,
                storage_provider,
                storage_uri,
                checksum,
                content_type,
                status,
                metadata,
                data_platform,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.store_id,
                record.artifact_id,
                record.storage_provider,
                record.storage_uri,
                record.checksum,
                record.content_type,
                record.status,
                Jsonb(record.metadata),
                record.data_platform,
                record.created_at,
            ),
        )
        return record

    def exists(self, store_id: str, artifact_id: str, status: str = "stored") -> bool:
        self._cursor.execute(
            """
            SELECT store_id
            FROM artifact_store_records
            WHERE store_id = %s AND artifact_id = %s AND data_platform = %s AND status = %s
            """,
            (store_id, artifact_id, "DB MARIAM", status),
        )
        return self._cursor.fetchone() is not None


class CursorAuditEventArchiveRecordRepository:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def ensure_schema(self) -> None:
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_event_archive_records (
                archive_id UUID PRIMARY KEY,
                audit_id UUID REFERENCES audit_log (audit_id) ON DELETE SET NULL,
                event_id UUID REFERENCES runtime_events (event_id) ON DELETE SET NULL,
                action TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                archive_reason TEXT NOT NULL,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    def save(self, record: AuditEventArchiveRecord) -> AuditEventArchiveRecord:
        from psycopg.types.json import Jsonb

        self._cursor.execute(
            """
            INSERT INTO audit_event_archive_records (
                archive_id,
                audit_id,
                event_id,
                action,
                actor_id,
                target_type,
                target_id,
                decision,
                archive_reason,
                payload,
                data_platform,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.archive_id,
                record.audit_id,
                record.event_id,
                record.action,
                record.actor_id,
                record.target_type,
                record.target_id,
                record.decision,
                record.archive_reason,
                Jsonb(record.payload),
                record.data_platform,
                record.created_at,
            ),
        )
        return record

    def exists(self, archive_id: str, audit_id: str, event_id: str) -> bool:
        self._cursor.execute(
            """
            SELECT archive_id
            FROM audit_event_archive_records
            WHERE archive_id = %s AND audit_id = %s AND event_id = %s AND data_platform = %s
            """,
            (archive_id, audit_id, event_id, "DB MARIAM"),
        )
        return self._cursor.fetchone() is not None


class CursorMetricsStoreRecordRepository:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def ensure_schema(self) -> None:
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics_store_records (
                metric_id UUID PRIMARY KEY,
                metric_name TEXT NOT NULL,
                metric_value DOUBLE PRECISION NOT NULL,
                metric_unit TEXT NOT NULL,
                source TEXT NOT NULL,
                dimensions JSONB NOT NULL DEFAULT '{}'::jsonb,
                status TEXT NOT NULL,
                data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    def save(self, record: MetricsStoreRecord) -> MetricsStoreRecord:
        from psycopg.types.json import Jsonb

        self._cursor.execute(
            """
            INSERT INTO metrics_store_records (
                metric_id,
                metric_name,
                metric_value,
                metric_unit,
                source,
                dimensions,
                status,
                data_platform,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record.metric_id,
                record.metric_name,
                record.metric_value,
                record.metric_unit,
                record.source,
                Jsonb(record.dimensions),
                record.status,
                record.data_platform,
                record.created_at,
            ),
        )
        return record

    def exists(self, metric_id: str, metric_name: str, status: str = "recorded") -> bool:
        self._cursor.execute(
            """
            SELECT metric_id
            FROM metrics_store_records
            WHERE metric_id = %s AND metric_name = %s AND data_platform = %s AND status = %s
            """,
            (metric_id, metric_name, "DB MARIAM", status),
        )
        return self._cursor.fetchone() is not None
