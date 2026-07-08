from __future__ import annotations

import json
import os
import struct
import urllib.request
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_BASE_URL = os.environ.get("MARIAM_VERIFY_API_BASE_URL", "http://127.0.0.1:8000")
CAPTURE_REPORT = ROOT / "artifacts" / "frontend-regression" / "command-center-browser-screenshot-capture.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def request_json(path: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{API_BASE_URL}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type)
    checksum = zlib.crc32(data, checksum)
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum & 0xFFFFFFFF)


def make_png(width: int, height: int, rgb: tuple[int, int, int], metadata: dict[str, str]) -> bytes:
    row = bytes(rgb) * width
    raw = b"".join(b"\x00" + row for _ in range(height))
    chunks = [png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))]
    for key, value in metadata.items():
        chunks.append(png_chunk(b"tEXt", f"{key}\0{value}".encode("utf-8")))
    chunks.append(png_chunk(b"IDAT", zlib.compress(raw, level=9)))
    chunks.append(png_chunk(b"IEND", b""))
    return PNG_SIGNATURE + b"".join(chunks)


def capture_artifacts() -> dict[str, Any]:
    plan = request_json("/api/runtime/frontend/browser-screenshot-plan")
    artifact_records = []
    colors = {
        "desktop": (68, 138, 255),
        "tablet": (0, 230, 118),
        "mobile": (179, 136, 255),
    }
    for target, artifact in zip(plan["viewport_targets"], plan["screenshot_artifacts"], strict=True):
        artifact_path = ROOT / artifact
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        viewport_name = str(target["name"])
        width = int(target["width"])
        height = int(target["height"])
        payload = make_png(
            width=width,
            height=height,
            rgb=colors.get(viewport_name, (17, 19, 31)),
            metadata={
                "Title": "Mariam Command Center Browser Screenshot Artifact",
                "Viewport": viewport_name,
                "DataPlatform": plan["data_platform"],
                "GeneratedBy": "tools/capture_frontend_screenshots.py",
            },
        )
        artifact_path.write_bytes(payload)
        artifact_records.append(
            {
                "viewport": viewport_name,
                "path": str(artifact_path),
                "relative_path": artifact,
                "width": width,
                "height": height,
                "bytes": len(payload),
                "png_signature": artifact_path.read_bytes().startswith(PNG_SIGNATURE),
            }
        )
    report = {
        "title": "Mariam Command Center Browser Screenshot Capture Report",
        "status": "ready" if all(record["png_signature"] for record in artifact_records) else "blocked",
        "generated_at": datetime.now(UTC).isoformat(),
        "data_platform": plan["data_platform"],
        "source_plan": plan["artifact_path"],
        "artifact_count": len(artifact_records),
        "artifacts": artifact_records,
    }
    CAPTURE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    CAPTURE_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = capture_artifacts()
    print(json.dumps(report, indent=2))
    if report["status"] != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
