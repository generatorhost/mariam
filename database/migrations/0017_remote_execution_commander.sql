CREATE TABLE IF NOT EXISTS remote_execution_commander_jobs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    command TEXT NOT NULL,
    working_directory TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_remote_execution_commander_jobs_status_created
    ON remote_execution_commander_jobs (status, created_at);

CREATE INDEX IF NOT EXISTS idx_remote_execution_commander_jobs_actor
    ON remote_execution_commander_jobs (actor_id, created_at);
