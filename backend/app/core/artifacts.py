from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class ArtifactStatus(StrEnum):
    awaiting_approval = "awaiting_approval"
    approved = "approved"
    rejected = "rejected"


class ArtifactApprovalRequest(BaseModel):
    approved_by: str = Field(default="artifact-governance", min_length=2)
    evidence: dict[str, str] = Field(default_factory=dict)


class ArtifactRejectionRequest(BaseModel):
    rejected_by: str = Field(default="artifact-governance", min_length=2)
    reason: str = Field(min_length=3)
    evidence: dict[str, str] = Field(default_factory=dict)


class ArtifactDeliveryRequest(BaseModel):
    packaged_by: str = Field(default="delivery-governance", min_length=2)
    destination: str = Field(default="client-review-channel", min_length=3)
    evidence: dict[str, str] = Field(default_factory=dict)


class DeliveryConfirmationRequest(BaseModel):
    delivered_by: str = Field(default="delivery-governance", min_length=2)
    client_reference: str = Field(default="client-confirmed-receipt", min_length=3)
    evidence: dict[str, str] = Field(default_factory=dict)


class Artifact(BaseModel):
    artifact_id: str
    mission_id: str
    plugin_id: str
    title: str
    content: str
    status: ArtifactStatus
    data_platform: str = "DB MARIAM"
    created_at: datetime


class DeliveryPackage(BaseModel):
    delivery_id: str
    artifact_id: str
    mission_id: str
    plugin_id: str
    destination: str
    status: str
    package_manifest: dict
    data_platform: str = "DB MARIAM"
    created_at: datetime


def create_artifact_from_mission(
    mission_id: str,
    plugin_id: str,
    user_request: str,
) -> Artifact:
    return Artifact(
        artifact_id=str(uuid4()),
        mission_id=mission_id,
        plugin_id=plugin_id,
        title=f"{plugin_id.upper()} Mission Artifact",
        content=(
            "Draft client artifact generated for review. "
            f"Mission request: {user_request}. "
            "Delivery is blocked until governance approval."
        ),
        status=ArtifactStatus.awaiting_approval,
        created_at=datetime.now(UTC),
    )


def create_delivery_package(artifact: Artifact, destination: str) -> DeliveryPackage:
    return DeliveryPackage(
        delivery_id=str(uuid4()),
        artifact_id=artifact.artifact_id,
        mission_id=artifact.mission_id,
        plugin_id=artifact.plugin_id,
        destination=destination,
        status="ready_for_client_delivery",
        package_manifest={
            "title": artifact.title,
            "content_length": len(artifact.content),
            "requires_client_delivery_record": True,
            "source_artifact_status": artifact.status,
        },
        created_at=datetime.now(UTC),
    )
