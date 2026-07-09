import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.remote_execution import (
    RemoteExecutionCommandRequest,
    RemoteExecutionJob,
    RemoteExecutionManifest,
)
from app.repositories.remote_execution import RemoteExecutionRepository
from app.services.audit import AuditService


class RemoteExecutionCommanderService:
    plugin_id = "remote-execution-commander"

    allowed_command_prefixes = [
        "Get-ChildItem",
        "Get-Content",
        "Select-String",
        "git status",
        "git diff",
        "git log",
        "npm run verify",
        "npm run backend:test",
        "python --version",
        "py -3.11",
    ]

    blocked_terms = [
        "Remove-Item",
        "del ",
        "rmdir",
        "rm ",
        "format",
        "shutdown",
        "Restart-Computer",
        "Stop-Process",
        "Start-Process",
        "Set-ExecutionPolicy",
        "Invoke-WebRequest",
        "curl ",
        "wget ",
        ">",
        ">>",
        "| Out-File",
        "New-Item",
        "Set-Content",
        "Add-Content",
    ]

    def __init__(
        self,
        event_bus: InMemoryEventBus,
        repository: RemoteExecutionRepository,
        audit_service: AuditService,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository
        self._audit_service = audit_service
        self._workspace_root = Path(__file__).resolve().parents[3]

    def manifest(self) -> RemoteExecutionManifest:
        return RemoteExecutionManifest(
            plugin_id=self.plugin_id,
            name="Remote Execution Commander Plugin",
            version="0.1.0",
            scope="Governed local command execution for diagnostics, repository inspection, and verification.",
            api_prefix=f"/api/plugins/{self.plugin_id}",
            dashboard_route=f"/plugins/{self.plugin_id}",
            chief_agent_role="Remote Execution Chief Agent",
            swarm_roles=[
                "Command Safety Reviewer",
                "Execution Runner",
                "Log Auditor",
                "Diagnostics Reporter",
            ],
            governance_gates=[
                "command allowlist",
                "blocked term scan",
                "workspace boundary check",
                "dry-run by default",
                "approval token for execution",
                "audit and event record",
            ],
            allowed_command_prefixes=self.allowed_command_prefixes,
            blocked_terms=self.blocked_terms,
            private_tables=[
                "remote_execution_commander_jobs",
                "remote_execution_commander_settings",
                "remote_execution_commander_audit_shadow",
            ],
        )

    def list_jobs(self) -> list[RemoteExecutionJob]:
        return sorted(self._repository.list(), key=lambda job: job.started_at, reverse=True)

    def get_job(self, job_id: str) -> RemoteExecutionJob | None:
        return self._repository.get(job_id)

    def run_command(self, request: RemoteExecutionCommandRequest) -> RemoteExecutionJob:
        started_at = datetime.now(UTC)
        allowed, safety_notes, resolved_cwd = self._validate_request(request)
        status = "dry_run" if request.dry_run else "blocked"
        stdout = ""
        stderr = ""
        exit_code = None
        finished_at = datetime.now(UTC)

        if allowed and request.dry_run:
            stdout = "Dry run accepted. Command was not executed."
        elif allowed:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", request.command],
                cwd=resolved_cwd,
                capture_output=True,
                check=False,
                text=True,
                timeout=request.timeout_seconds,
            )
            stdout = completed.stdout[-12000:]
            stderr = completed.stderr[-12000:]
            exit_code = completed.returncode
            status = "succeeded" if completed.returncode == 0 else "failed"
            finished_at = datetime.now(UTC)

        job = RemoteExecutionJob(
            job_id=f"remote-exec-{uuid4()}",
            command=request.command,
            working_directory=str(resolved_cwd),
            actor_id=request.actor_id,
            reason=request.reason,
            dry_run=request.dry_run,
            status=status,
            allowed=allowed,
            safety_notes=safety_notes,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
        )
        saved = self._repository.save(job)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="remote_execution.command",
                target_type="plugin",
                target_id=self.plugin_id,
                decision="approved" if allowed else "rejected",
                evidence={
                    "job_id": saved.job_id,
                    "command": saved.command,
                    "status": saved.status,
                    "dry_run": saved.dry_run,
                    "working_directory": saved.working_directory,
                    "safety_notes": saved.safety_notes,
                    "reason": request.reason,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "remote_execution.command",
            self.plugin_id,
            {
                "job_id": saved.job_id,
                "status": saved.status,
                "allowed": saved.allowed,
                "dry_run": saved.dry_run,
                "exit_code": saved.exit_code,
            },
        )
        return saved

    def _validate_request(
        self,
        request: RemoteExecutionCommandRequest,
    ) -> tuple[bool, list[str], Path]:
        notes: list[str] = []
        resolved_cwd = (self._workspace_root / request.working_directory).resolve()
        if not self._is_within_workspace(resolved_cwd):
            return False, ["working_directory must stay inside the Mariam repository."], self._workspace_root
        if not resolved_cwd.exists() or not resolved_cwd.is_dir():
            return False, ["working_directory must exist and be a directory."], self._workspace_root
        normalized_command = " ".join(request.command.strip().split())
        blocked = [term for term in self.blocked_terms if term.lower() in normalized_command.lower()]
        if blocked:
            return False, [f"blocked command term detected: {', '.join(blocked)}"], resolved_cwd
        if not any(normalized_command.startswith(prefix) for prefix in self.allowed_command_prefixes):
            return False, ["command prefix is not allowed for this plugin version."], resolved_cwd
        notes.append("command prefix passed allowlist")
        notes.append("blocked term scan passed")
        notes.append("working directory boundary passed")
        if not request.dry_run and request.approval_token != "LOCAL_OPERATOR_APPROVED":
            return False, [*notes, "execution requires approval_token LOCAL_OPERATOR_APPROVED"], resolved_cwd
        if request.dry_run:
            notes.append("dry-run mode prevents process execution")
        else:
            notes.append("approval token accepted for local execution")
        return True, notes, resolved_cwd

    def _is_within_workspace(self, path: Path) -> bool:
        try:
            path.relative_to(self._workspace_root)
        except ValueError:
            return False
        return True
