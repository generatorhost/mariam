from fastapi import APIRouter, Depends, HTTPException

from app.core.remote_execution import (
    RemoteExecutionCommandRequest,
    RemoteExecutionJob,
    RemoteExecutionManifest,
)
from app.dependencies import get_remote_execution_commander_service, require_permission
from app.services.remote_execution import RemoteExecutionCommanderService

router = APIRouter(
    prefix="/api/plugins/remote-execution-commander",
    tags=["remote-execution-commander"],
)


@router.get("/manifest", response_model=RemoteExecutionManifest)
def get_remote_execution_manifest(
    service: RemoteExecutionCommanderService = Depends(get_remote_execution_commander_service),
) -> RemoteExecutionManifest:
    return service.manifest()


@router.get("/jobs", response_model=list[RemoteExecutionJob])
def list_remote_execution_jobs(
    service: RemoteExecutionCommanderService = Depends(get_remote_execution_commander_service),
) -> list[RemoteExecutionJob]:
    return service.list_jobs()


@router.get("/jobs/{job_id}", response_model=RemoteExecutionJob)
def get_remote_execution_job(
    job_id: str,
    service: RemoteExecutionCommanderService = Depends(get_remote_execution_commander_service),
) -> RemoteExecutionJob:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Remote execution job {job_id} was not found.")
    return job


@router.post("/commands", response_model=RemoteExecutionJob)
def run_remote_execution_command(
    request: RemoteExecutionCommandRequest,
    authorization=Depends(require_permission("diagnostics.export", "remote_execution_command")),
    service: RemoteExecutionCommanderService = Depends(get_remote_execution_commander_service),
) -> RemoteExecutionJob:
    return service.run_command(request)
