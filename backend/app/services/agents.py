from app.core.agents import (
    AgentExecutionDecisionRequest,
    AgentExecutionPlan,
    AgentExecutionRunRequest,
    AgentMissionPlanRequest,
    AgentSociety,
    AgentSocietyRequest,
    create_agent_execution_plan,
    create_agent_society,
)
from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.repositories.agents import AgentRuntimeRepository
from app.services.audit import AuditService


class AgentRuntimeService:
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        repository: AgentRuntimeRepository,
        audit_service: AuditService,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository
        self._audit_service = audit_service

    def create_society(self, request: AgentSocietyRequest) -> AgentSociety:
        society = create_agent_society(request)
        saved = self._repository.save_society(society)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.requested_by,
                action="agent_society.create",
                target_type="agent_society",
                target_id=saved.society_id,
                decision="recorded",
                evidence={
                    "plugin_id": saved.plugin_id,
                    "chief_node_id": saved.chief_node_id,
                    "node_count": str(len(saved.nodes)),
                    "data_platform": saved.data_platform,
                },
            )
        )
        self._event_bus.publish(
            "agent_society.created",
            "agent-runtime",
            {
                "society_id": saved.society_id,
                "plugin_id": saved.plugin_id,
                "chief_node_id": saved.chief_node_id,
                "node_count": len(saved.nodes),
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def plan_mission(self, request: AgentMissionPlanRequest) -> AgentExecutionPlan:
        society = self._repository.get_society_by_plugin(request.plugin_id)
        if society is None:
            society = self.create_society(
                AgentSocietyRequest(
                    plugin_id=request.plugin_id,
                    business_unit_name=f"{request.plugin_id.title()} Business Unit",
                    requested_by="agent-runtime-autoboot",
                )
            )
        execution = create_agent_execution_plan(request, society)
        saved = self._repository.save_execution(execution)
        self._event_bus.publish(
            "agent_execution.planned",
            "agent-runtime",
            {
                "execution_id": saved.execution_id,
                "plugin_id": saved.plugin_id,
                "chief_node_id": saved.chief_node_id,
                "task_count": len(saved.tasks),
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def run_execution(self, execution_id: str, request: AgentExecutionRunRequest) -> AgentExecutionPlan:
        execution = self._repository.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Agent execution {execution_id} was not found.")
        if execution.status in {"completed", "awaiting_approval"}:
            return execution

        updated_tasks = []
        for task in execution.tasks:
            next_status = "awaiting_human_approval" if task.governance_gate == "human_approval_before_delivery" else "completed"
            updated_tasks.append(
                task.model_copy(
                    update={
                        "status": next_status,
                    }
                )
            )
        next_execution_status = (
            "awaiting_approval"
            if any(task.status == "awaiting_human_approval" for task in updated_tasks)
            else "completed"
        )
        updated_execution = execution.model_copy(
            update={
                "tasks": updated_tasks,
                "status": next_execution_status,
            }
        )
        saved = self._repository.update_execution(updated_execution)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="agent_execution.run",
                target_type="agent_execution",
                target_id=saved.execution_id,
                decision="recorded",
                evidence={
                    "plugin_id": saved.plugin_id,
                    "status": saved.status,
                    "completed_tasks": str(sum(1 for task in saved.tasks if task.status == "completed")),
                    "awaiting_human_approval": str(
                        sum(1 for task in saved.tasks if task.status == "awaiting_human_approval")
                    ),
                    "reason": request.reason,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "agent_execution.ran",
            "agent-runtime",
            {
                "execution_id": saved.execution_id,
                "plugin_id": saved.plugin_id,
                "status": saved.status,
                "completed_tasks": sum(1 for task in saved.tasks if task.status == "completed"),
                "awaiting_human_approval": sum(
                    1 for task in saved.tasks if task.status == "awaiting_human_approval"
                ),
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def decide_execution(self, execution_id: str, request: AgentExecutionDecisionRequest) -> AgentExecutionPlan:
        execution = self._repository.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Agent execution {execution_id} was not found.")
        if execution.status != "awaiting_approval":
            raise ValueError(f"Agent execution {execution_id} is not awaiting approval.")

        final_task_status = {
            "approved": "approved",
            "changes_requested": "changes_requested",
            "rejected": "rejected",
        }[request.decision]
        execution_status = "completed" if request.decision == "approved" else request.decision
        updated_tasks = [
            task.model_copy(update={"status": final_task_status})
            if task.status == "awaiting_human_approval"
            else task
            for task in execution.tasks
        ]
        updated_execution = execution.model_copy(
            update={
                "tasks": updated_tasks,
                "status": execution_status,
            }
        )
        saved = self._repository.update_execution(updated_execution)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.decided_by,
                action="agent_execution.review_decision",
                target_type="agent_execution",
                target_id=saved.execution_id,
                decision=request.decision,
                evidence={
                    "plugin_id": saved.plugin_id,
                    "status": saved.status,
                    "reason": request.reason,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "agent_execution.review_decided",
            "agent-runtime",
            {
                "execution_id": saved.execution_id,
                "plugin_id": saved.plugin_id,
                "decision": request.decision,
                "status": saved.status,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def list_societies(self) -> list[AgentSociety]:
        return self._repository.list_societies()

    def list_executions(self) -> list[AgentExecutionPlan]:
        return self._repository.list_executions()
