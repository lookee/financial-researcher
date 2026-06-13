"""Tests for per-agent model and reasoning-effort configuration."""

import os

import pytest

from financial_researcher.agent_llm import (
    build_agent_llm,
    build_openrouter_auto_plugins,
    clear_profile_caches,
    describe_active_profile,
    get_default_profile_name,
    get_profile_description,
    list_model_profile_names,
    resolve_active_profile_name,
    resolve_agent_model,
    resolve_openrouter_auto_tradeoff,
    resolve_reasoning_effort,
    uses_openrouter_auto_routing,
)
from financial_researcher.settings import _load_yaml_settings


@pytest.fixture(autouse=True)
def _reset_profile_caches(monkeypatch):
    monkeypatch.delenv("FR_MODEL_PROFILE", raising=False)
    for key in (
        "FR_MODEL_MARKET",
        "FR_MODEL_NEWS",
        "FR_MODEL_OUTLOOK",
        "FR_MODEL_CALENDAR",
        "FR_MODEL_CHIEF",
    ):
        monkeypatch.delenv(key, raising=False)
    clear_profile_caches()
    _load_yaml_settings.cache_clear()
    yield
    clear_profile_caches()
    _load_yaml_settings.cache_clear()


def test_list_model_profile_names():
    names = list_model_profile_names()
    assert "balanced" in names
    assert "frontier" in names
    assert "budget" in names
    assert "anthropic" in names
    assert "deepseek" in names
    assert "multi" in names
    assert "free_groq" in names
    assert "free_openrouter_nex" in names
    assert "openrouter_auto" in names


def test_deepseek_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "deepseek")
    assert resolve_agent_model("market") == "deepseek/deepseek-v4-flash"
    assert resolve_agent_model("news") == "deepseek/deepseek-v4-pro"
    assert resolve_agent_model("chief") == "deepseek/deepseek-v4-pro"


def test_deepseek_profile_reasoning(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "deepseek")
    assert resolve_reasoning_effort("market") == "low"
    assert resolve_reasoning_effort("news") == "medium"
    assert resolve_reasoning_effort("chief") == "medium"


def test_multi_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "multi")
    assert resolve_agent_model("market") == "deepseek/deepseek-v4-flash"
    assert resolve_agent_model("news") == "anthropic/claude-sonnet-4-6"
    assert resolve_agent_model("outlook") == "openai/gpt-5.4"
    assert resolve_agent_model("chief") == "openai/gpt-5.5"


def test_multi_profile_reasoning(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "multi")
    assert resolve_reasoning_effort("market") == "low"
    assert resolve_reasoning_effort("news") == "medium"
    assert resolve_reasoning_effort("chief") == "medium"


def test_anthropic_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "anthropic")
    assert resolve_agent_model("market") == "anthropic/claude-haiku-4-5"
    assert resolve_agent_model("news") == "anthropic/claude-sonnet-4-6"
    assert resolve_agent_model("chief") == "anthropic/claude-sonnet-4-6"
    assert resolve_reasoning_effort("news") == "medium"


def test_free_openrouter_nex_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "free_openrouter_nex")
    model = resolve_agent_model("chief")
    assert model == "openrouter/nex-agi/nex-n2-pro:free"
    assert resolve_reasoning_effort("chief") == "medium"
    assert resolve_agent_model("market") == model


def test_openrouter_auto_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto")
    assert resolve_agent_model("market") == "openrouter/openrouter/auto"
    assert resolve_agent_model("chief") == "openrouter/openrouter/auto"
    assert resolve_reasoning_effort("news") == "medium"
    assert resolve_reasoning_effort("market") == "low"


