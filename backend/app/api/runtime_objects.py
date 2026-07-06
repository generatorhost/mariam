from fastapi import APIRouter, Depends, HTTPException

from app.core.runtime_objects import (
    RuntimeObjectDNAImportRequest,
    RuntimeObjectImpactRequest,
    RuntimeObjectPatchRequest,
    RuntimeObjectRequest,
    RuntimeObjectStateChangeRequest,
)
from app.dependencies import get_runtime_object_service
from app.services.runtime_objects import RuntimeObjectService

router = APIRouter(prefix="/api/runtime-objects", tags=["runtime-objects"])


@router.get("")
def list_runtime_objects(service: RuntimeObjectService = Depends(get_runtime_object_service)) -> dict:
    return {"runtime_objects": [runtime_object.model_dump(mode="json") for runtime_object in service.list()]}


@router.post("")
def create_runtime_object(
    request: RuntimeObjectRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    runtime_object = service.create(request)
    return {"runtime_object": runtime_object.model_dump(mode="json")}


@router.post("/import-dna")
def import_runtime_object_dna(
    request: RuntimeObjectDNAImportRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    try:
        runtime_object = service.import_dna(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"runtime_object": runtime_object.model_dump(mode="json")}


@router.patch("/{object_id}")
def patch_runtime_object(
    object_id: str,
    request: RuntimeObjectPatchRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    try:
        runtime_object = service.patch(object_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"runtime_object": runtime_object.model_dump(mode="json")}


@router.post("/{object_id}/enable")
def enable_runtime_object(
    object_id: str,
    request: RuntimeObjectStateChangeRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    try:
        runtime_object = service.enable(object_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"runtime_object": runtime_object.model_dump(mode="json")}


@router.post("/{object_id}/disable")
def disable_runtime_object(
    object_id: str,
    request: RuntimeObjectStateChangeRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    try:
        runtime_object = service.disable(object_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"runtime_object": runtime_object.model_dump(mode="json")}


@router.post("/{object_id}/delete")
def soft_delete_runtime_object(
    object_id: str,
    request: RuntimeObjectStateChangeRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    try:
        runtime_object = service.soft_delete(object_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"runtime_object": runtime_object.model_dump(mode="json")}


@router.post("/{object_id}/restore")
def restore_runtime_object(
    object_id: str,
    request: RuntimeObjectStateChangeRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    try:
        runtime_object = service.restore(object_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"runtime_object": runtime_object.model_dump(mode="json")}


@router.post("/{object_id}/rollback")
def rollback_runtime_object(
    object_id: str,
    request: RuntimeObjectStateChangeRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    try:
        runtime_object = service.rollback(object_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"runtime_object": runtime_object.model_dump(mode="json")}


@router.post("/{object_id}/export-dna")
def export_runtime_object_dna(
    object_id: str,
    request: RuntimeObjectStateChangeRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    try:
        dna_package = service.export_dna(object_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"dna_package": dna_package.model_dump(mode="json")}


@router.post("/{object_id}/validate")
def validate_runtime_object(
    object_id: str,
    request: RuntimeObjectStateChangeRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    try:
        validation_report = service.validate(object_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"validation_report": validation_report.model_dump(mode="json")}


@router.post("/{object_id}/impact-analysis")
def analyze_runtime_object_impact(
    object_id: str,
    request: RuntimeObjectImpactRequest,
    service: RuntimeObjectService = Depends(get_runtime_object_service),
) -> dict:
    try:
        impact_report = service.analyze_impact(object_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"impact_report": impact_report.model_dump(mode="json")}
