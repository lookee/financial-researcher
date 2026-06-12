"""Tests for centralized runtime path helpers."""

import json
from pathlib import Path

from financial_researcher.paths import (
    briefings_dir,
    data_dir,
    ensure_runtime_dirs,
    identity_data_dir,
    market_data_dir,
    metrics_dir,
    output_dir,
    project_home,
)
from financial_researcher.services.run_metrics import metrics_output_path, write_run_metrics
from financial_researcher.services.watchlist_context import briefing_output_path
from financial_researcher.storage.identity_store import IdentityStore
from financial_researcher.storage.market_cache import MarketCache


class TestProjectHome:
    def test_defaults_to_cwd(self, monkeypatch):
        monkeypatch.delenv("FINANCIAL_RESEARCHER_HOME", raising=False)
        assert project_home() == Path.cwd()

    def test_env_override(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("FINANCIAL_RESEARCHER_HOME", str(tmp_path))
        assert project_home() == tmp_path.resolve()
        assert output_dir() == tmp_path / "output"
        assert data_dir() == tmp_path / "data"


class TestRuntimeArtifactsUnderHome:
    def test_all_artifacts_use_financial_researcher_home(
        self, monkeypatch, tmp_path: Path
    ):
        monkeypatch.setenv("FINANCIAL_RESEARCHER_HOME", str(tmp_path))
        ensure_runtime_dirs()

        briefing_path = Path(briefing_output_path("close"))
        metrics_path = metrics_output_path(date_str="2026-06-12", session="midday")
        identity_store = IdentityStore()
        market_cache = MarketCache()

        assert briefing_path.parent == briefings_dir() == tmp_path / "output" / "briefings"
        assert metrics_path.parent == metrics_dir() == tmp_path / "output" / "metrics"
        assert identity_store.base_dir == identity_data_dir() == tmp_path / "data" / "identity"
        assert market_cache.base_dir == market_data_dir() == tmp_path / "data" / "market"

        write_run_metrics(
            metrics_path,
            {
                "session": "midday",
                "language": "English",
                "instrument_count": 1,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "successful_requests": 0,
                "duration_seconds": 0.1,
                "postprocess_warnings": [],
            },
        )
        assert metrics_path.is_file()
        loaded = json.loads(metrics_path.read_text(encoding="utf-8"))
        assert loaded["session"] == "midday"
