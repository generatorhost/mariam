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
