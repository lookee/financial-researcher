#!/usr/bin/env python3
"""Maintain .github/badges/tests.json for the dynamic shields.io README badge."""

from __future__ import annotations

import argparse
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


def format_badge_message(count: int) -> str:
    return f"{count} passing"


def build_badge_payload(count: int) -> dict[str, str | int]:
    return {
        "schemaVersion": 1,
        "label": "tests",
        "message": format_badge_message(count),
        "color": "brightgreen",
    }


def read_badge_message() -> str | None:
    if not BADGE_PATH.exists():
        return None
    payload = json.loads(BADGE_PATH.read_text(encoding="utf-8"))
    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    return None


def write_badge(count: int) -> None:
    BADGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BADGE_PATH.write_text(
        json.dumps(build_badge_payload(count), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {BADGE_PATH} ({count} tests)")


def check_badge() -> None:
    count = count_tests()
    expected = format_badge_message(count)
    actual = read_badge_message()
    if actual == expected:
        print(f"Test badge is up to date ({expected})")
        return
    print(
        f"Test badge out of date: expected {expected!r}, found {actual!r}.\n"
        f"Run: uv run python scripts/update_test_badge.py",
        file=sys.stderr,
    )
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 1 when tests.json does not match pytest collection",
    )
    args = parser.parse_args()

    if args.check:
        check_badge()
        return

    write_badge(count_tests())


if __name__ == "__main__":
    main()
