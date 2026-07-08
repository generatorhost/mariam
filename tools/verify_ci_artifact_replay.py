from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts" / "frontend-regression"
REPLAY_ROOT = ROOT / "artifacts" / "ci-artifact-replay"
DOWNLOAD_DIR = REPLAY_ROOT / "mariam-frontend-regression-artifacts"
REPORT_PATH = REPLAY_ROOT / "ci-artifact-replay-report.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

REQUIRED_JSON = [
    "command-center-regression-snapshot.json",
    "command-center-visual-contract.json",
    "command-center-browser-screenshot-plan.json",
    "command-center-browser-screenshot-capture.json",
    "command-center-governance-export-interaction-smoke.json",
    "command-center-delivery-governance-export-visual-smoke.json",
    "command-center-export-button-click-smoke.json",
    "command-center-keyboard-focus-smoke.json",
    "command-center-responsive-navigation-smoke.json",
]

REQUIRED_PNG = [
    "desktop-command-center.png",
    "tablet-command-center.png",
    "mobile-command-center.png",
    "command-center-export-click-smoke-governance-before.png",
    "command-center-export-click-smoke-after.png",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def copy_artifacts() -> None:
    if DOWNLOAD_DIR.exists():
        shutil.rmtree(DOWNLOAD_DIR)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for name in [*REQUIRED_JSON, *REQUIRED_PNG]:
        source = SOURCE / name
        if source.exists():
            shutil.copy2(source, DOWNLOAD_DIR / name)


def main() -> None:
    copy_artifacts()
    missing_json = [name for name in REQUIRED_JSON if not (DOWNLOAD_DIR / name).exists()]
    missing_png = [name for name in REQUIRED_PNG if not (DOWNLOAD_DIR / name).exists()]
    json_reports = {
        name: read_json(DOWNLOAD_DIR / name)
        for name in REQUIRED_JSON
        if (DOWNLOAD_DIR / name).exists()
    }
    invalid_json_reports = [
        name
        for name, payload in json_reports.items()
        if payload.get("status") not in {"ready", "passed"}
        and not (
            name == "command-center-browser-screenshot-capture.json"
            and payload.get("artifact_count") == 3
        )
    ]
    invalid_png = [
        name
        for name in REQUIRED_PNG
        if (DOWNLOAD_DIR / name).exists()
        and not (DOWNLOAD_DIR / name).read_bytes().startswith(PNG_SIGNATURE)
    ]
    checks = {
        "download_directory_created": DOWNLOAD_DIR.exists(),
        "json_artifacts_replayed": not missing_json and not invalid_json_reports,
        "png_artifacts_replayed": not missing_png and not invalid_png,
        "keyboard_focus_smoke_replayed": json_reports.get(
            "command-center-keyboard-focus-smoke.json",
            {},
        ).get("status")
        == "ready",
        "responsive_navigation_smoke_replayed": json_reports.get(
            "command-center-responsive-navigation-smoke.json",
            {},
        ).get("status")
        == "ready",
        "export_click_smoke_replayed": json_reports.get(
            "command-center-export-button-click-smoke.json",
            {},
        ).get("status")
        == "ready",
        "db_mariam_preserved": all(
            payload.get("data_platform", "DB MARIAM") == "DB MARIAM"
            for payload in json_reports.values()
        ),
    }
    report = {
        "title": "Mariam CI Frontend Artifact Download Replay",
        "status": "ready" if all(checks.values()) else "blocked",
        "data_platform": "DB MARIAM",
        "source_artifact_name": "mariam-frontend-regression-artifacts",
        "source_contract": ".github/workflows/verify.yml upload-artifact/download-artifact",
        "download_dir": str(DOWNLOAD_DIR.relative_to(ROOT)),
        "required_json": REQUIRED_JSON,
        "required_png": REQUIRED_PNG,
        "missing_json": missing_json,
        "missing_png": missing_png,
        "invalid_json_reports": invalid_json_reports,
        "invalid_png": invalid_png,
        "checks": checks,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
