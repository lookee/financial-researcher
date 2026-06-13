"""Tests for briefing run metrics."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from financial_researcher.paths import metrics_dir
from financial_researcher.services.run_metrics import (
    append_run_metadata_footer,
    build_run_metrics_payload,
    extract_usage_metrics,
    format_duration,
    format_metrics_summary,
    format_run_metadata_footer,
    metrics_output_path,
    strip_run_metadata_footer,
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


class TestRunMetadataFooter:
    def _payload(self) -> dict:
        return build_run_metrics_payload(
            session="close",
            language="Italian",
            instrument_count=6,
            usage={
                "prompt_tokens": 33518,
                "completion_tokens": 14522,
                "total_tokens": 48040,
                "successful_requests": 7,
            },
            duration_seconds=96.75,
            warnings=[],
            model_profile="balanced",
            agent_models={
                "market": "openai/gpt-5.4-mini",
                "news": "openai/gpt-5.5",
                "outlook": "openai/gpt-5.4",
                "calendar": "openai/gpt-5.4-mini",
                "chief": "openai/gpt-5.5",
            },
        )

    def test_format_duration(self):
        assert format_duration(42.5) == "42.5s"
        assert format_duration(96.75) == "1m 37s"

    def test_footer_in_italian(self):
        footer = format_run_metadata_footer(
            metrics_payload=self._payload(),
            language="Italian",
        )
        assert "## Informazioni di elaborazione" in footer
        assert "Profilo modelli" in footer
        assert "balanced" in footer
        assert "33,518" in footer
        assert "openai/gpt-5.5" in footer

    def test_footer_in_english(self):
        footer = format_run_metadata_footer(
            metrics_payload=self._payload(),
            language="English",
        )
        assert "## Run metadata" in footer
        assert "Processing time" in footer

    def test_append_and_replace_footer(self):
        base = "## Disclaimer\n\nNot financial advice."
        first = append_run_metadata_footer(
            base,
            metrics_payload=self._payload(),
            language="Italian",
        )
        assert "Informazioni di elaborazione" in first

        updated_payload = self._payload()
        updated_payload["duration_seconds"] = 120.0
        second = append_run_metadata_footer(
            first,
            metrics_payload=updated_payload,
            language="Italian",
        )
        assert second.count("Informazioni di elaborazione") == 1
        assert "2m 0s" in second

    def test_strip_footer(self):
        with_footer = append_run_metadata_footer(
            "Body",
            metrics_payload=self._payload(),
            language="English",
        )
        assert strip_run_metadata_footer(with_footer) == "Body"
