from __future__ import annotations

from typing import Protocol

from app.core.workflows import WorkflowDefinition, WorkflowRun


class WorkflowEngineRepository(Protocol):
    def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        pass

    def get_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        pass

    def list_definitions(self) -> list[WorkflowDefinition]:
        pass

    def save_run(self, run: WorkflowRun) -> WorkflowRun:
        pass

    def list_runs(self) -> list[WorkflowRun]:
        pass


class InMemoryWorkflowEngineRepository:
    def __init__(self) -> None:
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._runs: dict[str, WorkflowRun] = {}

    def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        self._definitions[definition.workflow_id] = definition
        return definition

    def get_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._definitions.get(workflow_id)

    def list_definitions(self) -> list[WorkflowDefinition]:
        return list(self._definitions.values())

    def save_run(self, run: WorkflowRun) -> WorkflowRun:
        self._runs[run.run_id] = run
        return run

    def list_runs(self) -> list[WorkflowRun]:
        return list(self._runs.values())


class PostgresWorkflowEngineRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO workflow_definitions (
                        workflow_id, plugin_id, name, status, steps, permissions, data_platform, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        definition.workflow_id,
                        definition.plugin_id,
                        definition.name,
                        definition.status,
                        Jsonb([step.model_dump(mode="json") for step in definition.steps]),
                        definition.permissions,
                        definition.data_platform,
                        definition.created_at,
                    ),
                )
        return definition

    def get_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        return next((definition for definition in self.list_definitions() if definition.workflow_id == workflow_id), None)

    def list_definitions(self) -> list[WorkflowDefinition]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT workflow_id, plugin_id, name, status, steps, permissions, data_platform, created_at
                    FROM workflow_definitions
                    WHERE data_platform = %s
                    ORDER BY created_at DESC
                    """,
                    ("DB MARIAM",),
                )
                rows = cursor.fetchall()
        return [WorkflowDefinition(**dict(row)) for row in rows]

    def save_run(self, run: WorkflowRun) -> WorkflowRun:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO workflow_runs (
                        run_id,
                        workflow_id,
                        plugin_id,
                        mission_id,
                        requested_by,
                        status,
                        input_payload,
                        step_runs,
                        data_platform,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run.run_id,
                        run.workflow_id,
                        run.plugin_id,
                        run.mission_id,
                        run.requested_by,
                        run.status.value,
                        Jsonb(run.input_payload),
                        Jsonb([step.model_dump(mode="json") for step in run.step_runs]),
                        run.data_platform,
                        run.created_at,
                    ),
                )
        return run

    def list_runs(self) -> list[WorkflowRun]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        run_id,
                        workflow_id,
                        plugin_id,
                        mission_id,
                        requested_by,
                        status,
                        input_payload,
                        step_runs,
                        data_platform,
                        created_at
                    FROM workflow_runs
                    WHERE data_platform = %s
                    ORDER BY created_at DESC
                    """,
                    ("DB MARIAM",),
                )
                rows = cursor.fetchall()
        return [WorkflowRun(**dict(row)) for row in rows]
