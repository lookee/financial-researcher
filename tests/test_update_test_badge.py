"""Tests for scripts/update_test_badge.py helpers."""

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_test_badge.py"
SPEC = importlib.util.spec_from_file_location("update_test_badge", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

build_badge_payload = MODULE.build_badge_payload
format_badge_message = MODULE.format_badge_message
read_badge_message = MODULE.read_badge_message
write_badge = MODULE.write_badge


class TestUpdateTestBadge:
    def test_format_badge_message(self):
        assert format_badge_message(187) == "187 passing"

    def test_build_badge_payload(self):
        payload = build_badge_payload(42)
        assert payload["message"] == "42 passing"
        assert payload["label"] == "tests"

    def test_write_and_read_badge(self, tmp_path: Path, monkeypatch):
        badge_path = tmp_path / "tests.json"
        monkeypatch.setattr(MODULE, "BADGE_PATH", badge_path)
        write_badge(12)
        assert read_badge_message() == "12 passing"
        loaded = json.loads(badge_path.read_text(encoding="utf-8"))
        assert loaded["message"] == "12 passing"
