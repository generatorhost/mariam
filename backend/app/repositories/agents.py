from __future__ import annotations

from typing import Protocol

from app.core.agents import AgentExecutionPlan, AgentSociety


class AgentRuntimeRepository(Protocol):
    def save_society(self, society: AgentSociety) -> AgentSociety:
        pass

    def get_society_by_plugin(self, plugin_id: str) -> AgentSociety | None:
        pass

    def list_societies(self) -> list[AgentSociety]:
        pass

    def save_execution(self, execution: AgentExecutionPlan) -> AgentExecutionPlan:
        pass

    def list_executions(self) -> list[AgentExecutionPlan]:
        pass


class InMemoryAgentRuntimeRepository:
    def __init__(self) -> None:
        self._societies: dict[str, AgentSociety] = {}
        self._executions: dict[str, AgentExecutionPlan] = {}

    def save_society(self, society: AgentSociety) -> AgentSociety:
        self._societies[society.plugin_id] = society
        return society

    def get_society_by_plugin(self, plugin_id: str) -> AgentSociety | None:
        return self._societies.get(plugin_id)

    def list_societies(self) -> list[AgentSociety]:
        return list(self._societies.values())

    def save_execution(self, execution: AgentExecutionPlan) -> AgentExecutionPlan:
        self._executions[execution.execution_id] = execution
        return execution

    def list_executions(self) -> list[AgentExecutionPlan]:
        return list(self._executions.values())


class PostgresAgentRuntimeRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save_society(self, society: AgentSociety) -> AgentSociety:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_societies (
                        society_id,
                        plugin_id,
                        business_unit_name,
                        chief_node_id,
                        nodes,
                        data_platform,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (plugin_id) DO UPDATE
                    SET business_unit_name = EXCLUDED.business_unit_name,
                        chief_node_id = EXCLUDED.chief_node_id,
                        nodes = EXCLUDED.nodes,
                        data_platform = EXCLUDED.data_platform
                    """,
                    (
                        society.society_id,
                        society.plugin_id,
                        society.business_unit_name,
                        society.chief_node_id,
                        Jsonb([node.model_dump(mode="json") for node in society.nodes]),
                        society.data_platform,
                        society.created_at,
                    ),
                )
        return society

    def get_society_by_plugin(self, plugin_id: str) -> AgentSociety | None:
        return next((society for society in self.list_societies() if society.plugin_id == plugin_id), None)

    def list_societies(self) -> list[AgentSociety]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT society_id, plugin_id, business_unit_name, chief_node_id, nodes, data_platform, created_at
                    FROM agent_societies
                    WHERE data_platform = %s
                    ORDER BY created_at DESC
                    """,
                    ("DB MARIAM",),
                )
                rows = cursor.fetchall()
        return [AgentSociety(**dict(row)) for row in rows]

    def save_execution(self, execution: AgentExecutionPlan) -> AgentExecutionPlan:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_execution_plans (
                        execution_id,
                        plugin_id,
                        user_request,
                        requested_by,
                        chief_node_id,
                        tasks,
                        communication_channels,
                        review_gates,
                        status,
                        data_platform,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        execution.execution_id,
                        execution.plugin_id,
                        execution.user_request,
                        execution.requested_by,
                        execution.chief_node_id,
                        Jsonb([task.model_dump(mode="json") for task in execution.tasks]),
                        execution.communication_channels,
                        execution.review_gates,
                        execution.status,
                        execution.data_platform,
                        execution.created_at,
                    ),
                )
        return execution

    def list_executions(self) -> list[AgentExecutionPlan]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        execution_id,
                        plugin_id,
                        user_request,
                        requested_by,
                        chief_node_id,
                        tasks,
                        communication_channels,
                        review_gates,
                        status,
                        data_platform,
                        created_at
                    FROM agent_execution_plans
                    WHERE data_platform = %s
                    ORDER BY created_at DESC
                    """,
                    ("DB MARIAM",),
                )
                rows = cursor.fetchall()
        return [AgentExecutionPlan(**dict(row)) for row in rows]
