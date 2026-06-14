"""Tests for per-agent resolved LLM model tracking."""

from types import SimpleNamespace

from financial_researcher.services.llm_model_tracker import (
    RunModelTracker,
    extract_resolved_model,
    reset_run_model_tracker,
)


class TestExtractResolvedModel:
    def test_reads_model_from_object(self):
        response = SimpleNamespace(model="anthropic/claude-sonnet-4.6")
        assert extract_resolved_model(response) == "anthropic/claude-sonnet-4.6"

    def test_reads_model_from_dict(self):
        assert extract_resolved_model({"model": "deepseek/deepseek-v3.2"}) == (
            "deepseek/deepseek-v3.2"
        )

    def test_returns_none_when_missing(self):
        assert extract_resolved_model({}) is None
        assert extract_resolved_model(None) is None


class TestRunModelTracker:
    def test_records_distinct_models_in_order(self):
        tracker = RunModelTracker()
        tracker.record("news", "anthropic/claude-haiku-4-5")
        tracker.record("news", "deepseek/deepseek-v3.2")
        tracker.record("news", "anthropic/claude-haiku-4-5")
        assert tracker.snapshot() == {
            "news": [
                "anthropic/claude-haiku-4-5",
                "deepseek/deepseek-v3.2",
            ]
        }

    def test_reset_clears_state(self):
        tracker = RunModelTracker()
        tracker.record("chief", "openai/gpt-5.5")
        tracker.reset()
        assert tracker.snapshot() == {}


class TestLitellmCompletionPatch:
    def test_wrap_stream_records_last_chunk_model(self):
        reset_run_model_tracker()
        from financial_researcher.services.llm_model_tracker import (
            _wrap_stream,
            get_run_model_tracker,
        )

        chunks = list(
            _wrap_stream(
                "news",
                (
                    SimpleNamespace(model="openrouter/openrouter/auto"),
                    SimpleNamespace(model="anthropic/claude-haiku-4-5"),
                ),
            )
        )
        assert len(chunks) == 2
        assert get_run_model_tracker().snapshot() == {
            "news": ["anthropic/claude-haiku-4-5"]
        }

    def test_tracked_llm_call_records_resolved_model(self):
        reset_run_model_tracker()
        from financial_researcher.services import llm_model_tracker as module

        module.tracked_llm_call(
            "news",
            lambda: SimpleNamespace(model="deepseek/deepseek-v3.2"),
        )
        assert module.get_run_model_tracker().snapshot() == {}

        def invoke():
            module._record_agent_model(
                module._active_agent(),
                SimpleNamespace(model="deepseek/deepseek-v3.2"),
            )

        module.tracked_llm_call("news", invoke)
        assert module.get_run_model_tracker().snapshot() == {
            "news": ["deepseek/deepseek-v3.2"]
        }
