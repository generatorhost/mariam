from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class RuntimeObjectRequest(BaseModel):
    object_type: str = Field(min_length=2)
    name: str = Field(min_length=2)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    manifest: dict = Field(default_factory=dict)


class RuntimeObjectStateChangeRequest(BaseModel):
    actor_id: str = Field(default="runtime-governance", min_length=2)
    reason: str = Field(default="Governed runtime object state change.", min_length=5)
    evidence: dict = Field(default_factory=dict)


class RuntimeObjectPatchRequest(BaseModel):
    actor_id: str = Field(default="runtime-governance", min_length=2)
    reason: str = Field(default="Governed runtime object update.", min_length=5)
    name: str | None = Field(default=None, min_length=2)
    version: str | None = Field(default=None, pattern=r"^\d+\.\d+\.\d+$")
    manifest_updates: dict = Field(default_factory=dict)
    evidence: dict = Field(default_factory=dict)


class RuntimeObjectDNAPackage(BaseModel):
    dna_package_id: str
    source_object_id: str
    object_type: str
    name: str
    version: str
    exported_at: datetime
    payload: dict
    data_platform: str = "DB MARIAM"


class RuntimeObjectDNAImportRequest(BaseModel):
    actor_id: str = Field(default="runtime-governance", min_length=2)
    reason: str = Field(default="Governed runtime object DNA import.", min_length=5)
    dna_package: RuntimeObjectDNAPackage
    evidence: dict = Field(default_factory=dict)


class RuntimeObjectValidationReport(BaseModel):
    validation_id: str
    object_id: str
    status: str
    passed: bool
    checks: list[dict]
    validated_at: datetime
    data_platform: str = "DB MARIAM"


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
