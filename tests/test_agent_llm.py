"""Tests for per-agent model and reasoning-effort configuration."""

import os

import pytest

pytest.importorskip("crewai")

from financial_researcher.agent_llm import (
    build_agent_llm,
    build_openrouter_auto_plugins,
    clear_profile_caches,
    describe_active_profile,
    get_default_profile_name,
    is_free_profile,
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
        "OPENROUTER_AUTO_TRADEOFF",
    ):
        monkeypatch.delenv(key, raising=False)
    clear_profile_caches()
    _load_yaml_settings.cache_clear()
    yield
    clear_profile_caches()
    _load_yaml_settings.cache_clear()


def test_list_model_profile_names():
    names = list_model_profile_names()
    assert "openai_balanced" in names
    assert "openai_frontier" in names
    assert "openai_economy" in names
    assert "anthropic_balanced" in names
    assert "deepseek_balanced" in names
    assert "mixed_balanced" in names
    assert "free_groq" in names
    assert "free_openrouter_nex" in names
    assert "openrouter_auto_quality" in names
    assert "openrouter_auto_balanced" in names
    assert "openrouter_auto_economy" in names


def test_is_free_profile():
    assert is_free_profile("free_groq") is True
    assert is_free_profile("free_openrouter_nex") is True
    assert is_free_profile("openai_balanced") is False
    assert is_free_profile("openrouter_auto_economy") is False


def test_deepseek_balanced_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "deepseek_balanced")
    assert resolve_agent_model("market") == "deepseek/deepseek-v4-flash"
    assert resolve_agent_model("chief") == "deepseek/deepseek-v4-pro"


def test_mixed_balanced_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "mixed_balanced")
    assert resolve_agent_model("news") == "anthropic/claude-sonnet-4-6"
    assert resolve_agent_model("chief") == "openai/gpt-5.5"


def test_free_openrouter_nex_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "free_openrouter_nex")
    model = resolve_agent_model("chief")
    assert model == "openrouter/nex-agi/nex-n2-pro:free"
    assert is_free_profile("free_openrouter_nex")


def test_openrouter_auto_quality_tradeoff(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto_quality")
    assert resolve_openrouter_auto_tradeoff() == 1


def test_openrouter_auto_economy_tradeoff(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto_economy")
    assert resolve_openrouter_auto_tradeoff() == 10


def test_openrouter_auto_balanced_tradeoff(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto_balanced")
    assert resolve_openrouter_auto_tradeoff() == 7
    assert uses_openrouter_auto_routing() is True


def test_openrouter_tradeoff_env_overrides_profile(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto_economy")
    monkeypatch.setenv("OPENROUTER_AUTO_TRADEOFF", "3")
    clear_profile_caches()
    assert resolve_openrouter_auto_tradeoff() == 3


def test_build_openrouter_auto_plugins():
    assert build_openrouter_auto_plugins(9) == [
        {"id": "auto-router", "cost_quality_tradeoff": 9}
    ]


def test_build_agent_llm_attaches_openrouter_plugins(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto_balanced")
    monkeypatch.setenv("OPENROUTER_AUTO_TRADEOFF", "4")
    llm = build_agent_llm("market")
    assert llm.additional_params["plugins"] == [
        {"id": "auto-router", "cost_quality_tradeoff": 4}
    ]


def test_describe_free_profile_prefix(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "free_groq")
    assert describe_active_profile().startswith("[FREE] free_groq")


def test_default_openai_balanced_profile_models():
    assert resolve_active_profile_name() == "openai_balanced"
    assert get_default_profile_name() == "openai_balanced"
    assert resolve_agent_model("chief") == "openai/gpt-5.5"


def test_openai_frontier_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openai_frontier")
    assert resolve_agent_model("chief") == "openai/gpt-5.5"
    assert resolve_reasoning_effort("news") == "high"


def test_openai_economy_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openai_economy")
    assert resolve_agent_model("news") == "openai/gpt-5.4-mini"


def test_free_groq_profile_uses_groq(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "free_groq")
    assert resolve_agent_model("market").startswith("groq/")


def test_unknown_profile_raises(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "nonexistent")
    with pytest.raises(ValueError, match="Unknown model profile"):
        resolve_agent_model("market")


def test_retired_profile_name_raises(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "balanced")
    with pytest.raises(ValueError, match="Unknown model profile"):
        resolve_agent_model("market")
