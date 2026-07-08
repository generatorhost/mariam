from fastapi import APIRouter, Depends, HTTPException

from app.core.workflows import WorkflowDefinitionRequest, WorkflowRunRequest
from app.dependencies import get_workflow_engine_service, require_permission
from app.services.workflows import WorkflowEngineService

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("")
def list_workflows(service: WorkflowEngineService = Depends(get_workflow_engine_service)) -> dict:
    return {"workflows": [workflow.model_dump(mode="json") for workflow in service.list_definitions()]}


@router.post("")
def create_workflow(
    request: WorkflowDefinitionRequest,
    authorization=Depends(require_permission("workflow.configure", "workflow")),
    service: WorkflowEngineService = Depends(get_workflow_engine_service),
) -> dict:
    try:
        workflow = service.create_definition(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"workflow": workflow.model_dump(mode="json")}


@router.get("/runs")
def list_workflow_runs(service: WorkflowEngineService = Depends(get_workflow_engine_service)) -> dict:
    return {"workflow_runs": [run.model_dump(mode="json") for run in service.list_runs()]}


@router.post("/runs")
def run_workflow_definition(
    request: WorkflowRunRequest,
    authorization=Depends(require_permission("workflow.run", "workflow")),
    service: WorkflowEngineService = Depends(get_workflow_engine_service),
) -> dict:
    try:
        workflow_run = service.run(request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"workflow_run": workflow_run.model_dump(mode="json")}
