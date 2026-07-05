from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class RuntimeObjectRequest(BaseModel):
    object_type: str = Field(min_length=2)
    name: str = Field(min_length=2)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    manifest: dict = Field(default_factory=dict)


class RuntimeObject(BaseModel):
    object_id: str
    object_type: str
    name: str
    status: str
    version: str
    manifest: dict
    data_platform: str = "DB MARIAM"
    created_at: datetime
    updated_at: datetime


def create_runtime_object(request: RuntimeObjectRequest) -> RuntimeObject:
    now = datetime.now(UTC)
    return RuntimeObject(
        object_id=str(uuid4()),
        object_type=request.object_type,
        name=request.name,
        status="enabled",
        version=request.version,
        manifest=request.manifest,
        created_at=now,
        updated_at=now,
    )
