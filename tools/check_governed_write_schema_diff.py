from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "artifacts" / "verification" / "governed-write-api-schema-snapshots.json"
BASELINE_HASH_PATH = ROOT / "artifacts" / "verification" / "governed-write-api-schema-snapshots.sha256"


def read_hash(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip().lower()


def calculate_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not SNAPSHOT_PATH.exists():
        raise SystemExit(
            f"Governed write schema snapshot is missing: {SNAPSHOT_PATH}. Run npm run verify first."
        )
    if not BASELINE_HASH_PATH.exists():
        raise SystemExit(
            f"Governed write schema baseline hash is missing: {BASELINE_HASH_PATH}."
        )

    expected_hash = read_hash(BASELINE_HASH_PATH)
    actual_hash = calculate_hash(SNAPSHOT_PATH)
    if actual_hash != expected_hash:
        raise SystemExit(
            "\n".join(
                [
                    "Governed write API schema snapshot changed.",
                    f"Expected SHA-256: {expected_hash}",
                    f"Actual SHA-256:   {actual_hash}",
                    "Review artifacts/verification/governed-write-api-schema-snapshots.json.",
                    "If the schema change is intentional, update artifacts/verification/governed-write-api-schema-snapshots.sha256 in the same commit.",
                ]
            )
        )
    print("Governed write API schema snapshot matches the committed baseline hash.")


if __name__ == "__main__":
    main()
