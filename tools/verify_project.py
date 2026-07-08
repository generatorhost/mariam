from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
API_BASE_URL = os.environ.get("MARIAM_VERIFY_API_BASE_URL", "http://127.0.0.1:8000")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def run_command(command: list[str], cwd: Path) -> None:
    print(f"[verify] running: {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def request_json(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=payload,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def require_json(path: str) -> dict[str, Any]:
    try:
        return request_json(path)
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"{path} returned HTTP {error.code}. Restart the backend if it is running stale code."
        ) from error


def api_is_healthy() -> bool:
    try:
        return request_json("/api/health").get("status") == "healthy"
    except (OSError, urllib.error.URLError, TimeoutError):
        return False


def start_backend_if_needed() -> subprocess.Popen[bytes] | None:
    if api_is_healthy():
        print("[verify] backend already healthy")
        return None
    print("[verify] starting backend")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=BACKEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        if api_is_healthy():
            print("[verify] backend healthy")
            return process
        time.sleep(0.5)
    process.terminate()
    raise RuntimeError("Backend did not become healthy within the verification window.")


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_frontend_screenshot_capture() -> None:
    run_command([sys.executable, "tools/capture_frontend_screenshots.py"], ROOT)
    capture_report_path = ROOT / "artifacts" / "frontend-regression" / "command-center-browser-screenshot-capture.json"
    capture_report = json.loads(capture_report_path.read_text(encoding="utf-8"))
    assert_condition(
        capture_report["status"] == "ready"
        and capture_report["artifact_count"] == 3
        and all(
            (ROOT / artifact["relative_path"]).read_bytes().startswith(PNG_SIGNATURE)
            for artifact in capture_report["artifacts"]
        ),
        "Frontend screenshot capture did not produce valid PNG artifacts.",
    )
    print("[verify] ok: frontend screenshot capture artifacts")


