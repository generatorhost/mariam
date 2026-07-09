from datetime import datetime

from pydantic import BaseModel, Field


class RemoteExecutionCommandRequest(BaseModel):
    command: str = Field(min_length=2, max_length=2000)
    working_directory: str = Field(default=".", max_length=500)
    actor_id: str = Field(default="command-center-operator", min_length=2)
    reason: str = Field(default="Governed remote execution command.", min_length=5)
    dry_run: bool = True
    approval_token: str | None = None
    timeout_seconds: int = Field(default=20, ge=1, le=120)
    evidence: dict = Field(default_factory=dict)


class RemoteExecutionJob(BaseModel):
    job_id: str
    plugin_id: str = "remote-execution-commander"
    command: str
    working_directory: str
    actor_id: str
    reason: str
    dry_run: bool
    status: str
    allowed: bool
    safety_notes: list[str]
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    data_platform: str = "DB MARIAM"


class RemoteExecutionManifest(BaseModel):
    plugin_id: str
    name: str
    version: str
    scope: str
    api_prefix: str
    dashboard_route: str
    chief_agent_role: str
    swarm_roles: list[str]
    governance_gates: list[str]
    allowed_command_prefixes: list[str]
    blocked_terms: list[str]
    private_tables: list[str]
    data_platform: str = "DB MARIAM"
