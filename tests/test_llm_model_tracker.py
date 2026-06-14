"""Tests for per-agent resolved LLM model tracking."""

from types import SimpleNamespace

from financial_researcher.services.llm_model_tracker import (
    RunModelTracker,
    _ModelCaptureLogger,
    extract_resolved_model,
    reset_run_model_tracker,
    tracked_llm_call,
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


class TestModelCaptureLogger:
    def test_logs_model_for_active_agent(self):
        reset_run_model_tracker()
        from financial_researcher.services import llm_model_tracker as module

        logger = _ModelCaptureLogger()

        def fake_call():
            logger.log_success_event(
                {},
                SimpleNamespace(model="google/gemini-2.5-flash"),
                0,
                1,
            )

        tracked_llm_call("market", fake_call)
        assert module.get_run_model_tracker().snapshot() == {
            "market": ["google/gemini-2.5-flash"]
        }
