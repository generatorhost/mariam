from __future__ import annotations

import hashlib
import json

from app.core.artifacts import (
    Artifact,
    ArtifactApprovalRequest,
    ArtifactDeliveryRequest,
    ArtifactQualityReview,
    ArtifactQualityReviewRequest,
    ArtifactRejectionRequest,
    ArtifactRevisionRequest,
    ArtifactStatus,
    DeliveryConfirmationRequest,
    DeliveryPackage,
    create_artifact_quality_review,
    create_delivery_package,
    create_artifact_from_mission,
)
from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.repositories.artifacts import (
    ArtifactQualityReviewRepository,
    ArtifactRepository,
    DeliveryPackageRepository,
)
from app.services.audit import AuditService
from app.services.missions import MissionService


class ArtifactService:
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        repository: ArtifactRepository,
        delivery_repository: DeliveryPackageRepository,
        quality_review_repository: ArtifactQualityReviewRepository,
        audit_service: AuditService,
        mission_service: MissionService,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository
        self._delivery_repository = delivery_repository
        self._quality_review_repository = quality_review_repository
        self._audit_service = audit_service
        self._mission_service = mission_service

    def generate_from_mission(self, mission_id: str) -> Artifact:
        mission = next(
            (candidate for candidate in self._mission_service.list() if candidate.mission_id == mission_id),
            None,
        )
        if mission is None:
            raise ValueError(f"Mission {mission_id} was not found.")
        artifact = create_artifact_from_mission(
            mission_id=mission.mission_id,
            plugin_id=mission.plugin_id,
            user_request=mission.user_request,
        )
        saved = self._repository.save(artifact)
        self._event_bus.publish(
            "artifact.generated",
            "artifact-service",
            {
                "artifact_id": saved.artifact_id,
                "mission_id": saved.mission_id,
                "plugin_id": saved.plugin_id,
                "status": saved.status,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def approve(self, artifact_id: str, request: ArtifactApprovalRequest) -> Artifact:
        artifact = self._get(artifact_id)
        approved = artifact.model_copy(update={"status": ArtifactStatus.approved})
        saved = self._repository.update(approved)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.approved_by,
                action="artifact.approve",
                target_type="artifact",
                target_id=artifact_id,
                decision="approved",
                evidence={
                    "mission_id": saved.mission_id,
                    "plugin_id": saved.plugin_id,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "artifact.approved",
            "artifact-service",
            {
                "artifact_id": saved.artifact_id,
                "mission_id": saved.mission_id,
                "plugin_id": saved.plugin_id,
                "approved_by": request.approved_by,
                "status": saved.status,
            },
        )
        return saved

    def reject(self, artifact_id: str, request: ArtifactRejectionRequest) -> Artifact:
        artifact = self._get(artifact_id)
        rejected = artifact.model_copy(update={"status": ArtifactStatus.rejected})
        saved = self._repository.update(rejected)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.rejected_by,
                action="artifact.reject",
                target_type="artifact",
                target_id=artifact_id,
                decision="rejected",
                evidence={
                    "mission_id": saved.mission_id,
                    "plugin_id": saved.plugin_id,
                    "rejection_reason": request.reason,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "artifact.rejected",
            "artifact-service",
            {
                "artifact_id": saved.artifact_id,
                "mission_id": saved.mission_id,
                "plugin_id": saved.plugin_id,
                "rejected_by": request.rejected_by,
                "status": saved.status,
            },
        )
        return saved

    def request_revision(self, artifact_id: str, request: ArtifactRevisionRequest) -> Artifact:
        artifact = self._get(artifact_id)
        if artifact.status != ArtifactStatus.rejected:
            raise ValueError(f"Artifact {artifact_id} must be rejected before revision can be requested.")
        revised = artifact.model_copy(
            update={
                "status": ArtifactStatus.awaiting_approval,
                "content": (
                    f"{artifact.content}\n\nRevision requested: {request.revision_request}. "
                    "Delivery remains blocked until governance approval."
                ),
            }
        )
        saved = self._repository.update(revised)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.requested_by,
                action="artifact.request_revision",
                target_type="artifact",
                target_id=artifact_id,
                decision="approved",
                evidence={
                    "mission_id": saved.mission_id,
                    "plugin_id": saved.plugin_id,
                    "revision_request": request.revision_request,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "artifact.revision_requested",
            "artifact-service",
            {
                "artifact_id": saved.artifact_id,
                "mission_id": saved.mission_id,
                "plugin_id": saved.plugin_id,
                "requested_by": request.requested_by,
                "status": saved.status,
            },
        )
        return saved

    def package_for_delivery(self, artifact_id: str, request: ArtifactDeliveryRequest) -> DeliveryPackage:
        artifact = self._get(artifact_id)
        if artifact.status != ArtifactStatus.approved:
            raise ValueError(f"Artifact {artifact_id} must be approved before delivery packaging.")
        quality_review = self._quality_review_repository.latest_for_artifact(artifact_id)
        if quality_review is None or not quality_review.passed:
            raise ValueError(f"Artifact {artifact_id} must pass quality review before delivery packaging.")
        delivery_package = create_delivery_package(artifact, request.destination)
        evidence_bundle = {
            "artifact_id": artifact.artifact_id,
            "mission_id": artifact.mission_id,
            "plugin_id": artifact.plugin_id,
            "quality_review_id": quality_review.review_id,
            "quality_score": quality_review.score,
            "destination": request.destination,
            "data_platform": artifact.data_platform,
        }
        evidence_signature = self._sign_evidence_bundle(evidence_bundle)
        delivery_package.package_manifest.update(
            {
                "quality_review_id": quality_review.review_id,
                "quality_score": quality_review.score,
                "evidence_bundle": evidence_bundle,
                "evidence_signature": evidence_signature,
                "evidence_signature_algorithm": "sha256",
                "evidence_signed": True,
            }
        )
        saved_delivery = self._delivery_repository.save(delivery_package)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.packaged_by,
                action="artifact.package_delivery",
                target_type="artifact",
                target_id=artifact_id,
                decision="approved",
                evidence={
                    "delivery_id": saved_delivery.delivery_id,
                    "mission_id": saved_delivery.mission_id,
                    "plugin_id": saved_delivery.plugin_id,
                    "destination": saved_delivery.destination,
                    "evidence_signature": evidence_signature,
                    "data_platform": saved_delivery.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "artifact.delivery_packaged",
            "artifact-service",
            {
                "delivery_id": saved_delivery.delivery_id,
                "artifact_id": saved_delivery.artifact_id,
                "mission_id": saved_delivery.mission_id,
                "plugin_id": saved_delivery.plugin_id,
                "destination": saved_delivery.destination,
                "status": saved_delivery.status,
            },
        )
        return saved_delivery

    def list(self) -> list[Artifact]:
        return self._repository.list()

    def list_delivery_packages(self) -> list[DeliveryPackage]:
        return self._delivery_repository.list()

    def review_quality(
        self,
        artifact_id: str,
        request: ArtifactQualityReviewRequest,
    ) -> ArtifactQualityReview:
        artifact = self._get(artifact_id)
        review = create_artifact_quality_review(artifact)
        saved_review = self._quality_review_repository.save(review)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.reviewed_by,
                action="artifact.quality_review",
                target_type="artifact",
                target_id=artifact_id,
                decision="approved" if saved_review.passed else "rejected",
                evidence={
                    "review_id": saved_review.review_id,
                    "mission_id": saved_review.mission_id,
                    "plugin_id": saved_review.plugin_id,
                    "score": str(saved_review.score),
                    "data_platform": saved_review.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "artifact.quality_reviewed",
            "artifact-service",
            {
                "review_id": saved_review.review_id,
                "artifact_id": saved_review.artifact_id,
                "mission_id": saved_review.mission_id,
                "plugin_id": saved_review.plugin_id,
                "passed": saved_review.passed,
                "score": saved_review.score,
            },
        )
        return saved_review

    def list_quality_reviews(self) -> list[ArtifactQualityReview]:
        return self._quality_review_repository.list()

    def confirm_delivery(
        self,
        delivery_id: str,
        request: DeliveryConfirmationRequest,
    ) -> DeliveryPackage:
        delivery_package = self._delivery_repository.get(delivery_id)
        if delivery_package is None:
            raise ValueError(f"Delivery package {delivery_id} was not found.")
        if delivery_package.status != "ready_for_client_delivery":
            raise ValueError(
                f"Delivery package {delivery_id} must be ready_for_client_delivery before confirmation."
            )
        self._verify_delivery_signature(delivery_package)
        confirmed = delivery_package.model_copy(
            update={
                "status": "delivered_to_client",
                "package_manifest": {
                    **delivery_package.package_manifest,
                    "client_reference": request.client_reference,
                    "delivered_by": request.delivered_by,
                    "delivery_confirmed": True,
                    "delivery_confirmation_requires_signature": True,
                },
            }
        )
        saved_delivery = self._delivery_repository.update(confirmed)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.delivered_by,
                action="artifact.confirm_delivery",
                target_type="delivery_package",
                target_id=delivery_id,
                decision="approved",
                evidence={
                    "artifact_id": saved_delivery.artifact_id,
                    "mission_id": saved_delivery.mission_id,
                    "plugin_id": saved_delivery.plugin_id,
                    "client_reference": request.client_reference,
                    "evidence_signature": saved_delivery.package_manifest["evidence_signature"],
                    "data_platform": saved_delivery.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "artifact.delivery_confirmed",
            "artifact-service",
            {
                "delivery_id": saved_delivery.delivery_id,
                "artifact_id": saved_delivery.artifact_id,
                "mission_id": saved_delivery.mission_id,
                "plugin_id": saved_delivery.plugin_id,
                "client_reference": request.client_reference,
                "status": saved_delivery.status,
            },
        )
        return saved_delivery

    def _sign_evidence_bundle(self, evidence_bundle: dict) -> str:
        canonical_payload = json.dumps(evidence_bundle, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    def _verify_delivery_signature(self, delivery_package: DeliveryPackage) -> None:
        evidence_bundle = delivery_package.package_manifest.get("evidence_bundle")
        evidence_signature = delivery_package.package_manifest.get("evidence_signature")
        if not isinstance(evidence_bundle, dict) or not isinstance(evidence_signature, str):
            raise ValueError(
                f"Delivery package {delivery_package.delivery_id} must include a signed evidence bundle before confirmation."
            )
        expected_signature = self._sign_evidence_bundle(evidence_bundle)
        if evidence_signature != expected_signature:
            raise ValueError(
                f"Delivery package {delivery_package.delivery_id} has an invalid evidence bundle signature."
            )

    def _get(self, artifact_id: str) -> Artifact:
        artifact = self._repository.get(artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact {artifact_id} was not found.")
        return artifact
