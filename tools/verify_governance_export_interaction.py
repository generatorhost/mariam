from __future__ import annotations

import json
import os
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_BASE_URL = os.environ.get("MARIAM_VERIFY_API_BASE_URL", "http://127.0.0.1:8000")
FRONTEND_SOURCE = ROOT / "frontend" / "src" / "main.jsx"
ARTIFACT_PATH = (
    ROOT
    / "artifacts"
    / "frontend-regression"
    / "command-center-governance-export-interaction-smoke.json"
)


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


def run_interaction_smoke() -> dict[str, Any]:
    source_text = FRONTEND_SOURCE.read_text(encoding="utf-8")
    source_checks = {
        "export_button_visible": "Export Reviewer Decision Evidence" in source_text,
        "export_function_bound": "exportGovernanceDecisionEvidence" in source_text,
        "success_state_visible": "Reviewer Decision Evidence Export Ready" in source_text,
        "decision_count_rendered": "package_manifest.decision_count" in source_text,
        "governance_filters_visible": "Filter reviewer decisions by reviewer" in source_text
        and "Filter reviewer decisions by outcome" in source_text,
    }
    assignment_response = request_json(
        "/api/audit/approval-assignments",
        "POST",
        {
            "assigned_by": "visual-smoke-governance",
            "assignee_id": "visual-smoke-reviewer",
            "target_type": "artifact",
            "target_id": "visual-smoke-artifact",
            "approval_role": "quality-reviewer",
            "reason": "Create reviewer assignment before visual export smoke.",
            "evidence": {"verification": "governance-export-interaction-smoke"},
        },
    )
    assignment_audit_id = assignment_response["audit_record"]["audit_id"]
    history = request_json("/api/audit/governance-assignment-history")["history_report"]
    assignment = next(
        item for item in history["assignments"] if item["audit_id"] == assignment_audit_id
    )
    request_json(
        "/api/audit/reviewer-decisions",
        "POST",
        {
            "decided_by": "visual-smoke-reviewer",
            "reviewer_id": "visual-smoke-reviewer",
            "target_type": "artifact",
            "target_id": "visual-smoke-artifact",
            "assignment_id": assignment["assignment_id"],
            "decision": "approved",
            "reason": "Approve artifact to verify export control interaction.",
            "evidence": {"verification": "governance-export-interaction-smoke"},
        },
    )
    export_package = request_json(
        "/api/audit/governance-decision-evidence/export",
        "POST",
        {},
    )["export_package"]
    api_checks = {
        "export_ready_for_review": export_package["status"] == "ready_for_review",
        "export_counts_decisions": export_package["package_manifest"]["decision_count"] >= 1,
        "export_includes_smoke_reviewer": "visual-smoke-reviewer"
        in export_package["package_manifest"]["reviewer_ids"],
        "export_governance_gated": export_package["package_manifest"][
            "requires_governance_review_before_external_delivery"
        ]
        is True,
        "export_uses_db_mariam": export_package["data_platform"] == "DB MARIAM",
    }
    checks = {**source_checks, **api_checks}
    report = {
        "title": "Mariam Governance Decision Evidence Export Interaction Smoke",
        "status": "ready" if all(checks.values()) else "blocked",
        "generated_at": datetime.now(UTC).isoformat(),
        "data_platform": "DB MARIAM",
        "interaction_path": [
            "Open Command Center #governance",
            "Record reviewer decision evidence",
            "Press Export Reviewer Decision Evidence",
            "POST /api/audit/governance-decision-evidence/export",
            "Render Reviewer Decision Evidence Export Ready",
        ],
        "source_file": str(FRONTEND_SOURCE),
        "export_id": export_package["export_id"],
        "decision_count": export_package["package_manifest"]["decision_count"],
        "reviewer_ids": export_package["package_manifest"]["reviewer_ids"],
        "checks": checks,
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = run_interaction_smoke()
    print(json.dumps(report, indent=2))
    if report["status"] != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
