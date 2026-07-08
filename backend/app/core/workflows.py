from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class WorkflowRunStatus(StrEnum):
    planned = "planned"
    running = "running"
    awaiting_approval = "awaiting_approval"
    completed = "completed"
    failed = "failed"


class WorkflowStepDefinition(BaseModel):
    step_key: str = Field(min_length=2)
    title: str = Field(min_length=3)
    agent_role: str = Field(min_length=2)
    action: str = Field(min_length=3)
    requires_approval: bool = False


class WorkflowDefinitionRequest(BaseModel):
    plugin_id: str = Field(min_length=2)
    name: str = Field(min_length=3)
    requested_by: str = Field(default="workflow-governance", min_length=2)
    steps: list[WorkflowStepDefinition]
    permissions: list[str] = Field(default_factory=list)


class WorkflowRunRequest(BaseModel):
    workflow_id: str = Field(min_length=3)
    mission_id: str | None = None
    requested_by: str = Field(default="command-center-user", min_length=2)
    input_payload: dict = Field(default_factory=dict)


class WorkflowStepRun(BaseModel):
    step_run_id: str
    step_key: str
    title: str
    agent_role: str
    action: str
    status: str
    output: dict
    requires_approval: bool


class WorkflowDefinition(BaseModel):
    workflow_id: str
    plugin_id: str
    name: str
    status: str
    steps: list[WorkflowStepDefinition]
    permissions: list[str]
    data_platform: str = "DB MARIAM"
    created_at: datetime


class WorkflowRun(BaseModel):
    run_id: str
    workflow_id: str
    plugin_id: str
    mission_id: str | None
    requested_by: str
    status: WorkflowRunStatus
    input_payload: dict
    step_runs: list[WorkflowStepRun]
    data_platform: str = "DB MARIAM"
    created_at: datetime


def create_workflow_definition(request: WorkflowDefinitionRequest) -> WorkflowDefinition:
    if not request.steps:
        raise ValueError("Workflow must contain at least one step.")
    return WorkflowDefinition(
        workflow_id=f"workflow-{uuid4()}",
        plugin_id=request.plugin_id,
        name=request.name,
        status="active",
        steps=request.steps,
        permissions=request.permissions,
        created_at=datetime.now(UTC),
    )


def run_workflow(definition: WorkflowDefinition, request: WorkflowRunRequest) -> WorkflowRun:
    step_runs = [
        WorkflowStepRun(
            step_run_id=f"step-run-{uuid4()}",
            step_key=step.step_key,
            title=step.title,
            agent_role=step.agent_role,
            action=step.action,
            status="awaiting_approval" if step.requires_approval else "completed",
            output={
                "executed_by": step.agent_role,
                "action": step.action,
                "governed": True,
                "data_platform": "DB MARIAM",
            },
            requires_approval=step.requires_approval,
        )
        for step in definition.steps
    ]
    status = (
        WorkflowRunStatus.awaiting_approval
        if any(step.requires_approval for step in definition.steps)
        else WorkflowRunStatus.completed
    )
    return WorkflowRun(
        run_id=f"workflow-run-{uuid4()}",
        workflow_id=definition.workflow_id,
        plugin_id=definition.plugin_id,
        mission_id=request.mission_id,
        requested_by=request.requested_by,
        status=status,
        input_payload=request.input_payload,
        step_runs=step_runs,
        created_at=datetime.now(UTC),
    )
