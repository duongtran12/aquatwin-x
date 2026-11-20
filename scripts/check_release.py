from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify AquaTwin-X release metadata")
    parser.add_argument("--tag", default="v1.0.0")
    args = parser.parse_args()
    expected = args.tag.removeprefix("v")
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    versions = {
        "backend": Settings.model_fields["aquatwin_version"].default,
        "frontend": package["version"],
        "frontend_lock": lock["packages"][""]["version"],
    }
    mismatches = {name: value for name, value in versions.items() if value != expected}
    if mismatches:
        raise SystemExit(f"Release version mismatch: expected {expected}, found {mismatches}")
    if f"AQUATWIN_VERSION={expected}" not in env:
        raise SystemExit(".env.example release version is not synchronized")
    if f"AQUATWIN_VERSION:-{expected}" not in compose:
        raise SystemExit("docker-compose.yml release version is not synchronized")
    print(f"AquaTwin-X release metadata verified: v{expected}")


if __name__ == "__main__":
    main()
