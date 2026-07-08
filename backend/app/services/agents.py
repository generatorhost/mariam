from app.core.agents import (
    AgentExecutionPlan,
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

    def list_societies(self) -> list[AgentSociety]:
        return self._repository.list_societies()

    def list_executions(self) -> list[AgentExecutionPlan]:
        return self._repository.list_executions()
