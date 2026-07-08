from datetime import UTC, datetime

from pydantic import BaseModel, Field


class CommunicationRecord(BaseModel):
    record_id: str
    channel: str
    direction: str
    participant: str
    subject: str
    message: str
    status: str = "recorded"
    data_platform: str = "DB MARIAM"
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DocumentRecord(BaseModel):
    document_id: str
    artifact_id: str
    title: str
    document_type: str
    storage_uri: str
    status: str = "indexed"
    data_platform: str = "DB MARIAM"
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowRecord(BaseModel):
    workflow_id: str
    plugin_id: str
    name: str
    status: str = "active"
    steps: list[dict[str, object]] = Field(default_factory=list)
    data_platform: str = "DB MARIAM"
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CapabilityGraphRecord(BaseModel):
    capability_id: str
    name: str
    capability_type: str
    status: str = "available"
    nodes: list[dict[str, object]] = Field(default_factory=list)
    edges: list[dict[str, object]] = Field(default_factory=list)
    data_platform: str = "DB MARIAM"
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VectorIndexRecord(BaseModel):
    vector_id: str
    artifact_id: str
    namespace: str
    embedding_model: str
    dimensions: int
    status: str = "indexed"
    vector_metadata: dict[str, object] = Field(default_factory=dict)
    data_platform: str = "DB MARIAM"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ArtifactStoreRecord(BaseModel):
    store_id: str
    artifact_id: str
    storage_provider: str
    storage_uri: str
    checksum: str
    content_type: str
    status: str = "stored"
    metadata: dict[str, object] = Field(default_factory=dict)
    data_platform: str = "DB MARIAM"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditEventArchiveRecord(BaseModel):
    archive_id: str
    audit_id: str
    event_id: str
    action: str
    actor_id: str
    target_type: str
    target_id: str
    decision: str
    archive_reason: str
    payload: dict[str, object] = Field(default_factory=dict)
    data_platform: str = "DB MARIAM"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MetricsStoreRecord(BaseModel):
    metric_id: str
    metric_name: str
    metric_value: float
    metric_unit: str
    source: str
    dimensions: dict[str, object] = Field(default_factory=dict)
    status: str = "recorded"
    data_platform: str = "DB MARIAM"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
