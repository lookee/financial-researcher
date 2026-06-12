"""Tests for CLI output sanitisation."""

import subprocess
import sys
from pathlib import Path

import pytest

from financial_researcher.cli_output import (
    configure_clean_cli_output,
    crew_quiet_enabled,
    crew_verbose_enabled,
)

_ROOT = Path(__file__).resolve().parents[1]


class TestConfigureCleanCliOutput:
    def test_suppresses_pydantic_warnings_on_tool_import(self):
        pytest.importorskip("crewai_tools")
        code = """
from financial_researcher.cli_output import configure_clean_cli_output
configure_clean_cli_output()
from crewai_tools import ScrapeWebsiteTool
"""
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0
        assert "ArbitraryTypeWarning" not in completed.stderr
        assert "PydanticDeprecatedSince20" not in completed.stderr

    def test_verbose_on_by_default(self, monkeypatch):
        monkeypatch.delenv("BRIEFING_QUIET", raising=False)
        assert crew_quiet_enabled() is False
        assert crew_verbose_enabled() is True

    def test_quiet_flag_from_environment(self, monkeypatch):
        monkeypatch.setenv("BRIEFING_QUIET", "1")
        assert crew_quiet_enabled() is True
        assert crew_verbose_enabled() is False
