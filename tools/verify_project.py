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


def verify_api_smoke_flow() -> None:
    print("[verify] checking read endpoints")
    read_endpoints = [
        "/api/health",
        "/api/runtime/summary",
        "/api/runtime/readiness",
        "/api/runtime/data-platform/readiness",
        "/api/runtime/data-platform/migration-runner",
        "/api/runtime/data-platform/seed-data",
        "/api/runtime/data-platform/backup-readiness",
        "/api/runtime/data-platform/plugin-schema-isolation",
        "/api/runtime/verification-report",
        "/api/runtime/verification-report/snapshots",
        "/api/runtime/diagnostics",
        "/api/runtime/usage-guide",
        "/api/runtime/completion-report",
        "/api/runtime/implementation-roadmap",
        "/api/artifacts",
        "/api/artifacts/quality-reviews",
        "/api/artifacts/deliveries",
        "/api/audit",
        "/api/runtime/events",
        "/api/plugins",
        "/api/runtime-objects",
        "/api/ai-resources/providers",
    ]
    for endpoint in read_endpoints:
        require_json(endpoint)
        print(f"[verify] ok: {endpoint}")

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

    completion_report_export = request_json("/api/runtime/completion-report/export", "POST", {})[
        "export_package"
    ]
    assert_condition(
        completion_report_export["package_manifest"]["area_count"] == len(completion_report["areas"]),
        "Completion report export package did not preserve the area count.",
    )
    print("[verify] ok: completion report export")

    implementation_roadmap = request_json("/api/runtime/implementation-roadmap")
    assert_condition(
        implementation_roadmap["status"] == "ready_for_execution"
        and implementation_roadmap["items"][0]["area"] == "DB MARIAM persistence boundary",
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

    confirmed = request_json(
        f"/api/artifacts/deliveries/{delivery_package['delivery_id']}/confirm",
        "POST",
        {
            "delivered_by": "project-verifier",
            "client_reference": "verification-client-confirmation",
            "evidence": {"verification": "client-delivery-confirmed"},
        },
    )["delivery_package"]
    assert_condition(confirmed["status"] == "delivered_to_client", "Delivery was not confirmed to client.")
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
