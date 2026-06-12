"""Guard tests for CrewAI LLM compatibility monkey-patches."""

import inspect

import pytest

pytest.importorskip("crewai")

from crewai import LLM

from financial_researcher import llm_compat


class TestLlmCompatPatches:
    def test_prepare_completion_params_is_patched(self):
        assert LLM._prepare_completion_params is llm_compat._prepare_completion_params

    def test_supports_stop_words_is_patched(self):
        assert LLM.supports_stop_words is llm_compat._supports_stop_words

    def test_prepare_completion_params_signature(self):
        sig = inspect.signature(LLM._prepare_completion_params)
        params = list(sig.parameters)
        assert params[0] == "self"
        assert "messages" in params

    def test_supports_stop_words_signature(self):
        sig = inspect.signature(LLM.supports_stop_words)
        params = list(sig.parameters)
        assert params == ["self"]
        assert sig.return_annotation in (bool, inspect.Signature.empty)
