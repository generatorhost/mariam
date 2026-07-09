from fastapi import APIRouter, Depends, HTTPException

from app.core.agents import (
    AgentExecutionDecisionRequest,
    AgentExecutionRunRequest,
    AgentMissionPlanRequest,
    AgentSocietyRequest,
)
from app.dependencies import get_agent_runtime_service, require_permission
from app.services.agents import AgentRuntimeService

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/societies")
def list_agent_societies(service: AgentRuntimeService = Depends(get_agent_runtime_service)) -> dict:
    return {"agent_societies": [society.model_dump(mode="json") for society in service.list_societies()]}


@router.post("/societies")
def create_agent_society(
    request: AgentSocietyRequest,
    authorization=Depends(require_permission("agent_runtime.configure", "agent_society")),
    service: AgentRuntimeService = Depends(get_agent_runtime_service),
) -> dict:
    society = service.create_society(request)
    return {"agent_society": society.model_dump(mode="json")}


@router.get("/executions")
def list_agent_executions(service: AgentRuntimeService = Depends(get_agent_runtime_service)) -> dict:
    return {"agent_executions": [execution.model_dump(mode="json") for execution in service.list_executions()]}


@router.post("/executions/plan")
def plan_agent_execution(
    request: AgentMissionPlanRequest,
    authorization=Depends(require_permission("mission.create", "agent_execution")),
    service: AgentRuntimeService = Depends(get_agent_runtime_service),
) -> dict:
    execution = service.plan_mission(request)
    return {"agent_execution": execution.model_dump(mode="json")}


@router.post("/executions/{execution_id}/run")
def run_agent_execution(
    execution_id: str,
    request: AgentExecutionRunRequest,
    authorization=Depends(require_permission("mission.create", "agent_execution")),
    service: AgentRuntimeService = Depends(get_agent_runtime_service),
) -> dict:
    try:
        execution = service.run_execution(execution_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"agent_execution": execution.model_dump(mode="json")}


@router.post("/executions/{execution_id}/decision")
def decide_agent_execution(
    execution_id: str,
    request: AgentExecutionDecisionRequest,
    authorization=Depends(require_permission("artifact.approve", "agent_execution")),
    service: AgentRuntimeService = Depends(get_agent_runtime_service),
) -> dict:
    try:
        execution = service.decide_execution(execution_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"agent_execution": execution.model_dump(mode="json")}
