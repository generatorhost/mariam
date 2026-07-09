from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentRole(StrEnum):
    chief = "chief"
    team_leader = "team_leader"
    agent = "agent"
    reviewer = "reviewer"
    validator = "validator"


class AgentStatus(StrEnum):
    candidate = "candidate"
    active = "active"
    disabled = "disabled"


class AgentSocietyRequest(BaseModel):
    plugin_id: str = Field(min_length=2)
    business_unit_name: str = Field(min_length=3)
    requested_by: str = Field(default="agent-runtime-governance", min_length=2)
    chief_title: str | None = None
    team_domains: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)


class AgentMissionPlanRequest(BaseModel):
    plugin_id: str = Field(min_length=2)
    user_request: str = Field(min_length=3)
    requested_by: str = Field(default="local-user", min_length=2)
    priority: str = "normal"


class AgentExecutionRunRequest(BaseModel):
    actor_id: str = Field(default="agent-runtime-chief", min_length=2)
    reason: str = Field(default="Run governed agent execution plan.", min_length=5)
    evidence: dict = Field(default_factory=dict)


class AgentExecutionDecisionRequest(BaseModel):
    decided_by: str = Field(default="human-governance-reviewer", min_length=2)
    decision: str = Field(pattern="^(approved|changes_requested|rejected)$")
    reason: str = Field(min_length=5)
    evidence: dict = Field(default_factory=dict)


class AgentExecutionSchedule(BaseModel):
    execution_id: str
    status: str
    ready_task_ids: list[str]
    blocked_task_ids: list[str]
    approval_task_ids: list[str]
    completed_task_ids: list[str]
    task_dependencies: dict[str, list[str]]
    scheduler_notes: list[str]
    data_platform: str = "DB MARIAM"


class AgentRuntimeNode(BaseModel):
    node_id: str
    plugin_id: str
    role: AgentRole
    title: str
    reports_to: str | None
    skills: list[str]
    capabilities: list[str]
    permissions: list[str]
    status: AgentStatus
    data_boundary: str


class AgentTask(BaseModel):
    task_id: str
    title: str
    assigned_to: str
    depends_on: list[str]
    status: str
    expected_output: str
    governance_gate: str


class AgentSociety(BaseModel):
    society_id: str
    plugin_id: str
    business_unit_name: str
    chief_node_id: str
    nodes: list[AgentRuntimeNode]
    data_platform: str = "DB MARIAM"
    created_at: datetime


class AgentExecutionPlan(BaseModel):
    execution_id: str
    plugin_id: str
    user_request: str
    requested_by: str
    chief_node_id: str
    tasks: list[AgentTask]
    communication_channels: list[str]
    review_gates: list[str]
    status: str
    data_platform: str = "DB MARIAM"
    created_at: datetime


