"""Tests for briefing run metrics."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from financial_researcher.paths import metrics_dir
from financial_researcher.services.run_metrics import (
    build_run_metrics_payload,
    extract_usage_metrics,
    format_metrics_summary,
    metrics_output_path,
    write_run_metrics,
)


@dataclass
class _UsageStub:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    successful_requests: int


class _StubCrew:
    def __init__(self, usage_metrics):
        self.usage_metrics = usage_metrics


class TestExtractUsageMetrics:
    def test_reads_usage_metrics_model(self):
        usage = _UsageStub(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            successful_requests=3,
        )
        assert extract_usage_metrics(_StubCrew(usage)) == {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "successful_requests": 3,
        }

    def test_returns_zeros_when_missing(self):
        assert extract_usage_metrics(_StubCrew(None)) == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "successful_requests": 0,
        }


class TestRunMetricsPersistence:
    def test_writes_json_file(self, tmp_path: Path):
        path = tmp_path / "run_2026-06-12_close.json"
        payload = build_run_metrics_payload(
            session="close",
            language="Italian",
            instrument_count=6,
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "successful_requests": 2,
            },
            duration_seconds=42.5,
            warnings=["example warning"],
            timestamp=datetime(2026, 6, 12, 18, 0, tzinfo=ZoneInfo("Europe/Rome")),
        )
        write_run_metrics(path, payload)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["session"] == "close"
        assert loaded["instrument_count"] == 6
        assert loaded["postprocess_warnings"] == ["example warning"]
        assert loaded["duration_seconds"] == 42.5

    def test_metrics_output_path(self):
        assert metrics_output_path(date_str="2026-06-12", session="post_open") == (
            metrics_dir() / "run_2026-06-12_post_open.json"
        )


class TestFormatMetricsSummary:
    def test_summary_line(self):
        line = format_metrics_summary(
            {
                "prompt_tokens": 1200,
                "completion_tokens": 800,
                "total_tokens": 2000,
                "successful_requests": 7,
            },
            warnings=["a", "b"],
        )
        assert line == "Tokens: prompt=1200 completion=800 | requests=7 | warnings=2"