def test_openrouter_auto_default_tradeoff(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto")
    monkeypatch.delenv("OPENROUTER_AUTO_TRADEOFF", raising=False)
    assert resolve_openrouter_auto_tradeoff() == 7
    assert uses_openrouter_auto_routing() is True


def test_openrouter_auto_tradeoff_from_env(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto")
    monkeypatch.setenv("OPENROUTER_AUTO_TRADEOFF", "9")
    assert resolve_openrouter_auto_tradeoff() == 9


def test_build_openrouter_auto_plugins():
    plugins = build_openrouter_auto_plugins(9)
    assert plugins == [{"id": "auto-router", "cost_quality_tradeoff": 9}]


def test_build_agent_llm_attaches_openrouter_plugins(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto")
    monkeypatch.setenv("OPENROUTER_AUTO_TRADEOFF", "4")
    llm = build_agent_llm("market")
    assert llm.model == "openrouter/openrouter/auto"
    assert llm.additional_params["plugins"] == [
        {"id": "auto-router", "cost_quality_tradeoff": 4}
    ]


def test_describe_active_profile_includes_openrouter_savings(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto")
    monkeypatch.setenv("OPENROUTER_AUTO_TRADEOFF", "8")
    assert "openrouter_savings=8/10" in describe_active_profile()


def test_default_balanced_profile_models():
    assert resolve_active_profile_name() == "balanced"
    assert resolve_agent_model("market") == "openai/gpt-5.4-mini"
    assert resolve_agent_model("news") == "openai/gpt-5.5"
    assert resolve_agent_model("outlook") == "openai/gpt-5.4"
    assert resolve_agent_model("calendar") == "openai/gpt-5.4-mini"
    assert resolve_agent_model("chief") == "openai/gpt-5.5"


def test_frontier_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "frontier")
    assert resolve_agent_model("market") == "openai/gpt-5.5"
    assert resolve_agent_model("chief") == "openai/gpt-5.5"
    assert resolve_reasoning_effort("news") == "high"


def test_budget_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "budget")
    assert resolve_agent_model("news") == "openai/gpt-5.4-mini"
    assert resolve_agent_model("chief") == "openai/gpt-5.4"


def test_free_groq_profile_uses_groq(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "free_groq")
    assert resolve_agent_model("market").startswith("groq/")


def test_model_override_via_env_beats_profile(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "budget")
    monkeypatch.setenv("FR_MODEL_OUTLOOK", "openai/gpt-5.5")
    assert resolve_agent_model("outlook") == "openai/gpt-5.5"
    assert resolve_agent_model("news") == "openai/gpt-5.4-mini"


def test_reasoning_effort_balanced_tiers():
    assert resolve_reasoning_effort("market") == "low"
    assert resolve_reasoning_effort("calendar") == "low"
    assert resolve_reasoning_effort("outlook") == "low"
    assert resolve_reasoning_effort("news") == "medium"
    assert resolve_reasoning_effort("chief") == "medium"


def test_reasoning_override_via_env_beats_profile(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "balanced")
    monkeypatch.setenv("FR_REASONING_NEWS", "high")
    assert resolve_reasoning_effort("news") == "high"
    assert resolve_reasoning_effort("market") == "low"


def test_get_default_profile_name():
    assert get_default_profile_name() == "balanced"


def test_get_profile_description_deepseek():
    desc = get_profile_description("deepseek").lower()
    assert "deepseek" in desc


def test_get_profile_description_multi():
    desc = get_profile_description("multi").lower()
    assert "deepseek" in desc
    assert "anthropic" in desc or "openai" in desc


def test_build_agent_llm_sets_model_and_reasoning(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "balanced")
    llm = build_agent_llm("market")
    assert llm.model == "openai/gpt-5.4-mini"
    assert llm.reasoning_effort == "low"


def test_describe_active_profile(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "budget")
    summary = describe_active_profile()
    assert summary.startswith("budget (")
    assert "chief=openai/gpt-5.4" in summary


def test_get_profile_description():
    assert "frontier" in get_profile_description("frontier").lower()


def test_unknown_profile_raises(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "nonexistent")
    with pytest.raises(ValueError, match="Unknown model profile"):
        resolve_agent_model("market")
