#!/usr/bin/env python3
"""Write .github/badges/tests.json for the dynamic shields.io README badge."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BADGE_PATH = ROOT / ".github" / "badges" / "tests.json"


def count_tests() -> int:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT / "src"))
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    env.setdefault("MPLBACKEND", "Agg")
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout, file=sys.stderr)
        raise SystemExit(1) from exc

    combined = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"(\d+)\s+tests?\s+collected", combined)
    if not match:
        print(combined, file=sys.stderr)
        raise SystemExit("Could not parse pytest collection output")
    return int(match.group(1))


def main() -> None:
    count = count_tests()
    payload = {
        "schemaVersion": 1,
        "label": "tests",
        "message": f"{count} passing",
        "color": "brightgreen",
    }
    BADGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BADGE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {BADGE_PATH} ({count} tests)")


if __name__ == "__main__":
    main()
