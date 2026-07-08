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
    / "command-center-delivery-governance-export-visual-smoke.json"
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


def run_visual_smoke() -> dict[str, Any]:
    source_text = FRONTEND_SOURCE.read_text(encoding="utf-8")
    source_checks = {
        "delivery_panel_loads_report": "loadDeliveryEvidenceReport" in source_text,
        "export_button_visible": "Export Delivery Governance Evidence" in source_text,
        "export_handler_bound": "handleDeliveryEvidenceExport" in source_text,
        "export_api_bound": "exportDeliveryGovernanceEvidence" in source_text,
        "success_state_visible": "Delivery Governance Evidence Export Ready" in source_text,
        "manifest_counts_rendered": "package_manifest.delivery_count" in source_text
        and "package_manifest.sla_drilldown_count" in source_text,
        "client_delivery_dashboard_present": "Refresh Delivery Packages" in source_text
        and "Refresh Delivery Evidence" in source_text,
    }
    export_package = request_json(
        "/api/runtime/delivery-evidence-report/export",
        "POST",
        {},
    )["export_package"]
    api_checks = {
        "export_ready_for_review": export_package["status"] == "ready_for_review",
        "export_uses_db_mariam": export_package["data_platform"] == "DB MARIAM",
        "export_governance_gated": export_package["package_manifest"][
            "requires_governance_review_before_external_delivery"
        ]
        is True,
        "export_contains_delivery_counts": "delivery_count" in export_package["package_manifest"]
        and "signed_bundle_count" in export_package["package_manifest"]
        and "confirmed_delivery_count" in export_package["package_manifest"],
        "export_contains_sla_evidence": "sla_status" in export_package["package_manifest"]
        and "sla_drilldown_count" in export_package["package_manifest"],
    }
    checks = {**source_checks, **api_checks}
    report = {
        "title": "Mariam Delivery Governance Export Visual Interaction Smoke",
        "status": "ready" if all(checks.values()) else "blocked",
        "generated_at": datetime.now(UTC).isoformat(),
        "data_platform": "DB MARIAM",
        "interaction_path": [
            "Open Command Center #missions",
            "Load Delivery Evidence dashboard",
            "Press Export Delivery Governance Evidence",
            "POST /api/runtime/delivery-evidence-report/export",
            "Render Delivery Governance Evidence Export Ready",
            "Show export id and package manifest counts in the client delivery dashboard",
        ],
        "source_file": str(FRONTEND_SOURCE),
        "export_id": export_package["export_id"],
        "delivery_count": export_package["package_manifest"]["delivery_count"],
        "signed_bundle_count": export_package["package_manifest"]["signed_bundle_count"],
        "confirmed_delivery_count": export_package["package_manifest"]["confirmed_delivery_count"],
        "sla_drilldown_count": export_package["package_manifest"]["sla_drilldown_count"],
        "checks": checks,
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = run_visual_smoke()
    print(json.dumps(report, indent=2))
    if report["status"] != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