def create_agent_society(request: AgentSocietyRequest) -> AgentSociety:
    society_id = str(uuid4())
    safe_plugin = request.plugin_id.replace("-", "_")
    chief_id = f"{safe_plugin}_chief"
    domains = request.team_domains or ["planning", "execution", "review"]
    base_skills = request.skills or ["mission_planning", "task_routing", "artifact_review"]
    capabilities = request.capabilities or ["governed_execution", "plugin_coordination"]
    nodes = [
        AgentRuntimeNode(
            node_id=chief_id,
            plugin_id=request.plugin_id,
            role=AgentRole.chief,
            title=request.chief_title or f"{request.business_unit_name} Chief Agent",
            reports_to="mariam_enterprise_chief",
            skills=["strategic_planning", "governance_routing", *base_skills],
            capabilities=["business_unit_leadership", *capabilities],
            permissions=[f"{request.plugin_id}.mission.plan", f"{request.plugin_id}.task.assign"],
            status=AgentStatus.active,
            data_boundary=f"{safe_plugin}_agent_runtime",
        )
    ]
    for domain in domains:
        leader_id = f"{safe_plugin}_{domain}_leader"
        nodes.append(
            AgentRuntimeNode(
                node_id=leader_id,
                plugin_id=request.plugin_id,
                role=AgentRole.team_leader,
                title=f"{domain.replace('_', ' ').title()} Team Leader",
                reports_to=chief_id,
                skills=[domain, "team_coordination"],
                capabilities=[f"{domain}_coordination"],
                permissions=[f"{request.plugin_id}.{domain}.assign"],
                status=AgentStatus.active,
                data_boundary=f"{safe_plugin}_agent_runtime",
            )
        )
        nodes.append(
            AgentRuntimeNode(
                node_id=f"{safe_plugin}_{domain}_worker",
                plugin_id=request.plugin_id,
                role=AgentRole.agent,
                title=f"{domain.replace('_', ' ').title()} Agent",
                reports_to=leader_id,
                skills=[domain],
                capabilities=[f"{domain}_execution"],
                permissions=[f"{request.plugin_id}.{domain}.execute"],
                status=AgentStatus.active,
                data_boundary=f"{safe_plugin}_agent_runtime",
            )
        )
    nodes.append(
        AgentRuntimeNode(
            node_id=f"{safe_plugin}_quality_reviewer",
            plugin_id=request.plugin_id,
            role=AgentRole.reviewer,
            title="Quality Reviewer Agent",
            reports_to=chief_id,
            skills=["quality_review", "acceptance_check"],
            capabilities=["artifact_review"],
            permissions=[f"{request.plugin_id}.artifact.review"],
            status=AgentStatus.active,
            data_boundary=f"{safe_plugin}_agent_runtime",
        )
    )
    return AgentSociety(
        society_id=society_id,
        plugin_id=request.plugin_id,
        business_unit_name=request.business_unit_name,
        chief_node_id=chief_id,
        nodes=nodes,
        created_at=datetime.now(UTC),
    )


def create_agent_execution_plan(
    request: AgentMissionPlanRequest,
    society: AgentSociety,
) -> AgentExecutionPlan:
    chief_task_id = str(uuid4())
    breakdown_task_id = str(uuid4())
    execution_task_id = str(uuid4())
    review_task_id = str(uuid4())
    tasks = [
        AgentTask(
            task_id=chief_task_id,
            title="Chief intent analysis",
            assigned_to=society.chief_node_id,
            depends_on=[],
            status="planned",
            expected_output="Mission objective, risks, required capabilities, and governance path.",
            governance_gate="permission_and_scope_check",
        ),
        AgentTask(
            task_id=breakdown_task_id,
            title="Team leader task breakdown",
            assigned_to=next(node.node_id for node in society.nodes if node.role == AgentRole.team_leader),
            depends_on=[chief_task_id],
            status="planned",
            expected_output="Task graph with accountable agents and delivery evidence.",
            governance_gate="task_graph_review",
        ),
        AgentTask(
            task_id=execution_task_id,
            title="Agent execution package",
            assigned_to=next(node.node_id for node in society.nodes if node.role == AgentRole.agent),
            depends_on=[breakdown_task_id],
            status="planned",
            expected_output="Draft artifact or service action result ready for review.",
            governance_gate="sandbox_before_side_effect",
        ),
        AgentTask(
            task_id=review_task_id,
            title="Quality and governance review",
            assigned_to=next(node.node_id for node in society.nodes if node.role == AgentRole.reviewer),
            depends_on=[execution_task_id],
            status="planned",
            expected_output="Approve, reject, or request changes before delivery.",
            governance_gate="human_approval_before_delivery",
        ),
    ]
    return AgentExecutionPlan(
        execution_id=str(uuid4()),
        plugin_id=request.plugin_id,
        user_request=request.user_request,
        requested_by=request.requested_by,
        chief_node_id=society.chief_node_id,
        tasks=tasks,
        communication_channels=["chief_chat", "team_room", "audit_events"],
        review_gates=["permission", "scope", "quality", "security", "human_approval"],
        status="planned",
        created_at=datetime.now(UTC),
    )
