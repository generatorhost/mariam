from fastapi import APIRouter, Depends, HTTPException

from app.core.artifacts import (
    ArtifactApprovalRequest,
    ArtifactDeliveryRequest,
    ArtifactQualityReviewRequest,
    ArtifactRejectionRequest,
    DeliveryConfirmationRequest,
)
from app.dependencies import get_artifact_service
from app.services.artifacts import ArtifactService

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("")
def list_artifacts(service: ArtifactService = Depends(get_artifact_service)) -> dict:
    return {"artifacts": [artifact.model_dump(mode="json") for artifact in service.list()]}


@router.get("/deliveries")
def list_delivery_packages(service: ArtifactService = Depends(get_artifact_service)) -> dict:
    return {
        "delivery_packages": [
            delivery_package.model_dump(mode="json")
            for delivery_package in service.list_delivery_packages()
        ]
    }


@router.get("/quality-reviews")
def list_quality_reviews(service: ArtifactService = Depends(get_artifact_service)) -> dict:
    return {
        "quality_reviews": [
            quality_review.model_dump(mode="json")
            for quality_review in service.list_quality_reviews()
        ]
    }


@router.post("/deliveries/{delivery_id}/confirm")
def confirm_delivery_package(
    delivery_id: str,
    request: DeliveryConfirmationRequest,
    service: ArtifactService = Depends(get_artifact_service),
) -> dict:
    try:
        delivery_package = service.confirm_delivery(delivery_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"delivery_package": delivery_package.model_dump(mode="json")}


@router.post("/from-mission/{mission_id}")
def generate_artifact_from_mission(
    mission_id: str,
    service: ArtifactService = Depends(get_artifact_service),
) -> dict:
    try:
        artifact = service.generate_from_mission(mission_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"artifact": artifact.model_dump(mode="json")}


@router.post("/{artifact_id}/quality-review")
def review_artifact_quality(
    artifact_id: str,
    request: ArtifactQualityReviewRequest,
    service: ArtifactService = Depends(get_artifact_service),
) -> dict:
    try:
        quality_review = service.review_quality(artifact_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"quality_review": quality_review.model_dump(mode="json")}


@router.post("/{artifact_id}/approve")
def approve_artifact(
    artifact_id: str,
    request: ArtifactApprovalRequest,
    service: ArtifactService = Depends(get_artifact_service),
) -> dict:
    try:
        artifact = service.approve(artifact_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"artifact": artifact.model_dump(mode="json")}


@router.post("/{artifact_id}/reject")
def reject_artifact(
    artifact_id: str,
    request: ArtifactRejectionRequest,
    service: ArtifactService = Depends(get_artifact_service),
) -> dict:
    try:
        artifact = service.reject(artifact_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"artifact": artifact.model_dump(mode="json")}


@router.post("/{artifact_id}/package-delivery")
def package_artifact_delivery(
    artifact_id: str,
    request: ArtifactDeliveryRequest,
    service: ArtifactService = Depends(get_artifact_service),
) -> dict:
    try:
        delivery_package = service.package_for_delivery(artifact_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"delivery_package": delivery_package.model_dump(mode="json")}
