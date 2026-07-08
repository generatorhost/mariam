from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.workflows import (
    WorkflowDefinition,
    WorkflowDefinitionRequest,
    WorkflowRun,
    WorkflowRunRequest,
    create_workflow_definition,
    run_workflow,
)
from app.repositories.workflows import WorkflowEngineRepository
from app.services.audit import AuditService


class WorkflowEngineService:
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        repository: WorkflowEngineRepository,
        audit_service: AuditService,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository
        self._audit_service = audit_service

    def create_definition(self, request: WorkflowDefinitionRequest) -> WorkflowDefinition:
        definition = create_workflow_definition(request)
        saved = self._repository.save_definition(definition)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.requested_by,
                action="workflow.define",
                target_type="workflow",
                target_id=saved.workflow_id,
                decision="recorded",
                evidence={
                    "plugin_id": saved.plugin_id,
                    "step_count": str(len(saved.steps)),
                    "data_platform": saved.data_platform,
                },
            )
        )
        self._event_bus.publish(
            "workflow.defined",
            "workflow-engine",
            {
                "workflow_id": saved.workflow_id,
                "plugin_id": saved.plugin_id,
                "step_count": len(saved.steps),
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def run(self, request: WorkflowRunRequest) -> WorkflowRun:
        definition = self._repository.get_definition(request.workflow_id)
        if definition is None:
            raise ValueError(f"Workflow {request.workflow_id} was not found.")
        run = run_workflow(definition, request)
        saved = self._repository.save_run(run)
        self._event_bus.publish(
            "workflow.run.completed" if saved.status == "completed" else "workflow.run.awaiting_approval",
            "workflow-engine",
            {
                "run_id": saved.run_id,
                "workflow_id": saved.workflow_id,
                "plugin_id": saved.plugin_id,
                "status": saved.status,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def list_definitions(self) -> list[WorkflowDefinition]:
        return self._repository.list_definitions()

    def list_runs(self) -> list[WorkflowRun]:
        return self._repository.list_runs()
