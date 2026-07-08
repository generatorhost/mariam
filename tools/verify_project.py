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
        "/api/runtime/verification-report",
        "/api/runtime/verification-report/snapshots",
        "/api/runtime/diagnostics",
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
    print("[verify] ok: mission -> artifact -> quality -> package -> client delivery")


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
