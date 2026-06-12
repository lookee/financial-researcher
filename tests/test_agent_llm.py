"""Tests for per-agent model and reasoning-effort configuration."""

import os

import pytest

from financial_researcher.agent_llm import (
    build_agent_llm,
    clear_profile_caches,
    describe_active_profile,
    get_profile_description,
    list_model_profile_names,
    resolve_active_profile_name,
    resolve_agent_model,
    resolve_reasoning_effort,
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
    assert "free_groq" in names
    assert "free_openrouter_nex" in names


def test_free_openrouter_nex_profile_models(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "free_openrouter_nex")
    model = resolve_agent_model("chief")
    assert model == "openrouter/nex-agi/nex-n2-pro:free"
    assert resolve_reasoning_effort("chief") == "medium"
    assert resolve_agent_model("market") == model


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
