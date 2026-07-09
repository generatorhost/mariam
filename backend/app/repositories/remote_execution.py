from typing import Protocol

from app.core.remote_execution import RemoteExecutionJob


class RemoteExecutionRepository(Protocol):
    def save(self, job: RemoteExecutionJob) -> RemoteExecutionJob:
        pass

    def get(self, job_id: str) -> RemoteExecutionJob | None:
        pass

    def list(self) -> list[RemoteExecutionJob]:
        pass


class InMemoryRemoteExecutionRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, RemoteExecutionJob] = {}

    def save(self, job: RemoteExecutionJob) -> RemoteExecutionJob:
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> RemoteExecutionJob | None:
        return self._jobs.get(job_id)

    def list(self) -> list[RemoteExecutionJob]:
        return list(self._jobs.values())


class PostgresRemoteExecutionRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save(self, job: RemoteExecutionJob) -> RemoteExecutionJob:
        import psycopg
        from psycopg.types.json import Jsonb

        payload = job.model_dump(mode="json")
        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO remote_execution_commander_jobs (
                        job_id,
                        status,
                        command,
                        working_directory,
                        actor_id,
                        payload,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (job_id)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        command = EXCLUDED.command,
                        working_directory = EXCLUDED.working_directory,
                        actor_id = EXCLUDED.actor_id,
                        payload = EXCLUDED.payload
                    """,
                    (
                        job.job_id,
                        job.status,
                        job.command,
                        job.working_directory,
                        job.actor_id,
                        Jsonb(payload),
                        job.started_at,
                    ),
                )
        return job

    def get(self, job_id: str) -> RemoteExecutionJob | None:
        return next((job for job in self.list() if job.job_id == job_id), None)

    def list(self) -> list[RemoteExecutionJob]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM remote_execution_commander_jobs
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [RemoteExecutionJob.model_validate(dict(row["payload"])) for row in rows]