def verify_api_smoke_flow() -> None:
    print("[verify] checking read endpoints")
    read_endpoints = [
        "/api/health",
        "/api/auth/session",
        "/api/auth/request-context",
        "/api/runtime/summary",
        "/api/runtime/readiness",
        "/api/runtime/data-platform/readiness",
        "/api/runtime/data-platform/migration-runner",
        "/api/runtime/data-platform/seed-data",
        "/api/runtime/data-platform/backup-readiness",
        "/api/runtime/data-platform/plugin-schema-isolation",
        "/api/runtime/data-platform/docker-persistence",
        "/api/runtime/data-platform/live-db-smoke",
        "/api/runtime/data-platform/docker-container-execution",
        "/api/runtime/frontend/regression-snapshot",
        "/api/runtime/frontend/visual-contract",
        "/api/runtime/frontend/browser-screenshot-plan",
        "/api/runtime/frontend/browser-screenshot-capture",
        "/api/runtime/api-error-contract",
        "/api/runtime/delivery-evidence-report",
        "/api/runtime/verification-report",
        "/api/runtime/verification-automation",
        "/api/runtime/verification-report/snapshots",
        "/api/runtime/diagnostics",
        "/api/runtime/usage-guide",
        "/api/runtime/completion-report",
        "/api/runtime/implementation-roadmap",
        "/api/artifacts",
        "/api/artifacts/quality-reviews",
        "/api/artifacts/deliveries",
        "/api/audit",
        "/api/audit/reviewer-workload",
        "/api/runtime/events",
        "/api/plugins",
        "/api/runtime-objects",
        "/api/ai-resources/providers",
    ]
    for endpoint in read_endpoints:
        require_json(endpoint)
        print(f"[verify] ok: {endpoint}")

    request_context = request_json(
        "/api/auth/request-context",
        "GET",
        None,
    )["request_context"]
    assert_condition(
        request_context["actor_id"] == "command-center-operator"
        and request_context["actor_matches_session"] is True
        and request_context["data_platform"] == "DB MARIAM",
        "Request actor context did not match the current Command Center session.",
    )
    header_request = urllib.request.Request(
        f"{API_BASE_URL}/api/auth/request-context",
        method="GET",
        headers={
            "x-mariam-request-id": "verify-request-context",
            "x-mariam-actor-id": "command-center-operator",
        },
    )
    with urllib.request.urlopen(header_request, timeout=10) as response:
        header_context = json.loads(response.read().decode("utf-8"))["request_context"]
    assert_condition(
        header_context["request_id"] == "verify-request-context"
        and header_context["propagation_mode"] == "headers"
        and header_context["actor_matches_session"] is True,
        "Request actor context did not propagate actor headers.",
    )
    print("[verify] ok: request actor context")

    permission_check = request_json(
        "/api/auth/permissions/check",
        "POST",
        {
            "actor_id": "command-center-operator",
            "permission": "governance.assign_approval",
        },
    )["permission_check"]
    assert_condition(permission_check["allowed"] is True, "Permission check did not allow governance assignment.")
    print("[verify] ok: permission check")

    permission_enforcement = request_json(
        "/api/auth/permissions/enforce",
        "POST",
        {
            "actor_id": "command-center-operator",
            "permission": "governance.assign_approval",
            "target_type": "artifact",
            "target_id": "verification-artifact-review",
            "reason": "Verify backend permission enforcement.",
            "evidence": {"verification": "permission-enforced"},
        },
    )["permission_enforcement"]
    assert_condition(
        permission_enforcement["allowed"] is True
        and permission_enforcement["enforcement"] == "granted"
        and permission_enforcement["target_id"] == "verification-artifact-review",
        "Permission enforcement did not grant the known permission.",
    )
    denied_permission = urllib.request.Request(
        f"{API_BASE_URL}/api/auth/permissions/enforce",
        data=json.dumps(
            {
                "actor_id": "project-verifier",
                "permission": "system.destroy",
                "target_type": "system",
                "target_id": "core",
                "reason": "Verify denied backend permission enforcement.",
                "evidence": {"verification": "permission-denied"},
            }
        ).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(denied_permission, timeout=10)
        raise AssertionError("Permission enforcement allowed a denied permission.")
    except urllib.error.HTTPError as error:
        assert_condition(error.code == 403, "Denied permission should return HTTP 403.")
    print("[verify] ok: permission enforcement")

    authorization_audit_mission = request_json(
        "/api/missions",
        "POST",
        {
            "plugin_id": "crm",
            "user_request": "Verify endpoint authorization audit evidence.",
            "requested_by": "command-center-operator",
        },
    )["mission"]
    authorization_audit_records = request_json("/api/audit")["audit_records"]
    authorization_audit_record = next(
        (
            record
            for record in reversed(authorization_audit_records)
            if record["action"] == "authorization.permission_enforced"
            and record["target_type"] == "mission"
            and record["target_id"] == "/api/missions"
            and record["evidence"].get("path") == "/api/missions"
        ),
        None,
    )
    assert_condition(
        authorization_audit_record is not None
        and authorization_audit_record["decision"] == "granted"
        and authorization_audit_record["evidence"]["permission"] == "mission.create"
        and authorization_audit_record["evidence"]["authorization_dependency"] is True,
        "Authorization dependency did not record endpoint-level audit evidence.",
    )
    print("[verify] ok: authorization dependency audit evidence")

    unauthorized_mission = urllib.request.Request(
        f"{API_BASE_URL}/api/missions",
        data=json.dumps(
            {
                "plugin_id": "crm",
                "user_request": "This mission should be blocked by request-scoped authorization.",
                "requested_by": "intruder",
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-mariam-actor-id": "intruder",
            "x-mariam-request-id": "verification-unauthorized-mission",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(unauthorized_mission, timeout=10)
        raise AssertionError("Request-scoped authorization allowed an unauthorized mission.")
    except urllib.error.HTTPError as error:
        assert_condition(error.code == 403, "Unauthorized mission should return HTTP 403.")
    print("[verify] ok: request-scoped authorization dependency")

    human_identity = request_json(
        "/api/auth/human-identity/enforce",
        "POST",
        {
            "actor_id": "command-center-operator",
            "claimed_user_id": "command-center-operator",
            "target_type": "artifact",
            "target_id": "verification-artifact-review",
            "reason": "Verify human identity enforcement before governance approval.",
            "evidence": {"verification": "human-identity-enforced"},
        },
    )["human_identity"]
    assert_condition(
        human_identity["verified"] is True
        and human_identity["display_name"] == "Command Center Operator"
        and human_identity["data_platform"] == "DB MARIAM",
        "Human identity enforcement did not verify the current operator.",
    )
    print("[verify] ok: human identity enforcement")

    snapshot = request_json(
        "/api/runtime/verification-report/record",
        "POST",
        {
            "actor_id": "project-verifier",
            "evidence": {"source": "verify-project"},
        },
    )["audit_record"]
    assert_condition(
        snapshot["action"] == "runtime.verification_report.record",
        "Verification snapshot did not record the expected audit action.",
    )
    snapshot_history = request_json("/api/runtime/verification-report/snapshots")["snapshots"]
    assert_condition(
        snapshot["audit_id"] in [item["audit_id"] for item in snapshot_history],
        "Verification snapshot was not available from snapshot history.",
    )
    print("[verify] ok: verification snapshot audit")

    diagnostics_export = request_json("/api/runtime/diagnostics/export", "POST", {})["export_package"]
    assert_condition(
        diagnostics_export["status"] == "ready_for_review",
        "Diagnostics export package was not ready for review.",
    )
    print("[verify] ok: diagnostics export")

    data_platform_readiness = request_json("/api/runtime/data-platform/readiness")
    assert_condition(
        data_platform_readiness["status"] == "ready"
        and data_platform_readiness["database_name"] == "DB MARIAM",
        "DB MARIAM data platform readiness did not pass.",
    )
    print("[verify] ok: data platform readiness")

    data_platform_export = request_json(
        "/api/runtime/data-platform/readiness/export",
        "POST",
        {},
    )["export_package"]
    assert_condition(
        data_platform_export["package_manifest"]["secrets_masked"] is True,
        "DB MARIAM data platform readiness export did not mask secrets.",
    )
    print("[verify] ok: data platform readiness export")

    migration_runner = request_json("/api/runtime/data-platform/migration-runner")
    assert_condition(
        migration_runner["status"] == "ready" and migration_runner["migration_count"] >= 1,
        "DB MARIAM migration runner status did not pass.",
    )
    print("[verify] ok: migration runner status")

    migration_runner_export = request_json(
        "/api/runtime/data-platform/migration-runner/export",
        "POST",
        {},
    )["export_package"]
    assert_condition(
        migration_runner_export["package_manifest"]["migration_count"]
        == len(migration_runner["ordered_migrations"]),
        "DB MARIAM migration runner export did not preserve migration count.",
    )
    print("[verify] ok: migration runner export")

    seed_data_status = request_json("/api/runtime/data-platform/seed-data")
    assert_condition(
        seed_data_status["status"] == "ready" and seed_data_status["contains_secrets"] is False,
        "DB MARIAM seed data status did not pass.",
    )
    print("[verify] ok: seed data status")

    backup_readiness = request_json("/api/runtime/data-platform/backup-readiness")
    assert_condition(
        backup_readiness["status"] == "ready" and backup_readiness["contains_secrets"] is False,
        "DB MARIAM backup readiness did not pass.",
    )
    print("[verify] ok: backup readiness")

    plugin_schema_isolation = request_json("/api/runtime/data-platform/plugin-schema-isolation")
    assert_condition(
        plugin_schema_isolation["status"] == "ready"
        and plugin_schema_isolation["plugin_schema_count"] >= 1,
        "DB MARIAM plugin schema isolation did not pass.",
    )
    print("[verify] ok: plugin schema isolation")

    docker_persistence = request_json("/api/runtime/data-platform/docker-persistence")
    assert_condition(
        docker_persistence["status"] == "ready" and docker_persistence["postgres_store_count"] == 6,
        "DB MARIAM Docker persistence profile did not pass.",
    )
    print("[verify] ok: docker persistence profile")

    live_db_smoke = request_json("/api/runtime/data-platform/live-db-smoke")
    assert_condition(
        live_db_smoke["status"] == "ready" and live_db_smoke["compose_config_valid"] is True,
        "DB MARIAM live DB smoke readiness did not pass.",
    )
    print("[verify] ok: live DB smoke readiness")

    docker_execution = request_json("/api/runtime/data-platform/docker-container-execution")
    assert_condition(
        docker_execution["status"] == "ready"
        and docker_execution["postgres_running"] is True
        and docker_execution["pg_isready"] is True,
        "DB MARIAM Docker container execution verification did not pass.",
    )
    print("[verify] ok: docker container execution")

    live_write_smoke = request_json("/api/runtime/data-platform/live-write-smoke", "POST", {})
    assert_condition(
        live_write_smoke["status"] == "ready"
        and live_write_smoke["audit_written"] is True
        and live_write_smoke["event_written"] is True
        and live_write_smoke["data_platform"] == "DB MARIAM",
        "DB MARIAM live write smoke did not write and read audit/event records.",
    )
    print("[verify] ok: live DB write smoke")

    live_repository_write_smoke = request_json(
        "/api/runtime/data-platform/live-repository-write-smoke",
        "POST",
        {},
    )
    assert_condition(
        live_repository_write_smoke["status"] == "ready"
        and live_repository_write_smoke["mission_written"] is True
        and live_repository_write_smoke["artifact_written"] is True
        and live_repository_write_smoke["delivery_written"] is True
        and live_repository_write_smoke["plugin_written"] is True
        and live_repository_write_smoke["runtime_object_written"] is True
        and live_repository_write_smoke["ai_resource_route_written"] is True
        and live_repository_write_smoke["quality_review_written"] is True
        and live_repository_write_smoke["communication_record_written"] is True
        and live_repository_write_smoke["document_record_written"] is True
        and live_repository_write_smoke["workflow_record_written"] is True
        and live_repository_write_smoke["capability_graph_record_written"] is True
        and live_repository_write_smoke["data_platform"] == "DB MARIAM",
        "DB MARIAM live repository write smoke did not write mission/artifact/delivery/plugin/runtime object/AI route/quality review/communication/document/workflow/capability graph records.",
    )
    print("[verify] ok: live repository write smoke")

    frontend_regression = request_json("/api/runtime/frontend/regression-snapshot")
    assert_condition(
        frontend_regression["status"] == "ready"
        and frontend_regression["missing_controls"] == []
        and frontend_regression["missing_viewports"] == []
        and frontend_regression["missing_keyboard_traversal_targets"] == []
        and 'className="skip-link"' in frontend_regression["keyboard_traversal_targets"]
        and 'aria-label="Command Center sections"'
        in frontend_regression["keyboard_traversal_targets"]
        and "Refresh Actor Context" in frontend_regression["controls_checked"]
        and "Enforce Human Identity" in frontend_regression["controls_checked"]
        and "Refresh Docker Execution" in frontend_regression["controls_checked"]
        and "Refresh Visual Contract" in frontend_regression["controls_checked"]
        and "Refresh Screenshot Plan" in frontend_regression["controls_checked"]
        and "Refresh Governance SLA" in frontend_regression["controls_checked"]
        and "Run Repository Write Smoke" in frontend_regression["controls_checked"]
        and "Refresh Verification Automation" in frontend_regression["controls_checked"],
        "Frontend regression snapshot did not pass.",
    )
    print("[verify] ok: frontend regression snapshot")

    frontend_visual_contract = request_json("/api/runtime/frontend/visual-contract")
    assert_condition(
        frontend_visual_contract["status"] == "ready"
        and frontend_visual_contract["missing_design_tokens"] == []
        and frontend_visual_contract["missing_layout_contracts"] == []
        and frontend_visual_contract["missing_breakpoint_contracts"] == []
        and "#governance" in frontend_visual_contract["screenshot_targets"],
        "Frontend visual contract did not pass.",
    )
    print("[verify] ok: frontend visual contract")

    frontend_screenshot_plan = request_json("/api/runtime/frontend/browser-screenshot-plan")
    assert_condition(
        frontend_screenshot_plan["status"] == "ready"
        and any(target["name"] == "desktop" for target in frontend_screenshot_plan["viewport_targets"])
        and "#governance" in frontend_screenshot_plan["critical_sections"]
        and any(
            artifact.endswith("desktop-command-center.png")
            for artifact in frontend_screenshot_plan["screenshot_artifacts"]
        )
        and "screenshot_artifacts_captured"
        in frontend_screenshot_plan["required_browser_checks"],
        "Frontend browser screenshot plan did not pass.",
    )
    print("[verify] ok: frontend browser screenshot plan")
    verify_frontend_screenshot_capture()
    frontend_screenshot_capture = request_json("/api/runtime/frontend/browser-screenshot-capture")
    assert_condition(
        frontend_screenshot_capture["status"] == "ready"
        and frontend_screenshot_capture["artifact_count"] == 3
        and all(artifact["png_signature"] for artifact in frontend_screenshot_capture["artifacts"])
        and len(frontend_screenshot_capture["thumbnail_previews"]) == 3
        and all(
            thumbnail["available"]
            and thumbnail["data_url"].startswith("data:image/png;base64,")
            for thumbnail in frontend_screenshot_capture["thumbnail_previews"]
        ),
        "Frontend screenshot capture report did not verify generated PNG artifacts.",
    )
    print("[verify] ok: frontend screenshot capture report")

    api_error_contract = request_json("/api/runtime/api-error-contract")
    assert_condition(
        api_error_contract["status"] == "ready"
        and api_error_contract["data_platform"] == "DB MARIAM"
        and "error.request_id" in api_error_contract["required_fields"]
        and "governed_endpoints" in api_error_contract["applies_to"]
        and {"403", "404", "422"}.issubset(set(api_error_contract["openapi_response_examples"].keys())),
        "API error contract did not expose required governed error fields.",
    )
    openapi = request_json("/openapi.json")
    api_error_operation = openapi["paths"]["/api/runtime/api-error-contract"]["get"]
    assert_condition(
        all(
            api_error_operation["responses"][status_code]["content"]["application/json"]["example"]["error"][
                "data_platform"
            ]
            == "DB MARIAM"
            for status_code in ["403", "404", "422"]
        ),
        "OpenAPI did not document structured API error response examples.",
    )
    print("[verify] ok: api error contract")

    verification_automation = request_json("/api/runtime/verification-automation")
    assert_condition(
        verification_automation["status"] == "ready"
        and verification_automation["local_automation_status"] == "ready"
        and verification_automation["ci_status"] == "ready"
        and "npm run verify" in verification_automation["required_commands"]
        and "py -3.11 tools/capture_frontend_screenshots.py"
        in verification_automation["required_commands"]
        and any(
            check["name"] == "ci_frontend_artifact_upload" and check["status"] == "ready"
            for check in verification_automation["checks"]
        )
        and any(
            check["name"] == "ci_frontend_artifact_retention" and check["status"] == "ready"
            for check in verification_automation["checks"]
        )
        and any(
            check["name"] == "ci_badge_metadata_ready" and check["status"] == "ready"
            for check in verification_automation["checks"]
        )
        and any(
            check["name"] == "latest_ci_run_polling_configured" and check["status"] == "ready"
            for check in verification_automation["checks"]
        )
        and verification_automation["ci_artifact_retention"]["retention_days"] == 14
        and verification_automation["ci_artifact_retention"]["artifact_name"]
        == "mariam-frontend-regression-artifacts"
        and verification_automation["ci_badge"]["badge_url"].endswith(
            "/actions/workflows/verify.yml/badge.svg?branch=main"
        )
        and verification_automation["latest_run_status"]["polling_status"] == "configured"
        and "actions/workflows/verify.yml/runs"
        in verification_automation["latest_run_status"]["api_url"]
        and verification_automation["local_history_comparison"]["status"]
        in {"insufficient_history", "stable", "changed"}
        and "snapshot_count" in verification_automation["local_history_comparison"]
        and "/api/runtime/frontend/visual-contract" in verification_automation["required_endpoints"]
        and "/api/runtime/frontend/browser-screenshot-plan"
        in verification_automation["required_endpoints"]
        and "/api/runtime/frontend/browser-screenshot-capture"
        in verification_automation["required_endpoints"]
        and "/api/runtime/api-error-contract" in verification_automation["required_endpoints"]
        and "/api/runtime/delivery-evidence-report" in verification_automation["required_endpoints"],
        "Verification automation contract did not pass.",
    )
    print("[verify] ok: verification automation contract")

    usage_guide = request_json("/api/runtime/usage-guide")
    assert_condition(
        any(step["frontend_control"] == "Export Diagnostics" for step in usage_guide["steps"]),
        "Usage guide did not map the diagnostics export button.",
    )
    print("[verify] ok: usage guide")

    usage_guide_export = request_json("/api/runtime/usage-guide/export", "POST", {})["export_package"]
    assert_condition(
        usage_guide_export["package_manifest"]["step_count"] == len(usage_guide["steps"]),
        "Usage guide export package did not preserve the usage guide step count.",
    )
    print("[verify] ok: usage guide export")

    completion_report = request_json("/api/runtime/completion-report")
    assert_condition(
        completion_report["status"] == "in_progress_verified"
        and completion_report["verification"]["status"] == "passed",
        "Completion report did not confirm verified in-progress status.",
    )
    print("[verify] ok: completion report")

    openapi = request_json("/openapi.json")
    assert_condition(
        openapi["paths"]["/api/runtime/completion-report"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ProjectCompletionReportResponse"
        and openapi["paths"]["/api/runtime/implementation-roadmap"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ImplementationRoadmapResponse"
        and openapi["paths"]["/api/runtime/verification-automation"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/VerificationAutomationResponse"
        and openapi["paths"]["/api/runtime/delivery-evidence-report"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DeliveryEvidenceReportResponse"
        and openapi["paths"]["/api/runtime/data-platform/readiness"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DataPlatformReadinessResponse"
        and openapi["paths"]["/api/runtime/data-platform/readiness/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DataPlatformReadinessExportResponse",
        "Governed runtime endpoints did not publish typed response models.",
    )
    print("[verify] ok: governed runtime typed response models")

    completion_report_export = request_json("/api/runtime/completion-report/export", "POST", {})[
        "export_package"
    ]
    assert_condition(
        completion_report_export["package_manifest"]["area_count"] == len(completion_report["areas"]),
        "Completion report export package did not preserve the area count.",
    )
    print("[verify] ok: completion report export")

    approval_assignment = request_json(
        "/api/audit/approval-assignments",
        "POST",
        {
            "assigned_by": "project-verifier",
            "assignee_id": "quality-reviewer-01",
            "target_type": "artifact",
            "target_id": "verification-artifact-review",
            "approval_role": "quality-reviewer",
            "reason": "Verify approval assignment governance flow.",
            "evidence": {"verification": "approval-assigned"},
        },
    )["audit_record"]
    assert_condition(
        approval_assignment["decision"] == "assigned"
        and approval_assignment["evidence"]["assignee_id"] == "quality-reviewer-01",
        "Approval assignment did not record the expected audit evidence.",
    )
    print("[verify] ok: approval assignment")

    notification_route = request_json(
        "/api/audit/notifications/route",
        "POST",
        {
            "routed_by": "project-verifier",
            "recipient_id": "quality-reviewer-01",
            "channel": "command-center",
            "subject": "Verification artifact review",
            "message": "Verify notification routing before client delivery.",
            "target_type": "artifact",
            "target_id": "verification-artifact-review",
            "evidence": {"verification": "notification-routed"},
        },
    )["audit_record"]
    assert_condition(
        notification_route["decision"] == "routed"
        and notification_route["evidence"]["recipient_id"] == "quality-reviewer-01"
        and notification_route["evidence"]["channel"] == "command-center",
        "Notification routing did not record the expected audit evidence.",
    )
    print("[verify] ok: notification routing")

    reviewer_workload = request_json("/api/audit/reviewer-workload")["workload_report"]
    assert_condition(
        reviewer_workload["reviewer_count"] >= 1
        and any(item["reviewer_id"] == "quality-reviewer-01" for item in reviewer_workload["items"]),
        "Reviewer workload report did not include the assigned reviewer.",
    )
    governance_sla = request_json("/api/audit/governance-sla")["sla_report"]
    assert_condition(
        governance_sla["status"] in {"ready", "escalation_required"}
        and governance_sla["sla_minutes"] == 240
        and governance_sla["escalation_after_minutes"] == 480
        and any(item["target_id"] == "verification-artifact-review" for item in governance_sla["items"]),
        "Governance SLA report did not expose assignment aging rules.",
    )
    print("[verify] ok: governance SLA aging")
    escalation_record = request_json(
        "/api/audit/escalations",
        "POST",
        {
            "escalated_by": "project-verifier",
            "reviewer_id": "quality-reviewer-01",
            "target_type": "artifact",
            "target_id": "verification-artifact-review",
            "reason": "Verify governance reviewer workload escalation.",
            "escalation_level": "governance-lead-review",
            "evidence": {"verification": "reviewer-workload-escalated"},
        },
    )["audit_record"]
    assert_condition(
        escalation_record["decision"] == "escalated"
        and escalation_record["evidence"]["reviewer_id"] == "quality-reviewer-01",
        "Reviewer workload escalation did not record the expected audit evidence.",
    )
    print("[verify] ok: reviewer workload escalation")

    plugin_manifest = json.loads((ROOT / "plugins" / "crm" / "manifest.json").read_text(encoding="utf-8"))
    plugin = request_json("/api/plugins", "POST", plugin_manifest)["plugin"]
    plugin_workspace = request_json(f"/api/plugins/{plugin['plugin_id']}/workspace")
    assert_condition(
        plugin_workspace["dashboard"]["dashboard_route"] == "/plugins/crm"
        and plugin_workspace["chief_agent"]["role"] == "CRM Chief Agent"
        and plugin_workspace["data_boundary"]["platform"] == "DB MARIAM"
        and len(plugin_workspace["workspace_actions"]) == 4,
        "Plugin workspace did not expose dashboard, Chief, DB MARIAM boundary, and actions.",
    )
    print("[verify] ok: plugin workspace")

    implementation_roadmap = request_json("/api/runtime/implementation-roadmap")
    assert_condition(
        implementation_roadmap["status"] == "ready_for_execution"
        and implementation_roadmap["items"][0]["area"] == "Verification automation",
        "Implementation roadmap did not expose the expected next execution priority.",
    )
    print("[verify] ok: implementation roadmap")

    implementation_roadmap_export = request_json(
        "/api/runtime/implementation-roadmap/export",
        "POST",
        {},
    )["export_package"]
    assert_condition(
        implementation_roadmap_export["package_manifest"]["item_count"]
        == len(implementation_roadmap["items"]),
        "Implementation roadmap export package did not preserve the item count.",
    )
    print("[verify] ok: implementation roadmap export")

    print("[verify] checking mission to delivery flow")
    mission = request_json(
        "/api/missions",
        "POST",
        {
            "plugin_id": "crm",
            "user_request": "Verify complete quality and delivery flow.",
            "requested_by": "project-verifier",
        },
    )["mission"]
    artifact = request_json(f"/api/artifacts/from-mission/{mission['mission_id']}", "POST", {})["artifact"]
    rejected = request_json(
        f"/api/artifacts/{artifact['artifact_id']}/reject",
        "POST",
        {
            "rejected_by": "project-verifier",
            "reason": "Verify artifact revision loop before approval.",
            "evidence": {"verification": "artifact-rejected-for-revision"},
        },
    )["artifact"]
    assert_condition(rejected["status"] == "rejected", "Artifact rejection did not return rejected status.")

    revision = request_json(
        f"/api/artifacts/{artifact['artifact_id']}/request-revision",
        "POST",
        {
            "requested_by": "project-verifier",
            "revision_request": "Add traceability evidence before final approval.",
            "evidence": {"verification": "artifact-revision-requested"},
        },
    )["artifact"]
    assert_condition(
        revision["status"] == "awaiting_approval" and "Revision requested" in revision["content"],
        "Artifact revision loop did not return the artifact to approval.",
    )

    approved = request_json(
        f"/api/artifacts/{artifact['artifact_id']}/approve",
        "POST",
        {
            "approved_by": "project-verifier",
            "evidence": {"verification": "artifact-approved"},
        },
    )["artifact"]
    assert_condition(approved["status"] == "approved", "Artifact approval did not return approved status.")

    premature_delivery = urllib.request.Request(
        f"{API_BASE_URL}/api/artifacts/{artifact['artifact_id']}/package-delivery",
        data=json.dumps(
            {
                "packaged_by": "project-verifier",
                "destination": "verification-channel",
                "evidence": {"verification": "should-fail-before-quality"},
            }
        ).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(premature_delivery, timeout=10)
        raise AssertionError("Packaging succeeded before quality review.")
    except urllib.error.HTTPError as error:
        assert_condition(error.code == 400, "Packaging before quality review should fail with HTTP 400.")

    quality_review = request_json(
        f"/api/artifacts/{artifact['artifact_id']}/quality-review",
        "POST",
        {
            "reviewed_by": "project-verifier",
            "evidence": {"verification": "quality-reviewed"},
        },
    )["quality_review"]
    assert_condition(quality_review["passed"] is True, "Quality review did not pass.")
    assert_condition(quality_review["score"] == 100, "Quality review score should be 100.")

    delivery_package = request_json(
        f"/api/artifacts/{artifact['artifact_id']}/package-delivery",
        "POST",
        {
            "packaged_by": "project-verifier",
            "destination": "verification-channel",
            "evidence": {"verification": "delivery-packaged"},
        },
    )["delivery_package"]
    assert_condition(
        delivery_package["package_manifest"]["quality_review_id"] == quality_review["review_id"],
        "Delivery package is missing the quality review trace.",
    )
    assert_condition(
        delivery_package["package_manifest"]["evidence_signed"] is True
        and delivery_package["package_manifest"]["evidence_signature_algorithm"] == "sha256"
        and len(delivery_package["package_manifest"]["evidence_signature"]) == 64,
        "Delivery package is missing the signed evidence bundle.",
    )

    confirmed = request_json(
        f"/api/artifacts/deliveries/{delivery_package['delivery_id']}/confirm",
        "POST",
        {
            "delivered_by": "project-verifier",
            "client_reference": "verification-client-confirmation",
            "evidence": {"verification": "client-delivery-confirmed"},
        },
    )["delivery_package"]
    assert_condition(
        confirmed["status"] == "delivered_to_client"
        and confirmed["package_manifest"]["delivery_confirmation_requires_signature"] is True
        and confirmed["package_manifest"]["evidence_signature"]
        == delivery_package["package_manifest"]["evidence_signature"],
        "Delivery was not confirmed to client with a signed evidence bundle.",
    )
    delivery_evidence_report = request_json("/api/runtime/delivery-evidence-report")
    evidence_item = next(
        (
            item for item in delivery_evidence_report["evidence_items"]
            if item["delivery_id"] == confirmed["delivery_id"]
        ),
        None,
    )
    sla_item = next(
        (
            item for item in delivery_evidence_report["sla_items"]
            if item["delivery_id"] == confirmed["delivery_id"]
        ),
        None,
    )
    assert_condition(
        delivery_evidence_report["status"] == "ready"
        and delivery_evidence_report["invalid_signature_count"] == 0
        and delivery_evidence_report["signed_bundle_count"] >= 1
        and delivery_evidence_report["sla_minutes"] == 240
        and delivery_evidence_report["escalation_after_minutes"] == 480
        and evidence_item is not None
        and evidence_item["signature_valid"] is True
        and evidence_item["delivery_confirmed"] is True,
        "Delivery evidence report did not verify the signed client delivery package.",
    )
    assert_condition(
        sla_item is not None
        and sla_item["signature_valid"] is True
        and sla_item["delivery_confirmed"] is True
        and sla_item["sla_state"] == "confirmed"
        and sla_item["escalation_required"] is False,
        "Delivery evidence report did not expose the signed delivery SLA trace.",
    )
    drilldown_item = next(
        (
            item for item in delivery_evidence_report["sla_drilldown_items"]
            if item["delivery_id"] == confirmed["delivery_id"]
        ),
        None,
    )
    assert_condition(
        delivery_evidence_report["sla_drilldown_summary"]["signed_item_count"] >= 1
        and "delivery-evidence"
        in delivery_evidence_report["sla_drilldown_summary"]["reviewer_queue_counts"]
        and "confirmed" in delivery_evidence_report["sla_filters"]["sla_state_options"]
        and "delivery-evidence" in delivery_evidence_report["sla_filters"]["reviewer_queue_options"]
        and delivery_evidence_report["filtered_sla_drilldown_items"]
        and drilldown_item is not None
        and drilldown_item["reviewer_queue"] == "delivery-evidence"
        and drilldown_item["governance_action"] == "confirm_traceability_complete",
        "Delivery evidence report did not expose the governance SLA drill-down row and filters.",
    )
    print("[verify] ok: mission -> artifact -> revision -> quality -> package -> client delivery")


def main() -> None:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    run_command([sys.executable, "-m", "pytest"], BACKEND)
    run_command([npm, "run", "build"], FRONTEND)
    backend_process = start_backend_if_needed()
    try:
        verify_api_smoke_flow()
    finally:
        if backend_process is not None:
            backend_process.terminate()
            backend_process.wait(timeout=10)
    print("[verify] all checks passed")


if __name__ == "__main__":
    main()
